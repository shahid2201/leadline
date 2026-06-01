import json
import logging
from typing import Any

import requests

from app.core.config import get_settings
from app.observability.metrics import integration_calls_total
from app.observability.tracing import traced_span

logger = logging.getLogger(__name__)


class SvixClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def publish_event(self, event_type: str, payload: dict[str, Any]) -> bool:
        with traced_span("integration.svix.publish_event", {"provider": "svix"}):
            if not self.settings.svix_token or not self.settings.svix_app_id:
                logger.info("Svix credentials not configured; outbound webhook skipped")
                integration_calls_total.labels(
                    provider="svix",
                    operation="publish_event",
                    outcome="skipped",
                ).inc()
                return False

            url = f"{self.settings.svix_server_url}/api/v1/app/{self.settings.svix_app_id}/msg"
            headers = {
                "Authorization": self.settings.svix_token,
                "Content-Type": "application/json",
            }
            body = {
                "eventType": event_type,
                "payload": payload,
            }
            response = requests.post(url, headers=headers, data=json.dumps(body), timeout=10)
            ok = int(response.status_code) < 300
            integration_calls_total.labels(
                provider="svix",
                operation="publish_event",
                outcome="success" if ok else "error",
            ).inc()
            return ok
