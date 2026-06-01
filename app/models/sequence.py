from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Sequence(BaseModel):
    __tablename__ = "sequences"

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    trigger: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="draft")

    steps = relationship(
        "SequenceStep",
        back_populates="sequence",
        cascade="all, delete-orphan",
    )


class SequenceStep(BaseModel):
    __tablename__ = "sequence_steps"

    sequence_id: Mapped[str] = mapped_column(
        ForeignKey("sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    order_index: Mapped[int] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    delay_seconds: Mapped[int] = mapped_column(nullable=False, default=0)
    template: Mapped[str | None] = mapped_column(String(4000), nullable=True)

    sequence = relationship("Sequence", back_populates="steps")


class SequenceEnrollment(BaseModel):
    __tablename__ = "sequence_enrollments"

    tenant_id: Mapped[str] = mapped_column(
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    lead_id: Mapped[str] = mapped_column(
        ForeignKey("leads.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sequence_id: Mapped[str] = mapped_column(
        ForeignKey("sequences.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="active")
    current_step_index: Mapped[int] = mapped_column(nullable=False, default=0)
