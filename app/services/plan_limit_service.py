from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.message import Message
from app.models.session import Session
from app.models.tenant import Tenant

_DEFAULT_LIMITS: dict[str, dict[str, int]] = {
    "starter": {"max_leads": 500, "max_sessions": 3000, "max_messages": 20000},
    "growth": {"max_leads": 5000, "max_sessions": 30000, "max_messages": 250000},
    "enterprise": {"max_leads": 1000000, "max_sessions": 1000000, "max_messages": 10000000},
}


class PlanLimitService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_plan_limits(self, tenant_id: str) -> dict[str, int]:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.db.execute(stmt)
        tenant = result.scalar_one_or_none()
        if tenant is None:
            return _DEFAULT_LIMITS["starter"]

        plan = tenant.plan if tenant.plan in _DEFAULT_LIMITS else "starter"
        limits = dict(_DEFAULT_LIMITS[plan])
        tenant_limits = (
            tenant.settings.get("plan_limits", {})
            if isinstance(tenant.settings, dict)
            else {}
        )
        if isinstance(tenant_limits, dict):
            for key in {"max_leads", "max_sessions", "max_messages"}:
                value = tenant_limits.get(key)
                if isinstance(value, int) and value > 0:
                    limits[key] = value
        return limits

    async def enforce_lead_creation_limit(self, tenant_id: str) -> None:
        limits = await self.get_plan_limits(tenant_id)
        count_stmt = select(func.count(Lead.id)).where(Lead.tenant_id == tenant_id)
        count_result = await self.db.execute(count_stmt)
        lead_count = int(count_result.scalar_one())
        if lead_count >= limits["max_leads"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="plan lead limit exceeded",
            )

    async def enforce_session_creation_limit(self, tenant_id: str) -> None:
        limits = await self.get_plan_limits(tenant_id)
        count_stmt = select(func.count(Session.id)).where(Session.tenant_id == tenant_id)
        count_result = await self.db.execute(count_stmt)
        session_count = int(count_result.scalar_one())
        if session_count >= limits["max_sessions"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="plan session limit exceeded",
            )

    async def enforce_message_creation_limit(self, tenant_id: str) -> None:
        limits = await self.get_plan_limits(tenant_id)
        count_stmt = select(func.count(Message.id)).where(Message.tenant_id == tenant_id)
        count_result = await self.db.execute(count_stmt)
        message_count = int(count_result.scalar_one())
        if message_count >= limits["max_messages"]:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="plan message limit exceeded",
            )
