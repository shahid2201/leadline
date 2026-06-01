from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class SessionCreate(BaseModel):
    visitor_id: str
    lead_id: str | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SessionUpdate(BaseModel):
    lead_id: str | None = None
    ended_at: datetime | None = None
    metadata: dict[str, Any] | None = None


class SessionResponse(BaseModel):
    id: str
    tenant_id: str
    visitor_id: str
    lead_id: str | None
    started_at: datetime | None
    ended_at: datetime | None
    metadata: dict[str, Any] = Field(alias="session_metadata")
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True, "populate_by_name": True}


class MessageCreate(BaseModel):
    sender_type: str
    content: str
    intent: str | None = None
    entities: dict[str, Any] = Field(default_factory=dict)
    sentiment: str | None = None
    urgency: str | None = None
    topics: list[str] = Field(default_factory=list)


class MessageUpdate(BaseModel):
    sender_type: str | None = None
    content: str | None = None
    intent: str | None = None
    entities: dict[str, Any] | None = None
    sentiment: str | None = None
    urgency: str | None = None
    topics: list[str] | None = None


class MessageResponse(BaseModel):
    id: str
    tenant_id: str
    session_id: str
    sender_type: str
    content: str
    intent: str | None
    entities: dict[str, Any]
    sentiment: str | None
    urgency: str | None
    topics: list[str]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
