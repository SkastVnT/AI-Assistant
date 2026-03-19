"""
Image Generation API routes â€” Flask Blueprint.
Replaces the old Stable Diffusion routes with a modern multi-provider system.

Endpoints:
    POST /api/image-gen/generate     â†’ Generate image(s)
    POST /api/image-gen/edit         â†’ Edit last generated image
    GET  /api/image-gen/providers    â†’ List available providers
    GET  /api/image-gen/styles       â†’ List style presets
    GET  /api/image-gen/health       â†’ Health check all providers
    GET  /api/image-gen/stats        â†’ Usage statistics
    GET  /api/image-gen/images/<id>  â†’ Serve stored image
    GET  /api/image-gen/gallery      â†’ List recent images
    DELETE /api/image-gen/images/<id> â†’ Delete image
"""

from __future__ import annotations

import logging
import base64
import time as _time
from functools import wraps
from flask import Blueprint, request, jsonify, session, send_file
from io import BytesIO

from core.image_gen import (
    ImageGenerationRouter, SessionManager, ImageStorage,
    QualityMode, STYLE_PRESETS,
)

logger = logging.getLogger(__name__)

image_gen_bp = Blueprint("image_gen", __name__)

# â”€â”€ Validation & rate limiting â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_MAX_PROMPT = 2000
_MAX_DIM = 2048
_MIN_DIM = 64
_MAX_STEPS = 150
_RATE_WINDOW = 60
_RATE_MAX = 10
_req_log: dict = {}


def _validate(data: dict) -> str | None:
    for key in ("prompt",):
        if len(data.get(key, "")) > _MAX_PROMPT:
            return f"{key} too long (max {_MAX_PROMPT})"
    for d in ("width", "height"):
        v = data.get(d)
        if v is not None:
            try:
                v = int(v)
            except (ValueError, TypeError):
                return f"Invalid {d}"
            if not (_MIN_DIM <= v <= _MAX_DIM):
                return f"{d} must be {_MIN_DIM}-{_MAX_DIM}"
    s = data.get("steps")
    if s is not None:
        try:
            s = int(s)
        except (ValueError, TypeError):
            return "Invalid steps"
        if not (1 <= s <= _MAX_STEPS):
            return f"steps must be 1-{_MAX_STEPS}"
    return None


def _rate_check() -> str | None:
    sid = session.get("session_id", request.remote_addr or "anon")
    now = _time.time()
    log = _req_log.setdefault(sid, [])
    _req_log[sid] = [t for t in log if t > now - _RATE_WINDOW]
    if len(_req_log[sid]) >= _RATE_MAX:
        return f"Rate limited ({_RATE_MAX} req/{_RATE_WINDOW}s)"
    _req_log[sid].append(now)
    return None


def _guarded(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        data = request.get_json(force=True, silent=True) or {}
        err = _rate_check()
        if err:
            return jsonify({"error": err}), 429
        err = _validate(data)
        if err:
            return jsonify({"error": err}), 400
        return f(*args, **kwargs)
    return wrapper

# â”€â”€ Singletons (initialized once, shared across requests) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
_router: ImageGenerationRouter | None = None
_sessions: SessionManager | None = None
_storage: ImageStorage | None = None


def _get_router() -> ImageGenerationRouter:
    global _router
    if _router is None:
        _router = ImageGenerationRouter()
    return _router


def _get_sessions() -> SessionManager:
    global _sessions
    if _sessions is None:
        _sessions = SessionManager()
    return _sessions


def _get_storage() -> ImageStorage:
    global _storage
    if _storage is None:
        _storage = ImageStorage()
    return _storage


# â”€â”€ Main generation endpoint â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@image_gen_bp.route("/api/image-gen/generate", methods=["POST"])
@_guarded
def generate_image():
    """
    Generate image(s) from a text prompt.
    
    Body (JSON):
        prompt: str           â€” Image description
        quality: str          â€” "auto"|"fast"|"quality"|"free"|"cheap" (default: auto)
        style: str|null       â€” Style preset name
        width: int            â€” Output width (default: 1024)
        height: int           â€” Output height (default: 1024)
        provider: str|null    â€” Force specific provider
        model: str|null       â€” Force specific model
        enhance: bool         â€” Use LLM prompt enhancement (default: true)
        num_images: int       â€” Number of images (default: 1)
        seed: int|null        â€” Reproducibility seed
        steps: int            â€” Inference steps (default: 28)
        guidance: float       â€” Guidance/CFG scale (default: 3.5)
        conversation_id: str  â€” For session tracking
    """
    data = request.get_json(force=True, silent=True) or {}
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    router = _get_router()
    sessions = _get_sessions()
    storage = _get_storage()

    conversation_id = data.get("conversation_id", session.get("conversation_id", ""))
    img_session = sessions.get_or_create(conversation_id)

    # Build context from session history
    context = img_session.get_context_for_enhancement() if img_session.history else None

    result = router.generate(
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
    )

    if not result.success:
        return jsonify({
            "success": False,
            "error": result.error,
            "prompt_used": result.prompt_used,
        }), 500

    # Save to storage
    saved_images = []
    for img_b64 in result.images_b64:
        saved = storage.save(
            image_b64=img_b64,
            prompt=prompt,
            provider=result.provider,
            model=result.model,
            conversation_id=conversation_id,
            metadata=result.metadata,
        )
        saved_images.append(saved)

    for img_url in result.images_url:
        saved = storage.save(
            image_url=img_url,
            prompt=prompt,
            provider=result.provider,
            model=result.model,
            conversation_id=conversation_id,
            metadata=result.metadata,
        )
        saved_images.append(saved)

    # Update session
    img_session.add_generation(
        user_prompt=prompt,
        enhanced_prompt=result.prompt_used,
        result=result,
    )
    if data.get("style"):
        img_session.active_style = data["style"]

    # Log cost
    if result.cost_usd > 0:
        _log_cost('generate', result.provider, result.model, result.cost_usd)

    return jsonify({
        "success": True,
        "images": [
            {
                "url": s.get("url", ""),
                "image_id": s.get("image_id", ""),
                "local_path": s.get("local_path", ""),
            }
            for s in saved_images if not s.get("error")
        ],
        "images_url": result.images_url,
        "provider": result.provider,
        "model": result.model,
        "prompt_used": result.prompt_used,
        "original_prompt": prompt,
        "latency_ms": round(result.latency_ms, 1),
        "cost_usd": round(result.cost_usd, 4),
        "style": data.get("style"),
    })


# â”€â”€ Edit existing image â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@image_gen_bp.route("/api/image-gen/edit", methods=["POST"])
@_guarded
def edit_image():
    """
    Edit a previously generated image.
    
    Body (JSON):
        prompt: str            â€” Edit instruction (e.g., "add a rainbow")
        conversation_id: str   â€” Session to find last image
        image_b64: str|null    â€” Explicit base64 image to edit (overrides session)
        image_id: str|null     â€” Image ID from storage to edit
        strength: float        â€” Denoising strength 0-1 (default: 0.75)
        provider: str|null     â€” Force provider
        model: str|null        â€” Force model
    """
    data = request.get_json(force=True, silent=True) or {}
    prompt = data.get("prompt", "").strip()

    if not prompt:
        return jsonify({"error": "prompt is required"}), 400

    router = _get_router()
    sessions = _get_sessions()
    storage = _get_storage()

    conversation_id = data.get("conversation_id", session.get("conversation_id", ""))
    img_session = sessions.get_or_create(conversation_id)

    # Get source image
    source_b64 = data.get("image_b64")
    if not source_b64 and data.get("image_id"):
        img_bytes = storage.get(data["image_id"])
        if img_bytes:
            source_b64 = base64.b64encode(img_bytes).decode()

    if not source_b64:
        source_b64 = img_session.last_image_b64

    if not source_b64:
        # Try downloading from last URL
        if img_session.last_image_url:
            try:
                import httpx
                resp = httpx.get(img_session.last_image_url, timeout=15, follow_redirects=True)
                source_b64 = base64.b64encode(resp.content).decode()
            except Exception:
                pass

    if not source_b64:
        return jsonify({
            "error": "No source image found. Generate an image first, or provide image_b64/image_id.",
        }), 400

    context = img_session.get_context_for_enhancement()

    result = router.generate(
        prompt=prompt,
        mode="i2i",
        source_image_b64=source_b64,
        strength=data.get("strength", 0.75),
        quality=data.get("quality", QualityMode.AUTO),
        provider_name=data.get("provider"),
        model_name=data.get("model"),
        enhance_prompt=True,
        context=context,
    )

    if not result.success:
        return jsonify({"success": False, "error": result.error}), 500

    # Save
    saved_images = []
    for img_b64 in result.images_b64:
        saved = storage.save(
            image_b64=img_b64, prompt=prompt,
            provider=result.provider, model=result.model,
            conversation_id=conversation_id,
        )
        saved_images.append(saved)
    for img_url in result.images_url:
        saved = storage.save(
            image_url=img_url, prompt=prompt,
            provider=result.provider, model=result.model,
            conversation_id=conversation_id,
        )
        saved_images.append(saved)

    # Update session
    img_session.add_generation(
        user_prompt=prompt, enhanced_prompt=result.prompt_used,
        result=result, is_edit=True,
    )

    # Log cost
    if result.cost_usd > 0:
        _log_cost('edit', result.provider, result.model, result.cost_usd)

    return jsonify({
        "success": True,
        "images": [
            {"url": s.get("url", ""), "image_id": s.get("image_id", "")}
            for s in saved_images if not s.get("error")
        ],
        "images_url": result.images_url,
        "provider": result.provider,
        "model": result.model,
        "prompt_used": result.prompt_used,
        "latency_ms": round(result.latency_ms, 1),
        "cost_usd": round(result.cost_usd, 4),
        "is_edit": True,
    })


# â”€â”€ Serve stored images â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@image_gen_bp.route("/api/image-gen/images/<image_id>", methods=["GET"])
def serve_image(image_id: str):
    """Serve a stored image by ID."""
    storage = _get_storage()
    img_bytes = storage.get(image_id)
    if not img_bytes:
        return jsonify({"error": "Image not found"}), 404
    return send_file(BytesIO(img_bytes), mimetype="image/png", download_name=f"{image_id}.png")


@image_gen_bp.route("/api/image-gen/images/<image_id>", methods=["DELETE"])
def delete_image(image_id: str):
    """Delete a stored image."""
    storage = _get_storage()
    deleted = storage.delete(image_id)
    if deleted:
        return jsonify({"success": True, "message": f"Deleted {image_id}"})
    return jsonify({"error": "Image not found"}), 404


# â”€â”€ Gallery â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@image_gen_bp.route("/api/image-gen/gallery", methods=["GET"])
def gallery():
    """List recent generated images."""
    storage = _get_storage()
    limit = request.args.get("limit", 20, type=int)
    conversation_id = request.args.get("conversation_id", "")
    images = storage.list_recent(limit=limit, conversation_id=conversation_id)
    return jsonify({"images": images, "total": len(images)})


# â”€â”€ Provider info â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@image_gen_bp.route("/api/image-gen/providers", methods=["GET"])
def list_providers():
    """List all configured image generation providers."""
    router = _get_router()
    return jsonify({"providers": router.get_available_providers()})


@image_gen_bp.route("/api/image-gen/styles", methods=["GET"])
def list_styles():
    """List all available style presets."""
    styles = [{"name": k, "description": v} for k, v in STYLE_PRESETS.items()]
    return jsonify({"styles": styles})


@image_gen_bp.route("/api/image-gen/health", methods=["GET"])
def health():
    """Health check all providers."""
    router = _get_router()
    return jsonify({"health": router.health_check()})


@image_gen_bp.route("/api/image-gen/stats", methods=["GET"])
def stats():
    """Usage statistics."""
    router = _get_router()
    storage = _get_storage()
    return jsonify({
        "generation": router.get_stats(),
        "storage": storage.get_disk_usage(),
        "costs": _get_cost_summary(),
    })


# â”€â”€ Cost tracking â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

_cost_log_v2: list = []  # [{type, provider, model, cost_usd, timestamp}]


def _log_cost(gen_type: str, provider: str, model: str, cost_usd: float):
    """Append a cost entry."""
    from datetime import datetime
    _cost_log_v2.append({
        "type": gen_type,
        "provider": provider,
        "model": model,
        "cost_usd": round(cost_usd, 6),
        "timestamp": datetime.now().isoformat(),
    })
    if len(_cost_log_v2) > 500:
        del _cost_log_v2[:len(_cost_log_v2) - 500]


def _get_cost_summary() -> dict:
    total = sum(c["cost_usd"] for c in _cost_log_v2)
    return {"total_usd": round(total, 4), "count": len(_cost_log_v2), "recent": _cost_log_v2[-10:]}
