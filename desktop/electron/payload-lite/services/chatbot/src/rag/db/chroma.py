"""
ChromaDB vector store implementation.
"""
import logging
from abc import ABC, abstractmethod

from ..models import SearchResult

logger = logging.getLogger(__name__)


class VectorStore(ABC):
    """Abstract vector store interface."""

    @abstractmethod
    def add(
        self,
        collection: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None: ...

    @abstractmethod
    def query(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[SearchResult]: ...

    @abstractmethod
    def delete_collection(self, collection: str) -> None: ...

    @abstractmethod
    def list_collections(self) -> list[str]: ...


class ChromaStore(VectorStore):
    """Persistent ChromaDB-backed vector store."""

    def __init__(self, persist_dir: str | None = None):
        import chromadb
        from chromadb.config import Settings as ChromaSettings

        from ..config import RAG_CHROMA_DIR

        path = persist_dir or str(RAG_CHROMA_DIR)
        self._client = chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

    def _get_or_create(self, name: str):
        return self._client.get_or_create_collection(
            name=name,
            metadata={"hnsw:space": "cosine"},
        )

    # ── mutations ──────────────────────────────────────────────────────

    def add(
        self,
        collection: str,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict] | None = None,
    ) -> None:
        col = self._get_or_create(collection)
        col.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def delete_collection(self, collection: str) -> None:
        try:
            self._client.delete_collection(collection)
        except Exception:
            pass

    # ── queries ─────────────────────────────────────────────────────────

    def query(
        self,
        collection: str,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[SearchResult]:
        try:
            col = self._client.get_collection(collection)
        except Exception:
            return []

        results = col.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        out: list[SearchResult] = []
        for i, chunk_id in enumerate(results["ids"][0]):
            distance = results["distances"][0][i]
            score = 1.0 - distance  # cosine distance → similarity
            meta = results["metadatas"][0][i] or {}
            out.append(
                SearchResult(
                    chunk_id=chunk_id,
                    document_id=meta.get("document_id", ""),
                    content=results["documents"][0][i],
                    score=score,
                    metadata=meta,
                )
            )
        return out

    def list_collections(self) -> list[str]:
        return [c.name for c in self._client.list_collections()]
