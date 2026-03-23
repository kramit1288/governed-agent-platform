"""Small composition layer for the end-to-end V1 demo API."""

from __future__ import annotations

import re
from uuid import UUID, uuid4

from sqlalchemy.orm import Session

from db.enums import EvalResultStatus
from db.repositories import ApprovalRepository, EvalRepository, RunRepository
from evals import EvalResult as EvalReportResult
from evals import EvalRun as EvalReport
from evals import OfflineEvalRunner, ScoreCard, build_report
from orchestrator import (
    AgentTask,
    OrchestratorEngine,
    RetrievedContext,
    RunContext,
    RunState,
    ToolCall,
    ToolExecutionRecord,
    ToolExecutionResult,
)
from retrieval import RetrievalFilter, RetrievalService
from runtime import InMemoryRuntimeController
from tools import ToolExecutor as SingleToolExecutor, ToolRegistry
from tools.schemas import ToolCall as RegistryToolCall
from tracing import TraceRecorder, TraceEventRecord, TraceEventType

from apps.api.app.models import RunCreateRequest, RunResponse


class DemoGateway:
    """Deterministic gateway behavior for the V1 demo surface."""

    def classify(self, task: AgentTask) -> str:
        if "refund" in task.user_input.lower():
            return "action_request"
        return "grounded_answer"

    def generate_response(self, context: RunContext) -> str:
        if context.state is RunState.CANCELED:
            return context.failure_reason or "Run canceled."
        if context.tool_records and any(record.requires_approval for record in context.tool_records):
            if context.approval_request_id is not None and context.state is RunState.IN_PROGRESS:
                return "Refund request approved. V1 keeps the action as a non-executed preview for safety."
            return "Approval required before the proposed refund action can proceed."
        if context.tool_results:
            first = context.tool_results[0]
            if "ticket" in first:
                ticket = first["ticket"]
                return f"Ticket {ticket['ticket_id']}: {ticket['subject']} ({ticket['status']})."
            if "incident" in first:
                incident = first["incident"]
                return f"Incident {incident['incident_id']}: {incident['title']} ({incident['status']})."
            if "customer" in first:
                customer = first["customer"]
                return f"Customer {customer['customer_id']}: {customer['name']} on {customer['plan']}."
        if context.retrieved_context:
            top = context.retrieved_context[0]
            return f"{top.content} [{top.source_id}]"
        return "No grounded response available."

    def describe_route(self, context: RunContext) -> dict[str, object]:
        if context.classification == "action_request":
            return {"provider": "openai", "model": "gpt-4.1", "reason": "approval-sensitive path"}
        return {"provider": "openai", "model": "gpt-4.1-mini", "reason": "grounded support answer"}


class DemoRetrievalService:
    """Retrieval adapter for orchestrator-facing grounded context lookup."""

    def __init__(self) -> None:
        self._retrieval = RetrievalService.from_seed_data()

    def retrieve(self, task: AgentTask, _classification: str) -> list[RetrievedContext]:
        chunks, _ = self._retrieval.search(
            query=task.user_input,
            retrieval_filter=RetrievalFilter(
                tenant_id=task.tenant_id,
                source_type="support_doc",
                top_k=2,
            ),
        )
        return [
            RetrievedContext(source_id=f"{chunk.source_id}:{chunk.chunk_index}", content=chunk.content[:200])
            for chunk in chunks
        ]


class DemoToolExecutor:
    """Orchestrator-facing tool adapter built on the explicit tools package."""

    def __init__(self) -> None:
        self._registry = ToolRegistry()
        self._executor = SingleToolExecutor(self._registry)

    def plan_tools(self, context: RunContext) -> list[ToolCall]:
        text = context.task.user_input.lower()
        if ("draft" in text or "submit" in text or "approve" in text) and "refund" in text:
            return [
                ToolCall(
                    name="draft_refund_request",
                    requires_approval=True,
                    arguments=self._arguments_for(context, "draft_refund_request"),
                )
            ]
        ticket_match = re.search(r"(T-\d+)", context.task.user_input, re.IGNORECASE)
        if ticket_match is not None:
            return [
                ToolCall(
                    name="get_ticket",
                    arguments=self._arguments_for(
                        context,
                        "get_ticket",
                        ticket_id=ticket_match.group(1).upper(),
                    ),
                )
            ]
        incident_match = re.search(r"(INC-\d+)", context.task.user_input, re.IGNORECASE)
        if incident_match is not None:
            return [
                ToolCall(
                    name="get_incident",
                    arguments=self._arguments_for(
                        context,
                        "get_incident",
                        incident_id=incident_match.group(1).upper(),
                    ),
                )
            ]
        customer_match = re.search(r"(C-\d+)", context.task.user_input, re.IGNORECASE)
        if customer_match is not None and "customer" in text:
            return [
                ToolCall(
                    name="get_customer",
                    arguments=self._arguments_for(
                        context,
                        "get_customer",
                        customer_id=customer_match.group(1).upper(),
                    ),
                )
            ]
        return []

    def execute_tools(self, context: RunContext) -> ToolExecutionResult:
        outputs: list[dict[str, object]] = []
        records: list[ToolExecutionRecord] = []
        for planned_tool in context.planned_tools:
            result = self._executor.execute(
                RegistryToolCall(
                    name=planned_tool.name,
                    arguments=planned_tool.arguments,
                    requested_by=context.task.requested_by,
                )
            )
            if result.output is not None:
                outputs.append(result.output)
            invocation_id = uuid4()
            records.append(
                ToolExecutionRecord(
                    tool_name=planned_tool.name,
                    status=result.status.value,
                    tool_invocation_id=invocation_id,
                    output=result.output,
                    error=result.error,
                    requires_approval=result.requires_approval,
                    preview_payload=result.preview_payload,
                )
            )
            if result.requires_approval:
                return ToolExecutionResult(
                    outputs=outputs,
                    requires_approval=True,
                    approval_reason=f"Approval required for {planned_tool.name}",
                    approval_preview=result.preview_payload,
                    tool_records=records,
                )
        return ToolExecutionResult(outputs=outputs, tool_records=records)

    @staticmethod
    def _arguments_for(
        context: RunContext,
        tool_name: str,
        **overrides: object,
    ) -> dict[str, object]:
        defaults: dict[str, object] = {"tenant_id": context.task.tenant_id}
        if tool_name == "draft_refund_request":
            defaults.update(
                {
                    "customer_id": "C-100",
                    "ticket_id": "T-100",
                    "amount": 42.5,
                    "reason": "Duplicate charge confirmed",
                }
            )
        defaults.update(overrides)
        return defaults


class DemoPlatformService:
    """Thin API-facing service for runs, traces, approvals, and evals."""

    def __init__(self, *, session: Session, runtime_controller: InMemoryRuntimeController) -> None:
        self._session = session
        self._run_repository = RunRepository(session)
        self._approval_repository = ApprovalRepository(session)
        self._eval_repository = EvalRepository(session)
        self._runtime_controller = runtime_controller

    def start_run(self, request: RunCreateRequest) -> RunResponse:
        run = self._run_repository.create_run(
            workflow_key=request.workflow_key,
            requested_by=request.requested_by,
            input_payload={"user_input": request.user_input, "tenant_id": request.tenant_id},
        )
        task = AgentTask(
            run_id=run.id,
            workflow_key=request.workflow_key,
            user_input=request.user_input,
            tenant_id=request.tenant_id,
            requested_by=request.requested_by,
        )
        engine = self._build_engine()
        context = engine.start_run(task)
        self._session.commit()
        return self.get_run(run.id, context_override=context)

    def get_run(self, run_id: UUID, *, context_override: RunContext | None = None) -> RunResponse:
        run = self._run_repository.get_run(run_id)
        if run is None:
            raise LookupError("Run not found.")
        latest_approval = self._approval_repository.get_latest_for_run(run_id)
        response_text = _extract_response_text(self._run_repository.list_run_events(run_id))
        if context_override is not None and context_override.response_text is not None:
            response_text = context_override.response_text
        if (
            response_text is None
            and latest_approval is not None
            and latest_approval.status.value == "PENDING"
            and run.status.value == "WAITING_FOR_APPROVAL"
        ):
            response_text = "Approval required before the proposed action can proceed."
        user_input = run.input_payload.get("user_input") if run.input_payload else None
        return RunResponse(
            run_id=str(run.id),
            status=run.status.value,
            workflow_key=run.workflow_key,
            user_input=str(user_input) if user_input is not None else None,
            response_text=response_text,
            last_error=run.last_error,
            approval_request_id=(
                str(latest_approval.id)
                if latest_approval and latest_approval.status.value == "PENDING"
                else None
            ),
        )

    def resume_after_approval(self, approval_id: UUID) -> RunContext | None:
        run_id = self._runtime_controller.get_run_id_for_approval(approval_id)
        if run_id is None:
            return None
        context = self._runtime_controller.get_waiting_context(run_id)
        if context is None:
            return None
        engine = self._build_engine()
        resumed = engine.resume_after_approval(context, record_resolution_event=False)
        self._session.commit()
        return resumed

    def run_evals(self, *, name: str, compare_to_latest: bool) -> EvalReport:
        runner = OfflineEvalRunner(repository=self._eval_repository)
        report = runner.run(run_name=name, compare_to_latest=compare_to_latest)
        self._session.commit()
        return report

    def get_eval_report(self, eval_run_id: UUID) -> EvalReport:
        eval_run = self._eval_repository.get_eval_run(eval_run_id)
        if eval_run is None:
            raise LookupError("Eval run not found.")
        results = [
            EvalReportResult(
                case_key=result.eval_case.key,
                passed=result.status is EvalResultStatus.PASSED,
                summary=result.summary or "",
                scorecard=ScoreCard.model_validate(result.details.get("scorecard", {})),
                response_text=result.details.get("response_text", ""),
                tool_name=result.details.get("tool_name"),
                requires_approval=bool(result.details.get("requires_approval", False)),
                citation_count=int(result.details.get("citation_count", 0)),
                latency_ms=int(result.details.get("latency_ms", 0)),
                estimated_cost_usd=result.details.get("estimated_cost_usd"),
            )
            for result in self._eval_repository.list_eval_results(eval_run_id)
        ]
        return build_report(eval_run.name, eval_run.model_name, results).model_copy(
            update={"eval_run_id": str(eval_run.id)}
        )

    def build_trace_records(self, run_id: UUID) -> list[TraceEventRecord]:
        return [
            TraceEventRecord(
                run_id=event.run_id,
                sequence=event.sequence,
                event_type=TraceEventType(event.event_type),
                payload=event.payload,
                created_at=event.created_at,
            )
            for event in self._run_repository.list_run_events(run_id)
        ]

    def _build_engine(self) -> OrchestratorEngine:
        return OrchestratorEngine(
            run_store=self._run_repository,
            approval_store=self._approval_repository,
            ai_gateway=DemoGateway(),
            retrieval_service=DemoRetrievalService(),
            tool_executor=DemoToolExecutor(),
            trace_recorder=TraceRecorder(self._run_repository),
            runtime_hooks=self._runtime_controller,
        )


def _extract_response_text(events: list[object]) -> str | None:
    for event in reversed(events):
        if getattr(event, "event_type", None) == "RUN_COMPLETED":
            payload = getattr(event, "payload", None) or {}
            response_text = payload.get("response_text")
            if isinstance(response_text, str):
                return response_text
        if getattr(event, "event_type", None) == "RUN_FAILED":
            payload = getattr(event, "payload", None) or {}
            error = payload.get("error")
            if isinstance(error, str):
                return error
    return None
