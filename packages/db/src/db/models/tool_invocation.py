"""Tool invocation persistence model."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import Enum, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin
from db.enums import ToolInvocationStatus

if TYPE_CHECKING:
    from db.models.approval_request import ApprovalRequest
    from db.models.run import Run


class ToolInvocation(TimestampMixin, Base):
    """Stores a tool call attempt associated with a run."""

    __tablename__ = "tool_invocations"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(ForeignKey("runs.id", ondelete="CASCADE"), nullable=False, index=True)
    tool_name: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[ToolInvocationStatus] = mapped_column(
        Enum(ToolInvocationStatus, name="tool_invocation_status", native_enum=False),
        default=ToolInvocationStatus.PENDING,
        nullable=False,
    )
    requires_approval: Mapped[bool] = mapped_column(default=False, nullable=False)
    input_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    output_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)

    run: Mapped["Run"] = relationship(back_populates="tool_invocations")
    approval_request: Mapped["ApprovalRequest | None"] = relationship(back_populates="tool_invocation")
