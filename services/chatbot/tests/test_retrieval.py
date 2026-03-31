"""
Tests for the retrieval layer: RedisCache + RetrievalService.

Run from services/chatbot/:
    python -m pytest tests/test_retrieval.py -v
"""
from __future__ import annotations

import asyncio
import json
import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT = "test-tenant"
DIM = 4  # tiny dimension for tests


def _fake_vector(seed: float = 0.1) -> list[float]:
    return [seed] * DIM


# ---------------------------------------------------------------------------
# RedisCache unit tests
# ---------------------------------------------------------------------------


class TestRedisCacheKeyDeterminism:
    """Cache key must be stable and unique for the inputs."""

    def test_same_inputs_same_key(self):
        from src.rag.cache.redis_cache import _cache_key

        k1 = _cache_key("t1", "hello", 5, None)
        k2 = _cache_key("t1", "hello", 5, None)
        assert k1 == k2

    def test_different_query_different_key(self):
        from src.rag.cache.redis_cache import _cache_key

        k1 = _cache_key("t1", "hello", 5, None)
        k2 = _cache_key("t1", "world", 5, None)
        assert k1 != k2

    def test_doc_ids_order_ignored(self):
        from src.rag.cache.redis_cache import _cache_key

        k1 = _cache_key("t1", "q", 5, ["b", "a"])
        k2 = _cache_key("t1", "q", 5, ["a", "b"])
        assert k1 == k2

    def test_different_tenant_different_key(self):
        from src.rag.cache.redis_cache import _cache_key

        k1 = _cache_key("t1", "q", 5, None)
        k2 = _cache_key("t2", "q", 5, None)
        assert k1 != k2

    def test_key_prefix(self):
        from src.rag.cache.redis_cache import _cache_key

        k = _cache_key("t", "q", 3, None)
        assert k.startswith("rag:retrieve:")


class TestRedisCacheNoOp:
    """When Redis is unavailable the cache silently does nothing."""

    def test_construction_without_redis(self):
        from src.rag.cache.redis_cache import RedisCache

        cache = RedisCache("redis://localhost:1/0")  # unlikely port
        # _redis may or may not be set depending on env, but must not raise
        assert isinstance(cache, RedisCache)

    @pytest.mark.asyncio
    async def test_get_returns_none_when_disabled(self):
        from src.rag.cache.redis_cache import RedisCache

        cache = RedisCache.__new__(RedisCache)
        cache._redis = None
        cache._ttl = 60
        result = await cache.get_retrieval("t", "q", 5)
        assert result is None

    @pytest.mark.asyncio
    async def test_set_does_not_raise_when_disabled(self):
        from src.rag.cache.redis_cache import RedisCache

        cache = RedisCache.__new__(RedisCache)
        cache._redis = None
        cache._ttl = 60
        await cache.set_retrieval("t", "q", 5, [{"a": 1}])  # no-op


class TestRedisCacheMocked:
    """Test cache hit / miss with a mocked async Redis client."""

    @pytest.fixture
    def cache(self):
        from src.rag.cache.redis_cache import RedisCache

        c = RedisCache.__new__(RedisCache)
        c._ttl = 300
        c._redis = AsyncMock()
        return c

    @pytest.mark.asyncio
    async def test_cache_miss(self, cache):
        cache._redis.get = AsyncMock(return_value=None)
        result = await cache.get_retrieval("t", "q", 5)
        assert result is None

    @pytest.mark.asyncio
    async def test_cache_hit(self, cache):
        payload = [{"chunk_id": "abc", "score": 0.9}]
        cache._redis.get = AsyncMock(return_value=json.dumps(payload))
        result = await cache.get_retrieval("t", "q", 5)
        assert result == payload

    @pytest.mark.asyncio
    async def test_set_calls_redis(self, cache):
        cache._redis.set = AsyncMock()
        await cache.set_retrieval("t", "q", 5, [{"x": 1}])
        cache._redis.set.assert_awaited_once()


# ---------------------------------------------------------------------------
# RetrievalHit DTO
# ---------------------------------------------------------------------------


class TestRetrievalHit:
    def test_to_dict(self):
        from src.rag.service.retrieval_service import RetrievalHit

        hit = RetrievalHit(
            chunk_id="c1",
            document_id="d1",
            title="Test",
            content="hello",
            score=0.85,
            metadata_json={"page_number": 1},
        )
        d = hit.to_dict()
        assert d["chunk_id"] == "c1"
        assert d["score"] == 0.85
        assert d["metadata_json"] == {"page_number": 1}

    def test_frozen(self):
        from src.rag.service.retrieval_service import RetrievalHit

        hit = RetrievalHit(
            chunk_id="c1", document_id="d1", title="T",
            content="x", score=0.5,
        )
        with pytest.raises(AttributeError):
            hit.score = 1.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RetrievalService — mocked DB + embedder
# ---------------------------------------------------------------------------


class _FakeEmbedder:
    """Minimal embedder that returns a fixed vector."""

    def embed_query(self, text: str) -> list[float]:
        return _fake_vector(0.5)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [_fake_vector(0.5)] * len(texts)

    @property
    def dimension(self) -> int:
        return DIM


class TestRetrievalServiceUnit:
    """Unit tests with mocked DB session and no real Redis."""

    @pytest.fixture
    def service(self):
        from src.rag.service.retrieval_service import RetrievalService

        with patch("src.rag.service.retrieval_service.get_rag_settings") as mock_cfg:
            mock_cfg.return_value = MagicMock(
                embed_provider="openai",
                embed_model="test",
                embed_dim=DIM,
                redis_url="redis://localhost:1/0",
                cache_ttl=60,
                top_k=3,
                min_score=0.3,
            )
            svc = RetrievalService(
                embedder=_FakeEmbedder(),
                _disable_cache=True,
            )
        return svc

    @pytest.mark.asyncio
    async def test_retrieve_empty(self, service):
        """No rows returned from DB → empty result list."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_ctx

        with patch("src.rag.service.retrieval_service.get_session_factory", return_value=mock_factory):
            hits = await service.retrieve(tenant_id=TENANT, query="test")

        assert hits == []

    @pytest.mark.asyncio
    async def test_retrieve_with_rows(self, service):
        """Mocked DB rows are mapped into RetrievalHit objects."""
        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        fake_row = {
            "chunk_id": chunk_id,
            "document_id": doc_id,
            "title": "My Doc",
            "content": "chunk content here",
            "score": 0.87,
            "metadata_json": {"page_number": 2},
        }

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [fake_row]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_ctx

        with patch("src.rag.service.retrieval_service.get_session_factory", return_value=mock_factory):
            hits = await service.retrieve(tenant_id=TENANT, query="tell me about X")

        assert len(hits) == 1
        h = hits[0]
        assert h.chunk_id == str(chunk_id)
        assert h.document_id == str(doc_id)
        assert h.title == "My Doc"
        assert h.content == "chunk content here"
        assert h.score == 0.87
        assert h.metadata_json == {"page_number": 2}

    @pytest.mark.asyncio
    async def test_retrieve_respects_doc_ids(self, service):
        """When doc_ids is provided the SQL includes the ANY filter."""
        doc_id = str(uuid.uuid4())

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_ctx

        with patch("src.rag.service.retrieval_service.get_session_factory", return_value=mock_factory):
            await service.retrieve(
                tenant_id=TENANT, query="q", doc_ids=[doc_id],
            )

        # Verify execute was called with params including doc_ids
        call_args = mock_session.execute.call_args
        params = call_args[0][1]  # second positional arg = params dict
        assert "doc_ids" in params


class TestRetrievalServiceCacheIntegration:
    """Verify cache-hit path with mocked RedisCache."""

    @pytest.mark.asyncio
    async def test_cache_hit_skips_db(self):
        from src.rag.service.retrieval_service import RetrievalService

        cached_rows = [
            {
                "chunk_id": "c1",
                "document_id": "d1",
                "title": "Cached Doc",
                "content": "from cache",
                "score": 0.95,
                "metadata_json": {},
            }
        ]

        mock_cache = AsyncMock()
        mock_cache.get_retrieval = AsyncMock(return_value=cached_rows)

        with patch("src.rag.service.retrieval_service.get_rag_settings") as mock_cfg:
            mock_cfg.return_value = MagicMock(
                embed_provider="openai",
                embed_model="test",
                embed_dim=DIM,
                redis_url="",
                cache_ttl=60,
                top_k=3,
                min_score=0.3,
            )
            svc = RetrievalService(
                embedder=_FakeEmbedder(),
                cache=mock_cache,
            )

        hits = await svc.retrieve(tenant_id=TENANT, query="cached query")
        assert len(hits) == 1
        assert hits[0].content == "from cache"
        assert hits[0].title == "Cached Doc"
        # DB should NOT be touched
        mock_cache.get_retrieval.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_cache_miss_stores_result(self):
        from src.rag.service.retrieval_service import RetrievalService

        mock_cache = AsyncMock()
        mock_cache.get_retrieval = AsyncMock(return_value=None)
        mock_cache.set_retrieval = AsyncMock()

        doc_id = uuid.uuid4()
        chunk_id = uuid.uuid4()
        fake_row = {
            "chunk_id": chunk_id,
            "document_id": doc_id,
            "title": "Fresh",
            "content": "new result",
            "score": 0.8,
            "metadata_json": {},
        }

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.mappings.return_value.all.return_value = [fake_row]
        mock_session.execute = AsyncMock(return_value=mock_result)

        mock_factory = MagicMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__ = AsyncMock(return_value=mock_session)
        mock_ctx.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value = mock_ctx

        with patch("src.rag.service.retrieval_service.get_rag_settings") as mock_cfg:
            mock_cfg.return_value = MagicMock(
                embed_provider="openai",
                embed_model="test",
                embed_dim=DIM,
                redis_url="",
                cache_ttl=60,
                top_k=3,
                min_score=0.3,
            )
            svc = RetrievalService(
                embedder=_FakeEmbedder(),
                cache=mock_cache,
            )

        with patch("src.rag.service.retrieval_service.get_session_factory", return_value=mock_factory):
            hits = await svc.retrieve(tenant_id=TENANT, query="new query")

        assert len(hits) == 1
        mock_cache.set_retrieval.assert_awaited_once()
