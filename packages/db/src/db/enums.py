"""Database enums shared across persistence models."""

from __future__ import annotations

from enum import StrEnum


class RunStatus(StrEnum):
    """Lifecycle states for an orchestrated run."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_APPROVAL = "WAITING_FOR_APPROVAL"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class ApprovalStatus(StrEnum):
    """Resolution states for an approval request."""

    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ToolInvocationStatus(StrEnum):
    """Execution states for a tool invocation record."""

    PENDING = "PENDING"
    APPROVAL_REQUIRED = "APPROVAL_REQUIRED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class EvalRunStatus(StrEnum):
    """Execution states for an evaluation run."""

    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class EvalResultStatus(StrEnum):
    """Outcome states for a single evaluation result."""

    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"
