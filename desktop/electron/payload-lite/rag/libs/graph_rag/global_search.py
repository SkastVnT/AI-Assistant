"""Global graph retrieval — community-summary search.

Given a query, semantically search community summaries to find
high-level thematic matches. Best for broad / analytical questions.
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING
from uuid import UUID

from libs.graph_rag.types import CommunitySearchResult

if TYPE_CHECKING:
    from libs.core.providers.base import EmbeddingProvider
    from libs.graph_rag.store import GraphStore

logger = logging.getLogger("rag.graph_rag.global_search")


async def global_search(
    store: GraphStore,
    embedding_provider: EmbeddingProvider,
    *,
    tenant_id: UUID,
    query: str,
    top_k_communities: int = 10,
) -> CommunitySearchResult:
    """Retrieve community summaries relevant to the query.

    Flow:
    1. Embed the query.
    2. Semantic search over community summary embeddings.
    3. Return ranked community summaries as context.

    Parameters
    ----------
    store:
        GraphStore implementation.
    embedding_provider:
        For embedding the query.
    tenant_id:
        Tenant scope.
    query:
        User query.
    top_k_communities:
        Max number of communities to return.

    Returns
    -------
    CommunitySearchResult with matched communities.
    """
    t0 = time.perf_counter()

    # Step 1: Embed query
    embeddings = await embedding_provider.embed([query])
    query_embedding = embeddings[0]

    # Step 2: Search community summaries
    results = await store.search_communities_by_embedding(
        tenant_id,
        query_embedding,
        top_k=top_k_communities,
    )

    communities = [c for c, _ in results]
    total_found = len(communities)

    elapsed_ms = (time.perf_counter() - t0) * 1000
    logger.info(
        "global_search: query=%r communities=%d ms=%.1f",
        query[:50], total_found, elapsed_ms,
    )

    return CommunitySearchResult(
        communities=communities,
        total_found=total_found,
    )
