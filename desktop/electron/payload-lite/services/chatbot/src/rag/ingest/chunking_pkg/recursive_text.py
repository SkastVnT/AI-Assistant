"""
Recursive text splitter with overlap and metadata carry-over.

Tries to break at natural boundaries (paragraphs → lines → sentences →
words) before falling back to a hard character cut.
"""
from __future__ import annotations

from .base import Chunker, TextChunk

# Separators tried in order from most desirable to least.
_DEFAULT_SEPARATORS: list[str] = ["\n\n", "\n", ". ", ", ", " "]


class RecursiveTextChunker(Chunker):
    """Character-count chunker with overlap and smart boundary detection.

    Parameters:
        max_chars:      Maximum characters per chunk.
        overlap_chars:  How many trailing characters of one chunk reappear at
                        the start of the next.
        separators:     Ordered list of boundary strings to try.
    """

    def __init__(
        self,
        max_chars: int = 512,
        overlap_chars: int = 64,
        separators: list[str] | None = None,
    ):
        if overlap_chars >= max_chars:
            raise ValueError("overlap_chars must be less than max_chars")
        self.max_chars = max_chars
        self.overlap_chars = overlap_chars
        self.separators = separators or _DEFAULT_SEPARATORS

    def chunk(
        self,
        text: str,
        metadata: dict | None = None,
    ) -> list[TextChunk]:
        if not text or not text.strip():
            return []

        base_meta = dict(metadata) if metadata else {}
        chunks: list[TextChunk] = []
        start = 0
        index = 0

        while start < len(text):
            end = start + self.max_chars

            # Try to break at a natural boundary
            if end < len(text):
                best = -1
                for sep in self.separators:
                    # Search in the back half of the window
                    pos = text.rfind(sep, start + self.max_chars // 2, end)
                    if pos > start:
                        best = pos + len(sep)
                        break
                if best > start:
                    end = best

            fragment = text[start:end].strip()
            if fragment:
                meta = {**base_meta}
                chunks.append(TextChunk(text=fragment, chunk_index=index, metadata=meta))
                index += 1

            # Advance with overlap
            if end >= len(text):
                break
            start = end - self.overlap_chars

        return chunks


def chunk_pages(
    pages: list[dict],
    max_chars: int = 512,
    overlap_chars: int = 64,
) -> list[TextChunk]:
    """Convenience: chunk a list of ``{text, page_number, metadata}`` dicts.

    Each chunk inherits the ``page_number`` of the page it originates from.
    When a chunk spans a page boundary it gets the *starting* page number.
    """
    chunker = RecursiveTextChunker(max_chars=max_chars, overlap_chars=overlap_chars)
    all_chunks: list[TextChunk] = []
    global_index = 0

    for page in pages:
        page_text = page.get("text", "")
        page_num = page.get("page_number")
        page_meta = dict(page.get("metadata", {}))
        if page_num is not None:
            page_meta["page_number"] = page_num

        page_chunks = chunker.chunk(page_text, metadata=page_meta)
        for c in page_chunks:
            c.chunk_index = global_index
            global_index += 1
        all_chunks.extend(page_chunks)

    return all_chunks
