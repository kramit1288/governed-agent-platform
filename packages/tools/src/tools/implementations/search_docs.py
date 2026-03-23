"""Document search tool backed by the retrieval package."""

from __future__ import annotations

from typing import Protocol

from retrieval import RetrievalFilter, RetrievalService
from tools.schemas import SearchDocsFilters, SearchDocsInput, ToolExecutionOutput


class DocumentSearchBackend(Protocol):
    """Narrow integration point so retrieval can replace local search later."""

    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        filters: SearchDocsFilters | None,
    ) -> list[dict[str, object]]:
        """Return matching document results."""


class RetrievalDocumentSearch:
    """Adapter that exposes retrieval search to the tool layer."""

    def __init__(self, retrieval_service: RetrievalService | None = None) -> None:
        self._retrieval_service = retrieval_service or RetrievalService.from_seed_data()

    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        filters: SearchDocsFilters | None,
    ) -> list[dict[str, object]]:
        chunks, citations = self._retrieval_service.search(
            query=query,
            retrieval_filter=RetrievalFilter(
                tenant_id=tenant_id,
                source_type="support_doc",
                top_k=10,
            ),
        )
        results_by_doc: dict[str, dict[str, object]] = {}
        for chunk, citation in zip(chunks, citations, strict=True):
            if filters is not None and not _matches_filters(chunk.metadata, filters):
                continue
            existing = results_by_doc.get(citation.source_id)
            candidate = {
                "doc_id": citation.source_id,
                "title": citation.title,
                "category": chunk.metadata.get("category"),
                "tags": chunk.metadata.get("tags", []),
                "snippet": citation.snippet,
                "score": round(chunk.score, 6),
            }
            if existing is None or float(candidate["score"]) > float(existing["score"]):
                results_by_doc[citation.source_id] = candidate
        return sorted(results_by_doc.values(), key=lambda result: (-float(result["score"]), str(result["doc_id"])))


def build_search_docs_tool(backend: DocumentSearchBackend | None = None):
    """Build a handler closure for document search."""

    search_backend = backend or RetrievalDocumentSearch()

    def handler(arguments: SearchDocsInput) -> ToolExecutionOutput:
        results = search_backend.search(
            query=arguments.query,
            tenant_id=arguments.tenant_id,
            filters=arguments.optional_filters,
        )
        return ToolExecutionOutput(
            output={
                "query": arguments.query,
                "results": results,
                "result_count": len(results),
            }
        )

    return handler


def _matches_filters(metadata: dict[str, object], filters: SearchDocsFilters) -> bool:
    if filters.category is not None and metadata.get("category") != filters.category:
        return False
    if filters.tags:
        document_tags = {str(tag) for tag in metadata.get("tags", [])}
        if not set(filters.tags).issubset(document_tags):
            return False
    return True
