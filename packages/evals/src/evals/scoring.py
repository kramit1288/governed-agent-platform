"""Small deterministic scoring functions for V1 evals."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from evals.cases import EvalCase


class ScoreCard(BaseModel):
    """Readable breakdown of eval scoring dimensions."""

    model_config = ConfigDict(extra="forbid")

    groundedness: float = Field(ge=0.0, le=1.0)
    tool_choice: float = Field(ge=0.0, le=1.0)
    approval_trigger: float = Field(ge=0.0, le=1.0)
    response_usefulness: float = Field(ge=0.0, le=1.0)
    format_correctness: float = Field(ge=0.0, le=1.0)
    citation_presence: float = Field(ge=0.0, le=1.0)
    latency_signal: float = Field(ge=0.0, le=1.0)
    cost_signal: float = Field(ge=0.0, le=1.0)

    @property
    def total_score(self) -> float:
        values = [
            self.groundedness,
            self.tool_choice,
            self.approval_trigger,
            self.response_usefulness,
            self.format_correctness,
            self.citation_presence,
            self.latency_signal,
            self.cost_signal,
        ]
        return sum(values) / len(values)


class PlatformEvalOutput(BaseModel):
    """Normalized platform behavior captured for scoring."""

    model_config = ConfigDict(extra="forbid")

    response_text: str
    tool_name: str | None = None
    requires_approval: bool = False
    citations: list[dict[str, object]] = Field(default_factory=list)
    latency_ms: int = Field(ge=0)
    estimated_cost_usd: float | None = Field(default=None, ge=0.0)


def score_case(case: EvalCase, output: PlatformEvalOutput) -> ScoreCard:
    """Score a single eval case with small explainable heuristics."""

    response_lower = output.response_text.lower()
    expected = case.expectation
    response_contains = all(token.lower() in response_lower for token in expected.response_contains)
    citation_count = len(output.citations)
    return ScoreCard(
        groundedness=1.0 if citation_count >= expected.min_citations else 0.0,
        tool_choice=_binary(expected.tool_name is None or output.tool_name == expected.tool_name),
        approval_trigger=_binary(
            expected.requires_approval is None or output.requires_approval == expected.requires_approval
        ),
        response_usefulness=_binary(response_contains),
        format_correctness=_binary(_matches_format(output.response_text, expected.response_format)),
        citation_presence=_binary(citation_count >= expected.min_citations),
        latency_signal=_binary(output.latency_ms <= expected.max_latency_ms),
        cost_signal=_binary(_matches_cost(output.estimated_cost_usd, expected.max_cost_usd)),
    )


def _matches_format(response_text: str, expected_format: str | None) -> bool:
    if expected_format is None:
        return True
    if expected_format == "bullets":
        return "\n-" in response_text or "\n1." in response_text
    if expected_format == "paragraph":
        return "\n-" not in response_text and "\n1." not in response_text
    return False


def _matches_cost(actual_cost: float | None, max_cost: float | None) -> bool:
    if max_cost is None:
        return actual_cost is not None
    if actual_cost is None:
        return False
    return actual_cost <= max_cost


def _binary(condition: bool) -> float:
    return 1.0 if condition else 0.0
