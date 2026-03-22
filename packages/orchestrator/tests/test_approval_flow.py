"""Integration tests for persisted approval-gated run flow and tracing."""

from __future__ import annotations

from uuid import uuid4

import pytest
from db.enums import ApprovalStatus, RunStatus, ToolInvocationStatus
from db.repositories import ApprovalRepository, RunRepository, ToolInvocationRepository
from runtime.engine import InMemoryRuntimeController
from tracing import TimelineBuilder, TraceEventRecord, TraceEventType, TraceRecorder

from orchestrator.engine import OrchestratorEngine
from orchestrator.models import AgentTask, RetrievedContext, RunContext, RunState, ToolCall, ToolExecutionRecord, ToolExecutionResult


class IntegrationGateway:
    def classify(self, task: AgentTask) -> str:
        return "support"

    def generate_response(self, context: RunContext) -> str:
        return "final response"

    def describe_route(self, context: RunContext) -> dict[str, object]:
        return {"provider": "openai", "model": "gpt-4.1", "reason": "high-risk approval flow"}


class IntegrationRetrievalService:
    def retrieve(self, task: AgentTask, classification: str) -> list[RetrievedContext]:
        return [RetrievedContext(source_id="DOC-100", content="Refund policy")]


class IntegrationToolExecutor:
    def __init__(self, invocation_repository: ToolInvocationRepository, *, requires_approval: bool) -> None:
        self._invocation_repository = invocation_repository
        self._requires_approval = requires_approval

    def plan_tools(self, context: RunContext) -> list[ToolCall]:
        return [ToolCall(name="draft_refund_request", requires_approval=self._requires_approval)]

    def execute_tools(self, context: RunContext) -> ToolExecutionResult:
        invocation = self._invocation_repository.create_tool_invocation(
            run_id=context.task.run_id,
            tool_name="draft_refund_request",
            input_payload={"ticket_id": "T-100"},
            requires_approval=self._requires_approval,
            status=ToolInvocationStatus.APPROVAL_REQUIRED if self._requires_approval else ToolInvocationStatus.COMPLETED,
        )
        preview = {"action": "draft_refund_request", "amount": 42.5}
        return ToolExecutionResult(
            outputs=[{"preview": True}] if self._requires_approval else [{"ok": True}],
            requires_approval=self._requires_approval,
            approval_reason="Refund approval required" if self._requires_approval else None,
            approval_preview=preview if self._requires_approval else None,
            tool_records=[
                ToolExecutionRecord(
                    tool_name="draft_refund_request",
                    status="approval_required" if self._requires_approval else "succeeded",
                    tool_invocation_id=invocation.id,
                    output=None if self._requires_approval else {"ok": True},
                    requires_approval=self._requires_approval,
                    preview_payload=preview if self._requires_approval else None,
                )
            ],
        )


def build_engine(session, *, requires_approval: bool) -> tuple[OrchestratorEngine, RunRepository, ApprovalRepository, InMemoryRuntimeController]:
    run_repository = RunRepository(session)
    approval_repository = ApprovalRepository(session)
    invocation_repository = ToolInvocationRepository(session)
    runtime_controller = InMemoryRuntimeController()
    engine = OrchestratorEngine(
        run_store=run_repository,
        approval_store=approval_repository,
        ai_gateway=IntegrationGateway(),
        retrieval_service=IntegrationRetrievalService(),
        tool_executor=IntegrationToolExecutor(invocation_repository, requires_approval=requires_approval),
        trace_recorder=TraceRecorder(run_repository),
        runtime_hooks=runtime_controller,
    )
    return engine, run_repository, approval_repository, runtime_controller


def make_task(run_id) -> AgentTask:
    return AgentTask(
        run_id=run_id,
        workflow_key="support.ticket",
        user_input="Handle refund request",
        tenant_id="tenant-1",
        requested_by="operator@example.com",
    )


def test_risky_tool_path_creates_approval_and_pauses_run(session) -> None:
    engine, run_repository, approval_repository, runtime_controller = build_engine(session, requires_approval=True)
    run = run_repository.create_run(workflow_key="support.ticket", requested_by="operator@example.com")

    context = engine.start_run(make_task(run.id))

    approval = approval_repository.get_approval_request(context.approval_request_id)
    assert context.state is RunState.WAITING_FOR_APPROVAL
    assert approval is not None
    assert approval.status is ApprovalStatus.PENDING
    assert approval.tool_invocation_id is not None
    assert approval.action_preview == {"action": "draft_refund_request", "amount": 42.5}
    assert runtime_controller.get_waiting_context(run.id) is not None
    assert run_repository.get_run(run.id).status is RunStatus.WAITING_FOR_APPROVAL


def test_approval_resolution_appends_event_and_resumes_run(session) -> None:
    engine, run_repository, approval_repository, runtime_controller = build_engine(session, requires_approval=True)
    run = run_repository.create_run(workflow_key="support.ticket")

    waiting = engine.start_run(make_task(run.id))
    approval_repository.resolve_approval_request(waiting.approval_request_id, status=ApprovalStatus.APPROVED)

    resumed = engine.resume_after_approval(runtime_controller.get_waiting_context(run.id))

    assert resumed.state is RunState.COMPLETED
    event_types = [event.event_type for event in run_repository.list_run_events(run.id)]
    assert TraceEventType.APPROVAL_RESOLVED.value in event_types
    assert run_repository.get_run(run.id).status is RunStatus.COMPLETED


def test_rejection_appends_event_and_terminates_cleanly(session) -> None:
    engine, run_repository, approval_repository, runtime_controller = build_engine(session, requires_approval=True)
    run = run_repository.create_run(workflow_key="support.ticket")

    waiting = engine.start_run(make_task(run.id))
    approval_repository.resolve_approval_request(waiting.approval_request_id, status=ApprovalStatus.REJECTED)

    resumed = engine.resume_after_approval(runtime_controller.get_waiting_context(run.id))

    assert resumed.state is RunState.CANCELED
    assert resumed.failure_reason == "Approval rejected"
    event_types = [event.event_type for event in run_repository.list_run_events(run.id)]
    assert TraceEventType.APPROVAL_RESOLVED.value in event_types
    assert run_repository.get_run(run.id).status is RunStatus.CANCELED


def test_trace_timeline_includes_ordered_whole_lifecycle(session) -> None:
    engine, run_repository, approval_repository, runtime_controller = build_engine(session, requires_approval=True)
    run = run_repository.create_run(workflow_key="support.ticket")

    waiting = engine.start_run(make_task(run.id))
    approval_repository.resolve_approval_request(waiting.approval_request_id, status=ApprovalStatus.APPROVED)
    engine.resume_after_approval(runtime_controller.get_waiting_context(run.id))

    timeline = TimelineBuilder().build(
        run.id,
        [
            TraceEventRecord(
                run_id=event.run_id,
                sequence=event.sequence,
                event_type=TraceEventType(event.event_type),
                payload=event.payload,
                created_at=event.created_at,
            )
            for event in run_repository.list_run_events(run.id)
        ],
    )

    assert timeline.event_count >= 6
    assert [entry.sequence for entry in timeline.events] == sorted(entry.sequence for entry in timeline.events)
    assert timeline.events[0].event_type is TraceEventType.RUN_STARTED
    assert timeline.events[-1].event_type is TraceEventType.RUN_COMPLETED


def test_invalid_approval_resolution_states_are_rejected_safely(session) -> None:
    _, run_repository, approval_repository, _ = build_engine(session, requires_approval=True)
    run = run_repository.create_run(workflow_key="support.ticket")
    approval = approval_repository.create_approval_request(
        run_id=run.id,
        reason="Need approval",
        action_preview={"action": "draft"},
        tool_invocation_id=uuid4(),
    )
    approval_repository.resolve_approval_request(approval.id, status=ApprovalStatus.APPROVED)

    with pytest.raises(ValueError):
        approval_repository.resolve_approval_request(approval.id, status=ApprovalStatus.REJECTED)
