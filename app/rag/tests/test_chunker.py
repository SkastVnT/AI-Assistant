"""Tests for the chunking module."""

from libs.ingestion.chunker import chunk_text


def test_chunk_empty_text() -> None:
    assert chunk_text("") == []
    assert chunk_text("   ") == []


def test_chunk_short_text() -> None:
    text = "Hello, world!"
    chunks = chunk_text(text, chunk_size=100, chunk_overlap=10)
    assert len(chunks) == 1
    assert chunks[0].content == "Hello, world!"
    assert chunks[0].index == 0


def test_chunk_long_text_produces_overlap() -> None:
    # Create text that needs multiple chunks
    text = "Word " * 200  # ~1000 chars
    chunks = chunk_text(text, chunk_size=200, chunk_overlap=40)
    assert len(chunks) > 1
    # Check monotonic indexing
    for i, chunk in enumerate(chunks):
        assert chunk.index == i


def test_chunk_respects_paragraph_boundaries() -> None:
    text = "First paragraph content here.\n\nSecond paragraph content."
    chunks = chunk_text(text, chunk_size=40, chunk_overlap=5)
    assert len(chunks) >= 2


def test_chunk_token_count_estimated() -> None:
    text = "Some text that should have tokens estimated."
    chunks = chunk_text(text, chunk_size=500, chunk_overlap=0)
    assert len(chunks) == 1
    assert chunks[0].token_count > 0
