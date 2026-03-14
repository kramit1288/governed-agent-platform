"""Explicit state transition rules for the orchestrator."""

from __future__ import annotations

from orchestrator.errors import InvalidStateTransitionError
from orchestrator.models import RunState, RunStep


_ALLOWED_STATE_TRANSITIONS: dict[RunState, set[RunState]] = {
    RunState.PENDING: {RunState.IN_PROGRESS, RunState.CANCELED},
    RunState.IN_PROGRESS: {RunState.WAITING_FOR_APPROVAL, RunState.COMPLETED, RunState.FAILED, RunState.CANCELED},
    RunState.WAITING_FOR_APPROVAL: {RunState.IN_PROGRESS, RunState.FAILED, RunState.CANCELED},
    RunState.COMPLETED: set(),
    RunState.FAILED: set(),
    RunState.CANCELED: set(),
}


class OrchestratorStateMachine:
    """Validates lifecycle state changes and deterministic step sequencing."""

    def transition_state(self, current: RunState, target: RunState) -> RunState:
        if target not in _ALLOWED_STATE_TRANSITIONS[current]:
            raise InvalidStateTransitionError(f"Invalid state transition: {current} -> {target}")
        return target

    def next_step(self, current: RunStep | None) -> RunStep:
        if current is None:
            return RunStep.CLASSIFY
        ordered_steps = [
            RunStep.CLASSIFY,
            RunStep.RETRIEVE_CONTEXT,
            RunStep.DECIDE_TOOLS,
            RunStep.EXECUTE_TOOLS,
            RunStep.REQUEST_APPROVAL_IF_NEEDED,
            RunStep.GENERATE_RESPONSE,
            RunStep.COMPLETE,
        ]
        try:
            index = ordered_steps.index(current)
        except ValueError as error:
            raise InvalidStateTransitionError(f"Unknown step: {current}") from error
        if index == len(ordered_steps) - 1:
            raise InvalidStateTransitionError(f"Step {current} has no successor")
        return ordered_steps[index + 1]
