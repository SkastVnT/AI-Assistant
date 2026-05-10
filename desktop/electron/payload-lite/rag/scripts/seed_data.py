"""Seed data script — populates the database with sample records for development.

Usage:
    python -m scripts.seed_data          (from rag/ directory)
    or: make seed                        (via Makefile)

Requires a running Postgres instance with the schema already applied.
"""

import asyncio
import uuid

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.database import async_session_factory, engine
from libs.core.models import (
    DataSource,
    Document,
    DocumentChunk,
    DocumentStatus,
    DocumentVersion,
    IngestionJob,
    JobStatus,
    SensitivityLevel,
    SourceType,
    Tenant,
    User,
    VersionStatus,
)

# Deterministic IDs for easy reference
TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
DS_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")
DOC1_ID = uuid.UUID("00000000-0000-0000-0000-000000001000")
DOC2_ID = uuid.UUID("00000000-0000-0000-0000-000000002000")
VER1_ID = uuid.UUID("00000000-0000-0000-0000-000000010000")
VER2_ID = uuid.UUID("00000000-0000-0000-0000-000000020000")


async def seed(session: AsyncSession) -> None:
    # Skip if already seeded
    exists = await session.scalar(
        text("SELECT 1 FROM tenants WHERE id = :id"),
        {"id": str(TENANT_ID)},
    )
    if exists:
        print("Seed data already exists, skipping.")
        return

    # Tenant
    tenant = Tenant(
        id=TENANT_ID,
        name="Acme Corp",
        slug="acme",
        settings={"max_documents": 1000},
    )
    session.add(tenant)

    # User
    user = User(
        id=USER_ID,
        tenant_id=TENANT_ID,
        email="admin@acme.example",
        display_name="Admin User",
        role="admin",
    )
    session.add(user)

    # Data source
    ds = DataSource(
        id=DS_ID,
        tenant_id=TENANT_ID,
        name="Manual Uploads",
        source_type=SourceType.UPLOAD,
        config={},
    )
    session.add(ds)

    # Document 1 — with a ready version and sample chunks
    doc1 = Document(
        id=DOC1_ID,
        tenant_id=TENANT_ID,
        data_source_id=DS_ID,
        title="RAG Architecture Overview",
        author="Engineering Team",
        sensitivity_level=SensitivityLevel.INTERNAL,
        language="en",
        tags=["architecture", "rag"],
        metadata_={"department": "engineering"},
        status=DocumentStatus.ACTIVE,
    )
    session.add(doc1)

    ver1 = DocumentVersion(
        id=VER1_ID,
        tenant_id=TENANT_ID,
        document_id=DOC1_ID,
        version_number=1,
        storage_key="documents/seed/doc1_v1.md",
        filename="rag_architecture.md",
        content_type="text/markdown",
        file_size_bytes=2048,
        checksum="a" * 64,
        status=VersionStatus.READY,
        chunk_count=2,
    )
    session.add(ver1)

    # Sample chunks (no real embeddings — just placeholders)
    for i, text_content in enumerate([
        "Retrieval-Augmented Generation (RAG) combines information retrieval with "
        "language model generation. The retrieval component searches a knowledge base "
        "for relevant documents, while the generation component synthesizes answers.",
        "Key components of a RAG system include: vector database for similarity search, "
        "embedding model for document and query encoding, chunking strategy for splitting "
        "documents, and a language model for answer generation.",
    ]):
        chunk = DocumentChunk(
            tenant_id=TENANT_ID,
            document_id=DOC1_ID,
            version_id=VER1_ID,
            chunk_index=i,
            content=text_content,
            token_count=len(text_content.split()),
            embedding_model="text-embedding-3-small",
            sensitivity_level=SensitivityLevel.INTERNAL,
            language="en",
            tags=["architecture", "rag"],
            metadata_={"source": "seed"},
            # embedding omitted — no vector for seed data
        )
        session.add(chunk)

    job1 = IngestionJob(
        tenant_id=TENANT_ID,
        version_id=VER1_ID,
        status=JobStatus.COMPLETED,
        chunks_total=2,
        chunks_processed=2,
    )
    session.add(job1)

    # Document 2 — archived, no versions yet
    doc2 = Document(
        id=DOC2_ID,
        tenant_id=TENANT_ID,
        title="Old Design Document",
        sensitivity_level=SensitivityLevel.CONFIDENTIAL,
        language="en",
        tags=["design", "deprecated"],
        status=DocumentStatus.ARCHIVED,
    )
    session.add(doc2)

    await session.commit()
    print(f"Seed data created: tenant={TENANT_ID}, user={USER_ID}, "
          f"docs=[{DOC1_ID}, {DOC2_ID}]")


async def main() -> None:
    async with async_session_factory() as session:
        await seed(session)
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
