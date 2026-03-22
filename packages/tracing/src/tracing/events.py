"""Normalized trace event types and compact payload shapes."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TraceEventType(StrEnum):
    """Append-only orchestration events exposed to traces and the future UI."""

    RUN_STARTED = "RUN_STARTED"
    MODEL_SELECTED = "MODEL_SELECTED"
    RETRIEVAL_COMPLETED = "RETRIEVAL_COMPLETED"
    TOOL_CALLED = "TOOL_CALLED"
    TOOL_RESULT_RECEIVED = "TOOL_RESULT_RECEIVED"
    APPROVAL_REQUESTED = "APPROVAL_REQUESTED"
    APPROVAL_RESOLVED = "APPROVAL_RESOLVED"
    RUN_COMPLETED = "RUN_COMPLETED"
    RUN_FAILED = "RUN_FAILED"


class TracePayload(BaseModel):
    """Base class for compact event payloads."""

    model_config = ConfigDict(extra="forbid")


class RunStartedPayload(TracePayload):
    workflow_key: str
    tenant_id: str


class ModelSelectedPayload(TracePayload):
    provider: str
    model: str
    reason: str | None = None


class RetrievalCompletedPayload(TracePayload):
    classification: str
    document_count: int


class ToolCalledPayload(TracePayload):
    tool_name: str
    tool_invocation_id: str | None = None
    requires_approval: bool


class ToolResultReceivedPayload(TracePayload):
    tool_name: str
    tool_invocation_id: str | None = None
    status: str
    requires_approval: bool


class ApprovalRequestedPayload(TracePayload):
    approval_request_id: str
    tool_invocation_id: str | None = None
    status: str
    action_preview: dict[str, object] | None = None


class ApprovalResolvedPayload(TracePayload):
    approval_request_id: str
    status: str
    decision_comment: str | None = None


class RunCompletedPayload(TracePayload):
    final_state: str
    response_text: str | None = None


class RunFailedPayload(TracePayload):
    error: str


class TraceEventRecord(BaseModel):
    """Serialized run event returned by timeline builders and APIs."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    sequence: int
    event_type: TraceEventType
    payload: dict[str, object] | None = None
    created_at: datetime
