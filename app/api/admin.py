from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.context import AuthContext
from app.core.dependencies import require_admin
from app.db.session import get_db_session
from app.models.failed_job import FailedJob
from app.queue.sqs import QueueJob, SQSPublisher
from app.repositories.tenant_repository import TenantRepository
from app.schemas.admin import (
    DesignPartnerEnrollmentRequest,
    DesignPartnerEnrollmentResponse,
    DLQListResponse,
    DLQReplayResponse,
    FailedJobResponse,
    PlanLimitSnapshotResponse,
    ProvisionTenantRequest,
    ProvisionTenantResponse,
    RolloutPromotionRequest,
    RolloutPromotionResponse,
    UsageSummaryResponse,
)
from app.services.plan_limit_service import PlanLimitService
from app.services.provisioning_service import ProvisioningService
from app.services.usage_tracking_service import UsageTrackingService

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


@router.get("/tenants/{tenant_id}/usage", response_model=UsageSummaryResponse)
async def get_tenant_usage(
    tenant_id: str,
    days: int = Query(default=30, ge=1, le=365),
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> UsageSummaryResponse:
    _ = auth
    repo = TenantRepository(db)
    tenant = await repo.get(tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="tenant not found")
    usage_service = UsageTrackingService(db)
    records = await usage_service.get_summary(tenant_id=tenant_id, days=days)
    return UsageSummaryResponse(
        tenant_id=tenant_id,
        days=days,
        records=records,  # type: ignore[arg-type]
    )


@router.get("/dlq", response_model=DLQListResponse)
async def list_dlq_jobs(
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
    queue_name: str | None = Query(default=None),
) -> DLQListResponse:
    _ = auth
    stmt = select(FailedJob).where(FailedJob.status == "pending")
    if queue_name:
        stmt = stmt.where(FailedJob.queue_name == queue_name)
    stmt = stmt.order_by(FailedJob.created_at.desc()).limit(100)
    result = await db.execute(stmt)
    jobs = list(result.scalars().all())
    job_responses = [
        FailedJobResponse(
            id=j.id,
            queue_name=j.queue_name,
            event_type=j.event_type,
            error=j.error,
            attempts=j.attempts,
            status=j.status,
            tenant_id=j.tenant_id,
            created_at=j.created_at.isoformat(),
        )
        for j in jobs
    ]
    return DLQListResponse(total=len(job_responses), jobs=job_responses)


@router.post("/dlq/{job_id}/replay", response_model=DLQReplayResponse)
async def replay_dlq_job(
    job_id: str,
    auth: AuthContext = Depends(require_admin),
    db: AsyncSession = Depends(get_db_session),
) -> DLQReplayResponse:
    _ = auth
    stmt = select(FailedJob).where(FailedJob.id == job_id)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="job not found")

    publisher = SQSPublisher()
    publisher.publish(
        QueueJob(queue_name=job.queue_name, payload=job.payload)
    )

    job.status = "replayed"
    job.replayed_at = datetime.now(UTC)
    await db.commit()
    return DLQReplayResponse(job_id=job_id, replayed=True)

