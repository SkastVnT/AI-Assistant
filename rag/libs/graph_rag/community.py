"""Community detection and LLM summarization for the knowledge graph.

Builds a networkx graph from stored entities/relationships, runs
community detection (Leiden or Louvain), then summarizes each community
with an LLM and embeds the summaries for global search.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from uuid import UUID

from libs.graph_rag.types import Community

if TYPE_CHECKING:
    from libs.core.providers.base import EmbeddingProvider, LLMProvider
    from libs.graph_rag.store import GraphStore

logger = logging.getLogger("rag.graph_rag.community")

# ═══════════════════════════════════════════════════════════════════════
# Community detection
# ═══════════════════════════════════════════════════════════════════════


async def detect_communities(
    store: GraphStore,
    tenant_id: UUID,
    *,
    algorithm: str = "leiden",
    resolution: float = 1.0,
    min_community_size: int = 3,
) -> list[Community]:
    """Run community detection on the entity-relationship graph.

    Parameters
    ----------
    store:
        GraphStore to read entities/relationships from.
    tenant_id:
        Tenant scope.
    algorithm:
        "leiden" (default) or "louvain".
    resolution:
        Resolution parameter — higher = smaller communities.
    min_community_size:
        Discard communities smaller than this.

    Returns
    -------
    List of Community objects (without summaries/embeddings yet).
    """
    import networkx as nx

    entities = await store.get_all_entities(tenant_id)
    relationships = await store.get_all_relationships(tenant_id)

    if not entities:
        logger.info("no_entities: skipping community detection for tenant=%s", tenant_id)
        return []

    # Build networkx graph
    graph = nx.Graph()
    id_to_entity = {}
    for e in entities:
        if e.id is not None:
            graph.add_node(str(e.id), name=e.name, entity_type=e.entity_type)
            id_to_entity[str(e.id)] = e

    for r in relationships:
        src = str(r.source_entity_id) if r.source_entity_id else r.source_entity
        tgt = str(r.target_entity_id) if r.target_entity_id else r.target_entity
        if graph.has_node(src) and graph.has_node(tgt):
            graph.add_edge(src, tgt, type=r.relationship_type, weight=r.weight)

    # Run community detection
    if algorithm == "leiden":
        partitions = _leiden_partition(graph, resolution=resolution)
    else:
        partitions = _louvain_partition(graph, resolution=resolution)

    # Build Community objects
    communities: list[Community] = []
    for comm_idx, node_ids in enumerate(partitions):
        if len(node_ids) < min_community_size:
            continue

        comm_entities = [id_to_entity[n] for n in node_ids if n in id_to_entity]
        entity_names = [e.name for e in comm_entities]
        entity_uuids = [e.id for e in comm_entities if e.id]

        # Count relationships within community
        rel_count = sum(
            1 for u, v in graph.edges()
            if u in node_ids and v in node_ids
        )

        community = Community(
            name=f"Community {comm_idx}",
            level=0,
            entity_ids=entity_uuids,
            entity_names=entity_names,
            relationship_count=rel_count,
        )
        communities.append(community)

    logger.info(
        "community_detection: tenant=%s algorithm=%s found=%d (min_size=%d)",
        tenant_id, algorithm, len(communities), min_community_size,
    )
    return communities


def _leiden_partition(graph, *, resolution: float) -> list[set[str]]:
    """Run Leiden community detection. Falls back to Louvain if unavailable."""
    try:
        import igraph as ig
        import leidenalg

        ig_graph = ig.Graph.from_networkx(graph)
        partition = leidenalg.find_partition(
            ig_graph,
            leidenalg.RBConfigurationVertexPartition,
            resolution_parameter=resolution,
        )
        nx_nodes = list(graph.nodes())
        communities: list[set[str]] = []
        for comm in partition:
            communities.append({nx_nodes[i] for i in comm})
        return communities
    except ImportError:
        logger.warning("leidenalg not installed, falling back to louvain")
        return _louvain_partition(graph, resolution=resolution)


def _louvain_partition(graph, *, resolution: float) -> list[set[str]]:
    """Run Louvain community detection using networkx."""
    from networkx.algorithms.community import louvain_communities

    communities = louvain_communities(graph, resolution=resolution)
    return [set(c) for c in communities]


# ═══════════════════════════════════════════════════════════════════════
# Community summarization
# ═══════════════════════════════════════════════════════════════════════

COMMUNITY_SUMMARY_SYSTEM = """\
You are a knowledge-graph analyst. Given a list of entities and their \
relationships within a community, write a concise summary (2-4 sentences) \
describing the theme, purpose, or topic of this community.

Focus on: What connects these entities? What domain or topic do they represent?
"""

COMMUNITY_SUMMARY_PROMPT = """\
Summarize this community of entities:

ENTITIES:
{entity_list}

RELATIONSHIPS:
{relationship_list}

Write a concise summary (2-4 sentences).
"""


async def summarize_communities(
    communities: list[Community],
    store: GraphStore,
    llm: LLMProvider,
    embedding_provider: EmbeddingProvider,
    tenant_id: UUID,
    *,
    max_tokens: int = 512,
) -> list[Community]:
    """Generate LLM summaries and embeddings for each community.

    Parameters
    ----------
    communities:
        Communities from detect_communities() (no summaries yet).
    store:
        GraphStore for persisting communities.
    llm, embedding_provider:
        For summarization and embedding.
    tenant_id:
        Tenant scope.
    max_tokens:
        Max tokens for summary generation.

    Returns
    -------
    Updated Community list with summaries, embeddings, and database IDs.
    """
    if not communities:
        return communities

    # Fetch all relationships once for context building
    all_relationships = await store.get_all_relationships(tenant_id)
    rel_lookup: dict[str, list] = {}
    for r in all_relationships:
        key_src = str(r.source_entity_id or r.source_entity)
        key_tgt = str(r.target_entity_id or r.target_entity)
        if key_src not in rel_lookup:
            rel_lookup[key_src] = []
        rel_lookup[key_src].append(r)
        if key_tgt not in rel_lookup:
            rel_lookup[key_tgt] = []
        rel_lookup[key_tgt].append(r)

    for community in communities:
        # Build entity list text
        entity_lines = [
            f"- [ENTITY] {name}" for name in community.entity_names
        ]
        entity_text = "\n".join(entity_lines[:30])  # cap for prompt size

        # Build relationship list text
        rel_lines = set()
        for eid in community.entity_ids:
            for r in rel_lookup.get(str(eid), []):
                desc = f"{r.source_entity} --[{r.relationship_type}]--> {r.target_entity}"
                rel_lines.add(desc)
        rel_text = "\n".join(f"- {r}" for r in list(rel_lines)[:30])

        prompt = COMMUNITY_SUMMARY_PROMPT.format(
            entity_list=entity_text or "(no entities)",
            relationship_list=rel_text or "(no relationships)",
        )

        summary = await llm.complete(
            prompt,
            system=COMMUNITY_SUMMARY_SYSTEM,
            temperature=0.1,
            max_tokens=max_tokens,
        )
        community.summary = summary.strip()

    # Embed all summaries in one batch
    summaries = [c.summary for c in communities if c.summary]
    if summaries:
        embeddings = await embedding_provider.embed(summaries)
        idx = 0
        for c in communities:
            if c.summary:
                c.summary_embedding = embeddings[idx]
                idx += 1

    # Persist communities
    for community in communities:
        community = await store.upsert_community(tenant_id, community)

    # Assign entities to communities
    for community in communities:
        if community.id:
            for entity_id in community.entity_ids:
                await store.assign_entity_community(entity_id, community.id)

    logger.info(
        "summarize_communities: tenant=%s summarized=%d",
        tenant_id, len(communities),
    )
    return communities
