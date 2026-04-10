"""
Pluggable retrieval-strategy abstraction.

Implement :class:`RetrievalStrategy` to swap the search back-end
without touching the orchestrator or router layer.

The built-in :class:`RetrievalService` (pgvector cosine similarity)
already satisfies this protocol out of the box.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .retrieval_service import RetrievalHit


@runtime_checkable
class RetrievalStrategy(Protocol):
    """Contract that every retrieval back-end must satisfy."""

    async def retrieve(
        self,
        *,
        tenant_id: str,
        query: str,
        top_k: int | None = None,
        doc_ids: list[str] | None = None,
        min_score: float | None = None,
    ) -> list[RetrievalHit]: ...
