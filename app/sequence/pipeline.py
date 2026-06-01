from app.db.session import AsyncSessionLocal
from app.integrations.delivery import DeliveryService
from app.models.lead import Lead
from app.models.lead_timeline_event import LeadTimelineEvent
from app.queue.sqs import QueueJob, SQSPublisher
from app.repositories.lead_repository import LeadRepository
from app.repositories.sequence_repository import (
    SequenceEnrollmentRepository,
    SequenceRepository,
    SequenceStepRepository,
)
from app.services.usage_tracking_service import UsageTrackingService


async def process_sequence_trigger_event(payload: dict[str, str]) -> None:
    tenant_id = payload.get("tenant_id")
    lead_id = payload.get("lead_id")
    trigger = payload.get("trigger")
    if not tenant_id or not lead_id or not trigger:
        return

    publisher = SQSPublisher()
    async with AsyncSessionLocal() as db:
        sequences = SequenceRepository(db)
        enrollments = SequenceEnrollmentRepository(db)
        active = await sequences.list_active_sequences_by_trigger(
            tenant_id=tenant_id,
            trigger=trigger,
        )
        for sequence in active:
            enrollment = await enrollments.create(
                tenant_id=tenant_id,
                data={
                    "lead_id": lead_id,
                    "sequence_id": sequence.id,
                    "status": "active",
                    "current_step_index": 0,
                },
            )
            db.add(
                LeadTimelineEvent(
                    tenant_id=tenant_id,
                    lead_id=lead_id,
                    type="sequence_enrolled",
                    payload={"sequence_id": sequence.id, "enrollment_id": enrollment.id},
                )
            )
            publisher.publish(
                QueueJob(
                    queue_name="sequence_jobs",
                    payload={
                        "event": "sequence.step.execute",
                        "tenant_id": tenant_id,
                        "enrollment_id": enrollment.id,
                    },
                )
            )
        await db.commit()


async def process_sequence_step_event(payload: dict[str, str]) -> None:
    tenant_id = payload.get("tenant_id")
    enrollment_id = payload.get("enrollment_id")
    if not tenant_id or not enrollment_id:
        return

    publisher = SQSPublisher()
    delivery = DeliveryService()
    async with AsyncSessionLocal() as db:
        enrollments = SequenceEnrollmentRepository(db)
        sequences = SequenceRepository(db)
        steps = SequenceStepRepository(db)
        leads = LeadRepository(db)

        enrollment = await enrollments.get(tenant_id=tenant_id, enrollment_id=enrollment_id)
        if not enrollment or enrollment.status != "active":
            return

        sequence = await sequences.get(tenant_id=tenant_id, sequence_id=enrollment.sequence_id)
        if not sequence:
            return

        lead = await leads.get(tenant_id=tenant_id, lead_id=enrollment.lead_id)
        if not lead:
            return

        ordered_steps = await steps.list_for_sequence(sequence_id=sequence.id)
        current_idx = enrollment.current_step_index
        if current_idx >= len(ordered_steps):
            enrollment.status = "completed"
            await db.commit()
            return

        step = ordered_steps[current_idx]
        delivered = await _execute_step(
            delivery=delivery,
            lead=lead,
            step_type=step.type,
            template=step.template,
        )

        usage_service = UsageTrackingService(db)
        if delivered == "email":
            await usage_service.increment(tenant_id, emails_sent=1)
        elif delivered == "sms":
            await usage_service.increment(tenant_id, sms_sent=1)

        db.add(
            LeadTimelineEvent(
                tenant_id=tenant_id,
                lead_id=lead.id,
                type="sequence_step_executed",
                payload={
                    "sequence_id": sequence.id,
                    "enrollment_id": enrollment.id,
                    "step_id": step.id,
                    "step_type": step.type,
                },
            )
        )

        enrollment.current_step_index = current_idx + 1
        if enrollment.current_step_index >= len(ordered_steps):
            enrollment.status = "completed"
        else:
            publisher.publish(
                QueueJob(
                    queue_name="sequence_jobs",
                    payload={
                        "event": "sequence.step.execute",
                        "tenant_id": tenant_id,
                        "enrollment_id": enrollment.id,
                    },
                )
            )

        await db.commit()


async def _execute_step(
    delivery: DeliveryService,
    lead: Lead,
    step_type: str,
    template: str | None,
) -> str | None:
    """Execute the step and return a delivery type token (email|sms|None)."""
    content = template or ""
    if step_type == "email" and lead.email:
        delivery.send_email(to_email=lead.email, subject="Lead Line follow-up", body=content)
        return "email"
    elif step_type == "sms" and lead.phone:
        delivery.send_sms(to_phone=lead.phone, body=content)
        return "sms"
    elif step_type in {"wait", "task"}:
        return None
    return None
