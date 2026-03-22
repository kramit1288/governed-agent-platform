"""Collaborator protocols used by the explicit orchestrator engine."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from orchestrator.models import (
    ApprovalDecision,
    AgentTask,
    RetrievedContext,
    RunContext,
    RunState,
    ToolCall,
    ToolExecutionResult,
)


class RunStore(Protocol):
    """Persistence hooks for run status and append-only events."""

    def update_run_status(self, run_id: UUID, *, status: object, last_error: str | None = None) -> object | None:
        ...

    def append_run_event(self, *, run_id: UUID, event_type: str, payload: dict[str, object] | None = None) -> object:
        ...


class ApprovalStore(Protocol):
    """Persistence hooks for approval creation and resolution lookup."""

    def create_approval_request(
        self,
        *,
        run_id: UUID,
        reason: str,
        action_preview: dict[str, object] | None = None,
        tool_invocation_id: UUID | None = None,
    ) -> object:
        ...

    def get_approval_decision(self, approval_request_id: UUID) -> ApprovalDecision:
        ...

    def get_approval_request(self, approval_request_id: UUID) -> object | None:
        ...

    def resolve_approval_request(
        self,
        approval_request_id: UUID,
        *,
        status: object,
        decision_comment: str | None = None,
    ) -> object | None:
        ...


class AIGateway(Protocol):
    """Gateway-facing operations used by the orchestrator."""

    def classify(self, task: AgentTask) -> str:
        ...

    def generate_response(self, context: RunContext) -> str:
        ...

    def describe_route(self, context: RunContext) -> dict[str, object] | None:
        ...


class RetrievalService(Protocol):
    """Retrieval operations for assembling grounded context."""

    def retrieve(self, task: AgentTask, classification: str) -> list[RetrievedContext]:
        ...


class ToolExecutor(Protocol):
    """Tool planning and execution hooks."""

    def plan_tools(self, context: RunContext) -> list[ToolCall]:
        ...

    def execute_tools(self, context: RunContext) -> ToolExecutionResult:
        ...


class TraceRecorder(Protocol):
    """Trace emission hook for orchestration events."""

    def record_event(self, run_id: UUID, event_type: str, payload: dict[str, object] | None = None) -> None:
        ...


class RuntimeResumeHooks(Protocol):
    """Runtime notifications for waiting and resumed runs."""

    def store_waiting_context(self, context: RunContext) -> None:
        ...

    def on_waiting_for_approval(self, run_id: UUID, approval_request_id: UUID) -> None:
        ...

    def on_run_resumed(self, run_id: UUID) -> None:
        ...

    def on_run_completed(self, run_id: UUID, state: RunState) -> None:
        ...
