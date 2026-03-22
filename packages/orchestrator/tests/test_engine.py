"""Unit tests for the explicit orchestrator lifecycle."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

import pytest
from db.enums import ApprovalStatus
from tracing.events import TraceEventType

from orchestrator.engine import OrchestratorEngine
from orchestrator.errors import ApprovalResolutionError, InvalidStateTransitionError
from orchestrator.models import (
    AgentTask,
    ApprovalDecision,
    RetrievedContext,
    RunContext,
    RunState,
    ToolCall,
    ToolExecutionRecord,
    ToolExecutionResult,
)
from orchestrator.state_machine import OrchestratorStateMachine


@dataclass(slots=True)
class FakeApprovalRecord:
    id: UUID


class FakeRunStore:
    def __init__(self) -> None:
        self.status_updates: list[tuple[UUID, object, str | None]] = []
        self.events: list[tuple[UUID, str, dict[str, object] | None]] = []

    def update_run_status(self, run_id: UUID, *, status: object, last_error: str | None = None) -> object:
        self.status_updates.append((run_id, status, last_error))
        return {"run_id": run_id, "status": status}

    def append_run_event(self, *, run_id: UUID, event_type: str, payload: dict[str, object] | None = None) -> object:
        self.events.append((run_id, event_type, payload))
        return {"run_id": run_id, "event_type": event_type}


class FakeApprovalStore:
    def __init__(self, decision: ApprovalDecision = ApprovalDecision.PENDING) -> None:
        self.decision = decision
        self.created_requests: list[tuple[UUID, str, dict[str, object] | None, UUID | None]] = []
        self._approval_id = uuid4()
        self.decision_comment: str | None = None

    def create_approval_request(
        self,
        *,
        run_id: UUID,
        reason: str,
        action_preview: dict[str, object] | None = None,
        tool_invocation_id: UUID | None = None,
    ) -> FakeApprovalRecord:
        self.created_requests.append((run_id, reason, action_preview, tool_invocation_id))
        return FakeApprovalRecord(id=self._approval_id)

    def get_approval_decision(self, approval_request_id: UUID) -> ApprovalDecision:
        assert approval_request_id == self._approval_id
        return self.decision

    def get_approval_request(self, approval_request_id: UUID) -> object:
        assert approval_request_id == self._approval_id
        return type("ApprovalRecord", (), {"decision_comment": self.decision_comment})()

    def resolve_approval_request(
        self,
        approval_request_id: UUID,
        *,
        status: ApprovalStatus,
        decision_comment: str | None = None,
    ) -> object:
        assert approval_request_id == self._approval_id
        self.decision = ApprovalDecision(status.value)
        self.decision_comment = decision_comment
        return type("ApprovalRecord", (), {"id": approval_request_id})()


class FakeAIGateway:
    def classify(self, task: AgentTask) -> str:
        return "retrieve_and_answer"

    def generate_response(self, context: RunContext) -> str:
        return f"response:{context.classification}:{len(context.tool_results)}"

    def describe_route(self, context: RunContext) -> dict[str, object]:
        return {"provider": "mock", "model": "mock-strong", "reason": "test"}


class FakeRetrievalService:
    def retrieve(self, task: AgentTask, classification: str) -> list[RetrievedContext]:
        return [RetrievedContext(source_id="doc-1", content=f"context for {classification}")]


class FakeToolExecutor:
    def __init__(self, *, requires_approval: bool = False, should_fail: bool = False) -> None:
        self.requires_approval = requires_approval
        self.should_fail = should_fail

    def plan_tools(self, context: RunContext) -> list[ToolCall]:
        return [ToolCall(name="lookup_policy", requires_approval=self.requires_approval)]

    def execute_tools(self, context: RunContext) -> ToolExecutionResult:
        if self.should_fail:
            raise RuntimeError("tool execution failed")
        if self.requires_approval:
            invocation_id = uuid4()
            return ToolExecutionResult(
                outputs=[{"preview": True}],
                requires_approval=True,
                approval_reason="High-risk action",
                approval_preview={"tool": "lookup_policy"},
                tool_records=[
                    ToolExecutionRecord(
                        tool_name="lookup_policy",
                        status="approval_required",
                        tool_invocation_id=invocation_id,
                        requires_approval=True,
                        preview_payload={"tool": "lookup_policy"},
                    )
                ],
            )
        return ToolExecutionResult(
            outputs=[{"tool": "lookup_policy", "status": "ok"}],
            tool_records=[
                ToolExecutionRecord(
                    tool_name="lookup_policy",
                    status="succeeded",
                    output={"tool": "lookup_policy", "status": "ok"},
                )
            ],
        )


class FakeTraceRecorder:
    def __init__(self) -> None:
        self.events: list[tuple[UUID, str, dict[str, object] | None]] = []

    def record_event(self, run_id: UUID, event_type: str, payload: dict[str, object] | None = None) -> None:
        self.events.append((run_id, event_type, payload))


class FakeRuntimeHooks:
    def __init__(self) -> None:
        self.stored_contexts: list[RunContext] = []
        self.waiting_calls: list[tuple[UUID, UUID]] = []
        self.resumed_calls: list[UUID] = []
        self.completed_calls: list[tuple[UUID, RunState]] = []

    def store_waiting_context(self, context: RunContext) -> None:
        self.stored_contexts.append(context)

    def on_waiting_for_approval(self, run_id: UUID, approval_request_id: UUID) -> None:
        self.waiting_calls.append((run_id, approval_request_id))

    def on_run_resumed(self, run_id: UUID) -> None:
        self.resumed_calls.append(run_id)

    def on_run_completed(self, run_id: UUID, state: RunState) -> None:
        self.completed_calls.append((run_id, state))


def build_engine(*, requires_approval: bool = False, should_fail: bool = False, approval_decision: ApprovalDecision = ApprovalDecision.PENDING) -> tuple[OrchestratorEngine, FakeRunStore, FakeApprovalStore, FakeTraceRecorder, FakeRuntimeHooks]:
    run_store = FakeRunStore()
    approval_store = FakeApprovalStore(decision=approval_decision)
    trace_recorder = FakeTraceRecorder()
    runtime_hooks = FakeRuntimeHooks()
    engine = OrchestratorEngine(
        run_store=run_store,
        approval_store=approval_store,
        ai_gateway=FakeAIGateway(),
        retrieval_service=FakeRetrievalService(),
        tool_executor=FakeToolExecutor(requires_approval=requires_approval, should_fail=should_fail),
        trace_recorder=trace_recorder,
        runtime_hooks=runtime_hooks,
    )
    return engine, run_store, approval_store, trace_recorder, runtime_hooks


def make_task() -> AgentTask:
    return AgentTask(
        run_id=uuid4(),
        workflow_key="support.ticket",
        user_input="How do I handle this request?",
        tenant_id="tenant-1",
        requested_by="operator@example.com",
    )


def test_happy_path_completes_successfully() -> None:
    engine, run_store, _, trace_recorder, runtime_hooks = build_engine()

    context = engine.start_run(make_task())

    assert context.state is RunState.COMPLETED
    assert context.response_text == "response:retrieve_and_answer:1"
    assert [status for _, status, _ in run_store.status_updates] == ["IN_PROGRESS", "COMPLETED"]
    assert any(event_type == TraceEventType.RUN_COMPLETED.value for _, event_type, _ in trace_recorder.events)
    assert runtime_hooks.completed_calls[-1][1] is RunState.COMPLETED


def test_approval_required_path_pauses_run() -> None:
    engine, run_store, approval_store, _, runtime_hooks = build_engine(requires_approval=True)

    context = engine.start_run(make_task())

    assert context.state is RunState.WAITING_FOR_APPROVAL
    assert context.approval_request_id is not None
    assert approval_store.created_requests[0][1] == "High-risk action"
    assert run_store.status_updates[-1][1] == "WAITING_FOR_APPROVAL"
    assert runtime_hooks.waiting_calls[0][1] == context.approval_request_id
    assert runtime_hooks.stored_contexts[0].approval_request_id == context.approval_request_id
    assert any(event_type == TraceEventType.APPROVAL_REQUESTED.value for _, event_type, _ in trace_recorder.events)


def test_invalid_state_transition_raises_error() -> None:
    state_machine = OrchestratorStateMachine()

    with pytest.raises(InvalidStateTransitionError):
        state_machine.transition_state(RunState.PENDING, RunState.COMPLETED)


def test_resume_after_approval_continues_to_completion() -> None:
    engine, run_store, approval_store, trace_recorder, runtime_hooks = build_engine(
        requires_approval=True,
        approval_decision=ApprovalDecision.APPROVED,
    )
    context = engine.start_run(make_task())

    resumed = engine.resume_after_approval(context)

    assert resumed.state is RunState.COMPLETED
    assert resumed.response_text == "response:retrieve_and_answer:1"
    assert runtime_hooks.resumed_calls == [context.task.run_id]
    assert any(event_type == TraceEventType.APPROVAL_RESOLVED.value for _, event_type, _ in trace_recorder.events)
    assert run_store.status_updates[-1][1] == "COMPLETED"
    assert approval_store.created_requests


def test_terminal_failure_marks_run_failed() -> None:
    engine, run_store, _, trace_recorder, runtime_hooks = build_engine(should_fail=True)

    context = engine.start_run(make_task())

    assert context.state is RunState.FAILED
    assert context.failure_reason == "tool execution failed"
    assert run_store.status_updates[-1][1] == "FAILED"
    assert run_store.status_updates[-1][2] == "tool execution failed"
    assert any(event_type == TraceEventType.RUN_FAILED.value for _, event_type, _ in trace_recorder.events)
    assert runtime_hooks.completed_calls[-1][1] is RunState.FAILED


def test_resume_requires_waiting_state() -> None:
    engine, _, _, _, _ = build_engine()

    with pytest.raises(ApprovalResolutionError):
        engine.resume_after_approval(RunContext(task=make_task(), state=RunState.IN_PROGRESS))


def test_rejected_approval_cancels_run() -> None:
    engine, run_store, _, trace_recorder, runtime_hooks = build_engine(
        requires_approval=True,
        approval_decision=ApprovalDecision.REJECTED,
    )
    context = engine.start_run(make_task())

    resumed = engine.resume_after_approval(context)

    assert resumed.state is RunState.CANCELED
    assert resumed.failure_reason == "Approval rejected"
    assert run_store.status_updates[-1][1] == "CANCELED"
    assert any(event_type == TraceEventType.APPROVAL_RESOLVED.value for _, event_type, _ in trace_recorder.events)
    assert runtime_hooks.completed_calls[-1][1] is RunState.CANCELED
