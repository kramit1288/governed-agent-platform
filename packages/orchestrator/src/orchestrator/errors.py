"""Domain-specific errors for the orchestrator."""

from __future__ import annotations


class OrchestratorError(Exception):
    """Base class for orchestrator-specific errors."""


class InvalidStateTransitionError(OrchestratorError):
    """Raised when a run attempts an illegal lifecycle transition."""


class ApprovalResolutionError(OrchestratorError):
    """Raised when a waiting run cannot be resumed from approval state."""
