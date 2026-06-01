from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.models.base import BaseModel


class FailedJob(BaseModel):
    __tablename__ = "failed_jobs"

    queue_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    error: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    # pending | replayed
    status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, index=True)
    tenant_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    replayed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
