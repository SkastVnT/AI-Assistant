"""Tests for the GraphRAG extension layer.

Covers:
- GraphRAG types (Entity, Relationship, Community, GraphNeighbourhood, etc.)
- Entity extraction (prompt construction, JSON parsing, error handling)
- Query router (heuristic routing, strategy selection)
- Local search (semantic entity search + neighbourhood traversal)
- Global search (community summary retrieval)
- Graph indexing workflow (end-to-end with mocks)
- Community detection (networkx-based, with mock store)
- GraphRAGSettings defaults and overrides
- GraphEntity / GraphRelationship / GraphCommunity model instantiation
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from libs.graph_rag.types import (
    Community,
    CommunitySearchResult,
    Entity,
    ExtractionResult,
    GraphNeighbourhood,
    GraphSearchResult,
    Relationship,
)

# ════════════════════════════════════════════════════════════════════
# Types — basic construction and to_context_text()
# ════════════════════════════════════════════════════════════════════


class TestEntity:
    def test_create_entity(self):
        e = Entity(name="Python", entity_type="TECHNOLOGY", description="A language")
        assert e.name == "Python"
        assert e.entity_type == "TECHNOLOGY"
        assert e.id is None
        assert e.embedding is None
        assert e.source_chunk_ids == []
        assert e.metadata == {}

    def test_entity_with_id(self):
        uid = uuid4()
        e = Entity(name="X", entity_type="CONCEPT", description="", id=uid)
        assert e.id == uid


class TestRelationship:
    def test_create_relationship(self):
        r = Relationship(
            source_entity="Python",
            target_entity="Django",
            relationship_type="USES",
            description="Django uses Python",
        )
        assert r.source_entity == "Python"
        assert r.target_entity == "Django"
        assert r.weight == 1.0

    def test_relationship_custom_weight(self):
        r = Relationship(
            source_entity="A", target_entity="B",
            relationship_type="RELATED_TO", description="", weight=0.5,
        )
        assert r.weight == 0.5


class TestExtractionResult:
    def test_empty(self):
        er = ExtractionResult(entities=[], relationships=[])
        assert er.chunk_id is None
        assert er.document_id is None

    def test_with_data(self):
        e = Entity(name="X", entity_type="CONCEPT", description="test")
        r = Relationship(
            source_entity="X", target_entity="Y",
            relationship_type="RELATED_TO", description="",
        )
        er = ExtractionResult(
            entities=[e], relationships=[r],
            chunk_id="c1", document_id="d1",
        )
        assert len(er.entities) == 1
        assert len(er.relationships) == 1


class TestCommunity:
    def test_create_community(self):
        c = Community(
            name="Tech Community",
            level=0,
            entity_ids=[uuid4()],
            entity_names=["Python"],
            relationship_count=5,
        )
        assert c.name == "Tech Community"
        assert c.summary == ""
        assert c.summary_embedding is None


class TestGraphNeighbourhood:
    def test_empty(self):
        gn = GraphNeighbourhood(
            seed_entities=[], neighbour_entities=[],
            relationships=[], source_chunks=[],
        )
        assert gn.all_entities == []
        # Still has headers even when empty
        ctx = gn.to_context_text()
        assert "Entity Knowledge Graph Context" in ctx

    def test_with_entities(self):
        e1 = Entity(name="Python", entity_type="TECHNOLOGY", description="A language")
        e2 = Entity(name="Django", entity_type="TECHNOLOGY", description="A framework")
        r = Relationship(
            source_entity="Python", target_entity="Django",
            relationship_type="USES", description="Django runs on Python",
        )
        gn = GraphNeighbourhood(
            seed_entities=[e1],
            neighbour_entities=[e2],
            relationships=[r],
            source_chunks=[{"chunk_id": "c1"}],
        )
        assert len(gn.all_entities) == 2
        ctx = gn.to_context_text()
        assert "Python" in ctx
        assert "Django" in ctx
        assert "USES" in ctx

    def test_all_entities_combines_seed_and_neighbour(self):
        e1 = Entity(name="A", entity_type="CONCEPT", description="")
        e2 = Entity(name="B", entity_type="CONCEPT", description="")
        e3 = Entity(name="C", entity_type="CONCEPT", description="")
        gn = GraphNeighbourhood(
            seed_entities=[e1],
            neighbour_entities=[e2, e3],
            relationships=[], source_chunks=[],
        )
        assert len(gn.all_entities) == 3


class TestCommunitySearchResult:
    def test_empty(self):
        csr = CommunitySearchResult(communities=[], total_found=0)
        ctx = csr.to_context_text()
        assert "Community Summaries" in ctx

    def test_with_communities(self):
        c = Community(
            name="AI", level=0, entity_ids=[],
            entity_names=[], relationship_count=3,
            summary="This community covers AI topics.",
        )
        csr = CommunitySearchResult(communities=[c], total_found=1)
        ctx = csr.to_context_text()
        assert "AI" in ctx
        assert "AI topics" in ctx


class TestGraphSearchResult:
    def test_vector_only(self):
        gsr = GraphSearchResult(
            local=None, global_=None,
            strategy="vector", graph_ms=0.0,
        )
        assert gsr.to_context_text() == ""

    def test_local_only(self):
        e = Entity(name="X", entity_type="CONCEPT", description="desc")
        gn = GraphNeighbourhood(
            seed_entities=[e], neighbour_entities=[],
            relationships=[], source_chunks=[],
        )
        gsr = GraphSearchResult(
            local=gn, global_=None,
            strategy="local", graph_ms=5.0,
        )
        ctx = gsr.to_context_text()
        assert "X" in ctx

    def test_hybrid(self):
        e = Entity(name="X", entity_type="CONCEPT", description="desc")
        gn = GraphNeighbourhood(
            seed_entities=[e], neighbour_entities=[],
            relationships=[], source_chunks=[],
        )
        c = Community(
            name="Comm", level=0, entity_ids=[],
            entity_names=[], relationship_count=0,
            summary="Summary text.",
        )
        csr = CommunitySearchResult(communities=[c], total_found=1)
        gsr = GraphSearchResult(
            local=gn, global_=csr,
            strategy="hybrid", graph_ms=10.0,
        )
        ctx = gsr.to_context_text()
        assert "X" in ctx
        assert "Summary text" in ctx


# ════════════════════════════════════════════════════════════════════
# Entity extraction
# ════════════════════════════════════════════════════════════════════

class TestExtraction:
    @pytest.fixture()
    def mock_llm(self):
        llm = AsyncMock()
        return llm

    @pytest.mark.asyncio
    async def test_extract_entities_basic(self, mock_llm):
        from libs.graph_rag.extraction import extract_entities_and_relationships

        mock_llm.complete.return_value = json.dumps({
            "entities": [
                {"name": "Python", "type": "TECHNOLOGY", "description": "A language"},
                {"name": "Django", "type": "TECHNOLOGY", "description": "A framework"},
            ],
            "relationships": [
                {
                    "source": "Django",
                    "target": "Python",
                    "type": "USES",
                    "description": "Django uses Python",
                },
            ],
        })

        result = await extract_entities_and_relationships(
            mock_llm, "Django is a Python web framework.",
            chunk_id="c1", document_id="d1",
        )

        assert isinstance(result, ExtractionResult)
        assert len(result.entities) == 2
        assert len(result.relationships) == 1
        assert result.entities[0].name == "Python"
        assert result.relationships[0].relationship_type == "USES"
        assert result.chunk_id == "c1"

    @pytest.mark.asyncio
    async def test_extract_with_markdown_fences(self, mock_llm):
        from libs.graph_rag.extraction import extract_entities_and_relationships

        mock_llm.complete.return_value = (
            "```json\n"
            + json.dumps({
                "entities": [
                    {"name": "X", "type": "CONCEPT", "description": "test"},
                ],
                "relationships": [],
            })
            + "\n```"
        )

        result = await extract_entities_and_relationships(
            mock_llm, "X is a concept.",
        )
        assert len(result.entities) == 1

    @pytest.mark.asyncio
    async def test_extract_invalid_json(self, mock_llm):
        from libs.graph_rag.extraction import extract_entities_and_relationships

        mock_llm.complete.return_value = "not valid json at all"

        result = await extract_entities_and_relationships(
            mock_llm, "some text",
        )
        assert result.entities == []
        assert result.relationships == []

    @pytest.mark.asyncio
    async def test_extract_deduplication(self, mock_llm):
        from libs.graph_rag.extraction import extract_entities_and_relationships

        mock_llm.complete.return_value = json.dumps({
            "entities": [
                {"name": "Python", "type": "TECHNOLOGY", "description": "v1"},
                {"name": "Python", "type": "TECHNOLOGY", "description": "v2"},
            ],
            "relationships": [],
        })

        result = await extract_entities_and_relationships(
            mock_llm, "Python Python",
        )
        assert len(result.entities) == 1

    @pytest.mark.asyncio
    async def test_extract_invalid_entity_type_normalised_to_other(self, mock_llm):
        from libs.graph_rag.extraction import extract_entities_and_relationships

        mock_llm.complete.return_value = json.dumps({
            "entities": [
                {"name": "X", "type": "INVALID_TYPE", "description": "test"},
            ],
            "relationships": [],
        })

        result = await extract_entities_and_relationships(mock_llm, "text")
        assert result.entities[0].entity_type == "OTHER"

    @pytest.mark.asyncio
    async def test_extract_relationship_with_unknown_entity_skipped(self, mock_llm):
        from libs.graph_rag.extraction import extract_entities_and_relationships

        mock_llm.complete.return_value = json.dumps({
            "entities": [
                {"name": "A", "type": "CONCEPT", "description": "desc"},
            ],
            "relationships": [
                {"source": "A", "target": "MISSING", "type": "RELATED_TO", "description": ""},
            ],
        })

        result = await extract_entities_and_relationships(mock_llm, "text")
        assert len(result.entities) == 1
        assert len(result.relationships) == 0  # skipped

    @pytest.mark.asyncio
    async def test_extract_respects_max_entities(self, mock_llm):
        from libs.graph_rag.extraction import extract_entities_and_relationships

        entities = [
            {"name": f"E{i}", "type": "CONCEPT", "description": ""}
            for i in range(50)
        ]
        mock_llm.complete.return_value = json.dumps({
            "entities": entities, "relationships": [],
        })

        result = await extract_entities_and_relationships(
            mock_llm, "text", max_entities=5,
        )
        assert len(result.entities) == 5

    @pytest.mark.asyncio
    async def test_extract_empty_name_skipped(self, mock_llm):
        from libs.graph_rag.extraction import extract_entities_and_relationships

        mock_llm.complete.return_value = json.dumps({
            "entities": [
                {"name": "", "type": "CONCEPT", "description": "no name"},
                {"name": "Valid", "type": "CONCEPT", "description": "has name"},
            ],
            "relationships": [],
        })

        result = await extract_entities_and_relationships(mock_llm, "text")
        assert len(result.entities) == 1
        assert result.entities[0].name == "Valid"


# ════════════════════════════════════════════════════════════════════
# Extraction prompt constants
# ════════════════════════════════════════════════════════════════════

class TestExtractionPrompts:
    def test_system_prompt_has_entity_types(self):
        from libs.graph_rag.extraction import ENTITY_EXTRACTION_SYSTEM
        assert "PERSON" in ENTITY_EXTRACTION_SYSTEM
        assert "ORGANIZATION" in ENTITY_EXTRACTION_SYSTEM
        assert "TECHNOLOGY" in ENTITY_EXTRACTION_SYSTEM

    def test_system_prompt_has_relationship_types(self):
        from libs.graph_rag.extraction import ENTITY_EXTRACTION_SYSTEM
        assert "USES" in ENTITY_EXTRACTION_SYSTEM
        assert "PART_OF" in ENTITY_EXTRACTION_SYSTEM

    def test_extraction_prompt_has_placeholder(self):
        from libs.graph_rag.extraction import ENTITY_EXTRACTION_PROMPT
        assert "{chunk_text}" in ENTITY_EXTRACTION_PROMPT

    def test_valid_entity_types_set(self):
        from libs.graph_rag.extraction import VALID_ENTITY_TYPES
        assert "PERSON" in VALID_ENTITY_TYPES
        assert len(VALID_ENTITY_TYPES) == 9

    def test_valid_relationship_types_set(self):
        from libs.graph_rag.extraction import VALID_RELATIONSHIP_TYPES
        assert "USES" in VALID_RELATIONSHIP_TYPES
        assert len(VALID_RELATIONSHIP_TYPES) == 13


# ════════════════════════════════════════════════════════════════════
# Query router
# ════════════════════════════════════════════════════════════════════

class TestRouter:
    def test_route_disabled(self):
        from libs.graph_rag.router import SearchStrategy, route_query
        decision = route_query("anything", auto_route=False)
        assert decision.strategy == SearchStrategy.VECTOR
        assert decision.confidence == 1.0

    def test_route_local_entity_query(self):
        from libs.graph_rag.router import SearchStrategy, route_query
        decision = route_query("What is the relationship between Python and Django?")
        assert decision.strategy in (
            SearchStrategy.LOCAL_GRAPH, SearchStrategy.HYBRID_GRAPH,
        )

    def test_route_global_summary_query(self):
        from libs.graph_rag.router import SearchStrategy, route_query
        decision = route_query("Give me an overview of the main themes")
        assert decision.strategy in (
            SearchStrategy.GLOBAL_GRAPH, SearchStrategy.HYBRID_GRAPH,
        )

    def test_route_vector_no_indicators(self):
        from libs.graph_rag.router import SearchStrategy, route_query
        decision = route_query("fast search query")
        assert decision.strategy == SearchStrategy.VECTOR

    def test_route_hybrid_mixed_signals(self):
        from libs.graph_rag.router import SearchStrategy, route_query
        decision = route_query("Summarize the relationship between concepts")
        # "summarize" = global, "relationship between" = local → hybrid
        assert decision.strategy == SearchStrategy.HYBRID_GRAPH

    def test_route_capitalized_names_boost_local(self):
        from libs.graph_rag.router import SearchStrategy, route_query
        decision = route_query("Tell me about Microsoft Azure Cloud")
        assert decision.strategy in (
            SearchStrategy.LOCAL_GRAPH, SearchStrategy.HYBRID_GRAPH,
        )

    def test_search_strategy_values(self):
        from libs.graph_rag.router import SearchStrategy
        assert SearchStrategy.VECTOR.value == "vector"
        assert SearchStrategy.LOCAL_GRAPH.value == "local"
        assert SearchStrategy.GLOBAL_GRAPH.value == "global"
        assert SearchStrategy.HYBRID_GRAPH.value == "hybrid"


# ════════════════════════════════════════════════════════════════════
# Local search
# ════════════════════════════════════════════════════════════════════

class TestLocalSearch:
    @pytest.fixture()
    def mock_store(self):
        store = AsyncMock()
        return store

    @pytest.fixture()
    def mock_embedding(self):
        provider = AsyncMock()
        provider.embed.return_value = [[0.1] * 10]
        return provider

    @pytest.mark.asyncio
    async def test_local_search_no_results(self, mock_store, mock_embedding):
        from libs.graph_rag.local_search import local_search

        mock_store.search_entities_by_embedding.return_value = []

        result = await local_search(
            mock_store, mock_embedding,
            tenant_id=uuid4(), query="test query",
        )
        assert isinstance(result, GraphNeighbourhood)
        assert result.seed_entities == []

    @pytest.mark.asyncio
    async def test_local_search_with_results(self, mock_store, mock_embedding):
        from libs.graph_rag.local_search import local_search

        entity = Entity(
            id=uuid4(), name="Python",
            entity_type="TECHNOLOGY", description="A language",
        )
        mock_store.search_entities_by_embedding.return_value = [
            (entity, 0.9),
        ]
        mock_store.get_entity_neighbourhood.return_value = GraphNeighbourhood(
            seed_entities=[entity],
            neighbour_entities=[],
            relationships=[],
            source_chunks=[],
        )

        result = await local_search(
            mock_store, mock_embedding,
            tenant_id=uuid4(), query="test query",
        )
        assert len(result.seed_entities) == 1
        mock_store.get_entity_neighbourhood.assert_called_once()

    @pytest.mark.asyncio
    async def test_local_search_passes_params(self, mock_store, mock_embedding):
        from libs.graph_rag.local_search import local_search

        mock_store.search_entities_by_embedding.return_value = []
        tid = uuid4()

        await local_search(
            mock_store, mock_embedding,
            tenant_id=tid, query="q",
            top_k_entities=3, hops=1, max_entities=10,
            score_threshold=0.5,
        )
        mock_store.search_entities_by_embedding.assert_called_once_with(
            tid, [0.1] * 10, top_k=3, score_threshold=0.5,
        )


# ════════════════════════════════════════════════════════════════════
# Global search
# ════════════════════════════════════════════════════════════════════

class TestGlobalSearch:
    @pytest.fixture()
    def mock_store(self):
        return AsyncMock()

    @pytest.fixture()
    def mock_embedding(self):
        provider = AsyncMock()
        provider.embed.return_value = [[0.2] * 10]
        return provider

    @pytest.mark.asyncio
    async def test_global_search_no_results(self, mock_store, mock_embedding):
        from libs.graph_rag.global_search import global_search

        mock_store.search_communities_by_embedding.return_value = []

        result = await global_search(
            mock_store, mock_embedding,
            tenant_id=uuid4(), query="overview",
        )
        assert isinstance(result, CommunitySearchResult)
        assert result.total_found == 0

    @pytest.mark.asyncio
    async def test_global_search_with_results(self, mock_store, mock_embedding):
        from libs.graph_rag.global_search import global_search

        comm = Community(
            id=uuid4(), name="AI",
            level=0, entity_ids=[], entity_names=[],
            relationship_count=5, summary="AI community summary.",
        )
        mock_store.search_communities_by_embedding.return_value = [
            (comm, 0.85),
        ]

        result = await global_search(
            mock_store, mock_embedding,
            tenant_id=uuid4(), query="what are the main themes",
        )
        assert result.total_found == 1
        assert result.communities[0].name == "AI"


# ════════════════════════════════════════════════════════════════════
# Graph search (router orchestration)
# ════════════════════════════════════════════════════════════════════

class TestGraphSearch:
    @pytest.fixture()
    def mock_settings(self):
        settings = MagicMock()
        settings.enabled = True
        settings.auto_route = True
        settings.local_search_hops = 2
        settings.local_max_entities = 20
        settings.global_max_communities = 10
        settings.entity_score_threshold = 0.3
        return settings

    @pytest.fixture()
    def mock_store(self):
        return AsyncMock()

    @pytest.fixture()
    def mock_embedding(self):
        provider = AsyncMock()
        provider.embed.return_value = [[0.1] * 10]
        return provider

    @pytest.mark.asyncio
    async def test_graph_search_disabled(self, mock_store, mock_embedding):
        from libs.graph_rag.router import graph_search

        settings = MagicMock()
        settings.enabled = False

        result = await graph_search(
            mock_store, mock_embedding, settings,
            tenant_id=uuid4(), query="anything",
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_graph_search_vector_strategy_returns_none(
        self, mock_store, mock_embedding, mock_settings,
    ):
        from libs.graph_rag.router import SearchStrategy, graph_search

        result = await graph_search(
            mock_store, mock_embedding, mock_settings,
            tenant_id=uuid4(), query="test",
            strategy=SearchStrategy.VECTOR,
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_graph_search_local_strategy(
        self, mock_store, mock_embedding, mock_settings,
    ):
        from libs.graph_rag.router import SearchStrategy, graph_search

        mock_store.search_entities_by_embedding.return_value = []

        result = await graph_search(
            mock_store, mock_embedding, mock_settings,
            tenant_id=uuid4(), query="test",
            strategy=SearchStrategy.LOCAL_GRAPH,
        )
        assert isinstance(result, GraphSearchResult)
        assert result.strategy == "local"
        assert result.local is not None

    @pytest.mark.asyncio
    async def test_graph_search_global_strategy(
        self, mock_store, mock_embedding, mock_settings,
    ):
        from libs.graph_rag.router import SearchStrategy, graph_search

        mock_store.search_communities_by_embedding.return_value = []

        result = await graph_search(
            mock_store, mock_embedding, mock_settings,
            tenant_id=uuid4(), query="test",
            strategy=SearchStrategy.GLOBAL_GRAPH,
        )
        assert isinstance(result, GraphSearchResult)
        assert result.strategy == "global"
        assert result.global_ is not None


# ════════════════════════════════════════════════════════════════════
# Graph indexer
# ════════════════════════════════════════════════════════════════════

class TestIndexer:
    @pytest.fixture()
    def mock_deps(self):
        store = AsyncMock()
        llm = AsyncMock()
        embedding_provider = AsyncMock()
        settings = MagicMock()
        settings.max_entities_per_chunk = 20
        settings.max_relationships_per_chunk = 30
        settings.extraction_temperature = 0.0
        settings.community_algorithm = "louvain"
        settings.community_resolution = 1.0
        settings.min_community_size = 3
        settings.max_community_summary_tokens = 512
        return store, llm, embedding_provider, settings

    @pytest.mark.asyncio
    async def test_index_empty_chunks(self, mock_deps):
        from libs.graph_rag.indexer import index_document_graph

        store, llm, emb, settings = mock_deps
        store.get_all_entities.return_value = []

        result = await index_document_graph(
            store, llm, emb, settings,
            tenant_id=uuid4(), document_id=uuid4(), chunks=[],
        )
        assert result["entities_count"] == 0
        assert result["relationships_count"] == 0

    @pytest.mark.asyncio
    async def test_index_single_chunk(self, mock_deps):
        from libs.graph_rag.indexer import index_document_graph

        store, llm, emb, settings = mock_deps

        llm.complete.return_value = json.dumps({
            "entities": [
                {"name": "Python", "type": "TECHNOLOGY", "description": "A language"},
            ],
            "relationships": [],
        })
        store.upsert_entity.return_value = Entity(
            name="Python", entity_type="TECHNOLOGY", description="A language",
        )
        store.get_all_entities.return_value = []

        result = await index_document_graph(
            store, llm, emb, settings,
            tenant_id=uuid4(), document_id=uuid4(),
            chunks=[{"id": "c1", "text": "Python is a language."}],
        )
        assert result["entities_count"] == 1
        assert store.upsert_entity.call_count >= 1

    @pytest.mark.asyncio
    async def test_index_returns_stats(self, mock_deps):
        from libs.graph_rag.indexer import index_document_graph

        store, llm, emb, settings = mock_deps
        llm.complete.return_value = json.dumps({
            "entities": [], "relationships": [],
        })
        store.get_all_entities.return_value = []

        result = await index_document_graph(
            store, llm, emb, settings,
            tenant_id=uuid4(), document_id=uuid4(), chunks=[],
        )
        assert "elapsed_ms" in result
        assert "communities_count" in result
        assert isinstance(result["elapsed_ms"], float)


# ════════════════════════════════════════════════════════════════════
# Community detection
# ════════════════════════════════════════════════════════════════════

class TestCommunityDetection:
    @pytest.fixture()
    def entities_and_rels(self):
        """Create a small graph: A-B-C connected, D-E connected."""
        ids = [uuid4() for _ in range(5)]
        entities = [
            Entity(id=ids[0], name="A", entity_type="CONCEPT", description="a"),
            Entity(id=ids[1], name="B", entity_type="CONCEPT", description="b"),
            Entity(id=ids[2], name="C", entity_type="CONCEPT", description="c"),
            Entity(id=ids[3], name="D", entity_type="CONCEPT", description="d"),
            Entity(id=ids[4], name="E", entity_type="CONCEPT", description="e"),
        ]
        relationships = [
            Relationship(
                source_entity="A", target_entity="B",
                relationship_type="RELATED_TO", description="",
                source_entity_id=ids[0], target_entity_id=ids[1],
            ),
            Relationship(
                source_entity="B", target_entity="C",
                relationship_type="RELATED_TO", description="",
                source_entity_id=ids[1], target_entity_id=ids[2],
            ),
            Relationship(
                source_entity="A", target_entity="C",
                relationship_type="RELATED_TO", description="",
                source_entity_id=ids[0], target_entity_id=ids[2],
            ),
            Relationship(
                source_entity="D", target_entity="E",
                relationship_type="RELATED_TO", description="",
                source_entity_id=ids[3], target_entity_id=ids[4],
            ),
        ]
        return entities, relationships

    @pytest.mark.asyncio
    async def test_detect_communities_empty(self):
        from libs.graph_rag.community import detect_communities

        store = AsyncMock()
        store.get_all_entities.return_value = []
        store.get_all_relationships.return_value = []

        result = await detect_communities(store, uuid4())
        assert result == []

    @pytest.mark.asyncio
    async def test_detect_communities_finds_groups(self, entities_and_rels):
        from libs.graph_rag.community import detect_communities

        entities, relationships = entities_and_rels
        store = AsyncMock()
        store.get_all_entities.return_value = entities
        store.get_all_relationships.return_value = relationships

        # min_community_size=2 to catch the D-E pair
        result = await detect_communities(
            store, uuid4(),
            algorithm="louvain", min_community_size=2,
        )
        # Should find at least 1 community (A-B-C cluster)
        assert len(result) >= 1
        # Each community should have entity_ids
        for c in result:
            assert len(c.entity_ids) >= 2

    @pytest.mark.asyncio
    async def test_detect_communities_min_size_filters(self, entities_and_rels):
        from libs.graph_rag.community import detect_communities

        entities, relationships = entities_and_rels
        store = AsyncMock()
        store.get_all_entities.return_value = entities
        store.get_all_relationships.return_value = relationships

        # min_community_size=10 should filter everything
        result = await detect_communities(
            store, uuid4(),
            algorithm="louvain", min_community_size=10,
        )
        assert result == []


# ════════════════════════════════════════════════════════════════════
# Community summarization
# ════════════════════════════════════════════════════════════════════

class TestCommunitySummarization:
    @pytest.mark.asyncio
    async def test_summarize_empty_list(self):
        from libs.graph_rag.community import summarize_communities

        result = await summarize_communities(
            [], AsyncMock(), AsyncMock(), AsyncMock(), uuid4(),
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_summarize_generates_summaries(self):
        from libs.graph_rag.community import summarize_communities

        store = AsyncMock()
        store.get_all_relationships.return_value = []
        store.upsert_community.side_effect = lambda tid, c: c

        llm = AsyncMock()
        llm.complete.return_value = "This is a test community summary."

        emb = AsyncMock()
        emb.embed.return_value = [[0.1] * 10]

        community = Community(
            name="Test", level=0,
            entity_ids=[uuid4()], entity_names=["A"],
            relationship_count=0,
        )

        result = await summarize_communities(
            [community], store, llm, emb, uuid4(),
        )
        assert len(result) == 1
        assert result[0].summary == "This is a test community summary."
        assert result[0].summary_embedding is not None


# ════════════════════════════════════════════════════════════════════
# GraphRAGSettings
# ════════════════════════════════════════════════════════════════════

class TestGraphRAGSettings:
    def test_defaults(self):
        from libs.core.settings import GraphRAGSettings
        s = GraphRAGSettings()
        assert s.enabled is False
        assert s.store_backend == "postgres"
        assert s.max_entities_per_chunk == 20
        assert s.max_relationships_per_chunk == 30
        assert s.community_algorithm == "leiden"
        assert s.local_search_hops == 2
        assert s.auto_route is True

    def test_in_root_settings(self):
        from libs.core.settings import Settings
        s = Settings()
        assert hasattr(s, "graph_rag")
        assert s.graph_rag.enabled is False


# ════════════════════════════════════════════════════════════════════
# DB models instantiation
# ════════════════════════════════════════════════════════════════════

class TestGraphModels:
    def test_graph_entity_model(self):
        from libs.core.models import GraphEntity
        e = GraphEntity(
            tenant_id=uuid4(), name="Python",
            entity_type="TECHNOLOGY", description="A language",
        )
        assert e.name == "Python"
        assert e.entity_type == "TECHNOLOGY"

    def test_graph_relationship_model(self):
        from libs.core.models import GraphRelationship
        r = GraphRelationship(
            tenant_id=uuid4(),
            source_entity_id=uuid4(),
            target_entity_id=uuid4(),
            relationship_type="USES",
            description="uses",
        )
        assert r.relationship_type == "USES"

    def test_graph_community_model(self):
        from libs.core.models import GraphCommunity
        c = GraphCommunity(
            tenant_id=uuid4(), name="Cluster 0",
            level=0, summary="A summary",
            entity_count=5, relationship_count=10,
        )
        assert c.name == "Cluster 0"
        assert c.level == 0


# ════════════════════════════════════════════════════════════════════
# Store protocol
# ════════════════════════════════════════════════════════════════════

class TestStoreProtocol:
    def test_graph_store_is_protocol(self):
        from libs.graph_rag.store import GraphStore
        assert hasattr(GraphStore, "__protocol_attrs__") or hasattr(
            GraphStore, "__abstractmethods__"
        ) or hasattr(GraphStore, "_is_protocol")

    def test_neo4j_store_raises(self):
        from libs.graph_rag.store import Neo4jGraphStore
        store = Neo4jGraphStore(
            uri="bolt://localhost:7687",
            user="neo4j", password="test", database="neo4j",
        )
        with pytest.raises(NotImplementedError):
            import asyncio
            asyncio.get_event_loop().run_until_complete(
                store.upsert_entity(uuid4(), Entity(
                    name="X", entity_type="CONCEPT", description="",
                ))
            )

    def test_postgres_store_init(self):
        from libs.graph_rag.store import PostgresGraphStore
        factory = MagicMock()
        store = PostgresGraphStore(factory)
        assert store._session_factory is factory


# ════════════════════════════════════════════════════════════════════
# Reindex helper
# ════════════════════════════════════════════════════════════════════

class TestReindex:
    @pytest.mark.asyncio
    async def test_reindex_tenant_graph(self):
        from libs.graph_rag.indexer import reindex_tenant_graph

        store = AsyncMock()
        store.get_all_entities.return_value = []
        store.get_all_relationships.return_value = []

        llm = AsyncMock()
        emb = AsyncMock()

        settings = MagicMock()
        settings.community_algorithm = "louvain"
        settings.community_resolution = 1.0
        settings.min_community_size = 3
        settings.max_community_summary_tokens = 512

        result = await reindex_tenant_graph(
            store, llm, emb, settings, tenant_id=uuid4(),
        )
        assert "communities_count" in result
        assert "elapsed_ms" in result
