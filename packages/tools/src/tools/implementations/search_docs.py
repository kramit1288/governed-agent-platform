"""Local seeded document search for deterministic V1 retrieval-style lookups."""

from __future__ import annotations

from typing import Protocol

from tools.implementations._seed_data import load_seed_records
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


class LocalSeedDocumentSearch:
    """Simple seeded document search used by V1 tools and tests."""

    def search(
        self,
        *,
        query: str,
        tenant_id: str,
        filters: SearchDocsFilters | None,
    ) -> list[dict[str, object]]:
        query_terms = {term for term in query.lower().split() if term}
        matches: list[tuple[int, dict[str, object]]] = []
        for document in load_seed_records("docs"):
            if str(document["tenant_id"]) != tenant_id:
                continue
            if filters is not None and not _matches_filters(document, filters):
                continue
            searchable_text = f"{document['title']} {document['content']}".lower()
            score = sum(1 for term in query_terms if term in searchable_text)
            if score > 0:
                matches.append(
                    (
                        score,
                        {
                            "doc_id": document["doc_id"],
                            "title": document["title"],
                            "category": document["category"],
                            "tags": document["tags"],
                            "snippet": str(document["content"])[:160],
                            "score": score,
                        },
                    )
                )
        ordered = sorted(matches, key=lambda item: (-item[0], str(item[1]["doc_id"])))
        return [result for _, result in ordered]


def build_search_docs_tool(backend: DocumentSearchBackend | None = None):
    """Build a handler closure for document search."""

    search_backend = backend or LocalSeedDocumentSearch()

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


def _matches_filters(document: dict[str, object], filters: SearchDocsFilters) -> bool:
    if filters.category is not None and document.get("category") != filters.category:
        return False
    if filters.tags:
        document_tags = {str(tag) for tag in document.get("tags", [])}
        if not set(filters.tags).issubset(document_tags):
            return False
    return True
