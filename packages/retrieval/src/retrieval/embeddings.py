"""Embedding abstractions for retrieval indexing and query encoding."""

from __future__ import annotations

import hashlib
import math
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Small embedding abstraction used by ingestion and retrieval."""

    dimension: int

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for the provided texts."""


class DeterministicEmbeddingProvider:
    """Deterministic hash-based embeddings for tests and local ingestion."""

    def __init__(self, dimension: int = 8) -> None:
        self.dimension = dimension

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [_embed_text(text, self.dimension) for text in texts]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    """Compute cosine similarity for retrieval fallback and tests."""

    if not left or not right:
        return 0.0
    numerator = sum(a * b for a, b in zip(left, right, strict=False))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return numerator / (left_norm * right_norm)


def _embed_text(text: str, dimension: int) -> list[float]:
    values = [0.0 for _ in range(dimension)]
    tokens = [token for token in text.lower().split() if token]
    if not tokens:
        return values
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        dimension_index = digest[0] % dimension
        sign = 1.0 if digest[1] % 2 == 0 else -1.0
        values[dimension_index] += sign
    norm = math.sqrt(sum(value * value for value in values))
    if norm == 0:
        return [0.0 for _ in values]
    return [value / norm for value in values]
