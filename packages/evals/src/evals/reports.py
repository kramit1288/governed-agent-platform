"""Summary and regression reporting for offline eval runs."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from evals.scoring import ScoreCard


class EvalResult(BaseModel):
    """Eval result record returned by the runner."""

    model_config = ConfigDict(extra="forbid")

    case_key: str
    passed: bool
    summary: str
    scorecard: ScoreCard
    response_text: str
    tool_name: str | None = None
    requires_approval: bool = False
    citation_count: int = Field(ge=0)
    latency_ms: int = Field(ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)


class EvalRun(BaseModel):
    """Eval run summary returned by the runner."""

    model_config = ConfigDict(extra="forbid")

    eval_run_id: str | None = None
    run_name: str
    model_name: str | None = None
    total_cases: int = Field(ge=0)
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    average_score: float = Field(ge=0.0, le=1.0)
    dimension_averages: dict[str, float] = Field(default_factory=dict)
    results: list[EvalResult] = Field(default_factory=list)
    regression: dict[str, object] | None = None


def build_report(run_name: str, model_name: str | None, results: list[EvalResult]) -> EvalRun:
    """Build a readable aggregate report from eval results."""

    total_cases = len(results)
    passed_cases = sum(1 for result in results if result.passed)
    failed_cases = total_cases - passed_cases
    average_score = sum(result.scorecard.total_score for result in results) / total_cases if results else 0.0
    dimension_averages = _dimension_averages(results)
    return EvalRun(
        run_name=run_name,
        model_name=model_name,
        total_cases=total_cases,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        average_score=average_score,
        dimension_averages=dimension_averages,
        results=results,
    )


def compare_reports(current: EvalRun, baseline: EvalRun) -> dict[str, object]:
    """Compare two reports for simple regression visibility."""

    baseline_scores = {result.case_key: result.scorecard.total_score for result in baseline.results}
    improved = 0
    regressed = 0
    unchanged = 0
    for result in current.results:
        baseline_score = baseline_scores.get(result.case_key)
        if baseline_score is None:
            continue
        if result.scorecard.total_score > baseline_score:
            improved += 1
        elif result.scorecard.total_score < baseline_score:
            regressed += 1
        else:
            unchanged += 1
    return {
        "baseline_run": baseline.run_name,
        "score_delta": round(current.average_score - baseline.average_score, 4),
        "pass_delta": current.passed_cases - baseline.passed_cases,
        "improved_cases": improved,
        "regressed_cases": regressed,
        "unchanged_cases": unchanged,
    }


def format_report(report: EvalRun) -> str:
    """Render a compact CLI-friendly report."""

    lines = [
        f"Eval run: {report.run_name}",
        f"Model: {report.model_name or 'unknown'}",
        f"Cases: {report.total_cases} | Passed: {report.passed_cases} | Failed: {report.failed_cases}",
        f"Average score: {report.average_score:.3f}",
    ]
    for dimension, score in sorted(report.dimension_averages.items()):
        lines.append(f"- {dimension}: {score:.3f}")
    if report.regression is not None:
        lines.append(f"Regression delta: {report.regression}")
    return "\n".join(lines)


def _dimension_averages(results: list[EvalResult]) -> dict[str, float]:
    if not results:
        return {}
    dimensions = [
        "groundedness",
        "tool_choice",
        "approval_trigger",
        "response_usefulness",
        "format_correctness",
        "citation_presence",
        "latency_signal",
        "cost_signal",
    ]
    return {
        dimension: sum(getattr(result.scorecard, dimension) for result in results) / len(results)
        for dimension in dimensions
    }
