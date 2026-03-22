"""Typed contracts for provider-neutral model access."""

from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class ProviderName(StrEnum):
    """Supported model providers in V1."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    MOCK = "mock"


class TaskCategory(StrEnum):
    """High-level tasks that inform routing decisions."""

    GENERAL = "general"
    SUMMARIZATION = "summarization"
    ACTION_PLANNING = "action_planning"
    APPROVAL = "approval"


class RiskLevel(StrEnum):
    """Risk levels that inform model strength selection."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class UsageStats(BaseModel):
    """Normalized token, latency, and estimated cost metadata."""

    model_config = ConfigDict(extra="forbid")

    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    total_tokens: int = Field(default=0, ge=0)
    latency_ms: int = Field(default=0, ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)


class ModelRequest(BaseModel):
    """Provider-neutral completion request consumed by the gateway."""

    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=1)
    task_category: TaskCategory = TaskCategory.GENERAL
    risk_level: RiskLevel = RiskLevel.MEDIUM
    tenant_id: str = Field(min_length=1)
    temperature: float | None = Field(default=None, ge=0.0, le=2.0)
    max_output_tokens: int | None = Field(default=None, ge=1)
    allow_fallback: bool = True
    preferred_provider: ProviderName | None = None
    preferred_model: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RouteDecision(BaseModel):
    """Resolved provider/model selection including the fallback path."""

    model_config = ConfigDict(extra="forbid")

    primary_provider: ProviderName
    primary_model: str
    fallback_provider: ProviderName | None = None
    fallback_model: str | None = None
    task_category: TaskCategory
    risk_level: RiskLevel
    policy_name: str
    reason: str
    fallback_allowed: bool = False


class ModelResponse(BaseModel):
    """Normalized model output returned to callers."""

    model_config = ConfigDict(extra="forbid")

    provider: ProviderName
    model: str
    output_text: str
    usage: UsageStats
    stop_reason: str | None = None
    route_decision: RouteDecision | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ProviderError(RuntimeError):
    """Structured provider error used by fallback policy decisions."""

    def __init__(
        self,
        *,
        provider: ProviderName,
        message: str,
        retryable: bool,
        model: str | None = None,
        status_code: int | None = None,
        error_code: str | None = None,
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.model = model
        self.retryable = retryable
        self.status_code = status_code
        self.error_code = error_code

    def to_dict(self) -> dict[str, object]:
        """Serialize the error for trace metadata."""

        return {
            "provider": self.provider.value,
            "model": self.model,
            "message": str(self),
            "retryable": self.retryable,
            "status_code": self.status_code,
            "error_code": self.error_code,
        }


class ProviderAdapter(Protocol):
    """Provider-specific execution contract owned by the gateway."""

    name: ProviderName

    def is_configured(self) -> bool:
        """Return whether the adapter has enough config to serve requests."""

    def generate(self, *, request: ModelRequest, model: str) -> ModelResponse:
        """Execute a normalized request against a provider model."""
