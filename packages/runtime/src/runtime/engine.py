"""Minimal in-memory runtime coordination for pause and resume."""

from __future__ import annotations

from uuid import UUID

from orchestrator.models import RunContext, RunState


class InMemoryRuntimeController:
    """Stores waiting run contexts so approval resolution can resume them."""

    def __init__(self) -> None:
        self._waiting_contexts: dict[UUID, RunContext] = {}
        self._approval_to_run: dict[UUID, UUID] = {}

    def store_waiting_context(self, context: RunContext) -> None:
        if context.approval_request_id is None:
            return
        self._waiting_contexts[context.task.run_id] = context
        self._approval_to_run[context.approval_request_id] = context.task.run_id

    def on_waiting_for_approval(self, run_id: UUID, approval_request_id: UUID) -> None:
        self._approval_to_run[approval_request_id] = run_id

    def on_run_resumed(self, run_id: UUID) -> None:
        self._waiting_contexts.pop(run_id, None)

    def on_run_completed(self, run_id: UUID, state: RunState) -> None:
        self._waiting_contexts.pop(run_id, None)
        stale_approval_ids = [
            approval_id for approval_id, stored_run_id in self._approval_to_run.items() if stored_run_id == run_id
        ]
        for approval_id in stale_approval_ids:
            self._approval_to_run.pop(approval_id, None)

    def get_waiting_context(self, run_id: UUID) -> RunContext | None:
        return self._waiting_contexts.get(run_id)

    def get_run_id_for_approval(self, approval_request_id: UUID) -> UUID | None:
        return self._approval_to_run.get(approval_request_id)
