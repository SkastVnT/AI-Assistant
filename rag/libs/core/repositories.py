"""Repository interfaces (abstract base) for domain models.

Repositories encapsulate data access logic and provide a clean seam
for unit testing (mock the repo, not the DB).

Concrete implementations use SQLAlchemy AsyncSession.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from libs.core.models import (
    DataSource,
    Document,
    DocumentChunk,
    DocumentVersion,
    IngestionJob,
    RetrievalTrace,
    Tenant,
    User,
)


class TenantRepository(ABC):
    @abstractmethod
    async def get_by_id(self, tenant_id: UUID) -> Tenant | None: ...

    @abstractmethod
    async def get_by_slug(self, slug: str) -> Tenant | None: ...

    @abstractmethod
    async def create(self, tenant: Tenant) -> Tenant: ...

    @abstractmethod
    async def update(self, tenant: Tenant) -> Tenant: ...

    @abstractmethod
    async def list_all(self, *, offset: int = 0, limit: int = 50) -> list[Tenant]: ...


class UserRepository(ABC):
    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None: ...

    @abstractmethod
    async def get_by_email(self, tenant_id: UUID, email: str) -> User | None: ...

    @abstractmethod
    async def create(self, user: User) -> User: ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[User]: ...


class DataSourceRepository(ABC):
    @abstractmethod
    async def get_by_id(self, ds_id: UUID) -> DataSource | None: ...

    @abstractmethod
    async def create(self, ds: DataSource) -> DataSource: ...

    @abstractmethod
    async def update(self, ds: DataSource) -> DataSource: ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[DataSource]: ...


class DocumentRepository(ABC):
    @abstractmethod
    async def get_by_id(self, doc_id: UUID) -> Document | None: ...

    @abstractmethod
    async def create(self, doc: Document) -> Document: ...

    @abstractmethod
    async def update(self, doc: Document) -> Document: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> tuple[list[Document], int]: ...

    @abstractmethod
    async def count_by_tenant(self, tenant_id: UUID) -> int: ...


class DocumentVersionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, version_id: UUID) -> DocumentVersion | None: ...

    @abstractmethod
    async def create(self, version: DocumentVersion) -> DocumentVersion: ...

    @abstractmethod
    async def update(self, version: DocumentVersion) -> DocumentVersion: ...

    @abstractmethod
    async def get_latest(self, document_id: UUID) -> DocumentVersion | None: ...

    @abstractmethod
    async def list_by_document(
        self, document_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[DocumentVersion]: ...

    @abstractmethod
    async def get_next_version_number(self, document_id: UUID) -> int: ...

    @abstractmethod
    async def find_by_checksum(
        self, tenant_id: UUID, checksum: str
    ) -> DocumentVersion | None: ...

    @abstractmethod
    async def mark_superseded(
        self, document_id: UUID, *, exclude_version_id: UUID
    ) -> int: ...


class DocumentChunkRepository(ABC):
    @abstractmethod
    async def create_many(self, chunks: list[DocumentChunk]) -> None: ...

    @abstractmethod
    async def get_by_version(self, version_id: UUID) -> list[DocumentChunk]: ...

    @abstractmethod
    async def delete_by_version(self, version_id: UUID) -> int: ...

    @abstractmethod
    async def count_by_version(self, version_id: UUID) -> int: ...

    @abstractmethod
    async def get_unembedded(
        self, *, tenant_id: UUID | None = None, limit: int = 500
    ) -> list[DocumentChunk]: ...

    @abstractmethod
    async def get_by_version_for_reembed(
        self, version_id: UUID
    ) -> list[DocumentChunk]: ...

    @abstractmethod
    async def get_all_by_tenant(
        self, tenant_id: UUID, *, limit: int = 500, offset: int = 0
    ) -> list[DocumentChunk]: ...

    @abstractmethod
    async def bulk_update_embeddings(
        self, updates: list[tuple[UUID, list[float], str, str]]
    ) -> int: ...


class IngestionJobRepository(ABC):
    @abstractmethod
    async def get_by_id(self, job_id: UUID) -> IngestionJob | None: ...

    @abstractmethod
    async def create(self, job: IngestionJob) -> IngestionJob: ...

    @abstractmethod
    async def update(self, job: IngestionJob) -> IngestionJob: ...

    @abstractmethod
    async def list_by_tenant(
        self,
        tenant_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
        status: str | None = None,
    ) -> list[IngestionJob]: ...


class RetrievalTraceRepository(ABC):
    @abstractmethod
    async def create(self, trace: RetrievalTrace) -> RetrievalTrace: ...

    @abstractmethod
    async def get_by_id(self, trace_id: UUID) -> RetrievalTrace | None: ...

    @abstractmethod
    async def update_feedback(
        self, trace_id: UUID, score: float
    ) -> RetrievalTrace | None: ...

    @abstractmethod
    async def list_by_tenant(
        self, tenant_id: UUID, *, offset: int = 0, limit: int = 50
    ) -> list[RetrievalTrace]: ...
