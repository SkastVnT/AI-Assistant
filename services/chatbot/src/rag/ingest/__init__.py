"""
src.rag.ingest — Document ingestion pipeline.

Components:
    - parsers:      Format-specific document parsers (txt, md, html, pdf).
    - chunking_pkg: Text chunking strategies with overlap and metadata.
    - chunking:     Legacy flat splitter (``split_text``).
    - pipeline:     Orchestrates chunk → embed → store.
"""
from .chunking import split_text
from .chunking_pkg import Chunker, RecursiveTextChunker, TextChunk, chunk_pages
from .parsers import (
    DocumentParser,
    HTMLParser,
    PageContent,
    ParsedDocument,
    PDFParser,
    PlainTextParser,
    get_parser,
)
from .pipeline import Ingester

__all__ = [
    # parsers
    "DocumentParser",
    "ParsedDocument",
    "PageContent",
    "PlainTextParser",
    "HTMLParser",
    "PDFParser",
    "get_parser",
    # chunking
    "Chunker",
    "TextChunk",
    "RecursiveTextChunker",
    "chunk_pages",
    # legacy
    "split_text",
    "Ingester",
]
