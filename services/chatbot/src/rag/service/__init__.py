"""
src.rag.service — High-level retrieval and ingestion orchestration.

Responsibility:
    Coordinate embedding of a user query, searching across one or more
    vector-store collections, ranking/filtering results, and returning
    a unified list of ``SearchResult`` objects.

    Manage end-to-end document ingestion: store → parse → chunk → embed → persist.

    Orchestrate the full RAG pipeline (retrieve → sanitise → build context
    → augment prompt) via :class:`RAGOrchestrator`.
"""
from .ingest_service import IngestResult, IngestService
from .orchestrator import RAGOrchestrator, RAGResult
from .retrieval_service import RetrievalHit, RetrievalService
from .retriever import Retriever
from .strategy import RetrievalStrategy

__all__ = [
    "IngestResult",
    "IngestService",
    "RAGOrchestrator",
    "RAGResult",
    "RetrievalHit",
    "RetrievalService",
    "RetrievalStrategy",
    "Retriever",
]
