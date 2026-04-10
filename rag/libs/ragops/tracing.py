"""Lightweight span-based tracing for RAG pipelines.

Records named operations with timing, token usage, counts, and model metadata.
Spans are collected in-memory during a request and flushed to the existing
RetrievalTrace.metadata_ or IngestionJob.metadata_ JSONB column.

Usage:
    collector = SpanCollector()
    with collector.span("embedding", model="text-embedding-3-small") as s:
        vectors = await embed(texts)
        s.metadata["token_count"] = sum(len(t.split()) for t in texts)

    # Later: flush to trace
    trace.metadata_["spans"] = collector.to_dict()
"""

from __future__ import annotations

import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, field


@dataclass
class Span:
    """A single timed operation within a pipeline trace."""

    name: str
    start_ns: int
    end_ns: int | None = None
    metadata: dict = field(default_factory=dict)
    children: list[Span] = field(default_factory=list)

    @property
    def duration_ms(self) -> int:
        if self.end_ns is None:
            return 0
        return max(0, int((self.end_ns - self.start_ns) / 1_000_000))

    def close(self) -> None:
        if self.end_ns is None:
            self.end_ns = time.perf_counter_ns()

    def to_dict(self) -> dict:
        d: dict = {
            "name": self.name,
            "duration_ms": self.duration_ms,
        }
        if self.metadata:
            d["metadata"] = self.metadata
        if self.children:
            d["children"] = [c.to_dict() for c in self.children]
        return d


class SpanCollector:
    """Collects spans during a single pipeline execution.

    Supports nested spans via a stack. Top-level spans are roots;
    spans started while another is active become children.
    """

    def __init__(self) -> None:
        self._roots: list[Span] = []
        self._stack: list[Span] = []

    @contextmanager
    def span(self, name: str, **metadata: object) -> Generator[Span, None, None]:
        """Start a named span. Use as a context manager.

        Keyword arguments are stored in span.metadata.
        You can also mutate span.metadata inside the block.
        """
        s = Span(
            name=name,
            start_ns=time.perf_counter_ns(),
            metadata=dict(metadata),
        )
        if self._stack:
            self._stack[-1].children.append(s)
        else:
            self._roots.append(s)
        self._stack.append(s)
        try:
            yield s
        finally:
            s.close()
            self._stack.pop()

    def add_span(
        self,
        name: str,
        duration_ms: int,
        **metadata: object,
    ) -> Span:
        """Add a completed span directly (e.g. from sub-service timing)."""
        s = Span(
            name=name,
            start_ns=0,
            end_ns=duration_ms * 1_000_000,
            metadata=dict(metadata),
        )
        if self._stack:
            self._stack[-1].children.append(s)
        else:
            self._roots.append(s)
        return s

    @property
    def total_ms(self) -> int:
        return sum(s.duration_ms for s in self._roots)

    @property
    def spans(self) -> list[Span]:
        return list(self._roots)

    def to_dict(self) -> dict:
        """Serialize all spans for JSONB storage."""
        return {
            "spans": [s.to_dict() for s in self._roots],
            "total_ms": self.total_ms,
        }

    def summary(self) -> dict[str, int]:
        """Flat name -> duration_ms mapping of all root spans."""
        return {s.name: s.duration_ms for s in self._roots}
