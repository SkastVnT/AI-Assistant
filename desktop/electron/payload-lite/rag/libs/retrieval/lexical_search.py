"""BM25-based lexical search using PostgreSQL ts_vector / ts_query.

Uses the built-in full-text search capabilities of PostgreSQL rather than
a separate search engine. Chunks must have a `tsvector` column (or we
compute it on-the-fly from content) for production use. This initial
implementation uses `plainto_tsquery` with `ts_rank_cd` for scoring.

The same multi-tenant isolation and metadata filtering as vector search
is applied.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from libs.retrieval.search import SearchFilters, SearchResult


async def lexical_search(
    db: AsyncSession,
    query: str,
    *,
    tenant_id: UUID,
    top_k: int = 20,
    language: str = "english",
    filters: SearchFilters | None = None,
) -> list[SearchResult]:
    """BM25-style full-text search using PostgreSQL ts_rank_cd.

    Uses `plainto_tsquery` for safe query parsing (no special syntax needed).
    ts_rank_cd uses cover-density ranking which approximates BM25-like scoring.

    Returns results ordered by relevance score descending.
    """
    where_clauses = [
        "c.tenant_id = :tenant_id",
        "v.status = 'ready'",
        "to_tsvector(:lang, c.content) @@ plainto_tsquery(:lang, :query)",
    ]
    params: dict = {
        "tenant_id": str(tenant_id),
        "query": query,
        "lang": language,
        "top_k": top_k,
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
            ts_rank_cd(
                to_tsvector(:lang, c.content),
                plainto_tsquery(:lang, :query),
                32  -- normalize by document length
            ) AS score
        FROM document_chunks c
        JOIN document_versions v ON v.id = c.version_id
        JOIN documents d ON d.id = c.document_id
        WHERE {where_sql}
        ORDER BY score DESC
        LIMIT :top_k
    """)

    result = await db.execute(sql, params)
    rows = result.fetchall()

    results: list[SearchResult] = []
    for row in rows:
        chunk_meta = row.chunk_metadata or {}
        results.append(
            SearchResult(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                version_id=row.version_id,
                content=row.content,
                score=float(row.score),
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
