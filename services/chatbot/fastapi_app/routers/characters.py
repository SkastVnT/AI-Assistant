"""FastAPI router — Local character registry.

Mirrors the Flask blueprint at /api/characters/* so the topbar
"Choose character" picker works under both ``USE_FASTAPI=true`` and
the Flask legacy app. Routes are kept verbatim with the Flask version
so the frontend (services/chatbot/static/js/modules/character-picker.js)
needs zero changes.
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse

# core.character_registry is a sync, read-mostly module — safe to
# call from FastAPI handlers without going through asyncio.to_thread.
from core.character_registry import get_registry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/characters", tags=["Characters"])


@router.get("")
@router.get("/")
def list_characters(
    q: str = Query("", description="Free-text search across name/aliases/tag"),
    series: Optional[str] = Query(None, description="Filter by series_key/alias"),
    limit: int = Query(50, ge=1, le=200),
):
    """List/search characters — mirror of Flask's characters_bp.list_characters."""
    reg = get_registry()
    results = reg.find(query=q, series_filter=series, limit=limit)
    return {
        "characters": [r.to_dict() for r in results],
        "count": len(results),
        "query": q,
        "series_filter": series,
    }


@router.get("/series")
def list_series():
    reg = get_registry()
    return {"series": reg.list_series()}


@router.get("/{key}")
def get_character(key: str):
    reg = get_registry()
    rec = reg.get(key)
    if rec is None:
        return JSONResponse(
            status_code=404,
            content={"error": "not_found", "key": key},
        )
    collisions = reg.detect_collisions(rec.display_name)
    return {
        "character": rec.to_dict(),
        "collisions": [c.to_dict() for c in collisions if c.key != rec.key],
    }


@router.get("/{key}/thumbnail")
def get_thumbnail(key: str):
    reg = get_registry()
    rec = reg.get(key)
    if rec is None or not rec.thumbnail:
        raise HTTPException(status_code=404)
    # Resolve relative to repo root (4 levels up from this file:
    # services/chatbot/fastapi_app/routers/characters.py -> repo root)
    repo_root = Path(__file__).resolve().parents[4]
    thumb_path = (repo_root / rec.thumbnail).resolve()
    # Security: keep the resolved path under the repo root.
    try:
        thumb_path.relative_to(repo_root)
    except ValueError:
        raise HTTPException(status_code=403)
    if not thumb_path.exists() or not thumb_path.is_file():
        raise HTTPException(status_code=404)
    return FileResponse(str(thumb_path))


@router.post("/reload")
def reload_registry():
    """Force-reload the registry from disk (admin/dev convenience)."""
    reg = get_registry()
    reg.reload()
    return {"reloaded": True, "count": len(reg.list_all())}


@router.post("/resolve")
async def resolve_query(request: Request):
    """Resolve a free-form query to a single character record."""
    payload = await request.json() if request.headers.get("content-length") else {}
    query = (payload.get("query") or "").strip() if isinstance(payload, dict) else ""
    if not query:
        return JSONResponse(status_code=400, content={"error": "query_required"})
    reg = get_registry()
    rec = reg.resolve_query(query)
    if rec is None:
        return {"resolved": False, "query": query}
    return {"resolved": True, "query": query, "character": rec.to_dict()}
