"""
Ingest pipeline — chunk → embed → store documents.
"""
import logging

from ..config import RAG_CHUNK_OVERLAP, RAG_CHUNK_SIZE
from ..embeddings.base import EmbeddingProvider
from ..db.chroma import VectorStore
from ..models import Document
from .chunking import split_text

logger = logging.getLogger(__name__)

EMBED_BATCH_SIZE = 96


class Ingester:
    def __init__(self, store: VectorStore, embedder: EmbeddingProvider):
        self._store = store
        self._embedder = embedder

    def ingest(
        self,
        document: Document,
        collection: str,
        chunk_size: int = RAG_CHUNK_SIZE,
        chunk_overlap: int = RAG_CHUNK_OVERLAP,
    ) -> int:
        """Chunk, embed, and store a document. Returns number of chunks stored."""
        chunks = split_text(
            document.content,
            chunk_size,
            chunk_overlap,
            document_id=document.id,
        )
        if not chunks:
            return 0

        texts = [c.content for c in chunks]
        ids = [c.id for c in chunks]
        metadatas = [
            {
                "document_id": document.id,
                "document_title": document.title,
                "source": document.source,
                "chunk_index": c.index,
            }
            for c in chunks
        ]

        # Batch embed to stay within API limits
        for i in range(0, len(texts), EMBED_BATCH_SIZE):
            batch_texts = texts[i : i + EMBED_BATCH_SIZE]
            batch_ids = ids[i : i + EMBED_BATCH_SIZE]
            batch_meta = metadatas[i : i + EMBED_BATCH_SIZE]
            embeddings = self._embedder.embed(batch_texts)
            self._store.add(collection, batch_ids, batch_texts, embeddings, batch_meta)

        logger.info(
            f"[RAG] Ingested '{document.title}' → {len(chunks)} chunks into '{collection}'"
        )
        return len(chunks)
