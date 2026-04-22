"""Tests for series-first search ordering, NSFW intent detection, and
prioritize_sensitive chain flip in image_url_fallback.

Pinned behaviours (verbatim from 2026-04-23 user request):
  * "khi nguoi dung nhap <character> <prep> <Game/Anime/Manga>, luc do
     uu tien tai search tim truoc voi <Game/...>"
  * "tim anh nhay cam (nen tim 5 tam) thi su dung model stepfun step
     3.5 flash (openrouter)"
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


# ── NSFW heuristic ───────────────────────────────────────────────────

@pytest.mark.parametrize("prompt", [
    "Klee Genshin Impact, nude, ahegao",
    "Rem Re:Zero pussy",
    "Hu Tao naked spread legs",
    "anime girl r-18 explicit",
    "Kafka HSR uncensored nipples",
])
def test_detect_nsfw_intent_matches_explicit_prompts(prompt):
    from image_pipeline.anime_pipeline.character_research import _detect_nsfw_intent
    assert _detect_nsfw_intent(prompt) is True


@pytest.mark.parametrize("prompt", [
    "Klee Genshin Impact",
    "Rem Re:Zero, masterpiece, best quality",
    "Hu Tao official art portrait",
    "",
    "anime girl smiling in field",
    "Elysia Honkai Impact 3rd",
])
def test_detect_nsfw_intent_skips_safe_prompts(prompt):
    from image_pipeline.anime_pipeline.character_research import _detect_nsfw_intent
    assert _detect_nsfw_intent(prompt) is False


# ── Character-first SerpAPI query ordering ───────────────────────────

def test_image_search_first_query_starts_with_series():
    """The very first SerpAPI query must mention BOTH the character and
    the series so Google Images grounds results on the actual character.

    History: a pure-series warm-up query was tried in Phase 11 C5 to act
    as a 'palette anchor', but it returned generic franchise wallpapers
    that polluted the result set (Hu Tao search returned non-Hu-Tao
    Genshin art). Removed 2026-04-23. The first query now MUST contain
    the character name.
    """
    from image_pipeline.anime_pipeline import character_research as cr

    captured_queries: list[str] = []

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"images_results": []}

    def _fake_get(url, params=None, **kw):
        captured_queries.append(params.get("q", ""))
        return _FakeResp()

    with patch.object(cr, "_get_serpapi_key", return_value="fake_key"):
        import httpx
        with patch.object(httpx, "get", side_effect=_fake_get):
            cr._image_search_character("Klee", "Genshin Impact", "klee_(genshin_impact)")

    assert captured_queries, "expected at least one SerpAPI query"
    first = captured_queries[0].lower()
    # Both character and series must be present in the very first query.
    assert "klee" in first, f"first query missing character name: {first!r}"
    assert "genshin impact" in first, f"first query missing series name: {first!r}"


def test_image_search_nsfw_intent_skips_safe_queries():
    """When nsfw_intent=True we keep only one strong character-specific
    SerpAPI query — the additional safe queries waste quota."""
    from image_pipeline.anime_pipeline import character_research as cr

    captured_queries: list[str] = []

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self): return {"images_results": []}

    def _fake_get(url, params=None, **kw):
        captured_queries.append(params.get("q", ""))
        return _FakeResp()

    with patch.object(cr, "_get_serpapi_key", return_value="fake_key"):
        import httpx
        with patch.object(httpx, "get", side_effect=_fake_get):
            cr._image_search_character(
                "Klee", "Genshin Impact", "klee_(genshin_impact)",
                nsfw_intent=True,
            )

    assert len(captured_queries) == 1


# ── prioritize_sensitive chain flip ──────────────────────────────────

def test_fallback_chain_flips_when_prioritize_sensitive(monkeypatch):
    """With prioritize_sensitive=True, StepFun must be tried FIRST."""
    from image_pipeline.anime_pipeline import image_url_fallback as fb

    monkeypatch.setenv("GEMINI_API_KEY", "g_key")
    monkeypatch.setenv("OPENAI_API_KEY", "o_key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or_key")
    # Make sure XAI is unset so chain length is deterministic.
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)

    call_order: list[str] = []

    def _record(name):
        def _fn(query, key):
            call_order.append(name)
            return []  # contribute nothing so all providers are tried
        return _fn

    monkeypatch.setattr(fb, "_provider_gemini", _record("gemini"))
    monkeypatch.setattr(fb, "_provider_openai_search", _record("openai"))
    monkeypatch.setattr(fb, "_provider_stepfun_openrouter", _record("stepfun"))

    fb.fetch_image_urls_fallback(
        display_name="Klee", series_name="Genshin Impact",
        danbooru_tag="klee_(genshin_impact)",
        already_found=[], target_count=5,
        prioritize_sensitive=True,
    )

    assert call_order, "expected at least one provider call"
    assert call_order[0] == "stepfun"


def test_fallback_chain_normal_order_when_safe(monkeypatch):
    """Without prioritize_sensitive, the safe providers must run first
    and StepFun is appended only when allow_sensitive=True."""
    from image_pipeline.anime_pipeline import image_url_fallback as fb

    monkeypatch.setenv("GEMINI_API_KEY", "g_key")
    monkeypatch.setenv("OPENROUTER_API_KEY", "or_key")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("GROK_API_KEY", raising=False)

    call_order: list[str] = []
    monkeypatch.setattr(
        fb, "_provider_gemini",
        lambda q, k: (call_order.append("gemini") or []),
    )
    monkeypatch.setattr(
        fb, "_provider_stepfun_openrouter",
        lambda q, k: (call_order.append("stepfun") or []),
    )

    # allow_sensitive=False → StepFun NOT in chain at all.
    fb.fetch_image_urls_fallback(
        display_name="Klee", series_name="Genshin Impact",
        danbooru_tag="klee_(genshin_impact)",
        already_found=[], target_count=5,
        allow_sensitive=False,
    )
    assert call_order == ["gemini"]
    assert "stepfun" not in call_order

    # allow_sensitive=True without prioritize → safe first, StepFun last.
    call_order.clear()
    fb.fetch_image_urls_fallback(
        display_name="Klee", series_name="Genshin Impact",
        danbooru_tag="klee_(genshin_impact)",
        already_found=[], target_count=5,
        allow_sensitive=True,
    )
    assert call_order[0] == "gemini"
    assert call_order[-1] == "stepfun"


def test_stepfun_model_id_overridable_via_env(monkeypatch):
    """OPENROUTER_STEPFUN_MODEL env var must override the default model
    id sent to OpenRouter so we can swap step-3 → step-3.5-flash without
    a code change."""
    from image_pipeline.anime_pipeline import image_url_fallback as fb

    captured = {}

    class _FakeResp:
        def raise_for_status(self): pass
        def json(self):
            return {"choices": [{"message": {"content": "[]"}}]}

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["model"] = json["model"]
        return _FakeResp()

    import httpx
    monkeypatch.setenv("OPENROUTER_STEPFUN_MODEL", "stepfun-ai/step-3.5-flash")
    with patch.object(httpx, "post", side_effect=_fake_post):
        fb._provider_stepfun_openrouter("Klee", "fake_key")

    assert captured["model"] == "stepfun-ai/step-3.5-flash"
