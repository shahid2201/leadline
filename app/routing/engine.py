from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.models.lead import Lead
from app.models.routing_rule import RoutingRule


@dataclass
class RoutingDecision:
    matched_rule_id: str | None
    action: str | None
    action_payload: dict[str, Any]


def _to_float(value: Any) -> float | None:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _gt(lhs: Any, rhs: Any) -> bool:
    left = _to_float(lhs)
    right = _to_float(rhs)
    return left is not None and right is not None and left > right


def _gte(lhs: Any, rhs: Any) -> bool:
    left = _to_float(lhs)
    right = _to_float(rhs)
    return left is not None and right is not None and left >= right


def _lt(lhs: Any, rhs: Any) -> bool:
    left = _to_float(lhs)
    right = _to_float(rhs)
    return left is not None and right is not None and left < right


def _lte(lhs: Any, rhs: Any) -> bool:
    left = _to_float(lhs)
    right = _to_float(rhs)
    return left is not None and right is not None and left <= right


def _operators() -> dict[str, Callable[[Any, Any], bool]]:
    return {
        "eq": lambda lhs, rhs: lhs == rhs,
        "neq": lambda lhs, rhs: lhs != rhs,
        "contains": lambda lhs, rhs: str(rhs).lower() in str(lhs).lower(),
        "gt": _gt,
        "gte": _gte,
        "lt": _lt,
        "lte": _lte,
        "in": lambda lhs, rhs: lhs in rhs if isinstance(rhs, list) else False,
    }


def _lead_value(lead: Lead, field: str) -> Any:
    if hasattr(lead, field):
        return getattr(lead, field)
    if field.startswith("custom_fields."):
        key = field.split("custom_fields.", 1)[1]
        return (lead.custom_fields or {}).get(key)
    return None


def rule_matches(lead: Lead, rule: RoutingRule) -> bool:
    op_map = _operators()
    conditions = rule.conditions or []
    for condition in conditions:
        field = str(condition.get("field", "")).strip()
        op = str(condition.get("op", "eq")).strip()
        expected = condition.get("value")

        comparator = op_map.get(op)
        if not comparator:
            return False

        actual = _lead_value(lead, field)
        if not comparator(actual, expected):
            return False

    return True


def evaluate_routing(lead: Lead, rules: list[RoutingRule]) -> RoutingDecision:
    # Deterministic order: highest priority first, then stable id ordering.
    ordered = sorted(rules, key=lambda item: (-item.priority, item.id))
    for rule in ordered:
        if not rule.enabled:
            continue
        if rule_matches(lead, rule):
            return RoutingDecision(
                matched_rule_id=rule.id,
                action=rule.action,
                action_payload=rule.action_payload or {},
            )
    return RoutingDecision(matched_rule_id=None, action=None, action_payload={})


def apply_routing_decision(lead: Lead, decision: RoutingDecision) -> None:
    action = decision.action
    payload = decision.action_payload

    if action == "assign_user":
        lead.owner_user_id = str(payload.get("user_id")) if payload.get("user_id") else None
        lead.assigned_team_id = None
        lead.assigned_queue_name = None
    elif action == "assign_team":
        lead.assigned_team_id = str(payload.get("team_id")) if payload.get("team_id") else None
        lead.owner_user_id = None
        lead.assigned_queue_name = None
    elif action == "queue":
        lead.assigned_queue_name = (
            str(payload.get("queue_name")) if payload.get("queue_name") else None
        )
        lead.owner_user_id = None
        lead.assigned_team_id = None
