"""Add pgvector-backed document chunk storage for retrieval."""

from __future__ import annotations

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260322_0002"
down_revision = "20260313_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.String(length=100), nullable=False),
        sa.Column("source_type", sa.String(length=50), nullable=False),
        sa.Column("source_id", sa.String(length=100), nullable=False),
        sa.Column("object_id", sa.String(length=100), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("content", sa.String(length=4000), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("chunk_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("embedding", Vector(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_document_chunks")),
        sa.UniqueConstraint(
            "tenant_id",
            "source_type",
            "source_id",
            "chunk_index",
            name="uq_document_chunks_source_chunk",
        ),
    )
    op.create_index(op.f("ix_document_chunks_tenant_id"), "document_chunks", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_source_type"), "document_chunks", ["source_type"], unique=False)
    op.create_index(op.f("ix_document_chunks_source_id"), "document_chunks", ["source_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_object_id"), "document_chunks", ["object_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_content_hash"), "document_chunks", ["content_hash"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_chunks_content_hash"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_object_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_source_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_source_type"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_tenant_id"), table_name="document_chunks")
    op.drop_table("document_chunks")
