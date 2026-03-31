"""
src.rag.storage — Raw-file storage backends for the RAG pipeline.

Exports
-------
RagFileStore
    Primary interface used by :class:`~src.rag.service.IngestService`.
    Attempts to use MinIO when the ``minio`` package is installed and
    the endpoint is reachable; falls back to local disk storage otherwise.
"""
from .minio_client import RagFileStore

__all__ = ["RagFileStore"]
