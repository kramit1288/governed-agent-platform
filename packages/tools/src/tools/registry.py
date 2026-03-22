"""Explicit registry for schema-driven V1 tools."""

from __future__ import annotations

from tools.implementations.draft_refund_request import draft_refund_request
from tools.implementations.get_customer import get_customer
from tools.implementations.get_incident import get_incident
from tools.implementations.get_ticket import get_ticket
from tools.implementations.search_docs import build_search_docs_tool
from tools.schemas import (
    DraftRefundRequestInput,
    GetCustomerInput,
    GetIncidentInput,
    GetTicketInput,
    SearchDocsInput,
    ToolDefinition,
    ToolRiskLevel,
)


class ToolRegistry:
    """Registry of explicit tool definitions keyed by tool name."""

    def __init__(self, definitions: list[ToolDefinition] | None = None) -> None:
        definition_list = definitions or build_default_tool_definitions()
        self._definitions = {definition.name: definition for definition in definition_list}

    def list_tools(self) -> list[ToolDefinition]:
        """Return registered tools in deterministic name order."""

        return [self._definitions[name] for name in sorted(self._definitions)]

    def get(self, name: str) -> ToolDefinition:
        """Look up a tool definition by name."""

        try:
            return self._definitions[name]
        except KeyError as exc:
            raise KeyError(f"Unknown tool '{name}'.") from exc

    def has(self, name: str) -> bool:
        """Return whether the registry contains a tool."""

        return name in self._definitions


def build_default_tool_definitions() -> list[ToolDefinition]:
    """Return the explicit V1 tool set."""

    return [
        ToolDefinition(
            name="search_docs",
            description="Search seeded local support documents for a tenant.",
            input_schema=SearchDocsInput,
            risk_level=ToolRiskLevel.LOW,
            requires_approval=False,
            timeout_ms=250,
            retry_count=0,
            handler=build_search_docs_tool(),
        ),
        ToolDefinition(
            name="get_ticket",
            description="Load a seeded support ticket by id for a tenant.",
            input_schema=GetTicketInput,
            risk_level=ToolRiskLevel.LOW,
            requires_approval=False,
            timeout_ms=250,
            retry_count=0,
            handler=get_ticket,
        ),
        ToolDefinition(
            name="get_incident",
            description="Load a seeded incident by id for a tenant.",
            input_schema=GetIncidentInput,
            risk_level=ToolRiskLevel.LOW,
            requires_approval=False,
            timeout_ms=250,
            retry_count=0,
            handler=get_incident,
        ),
        ToolDefinition(
            name="get_customer",
            description="Load a seeded customer by id for a tenant.",
            input_schema=GetCustomerInput,
            risk_level=ToolRiskLevel.LOW,
            requires_approval=False,
            timeout_ms=250,
            retry_count=0,
            handler=get_customer,
        ),
        ToolDefinition(
            name="draft_refund_request",
            description="Generate a preview-only refund request draft for approval review.",
            input_schema=DraftRefundRequestInput,
            risk_level=ToolRiskLevel.HIGH,
            requires_approval=True,
            timeout_ms=250,
            retry_count=0,
            handler=draft_refund_request,
        ),
    ]
