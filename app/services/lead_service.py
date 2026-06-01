import re
from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.lead_timeline_event import LeadTimelineEvent
from app.observability.metrics import business_kpi_events_total
from app.observability.tracing import traced_span
from app.queue.sqs import QueueJob, SQSPublisher
from app.repositories.lead_repository import LeadRepository, LeadTimelineRepository


def _normalize_email(email: str | None) -> str | None:
    if not email:
        return None
    return email.strip().lower()


def _normalize_phone(phone: str | None) -> str | None:
    if not phone:
        return None
    digits = re.sub(r"[^0-9+]", "", phone)
    return digits or None


@dataclass
class LeadCreateOutcome:
    deduplicated: bool
    lead: Lead


class LeadService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.leads = LeadRepository(db)
        self.timeline = LeadTimelineRepository(db)
        self.publisher = SQSPublisher()

    def _publish_lifecycle(self, tenant_id: str, lead_id: str, event: str) -> None:
        self.publisher.publish(
            QueueJob(
                queue_name="routing_jobs",
                payload={
                    "event": event,
                    "tenant_id": tenant_id,
                    "lead_id": lead_id,
                },
            )
        )
        self.publisher.publish(
            QueueJob(
                queue_name="integration_jobs",
                payload={
                    "event": f"integration.{event}",
                    "tenant_id": tenant_id,
                    "lead_id": lead_id,
                },
            )
        )
        trigger_map = {
            "lead.created": "lead_created",
            "lead.updated": "lead_updated",
            "lead.score_updated": "score_updated",
        }
        trigger = trigger_map.get(event, event.replace(".", "_"))
        self.publisher.publish(
            QueueJob(
                queue_name="sequence_jobs",
                payload={
                    "event": "sequence.trigger",
                    "tenant_id": tenant_id,
                    "lead_id": lead_id,
                    "trigger": trigger,
                },
            )
        )

    async def create_lead(self, tenant_id: str, payload: dict[str, Any]) -> LeadCreateOutcome:
        with traced_span("lead.create", {"tenant.id": tenant_id}):
            payload = dict(payload)
            payload["email"] = _normalize_email(payload.get("email"))
            payload["phone"] = _normalize_phone(payload.get("phone"))

            existing = await self.leads.find_duplicate_by_email_or_phone(
                tenant_id=tenant_id,
                email=payload.get("email"),
                phone=payload.get("phone"),
            )
            if existing:
                return LeadCreateOutcome(deduplicated=True, lead=existing)

            lead = await self.leads.create(tenant_id=tenant_id, data=payload)
            await self.timeline.create(
                tenant_id=tenant_id,
                lead_id=lead.id,
                data={"type": "lead_created", "payload": {"source": "api"}},
            )
            await self.db.commit()
            self._publish_lifecycle(tenant_id=tenant_id, lead_id=lead.id, event="lead.created")
            business_kpi_events_total.labels(event="lead_created", tenant_id=tenant_id).inc()
            return LeadCreateOutcome(deduplicated=False, lead=lead)

    async def list_leads(self, tenant_id: str, status: str | None = None) -> list[Lead]:
        return await self.leads.list(tenant_id=tenant_id, status=status)

    async def get_lead(self, tenant_id: str, lead_id: str) -> Lead | None:
        return await self.leads.get(tenant_id=tenant_id, lead_id=lead_id)

    async def update_lead(
        self,
        tenant_id: str,
        lead_id: str,
        payload: dict[str, Any],
    ) -> Lead | None:
        with traced_span("lead.update", {"tenant.id": tenant_id, "lead.id": lead_id}):
            lead = await self.leads.get(tenant_id=tenant_id, lead_id=lead_id)
            if not lead:
                return None

            data = dict(payload)
            if "email" in data:
                data["email"] = _normalize_email(data["email"])
            if "phone" in data:
                data["phone"] = _normalize_phone(data["phone"])

            updated = await self.leads.update(lead, data)
            await self.db.commit()
            self._publish_lifecycle(tenant_id=tenant_id, lead_id=lead_id, event="lead.updated")
            business_kpi_events_total.labels(event="lead_updated", tenant_id=tenant_id).inc()
            return updated

    async def delete_lead(self, tenant_id: str, lead_id: str) -> bool:
        lead = await self.leads.get(tenant_id=tenant_id, lead_id=lead_id)
        if not lead:
            return False
        await self.leads.delete(lead)
        await self.db.commit()
        return True

    async def create_timeline_event(
        self,
        tenant_id: str,
        lead_id: str,
        payload: dict[str, Any],
    ) -> LeadTimelineEvent | None:
        lead = await self.leads.get(tenant_id=tenant_id, lead_id=lead_id)
        if not lead:
            return None
        event = await self.timeline.create(tenant_id=tenant_id, lead_id=lead_id, data=payload)
        await self.db.commit()
        self.publisher.publish(
            QueueJob(
                queue_name="integration_jobs",
                payload={
                    "event": "integration.timeline.created",
                    "tenant_id": tenant_id,
                    "lead_id": lead_id,
                    "timeline_event_id": event.id,
                },
            )
        )
        return event

    async def list_timeline_events(self, tenant_id: str, lead_id: str) -> list[LeadTimelineEvent]:
        return await self.timeline.list_for_lead(tenant_id=tenant_id, lead_id=lead_id)

    async def get_timeline_event(self, tenant_id: str, event_id: str) -> LeadTimelineEvent | None:
        return await self.timeline.get(tenant_id=tenant_id, event_id=event_id)

    async def update_timeline_event(
        self,
        tenant_id: str,
        event_id: str,
        payload: dict[str, Any],
    ) -> LeadTimelineEvent | None:
        event = await self.timeline.get(tenant_id=tenant_id, event_id=event_id)
        if not event:
            return None
        updated = await self.timeline.update(event, payload)
        await self.db.commit()
        return updated

    async def delete_timeline_event(self, tenant_id: str, event_id: str) -> bool:
        event = await self.timeline.get(tenant_id=tenant_id, event_id=event_id)
        if not event:
            return False
        await self.timeline.delete(event)
        await self.db.commit()
        return True
