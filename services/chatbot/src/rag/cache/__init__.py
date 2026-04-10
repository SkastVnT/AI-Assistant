"""
src.rag.cache — Caching layer for the RAG retrieval pipeline.

Exports
-------
RedisCache
    Async Redis-backed result cache used by
    :class:`~src.rag.service.RetrievalService`.
    Falls back to a no-op when the ``redis`` package is unavailable
    or the configured Redis server is unreachable.
"""
from .redis_cache import RedisCache

__all__ = ["RedisCache"]
