"""
Text chunking utilities for RAG ingest.
"""
import uuid

from ..models import Chunk


def split_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
    document_id: str = "",
) -> list[Chunk]:
    """Split text into overlapping chunks, breaking at natural boundaries."""
    if not text.strip():
        return []

    chunks: list[Chunk] = []
    start = 0
    index = 0

    while start < len(text):
        end = start + chunk_size

        # Try to break at a natural boundary
        if end < len(text):
            for sep in ["\n\n", "\n", ". ", " "]:
                pos = text.rfind(sep, start + chunk_size // 2, end)
                if pos > start:
                    end = pos + len(sep)
                    break

        chunk_text = text[start:end].strip()
        if chunk_text:
            chunks.append(
                Chunk(
                    id=f"{document_id}_{index}" if document_id else str(uuid.uuid4()),
                    document_id=document_id,
                    content=chunk_text,
                    index=index,
                )
            )
            index += 1

        start = end - chunk_overlap if end < len(text) else end

    return chunks
