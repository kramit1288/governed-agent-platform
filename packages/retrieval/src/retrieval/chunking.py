"""Deterministic chunking for seeded retrieval documents."""

from __future__ import annotations

import hashlib

from pydantic import BaseModel, ConfigDict, Field

from retrieval.types import ChunkRecord


class ChunkingConfig(BaseModel):
    """Small deterministic chunking config for V1 ingestion."""

    model_config = ConfigDict(extra="forbid")

    max_chars: int = Field(default=180, ge=50)
    overlap_chars: int = Field(default=30, ge=0)


class DocumentChunker:
    """Split seeded documents into stable overlapping character chunks."""

    def __init__(self, config: ChunkingConfig | None = None) -> None:
        self._config = config or ChunkingConfig()

    def chunk_document(self, document: dict[str, object]) -> list[ChunkRecord]:
        """Chunk a seeded document into stable `ChunkRecord` items."""

        content = str(document["content"]).strip()
        title = str(document["title"]).strip()
        source_text = f"{title}\n\n{content}"
        slices = _slice_text(
            source_text,
            max_chars=self._config.max_chars,
            overlap_chars=self._config.overlap_chars,
        )
        chunks: list[ChunkRecord] = []
        for index, chunk_text in enumerate(slices):
            chunks.append(
                ChunkRecord(
                    tenant_id=str(document["tenant_id"]),
                    source_type=str(document.get("source_type", "support_doc")),
                    source_id=str(document["doc_id"]),
                    object_id=str(document["doc_id"]),
                    chunk_index=index,
                    content=chunk_text,
                    content_hash=_content_hash(
                        tenant_id=str(document["tenant_id"]),
                        source_id=str(document["doc_id"]),
                        chunk_index=index,
                        content=chunk_text,
                    ),
                    metadata={
                        "title": title,
                        "category": document.get("category"),
                        "tags": document.get("tags", []),
                    },
                )
            )
        return chunks


def _slice_text(text: str, *, max_chars: int, overlap_chars: int) -> list[str]:
    normalized = " ".join(text.split())
    if len(normalized) <= max_chars:
        return [normalized]

    segments: list[str] = []
    start = 0
    step = max_chars - overlap_chars
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        if end < len(normalized):
            boundary = normalized.rfind(" ", start, end)
            if boundary > start:
                end = boundary
        segments.append(normalized[start:end].strip())
        if end >= len(normalized):
            break
        start = max(0, end - overlap_chars)
    return segments


def _content_hash(*, tenant_id: str, source_id: str, chunk_index: int, content: str) -> str:
    payload = f"{tenant_id}:{source_id}:{chunk_index}:{content}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()
