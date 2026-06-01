import logging
from typing import Any

import requests

from app.core.config import get_settings
from app.observability.metrics import integration_calls_total
from app.observability.tracing import traced_span

logger = logging.getLogger(__name__)


class HubSpotClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict[str, str] | None:
        if not self.settings.hubspot_access_token:
            return None
        return {
            "Authorization": f"Bearer {self.settings.hubspot_access_token}",
            "Content-Type": "application/json",
        }

    def sync_lead(self, lead_payload: dict[str, Any]) -> bool:
        with traced_span("integration.hubspot.sync_lead", {"provider": "hubspot"}):
            headers = self._headers()
            if headers is None:
                logger.info("HubSpot token not configured; lead sync skipped")
                integration_calls_total.labels(
                    provider="hubspot",
                    operation="sync_lead",
                    outcome="skipped",
                ).inc()
                return False

            url = f"{self.settings.hubspot_api_base_url}/crm/v3/objects/contacts"
            body = {
                "properties": {
                    "email": lead_payload.get("email"),
                    "firstname": lead_payload.get("name"),
                    "phone": lead_payload.get("phone"),
                    "company": lead_payload.get("company"),
                }
            }
            response = requests.post(url, json=body, headers=headers, timeout=10)
            ok = int(response.status_code) < 300
            integration_calls_total.labels(
                provider="hubspot",
                operation="sync_lead",
                outcome="success" if ok else "error",
            ).inc()
            return ok

    def sync_activity(self, lead_id: str, activity_payload: dict[str, Any]) -> bool:
        with traced_span("integration.hubspot.sync_activity", {"provider": "hubspot"}):
            headers = self._headers()
            if headers is None:
                logger.info("HubSpot token not configured; activity sync skipped")
                integration_calls_total.labels(
                    provider="hubspot",
                    operation="sync_activity",
                    outcome="skipped",
                ).inc()
                return False

            url = f"{self.settings.hubspot_api_base_url}/crm/v3/objects/notes"
            body = {
                "properties": {
                    "hs_note_body": str(activity_payload),
                    "leadline_lead_id": lead_id,
                }
            }
            response = requests.post(url, json=body, headers=headers, timeout=10)
            ok = int(response.status_code) < 300
            integration_calls_total.labels(
                provider="hubspot",
                operation="sync_activity",
                outcome="success" if ok else "error",
            ).inc()
            return ok
