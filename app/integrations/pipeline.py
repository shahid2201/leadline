from sqlalchemy import select

from app.db.session import AsyncSessionLocal
from app.models.lead import Lead
from app.observability.metrics import business_kpi_events_total
from app.repositories.integration_repository import IntegrationConnectionRepository
from app.services.integration_service import IntegrationService


async def process_integration_event(payload: dict[str, str]) -> None:
    event = payload.get("event")
    tenant_id = payload.get("tenant_id")
    lead_id = payload.get("lead_id")
    if not event or not tenant_id:
        return

    async with AsyncSessionLocal() as db:
        repository = IntegrationConnectionRepository(db)
        service = IntegrationService(repository)

        if not lead_id:
            return

        lead_stmt = select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
        lead_result = await db.execute(lead_stmt)
        lead = lead_result.scalar_one_or_none()
        if not lead:
            return

        lead_payload = {
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "company": lead.company,
            "status": lead.status,
            "lead_score": lead.lead_score,
        }

        if event in {"integration.lead.created", "integration.lead.updated"}:
            await service.sync_hubspot_lead(tenant_id=tenant_id, lead_payload=lead_payload)
            await service.publish_domain_event(event_type=event, payload=lead_payload)

        if event == "integration.lead.score_updated":
            await service.sync_hubspot_activity(
                tenant_id=tenant_id,
                lead_id=lead_id,
                activity_payload={
                    "event": "lead.score_updated",
                    "lead_score": lead.lead_score,
                },
            )
            if lead.lead_score >= 80:
                await service.notify_high_intent(
                    tenant_id=tenant_id,
                    lead_id=lead_id,
                    score=float(lead.lead_score),
                )
                business_kpi_events_total.labels(
                    event="high_intent_lead",
                    tenant_id=tenant_id,
                ).inc()
            await service.publish_domain_event(event_type=event, payload=lead_payload)

        await db.commit()
