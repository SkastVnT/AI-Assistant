"""Tests for hybrid retrieval: RRF fusion, rerankers, hybrid pipeline, eval metrics.

Covers:
- Reciprocal Rank Fusion (fusion.py)
- Reranker protocol, CrossEncoder, LateInteraction (rerankers.py)
- HybridRetrievalPipeline (hybrid.py)
- Evaluation metrics (eval_retrieval.py)
- Integration with retrieve() service
- HybridRetrievalSettings
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.core.settings import HybridRetrievalSettings
from libs.retrieval.fusion import reciprocal_rank_fusion
from libs.retrieval.hybrid import HybridRetrievalPipeline
from libs.retrieval.rerankers import (
    CrossEncoderReranker,
    LateInteractionReranker,
    _word_overlap_scores,
    create_reranker,
)
from libs.retrieval.search import SearchResult
from libs.retrieval.service import RetrievalRequest, retrieve
from scripts.eval_retrieval import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
    run_evaluation,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT_ID = uuid.uuid4()
DOC_ID = uuid.uuid4()
VER_ID = uuid.uuid4()


def _sr(
    *,
    chunk_id: uuid.UUID | None = None,
    score: float = 0.5,
    content: str = "chunk content",
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=DOC_ID,
        version_id=VER_ID,
        content=content,
        score=score,
        metadata={},
        filename="doc.pdf",
        chunk_index=0,
        sensitivity_level="internal",
        language="en",
        document_title="Test",
        version_number=1,
    )


class FakeEmbeddingProvider:
    model = "test-embed"

    @property
    def dimensions(self) -> int:
        return 8

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * 8 for _ in texts]


# ====================================================================
# Reciprocal Rank Fusion
# ====================================================================


class TestRRF:
    def test_single_list_passthrough(self):
        c1, c2 = _sr(score=0.9), _sr(score=0.7)
        fused = reciprocal_rank_fusion([[c1, c2]])
        assert len(fused) == 2
        assert fused[0].chunk_id == c1.chunk_id
        assert fused[1].chunk_id == c2.chunk_id

    def test_two_lists_merge(self):
        cid_shared = uuid.uuid4()
        cid_a = uuid.uuid4()
        cid_b = uuid.uuid4()

        list_a = [_sr(chunk_id=cid_shared, score=0.9), _sr(chunk_id=cid_a, score=0.7)]
        list_b = [_sr(chunk_id=cid_b, score=0.85), _sr(chunk_id=cid_shared, score=0.6)]

        fused = reciprocal_rank_fusion([list_a, list_b], k=60)

        ids = [r.chunk_id for r in fused]
        assert len(ids) == 3
        # Shared chunk gets contribution from both lists → highest RRF score
        assert ids[0] == cid_shared

    def test_rrf_score_formula(self):
        """Verify the exact RRF score for a simple case."""
        cid = uuid.uuid4()
        # Rank 1 in list A (k=60): 1/(60+1) = 0.01639...
        # Rank 2 in list B (k=60): 1/(60+2) = 0.01613...
        # Total: ~0.03252
        list_a = [_sr(chunk_id=cid)]
        list_b = [_sr(), _sr(chunk_id=cid)]
        fused = reciprocal_rank_fusion([list_a, list_b], k=60)
        shared = next(r for r in fused if r.chunk_id == cid)
        expected = 1 / 61 + 1 / 62
        assert abs(shared.score - expected) < 1e-10

    def test_weights(self):
        cid_a = uuid.uuid4()
        cid_b = uuid.uuid4()
        list_a = [_sr(chunk_id=cid_a)]
        list_b = [_sr(chunk_id=cid_b)]

        # Weight list_b 10x higher
        fused = reciprocal_rank_fusion([list_a, list_b], k=60, weights=[1.0, 10.0])
        assert fused[0].chunk_id == cid_b  # higher weighted list wins

    def test_top_k_limit(self):
        results = [_sr() for _ in range(10)]
        fused = reciprocal_rank_fusion([results], top_k=3)
        assert len(fused) == 3

    def test_empty_input(self):
        assert reciprocal_rank_fusion([]) == []
        assert reciprocal_rank_fusion([[]]) == []

    def test_weight_length_mismatch(self):
        with pytest.raises(ValueError, match="weights length"):
            reciprocal_rank_fusion([[_sr()]], weights=[1.0, 2.0])

    def test_sorted_by_rrf_score_desc(self):
        results = [_sr(score=0.1 * i) for i in range(5)]
        fused = reciprocal_rank_fusion([results])
        scores = [r.score for r in fused]
        assert scores == sorted(scores, reverse=True)


# ====================================================================
# Rerankers
# ====================================================================


class TestWordOverlapScores:
    def test_full_overlap(self):
        scores = _word_overlap_scores([("hello world", "hello world")])
        assert scores[0] == 1.0

    def test_partial_overlap(self):
        scores = _word_overlap_scores([("hello world", "hello there")])
        assert 0.0 < scores[0] < 1.0

    def test_no_overlap(self):
        scores = _word_overlap_scores([("hello", "goodbye")])
        assert scores[0] == 0.0

    def test_empty_query(self):
        scores = _word_overlap_scores([("", "hello world")])
        assert scores[0] == 0.0


class TestCrossEncoderReranker:
    @pytest.mark.asyncio
    async def test_rerank_returns_sorted(self):
        async def fake_score(model, pairs):
            return [0.3, 0.9, 0.1]  # middle chunk is most relevant

        reranker = CrossEncoderReranker(score_fn=fake_score)
        candidates = [_sr(content=f"chunk {i}") for i in range(3)]
        results = await reranker.rerank("test query", candidates)
        assert len(results) == 3
        assert results[0].rerank_score == 0.9
        assert results[2].rerank_score == 0.1

    @pytest.mark.asyncio
    async def test_rerank_top_n(self):
        async def fake_score(model, pairs):
            return [float(i) for i in range(len(pairs))]

        reranker = CrossEncoderReranker(score_fn=fake_score)
        candidates = [_sr() for _ in range(10)]
        results = await reranker.rerank("query", candidates, top_n=3)
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_rerank_empty(self):
        reranker = CrossEncoderReranker()
        results = await reranker.rerank("query", [])
        assert results == []


class TestLateInteractionReranker:
    @pytest.mark.asyncio
    async def test_rerank_returns_results(self):
        reranker = LateInteractionReranker()
        candidates = [_sr(content="hello world"), _sr(content="goodbye moon")]
        results = await reranker.rerank("hello", candidates)
        assert len(results) == 2
        # "hello world" should score higher (word overlap)
        assert results[0].rerank_score >= results[1].rerank_score


class TestCreateReranker:
    def test_cross_encoder(self):
        r = create_reranker("cross_encoder")
        assert isinstance(r, CrossEncoderReranker)

    def test_late_interaction(self):
        r = create_reranker("late_interaction")
        assert isinstance(r, LateInteractionReranker)

    def test_unknown_type(self):
        with pytest.raises(ValueError, match="Unknown reranker"):
            create_reranker("nonexistent")


# ====================================================================
# Hybrid Pipeline
# ====================================================================


class TestHybridPipeline:
    @pytest.mark.asyncio
    async def test_dense_only_when_lexical_disabled(self):
        settings = HybridRetrievalSettings(
            enable_lexical=False,
            enable_reranking=False,
            dense_top_k=10,
            final_context_k=3,
        )
        pipeline = HybridRetrievalPipeline(settings=settings)
        db = AsyncMock()
        provider = FakeEmbeddingProvider()

        dense_results = [_sr(score=0.9), _sr(score=0.8)]

        with patch(
            "libs.retrieval.hybrid.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=dense_results,
        ):
            result = await pipeline.execute(
                db, provider, "test query", tenant_id=TENANT_ID
            )

        assert result.strategy == "dense_only"
        assert len(result.dense_results) == 2
        assert len(result.lexical_results) == 0
        assert result.lexical_ms == 0

    @pytest.mark.asyncio
    async def test_hybrid_rrf_when_lexical_enabled(self):
        settings = HybridRetrievalSettings(
            enable_lexical=True,
            enable_reranking=False,
            dense_top_k=5,
            lexical_top_k=5,
            final_context_k=3,
        )
        pipeline = HybridRetrievalPipeline(settings=settings)
        db = AsyncMock()
        provider = FakeEmbeddingProvider()

        cid_shared = uuid.uuid4()
        dense_results = [_sr(chunk_id=cid_shared, score=0.9), _sr(score=0.7)]
        lex_results = [_sr(chunk_id=cid_shared, score=0.8), _sr(score=0.6)]

        with (
            patch(
                "libs.retrieval.hybrid.vector_search_from_embedding",
                new_callable=AsyncMock,
                return_value=dense_results,
            ),
            patch(
                "libs.retrieval.hybrid.lexical_search",
                new_callable=AsyncMock,
                return_value=lex_results,
            ),
        ):
            result = await pipeline.execute(
                db, provider, "test", tenant_id=TENANT_ID
            )

        assert result.strategy == "hybrid_rrf"
        assert len(result.lexical_results) == 2
        assert len(result.fused_results) > 0

    @pytest.mark.asyncio
    async def test_hybrid_with_reranking(self):
        async def fake_score(model, pairs):
            return [0.5 + 0.1 * i for i in range(len(pairs))]

        settings = HybridRetrievalSettings(
            enable_lexical=True,
            enable_reranking=True,
            dense_top_k=5,
            lexical_top_k=5,
            rerank_top_n=10,
            final_context_k=2,
        )
        reranker = CrossEncoderReranker(score_fn=fake_score)
        pipeline = HybridRetrievalPipeline(settings=settings, reranker=reranker)
        db = AsyncMock()
        provider = FakeEmbeddingProvider()

        dense_results = [_sr(score=0.9), _sr(score=0.8)]
        lex_results = [_sr(score=0.7)]

        with (
            patch(
                "libs.retrieval.hybrid.vector_search_from_embedding",
                new_callable=AsyncMock,
                return_value=dense_results,
            ),
            patch(
                "libs.retrieval.hybrid.lexical_search",
                new_callable=AsyncMock,
                return_value=lex_results,
            ),
        ):
            result = await pipeline.execute(
                db, provider, "test", tenant_id=TENANT_ID
            )

        assert "rerank" in result.strategy
        assert len(result.reranked_results) > 0
        assert len(result.results) <= 2
        assert result.rerank_ms >= 0

    @pytest.mark.asyncio
    async def test_uses_precomputed_embedding(self):
        settings = HybridRetrievalSettings(
            enable_lexical=False,
            enable_reranking=False,
        )
        pipeline = HybridRetrievalPipeline(settings=settings)
        db = AsyncMock()
        provider = FakeEmbeddingProvider()

        with patch(
            "libs.retrieval.hybrid.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[_sr()],
        ) as mock_vs:
            await pipeline.execute(
                db,
                provider,
                "test",
                query_embedding=[0.5] * 8,
                tenant_id=TENANT_ID,
            )

        # Should use the precomputed embedding, not call embed()
        call_args = mock_vs.call_args
        assert call_args[0][1] == [0.5] * 8


# ====================================================================
# Integration: retrieve() with hybrid pipeline
# ====================================================================


class TestRetrieveWithHybrid:
    @pytest.mark.asyncio
    async def test_retrieve_with_hybrid_pipeline(self):
        provider = FakeEmbeddingProvider()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        from libs.retrieval.hybrid import HybridPipelineResult

        fake_hybrid_result = HybridPipelineResult(
            results=[_sr(score=0.95)],
            dense_results=[_sr(score=0.9), _sr(score=0.8)],
            lexical_results=[_sr(score=0.7)],
            fused_results=[_sr(score=0.032)],
            reranked_results=[],
            dense_ms=10,
            lexical_ms=5,
            fusion_ms=1,
            rerank_ms=0,
            total_ms=16,
            strategy="hybrid_rrf",
        )

        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=fake_hybrid_result)

        request = RetrievalRequest(
            tenant_id=TENANT_ID, user_id=None, query="test"
        )

        result = await retrieve(
            db, provider, request, hybrid_pipeline=mock_pipeline
        )

        assert result.retrieval_strategy == "hybrid_rrf"
        assert result.dense_count == 2
        assert result.lexical_count == 1
        assert result.total_found == 1

    @pytest.mark.asyncio
    async def test_retrieve_falls_back_to_dense_without_hybrid(self):
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
            return_value=[_sr()],
        ):
            result = await retrieve(db, provider, request)

        assert result.retrieval_strategy == "vector_cosine"
        assert result.lexical_count == 0
        assert result.reranked_count == 0


# ====================================================================
# Evaluation metrics
# ====================================================================


class TestEvalMetrics:
    def test_precision_at_k(self):
        ids = [uuid.uuid4() for _ in range(5)]
        relevant = {ids[0], ids[2]}
        assert precision_at_k(ids, relevant, 5) == 2 / 5

    def test_precision_at_k_empty(self):
        assert precision_at_k([], set(), 5) == 0.0

    def test_recall_at_k(self):
        ids = [uuid.uuid4() for _ in range(5)]
        relevant = {ids[0], ids[2], uuid.uuid4()}  # 2 of 3 found
        assert recall_at_k(ids, relevant, 5) == pytest.approx(2 / 3)

    def test_recall_no_relevant(self):
        assert recall_at_k([uuid.uuid4()], set(), 5) == 0.0

    def test_reciprocal_rank_first(self):
        ids = [uuid.uuid4() for _ in range(3)]
        assert reciprocal_rank(ids, {ids[0]}) == 1.0

    def test_reciprocal_rank_third(self):
        ids = [uuid.uuid4() for _ in range(3)]
        assert reciprocal_rank(ids, {ids[2]}) == pytest.approx(1 / 3)

    def test_reciprocal_rank_not_found(self):
        ids = [uuid.uuid4() for _ in range(3)]
        assert reciprocal_rank(ids, {uuid.uuid4()}) == 0.0

    def test_ndcg_perfect(self):
        ids = [uuid.uuid4() for _ in range(3)]
        relevant = set(ids)
        assert ndcg_at_k(ids, relevant, 3) == pytest.approx(1.0)

    def test_ndcg_empty(self):
        assert ndcg_at_k([], set(), 5) == 0.0

    @pytest.mark.asyncio
    async def test_run_evaluation(self):
        metrics = await run_evaluation(k=5)
        assert "dense_only" in metrics
        assert "hybrid_rrf" in metrics
        assert "hybrid_rrf+rerank" in metrics
        # All strategies should have metrics
        for m in metrics.values():
            assert m.num_queries > 0
            assert 0.0 <= m.precision_at_k <= 1.0
            assert 0.0 <= m.recall_at_k <= 1.0


# ====================================================================
# Config
# ====================================================================


class TestHybridRetrievalSettings:
    def test_defaults(self):
        s = HybridRetrievalSettings()
        assert s.enable_lexical is False
        assert s.enable_reranking is False
        assert s.dense_top_k == 20
        assert s.lexical_top_k == 20
        assert s.rrf_k == 60
        assert s.rerank_top_n == 20
        assert s.final_context_k == 5

    def test_custom(self):
        s = HybridRetrievalSettings(
            enable_lexical=True,
            enable_reranking=True,
            dense_top_k=50,
            rrf_k=30,
            reranker_type="late_interaction",
        )
        assert s.enable_lexical is True
        assert s.dense_top_k == 50
        assert s.rrf_k == 30
        assert s.reranker_type == "late_interaction"
