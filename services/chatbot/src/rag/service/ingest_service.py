"""
End-to-end document ingestion service.

Flow
----
1. Upload raw bytes to object storage (MinIO / local fallback).
2. Parse the file into pages via the appropriate ``DocumentParser``.
3. Split pages into overlapping chunks (``RecursiveTextChunker``).
4. Batch-embed all chunks.
5. Write ``RagDocument`` + ``RagChunk`` rows inside a single transaction.

Returns
-------
``IngestResult`` with ``document_id``, ``num_chunks``, ``object_path``.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import func, select

from core.rag_settings import get_rag_settings
from src.rag.db.base import get_session_factory
from src.rag.db.models import RagChunk, RagDocument, RagImageChunk
from src.rag.embeddings.base import EmbeddingProvider
from src.rag.embeddings.factory import create_embedding_provider
from src.rag.ingest.chunking_pkg import chunk_pages
from src.rag.ingest.parsers import get_parser
from src.rag.security.policies import get_rag_policies
from src.rag.storage.minio_client import RagFileStore

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Result DTO
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class IngestResult:
    document_id: uuid.UUID
    num_chunks: int
    object_path: str


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class IngestError(Exception):
    """Raised when an ingestion step fails irrecoverably."""


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------

# Maximum texts per embedding API call (avoids request-size limits).
_EMBED_BATCH_SIZE = 64


class IngestService:
    """Orchestrates full ingestion: store → parse → chunk → embed → persist.

    Parameters
    ----------
    file_store : RagFileStore | None
        Custom storage backend.  ``None`` → use the default ``RagFileStore()``.
    embed_batch_size : int
        Number of chunks to embed per API call.
    max_chars : int
        Maximum characters per text chunk.
    overlap_chars : int
        Overlap between consecutive chunks.
    """

    def __init__(
        self,
        *,
        file_store: RagFileStore | None = None,
        embedder: EmbeddingProvider | None = None,
        embed_batch_size: int = _EMBED_BATCH_SIZE,
        max_chars: int = 512,
        overlap_chars: int = 64,
    ) -> None:
        self._store = file_store or RagFileStore()
        self._batch_size = embed_batch_size
        self._max_chars = max_chars
        self._overlap_chars = overlap_chars
        # Embedder is created lazily on first batch-embed call so that
        # construction never fails in environments without API credentials
        # (e.g. unit tests that exercise policy checks before any embedding).
        self._embedder: EmbeddingProvider | None = embedder

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def ingest(
        self,
        *,
        tenant_id: str,
        file_bytes: bytes,
        filename: str,
        mime_type: str | None = None,
        title: str | None = None,
        source_uri: str | None = None,
        source_type: str = "upload",
    ) -> IngestResult:
        """Ingest a single file end-to-end.

        All database writes happen inside one transaction; on failure
        everything is rolled back (the object-store blob is cleaned up
        on a best-effort basis).
        """
        if not file_bytes:
            raise IngestError("Empty file")
        if not tenant_id:
            raise IngestError("tenant_id is required")

        # ── Policy: max file size ─────────────────────────────────────
        policies = get_rag_policies()
        if len(file_bytes) > policies.max_file_bytes:
            raise IngestError(
                f"File too large: {len(file_bytes)} bytes "
                f"(limit {policies.max_file_bytes})"
            )

        # ── Policy: max documents per tenant ──────────────────────────
        await self._check_tenant_doc_limit(tenant_id, policies.max_documents_per_tenant)

        doc_id = uuid.uuid4()
        object_path = f"{tenant_id}/{doc_id!s}/{filename}"

        # 1 ── Upload raw file to storage ──────────────────────────────
        try:
            self._store.upload(file_bytes, object_path)
        except Exception as exc:
            raise IngestError(f"Storage upload failed: {exc}") from exc

        try:
            # 2 ── Image branch (CLIP multimodal) ──────────────────────
            if self._is_image(mime_type, filename):
                return await self._ingest_image(
                    doc_id=doc_id,
                    tenant_id=tenant_id,
                    file_bytes=file_bytes,
                    filename=filename,
                    mime_type=mime_type,
                    title=title or filename,
                    source_uri=source_uri,
                    source_type=source_type,
                    object_path=object_path,
                )

            # 2 ── Parse ───────────────────────────────────────────────
            parser = get_parser(mime_type=mime_type, filename=filename)
            parsed = parser.parse(file_bytes, source=filename)

            resolved_title = title or parsed.metadata.get("title") or filename

            # 3 ── Chunk ──────────────────────────────────────────────
            pages_dicts = [
                {
                    "text": p.text,
                    "page_number": p.page_number,
                    "metadata": p.metadata,
                }
                for p in parsed.pages
            ]
            chunks = chunk_pages(
                pages_dicts,
                max_chars=self._max_chars,
                overlap_chars=self._overlap_chars,
            )
            if not chunks:
                raise IngestError(
                    "Parsing produced no text chunks — file may be empty or unsupported"
                )

            # ── Policy: max chunks per document ───────────────────────
            if len(chunks) > policies.max_chunks_per_document:
                chunks = chunks[: policies.max_chunks_per_document]
                logger.warning(
                    "Truncated chunks to %d (policy limit) for %s",
                    policies.max_chunks_per_document,
                    filename,
                )

            logger.info(
                "Parsed %s → %d pages, %d chunks",
                filename,
                parsed.page_count,
                len(chunks),
            )

            # 4 ── Embed (batched) ────────────────────────────────────
            texts = [c.text for c in chunks]
            embeddings = self._batch_embed(texts)

            # 5 ── Persist (single transaction) ───────────────────────
            await self._persist(
                doc_id=doc_id,
                tenant_id=tenant_id,
                source_type=source_type,
                source_uri=source_uri,
                title=resolved_title,
                mime_type=parsed.mime_type,
                object_path=object_path,
                chunks=chunks,
                embeddings=embeddings,
            )

        except IngestError:
            self._cleanup_storage(object_path)
            raise
        except Exception as exc:
            self._cleanup_storage(object_path)
            raise IngestError(f"Ingestion failed: {exc}") from exc

        logger.info(
            "Ingested doc=%s  chunks=%d  storage=%s",
            doc_id,
            len(chunks),
            object_path,
        )
        return IngestResult(
            document_id=doc_id,
            num_chunks=len(chunks),
            object_path=object_path,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_image(mime_type: str | None, filename: str) -> bool:
        if mime_type and mime_type.lower().startswith("image/"):
            return True
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        return ext in {"png", "jpg", "jpeg", "gif", "webp", "bmp"}

    async def _ingest_image(
        self,
        *,
        doc_id: uuid.UUID,
        tenant_id: str,
        file_bytes: bytes,
        filename: str,
        mime_type: str | None,
        title: str,
        source_uri: str | None,
        source_type: str,
        object_path: str,
    ) -> IngestResult:
        """Ingest a single image: store → CLIP embed → persist.

        Skips text parsing/chunking. Requires the CLIP sidecar (image RAG).
        """
        import base64

        from core import clip_adapter

        if not clip_adapter.is_enabled():
            raise IngestError(
                "Image ingest requires RAG_IMAGE_ENABLED=true and a running "
                "CLIP sidecar."
            )

        b64 = base64.b64encode(file_bytes).decode("ascii")
        try:
            vectors = clip_adapter.embed_images([b64])
        except clip_adapter.ClipUnavailableError as exc:
            raise IngestError(f"CLIP image embedding failed: {exc}") from exc
        if not vectors:
            raise IngestError("CLIP sidecar returned no image embedding")

        await self._persist_image(
            doc_id=doc_id,
            tenant_id=tenant_id,
            source_type=source_type,
            source_uri=source_uri,
            title=title,
            mime_type=mime_type or "image/*",
            object_path=object_path,
            embedding=vectors[0],
            caption=title,
        )

        logger.info(
            "Ingested image doc=%s  storage=%s", doc_id, object_path
        )
        return IngestResult(
            document_id=doc_id, num_chunks=1, object_path=object_path
        )

    async def _persist_image(
        self,
        *,
        doc_id: uuid.UUID,
        tenant_id: str,
        source_type: str,
        source_uri: str | None,
        title: str,
        mime_type: str | None,
        object_path: str,
        embedding: list[float],
        caption: str | None,
    ) -> None:
        """Write RagDocument + RagImageChunk rows in one atomic transaction."""
        session_factory = get_session_factory()

        async with session_factory() as session, session.begin():
            doc = RagDocument(
                id=doc_id,
                tenant_id=tenant_id,
                source_type=source_type,
                source_uri=source_uri,
                title=title,
                mime_type=mime_type,
                object_path=object_path,
            )
            session.add(doc)
            session.add(
                RagImageChunk(
                    tenant_id=tenant_id,
                    document_id=doc_id,
                    object_path=object_path,
                    caption=caption,
                    embedding=embedding,
                    metadata_json={},
                )
            )

    def _batch_embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts in batches to respect API size limits."""
        if self._embedder is None:
            cfg = get_rag_settings()
            self._embedder = create_embedding_provider(
                provider=cfg.embed_provider,
                model=cfg.embed_model,
                dim=cfg.embed_dim,
            )
        all_vectors: list[list[float]] = []
        for start in range(0, len(texts), self._batch_size):
            batch = texts[start : start + self._batch_size]
            vectors = self._embedder.embed_texts(batch)
            all_vectors.extend(vectors)
        return all_vectors

    async def _persist(
        self,
        *,
        doc_id: uuid.UUID,
        tenant_id: str,
        source_type: str,
        source_uri: str | None,
        title: str,
        mime_type: str | None,
        object_path: str,
        chunks: list,
        embeddings: list[list[float]],
    ) -> None:
        """Write RagDocument + RagChunk rows in one atomic transaction."""
        session_factory = get_session_factory()

        async with session_factory() as session, session.begin():
            doc = RagDocument(
                id=doc_id,
                tenant_id=tenant_id,
                source_type=source_type,
                source_uri=source_uri,
                title=title,
                mime_type=mime_type,
                object_path=object_path,
            )
            session.add(doc)

            for chunk, vector in zip(chunks, embeddings):
                row = RagChunk(
                    tenant_id=tenant_id,
                    document_id=doc_id,
                    chunk_index=chunk.chunk_index,
                    content=chunk.text,
                    embedding=vector,
                    metadata_json=chunk.metadata,
                )
                session.add(row)

    async def _check_tenant_doc_limit(
        self,
        tenant_id: str,
        max_docs: int,
    ) -> None:
        """Raise ``IngestError`` if the tenant already has *max_docs*."""
        session_factory = get_session_factory()
        async with session_factory() as session:
            result = await session.execute(
                select(func.count())
                .select_from(RagDocument)
                .where(
                    RagDocument.tenant_id == tenant_id,
                ),
            )
            count = result.scalar_one()
        if count >= max_docs:
            raise IngestError(
                f"Tenant '{tenant_id}' has reached the document limit ({max_docs})"
            )

    def _cleanup_storage(self, object_path: str) -> None:
        """Best-effort removal of the uploaded blob on failure."""
        try:
            self._store.delete(object_path)
        except Exception:
            logger.warning(
                "Failed to clean up object %s after ingestion error",
                object_path,
                exc_info=True,
            )
