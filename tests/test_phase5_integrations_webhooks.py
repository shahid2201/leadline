from datetime import UTC, datetime, timedelta

from conftest import auth_headers

from app.services.integration_service import IntegrationService
from app.services.webhook_service import WebhookService


def test_calendar_booking_endpoint(client, monkeypatch) -> None:  # noqa: ANN001
    headers = auth_headers("tenant-phase5")

    async def fake_create_booking(self, tenant_id, calendar_id, summary, start, end):  # noqa: ANN001
        return True

    monkeypatch.setattr(IntegrationService, "create_calendar_booking", fake_create_booking)

    now = datetime.now(UTC)
    response = client.post(
        "/v1/integrations/calendar/bookings",
        json={
            "calendar_id": "primary",
            "summary": "Demo call",
            "start": now.isoformat(),
            "end": (now + timedelta(minutes=30)).isoformat(),
        },
        headers=headers,
    )

    assert response.status_code == 200
    assert response.json() == {"booked": True}


def test_svix_webhook_idempotency(client, monkeypatch) -> None:  # noqa: ANN001
    def fake_verify(self, payload, headers):  # noqa: ANN001
        return True

    monkeypatch.setattr(WebhookService, "verify_svix_signature", fake_verify)

    payload = {"tenant_id": "tenant-webhooks", "type": "lead.updated", "data": {"id": "lead-1"}}
    headers = {
        "svix-id": "msg_1",
        "svix-timestamp": "1700000000",
        "svix-signature": "v1,fakesig",
    }

    first = client.post("/v1/webhooks/svix", json=payload, headers=headers)
    assert first.status_code == 200
    assert first.json() == {"status": "processed"}

    second = client.post("/v1/webhooks/svix", json=payload, headers=headers)
    assert second.status_code == 200
    assert second.json() == {"status": "processed"}
