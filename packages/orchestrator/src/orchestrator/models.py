"""Domain models for the explicit orchestrator lifecycle."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from uuid import UUID


class RunState(StrEnum):
    """Lifecycle states owned by the orchestrator."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class RunStep(StrEnum):
    """Deterministic steps in the V1 run flow."""

    CLASSIFY = "classify"
    RETRIEVE_CONTEXT = "retrieve_context"
    DECIDE_TOOLS = "decide_tools"
    EXECUTE_TOOLS = "execute_tools"
    REQUEST_APPROVAL_IF_NEEDED = "request_approval_if_needed"
    GENERATE_RESPONSE = "generate_response"
    COMPLETE = "complete"


class ApprovalDecision(StrEnum):
    """Approval outcomes that affect run resumption."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


@dataclass(slots=True)
class AgentTask:
    """User task input for a single-agent run."""

    run_id: UUID
    workflow_key: str
    user_input: str
    tenant_id: str
    requested_by: str | None = None


@dataclass(slots=True)
class RetrievedContext:
    """Retrieved context record returned by the retrieval collaborator."""

    source_id: str
    content: str


@dataclass(slots=True)
class ToolCall:
    """A planned tool invocation in the explicit step flow."""

    name: str
    requires_approval: bool = False
    arguments: dict[str, object] = field(default_factory=dict)


@dataclass(slots=True)
class ToolExecutionResult:
    """Outcome of the tool execution stage."""

    outputs: list[dict[str, object]] = field(default_factory=list)
    requires_approval: bool = False
    approval_reason: str | None = None
    approval_preview: dict[str, object] | None = None
    tool_records: list["ToolExecutionRecord"] = field(default_factory=list)


@dataclass(slots=True)
class ToolExecutionRecord:
    """Audit-friendly tool execution record surfaced to the orchestrator."""

    tool_name: str
    status: str
    tool_invocation_id: UUID | None = None
    output: dict[str, object] | None = None
    error: str | None = None
    requires_approval: bool = False
    preview_payload: dict[str, object] | None = None


@dataclass(slots=True)
class RunContext:
    """Mutable run context carried through the orchestrator state machine."""

    task: AgentTask
    state: RunState = RunState.PENDING
    current_step: RunStep | None = None
    classification: str | None = None
    retrieved_context: list[RetrievedContext] = field(default_factory=list)
    planned_tools: list[ToolCall] = field(default_factory=list)
    tool_results: list[dict[str, object]] = field(default_factory=list)
    tool_records: list[ToolExecutionRecord] = field(default_factory=list)
    response_text: str | None = None
    approval_request_id: UUID | None = None
    pending_tool_invocation_id: UUID | None = None
    failure_reason: str | None = None
