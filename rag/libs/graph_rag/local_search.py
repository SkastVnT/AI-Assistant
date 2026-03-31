"""Local graph retrieval — entity-neighbourhood search.

Given a query, find the most relevant entities via semantic embedding
search, then traverse N hops to build a neighbourhood context.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING
from uuid import UUID

from libs.graph_rag.types import GraphNeighbourhood

if TYPE_CHECKING:
    from libs.core.providers.base import EmbeddingProvider
    from libs.graph_rag.store import GraphStore

logger = logging.getLogger("rag.graph_rag.local_search")


async def local_search(
    store: GraphStore,
    embedding_provider: EmbeddingProvider,
    *,
    tenant_id: UUID,
    query: str,
    top_k_entities: int = 5,
    hops: int = 2,
    max_entities: int = 20,
    score_threshold: float = 0.3,
) -> GraphNeighbourhood:
    """Retrieve a local graph neighbourhood around query-relevant entities.

    Flow:
    1. Embed the query.
    2. Semantic search for top-K entities by embedding similarity.
    3. BFS-traverse N hops from seed entities.
    4. Return the neighbourhood with entities, relationships, source chunks.

    Parameters
    ----------
    store:
        GraphStore implementation.
    embedding_provider:
        For embedding the query text.
    tenant_id:
        Tenant scope.
    query:
        User search query.
    top_k_entities:
        Number of seed entities to retrieve.
    hops:
        Number of hops for neighbourhood traversal.
    max_entities:
        Maximum total entities in neighbourhood.
    score_threshold:
        Minimum similarity score for seed entities.

    Returns
    -------
    GraphNeighbourhood with seed entities, neighbours, and relationships.
    """
    t0 = time.perf_counter()

    # Step 1: Embed the query
    embeddings = await embedding_provider.embed([query])
    query_embedding = embeddings[0]

    # Step 2: Find seed entities
    entity_scores = await store.search_entities_by_embedding(
        tenant_id,
        query_embedding,
        top_k=top_k_entities,
        score_threshold=score_threshold,
    )

    if not entity_scores:
        logger.info("local_search: no entities found above threshold for query")
        return GraphNeighbourhood(
            seed_entities=[], neighbour_entities=[],
            relationships=[], source_chunks=[],
        )

    seed_ids = [e.id for e, _ in entity_scores if e.id]

    # Step 3: Traverse neighbourhood
    neighbourhood = await store.get_entity_neighbourhood(
        tenant_id,
        seed_ids,
        hops=hops,
        max_entities=max_entities,
    )

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "local_search: query=%r seeds=%d neighbours=%d rels=%d ms=%.1f",
        query[:50],
        len(neighbourhood.seed_entities),
        len(neighbourhood.neighbour_entities),
        len(neighbourhood.relationships),
        elapsed_ms,
    )
    return neighbourhood
