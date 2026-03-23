"""Retrieval stores for pgvector-backed and deterministic local search."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from db.models import DocumentChunk
from retrieval.embeddings import cosine_similarity
from retrieval.filters import matches_filter
from retrieval.types import ChunkRecord, RetrievalFilter, RetrievedChunk


class RetrievalStore(Protocol):
    """Storage abstraction used by retrieval services."""

    def upsert_chunks(self, chunks: list[ChunkRecord]) -> None:
        """Persist chunk records."""

    def query(self, *, query_embedding: list[float], retrieval_filter: RetrievalFilter) -> list[RetrievedChunk]:
        """Query stored chunks using embeddings and filters."""


class PgVectorRetrievalStore:
    """Retrieval store backed by SQLAlchemy and pgvector in PostgreSQL."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def upsert_chunks(self, chunks: list[ChunkRecord]) -> None:
        if not chunks:
            return
        for chunk in chunks:
            self._session.execute(
                delete(DocumentChunk).where(
                    DocumentChunk.tenant_id == chunk.tenant_id,
                    DocumentChunk.source_type == chunk.source_type,
                    DocumentChunk.source_id == chunk.source_id,
                    DocumentChunk.chunk_index == chunk.chunk_index,
                )
            )
            self._session.add(
                DocumentChunk(
                    tenant_id=chunk.tenant_id,
                    source_type=chunk.source_type,
                    source_id=chunk.source_id,
                    object_id=chunk.object_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.content,
                    content_hash=chunk.content_hash,
                    chunk_metadata=chunk.metadata,
                    embedding=chunk.embedding,
                )
            )
        self._session.flush()

    def query(self, *, query_embedding: list[float], retrieval_filter: RetrievalFilter) -> list[RetrievedChunk]:
        if self._session.bind is not None and self._session.bind.dialect.name == "postgresql":
            return self._query_postgres(query_embedding=query_embedding, retrieval_filter=retrieval_filter)
        return self._query_python(query_embedding=query_embedding, retrieval_filter=retrieval_filter)

    def _query_postgres(
        self,
        *,
        query_embedding: list[float],
        retrieval_filter: RetrievalFilter,
    ) -> list[RetrievedChunk]:
        distance = DocumentChunk.embedding.cosine_distance(query_embedding)
        statement = (
            select(DocumentChunk, distance.label("distance"))
            .where(DocumentChunk.tenant_id == retrieval_filter.tenant_id)
            .order_by("distance")
            .limit(retrieval_filter.top_k)
        )
        if retrieval_filter.source_type is not None:
            statement = statement.where(DocumentChunk.source_type == retrieval_filter.source_type)
        if retrieval_filter.source_id is not None:
            statement = statement.where(DocumentChunk.source_id == retrieval_filter.source_id)
        if retrieval_filter.object_id is not None:
            statement = statement.where(DocumentChunk.object_id == retrieval_filter.object_id)
        rows = self._session.execute(statement).all()
        return [
            RetrievedChunk(
                tenant_id=row[0].tenant_id,
                source_type=row[0].source_type,
                source_id=row[0].source_id,
                object_id=row[0].object_id,
                chunk_index=row[0].chunk_index,
                content=row[0].content,
                metadata=row[0].chunk_metadata or {},
                score=max(0.0, 1.0 - float(row.distance)),
            )
            for row in rows
        ]

    def _query_python(
        self,
        *,
        query_embedding: list[float],
        retrieval_filter: RetrievalFilter,
    ) -> list[RetrievedChunk]:
        records = list(self._session.scalars(select(DocumentChunk)))
        filtered = [
            record
            for record in records
            if matches_filter(
                {
                    "tenant_id": record.tenant_id,
                    "source_type": record.source_type,
                    "source_id": record.source_id,
                    "object_id": record.object_id,
                },
                retrieval_filter,
            )
        ]
        ranked = sorted(
            filtered,
            key=lambda record: (
                -cosine_similarity(list(record.embedding), query_embedding),
                record.source_id,
                record.chunk_index,
            ),
        )[: retrieval_filter.top_k]
        return [
            RetrievedChunk(
                tenant_id=record.tenant_id,
                source_type=record.source_type,
                source_id=record.source_id,
                object_id=record.object_id,
                chunk_index=record.chunk_index,
                content=record.content,
                metadata=record.chunk_metadata or {},
                score=max(0.0, cosine_similarity(list(record.embedding), query_embedding)),
            )
            for record in ranked
        ]


class InMemoryRetrievalStore:
    """Deterministic in-memory retrieval store for tests and local tooling."""

    def __init__(self, initial_chunks: Iterable[ChunkRecord] | None = None) -> None:
        self._records: list[ChunkRecord] = list(initial_chunks or [])

    def upsert_chunks(self, chunks: list[ChunkRecord]) -> None:
        for chunk in chunks:
            self._records = [
                existing
                for existing in self._records
                if not (
                    existing.tenant_id == chunk.tenant_id
                    and existing.source_type == chunk.source_type
                    and existing.source_id == chunk.source_id
                    and existing.chunk_index == chunk.chunk_index
                )
            ]
            self._records.append(chunk)

    def query(self, *, query_embedding: list[float], retrieval_filter: RetrievalFilter) -> list[RetrievedChunk]:
        filtered = [record for record in self._records if matches_filter(record.model_dump(), retrieval_filter)]
        ranked = sorted(
            filtered,
            key=lambda record: (
                -cosine_similarity(record.embedding, query_embedding),
                record.source_id,
                record.chunk_index,
            ),
        )[: retrieval_filter.top_k]
        return [
            RetrievedChunk(
                tenant_id=record.tenant_id,
                source_type=record.source_type,
                source_id=record.source_id,
                object_id=record.object_id,
                chunk_index=record.chunk_index,
                content=record.content,
                metadata=record.metadata,
                score=max(0.0, cosine_similarity(record.embedding, query_embedding)),
            )
            for record in ranked
        ]
