"""Short-term memory for the agent — scratchpad + evidence accumulator.

Maintains context that the agent can read/write across turns.
All state is in-memory (per request). Nothing is persisted to DB
unless the orchestrator explicitly saves the final AgentState.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("rag.agent.memory")


@dataclass
class EvidenceItem:
    """A single piece of evidence collected by the agent."""

    source: str          # Tool that produced it (e.g. "retriever")
    query: str           # Query that led to this evidence
    content: str         # The actual evidence text
    turn_index: int      # Which turn collected it
    metadata: dict = field(default_factory=dict)


class ShortTermMemory:
    """In-memory scratchpad for one agent execution.

    Tracks:
    - evidence accumulator (capped to max_items)
    - scratchpad notes (agent's working thoughts)
    - query history (to avoid duplicate searches)
    - context window estimator (token budget tracking)
    """

    def __init__(self, *, max_evidence: int = 20, max_scratchpad: int = 10) -> None:
        self._evidence: list[EvidenceItem] = []
        self._scratchpad: list[str] = []
        self._query_history: list[str] = []
        self._max_evidence = max_evidence
        self._max_scratchpad = max_scratchpad

    # ── Evidence management ────────────────────────────────────────

    def add_evidence(
        self,
        content: str,
        *,
        source: str,
        query: str,
        turn_index: int,
        metadata: dict | None = None,
    ) -> None:
        """Add evidence, evicting oldest if over capacity."""
        if len(self._evidence) >= self._max_evidence:
            self._evidence.pop(0)
            logger.debug("memory: evicted oldest evidence (cap=%d)", self._max_evidence)

        self._evidence.append(EvidenceItem(
            source=source,
            query=query,
            content=content,
            turn_index=turn_index,
            metadata=metadata or {},
        ))

    @property
    def evidence(self) -> list[EvidenceItem]:
        return list(self._evidence)

    @property
    def evidence_count(self) -> int:
        return len(self._evidence)

    def get_evidence_text(self) -> str:
        """Render all evidence as numbered context for the LLM."""
        if not self._evidence:
            return "(no evidence collected yet)"
        lines = []
        for i, e in enumerate(self._evidence, 1):
            lines.append(f"[Evidence {i}] (from {e.source}, query: {e.query})")
            lines.append(e.content)
            lines.append("")
        return "\n".join(lines)

    # ── Scratchpad (agent's working notes) ─────────────────────────

    def add_note(self, note: str) -> None:
        """Append a working note. Oldest notes are evicted if over cap."""
        if len(self._scratchpad) >= self._max_scratchpad:
            self._scratchpad.pop(0)
        self._scratchpad.append(note)

    @property
    def notes(self) -> list[str]:
        return list(self._scratchpad)

    def get_scratchpad_text(self) -> str:
        if not self._scratchpad:
            return "(empty scratchpad)"
        return "\n".join(f"- {n}" for n in self._scratchpad)

    # ── Query deduplication ────────────────────────────────────────

    def record_query(self, query: str) -> None:
        self._query_history.append(query)

    def has_queried(self, query: str) -> bool:
        """Check if a similar query was already run (exact match)."""
        return query in self._query_history

    @property
    def query_history(self) -> list[str]:
        return list(self._query_history)

    # ── Context window estimation ──────────────────────────────────

    def estimate_tokens(self) -> int:
        """Rough token count of all memory content (4 chars ≈ 1 token)."""
        total_chars = sum(len(e.content) for e in self._evidence)
        total_chars += sum(len(n) for n in self._scratchpad)
        return total_chars // 4

    # ── Serialization ──────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "evidence_count": len(self._evidence),
            "scratchpad_notes": len(self._scratchpad),
            "queries_run": len(self._query_history),
            "estimated_tokens": self.estimate_tokens(),
        }
