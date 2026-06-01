import hashlib
import hmac
from typing import Any, cast

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.session import get_db_session
from app.repositories.integration_repository import WebhookEventRepository
from app.services.webhook_service import WebhookService

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


@router.post("/svix", response_model=dict[str, str])
async def receive_svix_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    payload_bytes = await request.body()
    payload = await request.json()

    svix_id = request.headers.get("svix-id")
    svix_timestamp = request.headers.get("svix-timestamp")
    svix_signature = request.headers.get("svix-signature")
    if not svix_id or not svix_timestamp or not svix_signature:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="missing svix headers")

    service = WebhookService(WebhookEventRepository(db))
    signature_valid = service.verify_svix_signature(
        payload=payload_bytes,
        headers={
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        },
    )

    tenant_id = str(payload.get("tenant_id", "global"))
    event_type = str(payload.get("type", "unknown"))
    is_new, current_status = await service.ensure_idempotent(
        tenant_id=tenant_id,
        provider="svix",
        source_event_id=svix_id,
        event_type=event_type,
        payload=payload,
        signature_valid=signature_valid,
    )

    if not is_new:
        return {"status": current_status}

    try:
        await service.mark_processed(tenant_id=tenant_id, provider="svix", source_event_id=svix_id)
        await db.commit()
        return {"status": "processed"}
    except Exception as exc:  # noqa: BLE001
        await service.mark_failed(
            tenant_id=tenant_id,
            provider="svix",
            source_event_id=svix_id,
            error=str(exc),
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="failed",
        ) from exc


def _verify_hubspot_signature(payload: bytes, signature: str, secret: str) -> bool:
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


@router.post("/hubspot", response_model=dict[str, str])
async def receive_hubspot_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    settings = get_settings()
    if not settings.hubspot_webhook_secret:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="HUBSPOT_WEBHOOK_SECRET is not configured",
        )

    payload_bytes = await request.body()
    payload_json = await request.json()
    signature = request.headers.get("x-hubspot-signature")
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="missing hubspot signature",
        )

    if not _verify_hubspot_signature(payload_bytes, signature, settings.hubspot_webhook_secret):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid signature")

    events = payload_json if isinstance(payload_json, list) else [payload_json]
    service = WebhookService(WebhookEventRepository(db))

    for item in events:
        if not isinstance(item, dict):
            continue
        tenant_id = str(item.get("tenantId", "global"))
        source_event_id = str(item.get("eventId", item.get("id", "unknown")))
        event_type = str(item.get("subscriptionType", "unknown"))

        is_new, _ = await service.ensure_idempotent(
            tenant_id=tenant_id,
            provider="hubspot",
            source_event_id=source_event_id,
            event_type=event_type,
            payload=cast(dict[str, Any], item),
            signature_valid=True,
        )
        if is_new:
            await service.mark_processed(
                tenant_id=tenant_id,
                provider="hubspot",
                source_event_id=source_event_id,
            )

    await db.commit()
    return {"status": "processed"}
