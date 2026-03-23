"""Eval case models and JSON case loading helpers."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class EvalExpectation(BaseModel):
    """Expected properties used by small deterministic scorers."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str | None = None
    requires_approval: bool | None = None
    min_citations: int = Field(default=0, ge=0)
    response_contains: list[str] = Field(default_factory=list)
    response_format: str | None = None
    max_latency_ms: int = Field(default=1000, ge=1)
    max_cost_usd: float | None = Field(default=None, ge=0.0)


class EvalCase(BaseModel):
    """Versioned offline eval case definition."""

    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1)
    version: str = Field(min_length=1)
    description: str
    input_text: str
    tenant_id: str = Field(min_length=1)
    context: dict[str, object] = Field(default_factory=dict)
    expectation: EvalExpectation
    tags: list[str] = Field(default_factory=list)

    @property
    def persisted_key(self) -> str:
        return f"{self.key}:{self.version}"


def load_eval_cases(case_directory: Path) -> list[EvalCase]:
    """Load all JSON eval cases from a directory in deterministic order."""

    cases: list[EvalCase] = []
    for path in sorted(case_directory.glob("*.json")):
        with path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
        if isinstance(payload, list):
            cases.extend(EvalCase.model_validate(item) for item in payload)
        else:
            cases.append(EvalCase.model_validate(payload))
    return cases
