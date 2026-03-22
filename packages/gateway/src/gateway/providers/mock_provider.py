"""Deterministic mock adapter for tests and local development."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from gateway.config import ProviderConfig
from gateway.types import (
    ModelRequest,
    ModelResponse,
    ProviderError,
    ProviderName,
    UsageStats,
)


class MockProviderBehavior(BaseModel):
    """Configurable deterministic behavior for the mock provider."""

    model_config = ConfigDict(extra="forbid")

    prefix: str = "mock-response"
    retryable_failure_count: int = Field(default=0, ge=0)
    non_retryable_failure_count: int = Field(default=0, ge=0)


class MockProvider:
    """Deterministic provider used for unit tests and local workflows."""

    def __init__(
        self,
        *,
        config: ProviderConfig,
        provider_name: ProviderName = ProviderName.MOCK,
        behavior: MockProviderBehavior | None = None,
    ) -> None:
        self._config = config
        self.name = provider_name
        self._behavior = behavior or MockProviderBehavior()
        self._calls = 0

    def is_configured(self) -> bool:
        return True

    def generate(self, *, request: ModelRequest, model: str) -> ModelResponse:
        self._calls += 1

        if self._calls <= self._behavior.non_retryable_failure_count:
            raise ProviderError(
                provider=self.name,
                model=model,
                message="Mock provider non-retryable failure.",
                retryable=False,
                error_code="mock_non_retryable",
            )

        retryable_cutoff = self._behavior.non_retryable_failure_count + self._behavior.retryable_failure_count
        if self._calls <= retryable_cutoff:
            raise ProviderError(
                provider=self.name,
                model=model,
                message="Mock provider retryable failure.",
                retryable=True,
                error_code="mock_retryable",
            )

        output = (
            f"{self._behavior.prefix}|provider={self.name.value}|model={model}|"
            f"task={request.task_category.value}|risk={request.risk_level.value}|"
            f"prompt={request.prompt}"
        )
        input_tokens = len(request.prompt.split())
        output_tokens = len(output.split())
        total_tokens = input_tokens + output_tokens

        return ModelResponse(
            provider=self.name,
            model=model,
            output_text=output,
            stop_reason="completed",
            usage=UsageStats(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                latency_ms=5,
                estimated_cost_usd=round(total_tokens * 0.000001, 6),
            ),
            metadata={"call_count": self._calls},
        )
