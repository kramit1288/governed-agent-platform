"""Seeded incident lookup tool implementation."""

from __future__ import annotations

from tools.implementations._seed_data import find_record
from tools.permissions import require_tenant_match
from tools.schemas import GetIncidentInput, ToolExecutionOutput


def get_incident(arguments: GetIncidentInput) -> ToolExecutionOutput:
    """Return a deterministic seeded incident for the requested tenant."""

    incident = find_record("incidents", "incident_id", arguments.incident_id)
    require_tenant_match(
        expected_tenant_id=arguments.tenant_id,
        actual_tenant_id=str(incident["tenant_id"]),
        resource_name=f"incident {arguments.incident_id}",
    )
    return ToolExecutionOutput(output={"incident": incident})
