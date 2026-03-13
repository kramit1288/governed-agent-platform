"""Evaluation run persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin
from db.enums import EvalRunStatus

if TYPE_CHECKING:
    from db.models.eval_result import EvalResult


class EvalRun(TimestampMixin, Base):
    """Represents a batch execution of offline evaluation cases."""

    __tablename__ = "eval_runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[EvalRunStatus] = mapped_column(
        Enum(EvalRunStatus, name="eval_run_status", native_enum=False),
        default=EvalRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    results: Mapped[list["EvalResult"]] = relationship(back_populates="eval_run")
