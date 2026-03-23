"""FastAPI application entrypoint."""

from __future__ import annotations

from collections.abc import Generator
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, status
from sqlalchemy.orm import Session, sessionmaker

from apps.api.app.demo import DemoPlatformService
from apps.api.app.models import ApprovalResponse, EvalRunRequest, RunCreateRequest, RunResponse
from db.repositories import ApprovalRepository, RunRepository
from db.session import create_db_engine, create_session_factory
from evals import EvalRun
from orchestrator.approval import resolve_approval_status
from runtime.engine import InMemoryRuntimeController
from tracing import RunTimeline
from tracing.events import ApprovalResolvedPayload, TraceEventType
from tracing.recorder import TraceRecorder
from tracing.timeline import TimelineBuilder


def create_app(
    *,
    session_factory: sessionmaker[Session] | None = None,
    runtime_controller: InMemoryRuntimeController | None = None,
) -> FastAPI:
    """Build the FastAPI application."""
    application = FastAPI(title="Governed Agent Platform API")
    application.state.session_factory = session_factory or create_session_factory(create_db_engine())
    application.state.timeline_builder = TimelineBuilder()
    application.state.runtime_controller = runtime_controller or InMemoryRuntimeController()

    def get_session() -> Generator[Session, None, None]:
        factory: sessionmaker[Session] = application.state.session_factory
        with factory() as session:
            yield session

    def get_demo_service(session: Session = Depends(get_session)) -> DemoPlatformService:
        return DemoPlatformService(
            session=session,
            runtime_controller=application.state.runtime_controller,
        )

    @application.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/runs", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
    async def create_run(
        request: RunCreateRequest,
        service: DemoPlatformService = Depends(get_demo_service),
    ) -> RunResponse:
        return service.start_run(request)

    @application.get("/runs/{run_id}", response_model=RunResponse)
    async def get_run(run_id: UUID, service: DemoPlatformService = Depends(get_demo_service)) -> RunResponse:
        try:
            return service.get_run(run_id)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    @application.get("/approvals/{approval_id}", response_model=ApprovalResponse)
    async def get_approval(
        approval_id: UUID,
        session: Session = Depends(get_session),
    ) -> ApprovalResponse:
        repository = ApprovalRepository(session)
        approval = repository.get_approval_request(approval_id)
        if approval is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Approval request not found.")
        return ApprovalResponse.model_validate(_serialize_approval(approval))

    @application.post("/approvals/{approval_id}/approve", response_model=ApprovalResponse)
    async def approve_approval(
        approval_id: UUID,
        session: Session = Depends(get_session),
        service: DemoPlatformService = Depends(get_demo_service),
    ) -> ApprovalResponse:
        return ApprovalResponse.model_validate(
            _resolve_approval(application, session, service, approval_id, decision="APPROVED")
        )

    @application.post("/approvals/{approval_id}/reject", response_model=ApprovalResponse)
    async def reject_approval(
        approval_id: UUID,
        session: Session = Depends(get_session),
        service: DemoPlatformService = Depends(get_demo_service),
    ) -> ApprovalResponse:
        return ApprovalResponse.model_validate(
            _resolve_approval(application, session, service, approval_id, decision="REJECTED")
        )

    @application.get("/runs/{run_id}/trace", response_model=RunTimeline)
    async def get_run_trace(
        run_id: UUID,
        service: DemoPlatformService = Depends(get_demo_service),
    ) -> RunTimeline:
        try:
            service.get_run(run_id)
        except LookupError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Run not found.")
        timeline = application.state.timeline_builder.build(
            run_id,
            service.build_trace_records(run_id),
        )
        return timeline

    @application.post("/evals/run", response_model=EvalRun)
    async def run_evals(
        request: EvalRunRequest,
        service: DemoPlatformService = Depends(get_demo_service),
    ) -> EvalRun:
        return service.run_evals(name=request.name, compare_to_latest=request.compare_to_latest)

    @application.get("/evals/{eval_run_id}", response_model=EvalRun)
    async def get_eval_run(eval_run_id: UUID, service: DemoPlatformService = Depends(get_demo_service)) -> EvalRun:
        try:
            return service.get_eval_report(eval_run_id)
        except LookupError as exc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

    return application


app = create_app()


def _resolve_approval(
    application: FastAPI,
    session: Session,
    service: DemoPlatformService,
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
    resume_result = service.resume_after_approval(approval_id)
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
