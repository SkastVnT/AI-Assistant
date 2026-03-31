"""Graph indexing workflow — extract → store → embed → detect communities.

This is the main entry point for building the knowledge graph from
ingested document chunks. Typically triggered after the standard
ingestion pipeline completes.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING
from uuid import UUID

from libs.graph_rag.community import detect_communities, summarize_communities
from libs.graph_rag.extraction import extract_entities_and_relationships

if TYPE_CHECKING:
    from libs.core.providers.base import EmbeddingProvider, LLMProvider
    from libs.core.settings import GraphRAGSettings
    from libs.graph_rag.store import GraphStore

logger = logging.getLogger("rag.graph_rag.indexer")


async def index_document_graph(
    store: GraphStore,
    llm: LLMProvider,
    embedding_provider: EmbeddingProvider,
    settings: GraphRAGSettings,
    *,
    tenant_id: UUID,
    document_id: UUID,
    chunks: list[dict],
) -> dict:
    """Build knowledge graph from document chunks.

    Parameters
    ----------
    store:
        GraphStore implementation.
    llm:
        LLM for entity extraction and community summarization.
    embedding_provider:
        For embedding entities and community summaries.
    settings:
        GraphRAGSettings with extraction and community config.
    tenant_id:
        Tenant scope for multi-tenant isolation.
    document_id:
        Document being indexed.
    chunks:
        List of dicts with at minimum {"id": str, "text": str}.

    Returns
    -------
    Dict with indexing stats: entities_count, relationships_count,
    communities_count, elapsed_ms.
    """
    t0 = time.perf_counter()

    total_entities = 0
    total_relationships = 0

    # ── Step 1: Extract entities and relationships from each chunk ──
    for chunk in chunks:
        chunk_id = str(chunk["id"])
        chunk_text = chunk["text"]

        result = await extract_entities_and_relationships(
            llm,
            chunk_text,
            chunk_id=chunk_id,
            document_id=str(document_id),
            max_entities=settings.max_entities_per_chunk,
            max_relationships=settings.max_relationships_per_chunk,
            temperature=settings.extraction_temperature,
        )

        # ── Step 2: Persist entities (with deduplication) ───────────
        for entity in result.entities:
            await store.upsert_entity(tenant_id, entity)
            total_entities += 1

        # ── Step 3: Persist relationships ───────────────────────────
        for relationship in result.relationships:
            await store.upsert_relationship(tenant_id, relationship)
            total_relationships += 1

    # ── Step 4: Embed all entities ──────────────────────────────────
    await _embed_entities(store, embedding_provider, tenant_id)

    # ── Step 5: Detect communities and summarize ────────────────────
    communities = await detect_communities(
        store,
        tenant_id,
        algorithm=settings.community_algorithm,
        resolution=settings.community_resolution,
        min_community_size=settings.min_community_size,
    )
    communities = await summarize_communities(
        communities,
        store,
        llm,
        embedding_provider,
        tenant_id,
        max_tokens=settings.max_community_summary_tokens,
    )

    elapsed_ms = (time.perf_counter() - t0) * 1000

    stats = {
        "document_id": str(document_id),
        "entities_count": total_entities,
        "relationships_count": total_relationships,
        "communities_count": len(communities),
        "elapsed_ms": round(elapsed_ms, 1),
    }
    logger.info("index_document_graph: %s", stats)
    return stats


async def _embed_entities(
    store: GraphStore,
    embedding_provider: EmbeddingProvider,
    tenant_id: UUID,
    *,
    batch_size: int = 64,
) -> int:
    """Embed entity descriptions and update the store.

    Returns the number of entities embedded.
    """
    entities = await store.get_all_entities(tenant_id)
    to_embed = [e for e in entities if e.embedding is None and e.description]

    if not to_embed:
        return 0

    count = 0
    for i in range(0, len(to_embed), batch_size):
        batch = to_embed[i : i + batch_size]
        texts = [
            f"{e.entity_type}: {e.name} — {e.description}" for e in batch
        ]
        embeddings = await embedding_provider.embed(texts)
        for entity, emb in zip(batch, embeddings, strict=True):
            entity.embedding = emb
            await store.upsert_entity(tenant_id, entity)
            count += 1

    logger.info("embed_entities: tenant=%s embedded=%d", tenant_id, count)
    return count


async def reindex_tenant_graph(
    store: GraphStore,
    llm: LLMProvider,
    embedding_provider: EmbeddingProvider,
    settings: GraphRAGSettings,
    *,
    tenant_id: UUID,
) -> dict:
    """Re-run community detection and summarization for existing entities.

    Useful when the community algorithm or resolution changes.
    Does NOT re-extract entities — only rebuilds communities.
    """
    t0 = time.perf_counter()

    communities = await detect_communities(
        store,
        tenant_id,
        algorithm=settings.community_algorithm,
        resolution=settings.community_resolution,
        min_community_size=settings.min_community_size,
    )
    communities = await summarize_communities(
        communities,
        store,
        llm,
        embedding_provider,
        tenant_id,
        max_tokens=settings.max_community_summary_tokens,
    )

    elapsed_ms = (time.perf_counter() - t0) * 1000
    return {
        "communities_count": len(communities),
        "elapsed_ms": round(elapsed_ms, 1),
    }
