"""Extensible chunking strategies for the RAG ingestion pipeline."""

from libs.ingestion.chunkers.base import ChunkingStrategy, ChunkMeta, ChunkResult
from libs.ingestion.chunkers.config import ChunkingPreset, get_preset
from libs.ingestion.chunkers.registry import get_chunker

__all__ = [
    "ChunkMeta",
    "ChunkResult",
    "ChunkingPreset",
    "ChunkingStrategy",
    "get_chunker",
    "get_preset",
]
