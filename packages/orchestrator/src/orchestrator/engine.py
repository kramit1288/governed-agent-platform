"""Explicit run lifecycle engine for the single-agent orchestrator."""

from __future__ import annotations

from uuid import UUID

from orchestrator.errors import ApprovalResolutionError
from orchestrator.interfaces import AIGateway, ApprovalStore, RetrievalService, RunStore, RuntimeResumeHooks, ToolExecutor, TraceRecorder
from orchestrator.models import ApprovalDecision, AgentTask, RunContext, RunState, RunStep
from orchestrator.response_builder import ResponseBuilder
from orchestrator.state_machine import OrchestratorStateMachine


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

    def start_run(self, task: AgentTask) -> RunContext:
        """Start a run and advance it until it completes, pauses, or fails."""
        context = RunContext(task=task)
        return self._execute(context)

    def resume_after_approval(self, context: RunContext) -> RunContext:
        """Resume a waiting run after checking the persisted approval decision."""
        if context.state is not RunState.WAITING_FOR_APPROVAL or context.approval_request_id is None:
            raise ApprovalResolutionError("Run is not waiting on an approval request")

        decision = self._approval_store.get_approval_decision(context.approval_request_id)
        if decision is ApprovalDecision.PENDING:
            raise ApprovalResolutionError("Approval request is still pending")

        if decision is not ApprovalDecision.APPROVED:
            return self._fail_run(context, f"Approval {decision.value.lower()}")

        self._transition_state(context, RunState.IN_PROGRESS, "run.resumed", {"approval_request_id": str(context.approval_request_id)})
        self._runtime_hooks.on_run_resumed(context.task.run_id)
        context.current_step = RunStep.GENERATE_RESPONSE
        return self._execute(context)

    def _execute(self, context: RunContext) -> RunContext:
        try:
            if context.state is RunState.PENDING:
                self._transition_state(context, RunState.IN_PROGRESS, "run.started", None)

            while context.state is RunState.IN_PROGRESS:
                step = context.current_step or self._state_machine.next_step(None)
                context.current_step = step
                self._record_event(context, "step.started", {"step": step.value})

                if step is RunStep.CLASSIFY:
                    context.classification = self._ai_gateway.classify(context.task)
                    self._record_event(context, "step.completed", {"step": step.value, "classification": context.classification})
                    context.current_step = self._state_machine.next_step(step)
                    continue

                if step is RunStep.RETRIEVE_CONTEXT:
                    context.retrieved_context = self._retrieval_service.retrieve(
                        context.task,
                        context.classification or "unclassified",
                    )
                    self._record_event(context, "step.completed", {"step": step.value, "documents": len(context.retrieved_context)})
                    context.current_step = self._state_machine.next_step(step)
                    continue

                if step is RunStep.DECIDE_TOOLS:
                    context.planned_tools = self._tool_executor.plan_tools(context)
                    self._record_event(context, "step.completed", {"step": step.value, "tool_count": len(context.planned_tools)})
                    context.current_step = self._state_machine.next_step(step)
                    continue

                if step is RunStep.EXECUTE_TOOLS:
                    execution_result = self._tool_executor.execute_tools(context)
                    context.tool_results = execution_result.outputs
                    self._record_event(context, "step.completed", {"step": step.value, "result_count": len(context.tool_results)})
                    if execution_result.requires_approval:
                        context.current_step = RunStep.REQUEST_APPROVAL_IF_NEEDED
                        context = self._request_approval(context, execution_result.approval_reason, execution_result.approval_preview)
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
                    context.response_text = self._response_builder.build(context)
                    self._record_event(context, "step.completed", {"step": step.value})
                    context.current_step = self._state_machine.next_step(step)
                    continue

                if step is RunStep.COMPLETE:
                    self._transition_state(context, RunState.COMPLETED, "run.completed", {"step": step.value})
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
        approval_request = self._approval_store.create_approval_request(
            run_id=context.task.run_id,
            reason=reason or "Approval required",
            preview_payload=preview_payload,
        )
        approval_request_id = self._extract_id(approval_request)
        context.approval_request_id = approval_request_id
        self._transition_state(
            context,
            RunState.WAITING_FOR_APPROVAL,
            "run.waiting_for_approval",
            {"approval_request_id": str(approval_request_id)},
        )
        self._runtime_hooks.on_waiting_for_approval(context.task.run_id, approval_request_id)
        return context

    def _fail_run(self, context: RunContext, reason: str) -> RunContext:
        if context.state not in {RunState.COMPLETED, RunState.FAILED, RunState.CANCELED}:
            self._transition_state(context, RunState.FAILED, "run.failed", {"error": reason}, last_error=reason)
            self._runtime_hooks.on_run_completed(context.task.run_id, context.state)
        context.failure_reason = reason
        return context

    def _transition_state(
        self,
        context: RunContext,
        target: RunState,
        event_type: str,
        payload: dict[str, object] | None,
        *,
        last_error: str | None = None,
    ) -> None:
        previous_state = context.state
        context.state = self._state_machine.transition_state(context.state, target)
        state_payload = {
            "from_state": previous_state.value,
            "to_state": target.value,
        }
        if payload:
            state_payload.update(payload)
        self._run_store.update_run_status(
            context.task.run_id,
            status=target.value,
            last_error=last_error,
        )
        self._record_event(context, event_type, state_payload)

    def _record_event(
        self,
        context: RunContext,
        event_type: str,
        payload: dict[str, object] | None,
    ) -> None:
        self._run_store.append_run_event(
            run_id=context.task.run_id,
            event_type=event_type,
            payload=payload,
        )
        self._trace_recorder.record_event(context.task.run_id, event_type, payload)

    @staticmethod
    def _extract_id(record: object) -> UUID:
        approval_request_id = getattr(record, "id", None)
        if not isinstance(approval_request_id, UUID):
            raise ApprovalResolutionError("Approval record did not expose a UUID id")
        return approval_request_id
