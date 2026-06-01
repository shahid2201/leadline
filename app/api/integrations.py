from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AuthContext
from app.core.dependencies import get_auth_context, require_admin
from app.db.session import get_db_session
from app.repositories.integration_repository import IntegrationConnectionRepository
from app.schemas.integration import (
    CalendarAvailabilityResponse,
    CalendarBookingCreate,
    CalendarBookingResult,
)
from app.services.integration_service import IntegrationService
from app.services.lead_service import LeadService

router = APIRouter(
    prefix="/integrations",
    tags=["integrations"],
    dependencies=[Depends(require_admin)],
)


@router.post("/hubspot/leads/{lead_id}/sync", response_model=dict[str, bool])
async def sync_hubspot_lead(
    lead_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, bool]:
    lead_service = LeadService(db)
    lead = await lead_service.get_lead(tenant_id=auth.tenant_id, lead_id=lead_id)
    if not lead:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="lead not found")

    integration_service = IntegrationService(IntegrationConnectionRepository(db))
    synced = await integration_service.sync_hubspot_lead(
        tenant_id=auth.tenant_id,
        lead_payload={
            "id": lead.id,
            "name": lead.name,
            "email": lead.email,
            "phone": lead.phone,
            "company": lead.company,
            "status": lead.status,
            "lead_score": lead.lead_score,
        },
    )
    await db.commit()
    return {"synced": synced}


@router.get("/calendar/availability", response_model=list[CalendarAvailabilityResponse])
async def get_calendar_availability(
    calendar_id: str = Query(...),
    time_min: datetime = Query(...),
    time_max: datetime = Query(...),
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> list[CalendarAvailabilityResponse]:
    integration_service = IntegrationService(IntegrationConnectionRepository(db))
    slots = await integration_service.get_calendar_availability(
        calendar_id=calendar_id,
        time_min=time_min,
        time_max=time_max,
    )
    return [CalendarAvailabilityResponse.model_validate(slot) for slot in slots]


@router.post("/calendar/bookings", response_model=CalendarBookingResult)
async def create_calendar_booking(
    payload: CalendarBookingCreate,
    auth: AuthContext = Depends(get_auth_context),
    db: AsyncSession = Depends(get_db_session),
) -> CalendarBookingResult:
    integration_service = IntegrationService(IntegrationConnectionRepository(db))
    booked = await integration_service.create_calendar_booking(
        tenant_id=auth.tenant_id,
        calendar_id=payload.calendar_id,
        summary=payload.summary,
        start=payload.start,
        end=payload.end,
    )
    await db.commit()
    return CalendarBookingResult(booked=booked)
