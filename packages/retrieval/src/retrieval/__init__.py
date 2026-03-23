"""Retrieval package."""

from retrieval.chunking import ChunkingConfig, DocumentChunker
from retrieval.citations import package_citations
from retrieval.embeddings import DeterministicEmbeddingProvider, EmbeddingProvider
from retrieval.service import RetrievalService
from retrieval.store import InMemoryRetrievalStore, PgVectorRetrievalStore, RetrievalStore
from retrieval.types import ChunkRecord, Citation, RetrievalFilter, RetrievedChunk

__all__ = [
    "ChunkRecord",
    "ChunkingConfig",
    "Citation",
    "DeterministicEmbeddingProvider",
    "DocumentChunker",
    "EmbeddingProvider",
    "InMemoryRetrievalStore",
    "PgVectorRetrievalStore",
    "RetrievalFilter",
    "RetrievalService",
    "RetrievalStore",
    "RetrievedChunk",
    "package_citations",
]
