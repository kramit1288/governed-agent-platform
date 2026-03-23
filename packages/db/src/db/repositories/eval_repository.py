"""Evaluation repository methods."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.enums import EvalResultStatus, EvalRunStatus
from db.models import EvalCase, EvalResult, EvalRun


class EvalRepository:
    """Persistence operations for eval runs and results."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create_eval_run(
        self,
        *,
        name: str,
        model_name: str | None = None,
        status: EvalRunStatus = EvalRunStatus.PENDING,
    ) -> EvalRun:
        eval_run = EvalRun(
            name=name,
            model_name=model_name,
            status=status,
            started_at=datetime.now(timezone.utc) if status == EvalRunStatus.IN_PROGRESS else None,
        )
        self._session.add(eval_run)
        self._session.flush()
        return eval_run

    def update_eval_run_status(
        self,
        eval_run_id: UUID,
        *,
        status: EvalRunStatus,
    ) -> EvalRun | None:
        eval_run = self._session.get(EvalRun, eval_run_id)
        if eval_run is None:
            return None
        eval_run.status = status
        if status == EvalRunStatus.IN_PROGRESS and eval_run.started_at is None:
            eval_run.started_at = datetime.now(timezone.utc)
        if status in {EvalRunStatus.COMPLETED, EvalRunStatus.FAILED}:
            eval_run.completed_at = datetime.now(timezone.utc)
        self._session.flush()
        return eval_run

    def get_or_create_eval_case(
        self,
        *,
        key: str,
        input_text: str,
        description: str | None = None,
        expected_behavior: str | None = None,
        tags: list[str] | None = None,
    ) -> EvalCase:
        statement = select(EvalCase).where(EvalCase.key == key)
        existing = self._session.scalar(statement)
        if existing is not None:
            existing.input_text = input_text
            existing.description = description
            existing.expected_behavior = expected_behavior
            existing.tags = tags
            self._session.flush()
            return existing

        eval_case = EvalCase(
            key=key,
            input_text=input_text,
            description=description,
            expected_behavior=expected_behavior,
            tags=tags,
            is_active=True,
        )
        self._session.add(eval_case)
        self._session.flush()
        return eval_case

    def store_eval_result(
        self,
        *,
        eval_run_id: UUID,
        eval_case_id: UUID,
        status: EvalResultStatus,
        score: Decimal | None = None,
        summary: str | None = None,
        details: dict | None = None,
    ) -> EvalResult:
        eval_result = EvalResult(
            eval_run_id=eval_run_id,
            eval_case_id=eval_case_id,
            status=status,
            score=score,
            summary=summary,
            details=details,
        )
        self._session.add(eval_result)
        self._session.flush()
        return eval_result

    def get_eval_run(self, eval_run_id: UUID) -> EvalRun | None:
        return self._session.get(EvalRun, eval_run_id)

    def list_eval_results(self, eval_run_id: UUID) -> list[EvalResult]:
        statement = (
            select(EvalResult)
            .where(EvalResult.eval_run_id == eval_run_id)
            .order_by(EvalResult.created_at.asc())
        )
        return list(self._session.scalars(statement))

    def get_latest_completed_run(self, name: str) -> EvalRun | None:
        statement = (
            select(EvalRun)
            .where(EvalRun.name == name, EvalRun.status == EvalRunStatus.COMPLETED)
            .order_by(EvalRun.completed_at.desc(), EvalRun.created_at.desc())
            .limit(1)
        )
        return self._session.scalar(statement)
