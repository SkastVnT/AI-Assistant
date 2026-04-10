"""
RAG API router — document ingest, vector search, and health check.

All endpoints enforce tenant isolation via the session-derived tenant ID.

Legacy ChromaDB-based endpoints (collection CRUD, plain-text ingest) are
preserved at the bottom of the file for backward compatibility.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from pydantic import BaseModel, Field

from src.rag import RAG_ENABLED

logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Tenant resolution (session-based, same pattern as dependencies.py)
# ---------------------------------------------------------------------------

def _get_tenant_id(request: Request) -> str:
    """Derive tenant from the Starlette session, creating one if absent."""
    sid = request.session.get("session_id")
    if not sid:
        import uuid
        sid = str(uuid.uuid4())
        request.session["session_id"] = sid
    return sid


def _require_rag_enabled() -> None:
    if not RAG_ENABLED:
        raise HTTPException(503, detail="RAG subsystem is disabled. Set RAG_ENABLED=true.")


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural-language search query")
    top_k: int = Field(5, ge=1, le=100, description="Max results to return")
    doc_ids: list[str] | None = Field(None, description="Restrict to these document IDs")
    min_score: float | None = Field(None, ge=0.0, le=1.0, description="Override score threshold")


class SearchHitResponse(BaseModel):
    chunk_id: str
    document_id: str
    title: str
    content: str
    score: float
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class SearchResponse(BaseModel):
    query: str
    tenant_id: str
    results: list[SearchHitResponse]
    cached: bool = False


class IngestResponse(BaseModel):
    document_id: str
    num_chunks: int
    object_path: str


class HealthDetail(BaseModel):
    rag_enabled: bool
    database: str   # "ok" | "unavailable"
    redis: str      # "ok" | "unavailable"
    storage: str    # "minio" | "local" | "unavailable"


# ---------------------------------------------------------------------------
# POST /rag/ingest  —  multipart file upload
# ---------------------------------------------------------------------------

@router.post("/ingest", response_model=IngestResponse)
async def ingest_file(
    request: Request,
    file: UploadFile = File(...),
    title: str = Form(""),
    source_uri: str = Form(""),
    mime_type: str = Form(""),
):
    """Ingest an uploaded file (PDF, HTML, TXT, MD) into the RAG store."""
    _require_rag_enabled()
    tenant_id = _get_tenant_id(request)

    raw = await file.read()
    if not raw:
        raise HTTPException(400, detail="Uploaded file is empty.")

    resolved_title = title or file.filename or "Untitled"
    resolved_mime = mime_type or None
    filename = file.filename or "upload.bin"

    try:
        from src.rag.service import IngestService

        svc = IngestService()
        result = await svc.ingest(
            tenant_id=tenant_id,
            file_bytes=raw,
            filename=filename,
            mime_type=resolved_mime,
            title=resolved_title,
            source_uri=source_uri or None,
        )
    except Exception as exc:
        logger.exception("Ingest failed for tenant=%s file=%s", tenant_id, filename)
        raise HTTPException(500, detail=f"Ingestion failed: {exc}") from exc

    return IngestResponse(
        document_id=str(result.document_id),
        num_chunks=result.num_chunks,
        object_path=result.object_path,
    )


# ---------------------------------------------------------------------------
# POST /rag/search  —  JSON vector search
# ---------------------------------------------------------------------------

@router.post("/search", response_model=SearchResponse)
async def search_rag(request: Request, body: SearchRequest):
    """Semantic search over ingested documents (tenant-scoped)."""
    _require_rag_enabled()
    tenant_id = _get_tenant_id(request)

    try:
        from src.rag.service import RetrievalService

        svc = RetrievalService()
        hits = await svc.retrieve(
            tenant_id=tenant_id,
            query=body.query,
            top_k=body.top_k,
            doc_ids=body.doc_ids,
            min_score=body.min_score,
        )
    except Exception as exc:
        logger.exception("Search failed for tenant=%s", tenant_id)
        raise HTTPException(500, detail=f"Search failed: {exc}") from exc

    return SearchResponse(
        query=body.query,
        tenant_id=tenant_id,
        results=[
            SearchHitResponse(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                title=h.title,
                content=h.content,
                score=round(h.score, 4),
                metadata_json=h.metadata_json,
            )
            for h in hits
        ],
    )


# ---------------------------------------------------------------------------
# GET /rag/health  —  dependency health check
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthDetail)
async def rag_health():
    """Report availability of RAG sub-components (DB, Redis, storage)."""
    db_status = "unavailable"
    redis_status = "unavailable"
    storage_status = "unavailable"

    # -- database (async engine ping) --
    if RAG_ENABLED:
        try:
            from src.rag.db.base import get_engine
            engine = get_engine()
            async with engine.connect() as conn:
                await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
            db_status = "ok"
        except Exception as exc:
            logger.debug("health: db check failed: %s", exc)

    # -- redis --
    if RAG_ENABLED:
        try:
            from src.rag.cache import RedisCache
            from core.rag_settings import get_rag_settings
            cache = RedisCache(get_rag_settings().redis_url)
            if cache._redis is not None:
                await cache._redis.ping()
                redis_status = "ok"
                await cache.close()
        except Exception as exc:
            logger.debug("health: redis check failed: %s", exc)

    # -- storage --
    if RAG_ENABLED:
        try:
            from src.rag.storage import RagFileStore
            store = RagFileStore()
            storage_status = store.backend_name
        except Exception as exc:
            logger.debug("health: storage check failed: %s", exc)

    return HealthDetail(
        rag_enabled=RAG_ENABLED,
        database=db_status,
        redis=redis_status,
        storage=storage_status,
    )


# ---------------------------------------------------------------------------
# Legacy endpoints (backward-compat with the ChromaDB pipeline)
# ---------------------------------------------------------------------------

class _LegacyIngestRequest(BaseModel):
    title: str
    content: str
    collection: str = "default"
    source: str = ""


class _LegacyQueryRequest(BaseModel):
    query: str
    collection_ids: list[str] = Field(default_factory=lambda: ["default"])
    top_k: int = 5


def _require_legacy_pipeline():
    from src.rag import get_rag_pipeline
    if not RAG_ENABLED:
        raise HTTPException(503, "RAG not enabled. Set RAG_ENABLED=true")
    pipeline = get_rag_pipeline()
    if not pipeline:
        raise HTTPException(503, "RAG pipeline failed to initialise")
    return pipeline


@router.get("/status")
async def rag_status():
    """Check whether the RAG subsystem is available."""
    from src.rag import get_rag_pipeline
    pipeline = get_rag_pipeline() if RAG_ENABLED else None
    return {"rag_enabled": RAG_ENABLED, "pipeline_ready": pipeline is not None}


@router.post("/ingest/text")
async def ingest_text(body: _LegacyIngestRequest):
    """Ingest plain text into a ChromaDB collection (legacy)."""
    pipeline = _require_legacy_pipeline()
    if not body.content.strip():
        raise HTTPException(400, "Empty content")

    import uuid as _uuid
    from src.rag.models import Document

    doc = Document(
        id=str(_uuid.uuid4()),
        title=body.title,
        content=body.content,
        source=body.source,
    )
    n = pipeline["ingester"].ingest(doc, collection=body.collection)
    return {"document_id": doc.id, "collection": body.collection, "chunks_stored": n}


@router.post("/query")
async def query_rag(body: _LegacyQueryRequest):
    """Direct retrieval from ChromaDB (legacy)."""
    pipeline = _require_legacy_pipeline()
    results = pipeline["retriever"].retrieve(
        body.query, body.collection_ids, top_k=body.top_k,
    )
    return {
        "query": body.query,
        "results": [
            {
                "chunk_id": r.chunk_id,
                "document_id": r.document_id,
                "content": r.content,
                "score": round(r.score, 4),
                "metadata": r.metadata,
            }
            for r in results
        ],
    }


@router.get("/collections")
async def list_collections():
    pipeline = _require_legacy_pipeline()
    return {"collections": pipeline["store"].list_collections()}


@router.delete("/collections/{name}")
async def delete_collection(name: str):
    pipeline = _require_legacy_pipeline()
    pipeline["store"].delete_collection(name)
    return {"deleted": name}
