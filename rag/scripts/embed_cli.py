"""CLI admin commands for embedding and indexing operations.

Usage:
    # Embed all pending (unembedded) chunks
    python -m scripts.embed_cli embed-pending

    # Embed pending for a specific tenant
    python -m scripts.embed_cli embed-pending --tenant-id <uuid>

    # Re-embed all chunks for a document version
    python -m scripts.embed_cli reembed-version <version-id>

    # Full reindex for a tenant (re-embed everything)
    python -m scripts.embed_cli full-reindex <tenant-id>

    # Dry run — show what would be done without making changes
    python -m scripts.embed_cli embed-pending --dry-run
"""

from __future__ import annotations

import argparse
import asyncio
import logging
from uuid import UUID

from libs.core.database import async_session_factory
from libs.core.providers.factory import get_embedding_provider
from libs.core.repositories_sql import SqlDocumentChunkRepository
from libs.embedding.indexer import IndexingService
from libs.embedding.service import EmbeddingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
)
logger = logging.getLogger("rag.cli.embed")


async def cmd_embed_pending(
    tenant_id: UUID | None = None,
    batch_limit: int = 500,
    dry_run: bool = False,
) -> None:
    """Embed all chunks that don't have embeddings yet."""
    async with async_session_factory() as db:
        chunk_repo = SqlDocumentChunkRepository(db)
        chunks = await chunk_repo.get_unembedded(
            tenant_id=tenant_id, limit=batch_limit
        )

        if not chunks:
            logger.info("No unembedded chunks found.")
            return

        logger.info("Found %d unembedded chunks", len(chunks))

        if dry_run:
            logger.info("[DRY RUN] Would embed %d chunks. Exiting.", len(chunks))
            return

        provider = get_embedding_provider()
        embed_svc = EmbeddingService(provider)
        indexer = IndexingService(db, embed_svc)

        result = await indexer.embed_pending(
            tenant_id=tenant_id, batch_limit=batch_limit
        )
        await db.commit()

        logger.info("Result: %s", result.summary())
        if result.chunks_failed > 0:
            logger.warning("%d chunks failed to embed!", result.chunks_failed)


async def cmd_reembed_version(
    version_id: UUID,
    force: bool = True,
    dry_run: bool = False,
) -> None:
    """Re-embed all chunks for a document version."""
    async with async_session_factory() as db:
        chunk_repo = SqlDocumentChunkRepository(db)
        chunks = await chunk_repo.get_by_version_for_reembed(version_id)

        if not chunks:
            logger.info("No chunks found for version %s", version_id)
            return

        logger.info(
            "Found %d chunks for version %s", len(chunks), version_id
        )

        if dry_run:
            logger.info(
                "[DRY RUN] Would re-embed %d chunks. Exiting.", len(chunks)
            )
            return

        provider = get_embedding_provider()
        embed_svc = EmbeddingService(provider)
        indexer = IndexingService(db, embed_svc)

        result = await indexer.reembed_version(version_id, force=force)
        await db.commit()

        logger.info("Result: %s", result.summary())


async def cmd_full_reindex(
    tenant_id: UUID,
    batch_size: int = 500,
    dry_run: bool = False,
) -> None:
    """Re-embed all chunks for an entire tenant."""
    async with async_session_factory() as db:
        # Count total chunks for the tenant
        from sqlalchemy import func, select

        from libs.core.models import DocumentChunk

        total = await db.scalar(
            select(func.count())
            .where(DocumentChunk.tenant_id == tenant_id)
        ) or 0

        if total == 0:
            logger.info("No chunks found for tenant %s", tenant_id)
            return

        logger.info(
            "Found %d total chunks for tenant %s", total, tenant_id
        )

        if dry_run:
            logger.info(
                "[DRY RUN] Would re-embed %d chunks. Exiting.", total
            )
            return

        provider = get_embedding_provider()
        embed_svc = EmbeddingService(provider)
        indexer = IndexingService(db, embed_svc)

        result = await indexer.full_reindex(tenant_id, batch_size=batch_size)
        await db.commit()

        logger.info("Result: %s", result.summary())
        if result.chunks_failed > 0:
            logger.warning("%d chunks failed!", result.chunks_failed)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG Embedding & Indexing CLI",
        prog="python -m scripts.embed_cli",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # embed-pending
    ep = sub.add_parser("embed-pending", help="Embed all unembedded chunks")
    ep.add_argument("--tenant-id", type=str, default=None, help="Scope to tenant UUID")
    ep.add_argument("--batch-limit", type=int, default=500, help="Max chunks per run")
    ep.add_argument("--dry-run", action="store_true", help="Show counts without embedding")

    # reembed-version
    rv = sub.add_parser("reembed-version", help="Re-embed chunks for a version")
    rv.add_argument("version_id", type=str, help="DocumentVersion UUID")
    rv.add_argument("--no-force", action="store_true", help="Skip already-matching embeddings")
    rv.add_argument("--dry-run", action="store_true", help="Show counts without embedding")

    # full-reindex
    fr = sub.add_parser("full-reindex", help="Re-embed all chunks for a tenant")
    fr.add_argument("tenant_id", type=str, help="Tenant UUID")
    fr.add_argument("--batch-size", type=int, default=500, help="Chunks per page")
    fr.add_argument("--dry-run", action="store_true", help="Show counts without embedding")

    args = parser.parse_args()

    if args.command == "embed-pending":
        tid = UUID(args.tenant_id) if args.tenant_id else None
        asyncio.run(
            cmd_embed_pending(
                tenant_id=tid,
                batch_limit=args.batch_limit,
                dry_run=args.dry_run,
            )
        )

    elif args.command == "reembed-version":
        asyncio.run(
            cmd_reembed_version(
                version_id=UUID(args.version_id),
                force=not args.no_force,
                dry_run=args.dry_run,
            )
        )

    elif args.command == "full-reindex":
        asyncio.run(
            cmd_full_reindex(
                tenant_id=UUID(args.tenant_id),
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
        )


if __name__ == "__main__":
    main()
