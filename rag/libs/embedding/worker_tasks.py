"""Worker tasks for embedding and indexing operations.

These async tasks are designed to be called from:
- The ingestion worker (after chunking)
- CLI admin commands
- Background job schedulers
"""

from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.providers.base import EmbeddingProvider
from libs.embedding.indexer import IndexingService, IndexResult
from libs.embedding.service import EmbeddingService

logger = logging.getLogger("rag.embedding.worker")


def _build_services(
    db: AsyncSession, provider: EmbeddingProvider
) -> tuple[EmbeddingService, IndexingService]:
    embed_svc = EmbeddingService(provider)
    indexer = IndexingService(db, embed_svc)
    return embed_svc, indexer


async def task_embed_pending(
    db: AsyncSession,
    provider: EmbeddingProvider,
    *,
    tenant_id: UUID | None = None,
    batch_limit: int = 500,
) -> IndexResult:
    """Find and embed all chunks that have no embedding yet.

    Safe to call repeatedly — idempotent via model+version check.
    """
    _, indexer = _build_services(db, provider)
    result = await indexer.embed_pending(
        tenant_id=tenant_id, batch_limit=batch_limit
    )
    await db.commit()
    logger.info("task_embed_pending: %s", result.summary())
    return result


async def task_reembed_version(
    db: AsyncSession,
    provider: EmbeddingProvider,
    version_id: UUID,
    *,
    force: bool = True,
) -> IndexResult:
    """Re-embed all chunks for a specific document version.

    Use when switching embedding models or fixing corrupted embeddings.
    """
    _, indexer = _build_services(db, provider)
    result = await indexer.reembed_version(version_id, force=force)
    await db.commit()
    logger.info("task_reembed_version %s: %s", version_id, result.summary())
    return result


async def task_full_reindex(
    db: AsyncSession,
    provider: EmbeddingProvider,
    tenant_id: UUID,
    *,
    batch_size: int = 500,
) -> IndexResult:
    """Re-embed all chunks for an entire tenant.

    Used when migrating to a new embedding model.
    Processes in pages to avoid memory issues.
    """
    _, indexer = _build_services(db, provider)
    result = await indexer.full_reindex(tenant_id, batch_size=batch_size)
    await db.commit()
    logger.info("task_full_reindex tenant=%s: %s", tenant_id, result.summary())
    return result
