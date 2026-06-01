from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AuthContext
from app.core.dependencies import get_auth_context
from app.db.session import get_db_session
from app.queue.sqs import QueueJob, SQSPublisher
from app.schemas.sequence import (
    SequenceCreate,
    SequenceEnrollmentResponse,
    SequenceEnrollRequest,
    SequenceResponse,
    SequenceStepCreate,
    SequenceStepResponse,
    SequenceStepUpdate,
    SequenceUpdate,
)
from app.services.sequence_service import SequenceService

router = APIRouter(prefix="/sequences", tags=["sequences"])


@router.post("", response_model=SequenceResponse)
async def create_sequence(
    payload: SequenceCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SequenceResponse:
    service = SequenceService(db)
    sequence = await service.create_sequence(tenant_id=auth.tenant_id, payload=payload.model_dump())
    return SequenceResponse.model_validate(sequence)


@router.get("", response_model=list[SequenceResponse])
async def list_sequences(
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[SequenceResponse]:
    service = SequenceService(db)
    records = await service.list_sequences(tenant_id=auth.tenant_id)
    return [SequenceResponse.model_validate(item) for item in records]


@router.get("/{sequence_id}", response_model=SequenceResponse)
async def get_sequence(
    sequence_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SequenceResponse:
    service = SequenceService(db)
    sequence = await service.get_sequence(tenant_id=auth.tenant_id, sequence_id=sequence_id)
    if not sequence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sequence not found")
    return SequenceResponse.model_validate(sequence)


@router.patch("/{sequence_id}", response_model=SequenceResponse)
async def update_sequence(
    sequence_id: str,
    payload: SequenceUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SequenceResponse:
    service = SequenceService(db)
    sequence = await service.update_sequence(
        tenant_id=auth.tenant_id,
        sequence_id=sequence_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    if not sequence:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sequence not found")
    return SequenceResponse.model_validate(sequence)


@router.delete("/{sequence_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sequence(
    sequence_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = SequenceService(db)
    deleted = await service.delete_sequence(tenant_id=auth.tenant_id, sequence_id=sequence_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sequence not found")


@router.post("/{sequence_id}/steps", response_model=SequenceStepResponse)
async def create_step(
    sequence_id: str,
    payload: SequenceStepCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SequenceStepResponse:
    service = SequenceService(db)
    step = await service.create_step(
        tenant_id=auth.tenant_id,
        sequence_id=sequence_id,
        payload=payload.model_dump(),
    )
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="sequence not found")
    return SequenceStepResponse.model_validate(step)


@router.get("/{sequence_id}/steps", response_model=list[SequenceStepResponse])
async def list_steps(
    sequence_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[SequenceStepResponse]:
    service = SequenceService(db)
    steps = await service.list_steps(tenant_id=auth.tenant_id, sequence_id=sequence_id)
    return [SequenceStepResponse.model_validate(item) for item in steps]


@router.patch("/{sequence_id}/steps/{step_id}", response_model=SequenceStepResponse)
async def update_step(
    sequence_id: str,
    step_id: str,
    payload: SequenceStepUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SequenceStepResponse:
    service = SequenceService(db)
    step = await service.update_step(
        tenant_id=auth.tenant_id,
        sequence_id=sequence_id,
        step_id=step_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    if not step:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="step not found")
    return SequenceStepResponse.model_validate(step)


@router.delete("/{sequence_id}/steps/{step_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_step(
    sequence_id: str,
    step_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = SequenceService(db)
    deleted = await service.delete_step(
        tenant_id=auth.tenant_id,
        sequence_id=sequence_id,
        step_id=step_id,
    )
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="step not found")


@router.post("/{sequence_id}/enroll", response_model=SequenceEnrollmentResponse)
async def enroll_lead(
    sequence_id: str,
    payload: SequenceEnrollRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> SequenceEnrollmentResponse:
    service = SequenceService(db)
    enrollment = await service.enroll(
        tenant_id=auth.tenant_id,
        sequence_id=sequence_id,
        lead_id=payload.lead_id,
    )
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="lead or sequence not found",
        )

    SQSPublisher().publish(
        QueueJob(
            queue_name="sequence_jobs",
            payload={
                "event": "sequence.step.execute",
                "tenant_id": auth.tenant_id,
                "enrollment_id": enrollment.id,
            },
        )
    )
    return SequenceEnrollmentResponse.model_validate(enrollment)
