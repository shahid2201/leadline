from datetime import datetime
from typing import Any

from app.integrations.google_calendar import GoogleCalendarClient
from app.integrations.hubspot import HubSpotClient
from app.integrations.slack import SlackClient
from app.integrations.svix_client import SvixClient
from app.repositories.integration_repository import IntegrationConnectionRepository
from app.security.encryption import EncryptionService


class IntegrationService:
    def __init__(self, repository: IntegrationConnectionRepository) -> None:
        self.repository = repository
        self.encryption = EncryptionService()
        self.hubspot = HubSpotClient()
        self.calendar = GoogleCalendarClient()
        self.slack = SlackClient()
        self.svix = SvixClient()

    async def sync_hubspot_lead(self, tenant_id: str, lead_payload: dict[str, Any]) -> bool:
        synced = self.hubspot.sync_lead(lead_payload=lead_payload)
        if synced:
            connection = await self.repository.upsert(
                tenant_id=tenant_id,
                integration_type="hubspot",
                data={
                    "auth_data": self.encryption.encrypt_json({"provider": "hubspot"}),
                    "status": "active",
                },
            )
            await self.repository.mark_synced(connection)
        return synced

    async def sync_hubspot_activity(
        self,
        tenant_id: str,
        lead_id: str,
        activity_payload: dict[str, Any],
    ) -> bool:
        synced = self.hubspot.sync_activity(lead_id=lead_id, activity_payload=activity_payload)
        if synced:
            connection = await self.repository.upsert(
                tenant_id=tenant_id,
                integration_type="hubspot",
                data={
                    "auth_data": self.encryption.encrypt_json({"provider": "hubspot"}),
                    "status": "active",
                },
            )
            await self.repository.mark_synced(connection)
        return synced

    async def notify_high_intent(self, tenant_id: str, lead_id: str, score: float) -> bool:
        return self.slack.notify_high_intent(tenant_id=tenant_id, lead_id=lead_id, score=score)

    async def publish_domain_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        return self.svix.publish_event(event_type=event_type, payload=payload)

    async def get_calendar_availability(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
    ) -> list[dict[str, str]]:
        return self.calendar.get_availability(
            calendar_id=calendar_id,
            time_min=time_min,
            time_max=time_max,
        )

    async def create_calendar_booking(
        self,
        tenant_id: str,
        calendar_id: str,
        summary: str,
        start: datetime,
        end: datetime,
    ) -> bool:
        booked = self.calendar.create_booking(
            calendar_id=calendar_id,
            summary=summary,
            start=start,
            end=end,
        )
        if booked:
            connection = await self.repository.upsert(
                tenant_id=tenant_id,
                integration_type="google_calendar",
                data={
                    "auth_data": self.encryption.encrypt_json({"provider": "google_calendar"}),
                    "status": "active",
                },
            )
            await self.repository.mark_synced(connection)
        return booked
