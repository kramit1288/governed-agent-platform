"""Typed request and response models for the demo API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class RunCreateRequest(BaseModel):
    """Request payload for starting a run."""

    model_config = ConfigDict(extra="forbid")

    workflow_key: str = "support.ticket"
    user_input: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    requested_by: str | None = None


class RunResponse(BaseModel):
    """API read model for a run detail."""

    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    workflow_key: str
    user_input: str | None = None
    response_text: str | None = None
    last_error: str | None = None
    approval_request_id: str | None = None


class ApprovalResponse(BaseModel):
    """API read model for approval details."""

    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    tool_invocation_id: str | None = None
    status: str
    reason: str
    action_preview: dict[str, object] | None = None
    requested_at: str
    resolved_at: str | None = None
    decision_comment: str | None = None
    resume_result: dict[str, object] | None = None


class EvalRunRequest(BaseModel):
    """Request payload for executing offline evals."""

    model_config = ConfigDict(extra="forbid")

    name: str = "smoke-suite"
    compare_to_latest: bool = False
