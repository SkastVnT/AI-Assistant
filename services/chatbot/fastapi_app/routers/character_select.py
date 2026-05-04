"""
Character Select SAA sidecar router — FastAPI parity.

Endpoints:
  GET /api/character-select/status     — feature flag + reachability
  GET /api/character-select/url        — URL the frontend should open
  GET /api/local-image-gen/recent      — list new ComfyUI output files
  GET /api/local-image-gen/file/{name} — serve one file from ComfyUI output
"""
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, JSONResponse

router = APIRouter()
logger = logging.getLogger("chatbot.fastapi.character_select")


@router.get(
    "/api/character-select/status",
    tags=["Tools"],
    summary="Character Select sidecar status",
)
async def character_select_status():
    try:
        from core.character_select_adapter import get_status, install_path_exists
        result = get_status()
        result["installed"] = install_path_exists()
        return result
    except Exception as exc:
        logger.error("[CHARACTER-SELECT-ROUTE] Status error: %s", exc)
        return {
            "enabled": False,
            "reachable": False,
            "running": False,
            "error": f"Internal error: {exc}",
        }


@router.get(
    "/api/character-select/url",
    tags=["Tools"],
    summary="Character Select sidecar URL",
)
async def character_select_url():
    from core.config import CHARACTER_SELECT_ENABLED, CHARACTER_SELECT_URL
    return {
        "enabled": bool(CHARACTER_SELECT_ENABLED),
        "url": CHARACTER_SELECT_URL,
    }


# ── Local image gen bridge (ComfyUI output watcher) ──────────────────


@router.get(
    "/api/local-image-gen/recent",
    tags=["Tools"],
    summary="List new ComfyUI output images",
)
async def local_image_gen_recent(
    since: float = Query(0.0, ge=0.0),
    limit: int = Query(12, ge=1, le=48),
):
    from core.local_image_gen_watch import list_recent
    payload = list_recent(since=since, limit=limit)
    status = 200 if payload.get("ok") else 503
    return JSONResponse(payload, status_code=status)


@router.get(
    "/api/local-image-gen/file/{name:path}",
    tags=["Tools"],
    summary="Serve one ComfyUI output file",
)
async def local_image_gen_file(name: str):
    from core.local_image_gen_watch import resolve_file
    path, mime = resolve_file(name)
    if path is None:
        raise HTTPException(status_code=404, detail="not_found")
    return FileResponse(str(path), media_type=mime)


# ── Tag autocomplete (Danbooru tag DB) ───────────────────────────────


@router.get(
    "/api/tags/autocomplete",
    tags=["Tools"],
    summary="Autocomplete Danbooru-style tags",
)
async def tags_autocomplete(
    q: str = Query("", description="prefix or substring query"),
    limit: int = Query(20, ge=1, le=50),
):
    q = (q or "").strip()
    if len(q) < 1:
        return {"ok": True, "tags": []}
    try:
        from image_pipeline.anime_pipeline.saa_character_db import autocomplete_tag
        hits = autocomplete_tag(q, limit=limit)
        return {"ok": True, "tags": hits}
    except Exception as exc:
        logger.warning("[TAGS-AUTOCOMPLETE] %s", exc)
        return JSONResponse({"ok": False, "tags": [], "error": str(exc)}, status_code=200)

