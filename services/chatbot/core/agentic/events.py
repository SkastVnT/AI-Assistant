"""
Agentic Council — Streaming events
====================================
Typed event schema and async emitter for SSE progress updates.

These events are **safe for the frontend** — they carry only operational
status and short role-based messages, never raw chain-of-thought.

Usage in the orchestrator::

    emitter = CouncilEventEmitter(run_id)
    await emitter.emit(stage="planning", role="planner",
                       status="started", short_message="Decomposing task…")
    # … later …
    async for event in emitter.events():
        yield _sse("council_event", event.model_dump())
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from enum import Enum
from typing import AsyncGenerator

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────

class EventStage(str, Enum):
    """Logical pipeline stage."""
    planning = "planning"
    researching = "researching"
    synthesizing = "synthesizing"
    critiquing = "critiquing"
    retrying = "retrying"
    completed = "completed"
    failed = "failed"


class EventStatus(str, Enum):
    """Per-stage lifecycle."""
    started = "started"
    progress = "progress"
    completed = "completed"
    skipped = "skipped"


# ── Event payload ──────────────────────────────────────────────────────

class CouncilEvent(BaseModel):
    """A single SSE-safe progress event.

    Serialised to JSON and sent as ``event: council_event\\ndata: …``
    on the ``/chat/council/stream`` endpoint.
    """
    run_id: str = Field(..., description="Council run ID for correlation")
    stage: EventStage = Field(..., description="Current pipeline stage")
    role: str = Field(..., description="Agent role name (planner/researcher/…)")
    status: EventStatus = Field(..., description="started | progress | completed | skipped")
    round: int = Field(1, ge=1, description="Current iteration round")
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
    )
    short_message: str = Field(
        "",
        description="Human-readable progress note (no raw reasoning)",
    )


# ── Sentinel ───────────────────────────────────────────────────────────

_SENTINEL = object()


# ── Async emitter ──────────────────────────────────────────────────────

class CouncilEventEmitter:
    """Publish / subscribe bridge between the orchestrator and the SSE route.

    The orchestrator calls :meth:`emit` at each stage transition.
    The route consumes events via :meth:`events` (an async generator).
    When the pipeline finishes, call :meth:`close` so the generator ends.
    """

    def __init__(self, run_id: str) -> None:
        self.run_id = run_id
        self._queue: asyncio.Queue = asyncio.Queue()
        self._closed = False

    async def emit(
        self,
        *,
        stage: EventStage | str,
        role: str,
        status: EventStatus | str = EventStatus.started,
        round: int = 1,
        short_message: str = "",
    ) -> CouncilEvent:
        """Create and enqueue a ``CouncilEvent``."""
        event = CouncilEvent(
            run_id=self.run_id,
            stage=EventStage(stage) if isinstance(stage, str) else stage,
            role=role,
            status=EventStatus(status) if isinstance(status, str) else status,
            round=round,
            short_message=short_message[:300],
        )
        await self._queue.put(event)
        return event

    async def close(self) -> None:
        """Signal the consumer that no more events will arrive."""
        self._closed = True
        await self._queue.put(_SENTINEL)

    async def events(self) -> AsyncGenerator[CouncilEvent, None]:
        """Async generator that yields events until :meth:`close` is called."""
        while True:
            item = await self._queue.get()
            if item is _SENTINEL:
                break
            yield item
