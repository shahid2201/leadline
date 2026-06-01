from datetime import datetime

from pydantic import BaseModel


class SequenceCreate(BaseModel):
    name: str
    description: str | None = None
    trigger: str
    status: str = "draft"


class SequenceUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    trigger: str | None = None
    status: str | None = None


class SequenceResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    description: str | None
    trigger: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SequenceStepCreate(BaseModel):
    order_index: int
    type: str
    delay_seconds: int = 0
    template: str | None = None


class SequenceStepUpdate(BaseModel):
    order_index: int | None = None
    type: str | None = None
    delay_seconds: int | None = None
    template: str | None = None


class SequenceStepResponse(BaseModel):
    id: str
    sequence_id: str
    order_index: int
    type: str
    delay_seconds: int
    template: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SequenceEnrollRequest(BaseModel):
    lead_id: str


class SequenceEnrollmentResponse(BaseModel):
    id: str
    tenant_id: str
    lead_id: str
    sequence_id: str
    status: str
    current_step_index: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
