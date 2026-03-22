"""Read models for presenting run traces as a simple lifecycle timeline."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from tracing.events import TraceEventRecord, TraceEventType


class TimelineEntry(BaseModel):
    """Single user-facing timeline row derived from a run event."""

    model_config = ConfigDict(extra="forbid")

    sequence: int
    event_type: TraceEventType
    title: str
    timestamp: datetime
    payload: dict[str, object] | None = None


class RunTimeline(BaseModel):
    """Ordered event timeline suitable for API and future UI consumption."""

    model_config = ConfigDict(extra="forbid")

    run_id: UUID
    event_count: int
    events: list[TimelineEntry]


class TimelineBuilder:
    """Build a readable timeline from append-only run events."""

    def build(self, run_id: UUID, events: list[TraceEventRecord]) -> RunTimeline:
        entries = [
            TimelineEntry(
                sequence=event.sequence,
                event_type=event.event_type,
                title=_title_for_event(event.event_type),
                timestamp=event.created_at,
                payload=event.payload,
            )
            for event in events
        ]
        return RunTimeline(run_id=run_id, event_count=len(entries), events=entries)


def _title_for_event(event_type: TraceEventType) -> str:
    return {
        TraceEventType.RUN_STARTED: "Run started",
        TraceEventType.MODEL_SELECTED: "Model selected",
        TraceEventType.RETRIEVAL_COMPLETED: "Retrieval completed",
        TraceEventType.TOOL_CALLED: "Tool called",
        TraceEventType.TOOL_RESULT_RECEIVED: "Tool result received",
        TraceEventType.APPROVAL_REQUESTED: "Approval requested",
        TraceEventType.APPROVAL_RESOLVED: "Approval resolved",
        TraceEventType.RUN_COMPLETED: "Run completed",
        TraceEventType.RUN_FAILED: "Run failed",
    }[event_type]
