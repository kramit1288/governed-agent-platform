"""Offline eval runner for deterministic V1 regression checks."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from time import perf_counter
from typing import Any

from db.enums import EvalResultStatus, EvalRunStatus
from db.repositories import EvalRepository
from tools import ToolCall, ToolExecutor, ToolRegistry

from evals.cases import EvalCase, load_eval_cases
from evals.reports import EvalResult, EvalRun, build_report, compare_reports
from evals.scoring import PlatformEvalOutput, score_case

CASES_DIR = Path(__file__).resolve().parents[2] / "cases"


class OfflineEvalRunner:
    """Load curated cases, execute deterministic platform behavior, and persist results."""

    def __init__(
        self,
        *,
        repository: EvalRepository,
        tool_registry: ToolRegistry | None = None,
        tool_executor: ToolExecutor | None = None,
    ) -> None:
        self._repository = repository
        self._tool_registry = tool_registry or ToolRegistry()
        self._tool_executor = tool_executor or ToolExecutor(self._tool_registry)

    def run(
        self,
        *,
        run_name: str,
        model_name: str = "v1-deterministic",
        case_directory: Path = CASES_DIR,
        compare_to_latest: bool = False,
    ) -> EvalRun:
        """Execute eval cases, persist results, and return a summary report."""

        cases = load_eval_cases(case_directory)
        baseline_report = self._load_baseline(run_name) if compare_to_latest else None
        persisted_run = self._repository.create_eval_run(
            name=run_name,
            model_name=model_name,
            status=EvalRunStatus.IN_PROGRESS,
        )

        results: list[EvalResult] = []
        try:
            for case in cases:
                persisted_case = self._repository.get_or_create_eval_case(
                    key=case.persisted_key,
                    input_text=case.input_text,
                    description=case.description,
                    expected_behavior=str(case.expectation.model_dump(mode="json")),
                    tags=case.tags,
                )
                platform_output = self._execute_case(case)
                scorecard = score_case(case, platform_output)
                passed = scorecard.total_score >= 0.75
                summary = _build_case_summary(case, platform_output, passed)
                result = EvalResult(
                    case_key=case.persisted_key,
                    passed=passed,
                    summary=summary,
                    scorecard=scorecard,
                    response_text=platform_output.response_text,
                    tool_name=platform_output.tool_name,
                    requires_approval=platform_output.requires_approval,
                    citation_count=len(platform_output.citations),
                    latency_ms=platform_output.latency_ms,
                    estimated_cost_usd=platform_output.estimated_cost_usd,
                )
                self._repository.store_eval_result(
                    eval_run_id=persisted_run.id,
                    eval_case_id=persisted_case.id,
                    status=EvalResultStatus.PASSED if passed else EvalResultStatus.FAILED,
                    score=Decimal(f"{result.scorecard.total_score:.2f}"),
                    summary=summary,
                    details={
                        "scorecard": result.scorecard.model_dump(mode="json"),
                        "response_text": result.response_text,
                        "tool_name": result.tool_name,
                        "requires_approval": result.requires_approval,
                        "citation_count": result.citation_count,
                        "latency_ms": result.latency_ms,
                        "estimated_cost_usd": result.estimated_cost_usd,
                    },
                )
                results.append(result)
            self._repository.update_eval_run_status(persisted_run.id, status=EvalRunStatus.COMPLETED)
        except Exception:
            self._repository.update_eval_run_status(persisted_run.id, status=EvalRunStatus.FAILED)
            raise

        report = build_report(run_name, model_name, results).model_copy(
            update={"eval_run_id": str(persisted_run.id)}
        )
        if baseline_report is not None:
            report = report.model_copy(update={"regression": compare_reports(report, baseline_report)})
        return report

    def _load_baseline(self, run_name: str) -> EvalRun | None:
        latest = self._repository.get_latest_completed_run(run_name)
        if latest is None:
            return None
        persisted_results = self._repository.list_eval_results(latest.id)
        results = [
            EvalResult(
                case_key=str(result.eval_case.key),
                passed=result.status is EvalResultStatus.PASSED,
                summary=result.summary or "",
                scorecard=ScoreCard.model_validate(result.details["scorecard"]),
                response_text=result.details.get("response_text", ""),
                tool_name=result.details.get("tool_name"),
                requires_approval=bool(result.details.get("requires_approval", False)),
                citation_count=int(result.details.get("citation_count", 0)),
                latency_ms=int(result.details.get("latency_ms", 0)),
                estimated_cost_usd=result.details.get("estimated_cost_usd"),
            )
            for result in persisted_results
        ]
        return build_report(latest.name, latest.model_name, results)

    def _execute_case(self, case: EvalCase) -> PlatformEvalOutput:
        started = perf_counter()
        tool_name = _select_tool(case)
        tool_call = ToolCall(
            name=tool_name,
            arguments=_tool_arguments_for_case(case, tool_name),
        )
        tool_result = self._tool_executor.execute(tool_call)
        latency_ms = int((perf_counter() - started) * 1000)
        response_text, citations = _build_response(case, tool_name, tool_result.output or {}, tool_result.preview_payload)
        return PlatformEvalOutput(
            response_text=response_text,
            tool_name=tool_name,
            requires_approval=tool_result.requires_approval,
            citations=citations,
            latency_ms=latency_ms,
            estimated_cost_usd=0.0,
        )


def _select_tool(case: EvalCase) -> str:
    text = case.input_text.lower()
    if ("draft" in text or "submit" in text or "approve" in text) and "refund" in text:
        return "draft_refund_request"
    if "incident" in text and "incident_id" in case.context:
        return "get_incident"
    if "customer" in text and "customer_id" in case.context and "profile" in text:
        return "get_customer"
    if "ticket" in text and "ticket_id" in case.context:
        return "get_ticket"
    return "search_docs"


def _tool_arguments_for_case(case: EvalCase, tool_name: str) -> dict[str, Any]:
    context = dict(case.context)
    tenant_id = case.tenant_id
    if tool_name == "search_docs":
        return {"query": case.input_text, "tenant_id": tenant_id}
    if tool_name == "get_ticket":
        return {"ticket_id": context["ticket_id"], "tenant_id": tenant_id}
    if tool_name == "get_incident":
        return {"incident_id": context["incident_id"], "tenant_id": tenant_id}
    if tool_name == "get_customer":
        return {"customer_id": context["customer_id"], "tenant_id": tenant_id}
    return {
        "customer_id": context["customer_id"],
        "ticket_id": context["ticket_id"],
        "amount": context["amount"],
        "reason": context["reason"],
        "tenant_id": tenant_id,
    }


def _build_response(
    _case: EvalCase,
    tool_name: str,
    output: dict[str, Any],
    preview_payload: dict[str, Any] | None,
) -> tuple[str, list[dict[str, object]]]:
    if tool_name == "search_docs":
        results = output.get("results", [])
        top = results[0] if results else None
        if top is None:
            return ("No grounded documentation found.", [])
        citation = {"citation_id": f"{top['doc_id']}:0", "source_id": top["doc_id"]}
        response = f"{top['snippet']} [{top['doc_id']}:0]"
        return response, [citation]
    if tool_name == "get_ticket":
        ticket = output["ticket"]
        return (f"Ticket {ticket['ticket_id']}: {ticket['subject']} ({ticket['status']}).", [])
    if tool_name == "get_incident":
        incident = output["incident"]
        return (f"Incident {incident['incident_id']}: {incident['title']} ({incident['status']}).", [])
    if tool_name == "get_customer":
        customer = output["customer"]
        return (f"Customer {customer['customer_id']}: {customer['name']} on {customer['plan']}.", [])
    preview = preview_payload or {}
    response = (
        "Approval required before submitting refund request. "
        f"Prepared draft for {preview.get('customer_id')} on ticket {preview.get('ticket_id')}."
    )
    return response, []


def _build_case_summary(case: EvalCase, output: PlatformEvalOutput, passed: bool) -> str:
    outcome = "passed" if passed else "failed"
    return (
        f"{case.persisted_key} {outcome}: tool={output.tool_name}, "
        f"approval={output.requires_approval}, citations={len(output.citations)}"
    )
