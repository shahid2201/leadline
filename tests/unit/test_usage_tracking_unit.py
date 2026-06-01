import asyncio

import pytest

from app.db.session import AsyncSessionLocal
from app.services.usage_tracking_service import UsageTrackingService


@pytest.mark.unit
def test_usage_tracking_increment_and_read() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            service = UsageTrackingService(db)
            tenant_id = "test-usage-tenant"

            await service.increment(
                tenant_id,
                ai_tokens_used=150,
                messages_sent=1,
                leads_created=1,
            )
            await db.commit()

            records = await service.get_summary(tenant_id, days=1)
            assert len(records) == 1
            rec = records[0]
            assert rec.ai_tokens_used == 150
            assert rec.messages_sent == 1
            assert rec.leads_created == 1
            assert rec.emails_sent == 0
            assert rec.sms_sent == 0

    asyncio.run(_run())


@pytest.mark.unit
def test_usage_tracking_accumulates_same_day() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            service = UsageTrackingService(db)
            tenant_id = "test-usage-accum"

            await service.increment(tenant_id, ai_tokens_used=100)
            await service.increment(tenant_id, ai_tokens_used=50, emails_sent=1)
            await db.commit()

            records = await service.get_summary(tenant_id, days=1)
            assert len(records) == 1
            rec = records[0]
            assert rec.ai_tokens_used == 150
            assert rec.emails_sent == 1

    asyncio.run(_run())
