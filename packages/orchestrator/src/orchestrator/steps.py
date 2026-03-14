"""Named helpers for the deterministic V1 step flow."""

from __future__ import annotations

from orchestrator.models import RunStep


ORDERED_STEPS: tuple[RunStep, ...] = (
    RunStep.CLASSIFY,
    RunStep.RETRIEVE_CONTEXT,
    RunStep.DECIDE_TOOLS,
    RunStep.EXECUTE_TOOLS,
    RunStep.REQUEST_APPROVAL_IF_NEEDED,
    RunStep.GENERATE_RESPONSE,
    RunStep.COMPLETE,
)
