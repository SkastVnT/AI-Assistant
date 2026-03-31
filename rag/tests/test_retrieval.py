"""Tests for the baseline retrieval service.

Covers:
- SearchResult with citation metadata
- SearchFilters with source_ids
- RetrievalService: embed → search → trace
- /query/retrieve endpoint (e2e via TestClient)
- Edge cases: empty results, score threshold filtering
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.core.models import RetrievalTrace
from libs.retrieval.search import SearchFilters, SearchResult
from libs.retrieval.service import (
    RetrievalRequest,
    RetrievalResponse,
    RetrievedChunk,
    _to_retrieved_chunk,
    retrieve,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

TENANT_ID = uuid.uuid4()
USER_ID = uuid.uuid4()
DOC_ID = uuid.uuid4()
VER_ID = uuid.uuid4()
CHUNK_ID_1 = uuid.uuid4()
CHUNK_ID_2 = uuid.uuid4()


def _make_search_result(
    *,
    chunk_id: uuid.UUID | None = None,
    score: float = 0.85,
    content: str = "Test chunk content",
    document_title: str = "My Document",
    version_number: int = 1,
    page_number: int | None = 3,
    heading_path: str | None = "Chapter 1 > Section 1.2",
    sensitivity_level: str = "internal",
) -> SearchResult:
    return SearchResult(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=DOC_ID,
        version_id=VER_ID,
        content=content,
        score=score,
        metadata={"page_number": page_number, "heading_path": heading_path},
        filename="report.pdf",
        chunk_index=0,
        sensitivity_level=sensitivity_level,
        language="en",
        tags=["finance"],
        document_title=document_title,
        version_number=version_number,
        page_number=page_number,
        heading_path=heading_path,
    )


class FakeEmbeddingProvider:
    """In-memory embedding provider for testing."""

    def __init__(self, dimensions: int = 8):
        self._dim = dimensions
        self.model = "test-embed-model"

    @property
    def dimensions(self) -> int:
        return self._dim

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[0.1] * self._dim for _ in texts]


# ====================================================================
# SearchResult citation fields
# ====================================================================


class TestSearchResultCitations:
    def test_search_result_has_citation_fields(self):
        r = _make_search_result()
        assert r.document_title == "My Document"
        assert r.version_number == 1
        assert r.page_number == 3
        assert r.heading_path == "Chapter 1 > Section 1.2"

    def test_search_result_optional_citation_fields(self):
        r = _make_search_result(page_number=None, heading_path=None)
        assert r.page_number is None
        assert r.heading_path is None

    def test_search_result_defaults(self):
        r = SearchResult(
            chunk_id=uuid.uuid4(),
            document_id=DOC_ID,
            version_id=VER_ID,
            content="x",
            score=0.5,
            metadata={},
            filename="f.txt",
            chunk_index=0,
            sensitivity_level="public",
            language="en",
        )
        assert r.document_title == ""
        assert r.version_number == 0
        assert r.page_number is None
        assert r.heading_path is None


# ====================================================================
# SearchFilters source_ids
# ====================================================================


class TestSearchFiltersSourceIds:
    def test_source_ids_default_none(self):
        f = SearchFilters()
        assert f.source_ids is None

    def test_source_ids_set(self):
        ids = [uuid.uuid4(), uuid.uuid4()]
        f = SearchFilters(source_ids=ids)
        assert f.source_ids == ids


# ====================================================================
# _to_retrieved_chunk conversion
# ====================================================================


class TestToRetrievedChunk:
    def test_converts_all_fields(self):
        sr = _make_search_result(chunk_id=CHUNK_ID_1)
        rc = _to_retrieved_chunk(sr)
        assert isinstance(rc, RetrievedChunk)
        assert rc.chunk_id == CHUNK_ID_1
        assert rc.document_title == "My Document"
        assert rc.version_number == 1
        assert rc.page_number == 3
        assert rc.heading_path == "Chapter 1 > Section 1.2"
        assert rc.score == 0.85
        assert rc.tags == ["finance"]

    def test_preserves_metadata(self):
        sr = _make_search_result()
        rc = _to_retrieved_chunk(sr)
        assert rc.metadata == sr.metadata


# ====================================================================
# RetrievalService.retrieve()
# ====================================================================


class TestRetrieveFunction:
    @pytest.mark.asyncio
    async def test_retrieve_returns_chunks(self):
        provider = FakeEmbeddingProvider()
        search_results = [
            _make_search_result(chunk_id=CHUNK_ID_1, score=0.9),
            _make_search_result(chunk_id=CHUNK_ID_2, score=0.7),
        ]

        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        request = RetrievalRequest(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            query="What is the revenue?",
            top_k=5,
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=search_results,
        ) as mock_search:
            result = await retrieve(db, provider, request)

        assert isinstance(result, RetrievalResponse)
        assert result.total_found == 2
        assert len(result.chunks) == 2
        assert result.chunks[0].chunk_id == CHUNK_ID_1
        assert result.chunks[1].chunk_id == CHUNK_ID_2
        assert result.query == "What is the revenue?"
        assert result.trace_id is not None
        assert result.retrieval_ms >= 0
        # Verify search was called with pre-computed embedding
        mock_search.assert_called_once()

    @pytest.mark.asyncio
    async def test_retrieve_empty_results(self):
        provider = FakeEmbeddingProvider()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        request = RetrievalRequest(
            tenant_id=TENANT_ID,
            user_id=None,
            query="Nonexistent topic",
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await retrieve(db, provider, request)

        assert result.total_found == 0
        assert result.chunks == []

    @pytest.mark.asyncio
    async def test_retrieve_records_trace(self):
        provider = FakeEmbeddingProvider()
        db = AsyncMock()
        added_objects = []
        db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))
        db.flush = AsyncMock()

        request = RetrievalRequest(
            tenant_id=TENANT_ID,
            user_id=USER_ID,
            query="Test query",
            top_k=3,
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[_make_search_result(score=0.8)],
        ):
            await retrieve(db, provider, request)

        # Trace was added to session
        assert len(added_objects) == 1
        trace = added_objects[0]
        assert isinstance(trace, RetrievalTrace)
        assert trace.tenant_id == TENANT_ID
        assert trace.user_id == USER_ID
        assert trace.query_text == "Test query"
        assert trace.retrieval_strategy == "vector_cosine"
        assert trace.top_k == 3
        assert len(trace.retrieved_chunks) == 1
        assert trace.retrieved_chunks[0]["rank"] == 1

    @pytest.mark.asyncio
    async def test_retrieve_passes_filters(self):
        provider = FakeEmbeddingProvider()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        source_ids = [uuid.uuid4()]
        filters = SearchFilters(
            sensitivity_level="public",
            source_ids=source_ids,
        )
        request = RetrievalRequest(
            tenant_id=TENANT_ID,
            user_id=None,
            query="Filter test",
            top_k=10,
            score_threshold=0.5,
            filters=filters,
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_search:
            await retrieve(db, provider, request)

        _, kwargs = mock_search.call_args
        assert kwargs["tenant_id"] == TENANT_ID
        assert kwargs["top_k"] == 10
        assert kwargs["score_threshold"] == 0.5
        assert kwargs["filters"] == filters

    @pytest.mark.asyncio
    async def test_retrieve_citation_metadata_propagated(self):
        provider = FakeEmbeddingProvider()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        sr = _make_search_result(
            document_title="Annual Report",
            version_number=3,
            page_number=42,
            heading_path="Financials > Q4",
        )

        request = RetrievalRequest(
            tenant_id=TENANT_ID,
            user_id=None,
            query="Q4 financials",
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[sr],
        ):
            result = await retrieve(db, provider, request)

        chunk = result.chunks[0]
        assert chunk.document_title == "Annual Report"
        assert chunk.version_number == 3
        assert chunk.page_number == 42
        assert chunk.heading_path == "Financials > Q4"

    @pytest.mark.asyncio
    async def test_retrieve_embedding_model_returned(self):
        provider = FakeEmbeddingProvider()
        db = AsyncMock()
        db.add = MagicMock()
        db.flush = AsyncMock()

        request = RetrievalRequest(
            tenant_id=TENANT_ID, user_id=None, query="x"
        )

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[],
        ):
            result = await retrieve(db, provider, request)

        assert result.embedding_model == "test-embed-model"


# ====================================================================
# Schemas (Pydantic)
# ====================================================================


class TestRetrievalSchemas:
    def test_retrieve_request_defaults(self):
        from libs.core.schemas import RetrieveRequest

        r = RetrieveRequest(query="hello")
        assert r.top_k == 5
        assert r.score_threshold == 0.0
        assert r.filters is None

    def test_retrieve_request_validation(self):
        from libs.core.schemas import RetrieveRequest

        with pytest.raises(Exception):  # noqa: B017
            RetrieveRequest(query="")  # min_length=1

    def test_retrieve_request_with_filters(self):
        from libs.core.schemas import RetrieveFilters, RetrieveRequest

        doc_id = uuid.uuid4()
        r = RetrieveRequest(
            query="test",
            top_k=10,
            score_threshold=0.5,
            filters=RetrieveFilters(
                sensitivity_levels=["public"],
                source_ids=[doc_id],
            ),
        )
        assert r.filters.source_ids == [doc_id]
        assert r.filters.sensitivity_levels == ["public"]

    def test_retrieved_chunk_response(self):
        from libs.core.schemas import RetrievedChunkResponse

        c = RetrievedChunkResponse(
            chunk_id=CHUNK_ID_1,
            document_id=DOC_ID,
            version_id=VER_ID,
            content="text",
            score=0.9,
            chunk_index=0,
            document_title="Title",
            filename="f.pdf",
            version_number=2,
            page_number=5,
            heading_path="H1 > H2",
            sensitivity_level="internal",
            language="en",
        )
        assert c.document_title == "Title"
        assert c.page_number == 5

    def test_retrieve_response(self):
        from libs.core.schemas import RetrievedChunkResponse, RetrieveResponse

        trace_id = uuid.uuid4()
        r = RetrieveResponse(
            query="q",
            chunks=[
                RetrievedChunkResponse(
                    chunk_id=CHUNK_ID_1,
                    document_id=DOC_ID,
                    version_id=VER_ID,
                    content="text",
                    score=0.9,
                    chunk_index=0,
                    document_title="T",
                    filename="f.pdf",
                    version_number=1,
                    sensitivity_level="public",
                    language="en",
                )
            ],
            total_found=1,
            trace_id=trace_id,
            retrieval_ms=42,
        )
        assert r.total_found == 1
        assert r.trace_id == trace_id


# ====================================================================
# End-to-end: /query/retrieve via TestClient
# ====================================================================


def _can_import_app() -> bool:
    """Check if we can import the FastAPI app (needs asyncpg, minio, etc.)."""
    try:
        import apps.api.main  # noqa: F401

        return True
    except ImportError:
        return False


@pytest.mark.skipif(not _can_import_app(), reason="app deps not installed")
class TestRetrieveEndpoint:
    """Integration test using FastAPI TestClient with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_retrieve_endpoint_e2e(self):
        from unittest.mock import patch as _patch

        from httpx import ASGITransport, AsyncClient

        from apps.api.main import create_app

        app = create_app()

        fake_provider = FakeEmbeddingProvider()
        search_results = [
            _make_search_result(chunk_id=CHUNK_ID_1, score=0.92),
        ]

        # Override FastAPI dependencies
        async def fake_db():
            db = AsyncMock()
            db.add = MagicMock()
            db.flush = AsyncMock()
            db.commit = AsyncMock()
            yield db

        app.dependency_overrides = {
            __import__(
                "apps.api.dependencies", fromlist=["db_session"]
            ).db_session: fake_db,
            __import__(
                "apps.api.dependencies", fromlist=["embedding_provider"]
            ).embedding_provider: lambda: fake_provider,
        }

        with _patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=search_results,
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/query/retrieve",
                    json={
                        "query": "What is revenue?",
                        "top_k": 5,
                        "score_threshold": 0.3,
                    },
                    headers={"x-tenant-id": str(TENANT_ID)},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "What is revenue?"
        assert data["total_found"] == 1
        assert len(data["chunks"]) == 1

        chunk = data["chunks"][0]
        assert chunk["chunk_id"] == str(CHUNK_ID_1)
        assert chunk["document_title"] == "My Document"
        assert chunk["version_number"] == 1
        assert chunk["page_number"] == 3
        assert chunk["heading_path"] == "Chapter 1 > Section 1.2"
        assert chunk["score"] == pytest.approx(0.92)
        assert "trace_id" in data
        assert data["retrieval_ms"] >= 0

    @pytest.mark.asyncio
    async def test_retrieve_endpoint_with_filters(self):
        from httpx import ASGITransport, AsyncClient

        from apps.api.main import create_app

        app = create_app()
        fake_provider = FakeEmbeddingProvider()

        async def fake_db():
            db = AsyncMock()
            db.add = MagicMock()
            db.flush = AsyncMock()
            db.commit = AsyncMock()
            yield db

        app.dependency_overrides = {
            __import__(
                "apps.api.dependencies", fromlist=["db_session"]
            ).db_session: fake_db,
            __import__(
                "apps.api.dependencies", fromlist=["embedding_provider"]
            ).embedding_provider: lambda: fake_provider,
        }

        with patch(
            "libs.retrieval.service.vector_search_from_embedding",
            new_callable=AsyncMock,
            return_value=[],
        ):
            transport = ASGITransport(app=app)
            async with AsyncClient(
                transport=transport, base_url="http://test"
            ) as client:
                resp = await client.post(
                    "/api/v1/query/retrieve",
                    json={
                        "query": "Any topic",
                        "top_k": 3,
                        "filters": {
                            "sensitivity_levels": ["public"],
                            "source_ids": [str(DOC_ID)],
                        },
                    },
                    headers={"x-tenant-id": str(TENANT_ID)},
                )

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_found"] == 0
        assert data["chunks"] == []

    @pytest.mark.asyncio
    async def test_retrieve_endpoint_missing_tenant_header(self):
        from httpx import ASGITransport, AsyncClient

        from apps.api.main import create_app

        app = create_app()

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport, base_url="http://test"
        ) as client:
            resp = await client.post(
                "/api/v1/query/retrieve",
                json={"query": "hello"},
            )

        assert resp.status_code == 422  # missing required header
