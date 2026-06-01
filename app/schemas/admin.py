from datetime import date

from pydantic import BaseModel, Field


class ProvisionTenantRequest(BaseModel):
    name: str
    slug: str
    owner_email: str
    plan: str = "starter"


class ProvisionTenantResponse(BaseModel):
    tenant_id: str
    user_id: str
    api_key: str
    plan: str


class DesignPartnerEnrollmentRequest(BaseModel):
    cohort: str = "wave-1"
    launch_notes: str | None = None


class DesignPartnerEnrollmentResponse(BaseModel):
    tenant_id: str
    enrolled: bool
    cohort: str


class PlanLimitSnapshotResponse(BaseModel):
    plan: str
    limits: dict[str, int]


class RolloutPromotionRequest(BaseModel):
    rollout_percentage: int = Field(ge=0, le=100)


class RolloutPromotionResponse(BaseModel):
    tenant_id: str
    rollout_percentage: int


class UsageDayRecord(BaseModel):
    model_config = {"from_attributes": True}

    record_date: date
    ai_tokens_used: int
    messages_sent: int
    emails_sent: int
    sms_sent: int
    leads_created: int
    sessions_created: int


class UsageSummaryResponse(BaseModel):
    tenant_id: str
    days: int
    records: list[UsageDayRecord]


class FailedJobResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    queue_name: str
    event_type: str
    error: str
    attempts: int
    status: str
    tenant_id: str | None
    created_at: str


class DLQListResponse(BaseModel):
    total: int
    jobs: list[FailedJobResponse]


class DLQReplayResponse(BaseModel):
    job_id: str
    replayed: bool
