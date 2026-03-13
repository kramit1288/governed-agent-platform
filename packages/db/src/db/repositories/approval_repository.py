"""Approval request repository methods."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from db.enums import ApprovalStatus
from db.models import ApprovalRequest


class ApprovalRepository:
    """Persistence operations for approval requests."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_approval_request(
        self,
        *,
        run_id: UUID,
        reason: str,
        preview_payload: dict | None = None,
        tool_invocation_id: UUID | None = None,
        expires_at: datetime | None = None,
    ) -> ApprovalRequest:
        approval_request = ApprovalRequest(
            run_id=run_id,
            reason=reason,
            preview_payload=preview_payload,
            tool_invocation_id=tool_invocation_id,
            expires_at=expires_at,
        )
        self._session.add(approval_request)
        self._session.flush()
        return approval_request

    def resolve_approval_request(
        self,
        approval_request_id: UUID,
        *,
        status: ApprovalStatus,
        decision_comment: str | None = None,
    ) -> ApprovalRequest | None:
        approval_request = self._session.get(ApprovalRequest, approval_request_id)
        if approval_request is None:
            return None

        approval_request.status = status
        approval_request.decision_comment = decision_comment
        approval_request.resolved_at = datetime.now(timezone.utc)
        self._session.flush()
        return approval_request
