"""
Shared RAG retrieval helper used by both chat and stream routers.

Thin wrapper around :class:`~src.rag.service.orchestrator.RAGOrchestrator`
so that the normal and streaming endpoints never diverge.
"""
from __future__ import annotations

from src.rag.service.orchestrator import RAGOrchestrator, RAGResult

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
    collections are empty, or retrieval fails.
    """
    orchestrator = RAGOrchestrator()
    return await orchestrator.retrieve_for_chat(
        message=message,
        custom_prompt=custom_prompt,
        language=language,
        tenant_id=tenant_id,
        collection_ids=rag_collection_ids,
        top_k=rag_top_k,
    )
