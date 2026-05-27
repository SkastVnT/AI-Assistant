"""Shared Gemini API key rotation pool for the anime pipeline.

Reads ``GEMINI_API_KEY``, ``GOOGLE_API_KEY`` and ``GEMINI_API_KEY_1..9``
from the environment once at import time. When an agent receives a 429
(quota exhausted) for the currently active key, it calls
:func:`mark_exhausted` to remove that key from the rotation. Once all
keys are exhausted the pool returns ``None`` and callers should skip
Gemini and fall through to their OpenAI fallback. This avoids spamming
the same dead key on every refine round.
"""

from __future__ import annotations

import logging
import os
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_keys: list[str] = []
_exhausted: set[str] = set()
_index: int = 0
_loaded: bool = False


def _load() -> None:
    global _loaded, _keys
    if _loaded:
        return
    seen: set[str] = set()
    candidates: list[str] = []
    for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
        v = os.getenv(name, "").strip()
        if v and v not in seen:
            candidates.append(v)
            seen.add(v)
    for i in range(1, 10):
        v = os.getenv(f"GEMINI_API_KEY_{i}", "").strip()
        if v and v not in seen:
            candidates.append(v)
            seen.add(v)
    _keys = candidates
    _loaded = True
    if _keys:
        logger.info("[GeminiPool] Loaded %d Gemini key(s) into rotation", len(_keys))


def get_active_key() -> str | None:
    """Return the next non-exhausted key, or ``None`` if all are dead."""
    with _lock:
        _load()
        n = len(_keys)
        if n == 0:
            return None
        global _index
        for _ in range(n):
            key = _keys[_index % n]
            if key not in _exhausted:
                return key
            _index = (_index + 1) % n
        return None


def mark_exhausted(key: str | None, reason: str = "429") -> None:
    """Mark ``key`` as exhausted and advance to the next key."""
    if not key:
        return
    with _lock:
        _load()
        if key in _exhausted:
            return
        _exhausted.add(key)
        global _index
        _index = (_index + 1) % max(len(_keys), 1)
        remaining = len(_keys) - len(_exhausted)
        logger.warning(
            "[GeminiPool] Key ...%s marked exhausted (%s); %d/%d keys remain",
            key[-6:],
            reason,
            remaining,
            len(_keys),
        )


def all_exhausted() -> bool:
    with _lock:
        _load()
        return bool(_keys) and len(_exhausted) >= len(_keys)


def is_quota_error(exc: BaseException) -> bool:
    """Detect 429 / quota / rate limit errors from httpx or generic responses."""
    msg = str(exc).lower()
    if (
        "429" in msg
        or "too many requests" in msg
        or "quota" in msg
        or "rate limit" in msg
    ):
        return True
    # httpx.HTTPStatusError exposes .response
    response = getattr(exc, "response", None)
    if response is not None and getattr(response, "status_code", None) == 429:
        return True
    return False


def is_auth_error(exc: BaseException) -> bool:
    """Detect 401/403 (invalid / disabled / region-blocked key) errors.

    Treated as permanently exhausted: the same key will keep returning the
    same status, so retrying it on every critique just wastes time.
    """
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        if status in (401, 403):
            return True
    msg = str(exc).lower()
    return (
        "401 unauthorized" in msg
        or "403 forbidden" in msg
        or "api key not valid" in msg
        or "permission denied" in msg
    )
