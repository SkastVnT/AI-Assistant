"""
src.rag.db — Database layer (pgvector + ChromaDB).

Responsibility:
    SQLAlchemy 2 async engine/session, ORM models for documents & chunks
    with pgvector embeddings, and the legacy ChromaDB vector-store adapter.
"""
from .base import Base, get_engine, get_session_factory
from .chroma import ChromaStore, VectorStore
from .models import RagChunk, RagDocument

__all__ = [
    "Base",
    "get_engine",
    "get_session_factory",
    "ChromaStore",
    "VectorStore",
    "RagDocument",
    "RagChunk",
]
