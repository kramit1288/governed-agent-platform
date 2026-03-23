"""Citation packaging for retrieval results."""

from __future__ import annotations

from retrieval.types import Citation, RetrievedChunk


def package_citations(chunks: list[RetrievedChunk]) -> list[Citation]:
    """Build stable UI-friendly citations from retrieved chunks."""

    citations: list[Citation] = []
    for chunk in chunks:
        title = chunk.metadata.get("title")
        citations.append(
            Citation(
                citation_id=f"{chunk.source_id}:{chunk.chunk_index}",
                source_type=chunk.source_type,
                source_id=chunk.source_id,
                object_id=chunk.object_id,
                title=str(title) if title is not None else None,
                snippet=chunk.content[:180],
                chunk_index=chunk.chunk_index,
            )
        )
    return citations
