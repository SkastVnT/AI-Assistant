"""Ingestion pipeline — Parse-Transform-Index architecture.

Pipeline stages (run by the worker, not the API):
    1. Fetch / Load    — download raw file from MinIO
    2. Parse           — extract structured content via parser adapters
    3. Normalize       — clean text, normalize unicode
    4. Extract metadata — derive title, word count, page count, etc.
    5. Persist         — store raw text + structured parse result
    6. Chunk & Index   — chunk → embed → persist DocumentChunks

API-facing entrypoint:
    enqueue_document() — validates, uploads to MinIO, creates DB records, returns job.
"""

from __future__ import annotations

import hashlib
import io
import json
import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.models import (
    Document,
    DocumentChunk,
    DocumentVersion,
    IngestionJob,
    JobStatus,
    SensitivityLevel,
    VersionStatus,
)
from libs.core.providers.base import EmbeddingProvider
from libs.core.settings import get_settings
from libs.core.storage import get_storage_client
from libs.embedding.indexer import IndexingService
from libs.embedding.service import EmbeddingService
from libs.ingestion.chunker import chunk_text
from libs.ingestion.metadata_extractor import extract_metadata
from libs.ingestion.normalizer import normalize_parse_result
from libs.ingestion.parsers.registry import parse_document

logger = logging.getLogger("rag.ingestion.pipeline")


# ====================================================================
# Stage 0 — Enqueue (called from API layer)
# ====================================================================


async def enqueue_document(
    db: AsyncSession,
    *,
    tenant_id: uuid.UUID,
    document_id: uuid.UUID | None = None,
    title: str,
    filename: str,
    content: bytes,
    content_type: str | None = None,
    author: str | None = None,
    sensitivity_level: str = "internal",
    language: str = "en",
    tags: list[str] | None = None,
    metadata: dict | None = None,
) -> tuple[Document, DocumentVersion, IngestionJob]:
    """Validate input, upload raw file, create DB records, enqueue job.

    Returns (document, version, job) with job.status == QUEUED.
    The worker picks up the job and runs stages 1-6.
    """
    checksum = hashlib.sha256(content).hexdigest()

    # --- Document (logical identity) ---
    if document_id:
        doc = await db.get(Document, document_id)
        if not doc or doc.tenant_id != tenant_id:
            raise ValueError("Document not found or tenant mismatch")
    else:
        doc = Document(
            tenant_id=tenant_id,
            title=title,
            author=author,
            sensitivity_level=SensitivityLevel(sensitivity_level),
            language=language,
            tags=tags or [],
            metadata_=metadata or {},
        )
        db.add(doc)
        await db.flush()

    # --- Dedup check at version level ---
    existing = await db.execute(
        select(DocumentVersion).where(
            DocumentVersion.document_id == doc.id,
            DocumentVersion.checksum == checksum,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(
            f"Version with identical content already exists (checksum: {checksum[:12]}...)"
        )

    # --- Upload raw file to MinIO ---
    settings = get_settings()
    storage = get_storage_client()
    storage_key = f"documents/{tenant_id}/{doc.id}/{uuid.uuid4()}/{filename}"

    storage.put_object(
        bucket_name=settings.minio.bucket,
        object_name=storage_key,
        data=io.BytesIO(content),
        length=len(content),
        content_type=content_type or "application/octet-stream",
    )

    # --- Version number ---
    max_ver = await db.scalar(
        select(func.max(DocumentVersion.version_number)).where(
            DocumentVersion.document_id == doc.id
        )
    )
    next_ver = (max_ver or 0) + 1

    # --- Create DocumentVersion (PENDING) ---
    version = DocumentVersion(
        tenant_id=tenant_id,
        document_id=doc.id,
        version_number=next_ver,
        storage_key=storage_key,
        filename=filename,
        content_type=content_type,
        file_size_bytes=len(content),
        checksum=checksum,
        status=VersionStatus.PENDING,
        metadata_=metadata or {},
    )
    db.add(version)
    await db.flush()

    # --- Create IngestionJob (QUEUED) ---
    job = IngestionJob(
        tenant_id=tenant_id,
        version_id=version.id,
        status=JobStatus.QUEUED,
    )
    db.add(job)
    await db.flush()

    logger.info(
        "Enqueued ingestion job %s for %s (version %d)",
        job.id,
        filename,
        next_ver,
    )
    return doc, version, job


# ====================================================================
# Stages 1-6 — Executed by the worker
# ====================================================================


async def process_ingestion_job(
    db: AsyncSession,
    embedding_provider: EmbeddingProvider,
    job: IngestionJob,
) -> None:
    """Run the full ingestion pipeline for one job.

    Mutates job and its version in-place (caller must commit).
    """
    settings = get_settings()

    # Transition: QUEUED/RUNNING → RUNNING
    job.status = JobStatus.RUNNING
    job.started_at = datetime.now(UTC)
    job.metadata_ = {**job.metadata_, "current_stage": "fetch"}
    await db.flush()

    version = await db.get(DocumentVersion, job.version_id)
    if not version:
        _fail_job(job, "DocumentVersion not found")
        return

    doc = await db.get(Document, version.document_id)
    if not doc:
        _fail_job(job, "Document not found")
        return

    version.status = VersionStatus.PROCESSING
    await db.flush()

    try:
        # ── Stage 1: Fetch / Load ────────────────────────────────
        job.metadata_ = {**job.metadata_, "current_stage": "fetch"}
        await db.flush()

        storage = get_storage_client()
        response = storage.get_object(settings.minio.bucket, version.storage_key)
        content = response.read()
        response.close()
        response.release_conn()

        logger.info("Stage 1 (fetch): %d bytes from %s", len(content), version.storage_key)

        # ── Stage 2: Parse ───────────────────────────────────────
        job.metadata_ = {**job.metadata_, "current_stage": "parse"}
        await db.flush()

        parse_result = parse_document(content, version.filename)
        logger.info(
            "Stage 2 (parse): %d elements extracted", len(parse_result.elements)
        )

        # ── Stage 3: Normalize ───────────────────────────────────
        job.metadata_ = {**job.metadata_, "current_stage": "normalize"}
        await db.flush()

        parse_result = normalize_parse_result(parse_result)

        # ── Stage 4: Extract metadata ────────────────────────────
        job.metadata_ = {**job.metadata_, "current_stage": "extract_metadata"}
        await db.flush()

        extracted_meta = extract_metadata(parse_result, version.filename)
        # Merge extracted metadata into version metadata
        version.metadata_ = {**version.metadata_, **extracted_meta}

        # ── Stage 5: Persist raw text + structured representation ─
        job.metadata_ = {**job.metadata_, "current_stage": "persist"}
        await db.flush()

        version.raw_text = parse_result.raw_text
        version.parsed_content = parse_result.to_dict()

        # Upload structured parse result to MinIO as artifact
        artifact_key = version.storage_key.rsplit("/", 1)[0] + "/parsed.json"
        artifact_bytes = json.dumps(
            parse_result.to_dict(), ensure_ascii=False
        ).encode("utf-8")
        storage.put_object(
            bucket_name=settings.minio.bucket,
            object_name=artifact_key,
            data=io.BytesIO(artifact_bytes),
            length=len(artifact_bytes),
            content_type="application/json",
        )
        logger.info("Stage 5 (persist): raw text + parsed JSON stored")

        # ── Stage 6: Chunk & Index ───────────────────────────────
        job.metadata_ = {**job.metadata_, "current_stage": "chunk_index"}
        await db.flush()

        chunks = chunk_text(parse_result.raw_text)
        job.chunks_total = len(chunks)

        if not chunks:
            version.status = VersionStatus.READY
            version.chunk_count = 0
            _complete_job(job)
            return

        # Build DocumentChunk objects with denormalized metadata
        db_chunks: list[DocumentChunk] = []
        for chunk in chunks:
            db_chunk = DocumentChunk(
                tenant_id=doc.tenant_id,
                document_id=doc.id,
                version_id=version.id,
                chunk_index=chunk.index,
                content=chunk.content,
                token_count=chunk.token_count,
                sensitivity_level=doc.sensitivity_level,
                language=doc.language,
                tags=doc.tags,
                metadata_=chunk.metadata,
            )
            db.add(db_chunk)
            db_chunks.append(db_chunk)

        await db.flush()

        # Embed via EmbeddingService + IndexingService
        embed_svc = EmbeddingService(embedding_provider)
        indexer = IndexingService(db, embed_svc)
        embed_result = await indexer.embed_and_finalize_version(db_chunks, version)

        job.chunks_processed = embed_result.embedded + embed_result.skipped
        _complete_job(job)
        logger.info(
            "Stage 6 (chunk_index): %d chunks created, %d embedded for version %s",
            len(chunks), embed_result.embedded, version.id,
        )

    except Exception as e:
        error_msg = str(e)[:1000]
        version.status = VersionStatus.ERROR
        version.error_message = error_msg
        _fail_job(job, error_msg)
        raise


# ====================================================================
# Helpers
# ====================================================================


def _complete_job(job: IngestionJob) -> None:
    job.status = JobStatus.COMPLETED
    job.completed_at = datetime.now(UTC)
    job.metadata_ = {**job.metadata_, "current_stage": "done"}


def _fail_job(job: IngestionJob, error_msg: str) -> None:
    job.status = JobStatus.FAILED
    job.error_message = error_msg
    job.completed_at = datetime.now(UTC)
    job.metadata_ = {**job.metadata_, "current_stage": "failed"}
