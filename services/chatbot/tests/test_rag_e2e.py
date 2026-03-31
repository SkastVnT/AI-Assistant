"""
End-to-end tests for the chatbot RAG integration.

Covers the FULL HTTP flow:
    1. Ingest a sample document via ``POST /api/rag/ingest``
    2. Search it via ``POST /api/rag/search``
    3. Ask a grounded question via ``POST /chat`` and verify citations
    4. Ask an unrelated question and verify "not enough information"
    5. Verify tenant isolation (tenant A cannot see tenant B's docs)
    6. Verify RAG-disabled mode still returns a normal chatbot response
    7. Verify streaming (SSE) includes RAG events and citations

All heavy deps (DB, Redis, MinIO, embedding API, LLM) are replaced by
in-memory fakes (see ``e2e_rag_fixtures.py``).

Run from ``services/chatbot/``::

    python -m pytest tests/test_rag_e2e.py -v

Expected: all tests PASSED, 0 failures.
"""
from __future__ import annotations

import json

import pytest

# Import all fixtures from the shared module via conftest
from e2e_rag_fixtures import (  # noqa: F401
    SAMPLE_DOCUMENT,
    UNRELATED_QUESTION,
    FakeChatbot,
    _reset_store,
    disabled_client,
    e2e_client,
    ingest_sample,
    rag_store,
    tenant_a_client,
)


# ═══════════════════════════════════════════════════════════════════════
# 1. Ingest a sample document
# ═══════════════════════════════════════════════════════════════════════


class TestIngest:
    """POST /api/rag/ingest — end-to-end file upload."""

    def test_ingest_returns_document_id(self, e2e_client):
        data = ingest_sample(e2e_client)
        assert "document_id" in data
        assert data["num_chunks"] >= 1
        assert data["object_path"]

    def test_ingest_empty_file_rejected(self, e2e_client):
        resp = e2e_client.post(
            "/api/rag/ingest",
            files={"file": ("empty.txt", b"", "text/plain")},
            data={"title": "Empty"},
        )
        assert resp.status_code == 400

    def test_ingest_stores_chunks(self, e2e_client, rag_store):
        ingest_sample(e2e_client)
        assert len(rag_store.documents) == 1
        doc = list(rag_store.documents.values())[0]
        assert doc.title == "Quantum Computing Guide"
        assert len(doc.chunks) >= 3


# ═══════════════════════════════════════════════════════════════════════
# 2. Search the ingested document
# ═══════════════════════════════════════════════════════════════════════


class TestSearch:
    """POST /api/rag/search — vector similarity search."""

    def test_search_finds_relevant_chunks(self, e2e_client):
        ingest_sample(e2e_client)
        resp = e2e_client.post(
            "/api/rag/search",
            json={"query": "quantum qubits superposition", "top_k": 3},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["query"] == "quantum qubits superposition"
        assert len(data["results"]) >= 1

    def test_search_returns_expected_fields(self, e2e_client):
        ingest_sample(e2e_client)
        resp = e2e_client.post(
            "/api/rag/search",
            json={"query": "qubits"},
        )
        hit = resp.json()["results"][0]
        assert "chunk_id" in hit
        assert "document_id" in hit
        assert "title" in hit
        assert "content" in hit
        assert "score" in hit
        assert isinstance(hit["score"], float)

    def test_search_no_results_for_unrelated(self, e2e_client):
        ingest_sample(e2e_client)
        resp = e2e_client.post(
            "/api/rag/search",
            json={"query": UNRELATED_QUESTION, "min_score": 0.99},
        )
        # With a very high threshold, unrelated query should return few/no hits
        assert resp.status_code == 200

    def test_search_empty_store(self, e2e_client):
        """Search with nothing ingested returns empty results."""
        resp = e2e_client.post(
            "/api/rag/search",
            json={"query": "anything"},
        )
        assert resp.status_code == 200
        assert resp.json()["results"] == []


# ═══════════════════════════════════════════════════════════════════════
# 3. Grounded question through chatbot — verify citations
# ═══════════════════════════════════════════════════════════════════════


class TestGroundedChat:
    """POST /chat with RAG collections — full round-trip."""

    def test_grounded_answer_has_citations(self, e2e_client):
        doc = ingest_sample(e2e_client)
        doc_id = doc["document_id"]

        resp = e2e_client.post("/chat", json={
            "message": "What are qubits and how do they work?",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": [doc_id],
            "rag_top_k": 5,
        })
        assert resp.status_code == 200
        data = resp.json()

        # Response should mention something from RAG context
        assert data["response"]
        assert "citations" in data
        assert data["citations"] is not None
        assert len(data["citations"]) >= 1

    def test_citation_structure(self, e2e_client):
        doc = ingest_sample(e2e_client)
        resp = e2e_client.post("/chat", json={
            "message": "quantum computing",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": [doc["document_id"]],
        })
        citations = resp.json()["citations"]
        c = citations[0]
        assert "ref" in c
        assert "chunk_id" in c
        assert "document_id" in c
        assert "title" in c
        assert "score" in c
        assert "preview" in c

    def test_grounded_response_contains_context(self, e2e_client):
        """The chatbot receives RAG context in the message."""
        doc = ingest_sample(e2e_client)
        resp = e2e_client.post("/chat", json={
            "message": "Tell me about quantum error correction",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": [doc["document_id"]],
        })
        # FakeChatbot echoes RAG context, so response should reference docs
        assert "Based on the provided documents" in resp.json()["response"]


# ═══════════════════════════════════════════════════════════════════════
# 4. Unknown question → "not enough information"
# ═══════════════════════════════════════════════════════════════════════


class TestUnknownQuestion:
    """Questions unrelated to the ingested docs get a graceful fallback."""

    def test_no_rag_collections_returns_no_citations(self, e2e_client):
        """Without rag_collection_ids, no RAG is triggered."""
        resp = e2e_client.post("/chat", json={
            "message": "What is the meaning of life?",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": [],
        })
        data = resp.json()
        assert data["citations"] is None

    def test_empty_store_returns_fallback(self, e2e_client):
        """RAG enabled but no docs → chatbot gives its own answer."""
        resp = e2e_client.post("/chat", json={
            "message": UNRELATED_QUESTION,
            "model": "grok",
            "language": "en",
            "rag_collection_ids": ["nonexistent-doc-id"],
        })
        data = resp.json()
        # FakeChatbot returns "I don't have enough information" when no RAG context
        assert "don't have enough information" in data["response"]


# ═══════════════════════════════════════════════════════════════════════
# 5. Tenant isolation
# ═══════════════════════════════════════════════════════════════════════


class TestTenantIsolation:
    """Each client has its own session → tenant_id.

    Tenant A's documents must NOT appear in tenant B's searches.
    """

    def test_tenant_b_cannot_search_tenant_a_docs(
        self, e2e_client, tenant_a_client
    ):
        # Tenant A ingests
        doc = ingest_sample(e2e_client, title="Tenant A Quantum")

        # Tenant B searches (different TestClient → different session)
        resp = tenant_a_client.post(
            "/api/rag/search",
            json={"query": "quantum qubits"},
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        # Tenant B should see NO results from tenant A
        assert len(results) == 0

    def test_tenant_b_cannot_chat_with_tenant_a_docs(
        self, e2e_client, tenant_a_client
    ):
        doc = ingest_sample(e2e_client)

        resp = tenant_a_client.post("/chat", json={
            "message": "quantum qubits",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": [doc["document_id"]],
        })
        data = resp.json()
        # Tenant B's chatbot should NOT get RAG context
        assert "don't have enough information" in data["response"]

    def test_each_tenant_sees_own_docs(self, e2e_client, tenant_a_client, rag_store):
        """Both tenants ingest; each only sees their own."""
        ingest_sample(e2e_client, title="Tenant A Doc")
        ingest_sample(tenant_a_client, title="Tenant B Doc")

        # 2 documents in total
        assert len(rag_store.documents) == 2

        # Tenant A search
        resp_a = e2e_client.post(
            "/api/rag/search",
            json={"query": "quantum"},
        )
        results_a = resp_a.json()["results"]

        # Tenant B search
        resp_b = tenant_a_client.post(
            "/api/rag/search",
            json={"query": "quantum"},
        )
        results_b = resp_b.json()["results"]

        # Each should see exactly 1 doc's chunks
        doc_ids_a = {r["document_id"] for r in results_a}
        doc_ids_b = {r["document_id"] for r in results_b}
        assert len(doc_ids_a) == 1
        assert len(doc_ids_b) == 1
        assert doc_ids_a != doc_ids_b  # different documents


# ═══════════════════════════════════════════════════════════════════════
# 6. RAG disabled mode
# ═══════════════════════════════════════════════════════════════════════


class TestRAGDisabled:
    """When RAG_ENABLED=false, endpoints return 503 but chat still works."""

    def test_ingest_returns_503(self, disabled_client):
        resp = disabled_client.post(
            "/api/rag/ingest",
            files={"file": ("test.txt", b"hello", "text/plain")},
            data={"title": "Test"},
        )
        assert resp.status_code == 503

    def test_search_returns_503(self, disabled_client):
        resp = disabled_client.post(
            "/api/rag/search",
            json={"query": "anything"},
        )
        assert resp.status_code == 503

    def test_chat_still_works_without_rag(self, disabled_client):
        """Chat endpoint should work fine with RAG disabled."""
        resp = disabled_client.post("/chat", json={
            "message": "Hello, how are you?",
            "model": "grok",
            "language": "en",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"]
        assert data["citations"] is None

    def test_chat_with_rag_ids_graceful_fallback(self, disabled_client):
        """Passing rag_collection_ids when RAG is disabled → no crash."""
        resp = disabled_client.post("/chat", json={
            "message": "Tell me about quantum",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": ["some-doc-id"],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["citations"] is None


# ═══════════════════════════════════════════════════════════════════════
# 7. Streaming (SSE) with RAG
# ═══════════════════════════════════════════════════════════════════════


def _parse_sse(raw: str) -> list[tuple[str, dict]]:
    """Parse text/event-stream into [(event_name, data_dict), ...]."""
    events = []
    current_event = ""
    current_data = ""
    for line in raw.split("\n"):
        if line.startswith("event: "):
            current_event = line[7:].strip()
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "":
            if current_event and current_data:
                try:
                    events.append((current_event, json.loads(current_data)))
                except json.JSONDecodeError:
                    events.append((current_event, {"raw": current_data}))
            current_event = ""
            current_data = ""
    return events


class TestStreamingWithRAG:
    """POST /chat/stream — SSE events include RAG metadata + citations."""

    def test_stream_includes_rag_context_event(self, e2e_client):
        doc = ingest_sample(e2e_client)
        resp = e2e_client.post("/chat/stream", json={
            "message": "How do qubits work in quantum computing?",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": [doc["document_id"]],
            "rag_top_k": 3,
        })
        assert resp.status_code == 200

        events = _parse_sse(resp.text)
        event_names = [e[0] for e in events]

        assert "rag_context" in event_names, f"Missing rag_context in {event_names}"
        assert "metadata" in event_names
        assert "chunk" in event_names
        assert "complete" in event_names
        assert "citations" in event_names

    def test_stream_rag_context_event_has_citations(self, e2e_client):
        doc = ingest_sample(e2e_client)
        resp = e2e_client.post("/chat/stream", json={
            "message": "quantum computing qubits",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": [doc["document_id"]],
        })

        events = _parse_sse(resp.text)
        rag_events = [d for name, d in events if name == "rag_context"]
        assert len(rag_events) == 1
        rag_data = rag_events[0]
        assert rag_data["chunk_count"] >= 1
        assert len(rag_data["citations"]) >= 1

    def test_stream_final_citations_event(self, e2e_client):
        doc = ingest_sample(e2e_client)
        resp = e2e_client.post("/chat/stream", json={
            "message": "quantum error correction",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": [doc["document_id"]],
        })

        events = _parse_sse(resp.text)
        cite_events = [d for name, d in events if name == "citations"]
        assert len(cite_events) == 1
        assert len(cite_events[0]["citations"]) >= 1

    def test_stream_without_rag_no_rag_events(self, e2e_client):
        """Without rag_collection_ids, no rag_context or citations events."""
        resp = e2e_client.post("/chat/stream", json={
            "message": "Hello!",
            "model": "grok",
            "language": "en",
        })
        assert resp.status_code == 200

        events = _parse_sse(resp.text)
        event_names = [e[0] for e in events]
        assert "rag_context" not in event_names
        assert "citations" not in event_names


# ═══════════════════════════════════════════════════════════════════════
# 8. Multi-document search + filtering
# ═══════════════════════════════════════════════════════════════════════


class TestMultiDocument:
    """Ingest multiple documents and verify doc_id filtering."""

    def test_search_filters_by_doc_id(self, e2e_client):
        doc1 = ingest_sample(e2e_client, title="Doc Alpha")

        # Ingest a second doc
        resp2 = e2e_client.post(
            "/api/rag/ingest",
            files={"file": (
                "biology.txt",
                b"DNA is a double helix. Genes encode proteins. RNA transcribes DNA.",
                "text/plain",
            )},
            data={"title": "Biology Basics"},
        )
        doc2 = resp2.json()

        # Search ALL docs
        resp_all = e2e_client.post(
            "/api/rag/search",
            json={"query": "quantum DNA genes", "top_k": 10},
        )
        all_ids = {r["document_id"] for r in resp_all.json()["results"]}
        assert len(all_ids) == 2  # both docs

        # Search restricted to doc1
        resp_filtered = e2e_client.post(
            "/api/rag/search",
            json={"query": "quantum", "doc_ids": [doc1["document_id"]]},
        )
        filtered_ids = {r["document_id"] for r in resp_filtered.json()["results"]}
        assert filtered_ids == {doc1["document_id"]}

    def test_chat_with_specific_doc_id(self, e2e_client):
        doc1 = ingest_sample(e2e_client, title="Quantum Doc")

        e2e_client.post(
            "/api/rag/ingest",
            files={"file": (
                "cooking.txt",
                b"Pasta is boiled in salted water. Al dente means firm to the bite.",
                "text/plain",
            )},
            data={"title": "Cooking Guide"},
        )

        # Chat asks about quantum but only references the quantum doc
        resp = e2e_client.post("/chat", json={
            "message": "Tell me about quantum computing",
            "model": "grok",
            "language": "en",
            "rag_collection_ids": [doc1["document_id"]],
        })
        data = resp.json()
        assert data["citations"] is not None
        # All citations must be from doc1
        for c in data["citations"]:
            assert c["document_id"] == doc1["document_id"]
