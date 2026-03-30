"""Vector similarity search using pgvector.

Supports multi-tenant isolation, version-aware search, and metadata filtering.
Future: hybrid search (BM25 + vector), reranking, GraphRAG.
"""

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.providers.base import EmbeddingProvider


@dataclass(frozen=True)
class SearchResult:
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


@dataclass(frozen=True)
class SearchFilters:
    sensitivity_level: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    data_source_id: UUID | None = None


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
        results.append(
            SearchResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                version_id=row.version_id,
                content=row.content,
                score=score,
                metadata=row.chunk_metadata or {},
                filename=row.filename,
                chunk_index=row.chunk_index,
                sensitivity_level=row.sensitivity_level,
                language=row.language,
                tags=row.tags or [],
            )
        )

    return results
