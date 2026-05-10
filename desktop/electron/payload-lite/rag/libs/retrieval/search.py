"""Vector similarity search using pgvector.

Supports multi-tenant isolation, version-aware search, and metadata filtering.
Future: hybrid search (BM25 + vector), reranking, GraphRAG.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.providers.base import EmbeddingProvider


@dataclass(frozen=True)
class SearchResult:
    """Single search hit with citation metadata."""

    chunk_id: UUID
    document_id: UUID
    version_id: UUID
    content: str
    score: float
    metadata: dict
    filename: str
    chunk_index: int
    sensitivity_level: str
    language: str
    tags: list[str] = field(default_factory=list)
    # Citation metadata
    document_title: str = ""
    version_number: int = 0
    page_number: int | None = None
    heading_path: str | None = None


@dataclass(frozen=True)
class SearchFilters:
    sensitivity_level: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    data_source_id: UUID | None = None
    source_ids: list[UUID] | None = None  # filter by document IDs


async def vector_search(
    db: AsyncSession,
    embedding_provider: EmbeddingProvider,
    query: str,
    *,
    tenant_id: UUID,
    top_k: int = 5,
    score_threshold: float = 0.0,
    filters: SearchFilters | None = None,
) -> list[SearchResult]:
    """Cosine similarity search with multi-tenant isolation and metadata filtering.

    Searches only chunks from the latest READY version of each document.
    """
    embeddings = await embedding_provider.embed([query])
    query_vector = embeddings[0]

    # Build WHERE clauses dynamically
    where_clauses = [
        "c.tenant_id = :tenant_id",
        "v.status = 'ready'",
    ]
    params: dict = {
        "query_embedding": str(query_vector),
        "top_k": top_k,
        "tenant_id": str(tenant_id),
    }

    if filters:
        if filters.sensitivity_level:
            where_clauses.append("c.sensitivity_level = :sensitivity_level")
            params["sensitivity_level"] = filters.sensitivity_level
        if filters.language:
            where_clauses.append("c.language = :language")
            params["language"] = filters.language
        if filters.tags:
            where_clauses.append("c.tags @> :tags")
            params["tags"] = filters.tags
        if filters.data_source_id:
            where_clauses.append("d.data_source_id = :data_source_id")
            params["data_source_id"] = str(filters.data_source_id)
        if filters.source_ids:
            where_clauses.append("c.document_id = ANY(:source_ids)")
            params["source_ids"] = [str(sid) for sid in filters.source_ids]

    where_sql = " AND ".join(where_clauses)

    sql = text(f"""
        SELECT
            c.id AS chunk_id,
            c.document_id,
            c.version_id,
            c.content,
            c.chunk_index,
            c.metadata AS chunk_metadata,
            c.sensitivity_level,
            c.language,
            c.tags,
            v.filename,
            v.version_number,
            d.title AS document_title,
            1 - (c.embedding <=> :query_embedding::vector) AS score
        FROM document_chunks c
        JOIN document_versions v ON v.id = c.version_id
        JOIN documents d ON d.id = c.document_id
        WHERE {where_sql}
        ORDER BY c.embedding <=> :query_embedding::vector
        LIMIT :top_k
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()

    results: list[SearchResult] = []
    for row in rows:
        score = float(row.score)
        if score < score_threshold:
            continue
        chunk_meta = row.chunk_metadata or {}
        results.append(
            SearchResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                version_id=row.version_id,
                content=row.content,
                score=score,
                metadata=chunk_meta,
                filename=row.filename,
                chunk_index=row.chunk_index,
                sensitivity_level=row.sensitivity_level,
                language=row.language,
                tags=row.tags or [],
                document_title=row.document_title or "",
                version_number=row.version_number or 0,
                page_number=chunk_meta.get("page_number"),
                heading_path=chunk_meta.get("heading_path"),
            )
        )

    return results


async def vector_search_from_embedding(
    db: AsyncSession,
    query_vector: list[float],
    *,
    tenant_id: UUID,
    top_k: int = 5,
    score_threshold: float = 0.0,
    filters: SearchFilters | None = None,
) -> list[SearchResult]:
    """Search using a pre-computed query embedding (avoids double-embedding)."""
    where_clauses = [
        "c.tenant_id = :tenant_id",
        "v.status = 'ready'",
    ]
    params: dict = {
        "query_embedding": str(query_vector),
        "top_k": top_k,
        "tenant_id": str(tenant_id),
    }

    if filters:
        if filters.sensitivity_level:
            where_clauses.append("c.sensitivity_level = :sensitivity_level")
            params["sensitivity_level"] = filters.sensitivity_level
        if filters.language:
            where_clauses.append("c.language = :language")
            params["language"] = filters.language
        if filters.tags:
            where_clauses.append("c.tags @> :tags")
            params["tags"] = filters.tags
        if filters.data_source_id:
            where_clauses.append("d.data_source_id = :data_source_id")
            params["data_source_id"] = str(filters.data_source_id)
        if filters.source_ids:
            where_clauses.append("c.document_id = ANY(:source_ids)")
            params["source_ids"] = [str(sid) for sid in filters.source_ids]

    where_sql = " AND ".join(where_clauses)

    sql = text(f"""
        SELECT
            c.id AS chunk_id,
            c.document_id,
            c.version_id,
            c.content,
            c.chunk_index,
            c.metadata AS chunk_metadata,
            c.sensitivity_level,
            c.language,
            c.tags,
            v.filename,
            v.version_number,
            d.title AS document_title,
            1 - (c.embedding <=> :query_embedding::vector) AS score
        FROM document_chunks c
        JOIN document_versions v ON v.id = c.version_id
        JOIN documents d ON d.id = c.document_id
        WHERE {where_sql}
        ORDER BY c.embedding <=> :query_embedding::vector
        LIMIT :top_k
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()

    results: list[SearchResult] = []
    for row in rows:
        score = float(row.score)
        if score < score_threshold:
            continue
        chunk_meta = row.chunk_metadata or {}
        results.append(
            SearchResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                version_id=row.version_id,
                content=row.content,
                score=score,
                metadata=row.chunk_metadata or {},
                metadata=chunk_meta,
                filename=row.filename,
                chunk_index=row.chunk_index,
                sensitivity_level=row.sensitivity_level,
                language=row.language,
                tags=row.tags or [],
                document_title=row.document_title or "",
                version_number=row.version_number or 0,
                page_number=chunk_meta.get("page_number"),
                heading_path=chunk_meta.get("heading_path"),
            )
        )

    return results
