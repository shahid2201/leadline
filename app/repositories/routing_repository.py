from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.routing_rule import RoutingRule


class RoutingRuleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, tenant_id: str, data: dict[str, Any]) -> RoutingRule:
        record = RoutingRule(tenant_id=tenant_id, **data)
        self.session.add(record)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def get(self, tenant_id: str, rule_id: str) -> RoutingRule | None:
        stmt = select(RoutingRule).where(
            RoutingRule.id == rule_id,
            RoutingRule.tenant_id == tenant_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_rules(self, tenant_id: str) -> list[RoutingRule]:
        stmt = (
            select(RoutingRule)
            .where(RoutingRule.tenant_id == tenant_id)
            .order_by(RoutingRule.priority.desc(), RoutingRule.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_enabled_rules(self, tenant_id: str) -> list[RoutingRule]:
        stmt = (
            select(RoutingRule)
            .where(RoutingRule.tenant_id == tenant_id, RoutingRule.enabled.is_(True))
            .order_by(RoutingRule.priority.desc(), RoutingRule.id.asc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, record: RoutingRule, data: dict[str, Any]) -> RoutingRule:
        for key, value in data.items():
            setattr(record, key, value)
        await self.session.flush()
        await self.session.refresh(record)
        return record

    async def delete(self, record: RoutingRule) -> None:
        await self.session.delete(record)
        await self.session.flush()
