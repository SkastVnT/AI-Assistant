"""
Shared RAG retrieval helper used by both chat and stream routers.

Thin wrapper around :class:`~src.rag.service.orchestrator.RAGOrchestrator`
so that the normal and streaming endpoints never diverge.

Falls back to a no-op stub when the RAG stack (pgvector, sqlalchemy, etc.)
is not installed in the active venv.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List

try:
    from src.rag.service.orchestrator import RAGOrchestrator, RAGResult
    _RAG_AVAILABLE = True
except (ImportError, Exception):
    _RAG_AVAILABLE = False
    RAGOrchestrator = None  # type: ignore[assignment,misc]

    @dataclass
    class RAGResult:  # type: ignore[no-redef]
        """Stub returned when RAG stack is unavailable — mirrors real RAGResult API."""
        message: str = ""
        custom_prompt: str = ""
        citations: List[dict] = field(default_factory=list)
        chunk_count: int = 0

__all__ = ["RAGResult", "retrieve_rag_context"]


async def retrieve_rag_context(
    *,
    message: str,
    custom_prompt: str,
    language: str,
    tenant_id: str,
    rag_collection_ids: list[str],
    rag_top_k: int = 5,
) -> RAGResult:
    """Run RAG retrieval and augment the message + prompt.

    Delegates to :meth:`RAGOrchestrator.retrieve_for_chat`.
    Returns the original message/prompt unchanged when RAG is disabled,
    collections are empty, retrieval fails, or the RAG stack is not installed.
    """
    if not _RAG_AVAILABLE or not rag_collection_ids:
        return RAGResult(
            message=message,
            custom_prompt=custom_prompt,
            citations=None,
            chunk_count=0,
        )

    orchestrator = RAGOrchestrator()
    return await orchestrator.retrieve_for_chat(
        message=message,
        custom_prompt=custom_prompt,
        language=language,
        tenant_id=tenant_id,
        collection_ids=rag_collection_ids,
        top_k=rag_top_k,
    )
