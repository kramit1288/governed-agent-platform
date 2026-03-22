"""Seeded customer lookup tool implementation."""

from __future__ import annotations

from tools.implementations._seed_data import find_record
from tools.permissions import require_tenant_match
from tools.schemas import GetCustomerInput, ToolExecutionOutput


def get_customer(arguments: GetCustomerInput) -> ToolExecutionOutput:
    """Return a deterministic seeded customer for the requested tenant."""

    customer = find_record("customers", "customer_id", arguments.customer_id)
    require_tenant_match(
        expected_tenant_id=arguments.tenant_id,
        actual_tenant_id=str(customer["tenant_id"]),
        resource_name=f"customer {arguments.customer_id}",
    )
    return ToolExecutionOutput(output={"customer": customer})
