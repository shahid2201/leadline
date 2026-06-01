import asyncio

import pytest

from app.db.session import AsyncSessionLocal
from app.services.plan_limit_service import PlanLimitService


@pytest.mark.unit
def test_plan_limit_defaults_unknown_tenant() -> None:
    async def _run() -> None:
        async with AsyncSessionLocal() as db:
            service = PlanLimitService(db)
            limits = await service.get_plan_limits("missing-tenant")
            assert limits["max_leads"] == 500
            assert limits["max_sessions"] == 3000
            assert limits["max_messages"] == 20000

    asyncio.run(_run())
