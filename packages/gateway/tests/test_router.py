"""Unit tests for explicit gateway routing and fallback behavior."""

from __future__ import annotations

from gateway.config import GatewayConfig, ProviderConfig
from gateway.providers.mock_provider import MockProvider, MockProviderBehavior
from gateway.router import AIGateway
from gateway.types import (
    ModelRequest,
    ProviderError,
    ProviderName,
    RiskLevel,
    TaskCategory,
)


class RecordingRouteDecisionRecorder:
    def __init__(self) -> None:
        self.decisions = []

    def record(self, decision) -> None:
        self.decisions.append(decision)


def build_config(
    *,
    default_provider: ProviderName,
    fallback_provider: ProviderName | None,
) -> GatewayConfig:
    provider_settings = {
        ProviderName.OPENAI: ProviderConfig(
            api_key="openai-key",
            default_model="gpt-default",
            fast_model="gpt-fast",
            strong_model="gpt-strong",
        ),
        ProviderName.ANTHROPIC: ProviderConfig(
            api_key="anthropic-key",
            default_model="claude-default",
            fast_model="claude-fast",
            strong_model="claude-strong",
        ),
        ProviderName.MOCK: ProviderConfig(
            default_model="mock-default",
            fast_model="mock-fast",
            strong_model="mock-strong",
        ),
    }
    return GatewayConfig(
        default_provider=default_provider,
        fallback_provider=fallback_provider,
        enable_fallback=True,
        providers=provider_settings,
    )


def make_request(
    *,
    task_category: TaskCategory = TaskCategory.GENERAL,
    risk_level: RiskLevel = RiskLevel.MEDIUM,
    allow_fallback: bool = True,
) -> ModelRequest:
    return ModelRequest(
        prompt="Summarize the change request",
        task_category=task_category,
        risk_level=risk_level,
        tenant_id="tenant-1",
        allow_fallback=allow_fallback,
    )


def test_routes_to_primary_provider_on_normal_path() -> None:
    config = build_config(default_provider=ProviderName.OPENAI, fallback_provider=ProviderName.ANTHROPIC)
    recorder = RecordingRouteDecisionRecorder()
    gateway = AIGateway(
        adapters={
            ProviderName.OPENAI: MockProvider(
                config=config.providers[ProviderName.OPENAI],
                provider_name=ProviderName.OPENAI,
                behavior=MockProviderBehavior(prefix="openai"),
            ),
            ProviderName.ANTHROPIC: MockProvider(
                config=config.providers[ProviderName.ANTHROPIC],
                provider_name=ProviderName.ANTHROPIC,
                behavior=MockProviderBehavior(prefix="anthropic"),
            ),
        },
        config=config,
        route_decision_recorder=recorder,
    )

    response = gateway.generate(make_request())

    assert response.provider is ProviderName.OPENAI
    assert response.model == "gpt-default"
    assert response.metadata["fallback_used"] is False
    assert recorder.decisions[0].primary_provider is ProviderName.OPENAI
    assert recorder.decisions[0].fallback_provider is ProviderName.ANTHROPIC


def test_falls_back_to_secondary_provider_on_retryable_failure() -> None:
    config = build_config(default_provider=ProviderName.OPENAI, fallback_provider=ProviderName.ANTHROPIC)
    gateway = AIGateway(
        adapters={
            ProviderName.OPENAI: MockProvider(
                config=config.providers[ProviderName.OPENAI],
                provider_name=ProviderName.OPENAI,
                behavior=MockProviderBehavior(prefix="openai", retryable_failure_count=1),
            ),
            ProviderName.ANTHROPIC: MockProvider(
                config=config.providers[ProviderName.ANTHROPIC],
                provider_name=ProviderName.ANTHROPIC,
                behavior=MockProviderBehavior(prefix="anthropic"),
            ),
        },
        config=config,
    )

    response = gateway.generate(make_request())

    assert response.provider is ProviderName.ANTHROPIC
    assert response.model == "claude-default"
    assert response.metadata["fallback_used"] is True
    assert response.metadata["primary_error"]["retryable"] is True


def test_does_not_fallback_on_non_retryable_failure_when_policy_forbids_it() -> None:
    config = build_config(default_provider=ProviderName.OPENAI, fallback_provider=ProviderName.ANTHROPIC)
    gateway = AIGateway(
        adapters={
            ProviderName.OPENAI: MockProvider(
                config=config.providers[ProviderName.OPENAI],
                provider_name=ProviderName.OPENAI,
                behavior=MockProviderBehavior(prefix="openai", non_retryable_failure_count=1),
            ),
            ProviderName.ANTHROPIC: MockProvider(
                config=config.providers[ProviderName.ANTHROPIC],
                provider_name=ProviderName.ANTHROPIC,
                behavior=MockProviderBehavior(prefix="anthropic"),
            ),
        },
        config=config,
    )

    try:
        gateway.generate(make_request())
    except ProviderError as error:
        assert error.retryable is False
    else:
        raise AssertionError("Expected ProviderError to be raised.")


def test_route_selection_differs_by_risk_and_task_category() -> None:
    config = build_config(default_provider=ProviderName.OPENAI, fallback_provider=ProviderName.ANTHROPIC)
    gateway = AIGateway(
        adapters={
            ProviderName.OPENAI: MockProvider(
                config=config.providers[ProviderName.OPENAI],
                provider_name=ProviderName.OPENAI,
                behavior=MockProviderBehavior(prefix="openai"),
            ),
            ProviderName.ANTHROPIC: MockProvider(
                config=config.providers[ProviderName.ANTHROPIC],
                provider_name=ProviderName.ANTHROPIC,
                behavior=MockProviderBehavior(prefix="anthropic"),
            ),
        },
        config=config,
    )

    summary_response = gateway.generate(
        make_request(task_category=TaskCategory.SUMMARIZATION, risk_level=RiskLevel.LOW)
    )
    approval_response = gateway.generate(
        make_request(task_category=TaskCategory.APPROVAL, risk_level=RiskLevel.HIGH)
    )

    assert summary_response.model == "gpt-fast"
    assert approval_response.model == "gpt-strong"
    assert summary_response.route_decision.reason != approval_response.route_decision.reason


def test_mock_provider_returns_deterministic_output_and_usage_metadata() -> None:
    config = build_config(default_provider=ProviderName.MOCK, fallback_provider=None)
    gateway = AIGateway(
        adapters={
            ProviderName.MOCK: MockProvider(
                config=config.providers[ProviderName.MOCK],
                behavior=MockProviderBehavior(prefix="deterministic"),
            ),
        },
        config=config,
    )

    response = gateway.generate(
        make_request(task_category=TaskCategory.SUMMARIZATION, risk_level=RiskLevel.LOW, allow_fallback=False)
    )

    assert (
        response.output_text
        == "deterministic|provider=mock|model=mock-fast|task=summarization|risk=low|prompt=Summarize the change request"
    )
    assert response.usage.input_tokens == 4
    assert response.usage.output_tokens > 0
    assert response.usage.total_tokens == response.usage.input_tokens + response.usage.output_tokens
    assert response.usage.latency_ms == 5
    assert response.usage.estimated_cost_usd is not None
