"""Unit tests for deterministic retrieval behavior."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from db.base import Base
from retrieval import DeterministicEmbeddingProvider, DocumentChunker, RetrievalFilter, RetrievalService
from retrieval.citations import package_citations
from retrieval.chunking import ChunkingConfig
from retrieval.store import PgVectorRetrievalStore

ROOT = Path(__file__).resolve().parents[3]
SEED_DOCS = ROOT / "data" / "seed" / "docs.json"


def load_seed_docs() -> list[dict[str, object]]:
    with SEED_DOCS.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_chunking_produces_deterministic_boundaries() -> None:
    document = load_seed_docs()[0]
    chunker = DocumentChunker(ChunkingConfig(max_chars=60, overlap_chars=10))

    first = chunker.chunk_document(document)
    second = chunker.chunk_document(document)

    assert [chunk.content for chunk in first] == [chunk.content for chunk in second]
    assert [chunk.chunk_index for chunk in first] == list(range(len(first)))
    assert len(first) > 1


def test_retrieval_returns_top_k_results_for_seeded_data() -> None:
    service = RetrievalService.from_seed_data()

    chunks, citations = service.search(
        query="refund approval",
        retrieval_filter=RetrievalFilter(tenant_id="tenant-1", source_type="support_doc", top_k=1),
    )

    assert len(chunks) == 1
    assert chunks[0].source_id == "DOC-100"
    assert citations[0].source_id == "DOC-100"


def test_tenant_filtering_prevents_cross_tenant_retrieval() -> None:
    service = RetrievalService.from_seed_data()

    chunks, _ = service.search(
        query="support handbook",
        retrieval_filter=RetrievalFilter(tenant_id="tenant-1", source_type="support_doc", top_k=5),
    )

    assert all(chunk.tenant_id == "tenant-1" for chunk in chunks)
    assert all(chunk.source_id != "DOC-200" for chunk in chunks)


def test_optional_metadata_filters_work() -> None:
    service = RetrievalService.from_seed_data()

    chunks, _ = service.search(
        query="refund",
        retrieval_filter=RetrievalFilter(
            tenant_id="tenant-1",
            source_type="support_doc",
            source_id="DOC-100",
            object_id="DOC-100",
            top_k=5,
        ),
    )

    assert chunks
    assert all(chunk.source_id == "DOC-100" for chunk in chunks)
    assert all(chunk.object_id == "DOC-100" for chunk in chunks)


def test_citation_packaging_produces_stable_output() -> None:
    service = RetrievalService.from_seed_data()
    chunks, _ = service.search(
        query="incident communication",
        retrieval_filter=RetrievalFilter(tenant_id="tenant-1", source_type="support_doc", top_k=1),
    )

    citations = package_citations(chunks)

    assert citations[0].citation_id == f"{chunks[0].source_id}:{chunks[0].chunk_index}"
    assert citations[0].snippet == chunks[0].content[:180]


def test_pgvector_store_python_fallback_returns_ranked_results() -> None:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        service = RetrievalService(
            store=PgVectorRetrievalStore(session),
            embedding_provider=DeterministicEmbeddingProvider(),
        )
        service.ingest_documents(load_seed_docs())

        chunks, _ = service.search(
            query="payment outage incident",
            retrieval_filter=RetrievalFilter(tenant_id="tenant-1", source_type="support_doc", top_k=2),
        )

        assert chunks
        assert chunks[0].tenant_id == "tenant-1"
