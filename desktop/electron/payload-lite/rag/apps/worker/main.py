"""Background worker for async document ingestion.

Polls for QUEUED ingestion jobs and runs the Parse-Transform-Index pipeline.
Future: replace with Celery/ARQ task queue for distributed workers.
"""

import asyncio
import contextlib
import signal
import sys
from pathlib import Path

# Ensure project root is on sys.path when running as module
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from libs.core.database import async_session_factory
from libs.core.logging import setup_logging
from libs.core.providers.factory import get_embedding_provider
from libs.core.settings import get_settings
from libs.ingestion.worker_tasks import process_pending_jobs

logger = setup_logging("rag.worker")


class Worker:
    """Simple polling worker that processes queued ingestion jobs."""

    def __init__(self) -> None:
        self._running = False
        self._embedding_provider = get_embedding_provider()
        self._settings = get_settings()

    async def run(self) -> None:
        self._running = True
        poll_interval = self._settings.ingestion.poll_interval
        logger.info("Worker started — polling every %ds", poll_interval)

        while self._running:
            try:
                async with async_session_factory() as session:
                    processed = await process_pending_jobs(
                        db=session,
                        embedding_provider=self._embedding_provider,
                    )
                    if processed > 0:
                        logger.info("Processed %d job(s)", processed)
            except Exception:
                logger.exception("Error in worker loop")

            await asyncio.sleep(poll_interval)

        logger.info("Worker stopped")

    def stop(self) -> None:
        logger.info("Shutdown signal received")
        self._running = False


async def main() -> None:
    worker = Worker()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        with contextlib.suppress(NotImplementedError):
            loop.add_signal_handler(sig, worker.stop)

    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
