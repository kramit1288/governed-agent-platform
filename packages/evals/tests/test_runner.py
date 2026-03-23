"""Unit tests for the offline eval runner and reporting."""

from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from db.base import Base
from db.repositories import EvalRepository
from evals import OfflineEvalRunner, format_report, load_eval_cases
from evals.reports import EvalResult, build_report, compare_reports
from evals.scoring import PlatformEvalOutput, ScoreCard, score_case

ROOT = Path(__file__).resolve().parents[3]
CASES_DIR = ROOT / "packages" / "evals" / "cases"


def build_repository() -> EvalRepository:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    return EvalRepository(Session(engine, expire_on_commit=False))


def test_eval_cases_load_successfully() -> None:
    cases = load_eval_cases(CASES_DIR)

    assert len(cases) >= 10
    assert all(case.version == "v1" for case in cases)


def test_scoring_functions_behave_deterministically() -> None:
    case = load_eval_cases(CASES_DIR)[0]
    output = PlatformEvalOutput(
        response_text="Refunds above 250 dollars require approval. [DOC-100:0]",
        tool_name="search_docs",
        requires_approval=False,
        citations=[{"citation_id": "DOC-100:0"}],
        latency_ms=10,
        estimated_cost_usd=0.0,
    )

    first = score_case(case, output)
    second = score_case(case, output)

    assert first == second
    assert first.total_score >= 0.75


def test_eval_runner_executes_end_to_end_and_persists_results() -> None:
    repository = build_repository()
    runner = OfflineEvalRunner(repository=repository)

    report = runner.run(run_name="smoke-suite", case_directory=CASES_DIR)
    persisted_run = repository.get_latest_completed_run("smoke-suite")

    assert report.total_cases >= 10
    assert persisted_run is not None
    persisted_results = repository.list_eval_results(persisted_run.id)
    assert len(persisted_results) == report.total_cases


def test_reports_summarize_pass_fail_and_score_breakdowns() -> None:
    scorecard = ScoreCard(
        groundedness=1.0,
        tool_choice=1.0,
        approval_trigger=1.0,
        response_usefulness=1.0,
        format_correctness=1.0,
        citation_presence=1.0,
        latency_signal=1.0,
        cost_signal=1.0,
    )
    results = [
        EvalResult(
            case_key="case-a:v1",
            passed=True,
            summary="passed",
            scorecard=scorecard,
            response_text="ok",
            tool_name="search_docs",
            citation_count=1,
            latency_ms=10,
            estimated_cost_usd=0.0,
        )
    ]

    report = build_report("smoke-suite", "v1-deterministic", results)
    rendered = format_report(report)

    assert report.passed_cases == 1
    assert "Average score" in rendered
    assert "groundedness" in rendered


def test_regression_compare_scenario_is_supported() -> None:
    scorecard = ScoreCard(
        groundedness=1.0,
        tool_choice=1.0,
        approval_trigger=1.0,
        response_usefulness=1.0,
        format_correctness=1.0,
        citation_presence=1.0,
        latency_signal=1.0,
        cost_signal=1.0,
    )
    baseline = build_report(
        "smoke-suite",
        "v1",
        [
            EvalResult(
                case_key="case-a:v1",
                passed=True,
                summary="baseline",
                scorecard=scorecard.model_copy(update={"cost_signal": 0.0}),
                response_text="ok",
                tool_name="search_docs",
                citation_count=1,
                latency_ms=10,
                estimated_cost_usd=0.0,
            )
        ],
    )
    current = build_report(
        "smoke-suite",
        "v1",
        [
            EvalResult(
                case_key="case-a:v1",
                passed=True,
                summary="current",
                scorecard=scorecard,
                response_text="ok",
                tool_name="search_docs",
                citation_count=1,
                latency_ms=10,
                estimated_cost_usd=0.0,
            )
        ],
    )

    regression = compare_reports(current, baseline)

    assert regression["improved_cases"] == 1
    assert regression["regressed_cases"] == 0
