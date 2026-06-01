from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.usage_record import UsageRecord


class UsageTrackingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def increment(
        self,
        tenant_id: str,
        *,
        ai_tokens_used: int = 0,
        messages_sent: int = 0,
        emails_sent: int = 0,
        sms_sent: int = 0,
        leads_created: int = 0,
        sessions_created: int = 0,
    ) -> None:
        today = datetime.now(UTC).date()
        stmt = select(UsageRecord).where(
            UsageRecord.tenant_id == tenant_id,
            UsageRecord.record_date == today,
        )
        result = await self.db.execute(stmt)
        record = result.scalar_one_or_none()

        if record is None:
            record = UsageRecord(
                tenant_id=tenant_id,
                record_date=today,
                ai_tokens_used=0,
                messages_sent=0,
                emails_sent=0,
                sms_sent=0,
                leads_created=0,
                sessions_created=0,
            )
            self.db.add(record)
            await self.db.flush()

        record.ai_tokens_used += ai_tokens_used
        record.messages_sent += messages_sent
        record.emails_sent += emails_sent
        record.sms_sent += sms_sent
        record.leads_created += leads_created
        record.sessions_created += sessions_created

    async def get_summary(self, tenant_id: str, days: int = 30) -> list[UsageRecord]:
        cutoff: date = (datetime.now(UTC) - timedelta(days=days)).date()
        stmt = (
            select(UsageRecord)
            .where(
                UsageRecord.tenant_id == tenant_id,
                UsageRecord.record_date >= cutoff,
            )
            .order_by(UsageRecord.record_date.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
