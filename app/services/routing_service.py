from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lead import Lead
from app.models.lead_timeline_event import LeadTimelineEvent
from app.models.routing_rule import RoutingRule
from app.repositories.lead_repository import LeadRepository
from app.repositories.routing_repository import RoutingRuleRepository
from app.routing.engine import RoutingDecision, apply_routing_decision, evaluate_routing


class RoutingService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.rules = RoutingRuleRepository(db)
        self.leads = LeadRepository(db)

    async def create_rule(self, tenant_id: str, payload: dict[str, Any]) -> RoutingRule:
        record = await self.rules.create(tenant_id=tenant_id, data=payload)
        await self.db.commit()
        return record

    async def list_rules(self, tenant_id: str) -> list[RoutingRule]:
        return await self.rules.list_rules(tenant_id=tenant_id)

    async def get_rule(self, tenant_id: str, rule_id: str) -> RoutingRule | None:
        return await self.rules.get(tenant_id=tenant_id, rule_id=rule_id)

    async def update_rule(
        self,
        tenant_id: str,
        rule_id: str,
        payload: dict[str, Any],
    ) -> RoutingRule | None:
        record = await self.rules.get(tenant_id=tenant_id, rule_id=rule_id)
        if not record:
            return None
        updated = await self.rules.update(record, payload)
        await self.db.commit()
        return updated

    async def delete_rule(self, tenant_id: str, rule_id: str) -> bool:
        record = await self.rules.get(tenant_id=tenant_id, rule_id=rule_id)
        if not record:
            return False
        await self.rules.delete(record)
        await self.db.commit()
        return True

    async def evaluate_and_apply(
        self,
        tenant_id: str,
        lead_id: str,
    ) -> tuple[Lead | None, RoutingDecision]:
        lead = await self.leads.get(tenant_id=tenant_id, lead_id=lead_id)
        if not lead:
            return None, RoutingDecision(None, None, {})

        enabled_rules = await self.rules.list_enabled_rules(tenant_id=tenant_id)
        decision = evaluate_routing(lead=lead, rules=enabled_rules)
        apply_routing_decision(lead=lead, decision=decision)

        self.db.add(
            LeadTimelineEvent(
                tenant_id=tenant_id,
                lead_id=lead.id,
                type="routing_evaluated",
                payload={
                    "matched_rule_id": decision.matched_rule_id,
                    "action": decision.action,
                    "action_payload": decision.action_payload,
                },
            )
        )
        await self.db.commit()
        await self.db.refresh(lead)
        return lead, decision
