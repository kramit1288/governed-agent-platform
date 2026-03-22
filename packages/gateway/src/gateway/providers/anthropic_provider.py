"""Anthropic adapter isolated behind the gateway provider contract."""

from __future__ import annotations

import time

import httpx

from gateway.config import ProviderConfig
from gateway.types import (
    ModelRequest,
    ModelResponse,
    ProviderError,
    ProviderName,
    UsageStats,
)


class AnthropicProvider:
    """Thin adapter around the Anthropic Messages API."""

    name = ProviderName.ANTHROPIC

    def __init__(
        self,
        *,
        config: ProviderConfig,
        client: httpx.Client | None = None,
    ) -> None:
        self._config = config
        self._client = client or httpx.Client(
            base_url=config.base_url or "https://api.anthropic.com/v1",
            timeout=config.timeout_seconds,
        )

    def is_configured(self) -> bool:
        return bool(self._config.api_key)

    def generate(self, *, request: ModelRequest, model: str) -> ModelResponse:
        if not self.is_configured():
            raise ProviderError(
                provider=self.name,
                model=model,
                message="Anthropic API key is not configured.",
                retryable=False,
            )

        payload: dict[str, object] = {
            "model": model,
            "messages": [{"role": "user", "content": request.prompt}],
            "max_tokens": request.max_output_tokens or 512,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature

        started_at = time.perf_counter()
        try:
            response = self._client.post(
                "/messages",
                headers={
                    "x-api-key": self._config.api_key or "",
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderError(
                provider=self.name,
                model=model,
                message="Anthropic request timed out.",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                provider=self.name,
                model=model,
                message=f"Anthropic request failed with status {exc.response.status_code}.",
                retryable=exc.response.status_code >= 500 or exc.response.status_code == 429,
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                provider=self.name,
                model=model,
                message="Anthropic request failed.",
                retryable=True,
            ) from exc

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        data = response.json()
        usage = data.get("usage", {})
        return ModelResponse(
            provider=self.name,
            model=model,
            output_text=_extract_anthropic_text(data),
            stop_reason=data.get("stop_reason"),
            usage=UsageStats(
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
                total_tokens=int(usage.get("input_tokens", 0)) + int(usage.get("output_tokens", 0)),
                latency_ms=latency_ms,
                estimated_cost_usd=None,
            ),
            metadata={"message_id": data.get("id")},
        )


def _extract_anthropic_text(payload: dict[str, object]) -> str:
    content = payload.get("content", [])
    if not isinstance(content, list):
        return ""

    parts: list[str] = []
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            text = block.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "".join(parts)
