from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AuthContext
from app.core.dependencies import require_admin
from app.db.session import get_db_session
from app.repositories.tenant_repository import TenantRepository
from app.schemas.admin import (
    DesignPartnerEnrollmentRequest,
    DesignPartnerEnrollmentResponse,
    PlanLimitSnapshotResponse,
    ProvisionTenantRequest,
    ProvisionTenantResponse,
    RolloutPromotionRequest,
    RolloutPromotionResponse,
)
from app.services.plan_limit_service import PlanLimitService
from app.services.provisioning_service import ProvisioningService

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.post("/provision", response_model=ProvisionTenantResponse)
async def provision_tenant(
    payload: ProvisionTenantRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> ProvisionTenantResponse:
    _ = auth
    service = ProvisioningService(TenantRepository(db))
    try:
        tenant_id, user_id, api_key, plan = await service.provision_tenant(
            name=payload.name,
            slug=payload.slug,
            owner_email=payload.owner_email,
            plan=payload.plan,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return ProvisionTenantResponse(tenant_id=tenant_id, user_id=user_id, api_key=api_key, plan=plan)


@router.get("/tenants/{tenant_id}/plan-limits", response_model=PlanLimitSnapshotResponse)
async def get_plan_limits(
    tenant_id: str,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> PlanLimitSnapshotResponse:
    _ = auth
    service = PlanLimitService(db)
    limits = await service.get_plan_limits(tenant_id)
    repo = TenantRepository(db)
    tenant = await repo.get(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
    return PlanLimitSnapshotResponse(plan=tenant.plan, limits=limits)


@router.post(
    "/design-partners/{tenant_id}/enroll",
    response_model=DesignPartnerEnrollmentResponse,
)
async def enroll_design_partner(
    tenant_id: str,
    payload: DesignPartnerEnrollmentRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> DesignPartnerEnrollmentResponse:
    _ = auth
    service = ProvisioningService(TenantRepository(db))
    try:
        enrolled, cohort = await service.enroll_design_partner(
            tenant_id=tenant_id,
            cohort=payload.cohort,
            launch_notes=payload.launch_notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return DesignPartnerEnrollmentResponse(tenant_id=tenant_id, enrolled=enrolled, cohort=cohort)


@router.post(
    "/design-partners/{tenant_id}/promote",
    response_model=RolloutPromotionResponse,
)
async def promote_rollout(
    tenant_id: str,
    payload: RolloutPromotionRequest,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> RolloutPromotionResponse:
    _ = auth
    service = ProvisioningService(TenantRepository(db))
    try:
        rollout_percentage = await service.promote_rollout(
            tenant_id=tenant_id,
            rollout_percentage=payload.rollout_percentage,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return RolloutPromotionResponse(tenant_id=tenant_id, rollout_percentage=rollout_percentage)
