"""Simple explicit permission and tenant guardrails for V1 tools."""

from __future__ import annotations

from tools.schemas import ToolDefinition, ToolRiskLevel


class ToolPermissionError(RuntimeError):
    """Raised when a tool call violates explicit V1 permissions."""


def require_tenant_match(*, expected_tenant_id: str, actual_tenant_id: str, resource_name: str) -> None:
    """Reject access when a resource does not belong to the requested tenant."""

    if expected_tenant_id != actual_tenant_id:
        raise ToolPermissionError(
            f"Tenant mismatch for {resource_name}: expected '{expected_tenant_id}' but found '{actual_tenant_id}'."
        )


def can_execute_without_approval(definition: ToolDefinition) -> bool:
    """Return whether the tool may execute without an approval checkpoint."""

    return not definition.requires_approval and definition.risk_level is not ToolRiskLevel.HIGH
