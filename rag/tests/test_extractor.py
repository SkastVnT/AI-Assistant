"""Tests for textextractor."""

import pytest

from libs.ingestion.extractor import extract_text


def test_extract_utf8_text() -> None:
    content = b"Hello, world!"
    result = extract_text(content, "test.txt")
    assert result == "Hello, world!"


def test_extract_markdown() -> None:
    content = b"# Title\n\nBody text."
    result = extract_text(content, "readme.md")
    assert "# Title" in result


def test_extract_unsupported_extension() -> None:
    with pytest.raises(ValueError, match="Unsupported file type"):
        extract_text(b"binary data", "file.pdf")


def test_extract_handles_encoding_errors() -> None:
    # Invalid UTF-8 bytes should be replaced, not crash
    content = b"\xff\xfe Hello"
    result = extract_text(content, "file.txt")
    assert "Hello" in result
