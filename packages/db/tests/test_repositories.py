"""Repository behavior tests for the db package."""

from __future__ import annotations

from decimal import Decimal

from db.enums import ApprovalStatus, EvalResultStatus, EvalRunStatus, RunStatus
from db.models import EvalCase
from db.repositories import ApprovalRepository, EvalRepository, RunRepository


def test_run_repository_creates_and_updates_runs(session) -> None:
    repository = RunRepository(session)

    run = repository.create_run(
        workflow_key="support.ticket",
        requested_by="operator@example.com",
        input_payload={"ticket_id": "T-100"},
    )
    event_one = repository.append_run_event(
        run_id=run.id,
        event_type="run.created",
        payload={"status": run.status.value},
    )
    event_two = repository.append_run_event(run_id=run.id, event_type="run.started")
    updated_run = repository.update_run_status(run.id, status=RunStatus.IN_PROGRESS)

    session.commit()

    fetched_run = repository.get_run(run.id)
    assert fetched_run is not None
    assert fetched_run.requested_by == "operator@example.com"
    assert fetched_run.status is RunStatus.IN_PROGRESS
    assert updated_run is not None
    assert updated_run.started_at is not None
    assert event_one.sequence == 1
    assert event_two.sequence == 2


def test_approval_repository_creates_and_resolves_requests(session) -> None:
    run_repository = RunRepository(session)
    approval_repository = ApprovalRepository(session)

    run = run_repository.create_run(workflow_key="ops.change")
    approval_request = approval_repository.create_approval_request(
        run_id=run.id,
        reason="Production change",
        preview_payload={"action": "restart"},
    )
    resolved_request = approval_repository.resolve_approval_request(
        approval_request.id,
        status=ApprovalStatus.APPROVED,
        decision_comment="Approved by reviewer",
    )

    session.commit()

    assert approval_request.status is ApprovalStatus.APPROVED
    assert resolved_request is not None
    assert resolved_request.resolved_at is not None
    assert resolved_request.decision_comment == "Approved by reviewer"


def test_eval_repository_creates_runs_and_results(session) -> None:
    eval_repository = EvalRepository(session)

    eval_case = EvalCase(
        key="grounded-answer",
        input_text="How do I reset a ticket?",
        expected_behavior="Provide grounded reset steps.",
    )
    session.add(eval_case)
    session.flush()

    eval_run = eval_repository.create_eval_run(
        name="smoke-suite",
        model_name="gpt-x",
        status=EvalRunStatus.IN_PROGRESS,
    )
    eval_result = eval_repository.store_eval_result(
        eval_run_id=eval_run.id,
        eval_case_id=eval_case.id,
        status=EvalResultStatus.PASSED,
        score=Decimal("0.95"),
        summary="Grounded answer with correct behavior.",
        details={"citations": 2},
    )

    session.commit()

    assert eval_run.status is EvalRunStatus.IN_PROGRESS
    assert eval_run.started_at is not None
    assert eval_result.score == Decimal("0.95")
    assert eval_result.summary == "Grounded answer with correct behavior."
