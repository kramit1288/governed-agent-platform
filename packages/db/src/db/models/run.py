"""Run persistence model."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin
from db.enums import RunStatus

if TYPE_CHECKING:
    from db.models.approval_request import ApprovalRequest
    from db.models.run_event import RunEvent
    from db.models.tool_invocation import ToolInvocation

JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")


class Run(TimestampMixin, Base):
    """Represents a single orchestrated run."""

    __tablename__ = "runs"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    status: Mapped[RunStatus] = mapped_column(
        Enum(RunStatus, name="run_status", native_enum=False),
        default=RunStatus.PENDING,
        nullable=False,
        index=True,
    )
    workflow_key: Mapped[str] = mapped_column(String(100), nullable=False)
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    input_payload: Mapped[dict | None] = mapped_column(JSON_DOCUMENT, nullable=True)
    last_error: Mapped[str | None] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    events: Mapped[list["RunEvent"]] = relationship(back_populates="run")
    tool_invocations: Mapped[list["ToolInvocation"]] = relationship(back_populates="run")
    approval_requests: Mapped[list["ApprovalRequest"]] = relationship(back_populates="run")
