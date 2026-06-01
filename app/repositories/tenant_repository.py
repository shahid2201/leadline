from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant


class TenantRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        name: str,
        slug: str,
        plan: str,
        settings: dict[str, object],
    ) -> Tenant:
        record = Tenant(name=name, slug=slug, plan=plan, settings=settings)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get(self, tenant_id: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.id == tenant_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Tenant | None:
        stmt = select(Tenant).where(Tenant.slug == slug)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def update(self, tenant: Tenant, data: dict[str, object]) -> Tenant:
        for key, value in data.items():
            setattr(tenant, key, value)
        await self.session.flush()
        await self.session.refresh(tenant)
        return tenant
