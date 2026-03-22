"""Trace recorder backed by append-only run events."""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from pydantic import BaseModel


class RunEventStore(Protocol):
    """Minimal persistence boundary for append-only run events."""

    def append_run_event(
        self,
        *,
        run_id: UUID,
        event_type: str,
        payload: dict[str, object] | None = None,
    ) -> object:
        """Persist a new run event."""


class TraceRecorder:
    """Appends normalized trace events to the run event store."""

    def __init__(self, store: RunEventStore) -> None:
        self._store = store

    def record_event(
        self,
        run_id: UUID,
        event_type: str,
        payload: dict[str, object] | BaseModel | None = None,
    ) -> None:
        normalized_payload: dict[str, object] | None
        if isinstance(payload, BaseModel):
            normalized_payload = payload.model_dump(mode="json")
        else:
            normalized_payload = payload
        self._store.append_run_event(
            run_id=run_id,
            event_type=event_type,
            payload=normalized_payload,
        )
