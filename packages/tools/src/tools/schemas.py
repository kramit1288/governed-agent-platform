"""Typed tool contracts and argument schemas for the V1 tool layer."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolRiskLevel(StrEnum):
    """Explicit risk classification used for execution guardrails."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ToolStatus(StrEnum):
    """Standardized tool execution outcomes."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    APPROVAL_REQUIRED = "approval_required"


class SearchDocsFilters(BaseModel):
    """Optional document filters for local search."""

    model_config = ConfigDict(extra="forbid")

    category: str | None = None
    tags: list[str] = Field(default_factory=list)


class SearchDocsInput(BaseModel):
    """Arguments for local document search."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)
    optional_filters: SearchDocsFilters | None = None


class GetTicketInput(BaseModel):
    """Arguments for loading a seeded ticket."""

    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)


class GetIncidentInput(BaseModel):
    """Arguments for loading a seeded incident."""

    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)


class GetCustomerInput(BaseModel):
    """Arguments for loading a seeded customer."""

    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)


class DraftRefundRequestInput(BaseModel):
    """Arguments for drafting a refund preview."""

    model_config = ConfigDict(extra="forbid")

    customer_id: str = Field(min_length=1)
    ticket_id: str = Field(min_length=1)
    amount: float = Field(gt=0)
    reason: str = Field(min_length=1)
    tenant_id: str = Field(min_length=1)


class ToolCall(BaseModel):
    """Tool invocation request emitted by higher-level layers."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)
    requested_by: str | None = None


class ToolExecutionMetadata(BaseModel):
    """Audit-friendly execution metadata for every tool run."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    risk_level: ToolRiskLevel
    requires_approval: bool
    tenant_id: str | None = None
    attempts: int = Field(ge=1)
    timeout_ms: int = Field(ge=1)
    started_at: datetime
    completed_at: datetime
    duration_ms: int = Field(ge=0)
    retried: bool = False


class ToolResult(BaseModel):
    """Standardized tool execution result returned to callers."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    status: ToolStatus
    output: dict[str, Any] | None = None
    error: str | None = None
    requires_approval: bool = False
    preview_payload: dict[str, Any] | None = None
    metadata: ToolExecutionMetadata


class ToolExecutionOutput(BaseModel):
    """Internal normalized payload produced by tool implementations."""

    model_config = ConfigDict(extra="forbid")

    output: dict[str, Any] | None = None
    preview_payload: dict[str, Any] | None = None


ToolHandler = Callable[[BaseModel], ToolExecutionOutput]


@dataclass(slots=True, frozen=True)
class ToolDefinition:
    """Static schema and behavior definition for a registered tool."""

    name: str
    description: str
    input_schema: type[BaseModel]
    risk_level: ToolRiskLevel
    requires_approval: bool
    timeout_ms: int
    retry_count: int
    handler: ToolHandler


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp for audit fields."""

    return datetime.now(tz=UTC)
