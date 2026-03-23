"""End-to-end API tests for the V1 demo flow."""

from __future__ import annotations

from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from apps.api.app.main import create_app
from db.base import Base
from runtime import InMemoryRuntimeController


def build_test_client() -> TestClient:
    """Create a FastAPI test client backed by an in-memory sqlite database."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def session_factory() -> Session:
        return Session(engine, expire_on_commit=False)

    app = create_app(
        session_factory=session_factory,
        runtime_controller=InMemoryRuntimeController(),
    )
    return TestClient(app)


def test_create_run_and_trace_happy_path() -> None:
    client = build_test_client()

    create_response = client.post(
        "/runs",
        json={
            "workflow_key": "support.ticket",
            "tenant_id": "tenant-1",
            "requested_by": "operator-1",
            "user_input": "Summarize ticket T-100 for me.",
        },
    )

    assert create_response.status_code == 201
    run_payload = create_response.json()
    run_id = run_payload["run_id"]

    assert UUID(run_id)
    assert run_payload["status"] == "COMPLETED"
    assert "Ticket T-100" in run_payload["response_text"]
    assert run_payload["approval_request_id"] is None

    get_response = client.get(f"/runs/{run_id}")
    trace_response = client.get(f"/runs/{run_id}/trace")

    assert get_response.status_code == 200
    assert trace_response.status_code == 200
    assert trace_response.json()["event_count"] >= 5
    event_types = [event["event_type"] for event in trace_response.json()["events"]]
    assert event_types[0] == "RUN_STARTED"
    assert "TOOL_RESULT_RECEIVED" in event_types
    assert event_types[-1] == "RUN_COMPLETED"


def test_approval_flow_can_resume_run_after_approval() -> None:
    client = build_test_client()

    create_response = client.post(
        "/runs",
        json={
            "workflow_key": "support.ticket",
            "tenant_id": "tenant-1",
            "requested_by": "operator-1",
            "user_input": "Draft a refund request for customer C-100 on ticket T-100 for 42.50.",
        },
    )

    assert create_response.status_code == 201
    run_payload = create_response.json()
    run_id = run_payload["run_id"]
    approval_id = run_payload["approval_request_id"]

    assert run_payload["status"] == "WAITING_FOR_APPROVAL"
    assert approval_id is not None
    assert "Approval required" in run_payload["response_text"]

    approval_response = client.get(f"/approvals/{approval_id}")
    assert approval_response.status_code == 200
    assert approval_response.json()["status"] == "PENDING"

    approve_response = client.post(f"/approvals/{approval_id}/approve")
    assert approve_response.status_code == 200
    assert approve_response.json()["status"] == "APPROVED"
    assert approve_response.json()["resume_result"]["run_state"] == "COMPLETED"

    run_after_response = client.get(f"/runs/{run_id}")
    trace_response = client.get(f"/runs/{run_id}/trace")

    assert run_after_response.status_code == 200
    assert run_after_response.json()["status"] == "COMPLETED"
    assert "Refund request approved" in run_after_response.json()["response_text"]

    trace_events = trace_response.json()["events"]
    event_types = [event["event_type"] for event in trace_events]
    assert "APPROVAL_REQUESTED" in event_types
    assert "APPROVAL_RESOLVED" in event_types
    assert event_types[-1] == "RUN_COMPLETED"


def test_rejection_path_cancels_run_and_rejects_duplicate_resolution() -> None:
    client = build_test_client()

    create_response = client.post(
        "/runs",
        json={
            "workflow_key": "support.ticket",
            "tenant_id": "tenant-1",
            "requested_by": "operator-1",
            "user_input": "Submit a refund immediately for customer C-100 on ticket T-100.",
        },
    )
    approval_id = create_response.json()["approval_request_id"]
    run_id = create_response.json()["run_id"]

    reject_response = client.post(f"/approvals/{approval_id}/reject")
    assert reject_response.status_code == 200
    assert reject_response.json()["status"] == "REJECTED"
    assert reject_response.json()["resume_result"]["run_state"] == "CANCELED"

    run_response = client.get(f"/runs/{run_id}")
    assert run_response.status_code == 200
    assert run_response.json()["status"] == "CANCELED"
    assert run_response.json()["response_text"] == "Approval rejected"

    duplicate_reject = client.post(f"/approvals/{approval_id}/reject")
    assert duplicate_reject.status_code == 409


def test_eval_run_endpoints_return_report_and_regression_summary() -> None:
    client = build_test_client()

    first_run = client.post(
        "/evals/run",
        json={"name": "demo-suite", "compare_to_latest": False},
    )
    assert first_run.status_code == 200
    first_report = first_run.json()
    assert UUID(first_report["eval_run_id"])
    assert first_report["total_cases"] >= 10
    assert len(first_report["results"]) == first_report["total_cases"]

    second_run = client.post(
        "/evals/run",
        json={"name": "demo-suite", "compare_to_latest": True},
    )
    assert second_run.status_code == 200
    second_report = second_run.json()
    assert second_report["regression"] is not None

    get_report = client.get(f"/evals/{second_report['eval_run_id']}")
    assert get_report.status_code == 200
    fetched = get_report.json()
    assert fetched["eval_run_id"] == second_report["eval_run_id"]
    assert fetched["run_name"] == "demo-suite"
