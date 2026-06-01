from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sequence import Sequence, SequenceEnrollment, SequenceStep


class SequenceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tenant_id: str, data: dict[str, Any]) -> Sequence:
        record = Sequence(tenant_id=tenant_id, **data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get(self, tenant_id: str, sequence_id: str) -> Sequence | None:
        stmt = select(Sequence).where(Sequence.id == sequence_id, Sequence.tenant_id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_sequences(self, tenant_id: str) -> list[Sequence]:
        stmt = (
            select(Sequence)
            .where(Sequence.tenant_id == tenant_id)
            .order_by(Sequence.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_sequences_by_trigger(
        self,
        tenant_id: str,
        trigger: str,
    ) -> list[Sequence]:
        stmt = (
            select(Sequence)
            .where(
                Sequence.tenant_id == tenant_id,
                Sequence.trigger == trigger,
                Sequence.status == "active",
            )
            .order_by(Sequence.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, record: Sequence, data: dict[str, Any]) -> Sequence:
        for key, value in data.items():
            setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def delete(self, record: Sequence) -> None:
        await self.session.delete(record)
        await self.session.flush()


class SequenceStepRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, sequence_id: str, data: dict[str, Any]) -> SequenceStep:
        record = SequenceStep(sequence_id=sequence_id, **data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get(self, step_id: str) -> SequenceStep | None:
        stmt = select(SequenceStep).where(SequenceStep.id == step_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_sequence(self, sequence_id: str) -> list[SequenceStep]:
        stmt = (
            select(SequenceStep)
            .where(SequenceStep.sequence_id == sequence_id)
            .order_by(SequenceStep.order_index.asc(), SequenceStep.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, record: SequenceStep, data: dict[str, Any]) -> SequenceStep:
        for key, value in data.items():
            setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def delete(self, record: SequenceStep) -> None:
        await self.session.delete(record)
        await self.session.flush()


class SequenceEnrollmentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tenant_id: str, data: dict[str, Any]) -> SequenceEnrollment:
        record = SequenceEnrollment(tenant_id=tenant_id, **data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get(self, tenant_id: str, enrollment_id: str) -> SequenceEnrollment | None:
        stmt = select(SequenceEnrollment).where(
            SequenceEnrollment.id == enrollment_id,
            SequenceEnrollment.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_for_lead(self, tenant_id: str, lead_id: str) -> list[SequenceEnrollment]:
        stmt = (
            select(SequenceEnrollment)
            .where(SequenceEnrollment.tenant_id == tenant_id, SequenceEnrollment.lead_id == lead_id)
            .order_by(SequenceEnrollment.created_at.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, record: SequenceEnrollment, data: dict[str, Any]) -> SequenceEnrollment:
        for key, value in data.items():
            setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record
