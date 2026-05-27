"""Tests for API schemas validation."""

import pytest
from pydantic import ValidationError

from apps.api.schemas import QueryRequest


def test_query_request_valid() -> None:
    req = QueryRequest(query="What is RAG?")
    assert req.query == "What is RAG?"
    assert req.top_k == 5


def test_query_request_empty_query() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="")


def test_query_request_top_k_bounds() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="test", top_k=0)
    with pytest.raises(ValidationError):
        QueryRequest(query="test", top_k=100)
