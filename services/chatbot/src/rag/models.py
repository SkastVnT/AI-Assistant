"""
RAG data models.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class Document(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    source: str = ""
    metadata: dict = Field(default_factory=dict)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class Chunk(BaseModel):
    id: str
    document_id: str
    content: str
    index: int
    metadata: dict = Field(default_factory=dict)


class SearchResult(BaseModel):
    chunk_id: str
    document_id: str
    content: str
    score: float
    metadata: dict = Field(default_factory=dict)
