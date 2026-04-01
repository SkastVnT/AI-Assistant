"""
High-level retrieval service — query → embed → search → filter → respond.

Performs a pgvector cosine-similarity search over ``rag_chunks``, enforces
tenant isolation and an optional document filter, applies a score threshold,
and optionally caches results in Redis.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import asdict, dataclass, field
from typing import Sequence

from sqlalchemy import select, text
from sqlalchemy.orm import selectinload

from core.rag_settings import get_rag_settings
from src.rag.cache.redis_cache import RedisCache
from src.rag.db.base import get_session_factory
from src.rag.db.models import RagChunk, RagDocument
from src.rag.embeddings.base import EmbeddingProvider
from src.rag.embeddings.factory import create_embedding_provider
from src.rag.security.policies import get_rag_policies
from src.rag.security.prompt_injection import cap_top_k, enforce_query_length

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Result DTO
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class RetrievalHit:
    """Single retrieval result returned to callers."""

    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float
    metadata_json: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class RetrievalService:
    """Orchestrates vector-similarity retrieval with tenant isolation.

    Parameters
    ----------
    embedder : EmbeddingProvider | None
        Custom embedder. ``None`` → created lazily on first retrieval call
        from ``RAGSettings`` to avoid eager API-client instantiation.
    cache : RedisCache | None
        ``None`` → a default ``RedisCache`` is created from settings.
        Pass ``False`` (cast to ``None`` inside) to disable caching entirely.
    """

    def __init__(
        self,
        *,
        embedder: EmbeddingProvider | None = None,
        cache: RedisCache | None = None,
        _disable_cache: bool = False,
    ) -> None:
        cfg = get_rag_settings()

        # Store the override; if None the provider is created lazily on first
        # call to _get_embedder() so that construction never fails in
        # environments without API credentials (e.g. unit tests).
        self._embedder: EmbeddingProvider | None = embedder
        self._embed_provider = cfg.embed_provider
        self._embed_model = cfg.embed_model
        self._embed_dim = cfg.embed_dim

        if _disable_cache:
            self._cache: RedisCache | None = None
        elif cache is not None:
            self._cache = cache
        else:
            self._cache = RedisCache(
                redis_url=cfg.redis_url,
                default_ttl=cfg.cache_ttl,
            )

        self._default_top_k = cfg.top_k
        self._min_score = cfg.min_score

    def _get_embedder(self) -> EmbeddingProvider:
        """Return the embedding provider, creating it on first call if needed."""
        if self._embedder is None:
            self._embedder = create_embedding_provider(
                provider=self._embed_provider,
                model=self._embed_model,
                dim=self._embed_dim,
            )
        return self._embedder

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def retrieve(
        self,
        *,
        tenant_id: str,
        query: str,
        top_k: int | None = None,
        doc_ids: list[str] | None = None,
        min_score: float | None = None,
    ) -> list[RetrievalHit]:
        """Search for the most relevant chunks.

        Parameters
        ----------
        tenant_id : str
            Mandatory tenant isolation key.
        query : str
            Natural language query.
        top_k : int | None
            Max results (defaults to ``RAG_TOP_K``).
        doc_ids : list[str] | None
            Restrict to these document IDs.
        min_score : float | None
            Override the default ``RAG_MIN_SCORE`` threshold.

        Returns
        -------
        list[RetrievalHit]
            Ordered by descending similarity score.
        """
        effective_k = top_k or self._default_top_k
        threshold = min_score if min_score is not None else self._min_score

        # ── Policy enforcement ────────────────────────────────────────
        policies = get_rag_policies()
        effective_k = cap_top_k(effective_k, policies=policies)
        query = enforce_query_length(query, policies=policies)

        # ── 1. Cache lookup ───────────────────────────────────────────
        if self._cache is not None:
            cached = await self._cache.get_retrieval(
                tenant_id, query, effective_k, doc_ids,
            )
            if cached is not None:
                return [RetrievalHit(**row) for row in cached]

        # ── 2. Embed query ────────────────────────────────────────────
        query_vector = self._get_embedder().embed_query(query)

        # ── 3. pgvector similarity search ─────────────────────────────
        hits = await self._vector_search(
            tenant_id=tenant_id,
            query_vector=query_vector,
            top_k=effective_k,
            doc_ids=doc_ids,
            threshold=threshold,
        )

        # ── 4. Cache store ────────────────────────────────────────────
        if self._cache is not None and hits:
            await self._cache.set_retrieval(
                tenant_id,
                query,
                effective_k,
                [h.to_dict() for h in hits],
                doc_ids,
            )

        return hits

    # ------------------------------------------------------------------
    # Internal: pgvector query
    # ------------------------------------------------------------------

    async def _vector_search(
        self,
        *,
        tenant_id: str,
        query_vector: list[float],
        top_k: int,
        doc_ids: list[str] | None,
        threshold: float,
    ) -> list[RetrievalHit]:
        """Run a cosine-distance query against ``rag_chunks``.

        Uses the pgvector ``<=>`` (cosine distance) operator.  The HNSW
        index on ``rag_chunks.embedding`` is automatically leveraged by
        PostgreSQL.

        Cosine *distance* is in [0, 2]; we convert it to a *similarity*
        score in [0, 1] via ``1 - distance``.
        """
        session_factory = get_session_factory()
        vec_literal = f"[{','.join(str(v) for v in query_vector)}]"

        async with session_factory() as session:
            # Build raw SQL for pgvector cosine distance + JOIN
            sql = text("""
                SELECT
                    c.id            AS chunk_id,
                    c.document_id   AS document_id,
                    d.title         AS title,
                    c.content       AS content,
                    1 - (c.embedding <=> :vec) AS score,
                    c.metadata_json AS metadata_json
                FROM rag_chunks c
                JOIN rag_documents d ON d.id = c.document_id
                WHERE c.tenant_id = :tenant
                  AND c.embedding IS NOT NULL
                  AND 1 - (c.embedding <=> :vec) >= :threshold
                  {doc_filter}
                ORDER BY c.embedding <=> :vec
                LIMIT :topk
            """.replace(
                "{doc_filter}",
                "AND c.document_id = ANY(:doc_ids)" if doc_ids else "",
            ))

            params: dict = {
                "vec": vec_literal,
                "tenant": tenant_id,
                "threshold": threshold,
                "topk": top_k,
            }
            if doc_ids:
                params["doc_ids"] = [uuid.UUID(d) if isinstance(d, str) else d for d in doc_ids]

            result = await session.execute(sql, params)
            rows = result.mappings().all()

        hits: list[RetrievalHit] = []
        for row in rows:
            hits.append(
                RetrievalHit(
                    chunk_id=str(row["chunk_id"]),
                    document_id=str(row["document_id"]),
                    title=row["title"],
                    content=row["content"],
                    score=float(row["score"]),
                    metadata_json=row["metadata_json"] or {},
                )
            )
        return hits
