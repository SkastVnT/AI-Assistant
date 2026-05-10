"""Query router — decides vector vs graph vs hybrid retrieval strategy.

Analyzes the query to detect whether graph-based retrieval would help,
then dispatches to the appropriate search path(s).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING
from uuid import UUID

from libs.graph_rag.global_search import global_search
from libs.graph_rag.local_search import local_search
from libs.graph_rag.types import GraphSearchResult

if TYPE_CHECKING:
    from libs.core.providers.base import EmbeddingProvider
    from libs.core.settings import GraphRAGSettings
    from libs.graph_rag.store import GraphStore

logger = logging.getLogger("rag.graph_rag.router")


class SearchStrategy(Enum):
    """Which retrieval strategy to use."""

    VECTOR = "vector"          # Standard vector-only retrieval
    LOCAL_GRAPH = "local"      # Entity neighbourhood search
    GLOBAL_GRAPH = "global"    # Community summary search
    HYBRID_GRAPH = "hybrid"    # Local + global graph search


@dataclass
class RoutingDecision:
    """Result of the routing analysis."""

    strategy: SearchStrategy
    confidence: float
    reason: str


# ═══════════════════════════════════════════════════════════════════════
# Routing logic
# ═══════════════════════════════════════════════════════════════════════

# Patterns that suggest entity-centric (local) queries
LOCAL_INDICATORS = frozenset({
    "who", "what is", "tell me about", "describe", "explain",
    "relationship between", "connected to", "related to",
    "how does", "what does",
})

# Patterns that suggest broad/analytical (global) queries
GLOBAL_INDICATORS = frozenset({
    "summarize", "overview", "main themes", "key topics",
    "what are the", "list all", "how many", "compare",
    "overall", "in general", "broadly",
})


def route_query(query: str, *, auto_route: bool = True) -> RoutingDecision:
    """Determine the best search strategy for a query.

    This is a lightweight heuristic router. For production, consider
    using an LLM-based classifier for better accuracy.

    Parameters
    ----------
    query:
        User's search query.
    auto_route:
        If False, always returns VECTOR (graph disabled).

    Returns
    -------
    RoutingDecision with strategy, confidence, and reason.
    """
    if not auto_route:
        return RoutingDecision(
            strategy=SearchStrategy.VECTOR,
            confidence=1.0,
            reason="auto_route disabled",
        )

    q_lower = query.lower().strip()

    local_score = sum(1 for p in LOCAL_INDICATORS if p in q_lower)
    global_score = sum(1 for p in GLOBAL_INDICATORS if p in q_lower)

    # Named entity detection heuristic: capitalized words (simple)
    words = query.split()
    capitalized = sum(
        1 for w in words[1:]  # skip first word
        if w[0].isupper() and len(w) > 1 and not w.isupper()
    ) if len(words) > 1 else 0
    local_score += capitalized

    if local_score > 0 and global_score > 0:
        return RoutingDecision(
            strategy=SearchStrategy.HYBRID_GRAPH,
            confidence=0.7,
            reason=f"mixed signals: local={local_score} global={global_score}",
        )
    if global_score > 0:
        return RoutingDecision(
            strategy=SearchStrategy.GLOBAL_GRAPH,
            confidence=min(0.5 + global_score * 0.15, 0.9),
            reason=f"global indicators detected: score={global_score}",
        )
    if local_score > 0:
        return RoutingDecision(
            strategy=SearchStrategy.LOCAL_GRAPH,
            confidence=min(0.5 + local_score * 0.15, 0.9),
            reason=f"local/entity indicators detected: score={local_score}",
        )

    # Default: vector search (no strong graph signal)
    return RoutingDecision(
        strategy=SearchStrategy.VECTOR,
        confidence=0.6,
        reason="no strong graph indicators",
    )


# ═══════════════════════════════════════════════════════════════════════
# Orchestrated graph search
# ═══════════════════════════════════════════════════════════════════════


async def graph_search(
    store: GraphStore,
    embedding_provider: EmbeddingProvider,
    settings: GraphRAGSettings,
    *,
    tenant_id: UUID,
    query: str,
    strategy: SearchStrategy | None = None,
) -> GraphSearchResult | None:
    """Execute graph-based retrieval based on the routing strategy.

    Parameters
    ----------
    store:
        GraphStore implementation.
    embedding_provider:
        For query embedding.
    settings:
        GraphRAGSettings.
    tenant_id:
        Tenant scope.
    query:
        User query.
    strategy:
        Override routing decision. If None, auto-routes.

    Returns
    -------
    GraphSearchResult with local and/or global results, or None
    if the strategy is VECTOR (no graph needed).
    """
    if not settings.enabled:
        return None

    t0 = time.perf_counter()

    if strategy is None:
        decision = route_query(query, auto_route=settings.auto_route)
        strategy = decision.strategy
        logger.info("route_decision: %s (confidence=%.2f, %s)",
                     decision.strategy.value, decision.confidence, decision.reason)

    if strategy == SearchStrategy.VECTOR:
        return None

    local_result = None
    global_result = None

    if strategy in (SearchStrategy.LOCAL_GRAPH, SearchStrategy.HYBRID_GRAPH):
        local_result = await local_search(
            store,
            embedding_provider,
            tenant_id=tenant_id,
            query=query,
            top_k_entities=settings.local_max_entities,
            hops=settings.local_search_hops,
            max_entities=settings.local_max_entities,
            score_threshold=settings.entity_score_threshold,
        )

    if strategy in (SearchStrategy.GLOBAL_GRAPH, SearchStrategy.HYBRID_GRAPH):
        global_result = await global_search(
            store,
            embedding_provider,
            tenant_id=tenant_id,
            query=query,
            top_k_communities=settings.global_max_communities,
        )

    elapsed_ms = (time.perf_counter() - t0) * 1000

    return GraphSearchResult(
        local=local_result,
        global_=global_result,
        strategy=strategy.value,
        graph_ms=round(elapsed_ms, 1),
    )
