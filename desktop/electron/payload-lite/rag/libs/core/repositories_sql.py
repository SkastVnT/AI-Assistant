"""Concrete SQLAlchemy implementations of repository interfaces."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from libs.core.models import (
    DataSource,
    Document,
    DocumentChunk,
    DocumentVersion,
    IngestionJob,
    RetrievalTrace,
    Tenant,
    User,
    VersionStatus,
)
from libs.core.repositories import (
    DataSourceRepository,
    DocumentChunkRepository,
    DocumentRepository,
    DocumentVersionRepository,
    IngestionJobRepository,
    RetrievalTraceRepository,
    TenantRepository,
    UserRepository,
)


class SqlTenantRepository(TenantRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, tenant_id: UUID) -> Tenant | None:
        return await self._db.get(Tenant, tenant_id)

    async def get_by_slug(self, slug: str) -> Tenant | None:
        result = await self._db.execute(select(Tenant).where(Tenant.slug == slug))
        return result.scalar_one_or_none()

    async def create(self, tenant: Tenant) -> Tenant:
        self._db.add(tenant)
        await self._db.flush()
        return tenant

    async def update(self, tenant: Tenant) -> Tenant:
        await self._db.flush()
        return tenant

    async def list_all(self, *, offset: int = 0, limit: int = 50) -> list[Tenant]:
        result = await self._db.execute(
            select(Tenant).offset(offset).limit(limit).order_by(Tenant.created_at)
        )
        return list(result.scalars().all())


class SqlUserRepository(UserRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self._db.get(User, user_id)

    async def get_by_email(self, tenant_id: UUID, email: str) -> User | None:
        result = await self._db.execute(
            select(User).where(User.tenant_id == tenant_id, User.email == email)
        )
        return result.scalar_one_or_none()

    async def create(self, user: User) -> User:
        self._db.add(user)
        await self._db.flush()
        return user

    async def list_by_tenant(
        self, tenant_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[User]:
        result = await self._db.execute(
            select(User)
            .where(User.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
            .order_by(User.created_at)
        )
        return list(result.scalars().all())


class SqlDataSourceRepository(DataSourceRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, ds_id: UUID) -> DataSource | None:
        return await self._db.get(DataSource, ds_id)

    async def create(self, ds: DataSource) -> DataSource:
        self._db.add(ds)
        await self._db.flush()
        return ds

    async def update(self, ds: DataSource) -> DataSource:
        await self._db.flush()
        return ds

    async def list_by_tenant(
        self, tenant_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[DataSource]:
        result = await self._db.execute(
            select(DataSource)
            .where(DataSource.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
            .order_by(DataSource.created_at)
        )
        return list(result.scalars().all())


class SqlDocumentRepository(DocumentRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, doc_id: UUID) -> Document | None:
        return await self._db.get(Document, doc_id)

    async def create(self, doc: Document) -> Document:
        self._db.add(doc)
        await self._db.flush()
        return doc

    async def update(self, doc: Document) -> Document:
        await self._db.flush()
        return doc

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[list[Document], int]:
        base = select(Document).where(Document.tenant_id == tenant_id)
        if status:
            base = base.where(Document.status == status)

        count_q = select(func.count()).select_from(base.subquery())
        total = await self._db.scalar(count_q) or 0

        result = await self._db.execute(
            base.offset(offset).limit(limit).order_by(desc(Document.created_at))
        )
        return list(result.scalars().all()), total

    async def count_by_tenant(self, tenant_id: UUID) -> int:
        result = await self._db.scalar(
            select(func.count()).where(Document.tenant_id == tenant_id)
        )
        return result or 0


class SqlDocumentVersionRepository(DocumentVersionRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, version_id: UUID) -> DocumentVersion | None:
        return await self._db.get(DocumentVersion, version_id)

    async def create(self, version: DocumentVersion) -> DocumentVersion:
        self._db.add(version)
        await self._db.flush()
        return version

    async def update(self, version: DocumentVersion) -> DocumentVersion:
        await self._db.flush()
        return version

    async def get_latest(self, document_id: UUID) -> DocumentVersion | None:
        result = await self._db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .order_by(desc(DocumentVersion.version_number))
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_by_document(
        self, document_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[DocumentVersion]:
        result = await self._db.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == document_id)
            .offset(offset)
            .limit(limit)
            .order_by(desc(DocumentVersion.version_number))
        )
        return list(result.scalars().all())

    async def get_next_version_number(self, document_id: UUID) -> int:
        max_ver = await self._db.scalar(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document_id
            )
        )
        return (max_ver or 0) + 1

    async def find_by_checksum(
        self, tenant_id: UUID, checksum: str
    ) -> DocumentVersion | None:
        result = await self._db.execute(
            select(DocumentVersion).where(
                DocumentVersion.tenant_id == tenant_id,
                DocumentVersion.checksum == checksum,
            )
        )
        return result.scalar_one_or_none()

    async def mark_superseded(
        self, document_id: UUID, *, exclude_version_id: UUID
    ) -> int:
        result = await self._db.execute(
            update(DocumentVersion)
            .where(
                DocumentVersion.document_id == document_id,
                DocumentVersion.id != exclude_version_id,
                DocumentVersion.status == VersionStatus.READY,
            )
            .values(status=VersionStatus.SUPERSEDED)
        )
        await self._db.flush()
        return result.rowcount


class SqlDocumentChunkRepository(DocumentChunkRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create_many(self, chunks: list[DocumentChunk]) -> None:
        self._db.add_all(chunks)
        await self._db.flush()

    async def get_by_version(self, version_id: UUID) -> list[DocumentChunk]:
        result = await self._db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.version_id == version_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def delete_by_version(self, version_id: UUID) -> int:
        from sqlalchemy import delete

        result = await self._db.execute(
            delete(DocumentChunk).where(DocumentChunk.version_id == version_id)
        )
        return result.rowcount

    async def count_by_version(self, version_id: UUID) -> int:
        result = await self._db.scalar(
            select(func.count()).where(DocumentChunk.version_id == version_id)
        )
        return result or 0

    async def get_unembedded(
        self, *, tenant_id: UUID | None = None, limit: int = 500
    ) -> list[DocumentChunk]:
        q = select(DocumentChunk).where(DocumentChunk.embedding.is_(None))
        if tenant_id:
            q = q.where(DocumentChunk.tenant_id == tenant_id)
        q = q.order_by(DocumentChunk.created_at).limit(limit)
        result = await self._db.execute(q)
        return list(result.scalars().all())

    async def get_by_version_for_reembed(
        self, version_id: UUID
    ) -> list[DocumentChunk]:
        result = await self._db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.version_id == version_id)
            .order_by(DocumentChunk.chunk_index)
        )
        return list(result.scalars().all())

    async def get_all_by_tenant(
        self, tenant_id: UUID, *, limit: int = 500, offset: int = 0
    ) -> list[DocumentChunk]:
        result = await self._db.execute(
            select(DocumentChunk)
            .where(DocumentChunk.tenant_id == tenant_id)
            .order_by(DocumentChunk.created_at)
            .offset(offset)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def bulk_update_embeddings(
        self, updates: list[tuple[UUID, list[float], str, str]]
    ) -> int:
        """Update embeddings for multiple chunks.

        Each tuple: (chunk_id, embedding_vector, embedding_model, embedding_version).
        """
        count = 0
        for chunk_id, embedding, model, version in updates:
            await self._db.execute(
                update(DocumentChunk)
                .where(DocumentChunk.id == chunk_id)
                .values(
                    embedding=embedding,
                    embedding_model=model,
                    embedding_version=version,
                )
            )
            count += 1
        await self._db.flush()
        return count


class SqlIngestionJobRepository(IngestionJobRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def get_by_id(self, job_id: UUID) -> IngestionJob | None:
        return await self._db.get(IngestionJob, job_id)

    async def create(self, job: IngestionJob) -> IngestionJob:
        self._db.add(job)
        await self._db.flush()
        return job

    async def update(self, job: IngestionJob) -> IngestionJob:
        await self._db.flush()
        return job

    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> list[IngestionJob]:
        base = select(IngestionJob).where(IngestionJob.tenant_id == tenant_id)
        if status:
            base = base.where(IngestionJob.status == status)
        result = await self._db.execute(
            base.offset(offset).limit(limit).order_by(desc(IngestionJob.created_at))
        )
        return list(result.scalars().all())


class SqlRetrievalTraceRepository(RetrievalTraceRepository):
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, trace: RetrievalTrace) -> RetrievalTrace:
        self._db.add(trace)
        await self._db.flush()
        return trace

    async def get_by_id(self, trace_id: UUID) -> RetrievalTrace | None:
        return await self._db.get(RetrievalTrace, trace_id)

    async def update_feedback(
        self, trace_id: UUID, score: float
    ) -> RetrievalTrace | None:
        trace = await self._db.get(RetrievalTrace, trace_id)
        if trace:
            trace.feedback_score = score
            await self._db.flush()
        return trace

    async def list_by_tenant(
        self, tenant_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[RetrievalTrace]:
        result = await self._db.execute(
            select(RetrievalTrace)
            .where(RetrievalTrace.tenant_id == tenant_id)
            .offset(offset)
            .limit(limit)
            .order_by(desc(RetrievalTrace.created_at))
        )
        return list(result.scalars().all())
