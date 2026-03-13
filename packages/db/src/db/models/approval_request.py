"""Approval request persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin
from db.enums import ApprovalStatus

if TYPE_CHECKING:
    from db.models.run import Run
    from db.models.tool_invocation import ToolInvocation


class ApprovalRequest(TimestampMixin, Base):
    """Represents an approval checkpoint for a risky action."""

    __tablename__ = "approval_requests"
    __table_args__ = (
        UniqueConstraint("tool_invocation_id", name="uq_approval_requests_tool_invocation_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_invocation_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("tool_invocations.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[ApprovalStatus] = mapped_column(
        Enum(ApprovalStatus, name="approval_status", native_enum=False),
        default=ApprovalStatus.PENDING,
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(255), nullable=False)
    preview_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decision_comment: Mapped[str | None] = mapped_column(String(500), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    run: Mapped["Run"] = relationship(back_populates="approval_requests")
    tool_invocation: Mapped["ToolInvocation | None"] = relationship(back_populates="approval_request")
