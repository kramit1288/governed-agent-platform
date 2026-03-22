"""Risky refund draft tool that produces an approval preview only."""

from __future__ import annotations

from tools.implementations._seed_data import find_record
from tools.permissions import require_tenant_match
from tools.schemas import DraftRefundRequestInput, ToolExecutionOutput


def draft_refund_request(arguments: DraftRefundRequestInput) -> ToolExecutionOutput:
    """Build a deterministic refund preview without executing any side effect."""

    customer = find_record("customers", "customer_id", arguments.customer_id)
    ticket = find_record("tickets", "ticket_id", arguments.ticket_id)
    require_tenant_match(
        expected_tenant_id=arguments.tenant_id,
        actual_tenant_id=str(customer["tenant_id"]),
        resource_name=f"customer {arguments.customer_id}",
    )
    require_tenant_match(
        expected_tenant_id=arguments.tenant_id,
        actual_tenant_id=str(ticket["tenant_id"]),
        resource_name=f"ticket {arguments.ticket_id}",
    )
    preview_payload = {
        "action": "draft_refund_request",
        "customer_id": arguments.customer_id,
        "ticket_id": arguments.ticket_id,
        "amount": round(arguments.amount, 2),
        "currency": customer["currency"],
        "reason": arguments.reason,
        "customer_email": customer["email"],
        "ticket_subject": ticket["subject"],
        "execution_mode": "preview_only",
    }
    return ToolExecutionOutput(preview_payload=preview_payload)
