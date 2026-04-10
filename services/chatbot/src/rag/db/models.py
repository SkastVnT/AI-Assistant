"""
SQLAlchemy ORM models for the RAG subsystem.

Tables
------
- ``rag_documents`` — ingested source files (PDF, HTML, …)
- ``rag_chunks``    — text chunks with pgvector embeddings

Every row carries a ``tenant_id`` so all future queries can be
scoped per tenant without schema changes.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Uuid,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.rag_settings import get_rag_settings
from .base import Base

_dim = get_rag_settings().embed_dim


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    source_type: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="upload | url | drive | api"
    )
    source_uri: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Original location / URL"
    )
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    object_path: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="MinIO/S3 object key"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    chunks: Mapped[list["RagChunk"]] = relationship(
        back_populates="document", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<RagDocument {self.id!s:.8} title={self.title!r}>"


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("rag_documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(_dim), nullable=True
    )
    metadata_json: Mapped[dict | None] = mapped_column(
        JSONB, nullable=True, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    document: Mapped["RagDocument"] = relationship(back_populates="chunks")

    __table_args__ = (
        Index(
            "ix_rag_chunks_embedding_hnsw",
            embedding,
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<RagChunk {self.id!s:.8} doc={self.document_id!s:.8} idx={self.chunk_index}>"
