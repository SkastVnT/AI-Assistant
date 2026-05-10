"""Indexing service — orchestrates embedding + storage for document chunks.

Provides three core operations:
1. embed_pending()    — find unembedded chunks and embed them
2. reembed_version()  — re-embed all chunks for a specific document version
3. full_reindex()     — re-embed all chunks for an entire tenant

Also handles:
- Marking old versions as SUPERSEDED
- Updating version/job metadata after embedding
- Idempotent operations (safe to retry)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.models import (
    DocumentChunk,
    DocumentVersion,
    VersionStatus,
)
from libs.core.repositories_sql import (
    SqlDocumentChunkRepository,
    SqlDocumentVersionRepository,
)
from libs.embedding.service import EmbedResult, EmbeddingService
from libs.embedding.service import EmbeddingService, EmbedResult

logger = logging.getLogger("rag.embedding.indexer")


@dataclass
class IndexResult:
    """Summary of an indexing operation."""

    operation: str
    chunks_processed: int
    chunks_embedded: int
    chunks_skipped: int
    chunks_failed: int
    versions_superseded: int
    model: str
    version: str
    duration_ms: int | None = None

    def summary(self) -> str:
        return (
            f"[{self.operation}] "
            f"processed={self.chunks_processed}, "
            f"embedded={self.chunks_embedded}, "
            f"skipped={self.chunks_skipped}, "
            f"failed={self.chunks_failed}, "
            f"superseded={self.versions_superseded}, "
            f"model={self.model}:{self.version}"
        )


class IndexingService:
    """Orchestrates embedding generation and version management.

    Uses EmbeddingService for the actual embedding calls and
    repository layer for persistence.
    """

    def __init__(
        self,
        db: AsyncSession,
        embedding_service: EmbeddingService,
    ) -> None:
        self._db = db
        self._embed_svc = embedding_service
        self._chunk_repo = SqlDocumentChunkRepository(db)
        self._version_repo = SqlDocumentVersionRepository(db)

    async def embed_pending(
        self,
        *,
        tenant_id: UUID | None = None,
        batch_limit: int = 500,
    ) -> IndexResult:
        """Find and embed chunks that have no embedding yet.

        Args:
            tenant_id: Scope to a specific tenant (None = all tenants).
            batch_limit: Max chunks to process in one call.

        Returns:
            IndexResult summary.
        """
        t_start = _now_ms()

        chunks = await self._chunk_repo.get_unembedded(
            tenant_id=tenant_id, limit=batch_limit
        )

        if not chunks:
            return IndexResult(
                operation="embed_pending",
                chunks_processed=0, chunks_embedded=0,
                chunks_skipped=0, chunks_failed=0,
                versions_superseded=0,
                model=self._embed_svc.model_name,
                version=self._embed_svc.model_version,
                duration_ms=_elapsed_ms(t_start),
            )

        result = await self._embed_svc.embed_chunks(chunks)
        await self._db.flush()

        logger.info(
            "embed_pending: %d embedded, %d skipped, %d failed",
            result.embedded, result.skipped, result.failed,
        )

        return IndexResult(
            operation="embed_pending",
            chunks_processed=result.total_chunks,
            chunks_embedded=result.embedded,
            chunks_skipped=result.skipped,
            chunks_failed=result.failed,
            versions_superseded=0,
            model=result.model,
            version=result.version,
            duration_ms=_elapsed_ms(t_start),
        )

    async def reembed_version(
        self,
        version_id: UUID,
        *,
        force: bool = True,
    ) -> IndexResult:
        """Re-embed all chunks for a specific document version.

        Args:
            version_id: The DocumentVersion to re-embed.
            force: If True, re-embed even if model+version match.

        Returns:
            IndexResult summary.
        """
        t_start = _now_ms()

        version = await self._version_repo.get_by_id(version_id)
        if not version:
            raise ValueError(f"DocumentVersion {version_id} not found")

        chunks = await self._chunk_repo.get_by_version_for_reembed(version_id)
        if not chunks:
            return IndexResult(
                operation="reembed_version",
                chunks_processed=0, chunks_embedded=0,
                chunks_skipped=0, chunks_failed=0,
                versions_superseded=0,
                model=self._embed_svc.model_name,
                version=self._embed_svc.model_version,
                duration_ms=_elapsed_ms(t_start),
            )

        result = await self._embed_svc.embed_chunks(chunks, force=force)
        await self._db.flush()

        # Update version metadata with embedding info
        version.metadata_ = {
            **version.metadata_,
            "last_embed_model": result.model,
            "last_embed_version": result.version,
            "last_embed_at": datetime.now(UTC).isoformat(),
            "embed_results": {
                "embedded": result.embedded,
                "skipped": result.skipped,
                "failed": result.failed,
            },
        }
        await self._db.flush()

        logger.info(
            "reembed_version %s: %d embedded, %d failed",
            version_id, result.embedded, result.failed,
        )

        return IndexResult(
            operation="reembed_version",
            chunks_processed=result.total_chunks,
            chunks_embedded=result.embedded,
            chunks_skipped=result.skipped,
            chunks_failed=result.failed,
            versions_superseded=0,
            model=result.model,
            version=result.version,
            duration_ms=_elapsed_ms(t_start),
        )

    async def full_reindex(
        self,
        tenant_id: UUID,
        *,
        batch_size: int = 500,
    ) -> IndexResult:
        """Re-embed all chunks for a tenant, processing in pages.

        Args:
            tenant_id: Tenant to reindex.
            batch_size: Chunks per page.

        Returns:
            Aggregated IndexResult.
        """
        t_start = _now_ms()
        total_embedded = 0
        total_skipped = 0
        total_failed = 0
        total_processed = 0
        offset = 0

        while True:
            chunks = await self._chunk_repo.get_all_by_tenant(
                tenant_id, limit=batch_size, offset=offset
            )
            if not chunks:
                break

            result = await self._embed_svc.embed_chunks(chunks, force=True)
            await self._db.flush()

            total_processed += result.total_chunks
            total_embedded += result.embedded
            total_skipped += result.skipped
            total_failed += result.failed
            offset += batch_size

            logger.info(
                "full_reindex tenant=%s: page offset=%d, embedded=%d",
                tenant_id, offset, result.embedded,
            )

        logger.info(
            "full_reindex tenant=%s complete: %d total, %d embedded, %d failed",
            tenant_id, total_processed, total_embedded, total_failed,
        )

        return IndexResult(
            operation="full_reindex",
            chunks_processed=total_processed,
            chunks_embedded=total_embedded,
            chunks_skipped=total_skipped,
            chunks_failed=total_failed,
            versions_superseded=0,
            model=self._embed_svc.model_name,
            version=self._embed_svc.model_version,
            duration_ms=_elapsed_ms(t_start),
        )

    async def mark_old_versions_superseded(
        self,
        document_id: UUID,
        current_version_id: UUID,
    ) -> int:
        """Mark all older READY versions of a document as SUPERSEDED.

        Call this after a new version transitions to READY.

        Returns:
            Number of versions marked superseded.
        """
        count = await self._version_repo.mark_superseded(
            document_id, exclude_version_id=current_version_id
        )
        if count:
            logger.info(
                "Marked %d old versions superseded for document %s (current=%s)",
                count, document_id, current_version_id,
            )
        return count

    async def embed_and_finalize_version(
        self,
        chunks: list[DocumentChunk],
        version: DocumentVersion,
    ) -> EmbedResult:
        """Embed chunks for a version, update status, mark old versions superseded.

        This is the main entry point used by the ingestion pipeline.
        """
        result = await self._embed_svc.embed_chunks(chunks)

        if result.failed > 0 and result.embedded == 0:
            version.status = VersionStatus.ERROR
            version.error_message = (
                f"All {result.failed} chunks failed to embed "
                f"(model={result.model}, version={result.version})"
            )
        else:
            version.status = VersionStatus.READY
            version.chunk_count = len(chunks)
            version.metadata_ = {
                **version.metadata_,
                "embed_model": result.model,
                "embed_version": result.version,
                "embed_results": {
                    "embedded": result.embedded,
                    "failed": result.failed,
                    "skipped": result.skipped,
                },
            }

            # Mark old versions as superseded
            await self.mark_old_versions_superseded(
                version.document_id, version.id
            )

        await self._db.flush()
        return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_ms() -> float:
    return datetime.now(UTC).timestamp() * 1000


def _elapsed_ms(start_ms: float) -> int:
    return int(datetime.now(UTC).timestamp() * 1000 - start_ms)
