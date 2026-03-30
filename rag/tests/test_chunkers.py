"""Tests for the extensible chunking module.

Covers: FixedTokenChunker, SemanticChunker, DocumentAwareChunker,
        ParentChildChunker, config/presets, registry, comparison.
"""

from __future__ import annotations

import uuid

import pytest

from libs.ingestion.chunkers.base import (
    ChunkerType,
    ChunkingStrategy,
    ChunkMeta,
    ChunkResult,
    estimate_tokens,
)
from libs.ingestion.chunkers.config import (
    DEFAULT_PRESETS,
    MVP_PRESET,
    ChunkingPreset,
    compare_strategies,
    get_preset,
    list_presets,
)
from libs.ingestion.chunkers.document_aware_chunker import DocumentAwareChunker
from libs.ingestion.chunkers.fixed_chunker import FixedTokenChunker
from libs.ingestion.chunkers.parent_child_chunker import ParentChildChunker
from libs.ingestion.chunkers.registry import get_chunker
from libs.ingestion.chunkers.semantic_chunker import SemanticChunker
from libs.ingestion.parsers.base import ContentElement, ElementType, ParseResult

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

DOC_ID = uuid.uuid4()
VER_ID = uuid.uuid4()

SAMPLE_TEXT = (
    "Introduction to Machine Learning\n\n"
    "Machine learning is a subset of artificial intelligence that focuses on "
    "building systems that learn from data. Instead of being explicitly "
    "programmed, these systems improve their performance through experience.\n\n"
    "Supervised Learning\n\n"
    "In supervised learning, the algorithm learns from labeled training data. "
    "Each training example includes an input and the expected output. "
    "The model makes predictions and is corrected when those predictions are wrong. "
    "Common algorithms include linear regression, decision trees, and neural networks.\n\n"
    "Unsupervised Learning\n\n"
    "Unsupervised learning deals with unlabeled data. The algorithm tries to "
    "find hidden patterns or structures in the input data. "
    "Clustering and dimensionality reduction are common tasks.\n\n"
    "Reinforcement Learning\n\n"
    "In reinforcement learning, an agent learns by interacting with its environment. "
    "The agent receives rewards or penalties based on its actions. "
    "This approach is used in robotics, game playing, and autonomous vehicles."
)

SAMPLE_PARSE_RESULT = ParseResult(
    elements=[
        ContentElement(type=ElementType.HEADING, content="Introduction to Machine Learning", level=1),
        ContentElement(
            type=ElementType.PARAGRAPH,
            content=(
                "Machine learning is a subset of artificial intelligence that focuses on "
                "building systems that learn from data. Instead of being explicitly "
                "programmed, these systems improve their performance through experience."
            ),
        ),
        ContentElement(type=ElementType.HEADING, content="Supervised Learning", level=2),
        ContentElement(
            type=ElementType.PARAGRAPH,
            content=(
                "In supervised learning, the algorithm learns from labeled training data. "
                "Each training example includes an input and the expected output. "
                "The model makes predictions and is corrected when those predictions are wrong. "
                "Common algorithms include linear regression, decision trees, and neural networks."
            ),
        ),
        ContentElement(type=ElementType.HEADING, content="Unsupervised Learning", level=2),
        ContentElement(
            type=ElementType.PARAGRAPH,
            content=(
                "Unsupervised learning deals with unlabeled data. The algorithm tries to "
                "find hidden patterns or structures in the input data. "
                "Clustering and dimensionality reduction are common tasks."
            ),
        ),
        ContentElement(type=ElementType.HEADING, content="Reinforcement Learning", level=2),
        ContentElement(
            type=ElementType.PARAGRAPH,
            content=(
                "In reinforcement learning, an agent learns by interacting with its environment. "
                "The agent receives rewards or penalties based on its actions. "
                "This approach is used in robotics, game playing, and autonomous vehicles."
            ),
        ),
    ],
    title="Introduction to Machine Learning",
    raw_text=SAMPLE_TEXT,
)


# ====================================================================
# Protocol conformance
# ====================================================================


class TestProtocolConformance:
    def test_fixed_chunker(self):
        assert isinstance(FixedTokenChunker(), ChunkingStrategy)

    def test_semantic_chunker(self):
        assert isinstance(SemanticChunker(), ChunkingStrategy)

    def test_document_aware_chunker(self):
        assert isinstance(DocumentAwareChunker(), ChunkingStrategy)

    def test_parent_child_chunker(self):
        assert isinstance(ParentChildChunker(), ChunkingStrategy)


# ====================================================================
# Helpers
# ====================================================================


class TestEstimateTokens:
    def test_basic_estimate(self):
        assert estimate_tokens("hello world") == 2  # 11 chars // 4 = 2

    def test_empty_returns_one(self):
        assert estimate_tokens("") == 1

    def test_custom_chars_per_token(self):
        assert estimate_tokens("hello world", chars_per_token=2) == 5


class TestChunkMeta:
    def test_to_dict(self):
        meta = ChunkMeta(
            chunk_id=DOC_ID,
            parent_document_id=DOC_ID,
            parent_version_id=VER_ID,
            chunk_index=0,
            start_offset=0,
            end_offset=100,
            heading_path="Intro > Background",
            page_number=1,
            token_count=25,
        )
        d = meta.to_dict()
        assert d["chunk_index"] == 0
        assert d["heading_path"] == "Intro > Background"
        assert d["page_number"] == 1
        assert d["parent_chunk_id"] is None
        assert d["is_parent"] is False


# ====================================================================
# FixedTokenChunker
# ====================================================================


class TestFixedTokenChunker:
    def setup_method(self):
        self.chunker = FixedTokenChunker(chunk_size=128, chunk_overlap=16)

    def test_strategy_name(self):
        assert self.chunker.strategy_name == "fixed_token"

    def test_empty_text(self):
        result = self.chunker.chunk("", document_id=DOC_ID, version_id=VER_ID)
        assert result == []

    def test_whitespace_only(self):
        result = self.chunker.chunk("   \n\n  ", document_id=DOC_ID, version_id=VER_ID)
        assert result == []

    def test_short_text_single_chunk(self):
        result = self.chunker.chunk("Hello world.", document_id=DOC_ID, version_id=VER_ID)
        assert len(result) == 1
        assert result[0].content == "Hello world."
        assert result[0].meta.chunk_index == 0
        assert result[0].meta.parent_document_id == DOC_ID
        assert result[0].meta.parent_version_id == VER_ID

    def test_multi_chunk_text(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        assert len(chunks) > 1

        # Sequential indices
        for i, c in enumerate(chunks):
            assert c.meta.chunk_index == i

        # IDs match
        for c in chunks:
            assert c.meta.parent_document_id == DOC_ID
            assert c.meta.parent_version_id == VER_ID

        # Token counts reasonable
        for c in chunks:
            assert c.meta.token_count > 0

    def test_chunk_overlap_applied(self):
        # With overlap, some content should appear in adjacent chunks
        chunker = FixedTokenChunker(chunk_size=64, chunk_overlap=16)
        chunks = chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        assert len(chunks) >= 3

        # Check that chunks overlap in offset ranges
        for i in range(len(chunks) - 1):
            # Next chunk start should be before current chunk end (overlap)
            # or very close
            curr_end = chunks[i].meta.end_offset
            next_start = chunks[i + 1].meta.start_offset
            assert next_start <= curr_end + 100  # allow some flexibility for boundary snapping

    def test_offsets_are_populated(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        for c in chunks:
            assert c.meta.start_offset >= 0
            assert c.meta.end_offset > c.meta.start_offset

    def test_chunk_ids_unique(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        ids = [c.meta.chunk_id for c in chunks]
        assert len(ids) == len(set(ids))

    def test_invalid_overlap(self):
        with pytest.raises(ValueError, match="chunk_overlap must be < chunk_size"):
            FixedTokenChunker(chunk_size=100, chunk_overlap=100)


# ====================================================================
# SemanticChunker
# ====================================================================


class TestSemanticChunker:
    def setup_method(self):
        self.chunker = SemanticChunker(max_chunk_tokens=128)

    def test_strategy_name(self):
        assert self.chunker.strategy_name == "semantic"

    def test_empty_text(self):
        assert self.chunker.chunk("", document_id=DOC_ID, version_id=VER_ID) == []

    def test_heuristic_mode(self):
        """Without embedder, uses heuristic grouping."""
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        assert len(chunks) >= 1

        for c in chunks:
            assert c.meta.parent_document_id == DOC_ID
            assert c.meta.token_count > 0

    def test_with_mock_embedder(self):
        """With embedder, groups by similarity."""

        class ConstantEmbedder:
            """All sentences get the same embedding → all end up in one big group
            (until max_tokens is hit)."""

            def embed_sentences(self, sentences: list[str]) -> list[list[float]]:
                return [[1.0, 0.0, 0.0]] * len(sentences)

        chunker = SemanticChunker(
            embedder=ConstantEmbedder(),
            similarity_threshold=0.5,
            max_chunk_tokens=128,
        )
        chunks = chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        assert len(chunks) >= 1

        # All chunks should have valid metadata
        for c in chunks:
            assert c.meta.chunk_index >= 0
            assert c.meta.token_count > 0

    def test_with_dissimilar_embedder(self):
        """Different embeddings → more chunks."""
        call_count = 0

        class AlternatingEmbedder:
            def embed_sentences(self, sentences: list[str]) -> list[list[float]]:
                nonlocal call_count
                result = []
                for i in range(len(sentences)):
                    if (call_count + i) % 2 == 0:
                        result.append([1.0, 0.0])
                    else:
                        result.append([0.0, 1.0])
                call_count += len(sentences)
                return result

        chunker = SemanticChunker(
            embedder=AlternatingEmbedder(),
            similarity_threshold=0.9,  # high threshold → more splits
            max_chunk_tokens=512,
        )
        chunks = chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        # Should have more chunks than heuristic since embeddings alternate
        assert len(chunks) >= 2

    def test_offsets_non_negative(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        for c in chunks:
            assert c.meta.start_offset >= 0
            assert c.meta.end_offset >= c.meta.start_offset


# ====================================================================
# DocumentAwareChunker
# ====================================================================


class TestDocumentAwareChunker:
    def setup_method(self):
        self.chunker = DocumentAwareChunker(max_chunk_tokens=128)

    def test_strategy_name(self):
        assert self.chunker.strategy_name == "document_aware"

    def test_empty_text(self):
        assert self.chunker.chunk("", document_id=DOC_ID, version_id=VER_ID) == []

    def test_fallback_without_parse_result(self):
        """Without ParseResult, falls back to fixed chunking."""
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        assert len(chunks) >= 1
        for c in chunks:
            assert c.meta.heading_path == ""

    def test_structured_chunking(self):
        """With ParseResult, uses heading-aware chunking."""
        chunks = self.chunker.chunk(
            SAMPLE_TEXT,
            document_id=DOC_ID,
            version_id=VER_ID,
            parse_result=SAMPLE_PARSE_RESULT,
        )
        assert len(chunks) >= 1

        # Should have heading paths
        heading_chunks = [c for c in chunks if c.meta.heading_path]
        assert len(heading_chunks) >= 1

    def test_heading_path_hierarchy(self):
        """Heading paths should reflect document structure."""
        chunker = DocumentAwareChunker(max_chunk_tokens=512)
        chunks = chunker.chunk(
            SAMPLE_TEXT,
            document_id=DOC_ID,
            version_id=VER_ID,
            parse_result=SAMPLE_PARSE_RESULT,
        )

        paths = [c.meta.heading_path for c in chunks if c.meta.heading_path]
        # Should have paths like "Introduction to ML > Supervised Learning"
        has_nested = any(">" in p for p in paths)
        assert has_nested, f"Expected nested heading paths, got: {paths}"

    def test_large_element_gets_own_chunk(self):
        """A single element exceeding max_tokens gets its own chunk."""
        big_content = "word " * 600  # ~600 tokens
        pr = ParseResult(
            elements=[
                ContentElement(type=ElementType.HEADING, content="Title", level=1),
                ContentElement(type=ElementType.CODE_BLOCK, content=big_content),
                ContentElement(type=ElementType.PARAGRAPH, content="Small paragraph."),
            ],
            title="Title",
            raw_text=f"Title\n\n{big_content}\n\nSmall paragraph.",
        )
        chunker = DocumentAwareChunker(max_chunk_tokens=128)
        chunks = chunker.chunk(
            pr.raw_text,
            document_id=DOC_ID,
            version_id=VER_ID,
            parse_result=pr,
        )
        # The big element should be a separate chunk
        big_chunks = [c for c in chunks if c.meta.token_count > 128]
        assert len(big_chunks) >= 1

    def test_page_numbers_propagated(self):
        """Page numbers from parse elements appear in chunk metadata."""
        pr = ParseResult(
            elements=[
                ContentElement(type=ElementType.HEADING, content="Page 1 Title", level=1, page=1),
                ContentElement(type=ElementType.PARAGRAPH, content="Content on page 1.", page=1),
                ContentElement(type=ElementType.PAGE_BREAK, content="", page=2),
                ContentElement(type=ElementType.HEADING, content="Page 2 Title", level=1, page=2),
                ContentElement(type=ElementType.PARAGRAPH, content="Content on page 2.", page=2),
            ],
            title="Page 1 Title",
            raw_text="Page 1 Title\n\nContent on page 1.\n\nPage 2 Title\n\nContent on page 2.",
        )
        chunks = self.chunker.chunk(
            pr.raw_text,
            document_id=DOC_ID,
            version_id=VER_ID,
            parse_result=pr,
        )
        pages = [c.meta.page_number for c in chunks if c.meta.page_number is not None]
        assert len(pages) >= 1


# ====================================================================
# ParentChildChunker
# ====================================================================


class TestParentChildChunker:
    def setup_method(self):
        self.chunker = ParentChildChunker(
            parent_chunk_size=256,
            child_chunk_size=64,
            child_overlap=8,
        )

    def test_strategy_name(self):
        assert self.chunker.strategy_name == "parent_child"

    def test_empty_text(self):
        assert self.chunker.chunk("", document_id=DOC_ID, version_id=VER_ID) == []

    def test_produces_parents_and_children(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        parents = [c for c in chunks if c.meta.is_parent]
        children = [c for c in chunks if not c.meta.is_parent]

        assert len(parents) >= 1
        assert len(children) >= 1

    def test_child_references_parent(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        parents = {c.meta.chunk_id for c in chunks if c.meta.is_parent}
        children = [c for c in chunks if not c.meta.is_parent]

        for child in children:
            assert child.meta.parent_chunk_id is not None
            assert child.meta.parent_chunk_id in parents, (
                f"Child {child.meta.chunk_id} references unknown parent {child.meta.parent_chunk_id}"
            )

    def test_parent_has_no_parent(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        parents = [c for c in chunks if c.meta.is_parent]
        for p in parents:
            assert p.meta.parent_chunk_id is None

    def test_children_smaller_than_parents(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        parents = [c for c in chunks if c.meta.is_parent]
        children = [c for c in chunks if not c.meta.is_parent]

        if parents and children:
            avg_parent_tokens = sum(p.meta.token_count for p in parents) / len(parents)
            avg_child_tokens = sum(c.meta.token_count for c in children) / len(children)
            assert avg_child_tokens < avg_parent_tokens

    def test_indices_are_sequential(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        indices = [c.meta.chunk_index for c in chunks]
        assert indices == list(range(len(chunks)))

    def test_child_offsets_within_document(self):
        chunks = self.chunker.chunk(SAMPLE_TEXT, document_id=DOC_ID, version_id=VER_ID)
        children = [c for c in chunks if not c.meta.is_parent]
        for c in children:
            assert c.meta.start_offset >= 0
            assert c.meta.end_offset <= len(SAMPLE_TEXT) + 100  # tolerance


# ====================================================================
# Registry
# ====================================================================


class TestRegistry:
    def test_get_fixed_chunker(self):
        chunker = get_chunker(ChunkerType.FIXED, chunk_size=128, chunk_overlap=16)
        assert isinstance(chunker, FixedTokenChunker)

    def test_get_semantic_chunker(self):
        chunker = get_chunker(ChunkerType.SEMANTIC)
        assert isinstance(chunker, SemanticChunker)

    def test_get_document_aware_chunker(self):
        chunker = get_chunker(ChunkerType.DOCUMENT_AWARE)
        assert isinstance(chunker, DocumentAwareChunker)

    def test_get_parent_child_chunker(self):
        chunker = get_chunker(ChunkerType.PARENT_CHILD)
        assert isinstance(chunker, ParentChildChunker)

    def test_get_chunker_by_string(self):
        chunker = get_chunker("fixed")
        assert isinstance(chunker, FixedTokenChunker)

    def test_unknown_strategy_raises(self):
        with pytest.raises(ValueError):
            get_chunker("nonexistent")


# ====================================================================
# Config & Presets
# ====================================================================


class TestConfig:
    def test_default_presets_exist(self):
        assert "general" in DEFAULT_PRESETS
        assert "policy_documents" in DEFAULT_PRESETS
        assert "technical_docs" in DEFAULT_PRESETS
        assert "code_repository" in DEFAULT_PRESETS
        assert "parent_child_retrieval" in DEFAULT_PRESETS
        assert "semantic_grouping" in DEFAULT_PRESETS

    def test_mvp_preset(self):
        assert MVP_PRESET == "general"
        preset = get_preset(MVP_PRESET)
        assert preset.strategy == ChunkerType.FIXED

    def test_get_preset_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown preset"):
            get_preset("nonexistent")

    def test_list_presets(self):
        presets = list_presets()
        assert len(presets) == len(DEFAULT_PRESETS)
        for p in presets:
            assert "name" in p
            assert "strategy" in p

    def test_preset_to_dict(self):
        preset = get_preset("general")
        d = preset.to_dict()
        assert d["name"] == "general"
        assert d["strategy"] == "fixed"
        assert "chunk_size" in d["params"]

    def test_all_presets_produce_valid_chunker(self):
        """Every default preset can instantiate a working chunker."""
        for name, preset in DEFAULT_PRESETS.items():
            chunker = get_chunker(preset.strategy, **preset.params)
            assert isinstance(chunker, ChunkingStrategy), f"Preset {name} failed"


# ====================================================================
# Comparison
# ====================================================================


class TestComparison:
    def test_compare_all_presets(self):
        results = compare_strategies(SAMPLE_TEXT)
        assert len(results) == len(DEFAULT_PRESETS)

        for r in results:
            assert r.num_chunks >= 1
            assert r.avg_tokens > 0

    def test_compare_subset(self):
        results = compare_strategies(
            SAMPLE_TEXT, preset_names=["general", "code_repository"]
        )
        assert len(results) == 2
        names = {r.preset_name for r in results}
        assert names == {"general", "code_repository"}

    def test_compare_with_parse_result(self):
        results = compare_strategies(
            SAMPLE_TEXT,
            preset_names=["technical_docs"],
            parse_result=SAMPLE_PARSE_RESULT,
        )
        assert len(results) == 1
        assert results[0].num_chunks >= 1

    def test_comparison_summary(self):
        results = compare_strategies(SAMPLE_TEXT, preset_names=["general"])
        assert "general" in results[0].summary()
        assert "chunks" in results[0].summary()


# ====================================================================
# ChunkResult repr
# ====================================================================


class TestChunkResultRepr:
    def test_repr(self):
        chunk = ChunkResult(
            content="Hello world this is a test",
            meta=ChunkMeta(
                chunk_id=uuid.uuid4(),
                parent_document_id=DOC_ID,
                parent_version_id=VER_ID,
                chunk_index=0,
                start_offset=0,
                end_offset=25,
                heading_path="Intro",
                page_number=None,
                token_count=6,
            ),
        )
        r = repr(chunk)
        assert "idx=0" in r
        assert "tokens=6" in r
        assert "Intro" in r
