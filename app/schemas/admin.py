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
