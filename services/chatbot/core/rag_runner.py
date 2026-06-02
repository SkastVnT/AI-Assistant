"""
Persistent background event loop for running RAG async coroutines from the
synchronous Flask request path.

The RAG subsystem uses an async SQLAlchemy engine that is cached (and therefore
bound to the loop that first created it). Spawning a fresh ``asyncio.run`` loop
per request would break asyncpg connection reuse, so we keep one dedicated loop
running on a daemon thread and submit coroutines to it via
``run_coroutine_threadsafe``.
"""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Coroutine
from typing import Any, TypeVar

_T = TypeVar("_T")

_loop: asyncio.AbstractEventLoop | None = None
_lock = threading.Lock()


def _ensure_loop() -> asyncio.AbstractEventLoop:
    global _loop
    if _loop is not None and not _loop.is_closed():
        return _loop
    with _lock:
        if _loop is not None and not _loop.is_closed():
            return _loop
        loop = asyncio.new_event_loop()
        thread = threading.Thread(
            target=loop.run_forever,
            name="rag-async-loop",
            daemon=True,
        )
        thread.start()
        _loop = loop
        return loop


def run_rag_coro(coro: Coroutine[Any, Any, _T], *, timeout: float = 30.0) -> _T:
    """Run *coro* on the dedicated RAG loop and return its result.

    Raises whatever the coroutine raises, or ``TimeoutError`` if it exceeds
    *timeout* seconds.
    """
    loop = _ensure_loop()
    future = asyncio.run_coroutine_threadsafe(coro, loop)
    return future.result(timeout=timeout)
