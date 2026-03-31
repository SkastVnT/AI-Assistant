"""
End-to-end fixtures for RAG integration tests.

Provides a self-contained FastAPI ``TestClient`` with **all** heavy
dependencies mocked (DB, Redis, MinIO, embedding API, chatbot LLM) while
exercising the real HTTP → router → helper → service call chain.

Import these fixtures in any ``test_rag_e2e*.py`` module.

Usage::

    # conftest.py or direct import
    from tests.e2e_rag_fixtures import *   # noqa: F401,F403

Run from ``services/chatbot/``::

    python -m pytest tests/test_rag_e2e.py -v
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware


# ═══════════════════════════════════════════════════════════════════════
# In-memory stores shared across a single test session
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class FakeDocument:
    doc_id: str
    tenant_id: str
    title: str
    chunks: list[dict]          # [{text, embedding, chunk_index, metadata}]
    object_path: str = ""


class InMemoryRAGStore:
    """In-memory stand-in for pgvector + MinIO, used by the fake services."""

    def __init__(self) -> None:
        self.documents: dict[str, FakeDocument] = {}     # doc_id → doc
        self.files: dict[str, bytes] = {}                # object_path → bytes
        self._embed_dim = 8                               # tiny vectors for tests

    def reset(self) -> None:
        self.documents.clear()
        self.files.clear()

    # ── Embedding stub ────────────────────────────────────────────────
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Deterministic embeddings based on text hash (repeatable)."""
        vecs = []
        for t in texts:
            h = hash(t) & 0xFFFF_FFFF
            vec = [(h >> (i * 4) & 0xF) / 15.0 for i in range(self._embed_dim)]
            vecs.append(vec)
        return vecs

    def embed_query(self, text: str) -> list[float]:
        return self.embed_texts([text])[0]

    # ── Cosine similarity ─────────────────────────────────────────────
    @staticmethod
    def _cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = sum(x * x for x in a) ** 0.5
        nb = sum(x * x for x in b) ** 0.5
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    # ── Search ────────────────────────────────────────────────────────
    def search(
        self,
        tenant_id: str,
        query_vec: list[float],
        top_k: int = 5,
        doc_ids: list[str] | None = None,
        min_score: float = 0.0,
    ) -> list[dict]:
        results = []
        for doc in self.documents.values():
            if doc.tenant_id != tenant_id:
                continue
            if doc_ids and doc.doc_id not in doc_ids:
                continue
            for ch in doc.chunks:
                score = self._cosine(query_vec, ch["embedding"])
                if score >= min_score:
                    results.append({
                        "chunk_id": f"{doc.doc_id}_{ch['chunk_index']}",
                        "document_id": doc.doc_id,
                        "title": doc.title,
                        "content": ch["text"],
                        "score": score,
                        "metadata_json": ch.get("metadata", {}),
                    })
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]


# Global singleton — reset per test
_store = InMemoryRAGStore()


# ═══════════════════════════════════════════════════════════════════════
# Fake IngestService
# ═══════════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class _FakeIngestResult:
    document_id: uuid.UUID
    num_chunks: int
    object_path: str


class FakeIngestService:
    """Replaces the real IngestService (no DB / MinIO / embedding API)."""

    async def ingest(
        self,
        *,
        tenant_id: str,
        file_bytes: bytes,
        filename: str,
        mime_type: str | None = None,
        title: str | None = None,
        source_uri: str | None = None,
        source_type: str = "upload",
    ) -> _FakeIngestResult:
        from src.rag.security.policies import get_rag_policies

        policies = get_rag_policies()
        if len(file_bytes) > policies.max_file_bytes:
            from src.rag.service.ingest_service import IngestError
            raise IngestError(f"File too large: {len(file_bytes)} bytes")

        doc_id = uuid.uuid4()
        obj_path = f"{tenant_id}/{doc_id}/{filename}"

        _store.files[obj_path] = file_bytes

        # Simple sentence-split chunking
        text = file_bytes.decode("utf-8", errors="replace")
        sentences = [s.strip() for s in text.split(".") if s.strip()]
        if not sentences:
            sentences = [text]

        chunks = []
        for i, sent in enumerate(sentences):
            chunks.append({
                "text": sent,
                "embedding": _store.embed_texts([sent])[0],
                "chunk_index": i,
                "metadata": {"page": 1},
            })

        _store.documents[str(doc_id)] = FakeDocument(
            doc_id=str(doc_id),
            tenant_id=tenant_id,
            title=title or filename,
            chunks=chunks,
            object_path=obj_path,
        )

        return _FakeIngestResult(
            document_id=doc_id,
            num_chunks=len(chunks),
            object_path=obj_path,
        )


# ═══════════════════════════════════════════════════════════════════════
# Fake RetrievalService
# ═══════════════════════════════════════════════════════════════════════

class FakeRetrievalService:
    """Replaces the real RetrievalService (no DB / Redis / embedding API)."""

    async def retrieve(
        self,
        *,
        tenant_id: str,
        query: str,
        top_k: int | None = None,
        doc_ids: list[str] | None = None,
        min_score: float | None = None,
    ):
        from src.rag.service.retrieval_service import RetrievalHit

        query_vec = _store.embed_query(query)
        raw = _store.search(
            tenant_id=tenant_id,
            query_vec=query_vec,
            top_k=top_k or 5,
            doc_ids=doc_ids,
            min_score=min_score or 0.0,
        )
        return [RetrievalHit(**r) for r in raw]


# ═══════════════════════════════════════════════════════════════════════
# Fake Chatbot
# ═══════════════════════════════════════════════════════════════════════

class FakeChatbot:
    """Minimal chatbot that echoes the RAG context block back."""

    def chat(self, *, message: str, **kw: Any) -> dict:
        # If RAG context is present, include marker + content in response
        if "[RAG_CONTEXT" in message:
            # Extract the first chunk content for a simple "grounded" reply
            return {
                "response": f"Based on the provided documents: {message[:500]}",
            }
        return {
            "response": "I don't have enough information to answer that question.",
        }

    def chat_stream(self, *, message: str, **kw: Any):
        """Yield a single chunk."""
        resp = self.chat(message=message, **kw)["response"]
        yield resp


# ═══════════════════════════════════════════════════════════════════════
# Pytest fixtures
# ═══════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
def _reset_store():
    """Clear the in-memory store before every test."""
    _store.reset()
    yield
    _store.reset()


@pytest.fixture()
def rag_store() -> InMemoryRAGStore:
    """Expose the in-memory store for direct inspection."""
    return _store


@pytest.fixture()
def e2e_client():
    """FastAPI TestClient with all heavy deps mocked.

    The client has a sticky session cookie, so every request shares the
    same ``tenant_id`` (derived from the Starlette session).
    """
    with (
        patch("src.rag.RAG_ENABLED", True),
        patch("src.rag.config.RAG_ENABLED", True),
        patch("fastapi_app.routers.rag.RAG_ENABLED", True),
        # IngestService → Fake
        patch(
            "fastapi_app.routers.rag.IngestService",
            side_effect=lambda **kw: FakeIngestService(),
            create=True,
        ),
        patch(
            "src.rag.service.IngestService",
            side_effect=lambda **kw: FakeIngestService(),
        ),
        # RetrievalService → Fake
        patch(
            "src.rag.service.RetrievalService",
            side_effect=lambda **kw: FakeRetrievalService(),
        ),
        # Chatbot → Fake (must patch at the import-site in each router)
        patch(
            "fastapi_app.routers.chat.get_chatbot_for_session",
            return_value=FakeChatbot(),
        ),
        patch(
            "fastapi_app.routers.stream.get_chatbot_for_session",
            return_value=FakeChatbot(),
        ),
    ):
        from fastapi_app import create_app

        app = create_app()
        client = TestClient(app, cookies={})
        yield client


@pytest.fixture()
def tenant_a_client():
    """A second client with a DIFFERENT session → different tenant."""
    with (
        patch("src.rag.RAG_ENABLED", True),
        patch("src.rag.config.RAG_ENABLED", True),
        patch("fastapi_app.routers.rag.RAG_ENABLED", True),
        patch(
            "fastapi_app.routers.rag.IngestService",
            side_effect=lambda **kw: FakeIngestService(),
            create=True,
        ),
        patch(
            "src.rag.service.IngestService",
            side_effect=lambda **kw: FakeIngestService(),
        ),
        patch(
            "src.rag.service.RetrievalService",
            side_effect=lambda **kw: FakeRetrievalService(),
        ),
        patch(
            "fastapi_app.routers.chat.get_chatbot_for_session",
            return_value=FakeChatbot(),
        ),
        patch(
            "fastapi_app.routers.stream.get_chatbot_for_session",
            return_value=FakeChatbot(),
        ),
    ):
        from fastapi_app import create_app

        app = create_app()
        client = TestClient(app, cookies={})
        yield client


@pytest.fixture()
def disabled_client():
    """Client where RAG is DISABLED."""
    with (
        patch("src.rag.RAG_ENABLED", False),
        patch("src.rag.config.RAG_ENABLED", False),
        patch("fastapi_app.routers.rag.RAG_ENABLED", False),
        patch(
            "fastapi_app.routers.chat.get_chatbot_for_session",
            return_value=FakeChatbot(),
        ),
        patch(
            "fastapi_app.routers.stream.get_chatbot_for_session",
            return_value=FakeChatbot(),
        ),
    ):
        from fastapi_app import create_app

        app = create_app()
        yield TestClient(app, cookies={})


# ═══════════════════════════════════════════════════════════════════════
# Helper to ingest a sample document via the API
# ═══════════════════════════════════════════════════════════════════════

SAMPLE_DOCUMENT = (
    "Quantum computing uses qubits instead of classical bits. "
    "Qubits can exist in superposition, enabling parallel computation. "
    "Major companies like IBM and Google are investing in quantum hardware. "
    "Quantum error correction is essential for fault-tolerant computing. "
    "Shor's algorithm can factor large numbers exponentially faster."
)

UNRELATED_QUESTION = "What is the recipe for chocolate cake?"


def ingest_sample(client: TestClient, title: str = "Quantum Computing Guide") -> dict:
    """POST a sample .txt file to /api/rag/ingest and return the JSON."""
    resp = client.post(
        "/api/rag/ingest",
        files={"file": ("quantum.txt", SAMPLE_DOCUMENT.encode(), "text/plain")},
        data={"title": title},
    )
    assert resp.status_code == 200, f"Ingest failed: {resp.text}"
    return resp.json()
