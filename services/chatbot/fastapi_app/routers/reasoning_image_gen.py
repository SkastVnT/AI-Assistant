"""
FastAPI Reasoning Image Gen Router (Cycle 7.6).

Mirrors the Flask ``routes.reasoning_image_gen`` blueprint so the chat UI's
``reasoning-image-gen.js`` button (which probes ``/api/reasoning-image-gen/status``)
works in FastAPI mode too.

The router is only included by ``fastapi_app/__init__.py`` when
``REASONING_PIPELINE_ENABLED`` is true. When the flag is off, the URL map
is byte-identical to before and the JS button silently removes itself
(its ``init()`` handles 404 as a no-op).

Both endpoints reuse the same ``run_pipeline_for_prompt()`` helper that
the Flask blueprint exposes — there is no duplicate pipeline logic.
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("chatbot.reasoning_image_gen")

router = APIRouter(prefix="/api/reasoning-image-gen", tags=["Reasoning Image Generation"])


@router.get("/status")
async def status():
    """Lightweight introspection — confirms flag is on and dependencies load."""
    from core.config import (
        REASONING_PIPELINE_COMFY_URL,
        REASONING_PIPELINE_MAX_CORRECTION_PASSES,
        REASONING_PIPELINE_MAX_PANELS,
    )
    return {
        "enabled": True,
        "comfy_url": REASONING_PIPELINE_COMFY_URL,
        "max_panels": REASONING_PIPELINE_MAX_PANELS,
        "max_correction_passes": REASONING_PIPELINE_MAX_CORRECTION_PASSES,
    }


@router.post("/generate")
async def generate(request: Request):
    """HTTP wrapper around :func:`routes.reasoning_image_gen.run_pipeline_for_prompt`.

    Same request / response contract as the Flask variant.
    """
    try:
        payload = await request.json()
    except Exception:
        payload = {}

    # Lazy import keeps the heavy ``image_pipeline.reasoning`` graph out of
    # module load when the flag is off (matches Flask hygiene).
    from routes.reasoning_image_gen import run_pipeline_for_prompt

    result = run_pipeline_for_prompt(
        payload.get("prompt") or "",
        layout=payload.get("layout"),
        attached_images=payload.get("attached_images") or 0,
        character_hint=payload.get("character_hint"),
    )
    status_code = int(result.pop("status_code", 200))
    return JSONResponse(result, status_code=status_code)
