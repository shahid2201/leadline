from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class RoutingRuleCreate(BaseModel):
    name: str
    priority: int = 100
    enabled: bool = True
    conditions: list[dict[str, Any]] = Field(default_factory=list)
    action: str
    action_payload: dict[str, Any] = Field(default_factory=dict)


class RoutingRuleUpdate(BaseModel):
    name: str | None = None
    priority: int | None = None
    enabled: bool | None = None
    conditions: list[dict[str, Any]] | None = None
    action: str | None = None
    action_payload: dict[str, Any] | None = None


class RoutingRuleResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    priority: int
    enabled: bool
    conditions: list[dict[str, Any]]
    action: str
    action_payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
