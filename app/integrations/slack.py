import logging

import requests

from app.core.config import get_settings
from app.observability.metrics import integration_calls_total
from app.observability.tracing import traced_span

logger = logging.getLogger(__name__)


class SlackClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def notify_high_intent(self, tenant_id: str, lead_id: str, score: float) -> bool:
        with traced_span("integration.slack.notify_high_intent", {"provider": "slack"}):
            webhook_url = self.settings.slack_webhook_url
            if not webhook_url:
                logger.info("Slack webhook not configured; notification skipped")
                integration_calls_total.labels(
                    provider="slack",
                    operation="notify_high_intent",
                    outcome="skipped",
                ).inc()
                return False

            response = requests.post(
                webhook_url,
                json={
                    "text": (
                        "High-intent lead detected for tenant "
                        f"{tenant_id}: {lead_id} (score={score})"
                    ),
                },
                timeout=10,
            )
            ok = int(response.status_code) < 300
            integration_calls_total.labels(
                provider="slack",
                operation="notify_high_intent",
                outcome="success" if ok else "error",
            ).inc()
            return ok
