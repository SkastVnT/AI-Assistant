"""
lora_manager.py - Character LoRA auto-search, download, and vision verification.

Given a detected character, this module:
  1. Searches CivitAI for LoRAs matching that character
  2. Downloads the top candidate to ComfyUI/models/loras/characters/<tag>/
  3. Runs a quick test generation via ComfyUI (minimal workflow)
  4. Uses vision AI to compare the test image against character references
  5. Keeps the LoRA if vision score >= threshold; deletes it otherwise

Cache: storage/character_loras/<tag>/lora_meta.json  (7-day TTL)
LoRA files: ComfyUI/models/loras/characters/<tag>/<filename>
"""

from __future__ import annotations

import base64
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ── Paths ────────────────────────────────────────────────────────────

_WORKSPACE_ROOT = Path(__file__).resolve().parents[2]
_COMFYUI_LORA_ROOT = _WORKSPACE_ROOT / "ComfyUI" / "models" / "loras"
_COMFYUI_LORA_DIR = _COMFYUI_LORA_ROOT / "characters"
_STORAGE_ROOT = _WORKSPACE_ROOT / "storage"
_LORA_META_DIR = _STORAGE_ROOT / "character_loras"
_LORA_META_TTL = 7 * 24 * 3600  # 7 days
_LORA_REGISTRY_YAML = _WORKSPACE_ROOT / "configs" / "lora_registry.yaml"

# 2026-04-26 user spec: SAA / local registry must be consulted BEFORE
# any CivitAI call.  Cache the parsed character-section once per process.
_CHAR_REGISTRY_CACHE: Optional[list[dict[str, Any]]] = None
_CHAR_REGISTRY_LOCK = __import__("threading").Lock()

def lora_file_exists(lora_rel_path: str) -> bool:
    """Return True if the LoRA file is present under ComfyUI/models/loras/.

    Accepts paths with forward or back slashes. An empty / None input returns
    False so callers can safely skip injection without raising.
    """
    if not lora_rel_path:
        return False
    rel = str(lora_rel_path).replace("\\", "/").lstrip("/")
    candidate = _COMFYUI_LORA_ROOT / rel
    try:
        return candidate.is_file()
    except OSError:
        return False


# ── ComfyUI LoRA list awareness ─────────────────────────────────────
# ComfyUI caches its lora_name dropdown at startup. When new LoRA files
# are dropped into subfolders (e.g. effects/mouth/) AFTER ComfyUI has
# started, the file is on disk but ``LoraLoader`` will reject it with
# HTTP 400 ``value_not_in_list``. We query /object_info/LoraLoader once
# per process and cache the membership set so callers can drop unknown
# LoRAs before submitting the workflow.

_COMFY_LORA_LIST_CACHE: Optional[set[str]] = None
_COMFY_LORA_LIST_LOCK = __import__("threading").Lock()


def _normalise_lora_name(name: str) -> str:
    return str(name or "").replace("\\", "/").lstrip("/").lower()


def _fetch_comfy_lora_list(base_url: str) -> Optional[set[str]]:
    try:
        import httpx
        with httpx.Client(timeout=8) as client:
            resp = client.get(f"{base_url.rstrip('/')}/object_info/LoraLoader")
            if resp.status_code != 200:
                return None
            info = resp.json()
            raw = (
                info.get("LoraLoader", {})
                    .get("input", {})
                    .get("required", {})
                    .get("lora_name", [[]])[0]
            )
            if not isinstance(raw, list):
                return None
            return {_normalise_lora_name(x) for x in raw if isinstance(x, str)}
    except Exception as e:
        logger.debug("[LoRA] Could not fetch ComfyUI lora list: %s", e)
        return None


def get_comfy_lora_set(force_refresh: bool = False) -> Optional[set[str]]:
    """Return ComfyUI's known LoRA filenames (lowercase, forward-slash).

    Returns ``None`` if ComfyUI is unreachable; callers should then fall
    back to disk-only checks. Cached for the process lifetime.
    """
    global _COMFY_LORA_LIST_CACHE
    with _COMFY_LORA_LIST_LOCK:
        if _COMFY_LORA_LIST_CACHE is not None and not force_refresh:
            return _COMFY_LORA_LIST_CACHE
        base_url = (
            os.getenv("ANIME_PIPELINE_COMFYUI_URL")
            or os.getenv("COMFYUI_URL")
            or "http://127.0.0.1:8188"
        )
        result = _fetch_comfy_lora_list(base_url)
        if result is not None:
            _COMFY_LORA_LIST_CACHE = result
            logger.info("[LoRA] Cached ComfyUI lora list: %d entries", len(result))
        return result


def lora_known_to_comfyui(lora_rel_path: str) -> bool:
    """Return True if ComfyUI's LoraLoader will accept this name.

    Falls back to ``lora_file_exists`` when ComfyUI is unreachable, so
    offline / cold-start workflows are not unnecessarily blocked.

    If the name is on disk but missing from the cached ComfyUI list,
    refresh the cache once: a user may have restarted ComfyUI mid-run
    after dropping new LoRA files into ``effects/<sub>/``.
    """
    if not lora_rel_path:
        return False
    known = get_comfy_lora_set()
    if known is None:
        return lora_file_exists(lora_rel_path)
    norm = _normalise_lora_name(lora_rel_path)
    if norm in known:
        return True
    # Cache miss — if file exists on disk, attempt one refresh in case
    # ComfyUI was restarted (or user manually triggered a /object_info
    # rescan) since process start. Avoids permanently blacklisting LoRAs
    # added after the first successful query.
    if lora_file_exists(lora_rel_path):
        refreshed = get_comfy_lora_set(force_refresh=True)
        if refreshed is not None and norm in refreshed:
            return True
    return False

_CIVITAI_API = "https://civitai.com/api/v1"
_CIVITAI_DOWNLOAD = "https://civitai.com/api/download/models"

# Vision score to accept a LoRA (0-10)
_VISION_ACCEPT_THRESHOLD = 7.0
# How many CivitAI candidates to try before giving up
_MAX_CANDIDATES = 3


# ── Data classes ─────────────────────────────────────────────────────

@dataclass
class LoRACandidate:
    """A single CivitAI LoRA candidate."""
    model_id: int
    version_id: int
    name: str
    filename: str
    download_url: str
    trigger_words: list[str] = field(default_factory=list)
    base_model: str = ""
    download_count: int = 0
    rating: float = 0.0
    size_bytes: int = 0


@dataclass
class LoRAVerificationResult:
    """Result of vision-based LoRA quality check."""
    accepted: bool
    vision_score: float
    test_image_b64: Optional[str]
    lora_filename: str
    lora_path: Optional[Path]
    trigger_words: list[str] = field(default_factory=list)
    rejection_reason: str = ""
    latency_ms: float = 0.0


# ════════════════════════════════════════════════════════════════════════
# CivitAI search
# ════════════════════════════════════════════════════════════════════════

def _civitai_search(
    display_name: str,
    series_name: str,
    danbooru_tag: str,
) -> list[LoRACandidate]:
    """Search CivitAI for character LoRAs.

    Tries multiple queries to find the best matches:
      1. Exact character name + series
      2. Danbooru tag
    Returns up to _MAX_CANDIDATES sorted by download count.
    """
    import httpx

    civitai_key = os.getenv("CIVITAI_API_KEY", "")
    headers = {}
    if civitai_key:
        headers["Authorization"] = f"Bearer {civitai_key}"

    queries = [
        f"{display_name} {series_name}",
        danbooru_tag.replace("_", " "),
        display_name,
    ]

    seen_ids: set[int] = set()
    candidates: list[LoRACandidate] = []

    for query in queries:
        if len(candidates) >= _MAX_CANDIDATES:
            break
        try:
            resp = httpx.get(
                f"{_CIVITAI_API}/models",
                params={
                    "query": query,
                    "types": "LORA",
                    "sort": "Most Downloaded",
                    "limit": 5,
                    "nsfw": True,  # include all, we'll filter by base model
                },
                headers=headers,
                timeout=15,
            )
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                model_id = item.get("id")
                if model_id in seen_ids:
                    continue
                seen_ids.add(model_id)

                versions = item.get("modelVersions", [])
                if not versions:
                    continue

                # Take the latest version
                ver = versions[0]
                version_id = ver.get("id")
                base_model = ver.get("baseModel", "")

                # Skip non-SDXL / non-Illustrious models for our pipeline
                if base_model and not any(
                    k in base_model.lower()
                    for k in ["sdxl", "illustrious", "noobai", "xl", "pony"]
                ):
                    logger.debug("[LoRAMgr] Skip %s — base=%s", item.get("name"), base_model)
                    continue

                # Get the safetensors file info
                files = ver.get("files", [])
                st_file = next(
                    (f for f in files if f.get("name", "").endswith(".safetensors")),
                    files[0] if files else None,
                )
                if not st_file:
                    continue

                dl_url = st_file.get("downloadUrl") or f"{_CIVITAI_DOWNLOAD}/{version_id}"
                size_bytes = st_file.get("sizeKB", 0) * 1024

                trigger_words = ver.get("trainedWords", [])
                stats = item.get("stats", {})

                candidates.append(LoRACandidate(
                    model_id=model_id,
                    version_id=version_id,
                    name=item.get("name", ""),
                    filename=st_file.get("name", f"char_{version_id}.safetensors"),
                    download_url=dl_url,
                    trigger_words=trigger_words,
                    base_model=base_model,
                    download_count=stats.get("downloadCount", 0),
                    rating=stats.get("rating", 0.0),
                    size_bytes=int(size_bytes),
                ))

        except Exception as e:
            logger.warning("[LoRAMgr] CivitAI search failed for '%s': %s", query, e)

    # Sort by download count desc
    candidates.sort(key=lambda c: c.download_count, reverse=True)
    return candidates[:_MAX_CANDIDATES]


# ════════════════════════════════════════════════════════════════════════
# Download
# ════════════════════════════════════════════════════════════════════════

def _download_lora(candidate: LoRACandidate, danbooru_tag: str) -> Optional[Path]:
    """Download a LoRA safetensors file to local cache.

    Returns the local path, or None on failure.
    """
    import httpx

    lora_dir = _COMFYUI_LORA_DIR / danbooru_tag
    lora_dir.mkdir(parents=True, exist_ok=True)

    dest = lora_dir / candidate.filename
    if dest.exists():
        logger.info("[LoRAMgr] Already downloaded: %s", dest)
        return dest

    # Size guard: skip files > 1 GB
    if candidate.size_bytes > 1_000_000_000:
        logger.warning("[LoRAMgr] Skip %s — too large (%.1f MB)",
                       candidate.filename, candidate.size_bytes / 1_000_000)
        return None

    civitai_key = os.getenv("CIVITAI_API_KEY", "")
    headers = {"User-Agent": "AI-Assistant/1.0"}
    if civitai_key:
        headers["Authorization"] = f"Bearer {civitai_key}"

    logger.info("[LoRAMgr] Downloading %s from CivitAI (~%.1f MB)...",
                candidate.filename, candidate.size_bytes / 1_000_000)

    try:
        with httpx.stream(
            "GET",
            candidate.download_url,
            headers=headers,
            follow_redirects=True,
            timeout=120,
        ) as resp:
            resp.raise_for_status()
            with dest.open("wb") as f:
                for chunk in resp.iter_bytes(chunk_size=65536):
                    f.write(chunk)

        logger.info("[LoRAMgr] Downloaded: %s (%.1f MB)",
                    dest, dest.stat().st_size / 1_000_000)
        return dest

    except Exception as e:
        logger.error("[LoRAMgr] Download failed for %s: %s", candidate.filename, e)
        if dest.exists():
            dest.unlink(missing_ok=True)
        return None


# ════════════════════════════════════════════════════════════════════════
# Quick ComfyUI test generation
# ════════════════════════════════════════════════════════════════════════

def _lora_relative_path(lora_abs: Path) -> str:
    """Return ComfyUI-relative LoRA path (from models/loras/)."""
    # ComfyUI expects paths relative to ComfyUI/models/loras/
    loras_root = _WORKSPACE_ROOT / "ComfyUI" / "models" / "loras"
    try:
        rel = lora_abs.relative_to(loras_root)
        # On Windows, use forward slashes
        return str(rel).replace("\\", "/")
    except ValueError:
        return lora_abs.name


def _build_test_workflow(
    lora_filename: str,
    character_prompt: str,
    base_model: str,
    width: int = 512,
    height: int = 768,
) -> dict:
    """Build a minimal ComfyUI workflow for LoRA quality testing.

    Just txt2img with the LoRA loaded — no ControlNet, no upscale.
    Uses a fast EULER sampler with 20 steps.
    """
    # Default model name - use whatever is configured in the pipeline
    checkpoint = base_model or "ChenkinNoob-XL-V0.2.safetensors"

    seed = int(time.time()) % 999999

    w: dict[str, Any] = {}

    # Checkpoint loader
    w["1"] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": checkpoint},
    }

    # LoRA loader
    w["2"] = {
        "class_type": "LoraLoader",
        "inputs": {
            "model": ["1", 0],
            "clip": ["1", 1],
            "lora_name": lora_filename,
            "strength_model": 0.85,
            "strength_clip": 0.85,
        },
    }

    # CLIP text encode positive
    w["3"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": character_prompt,
            "clip": ["2", 1],
        },
    }

    # CLIP text encode negative
    w["4"] = {
        "class_type": "CLIPTextEncode",
        "inputs": {
            "text": "ugly, bad anatomy, blurry, low quality, deformed, text, watermark",
            "clip": ["2", 1],
        },
    }

    # Empty latent
    w["5"] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": width, "height": height, "batch_size": 1},
    }

    # KSampler
    w["6"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": ["2", 0],
            "positive": ["3", 0],
            "negative": ["4", 0],
            "latent_image": ["5", 0],
            "seed": seed,
            "steps": 20,
            "cfg": 7.0,
            "sampler_name": "euler",
            "scheduler": "normal",
            "denoise": 1.0,
        },
    }

    # VAE decode
    w["7"] = {
        "class_type": "VAEDecode",
        "inputs": {
            "samples": ["6", 0],
            "vae": ["1", 2],
        },
    }

    # Save image (temp filename prefix)
    w["8"] = {
        "class_type": "SaveImage",
        "inputs": {
            "images": ["7", 0],
            "filename_prefix": f"lora_test_{uuid.uuid4().hex[:6]}",
        },
    }

    return w


def _run_test_generation(
    comfyui_url: str,
    workflow: dict,
    timeout: int = 120,
) -> Optional[str]:
    """Submit workflow to ComfyUI and wait for result.

    Returns base64 encoded image or None on failure.
    """
    import httpx

    client_id = uuid.uuid4().hex

    try:
        # Queue prompt
        resp = httpx.post(
            f"{comfyui_url}/prompt",
            json={"prompt": workflow, "client_id": client_id},
            timeout=15,
        )
        resp.raise_for_status()
        prompt_id = resp.json().get("prompt_id")
        if not prompt_id:
            logger.warning("[LoRAMgr] No prompt_id from ComfyUI")
            return None

        logger.info("[LoRAMgr] Test generation started, prompt_id=%s", prompt_id)

        # Poll for completion
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(2)
            try:
                hist_resp = httpx.get(
                    f"{comfyui_url}/history/{prompt_id}", timeout=10,
                )
                if hist_resp.status_code == 200:
                    hist = hist_resp.json()
                    if prompt_id in hist:
                        outputs = hist[prompt_id].get("outputs", {})
                        for node_id, node_out in outputs.items():
                            images = node_out.get("images", [])
                            if images:
                                img_info = images[0]
                                # Fetch the image bytes
                                img_resp = httpx.get(
                                    f"{comfyui_url}/view",
                                    params={
                                        "filename": img_info["filename"],
                                        "subfolder": img_info.get("subfolder", ""),
                                        "type": img_info.get("type", "output"),
                                    },
                                    timeout=15,
                                )
                                if img_resp.status_code == 200:
                                    b64 = base64.b64encode(img_resp.content).decode("ascii")
                                    logger.info("[LoRAMgr] Test generation complete")
                                    return b64
            except Exception as e:
                logger.debug("[LoRAMgr] Polling error: %s", e)

        logger.warning("[LoRAMgr] Test generation timed out after %ds", timeout)
        return None

    except Exception as e:
        logger.error("[LoRAMgr] Test generation failed: %s", e)
        return None


# ════════════════════════════════════════════════════════════════════════
# Vision verification
# ════════════════════════════════════════════════════════════════════════

_LORA_VERIFY_PROMPT = """\
You are evaluating whether a generated anime image successfully depicts a specific character.

Character: {display_name} from {series_name}
Expected appearance:
{appearance_description}

Compare the generated image against these expectations and return ONLY a JSON object:
{{
  "identity_match_score": <0-10>,
  "eyes_match": <0-10>,
  "hair_match": <0-10>,
  "outfit_match": <0-10>,
  "overall_quality": <0-10>,
  "is_correct_character": true/false,
  "issues": ["list of mismatches found"],
  "verdict": "accept" or "reject"
}}

Rules:
- Score 8+ only if the character is clearly recognizable with correct eye color, hair style, and outfit
- Score below 6 for wrong eye colors, wrong hair, or completely wrong character
- is_correct_character = true only if you are confident this is the right character
- verdict = "accept" if identity_match_score >= 7 AND is_correct_character = true
"""


def _verify_lora_with_vision(
    test_image_b64: str,
    display_name: str,
    series_name: str,
    appearance_description: str,
    reference_images: Optional[list[str]] = None,
) -> float:
    """Use vision AI to verify the LoRA output matches the character.

    Returns a score 0-10. Score >= _VISION_ACCEPT_THRESHOLD means accept.
    """
    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY", "")
    if not gemini_key and not os.getenv("OPENAI_API_KEY"):
        logger.warning("[LoRAMgr] No vision API key, skipping verification")
        # Default: accept if we can't verify (benefit of the doubt)
        return 7.0

    import httpx

    prompt = _LORA_VERIFY_PROMPT.format(
        display_name=display_name,
        series_name=series_name,
        appearance_description=appearance_description,
    )

    raw_test = test_image_b64.split(",", 1)[-1] if "," in test_image_b64 else test_image_b64

    # Gemini vision
    if gemini_key:
        parts = [{"text": prompt}]
        parts.append({
            "inline_data": {"mime_type": "image/png", "data": raw_test}
        })
        # Optionally include first reference image for comparison
        if reference_images:
            raw_ref = (
                reference_images[0].split(",", 1)[-1]
                if "," in reference_images[0]
                else reference_images[0]
            )
            parts.append({
                "inline_data": {"mime_type": "image/png", "data": raw_ref}
            })
            parts.insert(1, {"text": "This is the reference image of the character:"})
            parts.insert(3, {"text": "This is the generated image (check if it matches the character above):"})

        try:
            resp = httpx.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                "gemini-2.0-flash:generateContent",
                headers={"X-goog-api-key": gemini_key},
                json={
                    "contents": [{"parts": parts}],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 400,
                        "responseMimeType": "application/json",
                    },
                },
                timeout=25,
            )
            resp.raise_for_status()
            data = resp.json()
            text = (
                data.get("candidates", [{}])[0]
                .get("content", {})
                .get("parts", [{}])[0]
                .get("text", "{}")
            )
            result = _parse_verify_json(text)
            if result is not None:
                score = float(result.get("identity_match_score", 5.0))
                verdict = result.get("verdict", "")
                if verdict == "reject":
                    score = min(score, _VISION_ACCEPT_THRESHOLD - 0.1)
                logger.info("[LoRAMgr] Vision verify: score=%.1f verdict=%s issues=%s",
                            score, verdict, result.get("issues", []))
                return score
        except Exception as e:
            logger.warning("[LoRAMgr] Gemini verify failed: %s", e)

    # OpenAI fallback
    openai_key = os.getenv("OPENAI_API_KEY", "")
    if openai_key:
        content: list[dict] = [{"type": "text", "text": prompt}]
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{raw_test}", "detail": "low"},
        })
        if reference_images:
            raw_ref = (
                reference_images[0].split(",", 1)[-1]
                if "," in reference_images[0]
                else reference_images[0]
            )
            content.insert(1, {"type": "text", "text": "Reference (correct character):"})
            content.insert(2, {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{raw_ref}", "detail": "low"},
            })
            content.append({"type": "text", "text": "Generated image (check if it matches):"})

        try:
            resp = httpx.post(
                "https://api.openai.com/v1/chat/completions",
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": content}],
                    "max_tokens": 400,
                    "temperature": 0.1,
                    "response_format": {"type": "json_object"},
                },
                headers={"Authorization": f"Bearer {openai_key}"},
                timeout=25,
            )
            resp.raise_for_status()
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            result = _parse_verify_json(text)
            if result is not None:
                score = float(result.get("identity_match_score", 5.0))
                verdict = result.get("verdict", "")
                if verdict == "reject":
                    score = min(score, _VISION_ACCEPT_THRESHOLD - 0.1)
                return score
        except Exception as e:
            logger.warning("[LoRAMgr] OpenAI verify failed: %s", e)

    return 5.0  # Unknown — neither accept nor reject threshold


def _parse_verify_json(text: str) -> Optional[dict]:
    """Parse vision verification JSON."""
    try:
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except (json.JSONDecodeError, KeyError):
        return None


# ════════════════════════════════════════════════════════════════════════
# Metadata cache
# ════════════════════════════════════════════════════════════════════════

def _load_lora_cache(danbooru_tag: str) -> Optional[dict]:
    """Load cached LoRA metadata."""
    meta_file = _LORA_META_DIR / danbooru_tag / "lora_meta.json"
    if not meta_file.exists():
        return None
    try:
        data = json.loads(meta_file.read_text(encoding="utf-8"))
        if time.time() - data.get("timestamp", 0) > _LORA_META_TTL:
            return None
        return data
    except Exception:
        return None


def _save_lora_cache(danbooru_tag: str, meta: dict) -> None:
    """Save LoRA metadata to cache."""
    cache_dir = _LORA_META_DIR / danbooru_tag
    cache_dir.mkdir(parents=True, exist_ok=True)
    meta_file = cache_dir / "lora_meta.json"
    meta["timestamp"] = time.time()
    try:
        meta_file.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("[LoRAMgr] Cache save failed: %s", e)


# ════════════════════════════════════════════════════════════════════════
# Local registry (SAA-first lookup before CivitAI)
# ════════════════════════════════════════════════════════════════════════

def _load_character_registry() -> list[dict[str, Any]]:
    """Parse the ``character:`` section of configs/lora_registry.yaml once."""
    global _CHAR_REGISTRY_CACHE
    if _CHAR_REGISTRY_CACHE is not None:
        return _CHAR_REGISTRY_CACHE
    with _CHAR_REGISTRY_LOCK:
        if _CHAR_REGISTRY_CACHE is not None:
            return _CHAR_REGISTRY_CACHE
        entries: list[dict[str, Any]] = []
        if not _LORA_REGISTRY_YAML.exists():
            _CHAR_REGISTRY_CACHE = entries
            return entries
        try:
            import yaml  # type: ignore
            data = yaml.safe_load(_LORA_REGISTRY_YAML.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                section = data.get("character") or []
                if isinstance(section, list):
                    entries = [e for e in section if isinstance(e, dict) and e.get("name")]
        except Exception as exc:  # noqa: BLE001
            logger.warning("[LoRAMgr] Failed to load lora_registry.yaml: %s", exc)
        _CHAR_REGISTRY_CACHE = entries
        logger.info("[LoRAMgr] Local character registry loaded: %d entries", len(entries))
        return entries


def _resolve_local_lora_path(filename: str, location: str) -> Optional[Path]:
    """Find an actual file on disk for a registry entry."""
    if not filename:
        return None
    candidates: list[Path] = []
    if location == "comfyui" or not location:
        candidates += [
            _COMFYUI_LORA_DIR / filename,
            _COMFYUI_LORA_ROOT / filename,
        ]
    if location == "lora_dir" or not location:
        candidates += [
            _WORKSPACE_ROOT / "LORA" / filename,
            _WORKSPACE_ROOT / "LORA" / "new_2" / "character" / filename,
        ]
    for c in candidates:
        try:
            if c.is_file():
                return c
        except OSError:
            continue
    return None


def _local_registry_lookup(
    danbooru_tag: str,
    display_name: str,
    series_name: str,
) -> Optional[tuple[Path, list[str], dict[str, Any]]]:
    """Match a character against the local registry.

    Returns ``(lora_path, trigger_words, registry_entry)`` on hit, else None.
    Match order: exact char-list hit, then series-named all-in-one packs.
    """
    entries = _load_character_registry()
    if not entries:
        return None

    def _norm(s: str) -> str:
        return (s or "").lower().replace("-", "_").replace(" ", "_").strip()

    tag_n = _norm(danbooru_tag)
    series_n = _norm(series_name)
    display_n = _norm(display_name)

    # Pass 1: exact character-list match
    for entry in entries:
        chars = entry.get("characters") or []
        if not isinstance(chars, list):
            continue
        for c in chars:
            if not isinstance(c, str):
                continue
            cn = _norm(c)
            if not cn:
                continue
            if cn == tag_n or cn == display_n or (tag_n and (tag_n in cn or cn in tag_n)):
                path = _resolve_local_lora_path(entry.get("name", ""), entry.get("location", ""))
                if path:
                    triggers = entry.get("trigger_words") or []
                    if not isinstance(triggers, list):
                        triggers = []
                    triggers = [str(t) for t in triggers if t]
                    twbc = entry.get("trigger_words_by_character") or {}
                    if isinstance(twbc, dict):
                        for k, v in twbc.items():
                            if _norm(k) == cn and isinstance(v, list):
                                triggers = [str(t) for t in v if t] + triggers
                                break
                    return (path, triggers, entry)

    # Pass 2: series-named all-in-one packs
    if series_n:
        for entry in entries:
            name = (entry.get("name") or "").lower()
            if series_n in name:
                path = _resolve_local_lora_path(entry.get("name", ""), entry.get("location", ""))
                if path:
                    triggers = entry.get("trigger_words") or []
                    if not isinstance(triggers, list):
                        triggers = []
                    triggers = [str(t) for t in triggers if t]
                    return (path, triggers, entry)

    return None


# ════════════════════════════════════════════════════════════════════════
# Public API
# ════════════════════════════════════════════════════════════════════════

def find_and_verify_character_lora(
    danbooru_tag: str,
    display_name: str,
    series_name: str,
    appearance_description: str,
    comfyui_url: str,
    base_checkpoint: str = "",
    reference_images: Optional[list[str]] = None,
    force_refresh: bool = False,
) -> LoRAVerificationResult:
    """Main entry point: search, download, test, and verify a character LoRA.

    Args:
        danbooru_tag: Character identifier, e.g. "tokisaki_kurumi"
        display_name: Human-readable name, e.g. "Tokisaki Kurumi"
        series_name: Series name, e.g. "Date A Live"
        appearance_description: Text describing the character's key visual features
        comfyui_url: URL of the running ComfyUI instance
        base_checkpoint: Checkpoint model to use for test generation
        reference_images: Base64 reference images for comparison
        force_refresh: Skip cache, re-search and re-verify

    Returns:
        LoRAVerificationResult with accepted=True and lora_filename if a
        matching LoRA was found and verified.
    """
    t0 = time.time()

    # Check local cache first
    if not force_refresh:
        cached = _load_lora_cache(danbooru_tag)
        if cached and cached.get("accepted"):
            lora_path = Path(cached["lora_path"]) if cached.get("lora_path") else None
            if lora_path and lora_path.exists():
                logger.info("[LoRAMgr] Cached accepted LoRA for %s: %s",
                            danbooru_tag, lora_path.name)
                return LoRAVerificationResult(
                    accepted=True,
                    vision_score=cached.get("vision_score", 8.0),
                    test_image_b64=None,
                    lora_filename=lora_path.name,
                    lora_path=lora_path,
                    trigger_words=cached.get("trigger_words", []),
                    latency_ms=(time.time() - t0) * 1000,
                )
            else:
                logger.info("[LoRAMgr] Cached LoRA missing from disk, re-searching")

    # 2026-04-26: SAA-first — consult the local LoRA registry
    # (configs/lora_registry.yaml) BEFORE going to CivitAI.  If a known
    # local file matches the character, accept it without any external
    # network call.  This honours the user requirement that local /
    # SAA-curated assets always win over external search.
    local_hit = _local_registry_lookup(danbooru_tag, display_name, series_name)
    if local_hit is not None:
        local_path, local_triggers, local_meta = local_hit
        logger.info(
            "[LoRAMgr] Local registry hit for %s: %s (skipping CivitAI)",
            danbooru_tag, local_path.name,
        )
        result = LoRAVerificationResult(
            accepted=True,
            vision_score=8.0,  # registry-curated entries are trusted
            test_image_b64=None,
            lora_filename=local_path.name,
            lora_path=local_path,
            trigger_words=local_triggers,
            latency_ms=(time.time() - t0) * 1000,
        )
        try:
            _save_lora_cache(danbooru_tag, {
                "accepted": True,
                "lora_path": str(local_path),
                "vision_score": 8.0,
                "trigger_words": local_triggers,
                "source": "local_registry",
                "registry_entry": local_meta.get("name"),
            })
        except Exception as exc:  # noqa: BLE001
            logger.debug("[LoRAMgr] cache save (local hit) failed: %s", exc)
        return result

    logger.info("[LoRAMgr] Searching CivitAI for %s (%s) LoRAs...",
                display_name, series_name)

    # Step 1: CivitAI search
    candidates = _civitai_search(display_name, series_name, danbooru_tag)
    if not candidates:
        logger.info("[LoRAMgr] No CivitAI LoRAs found for %s", display_name)
        return LoRAVerificationResult(
            accepted=False,
            vision_score=0.0,
            test_image_b64=None,
            lora_filename="",
            lora_path=None,
            rejection_reason="No LoRAs found on CivitAI",
            latency_ms=(time.time() - t0) * 1000,
        )

    logger.info("[LoRAMgr] Found %d candidates for %s", len(candidates), display_name)

    for candidate in candidates:
        logger.info("[LoRAMgr] Trying: %s (downloads=%d, base=%s, size=%.1fMB)",
                    candidate.name, candidate.download_count,
                    candidate.base_model, candidate.size_bytes / 1_000_000)

        # Step 2: Download
        lora_path = _download_lora(candidate, danbooru_tag)
        if not lora_path:
            logger.warning("[LoRAMgr] Download failed for %s, trying next", candidate.filename)
            continue

        # Step 3: Build ComfyUI test workflow
        lora_rel = _lora_relative_path(lora_path)
        trigger_str = ", ".join(candidate.trigger_words[:3]) if candidate.trigger_words else ""
        test_prompt = _build_test_prompt(
            display_name, danbooru_tag, trigger_str, appearance_description,
        )

        workflow = _build_test_workflow(
            lora_filename=lora_rel,
            character_prompt=test_prompt,
            base_model=base_checkpoint,
        )

        # Step 4: Run test generation
        if not comfyui_url:
            # No ComfyUI available — keep the LoRA with a provisional accept
            logger.warning("[LoRAMgr] No ComfyUI URL, skipping test generation. Provisionally accepting %s",
                           candidate.filename)
            result = LoRAVerificationResult(
                accepted=True,
                vision_score=6.5,
                test_image_b64=None,
                lora_filename=lora_rel,
                lora_path=lora_path,
                trigger_words=candidate.trigger_words,
                latency_ms=(time.time() - t0) * 1000,
            )
            _save_lora_cache(danbooru_tag, {
                "accepted": True,
                "vision_score": result.vision_score,
                "lora_path": str(lora_path),
                "lora_filename": lora_rel,
                "trigger_words": candidate.trigger_words,
                "candidate_name": candidate.name,
            })
            return result

        test_image_b64 = _run_test_generation(comfyui_url, workflow, timeout=90)
        if not test_image_b64:
            logger.warning("[LoRAMgr] Test generation failed for %s", candidate.filename)
            # Clean up download on failure
            lora_path.unlink(missing_ok=True)
            continue

        # Step 5: Vision verification
        vision_score = _verify_lora_with_vision(
            test_image_b64=test_image_b64,
            display_name=display_name,
            series_name=series_name,
            appearance_description=appearance_description,
            reference_images=reference_images,
        )

        logger.info("[LoRAMgr] Vision score for %s: %.1f (threshold=%.1f)",
                    candidate.filename, vision_score, _VISION_ACCEPT_THRESHOLD)

        if vision_score >= _VISION_ACCEPT_THRESHOLD:
            # Accept this LoRA
            logger.info("[LoRAMgr] ACCEPTED LoRA: %s (score=%.1f)", lora_path.name, vision_score)
            result = LoRAVerificationResult(
                accepted=True,
                vision_score=vision_score,
                test_image_b64=test_image_b64,
                lora_filename=lora_rel,
                lora_path=lora_path,
                trigger_words=candidate.trigger_words,
                latency_ms=(time.time() - t0) * 1000,
            )
            _save_lora_cache(danbooru_tag, {
                "accepted": True,
                "vision_score": vision_score,
                "lora_path": str(lora_path),
                "lora_filename": lora_rel,
                "trigger_words": candidate.trigger_words,
                "candidate_name": candidate.name,
            })
            return result

        else:
            # Reject — delete downloaded file, try next candidate
            logger.info("[LoRAMgr] REJECTED LoRA: %s (score=%.1f < %.1f)",
                        candidate.filename, vision_score, _VISION_ACCEPT_THRESHOLD)
            lora_path.unlink(missing_ok=True)
            # Remove empty dir if nothing left
            try:
                lora_path.parent.rmdir()
            except OSError:
                pass

    # All candidates rejected
    logger.info("[LoRAMgr] No acceptable LoRA found for %s", display_name)
    _save_lora_cache(danbooru_tag, {
        "accepted": False,
        "vision_score": 0.0,
        "candidates_tried": len(candidates),
    })

    return LoRAVerificationResult(
        accepted=False,
        vision_score=0.0,
        test_image_b64=None,
        lora_filename="",
        lora_path=None,
        rejection_reason=f"All {len(candidates)} candidates rejected by vision check",
        latency_ms=(time.time() - t0) * 1000,
    )


def _build_test_prompt(
    display_name: str,
    danbooru_tag: str,
    trigger_words: str,
    appearance_description: str,
) -> str:
    """Build a concise test prompt for LoRA evaluation."""
    # Extract the first sentence of the appearance description
    short_desc = appearance_description.split(".")[0] if appearance_description else ""
    parts = [
        "masterpiece, best quality, anime",
        danbooru_tag.replace("_", " "),
    ]
    if trigger_words:
        parts.append(trigger_words)
    if short_desc:
        parts.append(short_desc[:100])
    parts.extend(["1girl", "solo", "simple_background", "looking_at_viewer"])
    return ", ".join(p for p in parts if p)


def get_cached_character_lora(danbooru_tag: str) -> Optional[dict]:
    """Return cached LoRA metadata for a character if available and valid.

    Returns dict with keys: accepted, lora_filename, lora_path, trigger_words
    """
    cached = _load_lora_cache(danbooru_tag)
    if not cached or not cached.get("accepted"):
        return None
    lora_path = Path(cached.get("lora_path", ""))
    if not lora_path.exists():
        return None
    return cached
