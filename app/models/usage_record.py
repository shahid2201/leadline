from datetime import date

from sqlalchemy import Date, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import BaseModel


class UsageRecord(BaseModel):
    __tablename__ = "usage_records"
    __table_args__ = (
        UniqueConstraint("tenant_id", "record_date", name="uq_usage_tenant_date"),
        Index("ix_usage_tenant_date", "tenant_id", "record_date"),
    )

    tenant_id: Mapped[str] = mapped_column(String(36), nullable=False)
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    ai_tokens_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    emails_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sms_sent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    leads_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sessions_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
