"""Core domain models for the RAG platform.

Domain hierarchy:
    Tenant → User
    Tenant → DataSource → Document → DocumentVersion → DocumentChunk
    Tenant → IngestionJob (tracks pipeline runs)
    Tenant → RetrievalTrace (tracks query + retrieval + generation)

Every table carries tenant_id for row-level multi-tenant isolation.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# =============================================================================
# Base
# =============================================================================


class Base(DeclarativeBase):
    """Shared declarative base for all models."""

    pass


class TimestampMixin:
    """Adds created_at / updated_at to any model."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


# =============================================================================
# Enums
# =============================================================================


class SensitivityLevel(enum.StrEnum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class SourceType(enum.StrEnum):
    UPLOAD = "upload"
    S3 = "s3"
    GCS = "gcs"
    GOOGLE_DRIVE = "google_drive"
    WEB_CRAWL = "web_crawl"
    API = "api"


class DocumentStatus(enum.StrEnum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class VersionStatus(enum.StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"
    SUPERSEDED = "superseded"


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# =============================================================================
# Tenant
# =============================================================================


class Tenant(TimestampMixin, Base):
    """Organizational boundary for multi-tenant isolation.

    Every row in the system belongs to exactly one tenant.
    Enables future ReBAC: tenant → org → team → user hierarchy.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(63), nullable=False, unique=True)
    settings: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # relationships
    users: Mapped[list[User]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    data_sources: Mapped[list[DataSource]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )
    documents: Mapped[list[Document]] = relationship(
        back_populates="tenant", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("idx_tenants_slug", "slug"),)


# =============================================================================
# User
# =============================================================================


class User(TimestampMixin, Base):
    """Represents a human or service account within a tenant.

    Auth is not implemented yet — this model provides the FK target
    for auditing (who uploaded, who queried).
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(
        String(50), server_default="member", nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="users")

    __table_args__ = (
        UniqueConstraint("tenant_id", "email", name="uq_users_tenant_email"),
        Index("idx_users_tenant_id", "tenant_id"),
    )


# =============================================================================
# DataSource
# =============================================================================


class DataSource(TimestampMixin, Base):
    """Represents a connection to an external data origin.

    Decouples "where data comes from" from "what documents exist".
    Examples: an S3 bucket, a Google Drive folder, an API endpoint.
    The config JSONB stores connection-specific details (bucket name, API url, etc.)
    — never store raw secrets here; reference secret manager keys instead.
    """

    __tablename__ = "data_sources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType, name="source_type_enum"), nullable=False
    )
    config: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    tenant: Mapped[Tenant] = relationship(back_populates="data_sources")
    documents: Mapped[list[Document]] = relationship(
        back_populates="data_source", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_data_sources_tenant_id", "tenant_id"),
        Index("idx_data_sources_source_type", "source_type"),
    )


# =============================================================================
# Document
# =============================================================================


class Document(TimestampMixin, Base):
    """Logical document identity — survives re-ingestion.

    One document can have many versions (re-uploads, edits).
    Carries shared metadata (title, author, tags, sensitivity, language).
    Status tracks lifecycle: active → archived → deleted.
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    data_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("data_sources.id", ondelete="SET NULL")
    )
    title: Mapped[str] = mapped_column(String(1024), nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text)
    author: Mapped[str | None] = mapped_column(String(255))
    sensitivity_level: Mapped[SensitivityLevel] = mapped_column(
        Enum(SensitivityLevel, name="sensitivity_level_enum"),
        server_default=SensitivityLevel.INTERNAL.value,
        nullable=False,
    )
    language: Mapped[str] = mapped_column(
        String(10), server_default="en", nullable=False
    )
    tags: Mapped[list[str]] = mapped_column(
        ARRAY(Text), server_default="{}", nullable=False
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=False
    )
    status: Mapped[DocumentStatus] = mapped_column(
        Enum(DocumentStatus, name="document_status_enum"),
        server_default=DocumentStatus.ACTIVE.value,
        nullable=False,
    )

    # relationships
    tenant: Mapped[Tenant] = relationship(back_populates="documents")
    data_source: Mapped[DataSource | None] = relationship(back_populates="documents")
    versions: Mapped[list[DocumentVersion]] = relationship(
        back_populates="document",
        cascade="all, delete-orphan",
        order_by="DocumentVersion.version_number",
    )

    __table_args__ = (
        Index("idx_documents_tenant_id", "tenant_id"),
        Index("idx_documents_data_source_id", "data_source_id"),
        Index("idx_documents_status", "status"),
        Index("idx_documents_sensitivity", "sensitivity_level"),
        Index("idx_documents_tags", "tags", postgresql_using="gin"),
        Index("idx_documents_language", "language"),
    )


# =============================================================================
# DocumentVersion
# =============================================================================


class DocumentVersion(TimestampMixin, Base):
    """Immutable snapshot of a document at a point in time.

    - Re-upload same doc → new version, old chunks preserved for audit.
    - Stores the raw file reference (storage_key in MinIO) and checksum for dedup.
    - version_number auto-increments per document.
    - status tracks ingestion: pending → processing → ready | error.
    """

    __tablename__ = "document_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(255))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    checksum: Mapped[str] = mapped_column(String(128), nullable=False)  # SHA-256
    status: Mapped[VersionStatus] = mapped_column(
        Enum(VersionStatus, name="version_status_enum"),
        server_default=VersionStatus.PENDING.value,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    parsed_content: Mapped[dict | None] = mapped_column(JSONB)
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=False
    )
    chunk_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )

    # relationships
    document: Mapped[Document] = relationship(back_populates="versions")
    chunks: Mapped[list[DocumentChunk]] = relationship(
        back_populates="version", cascade="all, delete-orphan"
    )

    __table_args__ = (
        UniqueConstraint(
            "document_id", "version_number", name="uq_docversion_doc_ver"
        ),
        Index("idx_docversions_tenant_id", "tenant_id"),
        Index("idx_docversions_document_id", "document_id"),
        Index("idx_docversions_checksum", "checksum"),
        Index("idx_docversions_status", "status"),
    )


# =============================================================================
# DocumentChunk
# =============================================================================


class DocumentChunk(TimestampMixin, Base):
    """The atomic unit of retrieval.

    Carries text content, embedding vector, and rich metadata for:
    - Vector similarity search (embedding column, HNSW index)
    - Filtering at query time (tenant_id, sensitivity, language, tags)
    - Citation (document_id, version_id, chunk_index, source_uri)
    - Analytics (token_count, embedding_model)
    """

    __tablename__ = "document_chunks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int | None] = mapped_column(Integer)
    embedding = mapped_column(Vector(1536))
    embedding_model: Mapped[str | None] = mapped_column(String(100))
    embedding_version: Mapped[str | None] = mapped_column(String(50))

    # Denormalized metadata for fast filtering (avoids JOINs during search)
    sensitivity_level: Mapped[SensitivityLevel | None] = mapped_column(
        Enum(SensitivityLevel, name="sensitivity_level_enum", create_type=False)
    )
    language: Mapped[str | None] = mapped_column(String(10))
    tags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=False
    )

    # relationships
    version: Mapped[DocumentVersion] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("idx_chunks_tenant_id", "tenant_id"),
        Index("idx_chunks_document_id", "document_id"),
        Index("idx_chunks_version_id", "version_id"),
        Index("idx_chunks_sensitivity", "sensitivity_level"),
        Index("idx_chunks_language", "language"),
        Index("idx_chunks_tags", "tags", postgresql_using="gin"),
        Index(
            "idx_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


# =============================================================================
# IngestionJob
# =============================================================================


class IngestionJob(TimestampMixin, Base):
    """Tracks a pipeline execution for ingesting a document version.

    Enables:
    - Async processing via worker queue
    - Progress tracking (chunks_processed / chunks_total)
    - Retry logic (attempt_number)
    - Debugging (error_message, metadata)
    """

    __tablename__ = "ingestion_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("document_versions.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[JobStatus] = mapped_column(
        Enum(JobStatus, name="job_status_enum"),
        server_default=JobStatus.QUEUED.value,
        nullable=False,
    )
    attempt_number: Mapped[int] = mapped_column(
        SmallInteger, server_default="1", nullable=False
    )
    chunks_total: Mapped[int | None] = mapped_column(Integer)
    chunks_processed: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=False
    )

    __table_args__ = (
        Index("idx_jobs_tenant_id", "tenant_id"),
        Index("idx_jobs_version_id", "version_id"),
        Index("idx_jobs_status", "status"),
    )


# =============================================================================
# RetrievalTrace
# =============================================================================


class RetrievalTrace(TimestampMixin, Base):
    """Records every RAG query for observability and evaluation.

    Captures the full pipeline trace:
    - Original query + transformed query (for HyDE / decomposition)
    - Retrieved chunk IDs with scores
    - LLM answer
    - Latency breakdown
    - User feedback (thumbs up/down)

    Essential for RAGOps: precision/recall measurement, drift detection,
    A/B testing of retrieval strategies.
    """

    __tablename__ = "retrieval_traces"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    query_text: Mapped[str] = mapped_column(Text, nullable=False)
    transformed_query: Mapped[str | None] = mapped_column(Text)
    retrieval_strategy: Mapped[str | None] = mapped_column(String(50))
    top_k: Mapped[int | None] = mapped_column(SmallInteger)
    retrieved_chunks: Mapped[dict] = mapped_column(
        JSONB, server_default="[]", nullable=False
    )  # [{chunk_id, score, rank}]
    answer_text: Mapped[str | None] = mapped_column(Text)
    llm_model: Mapped[str | None] = mapped_column(String(100))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    retrieval_latency_ms: Mapped[int | None] = mapped_column(Integer)
    generation_latency_ms: Mapped[int | None] = mapped_column(Integer)
    feedback_score: Mapped[float | None] = mapped_column(Float)  # -1 to 1
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=False
    )

    __table_args__ = (
        Index("idx_traces_tenant_id", "tenant_id"),
        Index("idx_traces_user_id", "user_id"),
        Index("idx_traces_created_at", "created_at"),
    )
