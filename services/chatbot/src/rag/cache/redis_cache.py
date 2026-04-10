"""
Redis-backed result cache for the RAG retrieval pipeline.

When Redis is unavailable (not installed, unreachable, or explicitly
disabled) every operation silently becomes a no-op so that the rest of
the system continues working without caching.

Public API
----------
_cache_key(tenant_id, query, top_k, doc_ids)
    Pure function that produces a stable, deterministic cache key.

RedisCache
    Async wrapper around ``redis.asyncio.Redis`` with get/set helpers
    for retrieval results.  Constructed with a Redis URL; the connection
    is attempted lazily and errors are swallowed.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

# Key prefix used for all retrieval cache entries.
_KEY_PREFIX = "rag:retrieve:"


def _cache_key(
    tenant_id: str,
    query: str,
    top_k: int,
    doc_ids: list[str] | None,
) -> str:
    """Return a deterministic cache key for a retrieval request.

    The key is independent of the *order* of ``doc_ids`` (sorted before
    hashing) and is prefixed with ``"rag:retrieve:"``.

    Parameters
    ----------
    tenant_id : str
        Tenant isolation key.
    query : str
        Natural-language query string.
    top_k : int
        Maximum number of results requested.
    doc_ids : list[str] | None
        Optional document filter.  Order is normalised.

    Returns
    -------
    str
        A ``rag:retrieve:<sha256_hex>`` cache key.
    """
    normalised_docs = sorted(doc_ids) if doc_ids else []
    payload = json.dumps(
        {"tenant": tenant_id, "q": query, "k": top_k, "docs": normalised_docs},
        sort_keys=True,
        separators=(",", ":"),
    ).encode()
    digest = hashlib.sha256(payload).hexdigest()
    return f"{_KEY_PREFIX}{digest}"


class RedisCache:
    """Async Redis cache for retrieval results.

    Parameters
    ----------
    redis_url : str
        Redis connection URL (e.g. ``"redis://localhost:6379/0"``).
    default_ttl : int
        Time-to-live in seconds for cached entries.  Default: 3600.
    connect_timeout : int
        Seconds to wait when establishing a TCP connection.  Default: 5.
    socket_timeout : int
        Seconds to wait for a response from Redis.  Default: 5.
    """

    def __init__(
        self,
        redis_url: str,
        default_ttl: int = 3600,
        connect_timeout: int = 5,
        socket_timeout: int = 5,
    ) -> None:
        self._ttl = default_ttl
        self._redis: Any = None  # redis.asyncio.Redis or None

        try:
            import redis.asyncio as aioredis  # type: ignore[import]

            self._redis = aioredis.from_url(
                redis_url,
                socket_connect_timeout=connect_timeout,
                socket_timeout=socket_timeout,
            )
        except ImportError:
            logger.debug("RedisCache: redis package not installed — cache disabled")
        except Exception as exc:
            logger.debug("RedisCache: could not create client (%s) — cache disabled", exc)

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def get_retrieval(
        self,
        tenant_id: str,
        query: str,
        top_k: int,
        doc_ids: list[str] | None = None,
    ) -> list[dict] | None:
        """Return cached retrieval results, or ``None`` on miss / error.

        Parameters
        ----------
        tenant_id, query, top_k, doc_ids
            Must match the values used when the entry was stored.

        Returns
        -------
        list[dict] | None
            Decoded JSON payload, or ``None`` if not cached.
        """
        if self._redis is None:
            return None
        try:
            key = _cache_key(tenant_id, query, top_k, doc_ids)
            raw = await self._redis.get(key)
            if raw is None:
                return None
            return json.loads(raw)
        except Exception as exc:
            logger.debug("RedisCache.get_retrieval failed: %s", exc)
            return None

    async def set_retrieval(
        self,
        tenant_id: str,
        query: str,
        top_k: int,
        data: list[dict],
        doc_ids: list[str] | None = None,
        ttl: int | None = None,
    ) -> None:
        """Persist retrieval results in Redis.

        Parameters
        ----------
        tenant_id, query, top_k, doc_ids
            Cache key components.
        data : list[dict]
            Serialisable list of result dicts.
        ttl : int | None
            Override TTL for this entry.  Defaults to ``default_ttl``.
        """
        if self._redis is None:
            return
        try:
            key = _cache_key(tenant_id, query, top_k, doc_ids)
            payload = json.dumps(data, separators=(",", ":"))
            await self._redis.set(key, payload, ex=ttl or self._ttl)
        except Exception as exc:
            logger.debug("RedisCache.set_retrieval failed: %s", exc)

    async def close(self) -> None:
        """Close the underlying Redis connection (best effort)."""
        if self._redis is not None:
            try:
                await self._redis.aclose()
            except Exception:
                pass
