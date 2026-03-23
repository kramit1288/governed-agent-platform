"""Ingest seeded support documents into pgvector-backed retrieval storage."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
for package in ("db", "retrieval"):
    src = ROOT / "packages" / package / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))

from db.session import create_db_engine, create_session_factory
from retrieval import DeterministicEmbeddingProvider, PgVectorRetrievalStore, RetrievalService

SEED_DOCS_PATH = ROOT / "data" / "seed" / "docs.json"


def main() -> None:
    engine = create_db_engine()
    session_factory = create_session_factory(engine)
    with session_factory() as session:
        with SEED_DOCS_PATH.open("r", encoding="utf-8") as handle:
            documents = json.load(handle)
        service = RetrievalService(
            store=PgVectorRetrievalStore(session),
            embedding_provider=DeterministicEmbeddingProvider(),
        )
        chunks = service.ingest_documents(documents)
        session.commit()
    print(f"Ingested {len(chunks)} document chunks from {SEED_DOCS_PATH}.")


if __name__ == "__main__":
    main()
