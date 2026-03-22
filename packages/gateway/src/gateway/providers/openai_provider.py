"""OpenAI adapter isolated behind the gateway provider contract."""

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


class OpenAIProvider:
    """Thin adapter around the OpenAI Responses API."""

    name = ProviderName.OPENAI

    def __init__(
        self,
        *,
        config: ProviderConfig,
        client: httpx.Client | None = None,
    ) -> None:
        self._config = config
        self._client = client or httpx.Client(
            base_url=config.base_url or "https://api.openai.com/v1",
            timeout=config.timeout_seconds,
        )

    def is_configured(self) -> bool:
        return bool(self._config.api_key)

    def generate(self, *, request: ModelRequest, model: str) -> ModelResponse:
        if not self.is_configured():
            raise ProviderError(
                provider=self.name,
                model=model,
                message="OpenAI API key is not configured.",
                retryable=False,
            )

        payload: dict[str, object] = {
            "model": model,
            "input": request.prompt,
        }
        if request.temperature is not None:
            payload["temperature"] = request.temperature
        if request.max_output_tokens is not None:
            payload["max_output_tokens"] = request.max_output_tokens

        started_at = time.perf_counter()
        try:
            response = self._client.post(
                "/responses",
                headers={
                    "Authorization": f"Bearer {self._config.api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        except httpx.TimeoutException as exc:
            raise ProviderError(
                provider=self.name,
                model=model,
                message="OpenAI request timed out.",
                retryable=True,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ProviderError(
                provider=self.name,
                model=model,
                message=f"OpenAI request failed with status {exc.response.status_code}.",
                retryable=exc.response.status_code >= 500 or exc.response.status_code == 429,
                status_code=exc.response.status_code,
            ) from exc
        except httpx.HTTPError as exc:
            raise ProviderError(
                provider=self.name,
                model=model,
                message="OpenAI request failed.",
                retryable=True,
            ) from exc

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        data = response.json()
        usage = data.get("usage", {})
        output_text = _extract_openai_text(data)
        return ModelResponse(
            provider=self.name,
            model=model,
            output_text=output_text,
            stop_reason=data.get("status"),
            usage=UsageStats(
                input_tokens=int(usage.get("input_tokens", 0)),
                output_tokens=int(usage.get("output_tokens", 0)),
                total_tokens=int(usage.get("total_tokens", 0)),
                latency_ms=latency_ms,
                estimated_cost_usd=None,
            ),
            metadata={"response_id": data.get("id")},
        )


def _extract_openai_text(payload: dict[str, object]) -> str:
    output_text = payload.get("output_text")
    if isinstance(output_text, str):
        return output_text

    output = payload.get("output", [])
    if not isinstance(output, list):
        return ""

    parts: list[str] = []
    for item in output:
        if not isinstance(item, dict):
            continue
        content = item.get("content", [])
        if not isinstance(content, list):
            continue
        for block in content:
            if isinstance(block, dict) and block.get("type") == "output_text":
                text = block.get("text")
                if isinstance(text, str):
                    parts.append(text)
    return "".join(parts)
