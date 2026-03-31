"""
Centralised RAG settings loaded from environment variables.

When RAG_ENABLED is false (the default) every helper in this module
returns safe no-op values and the chatbot behaves exactly as before.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache


def _bool(val: str) -> bool:
    return val.strip().lower() in ("true", "1", "yes")


@dataclass(frozen=True, slots=True)
class RAGSettings:
    """Immutable, env-driven RAG configuration."""

    # ── Feature flag ───────────────────────────────────────────────────
    enabled: bool = False

    # ── Vector DB ──────────────────────────────────────────────────────
    database_url: str = "sqlite+aiosqlite:///./rag.db"

    # ── Embedding ──────────────────────────────────────────────────────
    embed_provider: str = "openai"       # openai | gemini
    embed_model: str = "text-embedding-3-small"
    embed_dim: int = 1536

    # ── Retrieval ──────────────────────────────────────────────────────
    top_k: int = 5
    min_score: float = 0.3

    # ── Redis (cache / pub-sub) ────────────────────────────────────────
    redis_url: str = "redis://localhost:6379/0"

    # ── MinIO / S3 (raw file storage) ──────────────────────────────────
    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket: str = "rag-files"

    # ── Cache ──────────────────────────────────────────────────────────
    cache_ttl: int = 3600  # seconds


@lru_cache(maxsize=1)
def get_rag_settings() -> RAGSettings:
    """Build settings once from the current environment.

    Call ``get_rag_settings.cache_clear()`` in tests to reload.
    """
    return RAGSettings(
        enabled=_bool(os.getenv("RAG_ENABLED", "false")),
        database_url=os.getenv("RAG_DATABASE_URL", "sqlite+aiosqlite:///./rag.db"),
        embed_provider=os.getenv("RAG_EMBED_PROVIDER", "openai"),
        embed_model=os.getenv("RAG_EMBED_MODEL", "text-embedding-3-small"),
        embed_dim=int(os.getenv("RAG_EMBED_DIM", "1536")),
        top_k=int(os.getenv("RAG_TOP_K", "5")),
        min_score=float(os.getenv("RAG_MIN_SCORE", "0.3")),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        minio_endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        minio_access_key=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        minio_secret_key=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        minio_bucket=os.getenv("MINIO_BUCKET", "rag-files"),
        cache_ttl=int(os.getenv("RAG_CACHE_TTL", "3600")),
    )
