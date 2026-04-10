"""
Tests for the RAG FastAPI router endpoints.

Run from services/chatbot/:
    python -m pytest tests/test_rag_router.py -v
"""
from __future__ import annotations

import uuid
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from fastapi_app.routers import rag


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def rag_app():
    """Minimal FastAPI app with only the RAG router mounted."""
    _app = FastAPI()
    _app.add_middleware(SessionMiddleware, secret_key="test-secret")
    _app.include_router(rag.router, prefix="/api/rag")
    return _app


@pytest.fixture
def client(rag_app):
    return TestClient(rag_app)


# ---------------------------------------------------------------------------
# GET /api/rag/health
# ---------------------------------------------------------------------------

class TestHealthEndpoint:
    def test_health_rag_disabled(self, client):
        with patch.object(rag, "RAG_ENABLED", False):
            resp = client.get("/api/rag/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["rag_enabled"] is False
        assert body["database"] == "unavailable"
        assert body["redis"] == "unavailable"
        assert body["storage"] == "unavailable"

    def test_health_returns_all_fields(self, client):
        with patch.object(rag, "RAG_ENABLED", False):
            resp = client.get("/api/rag/health")
        body = resp.json()
        for key in ("rag_enabled", "database", "redis", "storage"):
            assert key in body


# ---------------------------------------------------------------------------
# POST /api/rag/ingest
# ---------------------------------------------------------------------------

class TestIngestEndpoint:
    def test_ingest_rag_disabled(self, client):
        with patch.object(rag, "RAG_ENABLED", False):
            resp = client.post(
                "/api/rag/ingest",
                files={"file": ("test.txt", b"hello world", "text/plain")},
            )
        assert resp.status_code == 503

    def test_ingest_empty_file(self, client):
        with patch.object(rag, "RAG_ENABLED", True):
            resp = client.post(
                "/api/rag/ingest",
                files={"file": ("test.txt", b"", "text/plain")},
            )
        assert resp.status_code == 400
        assert "empty" in resp.json()["detail"].lower()

    def test_ingest_success(self, client):
        fake_result = MagicMock()
        fake_result.document_id = uuid.uuid4()
        fake_result.num_chunks = 3
        fake_result.object_path = "tenant/doc/test.txt"

        mock_svc = MagicMock()
        mock_svc.ingest = AsyncMock(return_value=fake_result)

        with patch.object(rag, "RAG_ENABLED", True), \
             patch("src.rag.service.IngestService", return_value=mock_svc):
            resp = client.post(
                "/api/rag/ingest",
                files={"file": ("report.pdf", b"%PDF-fake", "application/pdf")},
                data={"title": "My Report", "source_uri": "https://example.com"},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["document_id"] == str(fake_result.document_id)
        assert body["num_chunks"] == 3
        assert body["object_path"] == "tenant/doc/test.txt"

        # Verify tenant isolation: ingest was called with a tenant_id
        call_kwargs = mock_svc.ingest.call_args.kwargs
        assert "tenant_id" in call_kwargs
        assert call_kwargs["tenant_id"]  # non-empty


# ---------------------------------------------------------------------------
# POST /api/rag/search
# ---------------------------------------------------------------------------

class TestSearchEndpoint:
    def test_search_rag_disabled(self, client):
        with patch.object(rag, "RAG_ENABLED", False):
            resp = client.post(
                "/api/rag/search",
                json={"query": "test"},
            )
        assert resp.status_code == 503

    def test_search_missing_query(self, client):
        with patch.object(rag, "RAG_ENABLED", True):
            resp = client.post("/api/rag/search", json={})
        assert resp.status_code == 422  # validation error

    def test_search_empty_query(self, client):
        with patch.object(rag, "RAG_ENABLED", True):
            resp = client.post("/api/rag/search", json={"query": ""})
        assert resp.status_code == 422  # min_length=1

    def test_search_success(self, client):
        from src.rag.service.retrieval_service import RetrievalHit

        fake_hits = [
            RetrievalHit(
                chunk_id="c1",
                document_id="d1",
                title="My Doc",
                content="relevant content",
                score=0.91,
                metadata_json={"page_number": 2},
            ),
        ]

        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=fake_hits)

        with patch.object(rag, "RAG_ENABLED", True), \
             patch("src.rag.service.RetrievalService", return_value=mock_svc):
            resp = client.post(
                "/api/rag/search",
                json={"query": "tell me about architecture", "top_k": 3},
            )

        assert resp.status_code == 200
        body = resp.json()
        assert body["query"] == "tell me about architecture"
        assert len(body["results"]) == 1

        hit = body["results"][0]
        assert hit["chunk_id"] == "c1"
        assert hit["document_id"] == "d1"
        assert hit["title"] == "My Doc"
        assert hit["content"] == "relevant content"
        assert hit["score"] == 0.91
        assert hit["metadata_json"] == {"page_number": 2}

        # Verify tenant is set
        assert body["tenant_id"]  # non-empty

    def test_search_with_doc_ids(self, client):
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=[])

        with patch.object(rag, "RAG_ENABLED", True), \
             patch("src.rag.service.RetrievalService", return_value=mock_svc):
            resp = client.post(
                "/api/rag/search",
                json={"query": "test", "doc_ids": ["doc-1", "doc-2"]},
            )

        assert resp.status_code == 200
        call_kwargs = mock_svc.retrieve.call_args.kwargs
        assert call_kwargs["doc_ids"] == ["doc-1", "doc-2"]


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------

class TestTenantIsolation:
    def test_different_sessions_get_different_tenants(self, rag_app):
        """Two separate clients should get distinct tenant IDs."""
        mock_svc = MagicMock()
        mock_svc.retrieve = AsyncMock(return_value=[])

        tenant_ids = []

        original_retrieve = mock_svc.retrieve

        async def capture_tenant(**kwargs):
            tenant_ids.append(kwargs["tenant_id"])
            return []

        mock_svc.retrieve = AsyncMock(side_effect=capture_tenant)

        with patch.object(rag, "RAG_ENABLED", True), \
             patch("src.rag.service.RetrievalService", return_value=mock_svc):

            c1 = TestClient(rag_app)
            c2 = TestClient(rag_app)

            c1.post("/api/rag/search", json={"query": "q1"})
            c2.post("/api/rag/search", json={"query": "q2"})

        assert len(tenant_ids) == 2
        assert tenant_ids[0] != tenant_ids[1]
