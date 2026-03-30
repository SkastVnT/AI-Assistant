"""Worker tasks — process queued ingestion jobs.

Picks up QUEUED jobs, runs the ingestion pipeline, handles retries.
Status transitions:
    QUEUED → RUNNING → COMPLETED  (success)
    QUEUED → RUNNING → FAILED     (all retries exhausted)
    RUNNING → QUEUED              (retry: re-enqueue with incremented attempt)
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.models import IngestionJob, JobStatus
from libs.core.providers.base import EmbeddingProvider
from libs.core.settings import get_settings
from libs.ingestion.pipeline import process_ingestion_job

logger = logging.getLogger("rag.worker.tasks")


async def process_pending_jobs(
    db: AsyncSession,
    embedding_provider: EmbeddingProvider,
    batch_limit: int | None = None,
) -> int:
    """Find and process queued ingestion jobs. Returns count processed."""
    settings = get_settings()
    limit = batch_limit or settings.ingestion.batch_size

    result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.status == JobStatus.QUEUED)
        .order_by(IngestionJob.created_at)
        .limit(limit)
    )
    queued_jobs = list(result.scalars().all())

    if not queued_jobs:
        return 0

    processed = 0
    for job in queued_jobs:
        try:
            await process_ingestion_job(db, embedding_provider, job)
            processed += 1
            logger.info("Job %s completed (attempt %d)", job.id, job.attempt_number)

        except Exception:
            logger.exception("Job %s failed (attempt %d)", job.id, job.attempt_number)
            # Retry logic: re-enqueue if under max retries
            if job.attempt_number < settings.ingestion.max_retries:
                job.status = JobStatus.QUEUED
                job.attempt_number += 1
                job.error_message = None
                logger.info(
                    "Job %s re-queued for attempt %d/%d",
                    job.id,
                    job.attempt_number,
                    settings.ingestion.max_retries,
                )
            # else: job stays FAILED (set by pipeline)

        # Commit each job individually so failures don't roll back others
        await db.commit()

    return processed
