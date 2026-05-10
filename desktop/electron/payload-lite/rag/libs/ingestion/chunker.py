"""Text chunking strategies.

MVP: recursive character splitter with overlap.
Future: semantic chunking, parent-document retrieval, code-aware chunking.
"""

from dataclasses import dataclass

from libs.core.settings import get_settings


@dataclass(frozen=True)
class TextChunk:
    index: int
    content: str
    token_count: int
    metadata: dict


def chunk_text(
    text: str,
    *,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[TextChunk]:
    """Split text into overlapping chunks by character count.

    Uses a simple recursive approach: split on paragraph breaks first,
    then sentences, then fall back to character splitting.
    """
    settings = get_settings()
    size = chunk_size or settings.chunking.size
    overlap = chunk_overlap or settings.chunking.overlap

    if not text.strip():
        return []

    # Rough token estimate: ~4 chars per token for English
    def estimate_tokens(s: str) -> int:
        return max(1, len(s) // 4)

    chunks: list[TextChunk] = []
    start = 0
    idx = 0

    while start < len(text):
        end = start + size

        # Try to break at a paragraph or sentence boundary
        if end < len(text):
            # Look for paragraph break
            para_break = text.rfind("\n\n", start, end)
            if para_break > start + size // 2:
                end = para_break + 2
            else:
                # Look for sentence break
                for sep in (". ", "! ", "? ", "\n"):
                    sent_break = text.rfind(sep, start, end)
                    if sent_break > start + size // 2:
                        end = sent_break + len(sep)
                        break

        chunk_content = text[start:end].strip()
        if chunk_content:
            chunks.append(
                TextChunk(
                    index=idx,
                    content=chunk_content,
                    token_count=estimate_tokens(chunk_content),
                    metadata={},
                )
            )
            idx += 1

        start = end - overlap if end < len(text) else len(text)

    return chunks
