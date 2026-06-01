from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.integration_connection import IntegrationConnection, WebhookEvent


class IntegrationConnectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(
        self,
        tenant_id: str,
        integration_type: str,
        data: dict[str, Any],
    ) -> IntegrationConnection:
        existing = await self.get_by_type(tenant_id=tenant_id, integration_type=integration_type)
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            await self.session.flush()
            await self.session.refresh(existing)
            return existing

        record = IntegrationConnection(tenant_id=tenant_id, type=integration_type, **data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get_by_type(
        self,
        tenant_id: str,
        integration_type: str,
    ) -> IntegrationConnection | None:
        stmt = select(IntegrationConnection).where(
            IntegrationConnection.tenant_id == tenant_id,
            IntegrationConnection.type == integration_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def mark_synced(self, record: IntegrationConnection) -> None:
        record.last_sync_at = datetime.utcnow()
        await self.session.flush()


class WebhookEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_source(
        self,
        tenant_id: str,
        provider: str,
        source_event_id: str,
    ) -> WebhookEvent | None:
        stmt = select(WebhookEvent).where(
            WebhookEvent.tenant_id == tenant_id,
            WebhookEvent.provider == provider,
            WebhookEvent.source_event_id == source_event_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, payload: dict[str, Any]) -> WebhookEvent:
        record = WebhookEvent(**payload)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def update(self, record: WebhookEvent, data: dict[str, Any]) -> WebhookEvent:
        for key, value in data.items():
            setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record
