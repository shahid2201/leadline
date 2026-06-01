from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sequence import Sequence, SequenceEnrollment, SequenceStep
from app.repositories.lead_repository import LeadRepository
from app.repositories.sequence_repository import (
    SequenceEnrollmentRepository,
    SequenceRepository,
    SequenceStepRepository,
)


class SequenceService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.sequences = SequenceRepository(db)
        self.steps = SequenceStepRepository(db)
        self.enrollments = SequenceEnrollmentRepository(db)
        self.leads = LeadRepository(db)

    async def create_sequence(self, tenant_id: str, payload: dict[str, Any]) -> Sequence:
        record = await self.sequences.create(tenant_id=tenant_id, data=payload)
        await self.db.commit()
        return record

    async def list_sequences(self, tenant_id: str) -> list[Sequence]:
        return await self.sequences.list_sequences(tenant_id=tenant_id)

    async def get_sequence(self, tenant_id: str, sequence_id: str) -> Sequence | None:
        return await self.sequences.get(tenant_id=tenant_id, sequence_id=sequence_id)

    async def update_sequence(
        self,
        tenant_id: str,
        sequence_id: str,
        payload: dict[str, Any],
    ) -> Sequence | None:
        record = await self.sequences.get(tenant_id=tenant_id, sequence_id=sequence_id)
        if not record:
            return None
        updated = await self.sequences.update(record, payload)
        await self.db.commit()
        return updated

    async def delete_sequence(self, tenant_id: str, sequence_id: str) -> bool:
        record = await self.sequences.get(tenant_id=tenant_id, sequence_id=sequence_id)
        if not record:
            return False
        await self.sequences.delete(record)
        await self.db.commit()
        return True

    async def create_step(
        self,
        tenant_id: str,
        sequence_id: str,
        payload: dict[str, Any],
    ) -> SequenceStep | None:
        sequence = await self.sequences.get(tenant_id=tenant_id, sequence_id=sequence_id)
        if not sequence:
            return None
        record = await self.steps.create(sequence_id=sequence_id, data=payload)
        await self.db.commit()
        return record

    async def list_steps(self, tenant_id: str, sequence_id: str) -> list[SequenceStep]:
        sequence = await self.sequences.get(tenant_id=tenant_id, sequence_id=sequence_id)
        if not sequence:
            return []
        return await self.steps.list_for_sequence(sequence_id=sequence_id)

    async def update_step(
        self,
        tenant_id: str,
        sequence_id: str,
        step_id: str,
        payload: dict[str, Any],
    ) -> SequenceStep | None:
        sequence = await self.sequences.get(tenant_id=tenant_id, sequence_id=sequence_id)
        if not sequence:
            return None
        step = await self.steps.get(step_id=step_id)
        if not step or step.sequence_id != sequence_id:
            return None
        updated = await self.steps.update(step, payload)
        await self.db.commit()
        return updated

    async def delete_step(self, tenant_id: str, sequence_id: str, step_id: str) -> bool:
        sequence = await self.sequences.get(tenant_id=tenant_id, sequence_id=sequence_id)
        if not sequence:
            return False
        step = await self.steps.get(step_id=step_id)
        if not step or step.sequence_id != sequence_id:
            return False
        await self.steps.delete(step)
        await self.db.commit()
        return True

    async def enroll(
        self,
        tenant_id: str,
        sequence_id: str,
        lead_id: str,
    ) -> SequenceEnrollment | None:
        sequence = await self.sequences.get(tenant_id=tenant_id, sequence_id=sequence_id)
        if not sequence:
            return None
        lead = await self.leads.get(tenant_id=tenant_id, lead_id=lead_id)
        if not lead:
            return None
        enrollment = await self.enrollments.create(
            tenant_id=tenant_id,
            data={
                "lead_id": lead_id,
                "sequence_id": sequence_id,
                "status": "active",
                "current_step_index": 0,
            },
        )
        await self.db.commit()
        return enrollment
