"""Seeded ticket lookup tool implementation."""

from __future__ import annotations

from tools.implementations._seed_data import find_record
from tools.permissions import require_tenant_match
from tools.schemas import GetTicketInput, ToolExecutionOutput


def get_ticket(arguments: GetTicketInput) -> ToolExecutionOutput:
    """Return a deterministic seeded ticket for the requested tenant."""

    ticket = find_record("tickets", "ticket_id", arguments.ticket_id)
    require_tenant_match(
        expected_tenant_id=arguments.tenant_id,
        actual_tenant_id=str(ticket["tenant_id"]),
        resource_name=f"ticket {arguments.ticket_id}",
    )
    return ToolExecutionOutput(output={"ticket": ticket})
