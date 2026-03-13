"""Evaluation repository methods."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from sqlalchemy.orm import Session

from db.enums import EvalResultStatus, EvalRunStatus
from db.models import EvalResult, EvalRun


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
