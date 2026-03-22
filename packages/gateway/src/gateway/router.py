"""Gateway service for provider-neutral model access."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol

from gateway.config import GatewayConfig
from gateway.policies import FallbackPolicy, RoutingPolicy, SimpleFallbackPolicy, SimpleRoutingPolicy
from gateway.types import (
    ModelRequest,
    ModelResponse,
    ProviderAdapter,
    ProviderError,
    ProviderName,
    RouteDecision,
)


class RouteDecisionRecorder(Protocol):
    """Hook for recording route decisions outside the gateway."""

    def record(self, decision: RouteDecision) -> None:
        """Persist or emit a route decision."""


class AIGateway:
    """Coordinates route selection, provider execution, and fallback."""

    def __init__(
        self,
        *,
        adapters: Mapping[ProviderName, ProviderAdapter],
        config: GatewayConfig | None = None,
        routing_policy: RoutingPolicy | None = None,
        fallback_policy: FallbackPolicy | None = None,
        route_decision_recorder: RouteDecisionRecorder | None = None,
    ) -> None:
        self._adapters = dict(adapters)
        self._config = config or GatewayConfig.from_env()
        self._routing_policy = routing_policy or SimpleRoutingPolicy()
        self._fallback_policy = fallback_policy or SimpleFallbackPolicy()
        self._route_decision_recorder = route_decision_recorder

    def route(self, request: ModelRequest) -> RouteDecision:
        """Resolve the primary route and optional fallback path for a request."""

        decision = self._routing_policy.select_route(
            request=request,
            config=self._config,
            adapters=self._adapters,
        )
        if self._route_decision_recorder is not None:
            self._route_decision_recorder.record(decision)
        return decision

    def generate(self, request: ModelRequest) -> ModelResponse:
        """Execute a request against the selected provider with simple fallback."""

        decision = self.route(request)
        primary_adapter = self._get_adapter(decision.primary_provider)

        try:
            response = primary_adapter.generate(request=request, model=decision.primary_model)
            return self._attach_route_metadata(response, decision, fallback_used=False)
        except ProviderError as error:
            if not self._fallback_policy.should_fallback(
                request=request,
                decision=decision,
                error=error,
            ):
                raise

            fallback_adapter = self._get_adapter(decision.fallback_provider)
            fallback_response = fallback_adapter.generate(request=request, model=decision.fallback_model)
            return self._attach_route_metadata(
                fallback_response,
                decision,
                fallback_used=True,
                primary_error=error,
            )

    def _get_adapter(self, provider: ProviderName | None) -> ProviderAdapter:
        if provider is None:
            raise ProviderError(
                provider=ProviderName.MOCK,
                message="No provider configured for the requested route.",
                retryable=False,
            )

        try:
            return self._adapters[provider]
        except KeyError as exc:
            raise ProviderError(
                provider=provider,
                message=f"No adapter registered for provider '{provider}'.",
                retryable=False,
            ) from exc

    @staticmethod
    def _attach_route_metadata(
        response: ModelResponse,
        decision: RouteDecision,
        *,
        fallback_used: bool,
        primary_error: ProviderError | None = None,
    ) -> ModelResponse:
        metadata = dict(response.metadata)
        metadata["fallback_used"] = fallback_used
        if primary_error is not None:
            metadata["primary_error"] = primary_error.to_dict()
        return response.model_copy(
            update={
                "route_decision": decision,
                "metadata": metadata,
            }
        )
