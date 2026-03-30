"""Tests for the domain model schemas (libs/core/schemas.py)."""

import uuid

import pytest
from pydantic import ValidationError

from libs.core.schemas import (
    DocumentCreate,
    QueryFilters,
    QueryRequest,
    SourceChunk,
    TenantCreate,
    UserCreate,
)

# --- Tenant ---

def test_tenant_create_valid() -> None:
    t = TenantCreate(name="Acme Corp", slug="acme")
    assert t.name == "Acme Corp"
    assert t.slug == "acme"
    assert t.settings == {}


def test_tenant_create_invalid_slug() -> None:
    with pytest.raises(ValidationError):
        TenantCreate(name="Acme", slug="INVALID_SLUG!")


# --- User ---

def test_user_create_defaults() -> None:
    u = UserCreate(email="test@example.com")
    assert u.role == "member"
    assert u.display_name is None


# --- Document ---

def test_document_create_valid() -> None:
    d = DocumentCreate(title="Test Document")
    assert d.sensitivity_level == "internal"
    assert d.language == "en"
    assert d.tags == []


def test_document_create_with_tags() -> None:
    d = DocumentCreate(title="Test", tags=["a", "b"])
    assert d.tags == ["a", "b"]


def test_document_create_empty_title_fails() -> None:
    with pytest.raises(ValidationError):
        DocumentCreate(title="")


# --- QueryRequest ---

def test_query_request_valid() -> None:
    req = QueryRequest(query="What is RAG?")
    assert req.query == "What is RAG?"
    assert req.top_k == 5
    assert req.filters is None


def test_query_request_with_filters() -> None:
    req = QueryRequest(
        query="test",
        filters=QueryFilters(tags=["rag"], languages=["en"]),
    )
    assert req.filters is not None
    assert req.filters.tags == ["rag"]


def test_query_request_empty_query() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="")


def test_query_request_top_k_bounds() -> None:
    with pytest.raises(ValidationError):
        QueryRequest(query="test", top_k=0)
    with pytest.raises(ValidationError):
        QueryRequest(query="test", top_k=100)


# --- SourceChunk ---

def test_source_chunk_fields() -> None:
    uid = uuid.uuid4()
    s = SourceChunk(
        chunk_id=uid,
        document_id=uid,
        version_id=uid,
        filename="test.md",
        content="hello",
        score=0.95,
        chunk_index=0,
    )
    assert s.score == 0.95
    assert s.chunk_index == 0
