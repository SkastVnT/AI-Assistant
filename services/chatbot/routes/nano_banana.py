"""
Nano Banana — Google Gemini 2.5 Flash Image API surface.

POST /api/nano-banana/generate
    Body (JSON):
        prompt:                  str    (required)
        num_images:              int    1..NANO_BANANA_MAX_IMAGES_PER_REQUEST (default 1)
        aspect_ratio:            str    "1:1"|"9:16"|"16:9"|"3:4"|"4:3"|"2:3"|"3:2" (default "1:1")
        image_size:              str    "1K"|"2K"|"4K" (default config.NANO_BANANA_DEFAULT_IMAGE_SIZE)
        reference_images_b64:    list[str]  base64-encoded PNG/JPEG bytes, up to N
        reference_mime_types:    list[str]  parallel mime-types (default image/png)
        conversation_id:         str
        model:                   str    override default model

    Returns:
        {success: bool, images: [{url, image_id, local_path}], provider, model,
         prompt_used, latency_ms, cost_usd, errors: [...]}

GET /api/nano-banana/status
    Quick reachability/config probe used by the UI to enable the button.
"""

from __future__ import annotations

import logging
import time as _time
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import wraps

from flask import Blueprint, jsonify, request, session

from core import config as _config
from core.image_gen import ImageStorage
from core.image_gen.providers.base import ImageMode, ImageRequest
from core.image_gen.providers.nano_banana_provider import (
    MAX_REFERENCE_IMAGES,
    VALID_ASPECT_RATIOS,
    VALID_IMAGE_SIZES,
    NanoBananaProvider,
)
from core.private_logger import log_image_generation

logger = logging.getLogger(__name__)

nano_banana_bp = Blueprint("nano_banana", __name__)

# ── Singletons ──────────────────────────────────────────────────────
_provider: NanoBananaProvider | None = None
_storage: ImageStorage | None = None


def _get_provider() -> NanoBananaProvider:
    global _provider
    if _provider is None:
        _provider = NanoBananaProvider(
            api_keys=getattr(_config, "GEMINI_API_KEYS", []) or [],
            default_model=getattr(
                _config, "NANO_BANANA_MODEL", "gemini-2.5-flash-image"
            ),
        )
    return _provider


def _get_storage() -> ImageStorage:
    global _storage
    if _storage is None:
        _storage = ImageStorage()
    return _storage


# ── Validation & rate limiting ──────────────────────────────────────
_MAX_PROMPT = 8000  # nano-banana handles long structured prompts well
_MAX_REF_BYTES = 10 * 1024 * 1024  # 10 MB per reference (base64 decoded)
_RATE_WINDOW = 60
_RATE_MAX = 8
_req_log: dict = {}


def _rate_check() -> str | None:
    sid = session.get("session_id", request.remote_addr or "anon")
    now = _time.time()
    recent = [t for t in _req_log.get(sid, []) if t > now - _RATE_WINDOW]
    if len(recent) >= _RATE_MAX:
        _req_log[sid] = recent
        return f"Rate limited ({_RATE_MAX} req/{_RATE_WINDOW}s)"
    recent.append(now)
    _req_log[sid] = recent
    return None


def _validate(data: dict) -> str | None:
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return "prompt is required"
    if len(prompt) > _MAX_PROMPT:
        return f"prompt too long (max {_MAX_PROMPT})"

    n = data.get("num_images", 1)
    try:
        n = int(n)
    except (TypeError, ValueError):
        return "num_images must be an integer"
    cap = getattr(_config, "NANO_BANANA_MAX_IMAGES_PER_REQUEST", 4)
    if not (1 <= n <= cap):
        return f"num_images must be 1..{cap}"

    ar = data.get("aspect_ratio")
    if ar and ar not in VALID_ASPECT_RATIOS:
        return f"aspect_ratio must be one of {sorted(VALID_ASPECT_RATIOS)}"

    sz = data.get("image_size")
    if sz and sz not in VALID_IMAGE_SIZES:
        return f"image_size must be one of {sorted(VALID_IMAGE_SIZES)}"

    # Model whitelist — only Nano Banana Pro / Nano Banana 2 are allowed.
    model = (data.get("model") or "").strip()
    if model:
        allowed_aliases = set(getattr(_config, "NANO_BANANA_ALLOWED_MODELS", {}).keys())
        allowed_ids = set(getattr(_config, "NANO_BANANA_ALLOWED_MODELS", {}).values())
        if model not in allowed_aliases and model not in allowed_ids:
            return (
                f"model must be one of {sorted(allowed_aliases) or sorted(allowed_ids)}"
            )

    refs = data.get("reference_images_b64") or []
    if not isinstance(refs, list):
        return "reference_images_b64 must be a list"
    max_refs = min(
        MAX_REFERENCE_IMAGES,
        getattr(_config, "NANO_BANANA_MAX_REFERENCE_IMAGES", MAX_REFERENCE_IMAGES),
    )
    if len(refs) > max_refs:
        return f"too many reference images (max {max_refs})"
    for i, b64 in enumerate(refs):
        if not isinstance(b64, str) or not b64:
            return f"reference_images_b64[{i}] must be a non-empty base64 string"
        # Strip optional data: prefix.
        if b64.startswith("data:"):
            try:
                b64_clean = b64.split(",", 1)[1]
            except IndexError:
                return f"reference_images_b64[{i}] is malformed"
            refs[i] = b64_clean
        # Cheap size check on base64 payload (≈ raw_bytes * 4/3).
        if len(refs[i]) * 3 // 4 > _MAX_REF_BYTES:
            return f"reference_images_b64[{i}] exceeds 10 MB"
    return None


def _guarded(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        data = request.get_json(force=True, silent=True) or {}
        err = _rate_check()
        if err:
            return jsonify({"success": False, "error": err}), 429
        err = _validate(data)
        if err:
            return jsonify({"success": False, "error": err}), 400
        return f(data, *args, **kwargs)

    return wrapper


# ── Routes ──────────────────────────────────────────────────────────
@nano_banana_bp.route("/api/nano-banana/status", methods=["GET"])
def status():
    enabled = bool(getattr(_config, "NANO_BANANA_ENABLED", True))
    has_key = bool(getattr(_config, "GEMINI_API_KEYS", []))
    cap = getattr(_config, "NANO_BANANA_MAX_IMAGES_PER_REQUEST", 4)
    max_refs = min(
        MAX_REFERENCE_IMAGES,
        getattr(_config, "NANO_BANANA_MAX_REFERENCE_IMAGES", MAX_REFERENCE_IMAGES),
    )
    allowed = getattr(_config, "NANO_BANANA_ALLOWED_MODELS", {})
    labels = getattr(_config, "NANO_BANANA_MODEL_LABELS", {})
    default_alias = getattr(
        _config, "NANO_BANANA_DEFAULT_ALIAS", next(iter(allowed), "")
    )
    return jsonify(
        {
            "enabled": enabled,
            "available": enabled and has_key,
            "model": allowed.get(
                default_alias, getattr(_config, "NANO_BANANA_MODEL", "")
            ),
            "default_model_alias": default_alias,
            "models": [
                {"alias": alias, "id": model_id, "label": labels.get(alias, alias)}
                for alias, model_id in allowed.items()
            ],
            "default_image_size": getattr(
                _config, "NANO_BANANA_DEFAULT_IMAGE_SIZE", "2K"
            ),
            "max_num_images": cap,
            "max_reference_images": max_refs,
            "aspect_ratios": sorted(VALID_ASPECT_RATIOS),
            "image_sizes": sorted(VALID_IMAGE_SIZES),
        }
    )


@nano_banana_bp.route("/api/nano-banana/generate", methods=["POST"])
@_guarded
def generate(data: dict):
    if not getattr(_config, "NANO_BANANA_ENABLED", True):
        return jsonify({"success": False, "error": "nano-banana disabled"}), 403

    provider = _get_provider()
    if not provider.is_available:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "GEMINI_API_KEY not configured. Set GEMINI_API_KEY_1..4 in env.",
                }
            ),
            503,
        )

    # ── Quota check (best-effort, mirrors /api/image-gen/generate) ──
    username = session.get("username", "")
    quota_db = None
    if username:
        try:
            from core.extensions import get_db as _get_quota_db
            from core.user_auth import check_image_quota

            quota_db = _get_quota_db()
            ok, reason = check_image_quota(quota_db, username)
            if not ok:
                return (
                    jsonify(
                        {"success": False, "error": reason, "quota_exceeded": True}
                    ),
                    403,
                )
        except Exception as e:
            logger.warning("[nano_banana] quota check failed: %s", e)

    prompt: str = data["prompt"].strip()
    num_images: int = int(data.get("num_images", 1))
    aspect_ratio: str = data.get("aspect_ratio") or "1:1"
    image_size: str = data.get("image_size") or getattr(
        _config, "NANO_BANANA_DEFAULT_IMAGE_SIZE", "2K"
    )
    refs: list[str] = list(data.get("reference_images_b64") or [])
    ref_mimes: list[str] = list(data.get("reference_mime_types") or [])
    model_override: str = (data.get("model") or "").strip()
    # Resolve alias â†’ concrete Gemini model id, falling back to default.
    allowed = getattr(_config, "NANO_BANANA_ALLOWED_MODELS", {})
    if model_override and model_override in allowed:
        model_override = allowed[model_override]
    elif model_override and model_override not in allowed.values():
        # Defensive: validation already rejected this; clear to default.
        model_override = ""
    conversation_id: str = data.get(
        "conversation_id", session.get("conversation_id", "")
    )

    # Build a prototype request (we'll reuse it for each parallel call).
    extra = {
        "reference_images_b64": refs,
        "reference_mime_types": ref_mimes,
        "aspect_ratio": aspect_ratio,
        "image_size": image_size,
    }
    if model_override:
        extra["model"] = model_override

    # Approximate WxH for aspect_ratio (only used as fallback inside provider).
    w, h = _ar_to_dims(aspect_ratio, image_size)

    def _one_call() -> tuple[object, str | None]:
        req = ImageRequest(
            prompt=prompt,
            mode=ImageMode.IMAGE_TO_IMAGE if refs else ImageMode.TEXT_TO_IMAGE,
            width=w,
            height=h,
            num_images=1,
            extra=dict(extra),  # shallow copy per call
        )
        try:
            result = provider.generate(req)
            return result, None
        except Exception as e:
            logger.exception("[nano_banana] provider call crashed")
            return None, str(e)

    t0 = _time.time()
    results = []
    errors = []

    if num_images == 1:
        r, err = _one_call()
        results = [r] if r else []
        if err:
            errors.append(err)
    else:
        # Parallel fan-out — Nano Banana per-key quota allows light concurrency.
        with ThreadPoolExecutor(max_workers=min(num_images, 4)) as ex:
            futs = [ex.submit(_one_call) for _ in range(num_images)]
            for f in as_completed(futs):
                r, err = f.result()
                if r is not None:
                    results.append(r)
                if err:
                    errors.append(err)

    # Collect successful images (each provider call returns 1 image normally).
    storage = _get_storage()
    saved_images: list[dict] = []
    successes = [r for r in results if r and r.success]
    fails = [r for r in results if r and not r.success]
    attempt_count = 1  # max attempt across all sub-calls
    for fr in fails:
        if fr.error:
            errors.append(fr.error)
        attempt_count = max(attempt_count, (fr.metadata or {}).get("attempt", 1))

    used_model = ""
    used_provider = "nano_banana"
    total_cost = 0.0

    for res in successes:
        used_model = res.model or used_model
        total_cost += res.cost_usd or 0.0
        attempt_count = max(attempt_count, (res.metadata or {}).get("attempt", 1))
        for img_b64 in res.images_b64 or []:
            saved = storage.save(
                image_b64=img_b64,
                prompt=prompt,
                provider=used_provider,
                model=res.model,
                conversation_id=conversation_id,
                metadata={
                    "aspect_ratio": aspect_ratio,
                    "image_size": image_size,
                    "ref_count": len(refs),
                },
            )
            if saved.get("error"):
                errors.append(f"save: {saved['error']}")
                continue
            saved_images.append(saved)
            _save_to_gallery(saved, prompt, used_provider, res.model, conversation_id)

    # Increment quota by number of saved images.
    if username and quota_db is not None and saved_images:
        try:
            from core.user_auth import increment_image_quota

            increment_image_quota(quota_db, username, len(saved_images))
        except Exception:
            pass

    for s in saved_images:
        try:
            log_image_generation(
                prompt=prompt,
                provider=used_provider,
                model=used_model,
                image_url=s.get("url", ""),
                image_path=s.get("local_path", ""),
                session_id=conversation_id,
                mode="i2i" if refs else "txt2img",
                extra={
                    "aspect_ratio": aspect_ratio,
                    "image_size": image_size,
                    "ref_count": len(refs),
                },
            )
        except Exception:
            pass

    latency_ms = (_time.time() - t0) * 1000.0
    if not saved_images:
        return (
            jsonify(
                {
                    "success": False,
                    "error": "; ".join(errors[:3]) or "no images generated",
                    "provider": used_provider,
                    "model": used_model,
                    "attempt_count": attempt_count,
                    "errors": errors,
                }
            ),
            500,
        )

    return jsonify(
        {
            "success": True,
            "images": [
                {
                    "url": s.get("url", ""),
                    "image_id": s.get("image_id", ""),
                    "local_path": s.get("local_path", ""),
                }
                for s in saved_images
            ],
            "provider": used_provider,
            "model": used_model,
            "prompt_used": prompt,
            "aspect_ratio": aspect_ratio,
            "image_size": image_size,
            "ref_count": len(refs),
            "requested_num_images": num_images,
            "delivered_num_images": len(saved_images),
            "attempt_count": attempt_count,
            "latency_ms": round(latency_ms, 1),
            "cost_usd": round(total_cost, 4),
            "errors": errors,
        }
    )


# ── Helpers ─────────────────────────────────────────────────────────
def _ar_to_dims(ar: str, image_size: str) -> tuple[int, int]:
    """Map aspect-ratio + image_size to nominal WxH for downstream metadata."""
    base = {"1K": 1024, "2K": 2048, "4K": 3840}.get(image_size, 2048)
    table = {
        "1:1": (base, base),
        "16:9": (base, int(base * 9 / 16)),
        "9:16": (int(base * 9 / 16), base),
        "4:3": (base, int(base * 3 / 4)),
        "3:4": (int(base * 3 / 4), base),
        "3:2": (base, int(base * 2 / 3)),
        "2:3": (int(base * 2 / 3), base),
        "4:5": (int(base * 4 / 5), base),
        "5:4": (base, int(base * 4 / 5)),
        "21:9": (base, int(base * 9 / 21)),
    }
    return table.get(ar, (base, base))


def _save_to_gallery(
    saved: dict, prompt: str, provider: str, model: str, conversation_id: str
) -> None:
    """Persist metadata to MongoDB so it appears in the main image gallery."""
    if saved.get("error"):
        return
    try:
        import os
        from datetime import datetime

        from core.image_storage import save_to_mongodb

        save_to_mongodb(
            {
                "url": saved.get("url", ""),
                "local_path": saved.get("local_path", ""),
                "filename": os.path.basename(saved.get("local_path", "")),
                "prompt": prompt,
                "provider": provider,
                "model": model,
                "source": "nano_banana",
                "conversation_id": conversation_id,
                "session_id": conversation_id,
                "created_at": datetime.utcnow(),
                "image_id": saved.get("image_id", ""),
            }
        )
    except Exception as e:
        logger.warning("[nano_banana] gallery sync failed (non-fatal): %s", e)
