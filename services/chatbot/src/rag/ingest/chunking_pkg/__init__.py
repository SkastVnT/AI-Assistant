"""src.rag.ingest.chunking_pkg — Text chunking strategies."""
from .base import Chunker, TextChunk
from .recursive_text import RecursiveTextChunker, chunk_pages

__all__ = ["Chunker", "TextChunk", "RecursiveTextChunker", "chunk_pages"]
