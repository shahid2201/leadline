from typing import Any

from fastapi import HTTPException
from svix.webhooks import Webhook, WebhookVerificationError

from app.core.config import get_settings
from app.repositories.integration_repository import WebhookEventRepository


class WebhookService:
    def __init__(self, repository: WebhookEventRepository) -> None:
        self.repository = repository
        self.settings = get_settings()

    def verify_svix_signature(self, payload: bytes, headers: dict[str, str]) -> bool:
        if not self.settings.svix_webhook_secret:
            raise HTTPException(status_code=500, detail="SVIX_WEBHOOK_SECRET is not configured")

        verifier = Webhook(self.settings.svix_webhook_secret)
        try:
            verifier.verify(payload.decode("utf-8"), headers)
            return True
        except WebhookVerificationError as exc:
            raise HTTPException(status_code=401, detail="Invalid webhook signature") from exc

    async def ensure_idempotent(
        self,
        tenant_id: str,
        provider: str,
        source_event_id: str,
        event_type: str,
        payload: dict[str, Any],
        signature_valid: bool,
    ) -> tuple[bool, str]:
        existing = await self.repository.get_by_source(
            tenant_id=tenant_id,
            provider=provider,
            source_event_id=source_event_id,
        )
        if existing:
            return False, existing.status

        await self.repository.create(
            {
                "tenant_id": tenant_id,
                "provider": provider,
                "source_event_id": source_event_id,
                "event_type": event_type,
                "payload": payload,
                "signature_valid": signature_valid,
                "status": "received",
                "attempts": 0,
            }
        )
        return True, "received"

    async def mark_processed(self, tenant_id: str, provider: str, source_event_id: str) -> None:
        record = await self.repository.get_by_source(
            tenant_id=tenant_id,
            provider=provider,
            source_event_id=source_event_id,
        )
        if record is None:
            return
        await self.repository.update(
            record,
            {"status": "processed", "attempts": record.attempts + 1},
        )

    async def mark_failed(
        self,
        tenant_id: str,
        provider: str,
        source_event_id: str,
        error: str,
    ) -> None:
        record = await self.repository.get_by_source(
            tenant_id=tenant_id,
            provider=provider,
            source_event_id=source_event_id,
        )
        if record is None:
            return

        next_attempts = record.attempts + 1
        status = "failed"
        if next_attempts < self.settings.integration_max_retries:
            status = "retry"

        await self.repository.update(
            record,
            {
                "status": status,
                "attempts": next_attempts,
                "last_error": error[:2000],
            },
        )
