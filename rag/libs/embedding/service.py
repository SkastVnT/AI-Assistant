"""Embedding service — batch embed text chunks via provider abstraction.

Handles:
- Batch splitting (respects API limits)
- Retry with exponential backoff per batch
- Idempotency (skips chunks that already have matching model+version)
- Tracks embedding_model and embedding_version metadata
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from libs.core.models import DocumentChunk
from libs.core.providers.base import EmbeddingProvider
from libs.core.settings import get_settings

logger = logging.getLogger("rag.embedding.service")


@dataclass(frozen=True)
class EmbedResult:
    """Summary of a batch embedding operation."""

    total_chunks: int
    embedded: int
    skipped: int
    failed: int
    model: str
    version: str


class EmbeddingService:
    """Orchestrates embedding generation for document chunks.

    Features:
    - Configurable batch size
    - Exponential backoff retry per batch
    - Idempotent: skips chunks already embedded with same model+version
    - Returns structured result for observability
    """

    def __init__(
        self,
        provider: EmbeddingProvider,
        *,
        batch_size: int | None = None,
        max_retries: int | None = None,
        model_name: str | None = None,
        model_version: str | None = None,
    ) -> None:
        settings = get_settings()
        self._provider = provider
        self._batch_size = batch_size or settings.embedding.batch_size
        self._max_retries = max_retries or settings.embedding.max_retries
        self._model_name = model_name or settings.embedding.model
        self._model_version = model_version or settings.embedding.version

    @property
    def model_name(self) -> str:
        return self._model_name

    @property
    def model_version(self) -> str:
        return self._model_version

    def _should_skip(self, chunk: DocumentChunk) -> bool:
        """Check if chunk already has an embedding with matching model+version."""
        return (
            chunk.embedding is not None
            and chunk.embedding_model == self._model_name
            and chunk.embedding_version == self._model_version
        )

    async def embed_chunks(
        self,
        chunks: list[DocumentChunk],
        *,
        force: bool = False,
    ) -> EmbedResult:
        """Generate embeddings for a list of chunks in-place.

        Args:
            chunks: DocumentChunk objects to embed. Modified in-place.
            force: If True, re-embed even if already matching.

        Returns:
            EmbedResult with counts.
        """
        if not chunks:
            return EmbedResult(
                total_chunks=0, embedded=0, skipped=0, failed=0,
                model=self._model_name, version=self._model_version,
            )

        # Filter to those needing embedding
        to_embed: list[DocumentChunk] = []
        skipped = 0
        for chunk in chunks:
            if not force and self._should_skip(chunk):
                skipped += 1
            else:
                to_embed.append(chunk)

        if not to_embed:
            return EmbedResult(
                total_chunks=len(chunks), embedded=0, skipped=skipped, failed=0,
                model=self._model_name, version=self._model_version,
            )

        # Process in batches
        embedded = 0
        failed = 0
        for i in range(0, len(to_embed), self._batch_size):
            batch = to_embed[i : i + self._batch_size]
            texts = [c.content for c in batch]

            embeddings = await self._embed_with_retry(texts)
            if embeddings is None:
                failed += len(batch)
                logger.error(
                    "Batch %d-%d failed after all retries",
                    i, i + len(batch),
                )
                continue

            for chunk, vector in zip(batch, embeddings, strict=True):
                chunk.embedding = vector
                chunk.embedding_model = self._model_name
                chunk.embedding_version = self._model_version
                embedded += 1

        logger.info(
            "Embedding complete: %d embedded, %d skipped, %d failed (model=%s, version=%s)",
            embedded, skipped, failed, self._model_name, self._model_version,
        )

        return EmbedResult(
            total_chunks=len(chunks),
            embedded=embedded,
            skipped=skipped,
            failed=failed,
            model=self._model_name,
            version=self._model_version,
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed raw texts with retry. Returns list of vectors."""
        all_embeddings: list[list[float]] = []
        for i in range(0, len(texts), self._batch_size):
            batch = texts[i : i + self._batch_size]
            embeddings = await self._embed_with_retry(batch)
            if embeddings is None:
                raise RuntimeError(
                    f"Embedding batch {i}-{i + len(batch)} failed after {self._max_retries} retries"
                )
            all_embeddings.extend(embeddings)
        return all_embeddings

    async def _embed_with_retry(
        self, texts: list[str]
    ) -> list[list[float]] | None:
        """Call provider.embed with exponential backoff retry."""
        for attempt in range(1, self._max_retries + 1):
            try:
                return await self._provider.embed(texts)
            except Exception:
                if attempt == self._max_retries:
                    logger.exception(
                        "Embed failed after %d attempts (%d texts)",
                        attempt, len(texts),
                    )
                    return None
                wait = min(2 ** attempt, 30)
                logger.warning(
                    "Embed attempt %d/%d failed, retrying in %ds",
                    attempt, self._max_retries, wait,
                )
                await asyncio.sleep(wait)
        return None
