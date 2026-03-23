"""Typed retrieval contracts for chunk search and citation packaging."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class ChunkRecord(BaseModel):
    """Normalized chunk record used for ingestion and storage boundaries."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    object_id: str | None = None
    chunk_index: int = Field(ge=0)
    content: str = Field(min_length=1)
    content_hash: str = Field(min_length=1)
    metadata: dict[str, object] = Field(default_factory=dict)
    embedding: list[float] = Field(default_factory=list)


class RetrievalFilter(BaseModel):
    """Filter inputs for tenant-scoped retrieval."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=1)
    source_type: str | None = None
    source_id: str | None = None
    object_id: str | None = None
    top_k: int = Field(default=5, ge=1, le=20)


class RetrievedChunk(BaseModel):
    """Retrieved chunk returned by vector search."""

    model_config = ConfigDict(extra="forbid")

    tenant_id: str
    source_type: str
    source_id: str
    object_id: str | None = None
    chunk_index: int
    content: str
    metadata: dict[str, object] = Field(default_factory=dict)
    score: float = Field(ge=0.0)


class Citation(BaseModel):
    """UI-friendly citation package derived from retrieved chunks."""

    model_config = ConfigDict(extra="forbid")

    citation_id: str
    source_type: str
    source_id: str
    object_id: str | None = None
    title: str | None = None
    snippet: str
    chunk_index: int
