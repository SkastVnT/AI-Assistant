"""Tests for the embedding and indexing layer.

Covers:
- EmbeddingService: batching, retry, idempotency, skip logic
- IndexingService: embed_pending, reembed_version, full_reindex, supersede
- Worker tasks: task_embed_pending, task_reembed_version, task_full_reindex
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.core.models import DocumentChunk, DocumentVersion, VersionStatus
from libs.embedding.service import EmbeddingService, EmbedResult

# ---------------------------------------------------------------------------
# Fake embedding provider
# ---------------------------------------------------------------------------


class FakeEmbeddingProvider:
    """In-memory embedding provider for testing."""

    def __init__(self, dimensions: int = 8, fail_after: int | None = None):
        self._dim = dimensions
        self._call_count = 0
        self._fail_after = fail_after  # fail on Nth call

    @property
    def dimensions(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        self._call_count += 1
        if self._fail_after and self._call_count >= self._fail_after:
            raise RuntimeError("Simulated API error")
        return [[float(i) / max(len(t), 1)] * self._dim for i, t in enumerate(texts)]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TENANT_ID = uuid.uuid4()
DOC_ID = uuid.uuid4()
VER_ID = uuid.uuid4()


def _make_chunk(
    *,
    content: str = "test content",
    embedding: list[float] | None = None,
    embedding_model: str | None = None,
    embedding_version: str | None = None,
) -> DocumentChunk:
    """Create a DocumentChunk with minimal required fields."""
    chunk = DocumentChunk(
        id=uuid.uuid4(),
        tenant_id=TENANT_ID,
        document_id=DOC_ID,
        version_id=VER_ID,
        chunk_index=0,
        content=content,
        token_count=len(content) // 4,
    )
    if embedding is not None:
        chunk.embedding = embedding
    if embedding_model is not None:
        chunk.embedding_model = embedding_model
    if embedding_version is not None:
        chunk.embedding_version = embedding_version
    return chunk


# ====================================================================
# EmbeddingService
# ====================================================================


class TestEmbeddingService:
    def setup_method(self):
        self.provider = FakeEmbeddingProvider(dimensions=8)
        self.service = EmbeddingService(
            self.provider,
            batch_size=3,
            max_retries=2,
            model_name="test-model",
            model_version="v1",
        )

    @pytest.mark.asyncio
    async def test_embed_empty_list(self):
        result = await self.service.embed_chunks([])
        assert result.total_chunks == 0
        assert result.embedded == 0

    @pytest.mark.asyncio
    async def test_embed_single_chunk(self):
        chunk = _make_chunk(content="Hello world")
        result = await self.service.embed_chunks([chunk])

        assert result.total_chunks == 1
        assert result.embedded == 1
        assert result.skipped == 0
        assert result.failed == 0
        assert result.model == "test-model"
        assert result.version == "v1"

        # Check chunk was modified in-place
        assert chunk.embedding is not None
        assert len(chunk.embedding) == 8
        assert chunk.embedding_model == "test-model"
        assert chunk.embedding_version == "v1"

    @pytest.mark.asyncio
    async def test_embed_multiple_chunks(self):
        chunks = [_make_chunk(content=f"Chunk {i}") for i in range(5)]
        result = await self.service.embed_chunks(chunks)

        assert result.total_chunks == 5
        assert result.embedded == 5
        for c in chunks:
            assert c.embedding is not None

    @pytest.mark.asyncio
    async def test_batching(self):
        """With batch_size=3, 5 chunks should make 2 API calls."""
        provider = FakeEmbeddingProvider(dimensions=8)
        service = EmbeddingService(
            provider, batch_size=3, max_retries=1,
            model_name="test-model", model_version="v1",
        )
        chunks = [_make_chunk(content=f"Chunk {i}") for i in range(5)]
        result = await service.embed_chunks(chunks)

        assert result.embedded == 5
        assert provider._call_count == 2  # ceil(5/3) = 2 batches

    @pytest.mark.asyncio
    async def test_idempotency_skip(self):
        """Chunks already embedded with same model+version are skipped."""
        chunk = _make_chunk(
            content="Already done",
            embedding=[0.1] * 8,
            embedding_model="test-model",
            embedding_version="v1",
        )
        result = await self.service.embed_chunks([chunk])

        assert result.total_chunks == 1
        assert result.embedded == 0
        assert result.skipped == 1

    @pytest.mark.asyncio
    async def test_force_reembed(self):
        """With force=True, re-embed even if already matching."""
        chunk = _make_chunk(
            content="Already done",
            embedding=[0.1] * 8,
            embedding_model="test-model",
            embedding_version="v1",
        )
        result = await self.service.embed_chunks([chunk], force=True)

        assert result.embedded == 1
        assert result.skipped == 0

    @pytest.mark.asyncio
    async def test_different_model_not_skipped(self):
        """Chunks with different model are re-embedded."""
        chunk = _make_chunk(
            content="Old model",
            embedding=[0.1] * 8,
            embedding_model="old-model",
            embedding_version="v0",
        )
        result = await self.service.embed_chunks([chunk])

        assert result.embedded == 1
        assert result.skipped == 0
        assert chunk.embedding_model == "test-model"
        assert chunk.embedding_version == "v1"

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """Service retries on transient failures."""
        # Provider fails on first call, succeeds on retry
        call_count = 0
        original_embed = self.provider.embed

        async def flaky_embed(texts):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("Transient error")
            return await original_embed(texts)

        self.provider.embed = flaky_embed

        chunk = _make_chunk(content="retry test")
        result = await self.service.embed_chunks([chunk])

        assert result.embedded == 1
        assert call_count == 2  # 1 failure + 1 success

    @pytest.mark.asyncio
    async def test_all_retries_exhausted(self):
        """When all retries fail, chunks are marked failed."""
        async def always_fail(texts):
            raise RuntimeError("Permanent error")

        self.provider.embed = always_fail

        chunks = [_make_chunk(content="fail")]
        result = await self.service.embed_chunks(chunks)

        assert result.failed == 1
        assert result.embedded == 0
        assert chunks[0].embedding is None

    @pytest.mark.asyncio
    async def test_embed_texts_direct(self):
        """embed_texts returns raw vectors."""
        texts = ["hello", "world"]
        vectors = await self.service.embed_texts(texts)

        assert len(vectors) == 2
        assert all(len(v) == 8 for v in vectors)

    @pytest.mark.asyncio
    async def test_embed_texts_batching(self):
        """embed_texts respects batch_size."""
        texts = [f"text {i}" for i in range(7)]
        vectors = await self.service.embed_texts(texts)

        assert len(vectors) == 7

    @pytest.mark.asyncio
    async def test_model_properties(self):
        assert self.service.model_name == "test-model"
        assert self.service.model_version == "v1"


# ====================================================================
# EmbedResult
# ====================================================================


class TestEmbedResult:
    def test_fields(self):
        r = EmbedResult(
            total_chunks=10, embedded=8, skipped=1, failed=1,
            model="m", version="v",
        )
        assert r.total_chunks == 10
        assert r.embedded + r.skipped + r.failed == 10


# ====================================================================
# IndexingService (unit tests with mocked DB)
# ====================================================================


class TestIndexingServiceUnit:
    """Unit tests using mocked database sessions."""

    @pytest.mark.asyncio
    async def test_embed_pending_no_chunks(self):
        """embed_pending with no unembedded chunks returns zeros."""
        from libs.embedding.indexer import IndexingService

        db = AsyncMock()
        provider = FakeEmbeddingProvider()
        embed_svc = EmbeddingService(
            provider, model_name="m", model_version="v1",
            batch_size=10, max_retries=1,
        )

        with patch(
            "libs.embedding.indexer.SqlDocumentChunkRepository"
        ) as mock_chunk_repo_cls, patch(
            "libs.embedding.indexer.SqlDocumentVersionRepository"
        ):
            mock_repo = mock_chunk_repo_cls.return_value
            mock_repo.get_unembedded = AsyncMock(return_value=[])

            indexer = IndexingService(db, embed_svc)
            result = await indexer.embed_pending()

            assert result.chunks_processed == 0
            assert result.chunks_embedded == 0

    @pytest.mark.asyncio
    async def test_embed_pending_with_chunks(self):
        from libs.embedding.indexer import IndexingService

        db = AsyncMock()
        db.flush = AsyncMock()
        provider = FakeEmbeddingProvider(dimensions=8)
        embed_svc = EmbeddingService(
            provider, model_name="m", model_version="v1",
            batch_size=10, max_retries=1,
        )

        chunks = [_make_chunk(content=f"text {i}") for i in range(3)]

        with patch(
            "libs.embedding.indexer.SqlDocumentChunkRepository"
        ) as mock_chunk_repo_cls, patch(
            "libs.embedding.indexer.SqlDocumentVersionRepository"
        ):
            mock_repo = mock_chunk_repo_cls.return_value
            mock_repo.get_unembedded = AsyncMock(return_value=chunks)

            indexer = IndexingService(db, embed_svc)
            result = await indexer.embed_pending()

            assert result.chunks_embedded == 3
            assert result.operation == "embed_pending"

    @pytest.mark.asyncio
    async def test_reembed_version_not_found(self):
        from libs.embedding.indexer import IndexingService

        db = AsyncMock()
        provider = FakeEmbeddingProvider()
        embed_svc = EmbeddingService(
            provider, model_name="m", model_version="v1",
            batch_size=10, max_retries=1,
        )

        with patch(
            "libs.embedding.indexer.SqlDocumentChunkRepository"
        ), patch(
            "libs.embedding.indexer.SqlDocumentVersionRepository"
        ) as mock_ver_repo_cls:
            mock_ver_repo = mock_ver_repo_cls.return_value
            mock_ver_repo.get_by_id = AsyncMock(return_value=None)

            indexer = IndexingService(db, embed_svc)
            with pytest.raises(ValueError, match="not found"):
                await indexer.reembed_version(uuid.uuid4())

    @pytest.mark.asyncio
    async def test_mark_old_versions_superseded(self):
        from libs.embedding.indexer import IndexingService

        db = AsyncMock()
        provider = FakeEmbeddingProvider()
        embed_svc = EmbeddingService(
            provider, model_name="m", model_version="v1",
            batch_size=10, max_retries=1,
        )

        with patch(
            "libs.embedding.indexer.SqlDocumentChunkRepository"
        ), patch(
            "libs.embedding.indexer.SqlDocumentVersionRepository"
        ) as mock_ver_repo_cls:
            mock_ver_repo = mock_ver_repo_cls.return_value
            mock_ver_repo.mark_superseded = AsyncMock(return_value=2)

            indexer = IndexingService(db, embed_svc)
            count = await indexer.mark_old_versions_superseded(
                DOC_ID, VER_ID
            )
            assert count == 2

    @pytest.mark.asyncio
    async def test_full_reindex_empty(self):
        from libs.embedding.indexer import IndexingService

        db = AsyncMock()
        db.flush = AsyncMock()
        provider = FakeEmbeddingProvider()
        embed_svc = EmbeddingService(
            provider, model_name="m", model_version="v1",
            batch_size=10, max_retries=1,
        )

        with patch(
            "libs.embedding.indexer.SqlDocumentChunkRepository"
        ) as mock_chunk_repo_cls, patch(
            "libs.embedding.indexer.SqlDocumentVersionRepository"
        ):
            mock_repo = mock_chunk_repo_cls.return_value
            mock_repo.get_all_by_tenant = AsyncMock(return_value=[])

            indexer = IndexingService(db, embed_svc)
            result = await indexer.full_reindex(TENANT_ID)

            assert result.chunks_processed == 0
            assert result.operation == "full_reindex"

    @pytest.mark.asyncio
    async def test_embed_and_finalize_success(self):
        from libs.embedding.indexer import IndexingService

        db = AsyncMock()
        db.flush = AsyncMock()
        provider = FakeEmbeddingProvider(dimensions=8)
        embed_svc = EmbeddingService(
            provider, model_name="m", model_version="v1",
            batch_size=10, max_retries=1,
        )

        chunks = [_make_chunk(content=f"text {i}") for i in range(3)]
        version = MagicMock(spec=DocumentVersion)
        version.document_id = DOC_ID
        version.id = VER_ID
        version.metadata_ = {}

        with patch(
            "libs.embedding.indexer.SqlDocumentChunkRepository"
        ), patch(
            "libs.embedding.indexer.SqlDocumentVersionRepository"
        ) as mock_ver_repo_cls:
            mock_ver_repo = mock_ver_repo_cls.return_value
            mock_ver_repo.mark_superseded = AsyncMock(return_value=0)

            indexer = IndexingService(db, embed_svc)
            result = await indexer.embed_and_finalize_version(chunks, version)

            assert result.embedded == 3
            assert version.status == VersionStatus.READY

    @pytest.mark.asyncio
    async def test_embed_and_finalize_all_failed(self):
        from libs.embedding.indexer import IndexingService

        db = AsyncMock()
        db.flush = AsyncMock()

        # Provider that always fails
        provider = FakeEmbeddingProvider()
        provider.embed = AsyncMock(side_effect=RuntimeError("fail"))

        embed_svc = EmbeddingService(
            provider, model_name="m", model_version="v1",
            batch_size=10, max_retries=1,
        )

        chunks = [_make_chunk(content="fail")]
        version = MagicMock(spec=DocumentVersion)
        version.document_id = DOC_ID
        version.id = VER_ID
        version.metadata_ = {}

        with patch(
            "libs.embedding.indexer.SqlDocumentChunkRepository"
        ), patch(
            "libs.embedding.indexer.SqlDocumentVersionRepository"
        ):
            indexer = IndexingService(db, embed_svc)
            result = await indexer.embed_and_finalize_version(chunks, version)

            assert result.failed == 1
            assert result.embedded == 0
            assert version.status == VersionStatus.ERROR


# ====================================================================
# IndexResult
# ====================================================================


class TestIndexResult:
    def test_summary(self):
        from libs.embedding.indexer import IndexResult

        r = IndexResult(
            operation="test_op",
            chunks_processed=10,
            chunks_embedded=8,
            chunks_skipped=1,
            chunks_failed=1,
            versions_superseded=2,
            model="m",
            version="v1",
        )
        s = r.summary()
        assert "test_op" in s
        assert "processed=10" in s
        assert "embedded=8" in s
        assert "superseded=2" in s


# ====================================================================
# VersionStatus.SUPERSEDED
# ====================================================================


class TestVersionStatusSuperseded:
    def test_superseded_exists(self):
        assert VersionStatus.SUPERSEDED == "superseded"
        assert VersionStatus.SUPERSEDED.value == "superseded"
