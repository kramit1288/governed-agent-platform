"""API tests for approval lifecycle and run trace endpoints."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from apps.api.app.main import create_app
from db.base import Base
from db.enums import ApprovalStatus
from db.repositories import ApprovalRepository, RunRepository
from tracing.events import ApprovalResolvedPayload, RunStartedPayload, TraceEventType
from tracing.recorder import TraceRecorder


def build_test_app():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def session_factory():
        return Session(engine, expire_on_commit=False)

    def approval_resume(approval_id):
        with session_factory() as session:
            approval = ApprovalRepository(session).get_approval_request(approval_id)
            return type(
                "ResumeResult",
                (),
                {
                    "state": type("State", (), {"value": "COMPLETED"})(),
                    "response_text": "resumed",
                    "failure_reason": None,
                },
            )()

    app = create_app(session_factory=session_factory, approval_resume=approval_resume)
    return app, session_factory


def test_get_approval_and_trace_endpoints() -> None:
    app, session_factory = build_test_app()
    with session_factory() as session:
        run_repository = RunRepository(session)
        approval_repository = ApprovalRepository(session)
        run = run_repository.create_run(workflow_key="support.ticket")
        TraceRecorder(run_repository).record_event(
            run.id,
            TraceEventType.RUN_STARTED.value,
            RunStartedPayload(workflow_key="support.ticket", tenant_id="tenant-1"),
        )
        approval = approval_repository.create_approval_request(
            run_id=run.id,
            reason="Approval required",
            action_preview={"action": "draft_refund_request"},
        )
        session.commit()

    client = TestClient(app)
    approval_response = client.get(f"/approvals/{approval.id}")
    trace_response = client.get(f"/runs/{run.id}/trace")

    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == ApprovalStatus.PENDING.value
    assert trace_response.status_code == 200
    assert trace_response.json()["event_count"] == 1
    assert trace_response.json()["events"][0]["event_type"] == TraceEventType.RUN_STARTED.value


def test_approve_endpoint_resolves_request() -> None:
    app, session_factory = build_test_app()
    with session_factory() as session:
        run = RunRepository(session).create_run(workflow_key="support.ticket")
        approval = ApprovalRepository(session).create_approval_request(
            run_id=run.id,
            reason="Approval required",
            action_preview={"action": "draft_refund_request"},
        )
        session.commit()

    client = TestClient(app)
    response = client.post(f"/approvals/{approval.id}/approve")

    assert response.status_code == 200
    assert response.json()["status"] == ApprovalStatus.APPROVED.value
    assert response.json()["resume_result"]["run_state"] == "COMPLETED"


def test_reject_endpoint_rejects_duplicate_resolution() -> None:
    app, session_factory = build_test_app()
    with session_factory() as session:
        run = RunRepository(session).create_run(workflow_key="support.ticket")
        approval_repository = ApprovalRepository(session)
        approval = approval_repository.create_approval_request(
            run_id=run.id,
            reason="Approval required",
            action_preview={"action": "draft_refund_request"},
        )
        approval_repository.resolve_approval_request(approval.id, status=ApprovalStatus.REJECTED)
        TraceRecorder(RunRepository(session)).record_event(
            run.id,
            TraceEventType.APPROVAL_RESOLVED.value,
            ApprovalResolvedPayload(
                approval_request_id=str(approval.id),
                status=ApprovalStatus.REJECTED.value,
                decision_comment=None,
            ),
        )
        session.commit()

    client = TestClient(app)
    response = client.post(f"/approvals/{approval.id}/reject")

    assert response.status_code == 409
