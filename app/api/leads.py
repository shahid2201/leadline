from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AuthContext
from app.core.dependencies import get_auth_context
from app.db.session import get_db_session
from app.schemas.lead import (
    AttachSessionPayload,
    LeadCreate,
    LeadCreateResult,
    LeadResponse,
    LeadUpdate,
)
from app.schemas.timeline import TimelineEventCreate, TimelineEventResponse, TimelineEventUpdate
from app.services.conversation_service import ConversationService
from app.services.lead_service import LeadService

router = APIRouter(prefix="/leads", tags=["leads"])
timeline_router = APIRouter(prefix="/timeline", tags=["timeline"])


@router.post("", response_model=LeadCreateResult)
async def create_lead(
    payload: LeadCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> LeadCreateResult:
    service = LeadService(db)
    result = await service.create_lead(tenant_id=auth.tenant_id, payload=payload.model_dump())
    return LeadCreateResult(
        deduplicated=result.deduplicated,
        lead=LeadResponse.model_validate(result.lead),
    )


@router.get("", response_model=list[LeadResponse])
async def list_leads(
    status_filter: str | None = Query(default=None, alias="status"),
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[LeadResponse]:
    service = LeadService(db)
    leads = await service.list_leads(tenant_id=auth.tenant_id, status=status_filter)
    return [LeadResponse.model_validate(item) for item in leads]


@router.get("/{lead_id}", response_model=LeadResponse)
async def get_lead(
    lead_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> LeadResponse:
    service = LeadService(db)
    lead = await service.get_lead(tenant_id=auth.tenant_id, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="lead not found")
    return LeadResponse.model_validate(lead)


@router.patch("/{lead_id}", response_model=LeadResponse)
async def update_lead(
    lead_id: str,
    payload: LeadUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> LeadResponse:
    service = LeadService(db)
    lead = await service.update_lead(
        tenant_id=auth.tenant_id,
        lead_id=lead_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="lead not found")
    return LeadResponse.model_validate(lead)


@router.delete("/{lead_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lead(
    lead_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = LeadService(db)
    deleted = await service.delete_lead(tenant_id=auth.tenant_id, lead_id=lead_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="lead not found")


@router.post("/{lead_id}/timeline", response_model=TimelineEventResponse)
async def create_timeline_event(
    lead_id: str,
    payload: TimelineEventCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> TimelineEventResponse:
    service = LeadService(db)
    event = await service.create_timeline_event(
        tenant_id=auth.tenant_id,
        lead_id=lead_id,
        payload=payload.model_dump(),
    )
    if not event:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="lead not found")
    return TimelineEventResponse.model_validate(event)


@router.get("/{lead_id}/timeline", response_model=list[TimelineEventResponse])
async def list_timeline_events(
    lead_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[TimelineEventResponse]:
    service = LeadService(db)
    events = await service.list_timeline_events(tenant_id=auth.tenant_id, lead_id=lead_id)
    return [TimelineEventResponse.model_validate(item) for item in events]


@timeline_router.get("/{event_id}", response_model=TimelineEventResponse)
async def get_timeline_event(
    event_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> TimelineEventResponse:
    service = LeadService(db)
    event = await service.get_timeline_event(tenant_id=auth.tenant_id, event_id=event_id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="timeline event not found",
        )
    return TimelineEventResponse.model_validate(event)


@timeline_router.patch("/{event_id}", response_model=TimelineEventResponse)
async def update_timeline_event(
    event_id: str,
    payload: TimelineEventUpdate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> TimelineEventResponse:
    service = LeadService(db)
    event = await service.update_timeline_event(
        tenant_id=auth.tenant_id,
        event_id=event_id,
        payload=payload.model_dump(exclude_unset=True),
    )
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="timeline event not found",
        )
    return TimelineEventResponse.model_validate(event)


@timeline_router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_timeline_event(
    event_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> None:
    service = LeadService(db)
    deleted = await service.delete_timeline_event(tenant_id=auth.tenant_id, event_id=event_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="timeline event not found",
        )


@router.post("/{lead_id}/attach-session", response_model=dict[str, str])
async def attach_session(
    lead_id: str,
    payload: AttachSessionPayload,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, str]:
    service = ConversationService(db)
    record = await service.attach_session_to_lead(
        tenant_id=auth.tenant_id,
        lead_id=lead_id,
        session_id=payload.session_id,
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="lead or session not found",
        )
    return {"session_id": record.id, "lead_id": lead_id}
