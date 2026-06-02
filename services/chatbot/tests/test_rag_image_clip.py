"""
Unit tests for the CLIP / image-RAG additions.

Covers:
    - clip_adapter HTTP contract (mocked requests): enabled gate, embed_text,
      embed_image, embed_query, graceful failure.
    - RAGOrchestrator image-merge behaviour (text + image hits merged & sorted).
    - rag_settings CLIP fields default + env override.

Run from services/chatbot/:
    python -m pytest tests/test_rag_image_clip.py -v
"""

from __future__ import annotations

import asyncio

import pytest

# ---------------------------------------------------------------------------
# rag_settings CLIP fields
# ---------------------------------------------------------------------------


@pytest.mark.rag
class TestRagSettingsClip:
    def test_defaults(self, monkeypatch):
        from core.rag_settings import get_rag_settings

        for var in ("RAG_IMAGE_ENABLED", "CLIP_EMBED_URL", "CLIP_EMBED_DIM"):
            monkeypatch.delenv(var, raising=False)
        get_rag_settings.cache_clear()
        s = get_rag_settings()
        assert s.image_enabled is False
        assert s.clip_embed_url == "http://localhost:8200"
        assert s.clip_embed_dim == 512

    def test_env_override(self, monkeypatch):
        from core.rag_settings import get_rag_settings

        monkeypatch.setenv("RAG_IMAGE_ENABLED", "true")
        monkeypatch.setenv("CLIP_EMBED_URL", "http://clip:9000")
        monkeypatch.setenv("CLIP_EMBED_DIM", "768")
        get_rag_settings.cache_clear()
        s = get_rag_settings()
        assert s.image_enabled is True
        assert s.clip_embed_url == "http://clip:9000"
        assert s.clip_embed_dim == 768
        get_rag_settings.cache_clear()


# ---------------------------------------------------------------------------
# clip_adapter
# ---------------------------------------------------------------------------


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


@pytest.mark.rag
class TestClipAdapter:
    def _enable(self, monkeypatch):
        from core.rag_settings import get_rag_settings

        monkeypatch.setenv("RAG_IMAGE_ENABLED", "true")
        monkeypatch.setenv("CLIP_EMBED_DIM", "512")
        get_rag_settings.cache_clear()

    def test_disabled_raises(self, monkeypatch):
        from core.rag_settings import get_rag_settings

        monkeypatch.setenv("RAG_IMAGE_ENABLED", "false")
        get_rag_settings.cache_clear()
        from core import clip_adapter

        assert clip_adapter.is_enabled() is False
        with pytest.raises(clip_adapter.ClipUnavailableError):
            clip_adapter.embed_texts(["hello"])
        get_rag_settings.cache_clear()

    def test_embed_texts(self, monkeypatch):
        self._enable(monkeypatch)
        from core import clip_adapter

        def _fake_post(url, json=None, timeout=None):
            assert url.endswith("/embed/text")
            assert json == {"texts": ["hello"]}
            return _FakeResponse({"embeddings": [[0.1] * 512], "dim": 512})

        monkeypatch.setattr(clip_adapter.requests, "post", _fake_post)
        vectors = clip_adapter.embed_texts(["hello"])
        assert vectors == [[0.1] * 512]

        from core.rag_settings import get_rag_settings

        get_rag_settings.cache_clear()

    def test_embed_query(self, monkeypatch):
        self._enable(monkeypatch)
        from core import clip_adapter

        monkeypatch.setattr(
            clip_adapter.requests,
            "post",
            lambda *a, **k: _FakeResponse({"embeddings": [[0.5, 0.5]], "dim": 512}),
        )
        assert clip_adapter.embed_query("q") == [0.5, 0.5]

        from core.rag_settings import get_rag_settings

        get_rag_settings.cache_clear()

    def test_embed_images(self, monkeypatch):
        self._enable(monkeypatch)
        from core import clip_adapter

        def _fake_post(url, json=None, timeout=None):
            assert url.endswith("/embed/image")
            assert json == {"images": ["BASE64"]}
            return _FakeResponse({"embeddings": [[1.0] * 512], "dim": 512})

        monkeypatch.setattr(clip_adapter.requests, "post", _fake_post)
        assert clip_adapter.embed_images(["BASE64"]) == [[1.0] * 512]

        from core.rag_settings import get_rag_settings

        get_rag_settings.cache_clear()

    def test_request_failure_raises(self, monkeypatch):
        self._enable(monkeypatch)
        from core import clip_adapter

        def _boom(*a, **k):
            raise clip_adapter.requests.RequestException("down")

        monkeypatch.setattr(clip_adapter.requests, "post", _boom)
        with pytest.raises(clip_adapter.ClipUnavailableError):
            clip_adapter.embed_texts(["x"])

        from core.rag_settings import get_rag_settings

        get_rag_settings.cache_clear()


# ---------------------------------------------------------------------------
# RAGOrchestrator image merge
# ---------------------------------------------------------------------------


def _make_hit(chunk_id, score, content="text", meta=None):
    from src.rag.service.retrieval_service import RetrievalHit

    return RetrievalHit(
        chunk_id=chunk_id,
        document_id="d1",
        title="Doc",
        content=content,
        score=score,
        metadata_json=meta or {},
    )


class _FakeStrategy:
    def __init__(self, text_hits, image_hits):
        self._text_hits = text_hits
        self._image_hits = image_hits

    async def retrieve(self, *, tenant_id, query, top_k, doc_ids=None, min_score=None):
        return self._text_hits

    async def retrieve_images(
        self, *, tenant_id, query, top_k, doc_ids=None, min_score=None
    ):
        return self._image_hits


@pytest.mark.rag
class TestOrchestratorImageMerge:
    def test_merges_and_sorts(self, monkeypatch):
        from core.rag_settings import get_rag_settings

        monkeypatch.setenv("RAG_IMAGE_ENABLED", "true")
        get_rag_settings.cache_clear()

        import src.rag as rag_pkg

        monkeypatch.setattr(rag_pkg, "RAG_ENABLED", True, raising=False)

        from src.rag.service.orchestrator import RAGOrchestrator

        text_hits = [_make_hit("t1", 0.7, "text chunk")]
        image_hits = [
            _make_hit("i1", 0.95, "a cat", meta={"source": "image", "object_path": "x"})
        ]
        orch = RAGOrchestrator(strategy=_FakeStrategy(text_hits, image_hits))

        result = asyncio.run(
            orch.retrieve_for_chat(
                message="find the cat",
                custom_prompt="sys",
                language="en",
                tenant_id="default",
                collection_ids=["c1"],
            )
        )
        # Both hits should contribute to citations; image hit ranks first.
        assert result.chunk_count == 2
        assert result.citations is not None
        get_rag_settings.cache_clear()
