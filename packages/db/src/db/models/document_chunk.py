"""Document chunk persistence model for pgvector-backed retrieval."""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from pgvector.sqlalchemy import Vector
from sqlalchemy import Integer, JSON, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base, TimestampMixin

if TYPE_CHECKING:
    pass

EMBEDDING_DIMENSION = 8
JSON_DOCUMENT = JSON().with_variant(JSONB, "postgresql")
VECTOR_DOCUMENT = JSON().with_variant(Vector(EMBEDDING_DIMENSION), "postgresql")


class DocumentChunk(TimestampMixin, Base):
    """Chunked source document stored for tenant-scoped retrieval."""

    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "source_type",
            "source_id",
            "chunk_index",
            name="uq_document_chunks_source_chunk",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    source_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    object_id: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(String(4000), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    chunk_metadata: Mapped[dict | None] = mapped_column(JSON_DOCUMENT, nullable=True)
    embedding: Mapped[list[float]] = mapped_column(VECTOR_DOCUMENT, nullable=False)
