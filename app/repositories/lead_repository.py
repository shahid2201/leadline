from typing import Any

from sqlalchemy import Select, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.lead_timeline_event import LeadTimelineEvent


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tenant_id: str, data: dict[str, Any]) -> Lead:
        lead = Lead(tenant_id=tenant_id, **data)
        self.session.add(lead)
        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def get(self, tenant_id: str, lead_id: str) -> Lead | None:
        stmt = select(Lead).where(Lead.id == lead_id, Lead.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(self, tenant_id: str, status: str | None = None) -> list[Lead]:
        stmt: Select[tuple[Lead]] = select(Lead).where(Lead.tenant_id == tenant_id)
        if status:
            stmt = stmt.where(Lead.status == status)
        stmt = stmt.order_by(Lead.created_at.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, lead: Lead, data: dict[str, Any]) -> Lead:
        for key, value in data.items():
            setattr(lead, key, value)
        await self.session.flush()
        await self.session.refresh(lead)
        return lead

    async def delete(self, lead: Lead) -> None:
        await self.session.delete(lead)
        await self.session.flush()

    async def find_duplicate_by_email_or_phone(
        self,
        tenant_id: str,
        email: str | None,
        phone: str | None,
    ) -> Lead | None:
        filters = []
        if email:
            filters.append(Lead.email == email)
        if phone:
            filters.append(Lead.phone == phone)
        if not filters:
            return None

        stmt = select(Lead).where(Lead.tenant_id == tenant_id, or_(*filters))
        result = await self.session.execute(stmt)
        return result.scalars().first()


class LeadTimelineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tenant_id: str, lead_id: str, data: dict[str, Any]) -> LeadTimelineEvent:
        event = LeadTimelineEvent(tenant_id=tenant_id, lead_id=lead_id, **data)
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def get(self, tenant_id: str, event_id: str) -> LeadTimelineEvent | None:
        stmt = select(LeadTimelineEvent).where(
            LeadTimelineEvent.id == event_id,
            LeadTimelineEvent.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_lead(self, tenant_id: str, lead_id: str) -> list[LeadTimelineEvent]:
        stmt = (
            select(LeadTimelineEvent)
            .where(LeadTimelineEvent.tenant_id == tenant_id, LeadTimelineEvent.lead_id == lead_id)
            .order_by(LeadTimelineEvent.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, event: LeadTimelineEvent, data: dict[str, Any]) -> LeadTimelineEvent:
        for key, value in data.items():
            setattr(event, key, value)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def delete(self, event: LeadTimelineEvent) -> None:
        await self.session.delete(event)
        await self.session.flush()
