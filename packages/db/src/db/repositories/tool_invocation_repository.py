"""Tool invocation repository methods."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.enums import ToolInvocationStatus
from db.models import ToolInvocation


class ToolInvocationRepository:
    """Persistence operations for tool invocation audit records."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_tool_invocation(
        self,
        *,
        run_id: UUID,
        tool_name: str,
        input_payload: dict | None = None,
        requires_approval: bool = False,
        status: ToolInvocationStatus = ToolInvocationStatus.PENDING,
    ) -> ToolInvocation:
        invocation = ToolInvocation(
            run_id=run_id,
            tool_name=tool_name,
            status=status,
            input_payload=input_payload,
            requires_approval=requires_approval,
        )
        self._session.add(invocation)
        self._session.flush()
        return invocation

    def get_tool_invocation(self, tool_invocation_id: UUID) -> ToolInvocation | None:
        return self._session.get(ToolInvocation, tool_invocation_id)

    def update_tool_invocation(
        self,
        tool_invocation_id: UUID,
        *,
        status: ToolInvocationStatus,
        output_payload: dict | None = None,
        error_message: str | None = None,
    ) -> ToolInvocation | None:
        invocation = self.get_tool_invocation(tool_invocation_id)
        if invocation is None:
            return None
        invocation.status = status
        invocation.output_payload = output_payload
        invocation.error_message = error_message
        self._session.flush()
        return invocation

    def list_for_run(self, run_id: UUID) -> list[ToolInvocation]:
        statement = (
            select(ToolInvocation)
            .where(ToolInvocation.run_id == run_id)
            .order_by(ToolInvocation.created_at.asc())
        )
        return list(self._session.scalars(statement))
