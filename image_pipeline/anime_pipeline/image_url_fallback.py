"""
image_url_fallback.py - Fallback chain for character reference image URL discovery.

Spec §3: when SerpAPI returns fewer than `target_count` images (or fails), try
additional providers to recover image URLs. StepFun (via OpenRouter) is used
for *sensitive* / NSFW character references that Google Images tends to filter.

Chain order (first-hit-wins, accumulates until ``target_count`` satisfied):

    1. SerpAPI google_images        (primary, already handled in caller)
    2. Gemini Grounding (google)    (GEMINI_API_KEY)
    3. OpenAI gpt-4o-search-preview (OPENAI_API_KEY)
    4. xAI Grok Live Search         (XAI_API_KEY or GROK_API_KEY)
    5. StepFun step-1v-32k          (OPENROUTER_API_KEY, NSFW-tolerant)

Every provider is best-effort. Missing keys / network errors are silently
skipped so the pipeline degrades instead of crashing.

Public API:
    fetch_image_urls_fallback(display_name, series_name, danbooru_tag,
                              already_found, target_count=10,
                              allow_sensitive=False) -> list[dict]

Each returned dict has shape::

    {"url": str, "source": str, "title": str, "provider": str}
"""

from __future__ import annotations

import json
import logging
import os
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ── Shared helpers ───────────────────────────────────────────────────

_URL_RE = re.compile(
    r"https?://[^\s'\"<>\]\)]+\.(?:jpg|jpeg|png|webp|gif)(?:\?[^\s'\"<>\]\)]*)?",
    re.IGNORECASE,
)


def _dedupe(seen: set[str], new: list[dict]) -> list[dict]:
    out: list[dict] = []
    for item in new:
        url = item.get("url", "").strip()
        if not url or url in seen:
            continue
        seen.add(url)
        out.append(item)
    return out


def _extract_urls_from_text(text: str) -> list[str]:
    return list(dict.fromkeys(_URL_RE.findall(text or "")))


# ── Provider 1: Gemini Grounding ─────────────────────────────────────

def _provider_gemini(query: str, api_key: str) -> list[dict]:
    """Use Gemini 2.0 Flash with Google Search grounding to collect URLs."""
    import httpx
    prompt = (
        f"Find 10 high-quality official anime illustration image URLs for "
        f"'{query}'. Output ONLY a JSON array of objects like "
        f'[{{"url":"https://...","source":"danbooru.donmai.us"}}]. '
        f"Only include URLs ending in .jpg, .jpeg, .png, or .webp. "
        f"Prefer danbooru, pixiv, fandom wiki, official character pages."
    )
    try:
        resp = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-2.0-flash:generateContent?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "tools": [{"google_search": {}}],
                "generationConfig": {
                    "temperature": 0.2, "maxOutputTokens": 2000,
                },
            },
            timeout=25,
        )
        resp.raise_for_status()
        data = resp.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {}).get("parts", [{}])[0]
            .get("text", "")
        )
        # Try strict JSON first
        try:
            m = re.search(r"\[.*\]", text, re.DOTALL)
            if m:
                items = json.loads(m.group(0))
                return [
                    {"url": it.get("url", ""),
                     "source": it.get("source", ""), "title": "",
                     "provider": "gemini"}
                    for it in items if isinstance(it, dict) and it.get("url")
                ]
        except Exception:
            pass
        # Fallback: regex-extract URLs from text
        return [
            {"url": u, "source": "", "title": "", "provider": "gemini"}
            for u in _extract_urls_from_text(text)
        ]
    except Exception as e:
        logger.debug("[ImageFallback] Gemini provider failed: %s", e)
        return []


# ── Provider 2: OpenAI Responses API (gpt-4o-search-preview) ─────────

def _provider_openai_search(query: str, api_key: str) -> list[dict]:
    """Use OpenAI's web-search-enabled chat model to fetch image URLs."""
    import httpx
    try:
        resp = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "gpt-4o-search-preview",
                "messages": [
                    {"role": "system", "content":
                        "You are a reference-image finder. Only output a JSON "
                        "array of {url, source} objects. Only anime / illustration "
                        "URLs ending in .jpg/.jpeg/.png/.webp."},
                    {"role": "user", "content":
                        f"Find 10 official anime illustration image URLs for: "
                        f"{query}. Prefer danbooru, pixiv, fandom wiki."},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            try:
                items = json.loads(m.group(0))
                return [
                    {"url": it.get("url", ""),
                     "source": it.get("source", ""), "title": "",
                     "provider": "openai"}
                    for it in items if isinstance(it, dict) and it.get("url")
                ]
            except Exception:
                pass
        return [
            {"url": u, "source": "", "title": "", "provider": "openai"}
            for u in _extract_urls_from_text(text)
        ]
    except Exception as e:
        logger.debug("[ImageFallback] OpenAI provider failed: %s", e)
        return []


# ── Provider 3: xAI Grok Live Search ─────────────────────────────────

def _provider_grok(query: str, api_key: str) -> list[dict]:
    """Use xAI Grok with Live Search (web) to fetch image URLs."""
    import httpx
    try:
        resp = httpx.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "model": "grok-4-fast-reasoning",
                "messages": [
                    {"role": "system", "content":
                        "Output ONLY a JSON array [{\"url\":\"...\",\"source\":\"...\"}]. "
                        "Only anime illustration URLs ending in .jpg/.jpeg/.png/.webp."},
                    {"role": "user", "content":
                        f"Find 10 official anime illustration image URLs for: {query}"},
                ],
                "search_parameters": {"mode": "on"},
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            try:
                items = json.loads(m.group(0))
                return [
                    {"url": it.get("url", ""),
                     "source": it.get("source", ""), "title": "",
                     "provider": "grok"}
                    for it in items if isinstance(it, dict) and it.get("url")
                ]
            except Exception:
                pass
        return [
            {"url": u, "source": "", "title": "", "provider": "grok"}
            for u in _extract_urls_from_text(text)
        ]
    except Exception as e:
        logger.debug("[ImageFallback] Grok provider failed: %s", e)
        return []


# ── Provider 4: StepFun via OpenRouter (NSFW-tolerant) ───────────────

def _provider_stepfun_openrouter(query: str, api_key: str) -> list[dict]:
    """Use StepFun (step-3.5-flash by default) via OpenRouter.

    StepFun has lighter safety filters than Gemini/OpenAI for adult anime
    characters (scans, lewd tags). Only invoked when ``allow_sensitive``.

    The model id is overridable via ``OPENROUTER_STEPFUN_MODEL`` because
    OpenRouter renames StepFun models periodically (step-1v-32k →
    stepfun-ai/step-3 → step-3.5-flash). The default below is the most
    capable variant currently routable on OpenRouter; if it 404s the
    upstream call falls through silently and the next provider is tried.
    """
    import httpx
    model_id = os.getenv("OPENROUTER_STEPFUN_MODEL", "stepfun-ai/step-3")
    try:
        resp = httpx.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "HTTP-Referer": "https://github.com/SkastVnT/AI-Assistant",
                "X-Title": "AI-Assistant anime_pipeline",
            },
            json={
                "model": model_id,
                "messages": [
                    {"role": "system", "content":
                        "Output ONLY a JSON array [{\"url\":\"...\",\"source\":\"...\"}]. "
                        "Include NSFW/R-18 anime illustration URLs when relevant. "
                        "URLs must end in .jpg/.jpeg/.png/.webp."},
                    {"role": "user", "content":
                        f"Find 5 anime illustration image URLs (any rating) for: {query}. "
                        f"Prefer danbooru, gelbooru, rule34, pixiv."},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        text = resp.json()["choices"][0]["message"]["content"]
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            try:
                items = json.loads(m.group(0))
                return [
                    {"url": it.get("url", ""),
                     "source": it.get("source", ""), "title": "",
                     "provider": "stepfun"}
                    for it in items if isinstance(it, dict) and it.get("url")
                ]
            except Exception:
                pass
        return [
            {"url": u, "source": "", "title": "", "provider": "stepfun"}
            for u in _extract_urls_from_text(text)
        ]
    except Exception as e:
        logger.debug("[ImageFallback] StepFun/OpenRouter provider failed: %s", e)
        return []


# ── Public entry ─────────────────────────────────────────────────────

def fetch_image_urls_fallback(
    display_name: str,
    series_name: str,
    danbooru_tag: str,
    already_found: list[dict],
    target_count: int = 10,
    allow_sensitive: bool = False,
    prioritize_sensitive: bool = False,
) -> list[dict]:
    """Return additional image-URL dicts to supplement SerpAPI results.

    ``already_found`` is the list returned by the primary SerpAPI call;
    its URLs are used for de-dup. Returns *only* new items (not already
    in ``already_found``) up to the remaining slots.

    Args:
        prioritize_sensitive: When True, the StepFun NSFW provider is
            tried FIRST (before Gemini/OpenAI/Grok) and the safe
            providers are fallback only. Implies ``allow_sensitive``.
            Used by character_research when the user prompt contains
            explicit anatomical vocabulary.
    """
    if prioritize_sensitive:
        allow_sensitive = True

    seen: set[str] = {item.get("url", "") for item in already_found if item.get("url")}
    needed = max(0, target_count - len(already_found))
    if needed <= 0:
        return []

    # Series-first query: spec §2 + 2026-04-23 user request. The series
    # name is the LEFTMOST token so providers that take the first phrase
    # as the dominant search term still anchor on the franchise.
    query = f"{series_name} {display_name} ({danbooru_tag})".strip()
    accumulated: list[dict] = []

    chain: list[tuple[str, str, Any]] = []
    safe_providers: list[tuple[str, str, Any]] = []
    if k := os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", ""):
        safe_providers.append(("gemini", k, _provider_gemini))
    if k := os.getenv("OPENAI_API_KEY", ""):
        safe_providers.append(("openai", k, _provider_openai_search))
    if k := os.getenv("XAI_API_KEY") or os.getenv("GROK_API_KEY", ""):
        safe_providers.append(("grok", k, _provider_grok))

    sensitive_provider: Optional[tuple[str, str, Any]] = None
    if allow_sensitive and (k := os.getenv("OPENROUTER_API_KEY", "")):
        sensitive_provider = ("stepfun", k, _provider_stepfun_openrouter)

    if prioritize_sensitive and sensitive_provider is not None:
        # NSFW intent: StepFun first, safe providers as backup.
        chain.append(sensitive_provider)
        chain.extend(safe_providers)
    else:
        chain.extend(safe_providers)
        if sensitive_provider is not None:
            chain.append(sensitive_provider)

    for name, key, func in chain:
        if len(accumulated) >= needed:
            break
        logger.info(
            "[ImageFallback] Trying %s (need %d more)",
            name, needed - len(accumulated),
        )
        try:
            results = func(query, key)
        except Exception as e:
            logger.warning("[ImageFallback] Provider %s raised: %s", name, e)
            continue
        fresh = _dedupe(seen, results)
        accumulated.extend(fresh[: needed - len(accumulated)])
        logger.info(
            "[ImageFallback] %s contributed %d URLs (total accumulated=%d)",
            name, len(fresh), len(accumulated),
        )

    return accumulated


__all__ = ["fetch_image_urls_fallback"]
