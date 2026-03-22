"""Explicit approval coordination for pause and resume flows."""

from __future__ import annotations

from uuid import UUID

from db.enums import ApprovalStatus
from orchestrator.errors import ApprovalResolutionError
from orchestrator.interfaces import ApprovalStore
from orchestrator.models import ApprovalDecision, RunContext
from tracing.events import ApprovalRequestedPayload, ApprovalResolvedPayload, TraceEventType
from tracing.recorder import TraceRecorder


class ApprovalCoordinator:
    """Own approval request creation and resolution-side trace emission."""

    def __init__(
        self,
        *,
        approval_store: ApprovalStore,
        trace_recorder: TraceRecorder,
    ) -> None:
        self._approval_store = approval_store
        self._trace_recorder = trace_recorder

    def request_approval(
        self,
        *,
        context: RunContext,
        reason: str,
        action_preview: dict[str, object] | None,
        tool_invocation_id: UUID | None,
    ) -> UUID:
        approval_request = self._approval_store.create_approval_request(
            run_id=context.task.run_id,
            reason=reason,
            action_preview=action_preview,
            tool_invocation_id=tool_invocation_id,
        )
        approval_request_id = _extract_uuid(getattr(approval_request, "id", None), "approval request id")
        self._trace_recorder.record_event(
            context.task.run_id,
            TraceEventType.APPROVAL_REQUESTED.value,
            ApprovalRequestedPayload(
                approval_request_id=str(approval_request_id),
                tool_invocation_id=str(tool_invocation_id) if tool_invocation_id is not None else None,
                status=ApprovalDecision.PENDING.value,
                action_preview=action_preview,
            ),
        )
        return approval_request_id

    def record_resolution(
        self,
        *,
        run_id: UUID,
        approval_request_id: UUID,
        decision: ApprovalDecision,
        decision_comment: str | None,
    ) -> None:
        self._trace_recorder.record_event(
            run_id,
            TraceEventType.APPROVAL_RESOLVED.value,
            ApprovalResolvedPayload(
                approval_request_id=str(approval_request_id),
                status=decision.value,
                decision_comment=decision_comment,
            ),
        )

    def decision_for_status(self, status: ApprovalStatus) -> ApprovalDecision:
        return ApprovalDecision(status.value)


def resolve_approval_status(decision: str) -> ApprovalStatus:
    """Translate API decisions to persistence status values."""

    normalized = decision.upper()
    try:
        return ApprovalStatus(normalized)
    except ValueError as exc:
        raise ApprovalResolutionError(f"Unsupported approval decision '{decision}'.") from exc


def _extract_uuid(value: object, label: str) -> UUID:
    if not isinstance(value, UUID):
        raise ApprovalResolutionError(f"Expected {label} to be a UUID.")
    return value
