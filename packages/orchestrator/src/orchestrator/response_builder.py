"""Response builder that keeps response assembly explicit."""

from __future__ import annotations

from orchestrator.interfaces import AIGateway
from orchestrator.models import RunContext


class ResponseBuilder:
    """Build the final response using the gateway placeholder."""

    def __init__(self, ai_gateway: AIGateway) -> None:
        self._ai_gateway = ai_gateway

    def build(self, context: RunContext) -> str:
        return self._ai_gateway.generate_response(context)
