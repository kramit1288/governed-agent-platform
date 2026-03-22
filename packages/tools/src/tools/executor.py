"""Explicit guarded tool executor for the V1 tool layer."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeoutError
from time import perf_counter

from pydantic import ValidationError

from tools.permissions import ToolPermissionError, can_execute_without_approval
from tools.registry import ToolRegistry
from tools.schemas import ToolCall, ToolDefinition, ToolExecutionMetadata, ToolResult, ToolStatus, utc_now


class ToolExecutionError(RuntimeError):
    """Raised when tool execution fails after validation and retries."""


class RetryableToolError(RuntimeError):
    """Raised by implementations that should be retried by the executor."""


class ToolExecutor:
    """Validates tool calls, applies guardrails, and returns standard results."""

    def __init__(self, registry: ToolRegistry) -> None:
        self._registry = registry

    def execute(self, call: ToolCall) -> ToolResult:
        """Execute a tool call through validation, timeout, and retry wrappers."""

        definition = self._registry.get(call.name)
        started_at = utc_now()
        started_clock = perf_counter()
        attempts = 0
        retried = False

        try:
            validated_input = definition.input_schema.model_validate(call.arguments)
        except ValidationError as exc:
            completed_at = utc_now()
            return ToolResult(
                tool_name=call.name,
                status=ToolStatus.FAILED,
                error=f"Invalid tool arguments: {exc}",
                metadata=self._build_metadata(
                    definition=definition,
                    tenant_id=call.arguments.get("tenant_id"),
                    attempts=1,
                    started_at=started_at,
                    completed_at=completed_at,
                    duration_ms=int((perf_counter() - started_clock) * 1000),
                    retried=False,
                ),
            )

        while attempts <= definition.retry_count:
            attempts += 1
            try:
                output = self._run_with_timeout(definition=definition, validated_input=validated_input)
                completed_at = utc_now()
                duration_ms = int((perf_counter() - started_clock) * 1000)
                if not can_execute_without_approval(definition):
                    return ToolResult(
                        tool_name=definition.name,
                        status=ToolStatus.APPROVAL_REQUIRED,
                        requires_approval=True,
                        preview_payload=output.preview_payload or output.output,
                        metadata=self._build_metadata(
                            definition=definition,
                            tenant_id=getattr(validated_input, "tenant_id", None),
                            attempts=attempts,
                            started_at=started_at,
                            completed_at=completed_at,
                            duration_ms=duration_ms,
                            retried=retried,
                        ),
                    )

                return ToolResult(
                    tool_name=definition.name,
                    status=ToolStatus.SUCCEEDED,
                    output=output.output,
                    metadata=self._build_metadata(
                        definition=definition,
                        tenant_id=getattr(validated_input, "tenant_id", None),
                        attempts=attempts,
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_ms=duration_ms,
                        retried=retried,
                    ),
                )
            except (RetryableToolError, TimeoutError) as exc:
                if attempts > definition.retry_count:
                    completed_at = utc_now()
                    return ToolResult(
                        tool_name=definition.name,
                        status=ToolStatus.FAILED,
                        error=str(exc),
                        metadata=self._build_metadata(
                            definition=definition,
                            tenant_id=getattr(validated_input, "tenant_id", None),
                            attempts=attempts,
                            started_at=started_at,
                            completed_at=completed_at,
                            duration_ms=int((perf_counter() - started_clock) * 1000),
                            retried=retried,
                        ),
                    )
                retried = True
            except (ToolPermissionError, ToolExecutionError) as exc:
                completed_at = utc_now()
                return ToolResult(
                    tool_name=definition.name,
                    status=ToolStatus.FAILED,
                    error=str(exc),
                    metadata=self._build_metadata(
                        definition=definition,
                        tenant_id=getattr(validated_input, "tenant_id", None),
                        attempts=attempts,
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_ms=int((perf_counter() - started_clock) * 1000),
                        retried=retried,
                    ),
                )
            except Exception as exc:
                completed_at = utc_now()
                return ToolResult(
                    tool_name=definition.name,
                    status=ToolStatus.FAILED,
                    error=f"Tool execution failed: {exc}",
                    metadata=self._build_metadata(
                        definition=definition,
                        tenant_id=getattr(validated_input, "tenant_id", None),
                        attempts=attempts,
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_ms=int((perf_counter() - started_clock) * 1000),
                        retried=retried,
                    ),
                )

        completed_at = utc_now()
        return ToolResult(
            tool_name=definition.name,
            status=ToolStatus.FAILED,
            error="Tool execution exhausted retries.",
            metadata=self._build_metadata(
                definition=definition,
                tenant_id=getattr(validated_input, "tenant_id", None),
                attempts=attempts,
                started_at=started_at,
                completed_at=completed_at,
                duration_ms=int((perf_counter() - started_clock) * 1000),
                retried=retried,
            ),
        )

    @staticmethod
    def _run_with_timeout(*, definition: ToolDefinition, validated_input: object):
        with ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(definition.handler, validated_input)
            try:
                return future.result(timeout=definition.timeout_ms / 1000)
            except FutureTimeoutError as exc:
                future.cancel()
                raise TimeoutError(
                    f"Tool '{definition.name}' timed out after {definition.timeout_ms} ms."
                ) from exc

    @staticmethod
    def _build_metadata(
        *,
        definition: ToolDefinition,
        tenant_id: str | None,
        attempts: int,
        started_at,
        completed_at,
        duration_ms: int,
        retried: bool,
    ) -> ToolExecutionMetadata:
        return ToolExecutionMetadata(
            tool_name=definition.name,
            risk_level=definition.risk_level,
            requires_approval=definition.requires_approval,
            tenant_id=tenant_id,
            attempts=attempts,
            timeout_ms=definition.timeout_ms,
            started_at=started_at,
            completed_at=completed_at,
            duration_ms=duration_ms,
            retried=retried,
        )
