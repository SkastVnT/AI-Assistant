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


# =============================================================================
# SecurityEvent
# =============================================================================


class SecurityEventKind(enum.StrEnum):
    """Enumeration of security event types logged by guardrails."""

    INGESTION_SANITIZE = "ingestion_sanitize"      # malicious content at ingest
    PROMPT_INJECTION = "prompt_injection"           # injection detected in context
    PII_REDACTED = "pii_redacted"                  # PII found and redacted
    OUTPUT_BLOCKED = "output_blocked"               # LLM output failed validation
    SOURCE_UNTRUSTED = "source_untrusted"           # untrusted source flagged
    HUMAN_REVIEW = "human_review"                   # response queued for review


class SecurityEvent(TimestampMixin, Base):
    """Audit log for all guardrail actions (blocks, flags, redactions).

    Every time a guardrail fires — whether it blocks content, redacts PII,
    or flags a response for human review — an event is recorded here.
    This table is append-only and never updated or deleted (audit trail).
    """

    __tablename__ = "security_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    kind: Mapped[SecurityEventKind] = mapped_column(
        Enum(SecurityEventKind, name="security_event_kind_enum"), nullable=False
    )
    severity: Mapped[str] = mapped_column(
        String(20), server_default="medium", nullable=False
    )  # low | medium | high | critical
    source: Mapped[str] = mapped_column(
        String(100), nullable=False
    )  # which guardrail component
    description: Mapped[str] = mapped_column(Text, nullable=False)
    document_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("documents.id", ondelete="SET NULL")
    )
    trace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("retrieval_traces.id", ondelete="SET NULL")
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    details: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )  # pattern matched, redacted fields, etc.
    resolved: Mapped[bool] = mapped_column(default=False, nullable=False)
    resolved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("idx_security_events_tenant_id", "tenant_id"),
        Index("idx_security_events_kind", "kind"),
        Index("idx_security_events_severity", "severity"),
        Index("idx_security_events_created_at", "created_at"),
        Index("idx_security_events_resolved", "resolved"),
    )


# =============================================================================
# EvalRun + EvalResult (RAGOps evaluation layer)
# =============================================================================


class EvalRun(TimestampMixin, Base):
    """A batch evaluation run over a dataset of test cases.

    Tracks aggregate metrics, configuration used, pass/fail status.
    Used by CI and ad-hoc evaluation workflows.
    """

    __tablename__ = "eval_runs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    dataset_name: Mapped[str] = mapped_column(String(255), nullable=False)
    config: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )  # settings snapshot
    status: Mapped[str] = mapped_column(
        String(20), server_default="pending", nullable=False
    )  # pending | running | completed | failed
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    summary: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )  # aggregate scores
    total_cases: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    passed_cases: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )
    failed_cases: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False
    )

    results: Mapped[list[EvalResult]] = relationship(
        back_populates="run", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("idx_eval_runs_tenant_id", "tenant_id"),
        Index("idx_eval_runs_status", "status"),
        Index("idx_eval_runs_dataset_name", "dataset_name"),
    )


class EvalResult(TimestampMixin, Base):
    """Single evaluation case result within an EvalRun.

    Stores per-metric scores for both retriever and generator evaluation,
    plus the raw data used for evaluation.
    """

    __tablename__ = "eval_results"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    run_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("eval_runs.id", ondelete="CASCADE"),
        nullable=False,
    )
    trace_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retrieval_traces.id", ondelete="SET NULL"),
    )
    case_id: Mapped[str] = mapped_column(String(255), nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    expected_answer: Mapped[str | None] = mapped_column(Text)
    retrieved_context: Mapped[str | None] = mapped_column(Text)
    generated_answer: Mapped[str | None] = mapped_column(Text)
    # Retriever metrics
    context_relevance: Mapped[float | None] = mapped_column(Float)
    # Generator metrics
    groundedness: Mapped[float | None] = mapped_column(Float)
    answer_relevance: Mapped[float | None] = mapped_column(Float)
    # Combined
    overall_score: Mapped[float | None] = mapped_column(Float)
    passed: Mapped[bool] = mapped_column(default=True, nullable=False)
    # Detailed breakdown
    retriever_details: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )
    generator_details: Mapped[dict] = mapped_column(
        JSONB, server_default="{}", nullable=False
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    error: Mapped[str | None] = mapped_column(Text)

    run: Mapped[EvalRun] = relationship(back_populates="results")

    __table_args__ = (
        Index("idx_eval_results_run_id", "run_id"),
        Index("idx_eval_results_case_id", "case_id"),
        Index("idx_eval_results_passed", "passed"),
    )


# =============================================================================
# GraphRAG — Entity / Relationship / Community
# =============================================================================


class GraphEntity(TimestampMixin, Base):
    """A named entity extracted from document chunks.

    Entities are the nodes of the knowledge graph. Each has a canonical
    name, type, description, and optional embedding for semantic matching.
    """

    __tablename__ = "graph_entities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    entity_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )  # PERSON, ORG, CONCEPT, TECHNOLOGY, LOCATION, EVENT, etc.
    description: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    embedding = mapped_column(Vector(1536))
    # Source provenance
    source_chunk_ids: Mapped[list] = mapped_column(
        JSONB, server_default="[]", nullable=False,
    )  # [{chunk_id, document_id}]
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=False,
    )
    # Community assignment (set by community detection)
    community_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("graph_communities.id", ondelete="SET NULL"),
    )

    community: Mapped[GraphCommunity | None] = relationship(
        back_populates="entities",
    )

    __table_args__ = (
        UniqueConstraint(
            "tenant_id", "name", "entity_type",
            name="uq_entity_tenant_name_type",
        ),
        Index("idx_graph_entities_tenant_id", "tenant_id"),
        Index("idx_graph_entities_type", "entity_type"),
        Index("idx_graph_entities_name", "name"),
        Index(
            "idx_graph_entities_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )


class GraphRelationship(TimestampMixin, Base):
    """A directed relationship between two entities.

    Edges of the knowledge graph, typed and weighted.
    """

    __tablename__ = "graph_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    source_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_entity_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("graph_entities.id", ondelete="CASCADE"),
        nullable=False,
    )
    relationship_type: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )  # USES, PART_OF, DEPENDS_ON, MENTIONS, CREATED_BY, etc.
    description: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    weight: Mapped[float] = mapped_column(Float, server_default="1.0", nullable=False)
    source_chunk_ids: Mapped[list] = mapped_column(
        JSONB, server_default="[]", nullable=False,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=False,
    )

    source_entity: Mapped[GraphEntity] = relationship(
        foreign_keys=[source_entity_id],
    )
    target_entity: Mapped[GraphEntity] = relationship(
        foreign_keys=[target_entity_id],
    )

    __table_args__ = (
        Index("idx_graph_rels_tenant_id", "tenant_id"),
        Index("idx_graph_rels_source", "source_entity_id"),
        Index("idx_graph_rels_target", "target_entity_id"),
        Index("idx_graph_rels_type", "relationship_type"),
    )


class GraphCommunity(TimestampMixin, Base):
    """A detected community (cluster) of related entities.

    Used for global retrieval — the community summary provides a
    high-level overview of a topic cluster.
    """

    __tablename__ = "graph_communities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(512), nullable=False)
    level: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False,
    )  # hierarchy level (0 = leaf)
    summary: Mapped[str] = mapped_column(Text, server_default="", nullable=False)
    summary_embedding = mapped_column(Vector(1536))
    entity_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False,
    )
    relationship_count: Mapped[int] = mapped_column(
        Integer, server_default="0", nullable=False,
    )
    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, server_default="{}", nullable=False,
    )

    entities: Mapped[list[GraphEntity]] = relationship(
        back_populates="community",
    )

    __table_args__ = (
        Index("idx_graph_communities_tenant_id", "tenant_id"),
        Index("idx_graph_communities_level", "level"),
        Index(
            "idx_graph_communities_summary_hnsw",
            "summary_embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"summary_embedding": "vector_cosine_ops"},
        ),
    )
