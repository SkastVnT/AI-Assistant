"""Tests for the query transformation pipeline.

Covers:
- Individual transforms: rewrite, acronym expansion, HyDE, decomposition
- TransformContext properties
- Pipeline orchestration with feature flags
- Integration with retrieve() — decomposition merge logic
- Timeout handling
- Example scenarios
"""

from __future__ import annotations

import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.core.settings import QueryTransformSettings
from libs.retrieval.search import SearchResult
from libs.retrieval.service import (
    RetrievalRequest,
    _merge_and_dedupe,
    retrieve,
)
from libs.retrieval.transforms.pipeline import (
    QueryTransformPipeline,
    TransformContext,
    decompose_query,
    expand_acronyms,
    generate_hyde_document,
    rewrite_query,
)

# ---------------------------------------------------------------------------
# Fake providers
# ---------------------------------------------------------------------------

TENANT_ID = uuid.uuid4()
DOC_ID = uuid.uuid4()
VER_ID = uuid.uuid4()


class FakeLLM:
    """Deterministic LLM for testing transforms."""

    def __init__(self, responses: dict[str, str] | None = None):
        self._responses = responses or {}
        self.calls: list[dict] = []

    async def complete(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        self.calls.append({"prompt": prompt, "system": system})
        # Return canned response based on system prompt keywords
        for key, response in self._responses.items():
            if key in (system or ""):
                return response
        return prompt  # echo back the prompt by default


class FakeEmbeddingProvider:
    def __init__(self, dimensions: int = 8):
        self._dim = dimensions
        self.model = "test-embed-model"

    @property
    def dimensions(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self._dim for _ in texts]


def _make_settings(**overrides) -> QueryTransformSettings:
    defaults = {
        "enable_rewrite": False,
        "enable_acronym_expansion": False,
        "enable_hyde": False,
        "enable_decomposition": False,
        "rewrite_timeout_ms": 5000,
        "hyde_timeout_ms": 5000,
        "decomposition_timeout_ms": 5000,
        "max_sub_queries": 3,
        "acronym_dict": {},
    }
    defaults.update(overrides)
    return QueryTransformSettings(**defaults)


def _make_search_result(
    *, chunk_id: uuid.UUID | None = None, score: float = 0.8
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=DOC_ID,
        version_id=VER_ID,
        content="chunk content",
        score=score,
        metadata={},
        filename="doc.pdf",
        chunk_index=0,
        sensitivity_level="internal",
        language="en",
        document_title="Test Doc",
        version_number=1,
    )


# ====================================================================
# TransformContext
# ====================================================================


class TestTransformContext:
    def test_effective_query_original(self):
        ctx = TransformContext(original_query="hello")
        assert ctx.effective_query == "hello"

    def test_effective_query_rewritten(self):
        ctx = TransformContext(original_query="hello", rewritten_query="hi there")
        assert ctx.effective_query == "hi there"

    def test_effective_query_expanded(self):
        ctx = TransformContext(original_query="hello", expanded_query="hello expanded")
        assert ctx.effective_query == "hello expanded"

    def test_effective_query_rewrite_takes_precedence(self):
        ctx = TransformContext(
            original_query="hello",
            rewritten_query="rewritten",
            expanded_query="expanded",
        )
        assert ctx.effective_query == "rewritten"

    def test_queries_for_retrieval_single(self):
        ctx = TransformContext(original_query="test")
        assert ctx.queries_for_retrieval == ["test"]

    def test_queries_for_retrieval_decomposed(self):
        ctx = TransformContext(
            original_query="complex",
            sub_queries=["sub1", "sub2"],
        )
        assert ctx.queries_for_retrieval == ["sub1", "sub2"]

    def test_hyde_text_none_by_default(self):
        ctx = TransformContext(original_query="test")
        assert ctx.hyde_text is None

    def test_hyde_text_set(self):
        ctx = TransformContext(original_query="test", hyde_document="hypo doc")
        assert ctx.hyde_text == "hypo doc"


# ====================================================================
# Individual transforms
# ====================================================================


class TestRewriteQuery:
    @pytest.mark.asyncio
    async def test_rewrite_success(self):
        llm = FakeLLM({"search query optimizer": "optimized query about revenue"})
        settings = _make_settings(enable_rewrite=True)
        ctx = TransformContext(original_query="what's the rev?")

        result = await rewrite_query(ctx, llm, settings)
        assert result.rewritten_query == "optimized query about revenue"
        assert len(result.transform_log) == 1
        assert result.transform_log[0]["transform"] == "rewrite"

    @pytest.mark.asyncio
    async def test_rewrite_timeout(self):
        async def slow_complete(*a, **kw):
            await asyncio.sleep(10)
            return "too slow"

        llm = MagicMock()
        llm.complete = slow_complete
        settings = _make_settings(enable_rewrite=True, rewrite_timeout_ms=10)
        ctx = TransformContext(original_query="test")

        result = await rewrite_query(ctx, llm, settings)
        assert result.rewritten_query is None
        assert result.transform_log[0].get("skipped") is True

    @pytest.mark.asyncio
    async def test_rewrite_llm_error(self):
        async def failing_complete(*a, **kw):
            raise RuntimeError("API down")

        llm = MagicMock()
        llm.complete = failing_complete
        settings = _make_settings(enable_rewrite=True, rewrite_timeout_ms=0)
        ctx = TransformContext(original_query="test")

        result = await rewrite_query(ctx, llm, settings)
        assert result.rewritten_query is None


class TestAcronymExpansion:
    def test_expand_known_acronym(self):
        settings = _make_settings(
            enable_acronym_expansion=True,
            acronym_dict={"ROI": "Return on Investment", "KPI": "Key Performance Indicator"},
        )
        ctx = TransformContext(original_query="What is the ROI for Q4?")
        result = expand_acronyms(ctx, settings)
        assert "Return on Investment" in result.expanded_query
        assert result.transform_log[0]["transform"] == "acronym_expansion"

    def test_expand_case_insensitive(self):
        settings = _make_settings(
            enable_acronym_expansion=True,
            acronym_dict={"api": "Application Programming Interface"},
        )
        ctx = TransformContext(original_query="How does the API work?")
        result = expand_acronyms(ctx, settings)
        assert "Application Programming Interface" in result.expanded_query

    def test_no_expansion_when_no_match(self):
        settings = _make_settings(
            enable_acronym_expansion=True,
            acronym_dict={"XYZ": "Unknown"},
        )
        ctx = TransformContext(original_query="What is revenue?")
        result = expand_acronyms(ctx, settings)
        assert result.expanded_query is None

    def test_empty_dict_noop(self):
        settings = _make_settings(enable_acronym_expansion=True)
        ctx = TransformContext(original_query="What is ROI?")
        result = expand_acronyms(ctx, settings)
        assert result.expanded_query is None

    def test_multiple_acronyms(self):
        settings = _make_settings(
            enable_acronym_expansion=True,
            acronym_dict={"ROI": "Return on Investment", "KPI": "Key Performance Indicator"},
        )
        ctx = TransformContext(original_query="Show KPI and ROI metrics")
        result = expand_acronyms(ctx, settings)
        assert "Key Performance Indicator" in result.expanded_query
        assert "Return on Investment" in result.expanded_query

    def test_expand_uses_rewritten_query(self):
        settings = _make_settings(
            enable_acronym_expansion=True,
            acronym_dict={"ROI": "Return on Investment"},
        )
        ctx = TransformContext(
            original_query="ROI?",
            rewritten_query="What is the current ROI metric?",
        )
        result = expand_acronyms(ctx, settings)
        assert "Return on Investment" in result.expanded_query
        assert "current" in result.expanded_query


class TestHyDE:
    @pytest.mark.asyncio
    async def test_hyde_generates_document(self):
        llm = FakeLLM({
            "knowledgeable assistant": "Revenue in Q4 was $50M, up 15% YoY."
        })
        settings = _make_settings(enable_hyde=True)
        ctx = TransformContext(original_query="What was Q4 revenue?")

        result = await generate_hyde_document(ctx, llm, settings)
        assert result.hyde_document == "Revenue in Q4 was $50M, up 15% YoY."
        assert result.transform_log[0]["transform"] == "hyde"

    @pytest.mark.asyncio
    async def test_hyde_timeout(self):
        async def slow(*a, **kw):
            await asyncio.sleep(10)
            return "too slow"

        llm = MagicMock()
        llm.complete = slow
        settings = _make_settings(enable_hyde=True, hyde_timeout_ms=10)
        ctx = TransformContext(original_query="test")

        result = await generate_hyde_document(ctx, llm, settings)
        assert result.hyde_document is None


class TestDecomposition:
    @pytest.mark.asyncio
    async def test_decompose_multi_hop(self):
        llm = FakeLLM({
            "question decomposer": (
                "1. What was Q4 revenue?\n"
                "2. What was Q3 revenue?\n"
                "3. What is the percentage change?"
            )
        })
        settings = _make_settings(enable_decomposition=True, max_sub_queries=3)
        ctx = TransformContext(
            original_query="How did Q4 revenue compare to Q3?"
        )

        result = await decompose_query(ctx, llm, settings)
        assert len(result.sub_queries) == 3
        assert "Q4 revenue" in result.sub_queries[0]

    @pytest.mark.asyncio
    async def test_decompose_simple_query_no_split(self):
        """A simple query should return 1 line — no decomposition."""
        llm = FakeLLM({
            "question decomposer": "1. What is the company revenue?"
        })
        settings = _make_settings(enable_decomposition=True)
        ctx = TransformContext(original_query="What is revenue?")

        result = await decompose_query(ctx, llm, settings)
        assert len(result.sub_queries) == 0  # single line = no decomposition

    @pytest.mark.asyncio
    async def test_decompose_respects_max(self):
        llm = FakeLLM({
            "question decomposer": "1. Q1\n2. Q2\n3. Q3\n4. Q4\n5. Q5"
        })
        settings = _make_settings(enable_decomposition=True, max_sub_queries=2)
        ctx = TransformContext(original_query="complex question")

        result = await decompose_query(ctx, llm, settings)
        assert len(result.sub_queries) == 2


# ====================================================================
# Pipeline orchestration
# ====================================================================


class TestQueryTransformPipeline:
    @pytest.mark.asyncio
    async def test_all_disabled_passthrough(self):
        settings = _make_settings()
        pipeline = QueryTransformPipeline(llm=None, settings=settings)
        ctx = await pipeline.transform("original query")
        assert ctx.effective_query == "original query"
        assert ctx.sub_queries == []
        assert ctx.hyde_document is None
        assert ctx.transform_log == []

    @pytest.mark.asyncio
    async def test_rewrite_only(self):
        llm = FakeLLM({"search query optimizer": "better query"})
        settings = _make_settings(enable_rewrite=True)
        pipeline = QueryTransformPipeline(llm=llm, settings=settings)
        ctx = await pipeline.transform("vague question")
        assert ctx.rewritten_query == "better query"
        assert ctx.effective_query == "better query"

    @pytest.mark.asyncio
    async def test_rewrite_then_expand(self):
        llm = FakeLLM({"search query optimizer": "What is the ROI metric?"})
        settings = _make_settings(
            enable_rewrite=True,
            enable_acronym_expansion=True,
            acronym_dict={"ROI": "Return on Investment"},
        )
        pipeline = QueryTransformPipeline(llm=llm, settings=settings)
        ctx = await pipeline.transform("ROI?")
        assert "Return on Investment" in ctx.expanded_query

    @pytest.mark.asyncio
    async def test_hyde_enabled(self):
        llm = FakeLLM({
            "knowledgeable assistant": "The revenue was $100M."
        })
        settings = _make_settings(enable_hyde=True)
        pipeline = QueryTransformPipeline(llm=llm, settings=settings)
        ctx = await pipeline.transform("What was revenue?")
        assert ctx.hyde_document == "The revenue was $100M."

    @pytest.mark.asyncio
    async def test_decomposition_enabled(self):
        llm = FakeLLM({
            "question decomposer": "1. Sub Q1\n2. Sub Q2"
        })
        settings = _make_settings(enable_decomposition=True)
        pipeline = QueryTransformPipeline(llm=llm, settings=settings)
        ctx = await pipeline.transform("complex multi-hop question")
        assert len(ctx.sub_queries) == 2

    @pytest.mark.asyncio
    async def test_no_llm_skips_llm_transforms(self):
        settings = _make_settings(
            enable_rewrite=True,
            enable_hyde=True,
            enable_decomposition=True,
            enable_acronym_expansion=True,
            acronym_dict={"AI": "Artificial Intelligence"},
        )
        pipeline = QueryTransformPipeline(llm=None, settings=settings)
        ctx = await pipeline.transform("AI research")
        # Only acronym expansion should fire (no LLM needed)
        assert ctx.rewritten_query is None
        assert ctx.hyde_document is None
        assert ctx.sub_queries == []
        assert "Artificial Intelligence" in ctx.expanded_query


# ====================================================================
# Merge and deduplicate
# ====================================================================


class TestMergeAndDedupe:
    def test_deduplicates_by_chunk_id(self):
        cid = uuid.uuid4()
        r1 = _make_search_result(chunk_id=cid, score=0.7)
        r2 = _make_search_result(chunk_id=cid, score=0.9)  # higher score wins
        r3 = _make_search_result(score=0.8)

        merged = _merge_and_dedupe([[r1, r3], [r2]], top_k=10)
        ids = [r.chunk_id for r in merged]
        assert ids.count(cid) == 1
        # cid should have the higher score
        for r in merged:
            if r.chunk_id == cid:
                assert r.score == 0.9

    def test_respects_top_k(self):
        results = [[_make_search_result(score=0.9 - i * 0.1) for i in range(5)]]
        merged = _merge_and_dedupe(results, top_k=3)
        assert len(merged) == 3

    def test_sorted_by_score_descending(self):
        r1 = _make_search_result(score=0.6)
        r2 = _make_search_result(score=0.9)
        r3 = _make_search_result(score=0.75)
        merged = _merge_and_dedupe([[r1], [r2], [r3]], top_k=10)
        scores = [r.score for r in merged]
        assert scores == sorted(scores, reverse=True)

    def test_empty_input(self):
        assert _merge_and_dedupe([], top_k=5) == []
        assert _merge_and_dedupe([[]], top_k=5) == []


# ====================================================================
# Integration: retrieve() with transforms
# ====================================================================


class TestRetrieveWithTransforms:
    @pytest.mark.asyncio
    async def test_retrieve_baseline_no_transforms(self):
        """When no pipeline is provided, behaves like baseline."""
        provider = FakeEmbeddingProvider()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        request = RetrievalRequest(
            tenant_id=TENANT_ID, user_id=None, query="test"
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[_make_search_result()],
        ):
            result = await retrieve(db, provider, request)

        assert result.total_found == 1
        assert result.transformed_query is None
        assert result.sub_queries == []
        assert result.transform_log == []

    @pytest.mark.asyncio
    async def test_retrieve_with_rewrite(self):
        provider = FakeEmbeddingProvider()
        llm = FakeLLM({"search query optimizer": "optimized query"})
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        settings = _make_settings(enable_rewrite=True)
        pipeline = QueryTransformPipeline(llm=llm, settings=settings)

        request = RetrievalRequest(
            tenant_id=TENANT_ID, user_id=None, query="vague question"
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[_make_search_result()],
        ):
            result = await retrieve(
                db, provider, request, llm=llm, transform_pipeline=pipeline
            )

        assert result.transformed_query == "optimized query"
        assert result.transform_ms >= 0
        assert result.total_found == 1

    @pytest.mark.asyncio
    async def test_retrieve_with_hyde(self):
        provider = FakeEmbeddingProvider()
        llm = FakeLLM({"knowledgeable assistant": "Hypothetical document about revenue"})
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        settings = _make_settings(enable_hyde=True)
        pipeline = QueryTransformPipeline(llm=llm, settings=settings)

        request = RetrievalRequest(
            tenant_id=TENANT_ID, user_id=None, query="What was Q4 revenue?"
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[_make_search_result()],
        ):
            result = await retrieve(
                db, provider, request, llm=llm, transform_pipeline=pipeline
            )

        assert result.total_found == 1
        # HyDE doc was used for search (logged in transform_log)
        hyde_log = [e for e in result.transform_log if e["transform"] == "hyde"]
        assert len(hyde_log) == 1

    @pytest.mark.asyncio
    async def test_retrieve_with_decomposition(self):
        provider = FakeEmbeddingProvider()
        llm = FakeLLM({
            "question decomposer": "1. What was Q4 revenue?\n2. What was Q3 revenue?"
        })
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        settings = _make_settings(enable_decomposition=True)
        pipeline = QueryTransformPipeline(llm=llm, settings=settings)

        cid1 = uuid.uuid4()
        cid2 = uuid.uuid4()

        call_count = 0

        async def mock_search(db, embedding_provider, text, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [_make_search_result(chunk_id=cid1, score=0.9)]
            return [_make_search_result(chunk_id=cid2, score=0.85)]

        request = RetrievalRequest(
            tenant_id=TENANT_ID, user_id=None, query="Compare Q3 and Q4 revenue"
        )

        with patch(
            "libs.retrieval.service._embed_and_search",
            side_effect=mock_search,
        ):
            result = await retrieve(
                db, provider, request, llm=llm, transform_pipeline=pipeline
            )

        assert result.total_found == 2
        assert len(result.sub_queries) == 2
        chunk_ids = {c.chunk_id for c in result.chunks}
        assert cid1 in chunk_ids
        assert cid2 in chunk_ids

    @pytest.mark.asyncio
    async def test_retrieve_trace_records_transform_info(self):
        provider = FakeEmbeddingProvider()
        llm = FakeLLM({"search query optimizer": "better"})
        db = AsyncMock()
        added = []
        db.add = MagicMock(side_effect=lambda obj: added.append(obj))
        db.flush = AsyncMock()

        settings = _make_settings(enable_rewrite=True)
        pipeline = QueryTransformPipeline(llm=llm, settings=settings)

        request = RetrievalRequest(
            tenant_id=TENANT_ID, user_id=None, query="original"
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[],
        ):
            await retrieve(
                db, provider, request, llm=llm, transform_pipeline=pipeline
            )

        from libs.core.models import RetrievalTrace

        traces = [o for o in added if isinstance(o, RetrievalTrace)]
        assert len(traces) == 1
        trace = traces[0]
        assert trace.transformed_query == "better"
        assert "transform_log" in trace.metadata_


# ====================================================================
# Feature flag config
# ====================================================================


class TestQueryTransformSettings:
    def test_defaults_all_disabled(self):
        s = QueryTransformSettings()
        assert s.enable_rewrite is False
        assert s.enable_acronym_expansion is False
        assert s.enable_hyde is False
        assert s.enable_decomposition is False

    def test_custom_values(self):
        s = QueryTransformSettings(
            enable_rewrite=True,
            rewrite_timeout_ms=1000,
            max_sub_queries=5,
            acronym_dict={"AI": "Artificial Intelligence"},
        )
        assert s.enable_rewrite is True
        assert s.rewrite_timeout_ms == 1000
        assert s.max_sub_queries == 5
        assert s.acronym_dict["AI"] == "Artificial Intelligence"


# ====================================================================
# Prompt templates
# ====================================================================


class TestPromptTemplates:
    def test_rewrite_prompt_format(self):
        from libs.retrieval.transforms.prompts import REWRITE_USER

        result = REWRITE_USER.format(query="What's the rev?")
        assert "What's the rev?" in result

    def test_hyde_prompt_format(self):
        from libs.retrieval.transforms.prompts import HYDE_USER

        result = HYDE_USER.format(query="What is Q4 revenue?")
        assert "Q4 revenue" in result

    def test_decomposition_prompt_format(self):
        from libs.retrieval.transforms.prompts import DECOMPOSITION_SYSTEM

        result = DECOMPOSITION_SYSTEM.format(max_sub_queries=3)
        assert "3" in result
