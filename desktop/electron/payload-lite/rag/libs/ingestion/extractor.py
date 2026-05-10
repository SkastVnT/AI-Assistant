"""Text extraction from uploaded files.

MVP: plain text and markdown.
Future: PDF (via unstructured/VLM), DOCX, HTML, images.
"""

from pathlib import PurePath

SUPPORTED_EXTENSIONS = {".txt", ".md", ".markdown", ".text"}


def extract_text(content: bytes, filename: str) -> str:
    """Extract text from file content.

    Raises ValueError for unsupported file types.
    """
    ext = PurePath(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type: {ext}. Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )
    # MVP: decode UTF-8 text directly
    return content.decode("utf-8", errors="replace")
