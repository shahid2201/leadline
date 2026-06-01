import logging
from datetime import datetime

import requests

from app.core.config import get_settings
from app.observability.metrics import integration_calls_total
from app.observability.tracing import traced_span

logger = logging.getLogger(__name__)


class GoogleCalendarClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def _headers(self) -> dict[str, str] | None:
        if not self.settings.google_calendar_access_token:
            return None
        return {
            "Authorization": f"Bearer {self.settings.google_calendar_access_token}",
            "Content-Type": "application/json",
        }

    def get_availability(
        self,
        calendar_id: str,
        time_min: datetime,
        time_max: datetime,
    ) -> list[dict[str, str]]:
        with traced_span("integration.google_calendar.get_availability", {"provider": "google"}):
            headers = self._headers()
            if headers is None:
                logger.info("Google Calendar token not configured; returning no availability")
                integration_calls_total.labels(
                    provider="google_calendar",
                    operation="get_availability",
                    outcome="skipped",
                ).inc()
                return []

            url = f"{self.settings.google_calendar_api_base_url}/calendars/{calendar_id}/events"
            response = requests.get(
                url,
                params={"timeMin": time_min.isoformat(), "timeMax": time_max.isoformat()},
                headers=headers,
                timeout=10,
            )
            if response.status_code >= 300:
                integration_calls_total.labels(
                    provider="google_calendar",
                    operation="get_availability",
                    outcome="error",
                ).inc()
                return []

            events = response.json().get("items", [])
            integration_calls_total.labels(
                provider="google_calendar",
                operation="get_availability",
                outcome="success",
            ).inc()
            return [
                {
                    "start": item.get("start", {}).get("dateTime", ""),
                    "end": item.get("end", {}).get("dateTime", ""),
                }
                for item in events
            ]

    def create_booking(
        self,
        calendar_id: str,
        summary: str,
        start: datetime,
        end: datetime,
    ) -> bool:
        with traced_span("integration.google_calendar.create_booking", {"provider": "google"}):
            headers = self._headers()
            if headers is None:
                logger.info("Google Calendar token not configured; booking skipped")
                integration_calls_total.labels(
                    provider="google_calendar",
                    operation="create_booking",
                    outcome="skipped",
                ).inc()
                return False

            url = f"{self.settings.google_calendar_api_base_url}/calendars/{calendar_id}/events"
            payload = {
                "summary": summary,
                "start": {"dateTime": start.isoformat()},
                "end": {"dateTime": end.isoformat()},
            }
            response = requests.post(url, headers=headers, json=payload, timeout=10)
            ok = int(response.status_code) < 300
            integration_calls_total.labels(
                provider="google_calendar",
                operation="create_booking",
                outcome="success" if ok else "error",
            ).inc()
            return ok
