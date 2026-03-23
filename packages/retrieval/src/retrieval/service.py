"""Explicit retrieval service for seeded document ingestion and search."""

from __future__ import annotations

import json
from pathlib import Path

from retrieval.chunking import DocumentChunker
from retrieval.citations import package_citations
from retrieval.embeddings import DeterministicEmbeddingProvider, EmbeddingProvider
from retrieval.store import InMemoryRetrievalStore, RetrievalStore
from retrieval.types import Citation, ChunkRecord, RetrievalFilter, RetrievedChunk

ROOT = Path(__file__).resolve().parents[4]
SEED_DOCS_PATH = ROOT / "data" / "seed" / "docs.json"


class RetrievalService:
    """Small retrieval service that owns chunking, embeddings, and citations."""

    def __init__(
        self,
        *,
        store: RetrievalStore,
        embedding_provider: EmbeddingProvider | None = None,
        chunker: DocumentChunker | None = None,
    ) -> None:
        self._store = store
        self._embedding_provider = embedding_provider or DeterministicEmbeddingProvider()
        self._chunker = chunker or DocumentChunker()

    def ingest_documents(self, documents: list[dict[str, object]]) -> list[ChunkRecord]:
        """Chunk, embed, and store seeded documents."""

        chunks: list[ChunkRecord] = []
        for document in documents:
            chunks.extend(self._chunker.chunk_document(document))
        embeddings = self._embedding_provider.embed([chunk.content for chunk in chunks])
        enriched = [
            chunk.model_copy(update={"embedding": embedding})
            for chunk, embedding in zip(chunks, embeddings, strict=True)
        ]
        self._store.upsert_chunks(enriched)
        return enriched

    def search(
        self,
        *,
        query: str,
        retrieval_filter: RetrievalFilter,
    ) -> tuple[list[RetrievedChunk], list[Citation]]:
        """Retrieve top-k relevant chunks and package citations."""

        query_embedding = self._embedding_provider.embed([query])[0]
        chunks = self._store.query(query_embedding=query_embedding, retrieval_filter=retrieval_filter)
        return chunks, package_citations(chunks)

    @classmethod
    def from_seed_data(
        cls,
        *,
        embedding_provider: EmbeddingProvider | None = None,
        chunker: DocumentChunker | None = None,
        seed_docs_path: Path = SEED_DOCS_PATH,
    ) -> "RetrievalService":
        """Build a deterministic retrieval service preloaded from local seed data."""

        with seed_docs_path.open("r", encoding="utf-8") as handle:
            documents = json.load(handle)
        service = cls(
            store=InMemoryRetrievalStore(),
            embedding_provider=embedding_provider,
            chunker=chunker,
        )
        service.ingest_documents(documents)
        return service
