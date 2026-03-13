"""Evaluation result persistence model."""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum, ForeignKey, JSON, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin
from db.enums import EvalResultStatus

if TYPE_CHECKING:
    from db.models.eval_case import EvalCase
    from db.models.eval_run import EvalRun


class EvalResult(TimestampMixin, Base):
    """Stores the outcome of a single eval case within an eval run."""

    __tablename__ = "eval_results"
    __table_args__ = (UniqueConstraint("eval_run_id", "eval_case_id", name="uq_eval_results_run_case"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    eval_run_id: Mapped[UUID] = mapped_column(ForeignKey("eval_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    eval_case_id: Mapped[UUID] = mapped_column(ForeignKey("eval_cases.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[EvalResultStatus] = mapped_column(
        Enum(EvalResultStatus, name="eval_result_status", native_enum=False),
        nullable=False,
    )
    score: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    summary: Mapped[str | None] = mapped_column(String(500), nullable=True)
    details: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    eval_run: Mapped["EvalRun"] = relationship(back_populates="results")
    eval_case: Mapped["EvalCase"] = relationship(back_populates="results")
