"""
Retrieval pipeline — embed query → search collections → rank results.
"""
import logging

from ..config import RAG_DEFAULT_TOP_K, RAG_SIMILARITY_THRESHOLD
from ..embeddings.base import EmbeddingProvider
from ..db.chroma import VectorStore
from ..models import SearchResult

logger = logging.getLogger(__name__)


class Retriever:
    def __init__(self, store: VectorStore, embedder: EmbeddingProvider):
        self._store = store
        self._embedder = embedder

    def retrieve(
        self,
        query: str,
        collection_ids: list[str],
        top_k: int = RAG_DEFAULT_TOP_K,
        threshold: float = RAG_SIMILARITY_THRESHOLD,
    ) -> list[SearchResult]:
        query_embedding = self._embedder.embed_query(query)

        all_results: list[SearchResult] = []
        for cid in collection_ids:
            results = self._store.query(cid, query_embedding, top_k=top_k)
            all_results.extend(results)

        # Filter by similarity threshold, sort descending
        filtered = [r for r in all_results if r.score >= threshold]
        filtered.sort(key=lambda r: r.score, reverse=True)

        return filtered[:top_k]
