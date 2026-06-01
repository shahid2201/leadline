from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LeadCreate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    channel: str | None = None
    campaign: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    status: str = "new"
    stage: str | None = None
    lead_score: int = 0
    fit_score: int = 0
    engagement_score: int = 0
    owner_user_id: str | None = None
    assigned_team_id: str | None = None
    assigned_queue_name: str | None = None
    marketing_opt_in: bool = False
    allowed_channels: list[str] = Field(default_factory=list)
    custom_fields: dict[str, Any] = Field(default_factory=dict)


class LeadUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    company: str | None = None
    role: str | None = None
    channel: str | None = None
    campaign: str | None = None
    utm_source: str | None = None
    utm_medium: str | None = None
    utm_campaign: str | None = None
    status: str | None = None
    stage: str | None = None
    lead_score: int | None = None
    fit_score: int | None = None
    engagement_score: int | None = None
    owner_user_id: str | None = None
    assigned_team_id: str | None = None
    assigned_queue_name: str | None = None
    marketing_opt_in: bool | None = None
    allowed_channels: list[str] | None = None
    custom_fields: dict[str, Any] | None = None


class LeadResponse(BaseModel):
    id: str
    tenant_id: str
    name: str | None
    email: str | None
    phone: str | None
    company: str | None
    role: str | None
    channel: str | None
    campaign: str | None
    utm_source: str | None
    utm_medium: str | None
    utm_campaign: str | None
    status: str
    stage: str | None
    lead_score: int
    fit_score: int
    engagement_score: int
    owner_user_id: str | None
    assigned_team_id: str | None
    assigned_queue_name: str | None
    marketing_opt_in: bool
    allowed_channels: list[str]
    custom_fields: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LeadCreateResult(BaseModel):
    deduplicated: bool
    lead: LeadResponse


class AttachSessionPayload(BaseModel):
    session_id: str
