"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import Callable, Generator
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from db.repositories import ApprovalRepository, RunRepository
from db.session import create_db_engine, create_session_factory
from orchestrator.approval import resolve_approval_status
from runtime.engine import InMemoryRuntimeController
from tracing.events import ApprovalResolvedPayload, TraceEventRecord, TraceEventType
from tracing.recorder import TraceRecorder
from tracing.timeline import TimelineBuilder


def create_app(
    *,
    session_factory: sessionmaker[Session] | None = None,
    runtime_controller: InMemoryRuntimeController | None = None,
    approval_resume: Callable[[UUID], object] | None = None,
) -> FastAPI:
    """Build the FastAPI application."""
    application = FastAPI(title="Governed Agent Platform API")
    application.state.session_factory = session_factory or create_session_factory(create_db_engine())
    application.state.timeline_builder = TimelineBuilder()
    application.state.runtime_controller = runtime_controller
    application.state.approval_resume = approval_resume

    def get_session() -> Generator[Session, None, None]:
        factory: sessionmaker[Session] = application.state.session_factory
        with factory() as session:
            yield session

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/approvals/{approval_id}")
    async def get_approval(approval_id: UUID, session: Session = Depends(get_session)) -> dict[str, object]:
        repository = ApprovalRepository(session)
        approval = repository.get_approval_request(approval_id)
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")
        return _serialize_approval(approval)

    @application.post("/approvals/{approval_id}/approve")
    async def approve_approval(
        approval_id: UUID,
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return _resolve_approval(application, session, approval_id, decision="APPROVED")

    @application.post("/approvals/{approval_id}/reject")
    async def reject_approval(
        approval_id: UUID,
        session: Session = Depends(get_session),
    ) -> dict[str, object]:
        return _resolve_approval(application, session, approval_id, decision="REJECTED")

    @application.get("/runs/{run_id}/trace")
    async def get_run_trace(run_id: UUID, session: Session = Depends(get_session)) -> dict[str, object]:
        repository = RunRepository(session)
        run = repository.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        timeline = application.state.timeline_builder.build(
            run_id,
            [
                TraceEventRecord(
                    run_id=event.run_id,
                    sequence=event.sequence,
                    event_type=TraceEventType(event.event_type),
                    payload=event.payload,
                    created_at=event.created_at,
                )
                for event in repository.list_run_events(run_id)
            ],
        )
        return timeline.model_dump(mode="json")

    return application


app = create_app()


def _resolve_approval(
    application: FastAPI,
    session: Session,
    approval_id: UUID,
    *,
    decision: str,
) -> dict[str, object]:
    approval_repository = ApprovalRepository(session)
    run_repository = RunRepository(session)
    approval = approval_repository.get_approval_request(approval_id)
    if approval is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")

    try:
        resolved = approval_repository.resolve_approval_request(
            approval_id,
            status=resolve_approval_status(decision),
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    TraceRecorder(run_repository).record_event(
        approval.run_id,
        TraceEventType.APPROVAL_RESOLVED.value,
        ApprovalResolvedPayload(
            approval_request_id=str(approval_id),
            status=decision,
            decision_comment=None,
        ),
    )
    session.commit()
    resume_result = None
    approval_resume = application.state.approval_resume
    if approval_resume is not None:
        resume_result = approval_resume(approval_id)
    payload = _serialize_approval(resolved)
    if resume_result is not None:
        payload["resume_result"] = _serialize_resume_result(resume_result)
    return payload


def _serialize_approval(approval: object) -> dict[str, object]:
    return {
        "id": str(getattr(approval, "id")),
        "run_id": str(getattr(approval, "run_id")),
        "tool_invocation_id": (
            str(getattr(approval, "tool_invocation_id"))
            if getattr(approval, "tool_invocation_id", None) is not None
            else None
        ),
        "status": getattr(approval, "status").value,
        "reason": getattr(approval, "reason"),
        "action_preview": getattr(approval, "action_preview"),
        "requested_at": getattr(approval, "requested_at").isoformat(),
        "resolved_at": (
            getattr(approval, "resolved_at").isoformat()
            if getattr(approval, "resolved_at", None) is not None
            else None
        ),
        "decision_comment": getattr(approval, "decision_comment"),
    }


def _serialize_resume_result(result: object) -> dict[str, object]:
    state = getattr(result, "state", None)
    return {
        "run_state": state.value if state is not None else None,
        "response_text": getattr(result, "response_text", None),
        "failure_reason": getattr(result, "failure_reason", None),
    }
