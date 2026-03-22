"""Minimal environment-backed configuration for the AI gateway."""

from __future__ import annotations

import os

from pydantic import BaseModel, ConfigDict, Field

from gateway.types import ProviderName


class ProviderConfig(BaseModel):
    """Provider credentials and model defaults used by routing."""

    model_config = ConfigDict(extra="forbid")

    api_key: str | None = None
    base_url: str | None = None
    timeout_seconds: float = Field(default=30.0, gt=0)
    default_model: str
    fast_model: str
    strong_model: str

    def model_for_tier(self, tier: str) -> str:
        """Resolve the concrete model name for a policy tier."""

        if tier == "fast":
            return self.fast_model
        if tier == "strong":
            return self.strong_model
        return self.default_model


class GatewayConfig(BaseModel):
    """Gateway-level routing and provider configuration."""

    model_config = ConfigDict(extra="forbid")

    default_provider: ProviderName = ProviderName.OPENAI
    fallback_provider: ProviderName | None = ProviderName.ANTHROPIC
    enable_fallback: bool = True
    providers: dict[ProviderName, ProviderConfig]

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        """Build configuration from environment variables with V1 defaults."""

        providers = {
            ProviderName.OPENAI: ProviderConfig(
                api_key=os.getenv("OPENAI_API_KEY"),
                base_url=os.getenv("OPENAI_BASE_URL"),
                timeout_seconds=float(os.getenv("OPENAI_TIMEOUT_SECONDS", "30")),
                default_model=os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4.1-mini"),
                fast_model=os.getenv("OPENAI_FAST_MODEL", "gpt-4.1-mini"),
                strong_model=os.getenv("OPENAI_STRONG_MODEL", "gpt-4.1"),
            ),
            ProviderName.ANTHROPIC: ProviderConfig(
                api_key=os.getenv("ANTHROPIC_API_KEY"),
                base_url=os.getenv("ANTHROPIC_BASE_URL"),
                timeout_seconds=float(os.getenv("ANTHROPIC_TIMEOUT_SECONDS", "30")),
                default_model=os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-3-5-sonnet-latest"),
                fast_model=os.getenv("ANTHROPIC_FAST_MODEL", "claude-3-5-haiku-latest"),
                strong_model=os.getenv("ANTHROPIC_STRONG_MODEL", "claude-3-5-sonnet-latest"),
            ),
            ProviderName.MOCK: ProviderConfig(
                api_key=None,
                base_url=None,
                timeout_seconds=5.0,
                default_model=os.getenv("MOCK_DEFAULT_MODEL", "mock-default"),
                fast_model=os.getenv("MOCK_FAST_MODEL", "mock-fast"),
                strong_model=os.getenv("MOCK_STRONG_MODEL", "mock-strong"),
            ),
        }
        return cls(
            default_provider=ProviderName(os.getenv("AI_GATEWAY_DEFAULT_PROVIDER", ProviderName.OPENAI.value)),
            fallback_provider=_read_optional_provider("AI_GATEWAY_FALLBACK_PROVIDER"),
            enable_fallback=os.getenv("AI_GATEWAY_ENABLE_FALLBACK", "true").lower() == "true",
            providers=providers,
        )


def _read_optional_provider(name: str) -> ProviderName | None:
    value = os.getenv(name)
    if value is None or value == "":
        return None
    return ProviderName(value)
