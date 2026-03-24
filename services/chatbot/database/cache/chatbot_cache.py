"""
ChatbotCache Module

Provides a singleton cache class for the chatbot service.
Attempts to use Redis; falls back to an in-memory cache when Redis is
unavailable, so the application degrades gracefully in all environments.
"""

import hashlib
import json
import logging
import time
from threading import Lock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class _MemoryCache:
    """
    Simple in-memory cache with per-entry TTL support.
    Used as a fallback when Redis is not available.
    """

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _is_expired(self, key: str) -> bool:
        exp = self._expiry.get(key)
        if exp is None:
            return False
        return time.time() > exp

    def _cleanup(self, key: str) -> None:
        self._store.pop(key, None)
        self._expiry.pop(key, None)

    # ------------------------------------------------------------------
    # Public interface (mirrors a minimal Redis client)
    # ------------------------------------------------------------------

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            if self._is_expired(key):
                self._cleanup(key)
                return None
            return self._store.get(key)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        with self._lock:
            self._store[key] = value
            if ttl is not None:
                self._expiry[key] = time.time() + ttl
            else:
                self._expiry.pop(key, None)

    def delete(self, key: str) -> None:
        with self._lock:
            self._cleanup(key)

    def keys(self, pattern: str) -> List[str]:
        """Return all non-expired keys matching a simple prefix pattern."""
        prefix = pattern.rstrip("*")
        with self._lock:
            return [
                k
                for k in list(self._store.keys())
                if k.startswith(prefix) and not self._is_expired(k)
            ]

    def flushall(self) -> None:
        with self._lock:
            self._store.clear()
            self._expiry.clear()

    def info(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "used_memory_human": f"{len(self._store)} entries",
                "connected_clients": 1,
            }

    def dbsize(self) -> int:
        with self._lock:
            return len(
                [k for k in self._store if not self._is_expired(k)]
            )


def _build_redis_client():
    """Try to create a Redis client; return None on failure."""
    try:
        import redis  # type: ignore
        from flask import current_app  # type: ignore

        url = current_app.config.get("REDIS_URL", "redis://localhost:6379/0")
        client = redis.from_url(url, decode_responses=False, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception:
        return None


# ---------------------------------------------------------------------------
# ChatbotCache – public singleton
# ---------------------------------------------------------------------------

class ChatbotCache:
    """
    Singleton cache façade for the chatbot service.

    All public methods are *class* methods so callers never need to hold a
    reference to the instance (matches the usage patterns found throughout the
    codebase).

    Supported backends (in priority order):
    1. Redis  – used when available and reachable.
    2. In-memory  – always available; does not survive process restarts.
    """

    # Default TTL values (seconds)
    TTL_CONVERSATION = 3600        # 1 hour
    TTL_USER_CONVERSATIONS = 1800  # 30 minutes
    TTL_MESSAGES = 3600            # 1 hour
    TTL_MEMORY = 7200              # 2 hours
    TTL_QUERY = 3600               # 1 hour

    _instance: Optional["ChatbotCache"] = None
    _lock = Lock()

    # ------------------------------------------------------------------
    # Singleton machinery
    # ------------------------------------------------------------------

    def __new__(cls) -> "ChatbotCache":
        with cls._lock:
            if cls._instance is None:
                obj = super().__new__(cls)
                obj._backend = None          # lazily initialised
                obj._backend_name = "none"
                cls._instance = obj
        return cls._instance

    # ------------------------------------------------------------------
    # Backend initialisation (lazy, called on first use)
    # ------------------------------------------------------------------

    @classmethod
    def _get_backend(cls):
        inst = cls.__new__(cls)
        if inst._backend is None:
            redis_client = _build_redis_client()
            if redis_client is not None:
                inst._backend = redis_client
                inst._backend_name = "redis"
                logger.info("ChatbotCache: using Redis backend")
            else:
                inst._backend = _MemoryCache()
                inst._backend_name = "memory"
                logger.info("ChatbotCache: Redis unavailable – using in-memory backend")
        return inst._backend

    # ------------------------------------------------------------------
    # Key builders
    # ------------------------------------------------------------------

    @staticmethod
    def _conv_key(conversation_id: str) -> str:
        return f"chatbot:conv:{conversation_id}"

    @staticmethod
    def _user_convs_key(user_id: str) -> str:
        return f"chatbot:user:{user_id}:convs"

    @staticmethod
    def _msgs_key(conversation_id: str) -> str:
        return f"chatbot:conv:{conversation_id}:msgs"

    @staticmethod
    def _memory_key(user_id: str) -> str:
        return f"chatbot:user:{user_id}:memories"

    @staticmethod
    def _query_key(cache_key: str) -> str:
        return f"chatbot:query:{cache_key}"

    # ------------------------------------------------------------------
    # Internal get / set / delete helpers
    # ------------------------------------------------------------------

    @classmethod
    def _get(cls, key: str) -> Optional[Any]:
        try:
            backend = cls._get_backend()
            raw = backend.get(key)
            if raw is None:
                return None
            if isinstance(raw, (bytes, bytearray)):
                return json.loads(raw.decode("utf-8"))
            if isinstance(raw, str):
                return json.loads(raw)
            return raw  # already decoded (MemoryCache stores native objects)
        except Exception as exc:
            logger.warning("Cache get error for key %s: %s", key, exc)
            return None

    @classmethod
    def _set(cls, key: str, value: Any, ttl: int) -> None:
        try:
            backend = cls._get_backend()
            if isinstance(backend, _MemoryCache):
                backend.set(key, value, ttl)
            else:
                # Redis expects bytes/str
                backend.setex(key, ttl, json.dumps(value, default=str))
        except Exception as exc:
            logger.warning("Cache set error for key %s: %s", key, exc)

    @classmethod
    def _delete(cls, key: str) -> None:
        try:
            backend = cls._get_backend()
            backend.delete(key)
        except Exception as exc:
            logger.warning("Cache delete error for key %s: %s", key, exc)

    @classmethod
    def _delete_pattern(cls, pattern: str) -> None:
        try:
            backend = cls._get_backend()
            keys = backend.keys(pattern)
            if keys:
                if isinstance(backend, _MemoryCache):
                    for k in keys:
                        backend.delete(k)
                else:
                    backend.delete(*keys)
        except Exception as exc:
            logger.warning("Cache delete pattern error for %s: %s", pattern, exc)

    # ------------------------------------------------------------------
    # Conversation cache
    # ------------------------------------------------------------------

    @classmethod
    def get_conversation(cls, conversation_id: str) -> Optional[Any]:
        return cls._get(cls._conv_key(conversation_id))

    @classmethod
    def set_conversation(cls, conversation_id: str, data: Any) -> None:
        cls._set(cls._conv_key(conversation_id), data, cls.TTL_CONVERSATION)

    @classmethod
    def invalidate_conversation(cls, conversation_id: str) -> None:
        cls._delete(cls._conv_key(conversation_id))

    # ------------------------------------------------------------------
    # User conversations list cache
    # ------------------------------------------------------------------

    @classmethod
    def get_user_conversations(cls, user_id: str) -> Optional[Any]:
        return cls._get(cls._user_convs_key(user_id))

    @classmethod
    def set_user_conversations(cls, user_id: str, data: Any) -> None:
        cls._set(cls._user_convs_key(user_id), data, cls.TTL_USER_CONVERSATIONS)

    @classmethod
    def invalidate_user_conversations(cls, user_id: str) -> None:
        cls._delete(cls._user_convs_key(user_id))

    # ------------------------------------------------------------------
    # Messages cache
    # ------------------------------------------------------------------

    @classmethod
    def get_messages(cls, conversation_id: str) -> Optional[Any]:
        return cls._get(cls._msgs_key(conversation_id))

    @classmethod
    def set_messages(cls, conversation_id: str, data: Any) -> None:
        cls._set(cls._msgs_key(conversation_id), data, cls.TTL_MESSAGES)

    @classmethod
    def invalidate_messages(cls, conversation_id: str) -> None:
        cls._delete(cls._msgs_key(conversation_id))

    # ------------------------------------------------------------------
    # User memories cache
    # ------------------------------------------------------------------

    @classmethod
    def get_user_memories(cls, user_id: str) -> Optional[Any]:
        return cls._get(cls._memory_key(user_id))

    @classmethod
    def set_user_memories(cls, user_id: str, data: Any) -> None:
        cls._set(cls._memory_key(user_id), data, cls.TTL_MEMORY)

    @classmethod
    def invalidate_user_memories(cls, user_id: str) -> None:
        cls._delete(cls._memory_key(user_id))

    # ------------------------------------------------------------------
    # Generic query-result cache
    # ------------------------------------------------------------------

    @classmethod
    def get_query_result(cls, cache_key: str) -> Optional[Any]:
        return cls._get(cls._query_key(cache_key))

    @classmethod
    def set_query_result(cls, cache_key: str, result: Any, ttl: int = TTL_QUERY) -> None:
        cls._set(cls._query_key(cache_key), result, ttl)

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    @classmethod
    def make_query_hash(cls, *args: Any, **kwargs: Any) -> str:
        """Generate a stable hash string for the given arguments."""
        payload = json.dumps({"args": args, "kwargs": kwargs}, sort_keys=True, default=str)
        return hashlib.md5(payload.encode("utf-8"), usedforsecurity=False).hexdigest()

    @classmethod
    def get_stats(cls) -> Dict[str, Any]:
        """Return cache backend statistics."""
        try:
            inst = cls.__new__(cls)
            backend = cls._get_backend()
            backend_name = inst._backend_name

            if backend_name == "redis":
                info = backend.info()
                return {
                    "backend": "redis",
                    "used_memory": info.get("used_memory_human", "unknown"),
                    "connected_clients": info.get("connected_clients", 0),
                    "keys": backend.dbsize(),
                }

            # In-memory backend
            return {
                "backend": "memory",
                "keys": backend.dbsize(),
            }
        except Exception as exc:
            return {"backend": "unknown", "error": str(exc)}

    @classmethod
    def clear_all(cls) -> None:
        """Clear the entire cache."""
        try:
            backend = cls._get_backend()
            if isinstance(backend, _MemoryCache):
                backend.flushall()
            else:
                backend.flushdb()
        except Exception as exc:
            logger.warning("Cache clear_all error: %s", exc)

    @classmethod
    def clear_user_cache(cls, user_id: str) -> None:
        """Clear all cache entries associated with a user."""
        cls.invalidate_user_conversations(user_id)
        cls.invalidate_user_memories(user_id)
        cls._delete_pattern(f"chatbot:user:{user_id}:*")
