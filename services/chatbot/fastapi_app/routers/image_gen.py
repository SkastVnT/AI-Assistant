"""
FastAPI Image Generation Router
Mirrors routes/image_gen.py (Flask Blueprint) for the FastAPI mode.

Endpoints:
    POST /api/image-gen/stream             → SSE streaming generation (primary)
    POST /api/image-gen/generate           → Blocking generation
    POST /api/image-gen/edit               → Edit/inpaint
    GET  /api/image-gen/providers          → List providers
    GET  /api/image-gen/styles             → List styles
    GET  /api/image-gen/health             → Provider health
    GET  /api/image-gen/stats              → Usage stats
    GET  /api/image-gen/gallery            → Recent images
    GET  /api/image-gen/loras              → Available LoRAs
    GET  /api/image-gen/workflow-presets   → Workflow presets
    GET  /api/image-gen/images/{id}        → Serve stored image
    DELETE /api/image-gen/images/{id}      → Delete image
    POST /api/image-gen/detect-characters  → Character detection
    GET  /api/image-gen/characters         → Detectable characters
"""
from __future__ import annotations

import json as _json
import logging
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, StreamingResponse

logger = logging.getLogger("chatbot.image_gen")

router = APIRouter(prefix="/api/image-gen", tags=["Image Generation"])

# ── Module-level singletons (lazy init) ──────────────────────────────────────

_router: object = None
_sessions: object = None
_storage: object = None

_MAX_PROMPT = 2000
_MAX_DIM = 3840
_MIN_DIM = 64
_MAX_STEPS = 150

# ── Cost tracking (in-process list, mirrors Flask) ───────────────────────────

_cost_log: list = []


def _log_cost(gen_type: str, provider: str, model: str, cost_usd: float):
    from datetime import datetime
    _cost_log.append({
        "type": gen_type, "provider": provider, "model": model,
        "cost_usd": round(cost_usd, 6), "timestamp": datetime.now().isoformat(),
    })
    if len(_cost_log) > 500:
        del _cost_log[: len(_cost_log) - 500]


def _get_cost_summary() -> dict:
    total = sum(c["cost_usd"] for c in _cost_log)
    return {"total_usd": round(total, 4), "count": len(_cost_log), "recent": _cost_log[-10:]}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_router():
    global _router
    if _router is None:
        from core.image_gen import ImageGenerationRouter
        _router = ImageGenerationRouter()
    return _router


def _get_sessions():
    global _sessions
    if _sessions is None:
        from core.image_gen import SessionManager
        _sessions = SessionManager()
    return _sessions


def _get_storage():
    global _storage
    if _storage is None:
        from core.image_gen import ImageStorage
        _storage = ImageStorage()
    return _storage


def _validate(data: dict) -> Optional[str]:
    if len(data.get("prompt", "")) > _MAX_PROMPT:
        return f"prompt too long (max {_MAX_PROMPT})"
    for d in ("width", "height"):
        v = data.get(d)
        if v is not None:
            try:
                v = int(v)
            except (TypeError, ValueError):
                return f"invalid {d}"
            if not (_MIN_DIM <= v <= _MAX_DIM):
                return f"{d} must be {_MIN_DIM}–{_MAX_DIM}"
    steps = data.get("steps")
    if steps is not None:
        try:
            steps = int(steps)
        except (TypeError, ValueError):
            return "invalid steps"
        if steps > _MAX_STEPS:
            return f"steps max {_MAX_STEPS}"
    return None


def _sse(event: str, data: dict) -> str:
    """Format a single SSE message."""
    return f"event: {event}\ndata: {_json.dumps(data)}\n\n"


def _save_to_gallery(saved: dict, prompt: str, provider: str, model: str, conversation_id: str):
    """Persist generation to DB gallery (best-effort)."""
    try:
        from core.extensions import get_db
        db = get_db()
        if db is None:
            return
        from datetime import datetime
        db.image_gallery.insert_one({
            "image_id": saved.get("image_id", ""),
            "prompt": prompt,
            "provider": provider,
            "model": model,
            "url": saved.get("url", ""),
            "cloud_url": saved.get("cloud_url", ""),
            "local_path": saved.get("local_path", ""),
            "conversation_id": conversation_id,
            "created_at": datetime.utcnow(),
        })
    except Exception:
        pass


# ── POST /api/image-gen/stream  (SSE — primary endpoint) ─────────────────────

@router.post("/stream")
async def generate_image_stream(request: Request):
    """
    Stream image generation with real-time SSE status updates.
    Events: status | provider_try | provider_fail | provider_success | result | saved | error
    """
    try:
        data = await request.json()
    except Exception:
        data = {}

    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        def _err():
            yield _sse("error", {"error": "prompt is required"})
        return StreamingResponse(_err(), media_type="text/event-stream", status_code=400)

    val_err = _validate(data)
    if val_err:
        def _val_err():
            yield _sse("error", {"error": val_err})
        return StreamingResponse(_val_err(), media_type="text/event-stream", status_code=400)

    conversation_id = data.get("conversation_id") or request.session.get("conversation_id", "")
    igv2_router = _get_router()
    sessions = _get_sessions()
    storage = _get_storage()
    img_session = sessions.get_or_create(conversation_id)
    context = img_session.get_context_for_enhancement() if img_session.history else None

    from core.image_gen import QualityMode

    def _stream():
        try:
            final_result = None
            for evt in igv2_router.generate_stream(
                prompt=prompt,
                quality=data.get("quality", QualityMode.AUTO),
                style=data.get("style"),
                width=data.get("width", 1024),
                height=data.get("height", 1024),
                steps=data.get("steps", 28),
                guidance=data.get("guidance", 3.5),
                seed=data.get("seed"),
                num_images=data.get("num_images", 1),
                provider_name=data.get("provider"),
                model_name=data.get("model"),
                enhance_prompt=data.get("enhance", True),
                context=context,
                negative_prompt=data.get("negative_prompt", ""),
                lora_models=data.get("loras"),
                vae_name=data.get("vae"),
                checkpoint=data.get("checkpoint"),
                preset_id=data.get("preset_id"),
                hires_fix=data.get("hires_fix", False),
                hires_scale=float(data.get("hires_scale", 1.5)),
                hires_denoise=float(data.get("hires_denoise", 0.45)),
                hires_steps=int(data.get("hires_steps", 15)),
            ):
                event_type = evt["event"]
                event_data = evt["data"]
                yield _sse(event_type, event_data)

                if event_type == "result":
                    final_result = event_data
                elif event_type == "error":
                    return

            if final_result and final_result.get("success"):
                saved_images = []
                for img_b64 in final_result.get("images_b64", []):
                    saved = storage.save(
                        image_b64=img_b64,
                        prompt=prompt,
                        provider=final_result["provider"],
                        model=final_result["model"],
                        conversation_id=conversation_id,
                        metadata=final_result.get("metadata", {}),
                    )
                    saved_images.append(saved)
                    _save_to_gallery(saved, prompt, final_result["provider"],
                                     final_result["model"], conversation_id)

                for img_url in final_result.get("images_url", []):
                    saved = storage.save(
                        image_url=img_url,
                        prompt=prompt,
                        provider=final_result["provider"],
                        model=final_result["model"],
                        conversation_id=conversation_id,
                        metadata=final_result.get("metadata", {}),
                    )
                    saved_images.append(saved)
                    _save_to_gallery(saved, prompt, final_result["provider"],
                                     final_result["model"], conversation_id)

                try:
                    from core.image_gen.providers.base import ImageResult as _ImageResult
                    result_obj = _ImageResult(
                        success=True,
                        provider=final_result["provider"],
                        model=final_result["model"],
                        images_url=final_result.get("images_url", []),
                        images_b64=final_result.get("images_b64", []),
                        prompt_used=final_result.get("prompt_used", prompt),
                        cost_usd=final_result.get("cost_usd", 0),
                        latency_ms=final_result.get("latency_ms", 0),
                        metadata=final_result.get("metadata", {}),
                    )
                    img_session.add_generation(
                        user_prompt=prompt,
                        enhanced_prompt=final_result.get("prompt_used", prompt),
                        result=result_obj,
                    )
                except Exception:
                    pass

                if data.get("style"):
                    img_session.active_style = data["style"]
                if final_result.get("cost_usd", 0) > 0:
                    _log_cost("generate", final_result["provider"],
                              final_result["model"], final_result["cost_usd"])

                images_out = [
                    {"url": s.get("url", ""), "image_id": s.get("image_id", ""), "local_path": s.get("local_path", "")}
                    for s in saved_images if not s.get("error")
                ]
                yield _sse("saved", {"images": images_out})

                try:
                    from core.private_logger import log_image_generation
                    for s in saved_images:
                        if not s.get("error"):
                            log_image_generation(
                                prompt=prompt, provider=final_result["provider"],
                                model=final_result["model"],
                                image_url=s.get("url", ""),
                                image_path=s.get("local_path", ""),
                                session_id=conversation_id, mode="txt2img",
                                extra={
                                    "prompt_used": final_result.get("prompt_used"),
                                    "cost_usd": final_result.get("cost_usd"),
                                    "latency_ms": final_result.get("latency_ms"),
                                    "style": data.get("style"),
                                },
                            )
                except Exception:
                    pass

        except GeneratorExit:
            logger.info("[ImageGen SSE] Client disconnected")
        except Exception as e:
            logger.error(f"[ImageGen SSE] Error: {e}")
            yield _sse("error", {"error": str(e)})

    return StreamingResponse(
        _stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ── POST /api/image-gen/generate  (blocking) ─────────────────────────────────

@router.post("/generate")
async def generate_image(request: Request):
    """
    Generate image(s) synchronously.
    Returns all result data in a single JSON response.
    """
    try:
        data = await request.json()
    except Exception:
        data = {}

    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"success": False, "error": "prompt is required"}, status_code=400)

    val_err = _validate(data)
    if val_err:
        return JSONResponse({"success": False, "error": val_err}, status_code=400)

    conversation_id = data.get("conversation_id") or request.session.get("conversation_id", "")
    igv2_router = _get_router()
    sessions = _get_sessions()
    storage = _get_storage()
    img_session = sessions.get_or_create(conversation_id)
    context = img_session.get_context_for_enhancement() if img_session.history else None

    from core.image_gen import QualityMode

    try:
        result = igv2_router.generate(
            prompt=prompt,
            quality=data.get("quality", QualityMode.AUTO),
            style=data.get("style"),
            width=data.get("width", 1024),
            height=data.get("height", 1024),
            steps=data.get("steps", 28),
            guidance=data.get("guidance", 3.5),
            seed=data.get("seed"),
            num_images=data.get("num_images", 1),
            provider_name=data.get("provider"),
            model_name=data.get("model"),
            enhance_prompt=data.get("enhance", True),
            context=context,
            lora_models=data.get("loras"),
            vae_name=data.get("vae"),
            checkpoint=data.get("checkpoint"),
            preset_id=data.get("preset_id"),
            hires_fix=data.get("hires_fix", False),
            hires_scale=float(data.get("hires_scale", 1.5)),
            hires_denoise=float(data.get("hires_denoise", 0.45)),
            hires_steps=int(data.get("hires_steps", 15)),
        )
        if not result.success:
            return JSONResponse({"success": False, "error": result.error or "Generation failed"}, status_code=500)

        saved_images = []
        for img_b64 in result.images_b64:
            saved = storage.save(
                image_b64=img_b64,
                prompt=prompt,
                provider=result.provider,
                model=result.model,
                conversation_id=conversation_id,
                metadata=result.metadata or {},
            )
            saved_images.append(saved)
        for img_url in result.images_url:
            saved = storage.save(
                image_url=img_url,
                prompt=prompt,
                provider=result.provider,
                model=result.model,
                conversation_id=conversation_id,
                metadata=result.metadata or {},
            )
            saved_images.append(saved)

        images_out = [
            {"url": s.get("url", ""), "image_id": s.get("image_id", ""), "local_path": s.get("local_path", "")}
            for s in saved_images if not s.get("error")
        ]
        return {
            "success": True,
            "images": images_out,
            "provider": result.provider,
            "model": result.model,
            "prompt_used": result.prompt_used,
            "cost_usd": result.cost_usd,
            "latency_ms": result.latency_ms,
        }
    except Exception as e:
        logger.error(f"[ImageGen] Generate error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ── GET /api/image-gen/providers ─────────────────────────────────────────────

@router.get("/providers")
async def list_providers():
    try:
        igv2_router = _get_router()
        return {"providers": igv2_router.get_available_providers()}
    except Exception as e:
        logger.warning(f"[ImageGen] Providers error: {e}")
        return {"providers": []}


# ── GET /api/image-gen/styles ────────────────────────────────────────────────

@router.get("/styles")
async def list_styles():
    try:
        from core.image_gen import STYLE_PRESETS
        styles = [{"name": k, "description": v} for k, v in STYLE_PRESETS.items()]
    except Exception:
        styles = []
    return {"styles": styles}


# ── GET /api/image-gen/health ────────────────────────────────────────────────

@router.get("/health")
async def health_check():
    try:
        igv2_router = _get_router()
        return {"health": igv2_router.health_check()}
    except Exception as e:
        return {"health": {}, "error": str(e)}


# ── GET /api/image-gen/stats ─────────────────────────────────────────────────

@router.get("/stats")
async def image_stats():
    try:
        igv2_router = _get_router()
        storage = _get_storage()
        return {
            "generation": igv2_router.get_stats(),
            "storage": storage.get_disk_usage(),
            "costs": _get_cost_summary(),
        }
    except Exception as e:
        return {"error": str(e)}


# ── GET /api/image-gen/gallery ───────────────────────────────────────────────

@router.get("/gallery")
async def gallery(limit: int = 20, conversation_id: str = ""):
    try:
        storage = _get_storage()
        images = storage.list_recent(limit=limit, conversation_id=conversation_id)
        return {"images": images, "total": len(images)}
    except Exception as e:
        return {"images": [], "total": 0, "error": str(e)}


# ── GET /api/image-gen/images/{image_id} ─────────────────────────────────────

@router.get("/images/{image_id}")
async def serve_image(image_id: str):
    try:
        storage = _get_storage()
        path = storage.get_path(image_id)
        if path and path.exists():
            from fastapi.responses import FileResponse
            return FileResponse(str(path))
        return JSONResponse({"error": "Image not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── DELETE /api/image-gen/images/{image_id} ──────────────────────────────────

@router.delete("/images/{image_id}")
async def delete_image(image_id: str):
    try:
        storage = _get_storage()
        ok = storage.delete(image_id)
        return {"success": ok}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ── POST /api/image-gen/save/{image_id} ──────────────────────────────────────

@router.post("/save/{image_id}")
async def save_image(image_id: str, request: Request):
    """Mark a generated image as explicitly saved/favourited."""
    try:
        storage = _get_storage()
        result = storage.mark_saved(image_id)
        return {"success": bool(result)}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ── GET /api/image-gen/meta/{image_id} ───────────────────────────────────────

@router.get("/meta/{image_id}")
async def get_image_meta(image_id: str):
    try:
        storage = _get_storage()
        meta = storage.get_meta(image_id)
        if meta:
            return meta
        return JSONResponse({"error": "Not found"}, status_code=404)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── GET /api/image-gen/loras ─────────────────────────────────────────────────

@router.get("/loras")
async def list_loras():
    try:
        from config.model_presets import LORA_CATALOG
    except ImportError:
        LORA_CATALOG = {}
    try:
        igv2_router = _get_router()
        live_loras = igv2_router.get_available_loras()
    except Exception:
        live_loras = []
    catalog = [
        {
            "key": k, "file": v["file"], "category": v.get("category", ""),
            "trigger": v.get("trigger", []), "base": v.get("base", ""),
        }
        for k, v in LORA_CATALOG.items()
    ]
    return {
        "catalog": catalog, "live": live_loras,
        "total_catalog": len(catalog), "total_live": len(live_loras),
    }


# ── GET /api/image-gen/workflow-presets ──────────────────────────────────────

@router.get("/workflow-presets")
async def list_workflow_presets():
    try:
        from config.model_presets import get_all_workflow_presets
        presets = get_all_workflow_presets()
    except ImportError:
        presets = {}
    return {"presets": presets}


@router.get("/workflow-presets/{preset_id}")
async def get_workflow_preset(preset_id: str):
    try:
        from config.model_presets import get_workflow_preset, resolve_loras_for_preset
        preset = get_workflow_preset(preset_id)
        if not preset:
            return JSONResponse({"error": f"Preset '{preset_id}' not found"}, status_code=404)
        loras = resolve_loras_for_preset(preset_id)
        return {"preset": {"id": preset_id, **preset}, "resolved_loras": loras}
    except ImportError:
        return JSONResponse({"error": "Presets not available"}, status_code=500)


# ── POST /api/image-gen/detect-characters ────────────────────────────────────

@router.post("/detect-characters")
async def detect_characters(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)
    try:
        igv2_router = _get_router()
        return igv2_router.detect_characters(prompt)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── GET /api/image-gen/characters ────────────────────────────────────────────

@router.get("/characters")
async def list_characters():
    try:
        igv2_router = _get_router()
        characters = igv2_router.get_detectable_characters()
        return {"characters": characters, "total": len(characters)}
    except Exception as e:
        return {"characters": [], "total": 0, "error": str(e)}


# ── POST /api/image-gen/edit ─────────────────────────────────────────────────

@router.post("/edit")
async def edit_image_endpoint(request: Request):
    """Edit / inpaint a previously generated image."""
    try:
        data = await request.json()
    except Exception:
        data = {}
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return JSONResponse({"success": False, "error": "prompt is required"}, status_code=400)

    try:
        igv2_router = _get_router()
        storage = _get_storage()
        conversation_id = data.get("conversation_id") or request.session.get("conversation_id", "")

        # Build image input
        image_b64 = data.get("image_b64") or data.get("init_image")
        image_url = data.get("image_url") or data.get("image_src")

        result = igv2_router.edit(
            prompt=prompt,
            image_b64=image_b64,
            image_url=image_url,
            mask_b64=data.get("mask_b64"),
            strength=data.get("strength", 0.7),
            provider_name=data.get("provider"),
            model_name=data.get("model"),
            enhance_prompt=data.get("enhance", True),
        )

        if not result.success:
            return JSONResponse({"success": False, "error": result.error or "Edit failed"}, status_code=500)

        saved_images = []
        for img_b64 in result.images_b64:
            saved = storage.save(
                image_b64=img_b64, prompt=prompt,
                provider=result.provider, model=result.model,
                conversation_id=conversation_id,
                metadata=result.metadata or {},
            )
            saved_images.append(saved)
        for img_url in result.images_url:
            saved = storage.save(
                image_url=img_url, prompt=prompt,
                provider=result.provider, model=result.model,
                conversation_id=conversation_id,
                metadata=result.metadata or {},
            )
            saved_images.append(saved)

        images_out = [
            {"url": s.get("url", ""), "image_id": s.get("image_id", ""), "local_path": s.get("local_path", "")}
            for s in saved_images if not s.get("error")
        ]
        return {
            "success": True, "images": images_out,
            "provider": result.provider, "model": result.model,
            "prompt_used": result.prompt_used,
        }
    except Exception as e:
        logger.error(f"[ImageGen Edit] Error: {e}")
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)
