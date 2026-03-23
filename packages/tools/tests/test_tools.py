"""Unit tests for the explicit V1 tool registry and executor."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import sleep

from pydantic import BaseModel, ConfigDict, Field

from tools.executor import RetryableToolError, ToolExecutor
from tools.registry import ToolRegistry
from tools.schemas import ToolCall, ToolDefinition, ToolExecutionOutput, ToolRiskLevel, ToolStatus


def test_registry_exposes_all_v1_tools() -> None:
    registry = ToolRegistry()

    assert [definition.name for definition in registry.list_tools()] == [
        "draft_refund_request",
        "get_customer",
        "get_incident",
        "get_ticket",
        "search_docs",
    ]


def test_schema_validation_rejects_invalid_arguments() -> None:
    executor = ToolExecutor(ToolRegistry())

    result = executor.execute(
        ToolCall(
            name="draft_refund_request",
            arguments={
                "customer_id": "C-100",
                "ticket_id": "T-100",
                "amount": -10,
                "reason": "refund",
                "tenant_id": "tenant-1",
            },
        )
    )

    assert result.status is ToolStatus.FAILED
    assert "Invalid tool arguments" in result.error


def test_read_tools_execute_successfully_with_seeded_data() -> None:
    executor = ToolExecutor(ToolRegistry())

    ticket_result = executor.execute(
        ToolCall(name="get_ticket", arguments={"ticket_id": "T-100", "tenant_id": "tenant-1"})
    )
    docs_result = executor.execute(
        ToolCall(
            name="search_docs",
            arguments={
                "query": "refund approval",
                "tenant_id": "tenant-1",
                "optional_filters": {"category": "policy"},
            },
        )
    )

    assert ticket_result.status is ToolStatus.SUCCEEDED
    assert ticket_result.output["ticket"]["subject"] == "Duplicate charge on March invoice"
    assert docs_result.status is ToolStatus.SUCCEEDED
    assert docs_result.output["result_count"] == 1
    assert docs_result.output["results"][0]["doc_id"] == "DOC-100"
    assert docs_result.output["results"][0]["title"] == "Refund escalation policy"


def test_risky_tool_returns_preview_and_requires_approval() -> None:
    executor = ToolExecutor(ToolRegistry())

    result = executor.execute(
        ToolCall(
            name="draft_refund_request",
            arguments={
                "customer_id": "C-100",
                "ticket_id": "T-100",
                "amount": 42.5,
                "reason": "Duplicate charge confirmed",
                "tenant_id": "tenant-1",
            },
        )
    )

    assert result.status is ToolStatus.APPROVAL_REQUIRED
    assert result.requires_approval is True
    assert result.preview_payload["execution_mode"] == "preview_only"
    assert result.preview_payload["amount"] == 42.5


def test_tenant_mismatch_is_rejected() -> None:
    executor = ToolExecutor(ToolRegistry())

    result = executor.execute(
        ToolCall(name="get_customer", arguments={"customer_id": "C-200", "tenant_id": "tenant-1"})
    )

    assert result.status is ToolStatus.FAILED
    assert "Tenant mismatch" in result.error


class RetryInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=1)


@dataclass
class RetryState:
    calls: int = 0
    sleep_seconds: float = 0.0
    fail_until: int = 0
    events: list[str] = field(default_factory=list)


def test_timeout_and_retry_wrapper_behavior() -> None:
    state = RetryState(sleep_seconds=0.03, fail_until=1)

    def handler(arguments: RetryInput) -> ToolExecutionOutput:
        state.calls += 1
        state.events.append(arguments.tenant_id)
        if state.calls <= state.fail_until:
            raise RetryableToolError("retry me")
        if state.sleep_seconds:
            sleep(state.sleep_seconds)
        return ToolExecutionOutput(output={"ok": True})

    registry = ToolRegistry(
        definitions=[
            ToolDefinition(
                name="flaky_tool",
                description="Test retry behavior.",
                input_schema=RetryInput,
                risk_level=ToolRiskLevel.LOW,
                requires_approval=False,
                timeout_ms=100,
                retry_count=1,
                handler=handler,
            ),
            ToolDefinition(
                name="slow_tool",
                description="Test timeout behavior.",
                input_schema=RetryInput,
                risk_level=ToolRiskLevel.LOW,
                requires_approval=False,
                timeout_ms=10,
                retry_count=0,
                handler=lambda arguments: (sleep(0.05), ToolExecutionOutput(output={"never": True}))[1],
            ),
        ]
    )
    executor = ToolExecutor(registry)

    retry_result = executor.execute(ToolCall(name="flaky_tool", arguments={"tenant_id": "tenant-1"}))
    timeout_result = executor.execute(ToolCall(name="slow_tool", arguments={"tenant_id": "tenant-1"}))

    assert retry_result.status is ToolStatus.SUCCEEDED
    assert retry_result.metadata.attempts == 2
    assert retry_result.metadata.retried is True
    assert state.events == ["tenant-1", "tenant-1"]
    assert timeout_result.status is ToolStatus.FAILED
    assert "timed out" in timeout_result.error
