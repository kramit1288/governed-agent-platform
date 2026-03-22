"""Explicit run lifecycle engine for the single-agent orchestrator."""

from __future__ import annotations

from uuid import UUID

from orchestrator.approval import ApprovalCoordinator
from orchestrator.errors import ApprovalResolutionError
from orchestrator.interfaces import AIGateway, ApprovalStore, RetrievalService, RunStore, RuntimeResumeHooks, ToolExecutor, TraceRecorder
from orchestrator.models import ApprovalDecision, AgentTask, RunContext, RunState, RunStep, ToolExecutionRecord
from orchestrator.response_builder import ResponseBuilder
from orchestrator.state_machine import OrchestratorStateMachine
from tracing.events import (
    ModelSelectedPayload,
    RetrievalCompletedPayload,
    RunCompletedPayload,
    RunFailedPayload,
    RunStartedPayload,
    ToolCalledPayload,
    ToolResultReceivedPayload,
    TraceEventType,
)


class OrchestratorEngine:
    """Own the explicit run lifecycle for V1 single-agent orchestration."""

    def __init__(
        self,
        *,
        run_store: RunStore,
        approval_store: ApprovalStore,
        ai_gateway: AIGateway,
        retrieval_service: RetrievalService,
        tool_executor: ToolExecutor,
        trace_recorder: TraceRecorder,
        runtime_hooks: RuntimeResumeHooks,
        state_machine: OrchestratorStateMachine | None = None,
        response_builder: ResponseBuilder | None = None,
    ) -> None:
        self._run_store = run_store
        self._approval_store = approval_store
        self._ai_gateway = ai_gateway
        self._retrieval_service = retrieval_service
        self._tool_executor = tool_executor
        self._trace_recorder = trace_recorder
        self._runtime_hooks = runtime_hooks
        self._state_machine = state_machine or OrchestratorStateMachine()
        self._response_builder = response_builder or ResponseBuilder(ai_gateway)
        self._approval_coordinator = ApprovalCoordinator(
            approval_store=approval_store,
            trace_recorder=trace_recorder,
        )

    def start_run(self, task: AgentTask) -> RunContext:
        """Start a run and advance it until it completes, pauses, or fails."""
        context = RunContext(task=task)
        return self._execute(context)

    def resume_after_approval(self, context: RunContext, *, record_resolution_event: bool = True) -> RunContext:
        """Resume a waiting run after checking the persisted approval decision."""
        if context.state is not RunState.WAITING_FOR_APPROVAL or context.approval_request_id is None:
            raise ApprovalResolutionError("Run is not waiting on an approval request")

        raw_decision = self._approval_store.get_approval_decision(context.approval_request_id)
        decision = ApprovalDecision(getattr(raw_decision, "value", raw_decision))
        if decision is ApprovalDecision.PENDING:
            raise ApprovalResolutionError("Approval request is still pending")

        if record_resolution_event:
            self._approval_coordinator.record_resolution(
                run_id=context.task.run_id,
                approval_request_id=context.approval_request_id,
                decision=decision,
                decision_comment=self._extract_decision_comment(context.approval_request_id),
            )

        if decision is not ApprovalDecision.APPROVED:
            return self._cancel_run(context, f"Approval {decision.value.lower()}")

        self._transition_state(context, RunState.IN_PROGRESS, None, None)
        self._runtime_hooks.on_run_resumed(context.task.run_id)
        context.current_step = RunStep.GENERATE_RESPONSE
        return self._execute(context)

    def _execute(self, context: RunContext) -> RunContext:
        try:
            if context.state is RunState.PENDING:
                self._transition_state(
                    context,
                    RunState.IN_PROGRESS,
                    TraceEventType.RUN_STARTED.value,
                    RunStartedPayload(
                        workflow_key=context.task.workflow_key,
                        tenant_id=context.task.tenant_id,
                    ),
                )

            while context.state is RunState.IN_PROGRESS:
                step = context.current_step or self._state_machine.next_step(None)
                context.current_step = step

                if step is RunStep.CLASSIFY:
                    context.classification = self._ai_gateway.classify(context.task)
                    context.current_step = self._state_machine.next_step(step)
                    continue

                if step is RunStep.RETRIEVE_CONTEXT:
                    context.retrieved_context = self._retrieval_service.retrieve(
                        context.task,
                        context.classification or "unclassified",
                    )
                    self._record_event(
                        context,
                        TraceEventType.RETRIEVAL_COMPLETED.value,
                        RetrievalCompletedPayload(
                            classification=context.classification or "unclassified",
                            document_count=len(context.retrieved_context),
                        ),
                    )
                    context.current_step = self._state_machine.next_step(step)
                    continue

                if step is RunStep.DECIDE_TOOLS:
                    context.planned_tools = self._tool_executor.plan_tools(context)
                    context.current_step = self._state_machine.next_step(step)
                    continue

                if step is RunStep.EXECUTE_TOOLS:
                    for tool_call in context.planned_tools:
                        self._record_event(
                            context,
                            TraceEventType.TOOL_CALLED.value,
                            ToolCalledPayload(
                                tool_name=tool_call.name,
                                tool_invocation_id=None,
                                requires_approval=tool_call.requires_approval,
                            ),
                        )
                    execution_result = self._tool_executor.execute_tools(context)
                    context.tool_results = execution_result.outputs
                    context.tool_records = execution_result.tool_records or self._derive_tool_records(context)
                    for record in context.tool_records:
                        self._record_event(
                            context,
                            TraceEventType.TOOL_RESULT_RECEIVED.value,
                            ToolResultReceivedPayload(
                                tool_name=record.tool_name,
                                tool_invocation_id=str(record.tool_invocation_id)
                                if record.tool_invocation_id is not None
                                else None,
                                status=record.status,
                                requires_approval=record.requires_approval,
                            ),
                        )
                    if execution_result.requires_approval:
                        context.current_step = RunStep.REQUEST_APPROVAL_IF_NEEDED
                        context = self._request_approval(
                            context,
                            execution_result.approval_reason,
                            execution_result.approval_preview,
                        )
                        if context.state is RunState.WAITING_FOR_APPROVAL:
                            return context
                        continue
                    context.current_step = RunStep.GENERATE_RESPONSE
                    continue

                if step is RunStep.REQUEST_APPROVAL_IF_NEEDED:
                    context = self._request_approval(context, "Approval required", None)
                    if context.state is RunState.WAITING_FOR_APPROVAL:
                        return context
                    continue

                if step is RunStep.GENERATE_RESPONSE:
                    route_payload = self._describe_route(context)
                    if route_payload is not None:
                        self._record_event(
                            context,
                            TraceEventType.MODEL_SELECTED.value,
                            ModelSelectedPayload(
                                provider=str(route_payload.get("provider", "unknown")),
                                model=str(route_payload.get("model", "unknown")),
                                reason=(
                                    str(route_payload["reason"])
                                    if route_payload.get("reason") is not None
                                    else None
                                ),
                            ),
                        )
                    context.response_text = self._response_builder.build(context)
                    context.current_step = self._state_machine.next_step(step)
                    continue

                if step is RunStep.COMPLETE:
                    self._transition_state(
                        context,
                        RunState.COMPLETED,
                        TraceEventType.RUN_COMPLETED.value,
                        RunCompletedPayload(
                            final_state=RunState.COMPLETED.value,
                            response_text=context.response_text,
                        ),
                    )
                    self._runtime_hooks.on_run_completed(context.task.run_id, context.state)
                    return context

            return context
        except Exception as error:
            return self._fail_run(context, str(error))

    def _request_approval(
        self,
        context: RunContext,
        reason: str | None,
        preview_payload: dict[str, object] | None,
    ) -> RunContext:
        pending_record = next((record for record in context.tool_records if record.requires_approval), None)
        context.pending_tool_invocation_id = pending_record.tool_invocation_id if pending_record is not None else None
        action_preview = (
            pending_record.preview_payload if pending_record is not None and pending_record.preview_payload is not None else preview_payload
        )
        approval_request_id = self._approval_coordinator.request_approval(
            context=context,
            reason=reason or "Approval required",
            action_preview=action_preview,
            tool_invocation_id=context.pending_tool_invocation_id,
        )
        context.approval_request_id = approval_request_id
        self._transition_state(context, RunState.WAITING_FOR_APPROVAL, None, None)
        self._runtime_hooks.store_waiting_context(context)
        self._runtime_hooks.on_waiting_for_approval(context.task.run_id, approval_request_id)
        return context

    def _cancel_run(self, context: RunContext, reason: str) -> RunContext:
        if context.state not in {RunState.COMPLETED, RunState.FAILED, RunState.CANCELED}:
            self._transition_state(
                context,
                RunState.CANCELED,
                TraceEventType.RUN_COMPLETED.value,
                RunCompletedPayload(
                    final_state=RunState.CANCELED.value,
                    response_text=reason,
                ),
            )
            self._runtime_hooks.on_run_completed(context.task.run_id, context.state)
        context.failure_reason = reason
        return context

    def _fail_run(self, context: RunContext, reason: str) -> RunContext:
        if context.state not in {RunState.COMPLETED, RunState.FAILED, RunState.CANCELED}:
            self._transition_state(
                context,
                RunState.FAILED,
                TraceEventType.RUN_FAILED.value,
                RunFailedPayload(error=reason),
                last_error=reason,
            )
            self._runtime_hooks.on_run_completed(context.task.run_id, context.state)
        context.failure_reason = reason
        return context

    def _transition_state(
        self,
        context: RunContext,
        target: RunState,
        event_type: str | None,
        payload: object | None,
        *,
        last_error: str | None = None,
    ) -> None:
        context.state = self._state_machine.transition_state(context.state, target)
        self._run_store.update_run_status(
            context.task.run_id,
            status=target.value,
            last_error=last_error,
        )
        if event_type is not None:
            self._record_event(context, event_type, payload)

    def _record_event(
        self,
        context: RunContext,
        event_type: str,
        payload: object | None,
    ) -> None:
        self._trace_recorder.record_event(context.task.run_id, event_type, payload)

    def _extract_decision_comment(self, approval_request_id: UUID) -> str | None:
        approval_request = self._approval_store.get_approval_request(approval_request_id)
        return getattr(approval_request, "decision_comment", None)

    def _derive_tool_records(self, context: RunContext) -> list[ToolExecutionRecord]:
        records: list[ToolExecutionRecord] = []
        for index, output in enumerate(context.tool_results):
            tool_name = context.planned_tools[index].name if index < len(context.planned_tools) else "tool"
            records.append(ToolExecutionRecord(tool_name=tool_name, status="succeeded", output=output))
        return records

    def _describe_route(self, context: RunContext) -> dict[str, object] | None:
        describe_route = getattr(self._ai_gateway, "describe_route", None)
        if callable(describe_route):
            return describe_route(context)
        return None
