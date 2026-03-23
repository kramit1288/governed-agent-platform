"""Filter helpers for explicit retrieval queries."""

from __future__ import annotations

from retrieval.types import RetrievalFilter


def matches_filter(record: dict[str, object], retrieval_filter: RetrievalFilter) -> bool:
    """Return whether a record matches the explicit retrieval filter."""

    if str(record["tenant_id"]) != retrieval_filter.tenant_id:
        return False
    if retrieval_filter.source_type is not None and str(record["source_type"]) != retrieval_filter.source_type:
        return False
    if retrieval_filter.source_id is not None and str(record["source_id"]) != retrieval_filter.source_id:
        return False
    if retrieval_filter.object_id is not None and str(record.get("object_id")) != retrieval_filter.object_id:
        return False
    return True
