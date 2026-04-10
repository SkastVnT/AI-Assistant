"""Document ingestion routes."""

import uuid

from fastapi import APIRouter, Depends, Form, Header, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import db_session
from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from apps.api.dependencies import auth_context, db_session
from apps.api.schemas import (
    DocumentListResponse,
    DocumentResponse,
    DocumentVersionResponse,
    IngestionJobResponse,
)
from libs.auth.context import AuthContext
from libs.core.models import Document, DocumentVersion, IngestionJob
from libs.ingestion.parsers.registry import get_supported_extensions
from libs.ingestion.pipeline import enqueue_document

router = APIRouter(prefix="/documents", tags=["documents"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB


@router.post("/", status_code=202)
async def upload_document(
    file: UploadFile,
    title: str = Form(...),
    sensitivity_level: str = Form("internal"),
    language: str = Form("en"),
    db: AsyncSession = Depends(db_session),
    x_tenant_id: str = Header(...),
    auth: AuthContext = Depends(auth_context),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """Upload a document and enqueue it for async ingestion.

    Returns 202 Accepted — the job will be processed by the worker.
    Poll GET /documents/jobs/{job_id} for status.
    """
    if not file.filename:
        raise HTTPException(400, "Filename is required")

    # Validate file extension
    from pathlib import PurePath

    ext = PurePath(file.filename).suffix.lower()
    supported = get_supported_extensions()
    if ext not in supported:
        raise HTTPException(
            400,
            f"Unsupported file type: '{ext}'. Supported: {', '.join(sorted(supported))}",
        )

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            413,
            f"File too large. Maximum size: {MAX_FILE_SIZE // (1024 * 1024)} MB",
        )
    if len(content) == 0:
        raise HTTPException(400, "File is empty")

    tenant_id = uuid.UUID(x_tenant_id)
    tenant_id = auth.tenant_id

    # Enforce: non-admins cannot upload restricted docs
    if sensitivity_level == "restricted" and not auth.is_admin:
        raise HTTPException(
            403,
            "Only admins may upload documents with 'restricted' sensitivity.",
        )

    try:
        doc, version, job = await enqueue_document(
            db=db,
            tenant_id=tenant_id,
            title=title,
            filename=file.filename,
            content=content,
            content_type=file.content_type,
            sensitivity_level=sensitivity_level,
            language=language,
        )
        await db.commit()
    except ValueError as e:
        raise HTTPException(409, str(e)) from None

    return {
        "document": DocumentResponse.model_validate(doc).model_dump(),
        "version": DocumentVersionResponse.model_validate(version).model_dump(),
        "job": IngestionJobResponse.model_validate(job).model_dump(),
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: str,
    db: AsyncSession = Depends(db_session),
    x_tenant_id: str = Header(...),
) -> dict:
    """Check the status of an ingestion job."""
    tenant_id = uuid.UUID(x_tenant_id)
    auth: AuthContext = Depends(auth_context),
    db: AsyncSession = Depends(db_session),
) -> dict:
    """Check the status of an ingestion job."""
    tenant_id = auth.tenant_id
    job = await db.get(IngestionJob, uuid.UUID(job_id))
    if not job or job.tenant_id != tenant_id:
        raise HTTPException(404, "Job not found")
    return IngestionJobResponse.model_validate(job).model_dump()


@router.get("/", response_model=DocumentListResponse)
async def list_documents(
    db: AsyncSession = Depends(db_session),
    x_tenant_id: str = Header(...),
    auth: AuthContext = Depends(auth_context),
    db: AsyncSession = Depends(db_session),
    skip: int = 0,
    limit: int = 20,
) -> DocumentListResponse:
    """List all ingested documents for a tenant."""
    tenant_id = uuid.UUID(x_tenant_id)
    tenant_id = auth.tenant_id

    total = await db.scalar(
        select(func.count())
        .select_from(Document)
        .where(Document.tenant_id == tenant_id)
    )
    result = await db.execute(
        select(Document)
        .where(Document.tenant_id == tenant_id)
        .offset(skip)
        .limit(limit)
        .order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()

    items: list[DocumentResponse] = []
    for doc in docs:
        version_count = await db.scalar(
            select(func.count()).where(DocumentVersion.document_id == doc.id)
        )
        resp = DocumentResponse.model_validate(doc)
        resp.version_count = version_count or 0
        items.append(resp)

    return DocumentListResponse(documents=items, total=total or 0)


@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    db: AsyncSession = Depends(db_session),
    x_tenant_id: str = Header(...),
) -> None:
    """Delete a document and all its versions/chunks (cascade)."""
    tenant_id = uuid.UUID(x_tenant_id)
    auth: AuthContext = Depends(auth_context),
    db: AsyncSession = Depends(db_session),
) -> None:
    """Delete a document and all its versions/chunks (cascade)."""
    tenant_id = auth.tenant_id
    doc = await db.get(Document, document_id)
    if not doc or doc.tenant_id != tenant_id:
        raise HTTPException(404, "Document not found")
    await db.delete(doc)
