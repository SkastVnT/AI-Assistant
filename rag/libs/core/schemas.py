"""Pydantic schemas for the RAG domain model.

Naming convention:
    {Model}Create   — request body for creation
    {Model}Update   — request body for partial update (all fields optional)
    {Model}Response — response body (includes id, timestamps)
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

# =============================================================================
# Tenant
# =============================================================================


class TenantCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    slug: str = Field(..., min_length=1, max_length=63, pattern=r"^[a-z0-9\-]+$")
    settings: dict = Field(default_factory=dict)


class TenantUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    settings: dict | None = None
    is_active: bool | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    slug: str
    settings: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# User
# =============================================================================


class UserCreate(BaseModel):
    email: str = Field(..., min_length=1, max_length=320)
    display_name: str | None = Field(None, max_length=255)
    role: str = Field(default="member", max_length=50)


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    email: str
    display_name: str | None
    role: str
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# DataSource
# =============================================================================


class DataSourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    source_type: str  # validated against SourceType enum
    config: dict = Field(default_factory=dict)


class DataSourceUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    config: dict | None = None
    is_active: bool | None = None


class DataSourceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    name: str
    source_type: str
    config: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


# =============================================================================
# Document
# =============================================================================


class DocumentCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=1024)
    data_source_id: UUID | None = None
    source_uri: str | None = None
    author: str | None = Field(None, max_length=255)
    sensitivity_level: str = "internal"
    language: str = Field(default="en", max_length=10)
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class DocumentUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=1024)
    author: str | None = None
    sensitivity_level: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    metadata: dict | None = None
    status: str | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    data_source_id: UUID | None
    title: str
    source_uri: str | None
    author: str | None
    sensitivity_level: str
    language: str
    tags: list[str]
    metadata: dict = Field(validation_alias="metadata_")
    status: str
    created_at: datetime
    updated_at: datetime
    version_count: int = 0


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


# =============================================================================
# DocumentVersion
# =============================================================================


class DocumentVersionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    document_id: UUID
    version_number: int
    storage_key: str
    filename: str
    content_type: str | None
    file_size_bytes: int | None
    checksum: str
    status: str
    error_message: str | None
    has_parsed_content: bool = False
    metadata: dict = Field(validation_alias="metadata_")
    chunk_count: int
    created_at: datetime
    updated_at: datetime


class DocumentVersionListResponse(BaseModel):
    versions: list[DocumentVersionResponse]
    total: int


# =============================================================================
# DocumentChunk
# =============================================================================


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    document_id: UUID
    version_id: UUID
    chunk_index: int
    content: str
    token_count: int | None
    embedding_model: str | None
    sensitivity_level: str | None
    language: str | None
    tags: list[str] | None
    metadata: dict = Field(validation_alias="metadata_")
    created_at: datetime


# =============================================================================
# IngestionJob
# =============================================================================


class IngestionJobResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    version_id: UUID
    status: str
    attempt_number: int
    chunks_total: int | None
    chunks_processed: int
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    metadata: dict = Field(validation_alias="metadata_")
    created_at: datetime
    updated_at: datetime


class IngestionJobListResponse(BaseModel):
    jobs: list[IngestionJobResponse]
    total: int


# =============================================================================
# RetrievalTrace
# =============================================================================


class RetrievalTraceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: UUID
    user_id: UUID | None
    query_text: str
    transformed_query: str | None
    retrieval_strategy: str | None
    top_k: int | None
    retrieved_chunks: dict  # actually list[dict], stored as JSONB
    answer_text: str | None
    llm_model: str | None
    latency_ms: int | None
    retrieval_latency_ms: int | None
    generation_latency_ms: int | None
    feedback_score: float | None
    metadata: dict = Field(validation_alias="metadata_")
    created_at: datetime


class FeedbackRequest(BaseModel):
    score: float = Field(..., ge=-1.0, le=1.0)


# =============================================================================
# Query (used by retrieval routes)
# =============================================================================


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=20)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    filters: QueryFilters | None = None


class QueryFilters(BaseModel):
    sensitivity_levels: list[str] | None = None
    languages: list[str] | None = None
    tags: list[str] | None = None
    document_ids: list[UUID] | None = None


class SourceChunk(BaseModel):
    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    filename: str
    content: str
    score: float
    chunk_index: int


class QueryResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
    query: str
    trace_id: UUID | None = None


# =============================================================================
# Retrieve (baseline retrieval — no LLM generation)
# =============================================================================


class RetrieveFilters(BaseModel):
    sensitivity_levels: list[str] | None = None
    languages: list[str] | None = None
    tags: list[str] | None = None
    source_ids: list[UUID] | None = None


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    filters: RetrieveFilters | None = None


class RetrievedChunkResponse(BaseModel):
    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    content: str
    score: float
    chunk_index: int
    # Citation metadata
    document_title: str
    filename: str
    version_number: int
    page_number: int | None = None
    heading_path: str | None = None
    sensitivity_level: str
    language: str
    tags: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class RetrieveResponse(BaseModel):
    query: str
    chunks: list[RetrievedChunkResponse]
    total_found: int
    trace_id: UUID | None = None
    retrieval_ms: int
    embedding_model: str | None = None
    transformed_query: str | None = None
    sub_queries: list[str] = Field(default_factory=list)
    transform_log: list[dict] = Field(default_factory=list)
    transform_ms: int = 0
    # Hybrid retrieval diagnostics
    retrieval_strategy: str = "vector_cosine"
    dense_count: int = 0
    lexical_count: int = 0
    fused_count: int = 0
    reranked_count: int = 0
    dense_ms: int = 0
    lexical_ms: int = 0
    fusion_ms: int = 0
    rerank_ms: int = 0


# =============================================================================
# Answer Generation (grounded RAG answer with citations)
# =============================================================================


class AnswerRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=50)
    score_threshold: float = Field(default=0.0, ge=0.0, le=1.0)
    mode: str = Field(
        default="standard",
        pattern=r"^(concise|standard|detailed)$",
        description="Response verbosity: concise, standard, or detailed.",
    )
    filters: RetrieveFilters | None = None


class CitationRef(BaseModel):
    """A single citation reference to a source chunk."""

    source_index: int = Field(
        ..., description="1-based index matching [Source N] in the answer."
    )
    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    filename: str
    content_snippet: str = Field(
        ..., max_length=300,
        description="Truncated content of the chunk used as evidence.",
    )
    score: float
    page_number: int | None = None
    heading_path: str | None = None


class AnswerResponse(BaseModel):
    answer: str
    citations: list[CitationRef]
    query: str
    mode: str
    evidence_used: int = Field(
        ..., description="Number of evidence chunks fed to the LLM."
    )
    trace_id: UUID | None = None
    retrieval_ms: int = 0
    generation_ms: int = 0
    total_ms: int = 0


# =============================================================================
# Health
# =============================================================================


class HealthResponse(BaseModel):
    status: str
    postgres: bool
    redis: bool
    minio: bool
