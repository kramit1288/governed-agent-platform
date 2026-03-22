"""Run-focused repository methods."""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from db.enums import RunStatus
from db.models import Run, RunEvent


class RunRepository:
    """Persistence operations for runs and append-only run events."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_run(
        self,
        *,
        workflow_key: str,
        requested_by: str | None = None,
        input_payload: dict | None = None,
        status: RunStatus = RunStatus.PENDING,
    ) -> Run:
        run = Run(
            workflow_key=workflow_key,
            requested_by=requested_by,
            input_payload=input_payload,
            status=status,
            started_at=datetime.now(timezone.utc) if status == RunStatus.IN_PROGRESS else None,
        )
        self._session.add(run)
        self._session.flush()
        return run

    def get_run(self, run_id: UUID) -> Run | None:
        return self._session.get(Run, run_id)

    def update_run_status(
        self,
        run_id: UUID,
        *,
        status: RunStatus | str,
        last_error: str | None = None,
    ) -> Run | None:
        run = self.get_run(run_id)
        if run is None:
            return None

        normalized_status = RunStatus(status)

        run.status = normalized_status
        run.last_error = last_error
        if normalized_status == RunStatus.IN_PROGRESS and run.started_at is None:
            run.started_at = datetime.now(timezone.utc)
        if normalized_status in {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELED}:
            run.completed_at = datetime.now(timezone.utc)
        self._session.flush()
        return run

    def append_run_event(
        self,
        *,
        run_id: UUID,
        event_type: str,
        payload: dict | None = None,
    ) -> RunEvent:
        sequence = self._next_sequence(run_id)
        event = RunEvent(
            run_id=run_id,
            sequence=sequence,
            event_type=event_type,
            payload=payload,
        )
        self._session.add(event)
        self._session.flush()
        return event

    def list_run_events(self, run_id: UUID) -> list[RunEvent]:
        statement = (
            select(RunEvent)
            .where(RunEvent.run_id == run_id)
            .order_by(RunEvent.sequence.asc())
        )
        return list(self._session.scalars(statement))

    def _next_sequence(self, run_id: UUID) -> int:
        statement = select(func.coalesce(func.max(RunEvent.sequence), 0) + 1).where(
            RunEvent.run_id == run_id
        )
        return int(self._session.execute(statement).scalar_one())
