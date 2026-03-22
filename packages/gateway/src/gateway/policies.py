"""Small, explicit routing and fallback policies for V1."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from gateway.config import GatewayConfig
from gateway.types import (
    ModelRequest,
    ProviderAdapter,
    ProviderError,
    ProviderName,
    RiskLevel,
    RouteDecision,
    TaskCategory,
)


class RoutingPolicy(Protocol):
    """Resolves provider and model selection for a request."""

    def select_route(
        self,
        *,
        request: ModelRequest,
        config: GatewayConfig,
        adapters: Mapping[ProviderName, ProviderAdapter],
    ) -> RouteDecision:
        """Return the primary route and fallback path."""


class FallbackPolicy(Protocol):
    """Determines whether a provider error should trigger fallback."""

    def should_fallback(
        self,
        *,
        request: ModelRequest,
        decision: RouteDecision,
        error: ProviderError,
    ) -> bool:
        """Return whether the gateway should try the secondary route."""


class CostLatencyTierPolicy:
    """Maps request risk and task class to a simple model strength tier."""

    def select_tier(self, request: ModelRequest) -> str:
        """Choose between fast, default, and strong model tiers."""

        if request.task_category is TaskCategory.SUMMARIZATION and request.risk_level is RiskLevel.LOW:
            return "fast"
        if request.task_category in {TaskCategory.ACTION_PLANNING, TaskCategory.APPROVAL}:
            return "strong"
        if request.risk_level is RiskLevel.HIGH:
            return "strong"
        return "default"


class SimpleRoutingPolicy:
    """Small routing policy with explicit task/risk-driven decisions."""

    def __init__(self, *, tier_policy: CostLatencyTierPolicy | None = None) -> None:
        self._tier_policy = tier_policy or CostLatencyTierPolicy()

    def select_route(
        self,
        *,
        request: ModelRequest,
        config: GatewayConfig,
        adapters: Mapping[ProviderName, ProviderAdapter],
    ) -> RouteDecision:
        tier = self._tier_policy.select_tier(request)
        primary_provider = request.preferred_provider or config.default_provider
        _require_configured_adapter(primary_provider, adapters)
        primary_model = request.preferred_model or config.providers[primary_provider].model_for_tier(tier)

        fallback_provider = None
        fallback_model = None
        fallback_allowed = bool(request.allow_fallback and config.enable_fallback)
        if fallback_allowed and config.fallback_provider is not None and config.fallback_provider != primary_provider:
            candidate_fallback = config.fallback_provider
            fallback_adapter = adapters.get(candidate_fallback)
            if fallback_adapter is not None and fallback_adapter.is_configured():
                fallback_provider = candidate_fallback
                fallback_model = config.providers[fallback_provider].model_for_tier(tier)

        reason = (
            f"Selected {tier} tier for task='{request.task_category.value}' "
            f"risk='{request.risk_level.value}' using provider='{primary_provider.value}'."
        )
        return RouteDecision(
            primary_provider=primary_provider,
            primary_model=primary_model,
            fallback_provider=fallback_provider,
            fallback_model=fallback_model,
            task_category=request.task_category,
            risk_level=request.risk_level,
            policy_name="simple_routing_v1",
            reason=reason,
            fallback_allowed=fallback_provider is not None,
        )


class SimpleFallbackPolicy:
    """Fallback policy that retries once on retryable provider failures."""

    def should_fallback(
        self,
        *,
        request: ModelRequest,
        decision: RouteDecision,
        error: ProviderError,
    ) -> bool:
        return bool(
            request.allow_fallback
            and decision.fallback_allowed
            and decision.fallback_provider is not None
            and decision.fallback_model is not None
            and error.retryable
        )


def _require_configured_adapter(
    provider: ProviderName,
    adapters: Mapping[ProviderName, ProviderAdapter],
) -> ProviderAdapter:
    try:
        adapter = adapters[provider]
    except KeyError as exc:
        raise ProviderError(
            provider=provider,
            message=f"No adapter registered for provider '{provider}'.",
            retryable=False,
        ) from exc

    if not adapter.is_configured():
        raise ProviderError(
            provider=provider,
            message=f"Provider '{provider}' is not configured.",
            retryable=False,
        )
    return adapter
