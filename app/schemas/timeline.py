from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class TimelineEventCreate(BaseModel):
    type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TimelineEventUpdate(BaseModel):
    type: str | None = None
    payload: dict[str, Any] | None = None


class TimelineEventResponse(BaseModel):
    id: str
    tenant_id: str
    lead_id: str
    type: str
    payload: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
