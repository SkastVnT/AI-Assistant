"""
RAG subsystem public API.

Usage:
    from src.rag import RAG_ENABLED, get_rag_pipeline

    pipeline = get_rag_pipeline()   # None when RAG_ENABLED=false
    if pipeline:
        retriever = pipeline["retriever"]
        ingester  = pipeline["ingester"]
"""
import logging

from .config import RAG_ENABLED

logger = logging.getLogger(__name__)

_pipeline: dict | None = None


def get_rag_pipeline() -> dict | None:
    """Lazy-initialised singleton.  Returns None when RAG is disabled or deps missing."""
    global _pipeline
    if _pipeline is not None:
        return _pipeline

    if not RAG_ENABLED:
        return None

    try:
        from .db import ChromaStore
        from .embeddings import create_embedding_provider
        from .ingest import Ingester
        from .service import Retriever

        embedder = create_embedding_provider()

        store = ChromaStore()

        _pipeline = {
            "embedder": embedder,
            "store": store,
            "retriever": Retriever(store, embedder),
            "ingester": Ingester(store, embedder),
        }
        logger.info(
            f"[RAG] Pipeline ready  provider={embedder.__class__.__name__}  "
            f"dim={embedder.dimension}"
        )
        return _pipeline

    except ImportError as exc:
        logger.error(
            f"[RAG] Missing dependency: {exc}. "
            "Install with: pip install chromadb"
        )
        return None
    except Exception as exc:
        logger.error(f"[RAG] Init failed: {exc}")
        return None
