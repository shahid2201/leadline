from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Lead(BaseModel):
    __tablename__ = "leads"

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(320), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str | None] = mapped_column(String(120), nullable=True)

    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    campaign: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_source: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_medium: Mapped[str | None] = mapped_column(String(120), nullable=True)
    utm_campaign: Mapped[str | None] = mapped_column(String(120), nullable=True)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default="new")
    stage: Mapped[str | None] = mapped_column(String(50), nullable=True)

    lead_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fit_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    engagement_score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    assigned_team_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    assigned_queue_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    marketing_opt_in: Mapped[bool] = mapped_column(nullable=False, default=False)
    allowed_channels: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)

    custom_fields: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    timeline_events = relationship(
        "LeadTimelineEvent",
        back_populates="lead",
        cascade="all, delete-orphan",
    )
    sessions = relationship("Session", back_populates="lead")
