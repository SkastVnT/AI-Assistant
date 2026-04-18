"""
FastAPI Stable Diffusion Router
Mirrors routes/stable_diffusion.py (Flask Blueprint) for FastAPI mode.

Endpoints (frontend calls):
    GET  /sd-api/status        → Check ComfyUI health
    GET  /sd-api/models        → List checkpoint models
    GET  /sd-api/samplers      → List samplers
    GET  /sd-api/loras         → List LoRA models
    GET  /sd-api/vaes          → List VAE models
    POST /sd-api/text2img      → Generate from text (alias)
    POST /sd-api/img2img       → Img2Img generation
    POST /sd-api/interrogate   → Tag extraction

    GET  /api/sd-health        → Health alias
    GET  /api/sd-models        → Models alias
    GET  /api/sd-samplers      → Samplers alias
    GET  /api/sd-loras         → LoRA alias
    GET  /api/sd-vaes          → VAE alias
    POST /api/generate-image   → Text2Img
    POST /api/img2img          → Img2Img
    POST /api/generate-prompt  → AI prompt generation
    POST /api/share-image-imgbb → ImgBB upload
    GET  /api/sd-capabilities  → Advanced features check
    POST /api/sd-inpaint       → Inpainting
    POST /api/sd-controlnet    → ControlNet
    POST /api/sd-upscale       → Upscaling
    POST /api/sd-outpaint      → Outpainting
    POST /api/sd-batch         → Batch generation
    GET  /api/sd-negative-presets → Negative prompt presets
    GET  /api/prompt-history   → Prompt history
    POST /api/prompt-history   → Save prompt history
    GET  /api/sd-cost-log      → Cost log
    POST /api/sd-cost-log      → Save cost
    POST /api/sd-change-model  → Change model
    GET  /api/sd-presets       → Model presets
    GET  /api/sd-presets/{id}  → Preset detail
    POST /api/sd-interrogate   → Tag extraction alias
"""
from __future__ import annotations

import os
import sys
import json
import base64
import time as _time
import logging
import random
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("chatbot.sd")

CHATBOT_DIR = Path(__file__).resolve().parent.parent.parent
if str(CHATBOT_DIR) not in sys.path:
    sys.path.insert(0, str(CHATBOT_DIR))

from core.config import IMAGE_STORAGE_DIR, OPENAI_API_KEY, DEEPSEEK_API_KEY
from core.extensions import MONGODB_ENABLED, CLOUD_UPLOAD_ENABLED, ConversationDB, logger as ext_logger
from core.private_logger import log_image_generation

# Import model presets
try:
    import importlib.util
    _preset_path = CHATBOT_DIR / "config" / "model_presets.py"
    _spec = importlib.util.spec_from_file_location("model_presets", _preset_path)
    _presets_module = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_presets_module)

    MODEL_PRESETS = _presets_module.MODEL_PRESETS
    CATEGORIES = _presets_module.CATEGORIES
    QUICK_PRESETS = _presets_module.QUICK_PRESETS
    get_preset = _presets_module.get_preset
    get_all_presets = _presets_module.get_all_presets
    get_presets_by_category = _presets_module.get_presets_by_category
    PRESETS_AVAILABLE = True
except Exception as e:
    logger.warning(f"Model presets load failed: {e}")
    PRESETS_AVAILABLE = False
    MODEL_PRESETS = {}
    QUICK_PRESETS = []
    def get_preset(x): return None
    def get_all_presets(): return {}

# ImgBB uploader
ImgBBUploader = None
try:
    from src.utils.imgbb_uploader import ImgBBUploader
except ImportError:
    pass

router = APIRouter(tags=["Stable Diffusion"])

# ── Validation & Rate Limiting ───────────────────────────────────────────────

_MAX_PROMPT_LENGTH = 2000
_MAX_DIMENSION = 2048
_MIN_DIMENSION = 64
_MAX_STEPS = 150
_MAX_CFG = 30.0
_RATE_WINDOW = 60
_RATE_MAX_REQUESTS = 10

_request_log: dict = {}


def _validate_gen_params(data: dict) -> Optional[str]:
    prompt = data.get("prompt", "")
    if len(prompt) > _MAX_PROMPT_LENGTH:
        return f"Prompt too long ({len(prompt)} chars, max {_MAX_PROMPT_LENGTH})"

    neg = data.get("negative_prompt", "")
    if len(neg) > _MAX_PROMPT_LENGTH:
        return f"Negative prompt too long ({len(neg)} chars, max {_MAX_PROMPT_LENGTH})"

    for dim_key in ("width", "height"):
        val = data.get(dim_key)
        if val is not None:
            try:
                v = int(val)
            except (ValueError, TypeError):
                return f"Invalid {dim_key}"
            if v < _MIN_DIMENSION or v > _MAX_DIMENSION:
                return f"{dim_key} must be {_MIN_DIMENSION}-{_MAX_DIMENSION}"

    steps = data.get("steps")
    if steps is not None:
        try:
            s = int(steps)
        except (ValueError, TypeError):
            return "Invalid steps"
        if s < 1 or s > _MAX_STEPS:
            return f"Steps must be 1-{_MAX_STEPS}"

    cfg = data.get("cfg_scale")
    if cfg is not None:
        try:
            c = float(cfg)
        except (ValueError, TypeError):
            return "Invalid cfg_scale"
        if c < 0 or c > _MAX_CFG:
            return f"cfg_scale must be 0-{_MAX_CFG}"

    seed = data.get("seed")
    if seed is not None:
        try:
            int(seed)
        except (ValueError, TypeError):
            return "Invalid seed"

    return None


def _rate_limit_check(request: Request) -> Optional[str]:
    sid = request.session.get("session_id", request.client.host if request.client else "unknown")
    now = _time.time()
    window_start = now - _RATE_WINDOW

    log = _request_log.setdefault(sid, [])
    _request_log[sid] = [t for t in log if t > window_start]
    log = _request_log[sid]

    if len(log) >= _RATE_MAX_REQUESTS:
        wait = int(log[0] - window_start) + 1
        return f"Rate limited. Try again in {wait}s (max {_RATE_MAX_REQUESTS} requests/{_RATE_WINDOW}s)"

    log.append(now)
    return None


def _guard_generation(request: Request, data: dict) -> Optional[JSONResponse]:
    err = _rate_limit_check(request)
    if err:
        return JSONResponse({"error": err}, status_code=429)
    err = _validate_gen_params(data)
    if err:
        return JSONResponse({"error": err}, status_code=400)
    return None


# ── Helper functions ─────────────────────────────────────────────────────────

def _save_images_to_storage(base64_images, prefix, prompt, params):
    saved_filenames = []
    cloud_urls = []

    for idx, image_base64 in enumerate(base64_images):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{prefix}_{timestamp}_{idx}.png"
            filepath = IMAGE_STORAGE_DIR / filename

            image_data = base64.b64decode(image_base64)
            with open(filepath, "wb") as f:
                f.write(image_data)

            saved_filenames.append(filename)

            cloud_url = None
            delete_url = None
            if CLOUD_UPLOAD_ENABLED and ImgBBUploader:
                try:
                    uploader = ImgBBUploader()
                    upload_result = uploader.upload_image(str(filepath), title=f"AI: {prompt[:50]}")
                    if upload_result:
                        cloud_url = upload_result["url"]
                        delete_url = upload_result.get("delete_url", "")
                        cloud_urls.append(cloud_url)
                except Exception as e:
                    logger.error(f"[SD] ImgBB error: {e}")

            metadata_file = filepath.with_suffix(".json")
            metadata = {
                "filename": filename,
                "created_at": datetime.now().isoformat(),
                "prompt": prompt,
                "negative_prompt": params.get("negative_prompt", ""),
                "parameters": {k: v for k, v in params.items() if k != "init_images"},
                "cloud_url": cloud_url,
                "delete_url": delete_url,
                "service": "imgbb" if cloud_url else "local",
            }
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"[SD] Error saving image {idx}: {e}")

    return saved_filenames, cloud_urls


def _get_advanced_generator():
    try:
        from src.handlers.advanced_image_gen import get_advanced_image_generator
        return get_advanced_image_generator()
    except Exception as e:
        logger.error(f"[Advanced] Cannot load AdvancedImageGenerator: {e}")
        return None


# ── Health & Config ──────────────────────────────────────────────────────────

@router.get("/sd-api/status")
@router.get("/api/sd-health")
async def sd_health():
    try:
        try:
            from src.utils.comfyui_client import get_comfyui_client
            sd_api_url = os.getenv("COMFYUI_URL", os.getenv("SD_API_URL", "http://127.0.0.1:8188"))
            sd_client = get_comfyui_client(sd_api_url)
        except ImportError:
            from src.utils.sd_client import get_sd_client
            sd_api_url = os.getenv("SD_API_URL", "http://127.0.0.1:8188")
            sd_client = get_sd_client(sd_api_url)

        is_running = sd_client.check_health()

        if is_running:
            current_model = sd_client.get_current_model()
            return JSONResponse(
                {"status": "online", "api_url": sd_api_url, "current_model": current_model, "backend": "comfyui"},
                headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
            )
        return JSONResponse(
            {"status": "offline", "api_url": sd_api_url, "message": "ComfyUI is not running"},
            status_code=503,
            headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
        )
    except Exception as e:
        logger.error(f"[SD Health] Error: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@router.get("/sd-api/models")
@router.get("/api/sd-models")
async def sd_models():
    try:
        try:
            from src.utils.comfyui_client import get_comfyui_client
            sd_client = get_comfyui_client()
            models = sd_client.get_models()
            current = sd_client.get_current_model()
            return {"models": models, "current_model": current}
        except ImportError:
            from src.utils.sd_client import get_sd_client
            sd_client = get_sd_client()
            models = sd_client.get_models()
            current = sd_client.get_current_model()
            model_titles = [m.get("title", m.get("model_name", "Unknown")) for m in models]
            return {"models": model_titles, "current_model": current["model"]}
    except Exception as e:
        logger.error(f"[SD Models] Error: {e}")
        return JSONResponse({"error": "Failed to retrieve SD models"}, status_code=500)


@router.post("/api/sd-change-model")
@router.post("/api/sd/change-model")
async def sd_change_model(request: Request):
    try:
        from src.utils.sd_client import get_sd_client
        data = await request.json()
        model_name = data.get("model_name")
        if not model_name:
            return JSONResponse({"error": "model_name is required"}, status_code=400)
        sd_client = get_sd_client()
        success = sd_client.change_model(model_name)
        if success:
            return {"success": True, "message": f"Changed model to {model_name}"}
        return JSONResponse({"success": False, "error": "Cannot change model"}, status_code=500)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ── Presets ──────────────────────────────────────────────────────────────────

@router.get("/api/sd-presets")
@router.get("/api/sd/presets")
async def sd_presets():
    try:
        if PRESETS_AVAILABLE:
            return {"success": True, "presets": MODEL_PRESETS, "quick_presets": QUICK_PRESETS, "categories": get_all_presets()}
        return JSONResponse({"success": False, "error": "Presets not available"}, status_code=404)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/api/sd-presets/{preset_id}")
@router.get("/api/sd/presets/{preset_id}")
async def sd_preset_detail(preset_id: str):
    try:
        if PRESETS_AVAILABLE:
            preset = get_preset(preset_id)
            if preset:
                return {"success": True, "preset_id": preset_id, "preset": preset}
            return JSONResponse({"success": False, "error": "Preset not found"}, status_code=404)
        return JSONResponse({"success": False, "error": "Presets not available"}, status_code=404)
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


# ── Samplers, LoRAs, VAEs ────────────────────────────────────────────────────

@router.get("/sd-api/samplers")
@router.get("/api/sd-samplers")
@router.get("/api/sd/samplers")
async def sd_samplers():
    try:
        from src.utils.comfyui_client import get_comfyui_client
        sd_client = get_comfyui_client()
        samplers = sd_client.get_samplers()
        return {"success": True, "samplers": samplers}
    except Exception as e:
        return JSONResponse({"success": False, "error": str(e)}, status_code=500)


@router.get("/sd-api/loras")
@router.get("/api/sd-loras")
async def sd_loras():
    try:
        from src.utils.comfyui_client import get_comfyui_client
        sd_client = get_comfyui_client()
        loras_raw = sd_client.get_loras()
        loras_simple = []
        if isinstance(loras_raw, list):
            for lora in loras_raw:
                if isinstance(lora, dict):
                    name = lora.get("alias") or lora.get("name") or str(lora)
                    loras_simple.append({"name": name})
                else:
                    loras_simple.append({"name": str(lora)})
        return {"loras": loras_simple}
    except Exception as e:
        logger.error(f"[LoRAs] Error: {e}")
        return JSONResponse({"error": "Failed to retrieve LoRAs"}, status_code=500)


@router.get("/sd-api/vaes")
@router.get("/api/sd-vaes")
async def sd_vaes():
    try:
        from src.utils.comfyui_client import get_comfyui_client
        sd_client = get_comfyui_client()
        vaes_raw = sd_client.get_vaes()
        vae_names = []
        if isinstance(vaes_raw, list):
            for vae in vaes_raw:
                if isinstance(vae, dict):
                    name = vae.get("model_name") or vae.get("name") or str(vae)
                    vae_names.append(name)
                else:
                    vae_names.append(str(vae))
        return {"vaes": vae_names}
    except Exception as e:
        logger.error(f"[VAEs] Error: {e}")
        return JSONResponse({"error": "Failed to retrieve VAEs"}, status_code=500)


# ── Text2Img ─────────────────────────────────────────────────────────────────

@router.post("/api/generate-image")
@router.post("/sd-api/text2img")
async def generate_image(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    guard = _guard_generation(request, data)
    if guard:
        return guard

    try:
        try:
            from src.utils.comfyui_client import get_comfyui_client
            sd_client = get_comfyui_client()
            use_comfyui = True
        except ImportError:
            from src.utils.sd_client import get_sd_client
            sd_client = get_sd_client()
            use_comfyui = False

        # Quota check
        username = request.session.get("username", "")
        if username:
            try:
                from core.user_auth import check_image_quota
                from core.extensions import get_db
                db = get_db()
                allowed, reason = check_image_quota(db, username)
                if not allowed:
                    return JSONResponse({"error": reason, "quota_exceeded": True}, status_code=403)
            except Exception as qe:
                logger.warning(f"[sd] quota check: {qe}")

        prompt = data.get("prompt", "")
        if not prompt:
            return JSONResponse({"error": "Prompt is required"}, status_code=400)

        save_to_storage = data.get("save_to_storage", False)

        preset_id = data.get("preset", data.get("style"))
        preset_config = {}
        if preset_id and PRESETS_AVAILABLE:
            preset_config = get_preset(preset_id) or {}

        params = {
            "prompt": prompt,
            "negative_prompt": data.get("negative_prompt") or preset_config.get("negative_prompt", "bad quality, blurry, distorted"),
            "width": int(data.get("width") or preset_config.get("width", 1024)),
            "height": int(data.get("height") or preset_config.get("height", 1024)),
            "steps": int(data.get("steps") or preset_config.get("steps", 20)),
            "cfg_scale": float(data.get("cfg_scale") or preset_config.get("cfg_scale", 7.0)),
            "seed": int(data.get("seed") or -1),
            "model": data.get("model") or preset_config.get("model"),
        }

        logger.info(f"[TEXT2IMG] model={params.get('model')}, prompt={prompt[:50]}...")

        if use_comfyui:
            image_bytes = sd_client.generate_image(**params)
            if image_bytes:
                base64_image = base64.b64encode(image_bytes).decode("utf-8")
                base64_images = [base64_image]
            else:
                return JSONResponse({"error": "ComfyUI failed to generate image."}, status_code=500)
        else:
            result = sd_client.txt2img(**params)
            if "error" in result:
                return JSONResponse(result, status_code=500)
            base64_images = result.get("images", [])

        if not base64_images:
            return JSONResponse({"error": "No images generated"}, status_code=500)

        saved_filenames = []
        cloud_urls = []
        if save_to_storage:
            saved_filenames, cloud_urls = _save_images_to_storage(base64_images, "generated", prompt, params)

        return {
            "success": True,
            "images": saved_filenames if saved_filenames else base64_images,
            "image": (saved_filenames[0] if saved_filenames else base64_images[0]) if (saved_filenames or base64_images) else None,
            "base64_images": base64_images,
            "cloud_urls": cloud_urls,
            "cloud_url": cloud_urls[0] if cloud_urls else None,
            "backend": "comfyui" if use_comfyui else "a1111",
        }
    except Exception as e:
        import traceback
        logger.error(f"[TEXT2IMG] Error: {e}\n{traceback.format_exc()}")
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Img2Img ──────────────────────────────────────────────────────────────────

@router.post("/api/img2img")
@router.post("/sd-api/img2img")
async def img2img(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    guard = _guard_generation(request, data)
    if guard:
        return guard

    try:
        from src.utils.comfyui_client import get_comfyui_client

        image = data.get("image", "")
        prompt = data.get("prompt", "")

        if not image:
            return JSONResponse({"error": "Image is required"}, status_code=400)
        if not prompt:
            return JSONResponse({"error": "Prompt is required"}, status_code=400)

        params = {
            "init_images": [image],
            "prompt": prompt,
            "negative_prompt": data.get("negative_prompt", ""),
            "denoising_strength": float(data.get("denoising_strength") or 0.8),
            "width": int(data.get("width") or 512),
            "height": int(data.get("height") or 512),
            "steps": int(data.get("steps") or 30),
            "cfg_scale": float(data.get("cfg_scale") or 7.0),
            "sampler_name": data.get("sampler_name") or "DPM++ 2M Karras",
            "seed": int(data.get("seed") or -1),
            "restore_faces": data.get("restore_faces", False),
            "lora_models": data.get("lora_models", []),
            "vae": data.get("vae"),
        }

        sd_api_url = os.getenv("COMFYUI_URL", os.getenv("SD_API_URL", "http://127.0.0.1:8188"))
        sd_client = get_comfyui_client(sd_api_url)
        result = sd_client.img2img(**params)

        if "error" in result:
            return JSONResponse({"error": "Failed to generate image"}, status_code=500)

        base64_images = result.get("images", [])
        if not base64_images:
            return JSONResponse({"error": "No images generated"}, status_code=500)

        save_to_storage = data.get("save_to_storage", False)
        saved_filenames = []
        cloud_urls = []
        if save_to_storage:
            saved_filenames, cloud_urls = _save_images_to_storage(base64_images, "img2img", prompt, params)

        for img_b64 in base64_images:
            log_image_generation(
                prompt=prompt, provider="comfyui", model="stable-diffusion",
                image_data=img_b64, session_id=request.session.get("conversation_id", ""),
                mode="img2img",
                extra={"denoising_strength": params.get("denoising_strength"), "steps": params.get("steps")},
            )

        return {
            "success": True,
            "image": base64_images[0] if base64_images else None,
            "images": base64_images,
            "filenames": saved_filenames,
            "cloud_urls": cloud_urls,
            "info": result.get("info", ""),
            "parameters": result.get("parameters", {}),
        }
    except Exception as e:
        import traceback
        logger.error(f"[IMG2IMG] Error: {e}\n{traceback.format_exc()}")
        return JSONResponse({"error": "Failed to process img2img request"}, status_code=500)


# ── Prompt generation ────────────────────────────────────────────────────────

@router.post("/api/generate-prompt-grok")
@router.post("/api/generate-prompt")
async def generate_prompt(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    context = data.get("context", "")
    tags = data.get("tags", [])
    selected_model = data.get("model", "grok").lower()

    if not tags:
        return JSONResponse({"error": "Tags are required"}, status_code=400)

    system_prompt = """You are an expert at creating high-quality Stable Diffusion prompts.

Task:
1. Generate a POSITIVE prompt combining extracted features with quality boosters
2. Generate a NEGATIVE prompt to avoid low quality and NSFW content
3. Return JSON: {"prompt": "...", "negative_prompt": "..."}

Rules:
- Start with: masterpiece, best quality, highly detailed
- Include visual features from tags
- Negative MUST include: nsfw, nude, sexual, explicit, bad quality
- Output ONLY valid JSON"""

    try:
        if selected_model == "grok":
            result = _generate_with_grok(context, system_prompt, tags)
        elif selected_model == "openai":
            result = _generate_with_openai(context, system_prompt, tags)
        elif selected_model == "deepseek":
            result = _generate_with_deepseek(context, system_prompt, tags)
        else:
            result = _generate_fallback(tags)
        return result
    except Exception as model_error:
        logger.error(f"[Prompt Gen] Model error: {model_error}")
        result = _generate_fallback(tags)
        result["fallback"] = True
        return result


def _generate_with_grok(context, system_prompt, tags):
    from openai import OpenAI
    api_key = os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY")
    if not api_key:
        raise ValueError("GROK API key not configured")
    client = OpenAI(api_key=api_key, base_url="https://api.x.ai/v1")
    response = client.chat.completions.create(
        model="grok-3", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": context}],
        temperature=0.7, max_tokens=500, response_format={"type": "json_object"},
    )
    result_json = json.loads(response.choices[0].message.content.strip())
    return _process_prompt_result(result_json, tags, "grok")


def _generate_with_openai(context, system_prompt, tags):
    import openai
    if not OPENAI_API_KEY:
        raise ValueError("OpenAI API key not configured")
    openai.api_key = OPENAI_API_KEY
    response = openai.chat.completions.create(
        model="gpt-4o-mini", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": context}],
        temperature=0.7, max_tokens=500, response_format={"type": "json_object"},
    )
    result_json = json.loads(response.choices[0].message.content.strip())
    return _process_prompt_result(result_json, tags, "openai")


def _generate_with_deepseek(context, system_prompt, tags):
    from openai import OpenAI
    if not DEEPSEEK_API_KEY:
        raise ValueError("DeepSeek API key not configured")
    client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url="https://api.deepseek.com")
    response = client.chat.completions.create(
        model="deepseek-chat", messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": context}],
        temperature=0.7, max_tokens=500, response_format={"type": "json_object"},
    )
    result_json = json.loads(response.choices[0].message.content.strip())
    return _process_prompt_result(result_json, tags, "deepseek")


def _process_prompt_result(result_json, tags, model_name):
    generated_prompt = result_json.get("prompt", "").strip()
    generated_negative = result_json.get("negative_prompt", result_json.get("negative", "")).strip()
    if not generated_negative:
        generated_negative = "nsfw, nude, sexual, explicit, bad quality, blurry, worst quality"
    elif "nsfw" not in generated_negative.lower():
        generated_negative = "nsfw, nude, sexual, explicit, " + generated_negative
    return {"success": True, "prompt": generated_prompt, "negative_prompt": generated_negative, "tags_used": len(tags), "model": model_name}


def _generate_fallback(tags):
    prompt_parts = tags[:25]
    quality_tags = ["masterpiece", "best quality", "highly detailed", "beautiful"]
    return {
        "success": True,
        "prompt": ", ".join(quality_tags + prompt_parts),
        "negative_prompt": "nsfw, nude, sexual, explicit, bad quality, blurry, distorted, worst quality",
        "tags_used": len(tags),
    }


# ── Share / Upload ───────────────────────────────────────────────────────────

@router.post("/api/share-image-imgbb")
async def share_image_imgbb(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    base64_image = data.get("image", "")
    title = data.get("title", f'AI_Generated_{datetime.now().strftime("%Y%m%d_%H%M%S")}')

    if not base64_image:
        return JSONResponse({"error": "No image provided"}, status_code=400)

    if "," in base64_image:
        base64_image = base64_image.split(",")[1]

    try:
        uploader = ImgBBUploader()
        result = uploader.upload(base64_image, title=title)
        if result and result.get("url"):
            return {
                "success": True,
                "url": result["url"],
                "display_url": result.get("display_url", result["url"]),
                "delete_url": result.get("delete_url"),
                "thumb_url": result.get("thumb", {}).get("url"),
                "title": title,
            }
        return JSONResponse({"error": "ImgBB upload failed"}, status_code=500)
    except Exception as e:
        logger.error(f"[ImgBB Share] Error: {e}")
        return JSONResponse({"error": "Failed to upload image"}, status_code=500)


# ── Advanced: Capabilities, Inpaint, ControlNet, Upscale, Outpaint ──────────

@router.get("/api/sd-capabilities")
async def sd_capabilities():
    gen = _get_advanced_generator()
    if gen is None or not gen.is_available:
        return {"available": False, "message": "SD WebUI API not available", "capabilities": {}}
    return {"available": True, "capabilities": gen.get_capabilities()}


@router.post("/api/sd-inpaint")
async def sd_inpaint(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    guard = _guard_generation(request, data)
    if guard:
        return guard

    gen = _get_advanced_generator()
    if gen is None or not gen.is_available:
        return JSONResponse({"error": "Inpainting not available"}, status_code=503)

    image_b64 = data.get("image", "")
    mask_b64 = data.get("mask", "")
    prompt = data.get("prompt", "")

    if not image_b64 or not mask_b64:
        return JSONResponse({"error": "image and mask are required (base64)"}, status_code=400)
    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)

    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]
    if "," in mask_b64:
        mask_b64 = mask_b64.split(",", 1)[1]

    import tempfile, shutil
    tmp_dir = Path(tempfile.mkdtemp())
    img_path = tmp_dir / "image.png"
    mask_path = tmp_dir / "mask.png"
    try:
        img_path.write_bytes(base64.b64decode(image_b64))
        mask_path.write_bytes(base64.b64decode(mask_b64))
        result = gen.inpaint_image(
            image_path=str(img_path), mask_path=str(mask_path), prompt=prompt,
            negative_prompt=data.get("negative_prompt", ""),
            steps=int(data.get("steps", 30)), cfg_scale=float(data.get("cfg_scale", 7.5)),
            denoising_strength=float(data.get("denoising_strength", 0.75)),
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if "error" in result:
        return JSONResponse(result, status_code=500)

    images = result.get("images", [])
    saved_filenames, cloud_urls = [], []
    if data.get("save_to_storage") and images:
        saved_filenames, cloud_urls = _save_images_to_storage(images, "inpaint", prompt, data)

    return {"success": True, "images": images, "image": images[0] if images else None, "filenames": saved_filenames, "cloud_urls": cloud_urls, "processing_time": result.get("processing_time", 0)}


@router.post("/api/sd-controlnet")
async def sd_controlnet(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    guard = _guard_generation(request, data)
    if guard:
        return guard

    gen = _get_advanced_generator()
    if gen is None or not gen.is_available:
        return JSONResponse({"error": "ControlNet not available"}, status_code=503)

    prompt = data.get("prompt", "")
    control_b64 = data.get("control_image", "")
    cn_type = data.get("controlnet_type", "canny")

    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)
    if not control_b64:
        return JSONResponse({"error": "control_image is required (base64)"}, status_code=400)

    if "," in control_b64:
        control_b64 = control_b64.split(",", 1)[1]

    import tempfile, shutil
    tmp_dir = Path(tempfile.mkdtemp())
    ctrl_path = tmp_dir / "control.png"
    try:
        ctrl_path.write_bytes(base64.b64decode(control_b64))
        result = gen.generate_with_controlnet(
            prompt=prompt, control_image_path=str(ctrl_path), controlnet_type=cn_type,
            controlnet_weight=float(data.get("controlnet_weight", 1.0)),
            width=int(data.get("width", 512)), height=int(data.get("height", 512)),
            steps=int(data.get("steps", 30)), cfg_scale=float(data.get("cfg_scale", 7.5)),
            negative_prompt=data.get("negative_prompt", ""),
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if "error" in result:
        return JSONResponse(result, status_code=500)

    images = result.get("images", [])
    saved_filenames, cloud_urls = [], []
    if data.get("save_to_storage") and images:
        saved_filenames, cloud_urls = _save_images_to_storage(images, "controlnet", prompt, data)

    return {"success": True, "images": images, "image": images[0] if images else None, "filenames": saved_filenames, "cloud_urls": cloud_urls, "controlnet_used": result.get("controlnet_used"), "processing_time": result.get("processing_time", 0)}


@router.post("/api/sd-upscale")
async def sd_upscale(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    guard = _guard_generation(request, data)
    if guard:
        return guard

    gen = _get_advanced_generator()
    if gen is None or not gen.is_available:
        return JSONResponse({"error": "Upscaling not available"}, status_code=503)

    image_b64 = data.get("image", "")
    if not image_b64:
        return JSONResponse({"error": "image is required (base64)"}, status_code=400)

    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    import tempfile, shutil
    tmp_dir = Path(tempfile.mkdtemp())
    img_path = tmp_dir / "image.png"
    try:
        img_path.write_bytes(base64.b64decode(image_b64))
        result = gen.upscale_image(
            image_path=str(img_path), upscaler=data.get("upscaler", "R-ESRGAN 4x+"),
            scale_factor=float(data.get("scale_factor", 2.0)),
            restore_faces=data.get("restore_faces", False),
            face_restorer=data.get("face_restorer", "CodeFormer"),
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if "error" in result:
        return JSONResponse(result, status_code=500)

    image_out = result.get("image", "")
    saved_filenames, cloud_urls = [], []
    if data.get("save_to_storage") and image_out:
        saved_filenames, cloud_urls = _save_images_to_storage([image_out], "upscaled", "upscale", data)

    return {"success": True, "image": image_out, "original_size": result.get("original_size"), "upscaled_size": result.get("upscaled_size"), "upscaler_used": result.get("upscaler_used"), "filenames": saved_filenames, "cloud_urls": cloud_urls, "processing_time": result.get("processing_time", 0)}


@router.post("/api/sd-outpaint")
async def sd_outpaint(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    guard = _guard_generation(request, data)
    if guard:
        return guard

    gen = _get_advanced_generator()
    if gen is None or not gen.is_available:
        return JSONResponse({"error": "Outpainting not available"}, status_code=503)

    image_b64 = data.get("image", "")
    if not image_b64:
        return JSONResponse({"error": "image is required (base64)"}, status_code=400)

    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    direction = data.get("direction", "all")
    pixels = int(data.get("pixels", 128))
    if pixels < 16 or pixels > 512:
        return JSONResponse({"error": "pixels must be 16-512"}, status_code=400)

    import tempfile, shutil
    tmp_dir = Path(tempfile.mkdtemp())
    img_path = tmp_dir / "image.png"
    try:
        img_path.write_bytes(base64.b64decode(image_b64))
        result = gen.outpaint_image(image_path=str(img_path), direction=direction, pixels=pixels, prompt=data.get("prompt", ""))
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    if "error" in result:
        return JSONResponse(result, status_code=500)

    images = result.get("images", [])
    return {"success": True, "images": images, "image": images[0] if images else None, "original_size": result.get("original_size"), "extended_size": result.get("extended_size"), "direction": result.get("direction"), "processing_time": result.get("processing_time", 0)}


# ── Batch ────────────────────────────────────────────────────────────────────

@router.post("/api/sd-batch")
async def sd_batch(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    guard = _guard_generation(request, data)
    if guard:
        return guard

    prompt = data.get("prompt", "")
    if not prompt:
        return JSONResponse({"error": "prompt is required"}, status_code=400)

    count = int(data.get("count", 4))
    if count < 2 or count > 8:
        return JSONResponse({"error": "count must be 2-8"}, status_code=400)

    base_seed = int(data.get("seed", -1))
    seeds = []
    for _ in range(count):
        seeds.append(base_seed if base_seed != -1 else random.randint(0, 2**32 - 1))
        if base_seed != -1:
            base_seed += 1

    try:
        try:
            from src.utils.comfyui_client import get_comfyui_client
            sd_client = get_comfyui_client()
            use_comfyui = True
        except ImportError:
            from src.utils.sd_client import get_sd_client
            sd_client = get_sd_client()
            use_comfyui = False

        results = []
        for seed in seeds:
            params = {
                "prompt": prompt, "negative_prompt": data.get("negative_prompt", ""),
                "width": int(data.get("width", 1024)), "height": int(data.get("height", 1024)),
                "steps": int(data.get("steps", 20)), "cfg_scale": float(data.get("cfg_scale", 7.0)),
                "seed": seed, "model": data.get("model"),
            }
            if use_comfyui:
                image_bytes = sd_client.generate_image(**params)
                if image_bytes:
                    results.append({"image": base64.b64encode(image_bytes).decode("utf-8"), "seed": seed})
            else:
                res = sd_client.txt2img(**params)
                if isinstance(res, dict) and res.get("error"):
                    continue
                imgs = res.get("images", []) if isinstance(res, dict) else []
                if imgs:
                    results.append({"image": imgs[0], "seed": seed})

        if not results:
            return JSONResponse({"error": "All batch generations failed"}, status_code=500)

        all_b64 = [r["image"] for r in results]
        saved_filenames, cloud_urls = [], []
        if data.get("save_to_storage") and all_b64:
            saved_filenames, cloud_urls = _save_images_to_storage(all_b64, "batch", prompt, data)

        return {"success": True, "results": results, "count": len(results), "seeds": [r["seed"] for r in results], "filenames": saved_filenames, "cloud_urls": cloud_urls}
    except Exception as e:
        import traceback
        logger.error(f"[BATCH] Error: {e}\n{traceback.format_exc()}")
        return JSONResponse({"error": "internal server error", "error_code": "BATCH_GENERATION_ERROR"}, status_code=500)


# ── Negative presets ─────────────────────────────────────────────────────────

_NEGATIVE_PRESETS = {
    "general": {"label": "General Quality", "prompt": "bad quality, worst quality, low quality, blurry, distorted, deformed, disfigured, ugly, duplicate, watermark, text, signature"},
    "portrait": {"label": "Portrait / Face", "prompt": "bad anatomy, bad hands, bad fingers, extra fingers, missing fingers, extra limbs, missing limbs, fused fingers, long neck, cross-eyed, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, ugly, blurry, bad proportions"},
    "anime": {"label": "Anime / Illustration", "prompt": "nsfw, nude, lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, jpeg artifacts, signature, watermark, username, blurry, artist name"},
    "realistic": {"label": "Realistic / Photo", "prompt": "cartoon, anime, illustration, painting, drawing, art, sketch, deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, text, close up, cropped, out of frame, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated"},
    "landscape": {"label": "Landscape / Scene", "prompt": "text, watermark, signature, blurry, low resolution, oversaturated, underexposed, overexposed, grainy, noisy, distorted perspective, bad composition, ugly, worst quality"},
    "nsfw_block": {"label": "NSFW Block (Safety)", "prompt": "nsfw, nude, naked, sexual, explicit, pornographic, lewd, erotic, suggestive, revealing clothing, underwear, bikini, lingerie"},
}


@router.get("/api/sd-negative-presets")
async def sd_negative_presets():
    presets = [{"id": k, "label": v["label"], "prompt": v["prompt"]} for k, v in _NEGATIVE_PRESETS.items()]
    return {"success": True, "presets": presets}


# ── Prompt history & Cost tracking ───────────────────────────────────────────

_prompt_history: dict = {}
_cost_log: dict = {}


@router.get("/api/prompt-history")
async def get_prompt_history(request: Request):
    sid = request.session.get("session_id", request.client.host if request.client else "unknown")
    history = _prompt_history.get(sid, [])
    q = (request.query_params.get("q") or "").lower()
    if q:
        history = [h for h in history if q in h["prompt"].lower()]
    return {"history": history[-50:]}


@router.post("/api/prompt-history")
async def save_prompt_history(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    prompt = data.get("prompt", "").strip()
    if not prompt:
        return JSONResponse({"error": "prompt required"}, status_code=400)

    sid = request.session.get("session_id", request.client.host if request.client else "unknown")
    history = _prompt_history.setdefault(sid, [])
    if not history or history[-1]["prompt"] != prompt:
        history.append({"prompt": prompt, "negative_prompt": data.get("negative_prompt", ""), "timestamp": datetime.now().isoformat()})
    if len(history) > 100:
        _prompt_history[sid] = history[-100:]
    return {"success": True, "count": len(_prompt_history[sid])}


@router.get("/api/sd-cost-log")
async def get_cost_log(request: Request):
    sid = request.session.get("session_id", request.client.host if request.client else "unknown")
    costs = _cost_log.get(sid, [])
    total = sum(c.get("cost_usd", 0) for c in costs)
    return {"costs": costs[-50:], "total_usd": round(total, 4), "count": len(costs)}


@router.post("/api/sd-cost-log")
async def save_cost_log(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}
    sid = request.session.get("session_id", request.client.host if request.client else "unknown")
    entry = {"type": data.get("type", "unknown"), "provider": data.get("provider", "local"), "model": data.get("model", ""), "cost_usd": float(data.get("cost_usd", 0)), "timestamp": datetime.now().isoformat()}
    costs = _cost_log.setdefault(sid, [])
    costs.append(entry)
    if len(costs) > 200:
        _cost_log[sid] = costs[-200:]
    return {"success": True}


# ── Interrogation ────────────────────────────────────────────────────────────

@router.post("/sd-api/interrogate")
@router.post("/api/sd-interrogate")
async def sd_interrogate(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    image_b64 = data.get("image", "")
    if not image_b64:
        return JSONResponse({"error": "image field is required (base64)"}, status_code=400)

    if "," in image_b64:
        image_b64 = image_b64.split(",", 1)[1]

    try:
        from src.utils.comfyui_client import get_comfyui_client
        sd_client = get_comfyui_client()

        if not sd_client.check_health():
            return JSONResponse({"error": "ComfyUI is not running"}, status_code=503)

        image_bytes = base64.b64decode(image_b64)
        upload_result = sd_client._upload_image(image_bytes)
        if not upload_result:
            return JSONResponse({"error": "Failed to upload image to ComfyUI"}, status_code=500)

        input_image_name = upload_result.get("name")

        workflow = {
            "1": {"class_type": "LoadImage", "inputs": {"image": input_image_name}},
            "2": {"class_type": "WD14Tagger|pysssss", "inputs": {"image": ["1", 0], "model": "wd-v1-4-moat-tagger-v2", "threshold": 0.35, "character_threshold": 0.85, "replace_underscore": True, "trailing_comma": False, "exclude_tags": ""}},
            "3": {"class_type": "ShowText|pysssss", "inputs": {"text": ["2", 0]}},
        }

        result = sd_client._queue_prompt(workflow)
        if result and "prompt_id" in result:
            output = sd_client._wait_for_result(result["prompt_id"])
            if output:
                tags_text = ""
                for node_id, node_output in output.items():
                    if "text" in node_output:
                        tags_text = node_output["text"][0] if isinstance(node_output["text"], list) else node_output["text"]
                        break
                if tags_text:
                    tags_list = [t.strip() for t in tags_text.split(",") if t.strip()]
                    return {"success": True, "tags": tags_list, "raw": tags_text, "model": "wd14-tagger"}
        return JSONResponse({"error": "Tag extraction failed"}, status_code=500)
    except Exception as e:
        logger.error(f"[Interrogate] Error: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)
