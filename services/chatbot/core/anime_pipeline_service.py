"""
core.anime_pipeline_service — Service layer for the layered anime image pipeline.

Bridges the Flask / FastAPI routes and the image_pipeline.anime_pipeline
orchestrator.  Handles:
  - availability checks (ComfyUI reachable, IMAGE_PIPELINE_V2 flag)
  - request validation and AnimePipelineJob construction
  - SSE event translation to the chatbot's standard wire format
  - intermediate-image URL generation
  - error normalisation
"""

from __future__ import annotations

import base64
import json
import logging
import os
import threading as _threading
import time
from collections.abc import Generator
from dataclasses import dataclass, field
from typing import Any

try:
    from .project_paths import COMFYUI_DIR
except ImportError:  # pragma: no cover - supports top-level core imports
    from core.project_paths import COMFYUI_DIR

try:
    from .config import IMAGE_STORAGE_DIR as _IMAGE_STORAGE_DIR
except ImportError:  # pragma: no cover - supports top-level core imports
    from core.config import IMAGE_STORAGE_DIR as _IMAGE_STORAGE_DIR

logger = logging.getLogger(__name__)

# ── Feature-flag helpers ────────────────────────────────────────────────

_PIPELINE_FLAG = "IMAGE_PIPELINE_V2"
_COMFYUI_URL_KEY = "COMFYUI_URL"
_DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"

# Image storage: canonical IMAGE_STORAGE_DIR from core.config
# (keeps write and serve paths in sync — both use services/chatbot/Storage/Image_Gen/)

# ComfyUI sibling folder for the final canonical image of every run, including
# runs that ended early via Stop. Mirrors the file already written under
# Storage/Image_Gen so users can browse it next to ComfyUI/input + output.
_COMFYUI_FINAL_DIR = COMFYUI_DIR / "final"


def _mirror_final_to_comfyui(b64: str, filename: str) -> str | None:
    """Write the final image bytes into ComfyUI/final/ alongside the canonical
    Storage/Image_Gen copy. Also overwrites ``latest.png`` for quick access.

    Returns the absolute filesystem path of the written file on success, or
    None on any failure (mirroring is best-effort and never blocks the run).
    """
    if not b64 or not filename:
        return None
    try:
        _COMFYUI_FINAL_DIR.mkdir(parents=True, exist_ok=True)
        raw = base64.b64decode(b64)
        target = _COMFYUI_FINAL_DIR / filename
        target.write_bytes(raw)
        # Always-overwriting pointer so external tools can find "the last one".
        try:
            (_COMFYUI_FINAL_DIR / "latest.png").write_bytes(raw)
        except Exception:
            pass
        return str(target)
    except Exception as exc:
        logger.debug("[AnimePipelineService] ComfyUI/final mirror failed: %s", exc)
        return None


# ── Concurrency control ─────────────────────────────────────────────────────
# Limit concurrent ComfyUI pipeline jobs on local GPU.
# Override via ANIME_PIPELINE_MAX_CONCURRENT env var (default 1).
_PIPELINE_MAX_CONCURRENT = int(os.getenv("ANIME_PIPELINE_MAX_CONCURRENT", "1"))
_PIPELINE_SEMAPHORE = _threading.Semaphore(_PIPELINE_MAX_CONCURRENT)
_PIPELINE_QUEUE_LOCK = _threading.Lock()
_PIPELINE_WAITING_COUNT = 0
# Hard cap on how long a queued job will wait for a GPU slot before
# failing fast with ap_error. Prevents the "second tab stalls forever"
# bug when an earlier pipeline hangs and never releases its semaphore
# permit. Override via ANIME_PIPELINE_QUEUE_TIMEOUT_SEC env var.
_PIPELINE_QUEUE_TIMEOUT_SEC = float(os.getenv("ANIME_PIPELINE_QUEUE_TIMEOUT_SEC", "60"))


def pipeline_enabled() -> bool:
    """Return True when the anime pipeline feature flag is on.

    Explicitly set to enable: IMAGE_PIPELINE_V2=true/1/yes/on
    Empty or not set: disabled by default
    Explicitly disabled: IMAGE_PIPELINE_V2=false/0/no/off
    """
    val = os.getenv(_PIPELINE_FLAG, "").lower().strip()
    return val in ("1", "true", "yes", "on")


def comfyui_url() -> str:
    return os.getenv(_COMFYUI_URL_KEY, _DEFAULT_COMFYUI_URL)


def comfyui_reachable(timeout: float = 3.0) -> bool:
    """Quick connectivity probe against the ComfyUI /system_stats endpoint."""
    try:
        import httpx
        from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy

        RuntimePolicy.from_env().assert_url(comfyui_url(), purpose="comfyui_health")
        with httpx.Client(timeout=timeout) as client:
            r = client.get(f"{comfyui_url()}/system_stats")
            return r.status_code == 200
    except Exception:
        return False


# ── Availability check (returned to frontend as JSON) ───────────────────


@dataclass
class AvailabilityResult:
    available: bool = False
    feature_flag: bool = False
    comfyui_reachable: bool = False
    readiness: str = "blocked"
    runtime_policy: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, str] = field(default_factory=dict)
    missing_assets: list[str] = field(default_factory=list)
    active_models: list[str] = field(default_factory=list)
    endpoint_health: dict[str, bool] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "feature_flag": self.feature_flag,
            "comfyui_reachable": self.comfyui_reachable,
            "readiness": self.readiness,
            "runtime_policy": self.runtime_policy,
            "capabilities": self.capabilities,
            "missing_assets": self.missing_assets,
            "active_models": self.active_models,
            "endpoint_health": self.endpoint_health,
            "errors": self.errors,
        }


def check_availability(*, probe_remote: bool = False) -> AvailabilityResult:
    """Pre-flight check. Routes use deep endpoint probes before accepting work."""
    result = AvailabilityResult()
    result.feature_flag = pipeline_enabled()
    if not result.feature_flag:
        result.errors.append(
            f"Anime pipeline is disabled. Set {_PIPELINE_FLAG}=true to enable."
        )

    result.comfyui_reachable = comfyui_reachable()
    if not result.comfyui_reachable:
        result.errors.append(
            f"ComfyUI is not reachable at {comfyui_url()}. "
            "Start ComfyUI or set COMFYUI_URL to the correct address."
        )

    try:
        from image_pipeline.anime_pipeline.preflight import run_preflight

        preflight = run_preflight(probe_remote=probe_remote)
        result.readiness = preflight.readiness
        result.runtime_policy = preflight.runtime_policy
        result.capabilities = preflight.capabilities
        result.missing_assets = preflight.missing_assets
        result.active_models = preflight.active_models
        result.endpoint_health = preflight.endpoint_health
        result.errors.extend(preflight.errors)
        if preflight.readiness == "blocked":
            result.errors.append("Anime pipeline asset preflight is blocked")
    except Exception as exc:
        result.readiness = "blocked"
        result.errors.append(f"Anime pipeline preflight failed: {exc}")

    result.available = (
        result.feature_flag
        and result.comfyui_reachable
        and result.readiness != "blocked"
    )
    return result


# ── Request validation ──────────────────────────────────────────────────

_VALID_QUALITY = {"auto", "fast", "quality"}
_VALID_PRESETS = {"anime_quality", "anime_speed", "anime_balanced"}
# Prompt cap kept only as a safety net against pathological inputs; real
# anime prompts can easily exceed 3-4 KB once layered tags + scene + LoRA
# trigger words are concatenated. Set well above realistic usage.
_MAX_PROMPT = 20000
_MAX_REFS = 4


@dataclass
class PipelineRequest:
    """Validated request parameters for a pipeline run."""

    prompt: str = ""
    reference_images_b64: list[str] = field(default_factory=list)
    preset: str = "anime_quality"
    quality_mode: str = "quality"
    model_base: str = ""
    model_cleanup: str = ""
    model_final: str = ""
    debug: bool = False
    width: int = 0
    height: int = 0
    session_id: str = ""
    conversation_id: str = ""
    thinking_mode: str = "instant"
    # Image-only fast path: when True, the orchestrator stops after
    # composition_pass and skips structure_lock / beauty / yolo /
    # critique / upscale. Triggered by the "Chỉ tạo ảnh" toggle on
    # the chat choice card. ``batch_size`` (clamped 1-6) is the number
    # of candidate images the composition KSampler emits in a single
    # workflow; only meaningful when ``image_only`` is True.
    image_only: bool = False
    batch_size: int = 1
    deployment_profile: str = "laptop_6gb"
    content_mode: str = "sfw"
    validator_mode: str = "local"
    adult_verified: bool = False
    adult_attestation_source: str = ""
    character_key: str = ""


def validate_request(data: dict) -> tuple[PipelineRequest | None, str | None]:
    """Parse and validate incoming JSON.  Returns (request, None) or (None, error)."""
    prompt = (data.get("prompt") or "").strip()
    if not prompt:
        return None, "prompt is required"
    if len(prompt) > _MAX_PROMPT:
        return None, f"prompt too long (max {_MAX_PROMPT} chars)"

    refs = data.get("reference_images", []) or []
    if not isinstance(refs, list):
        refs = [refs]
    if len(refs) > _MAX_REFS:
        return None, f"Too many reference images (max {_MAX_REFS})"

    preset = data.get("preset", "anime_quality")
    if preset not in _VALID_PRESETS:
        preset = "anime_quality"

    quality = data.get("quality_mode", "quality")
    if quality not in _VALID_QUALITY:
        quality = "quality"

    try:
        from image_pipeline.anime_pipeline.character_pack import (
            character_is_adult_verified,
        )
        from image_pipeline.anime_pipeline.config import load_config
        from image_pipeline.anime_pipeline.adult_subject_guard import (
            assert_adult_subject_allowed,
        )
        from image_pipeline.anime_pipeline.runtime_policy import (
            AdultContentPolicy,
            RuntimePolicy,
        )

        config = load_config()
        policy = RuntimePolicy.from_config(config)
        deployment_profile = str(
            data.get("deployment_profile") or config.deployment_profile
        )
        if deployment_profile != config.deployment_profile:
            return (
                None,
                f"deployment_profile must match this worker ({config.deployment_profile})",
            )
        content_mode = str(
            data.get("content_mode") or policy.default_content_mode.value
        )
        validator_mode = str(data.get("validator_mode", "local"))
        character_key = str(data.get("character_key", "") or "")
        request_adult_verified = bool(data.get("adult_verified", False))
        adult_verified = request_adult_verified
        adult_attestation_source = "request" if request_adult_verified else ""
        if content_mode == "adult_only":
            if character_key:
                pack_verified = character_is_adult_verified(character_key)
                if not pack_verified:
                    return None, "adult_only character pack is not adult_verified"
                adult_verified = pack_verified and (
                    request_adult_verified
                    or policy.adult_content_policy
                    is AdultContentPolicy.WORKER_DEFAULT
                )
                adult_attestation_source = (
                    "character_pack" if adult_verified else ""
                )
            elif (
                policy.adult_content_policy is AdultContentPolicy.WORKER_DEFAULT
                and policy.verified_adult_worker_asserted
            ):
                adult_verified = True
                adult_attestation_source = "worker"
        policy.validate_request(
            content_mode=content_mode,
            validator_mode=validator_mode,
            adult_verified=adult_verified,
        )
        if content_mode == "adult_only":
            assert_adult_subject_allowed(
                prompt,
                adult_verified=adult_verified,
                attestation_source=adult_attestation_source,
            )
    except ValueError as exc:
        return None, str(exc)

    req = PipelineRequest(
        prompt=prompt,
        reference_images_b64=refs,
        preset=preset,
        quality_mode=quality,
        model_base=data.get("model_base", ""),
        model_cleanup=data.get("model_cleanup", ""),
        model_final=data.get("model_final", ""),
        debug=bool(data.get("debug", False)),
        width=int(data.get("width", 0)),
        height=int(data.get("height", 0)),
        session_id=data.get("session_id", ""),
        conversation_id=data.get("conversation_id", ""),
        thinking_mode=data.get("thinking_mode", "instant"),
        image_only=bool(data.get("image_only", False)),
        batch_size=max(1, min(int(data.get("batch_size", 1) or 1), 6)),
        deployment_profile=deployment_profile,
        content_mode=content_mode,
        validator_mode=validator_mode,
        adult_verified=adult_verified,
        adult_attestation_source=adult_attestation_source,
        character_key=character_key,
    )
    return req, None


# ── Job construction ────────────────────────────────────────────────────


def build_job(req: PipelineRequest) -> Any:
    """Create an AnimePipelineJob from validated request params."""
    from image_pipeline.anime_pipeline import AnimePipelineJob
    from image_pipeline.anime_pipeline.character_pack import get_character_pack

    pack = get_character_pack(req.character_key) if req.character_key else None
    prompt = req.prompt
    if pack:
        identity_tokens = [pack.prompt_alias, *pack.trigger_words]
        identity_suffix = ", ".join(token for token in identity_tokens if token)
        if identity_suffix:
            prompt = f"{prompt}, {identity_suffix}"
    job = AnimePipelineJob(
        user_prompt=prompt,
        reference_images_b64=req.reference_images_b64,
        preset=req.preset,
        quality_hint=req.quality_mode,
        session_id=req.session_id,
        thinking_mode=req.thinking_mode,
        image_only=req.image_only,
        batch_size=req.batch_size,
        deployment_profile=req.deployment_profile,
        content_mode=req.content_mode,
        validator_mode=req.validator_mode,
        adult_verified=req.adult_verified,
        adult_attestation_source=req.adult_attestation_source,
    )
    from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy

    job.network_policy = RuntimePolicy.from_profile(req.deployment_profile).to_dict()
    if pack:
        job.user_loras = [dict(lora) for lora in pack.loras]
        job.metadata["character_pack"] = {
            "key": pack.key,
            "base_model": pack.base_model,
            "refs": list(pack.refs),
            "adult_verified": pack.adult_verified,
        }
        job.metadata["model_checksums"] = dict(pack.checksums)
        job.metadata["loras"] = [dict(lora) for lora in pack.loras]
    if req.adult_attestation_source:
        job.metadata["adult_attestation_source"] = req.adult_attestation_source
    return job


# ── SSE helpers ─────────────────────────────────────────────────────────

_STAGE_LABELS = {
    "vision_analysis": "Analyzing references…",
    "layer_planning": "Planning layers…",
    "composition_pass": "Generating composition…",
    "structure_lock": "Locking structure…",
    "cleanup_pass": "Cleaning up…",
    "beauty_pass": "Beauty rendering…",
    "critique": "Critiquing result…",
    "upscale": "Upscaling…",
}

# Stages that produce a visually-meaningful intermediate worth showing as
# a "Layer N" thumbnail in the chat bubble (ChatGPT-style live gallery).
# Each entry: stage_key -> (layer_num, short_vi_label).
# Order matches the canonical pipeline pass order.
_LAYER_STAGES: dict[str, tuple[int, str]] = {
    "composition_pass": (1, "Bố cục"),
    "structure_lock": (2, "Khoá nét"),
    "beauty_pass": (3, "Tô màu"),
    "detection_inpaint": (4, "Tinh chỉnh"),
}


def _sse_line(event: str, data: dict) -> str:
    """Format a single SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _persist_intermediate_preview(job_id: str, stage: str, b64: str) -> str | None:
    """Persist a per-stage preview PNG to Storage/Image_Gen and return its
    local URL. Returns None on any failure (caller should fall back to
    embedding the b64 directly in the SSE frame).
    """
    if not b64 or not job_id or not stage:
        return None
    try:
        _IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        # Stable per-stage filename so re-runs of the same stage overwrite
        # the previous preview rather than accumulating clones.
        safe_jid = "".join(c for c in job_id if c.isalnum() or c in "-_")[:32]
        safe_stage = "".join(c for c in stage if c.isalnum() or c == "_")[:32]
        filename = f"preview_{safe_jid}_{safe_stage}.png"
        (_IMAGE_STORAGE_DIR / filename).write_bytes(base64.b64decode(b64))
        return f"/storage/images/{filename}"
    except Exception as exc:
        logger.debug("[AnimePipelineService] preview persist failed: %s", exc)
        return None


def _make_thumb_b64(b64: str, max_dim: int = 192) -> str | None:
    """Decode a full PNG b64 and return a small JPEG b64 thumbnail.

    Used to ship a tiny inline preview inside the SSE frame so the browser
    does NOT need a second HTTP roundtrip to /storage/images while the
    pipeline is still running (uvicorn workers are busy on the SSE stream
    and can stall parallel image GETs). Returns None on any failure;
    caller should then fall back to the local_url path.
    """
    if not b64:
        return None
    try:
        from io import BytesIO

        from PIL import Image

        raw = base64.b64decode(b64)
        with Image.open(BytesIO(raw)) as im:
            im = im.convert("RGB")
            im.thumbnail((max_dim, max_dim), Image.LANCZOS)
            buf = BytesIO()
            im.save(buf, format="JPEG", quality=78, optimize=True)
            return base64.b64encode(buf.getvalue()).decode("ascii")
    except Exception as exc:
        logger.debug("[AnimePipelineService] thumb b64 failed: %s", exc)
        return None


def persist_pipeline_result(job: Any, req: PipelineRequest) -> dict[str, Any]:
    """Persist a final image locally; cloud persistence is a legacy opt-in."""
    if not job.final_image_b64:
        return {}

    persisted: dict[str, Any] = {
        "db_status": {
            "mongodb": False,
            "firebase": False,
        }
    }

    filename = ""
    local_url = ""

    # Always persist local file so gallery can recover even if DB is unavailable.
    try:
        _IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        ts = time.strftime("%Y%m%d_%H%M%S")
        filename = f"anime_pipeline_{ts}_{job.job_id[:8]}.png"
        filepath = _IMAGE_STORAGE_DIR / filename
        filepath.write_bytes(base64.b64decode(job.final_image_b64))
        local_url = f"/storage/images/{filename}"
        persisted["filename"] = filename
        persisted["local_url"] = local_url
        logger.info("[AnimePipelineService] Saved final image locally: %s", filename)
        # Mirror into ComfyUI/final/ so users can browse the last image of
        # every run (including Stop-and-export snapshots) right next to
        # ComfyUI/input and ComfyUI/output. Best-effort, never blocks.
        _mirror_final_to_comfyui(job.final_image_b64, filename)
    except Exception as save_err:
        logger.warning(
            "[AnimePipelineService] Could not save image locally: %s", save_err
        )

    from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy

    policy = RuntimePolicy.from_profile(req.deployment_profile)
    persisted["network_policy"] = policy.to_dict()
    if os.getenv("ANIME_PIPELINE_ALLOW_CLOUD_PERSISTENCE", "").lower() not in (
        "1",
        "true",
        "yes",
    ):
        persisted["share_url"] = local_url
        persisted["cloud_persistence"] = "disabled_by_runtime_policy"
        return persisted

    # Persist canonical record for gallery/admin (generated_images + optional Firebase/Drive).
    try:
        from core.image_storage import store_generated_image

        metadata = {
            "filename": filename,
            "session_id": req.session_id,
            "conversation_id": req.conversation_id,
            "source": "anime_pipeline",
            "preset": req.preset,
            "quality_mode": req.quality_mode,
            "model_base": req.model_base,
            "model_cleanup": req.model_cleanup,
            "model_final": req.model_final,
            "models_used": job.models_used,
        }
        storage_result = store_generated_image(
            image_base64=job.final_image_b64,
            prompt=req.prompt,
            negative_prompt="",
            metadata=metadata,
            raw_legacy_payload={"job_id": job.job_id, "source": "anime_pipeline"},
        )

        cloud_url = storage_result.get("imgbb_url")
        drive_url = storage_result.get("drive_url")

        persisted["cloud_url"] = cloud_url
        persisted["drive_url"] = drive_url
        persisted["drive_file_id"] = storage_result.get("drive_file_id")
        persisted["share_url"] = drive_url or cloud_url or local_url
        persisted["db_status"] = {
            "mongodb": bool(storage_result.get("saved_to_mongodb")),
            "firebase": bool(storage_result.get("saved_to_firebase")),
        }
    except Exception as storage_err:
        logger.warning(
            "[AnimePipelineService] Cloud/DB persistence failed: %s", storage_err
        )
        persisted["share_url"] = local_url

    return persisted


def stream_pipeline(req: PipelineRequest) -> Generator[str, None, None]:
    """Run the anime pipeline and yield SSE text frames.

    Event types emitted:
        ap_status       — availability / init status
        ap_stage_start  — a stage has begun
        ap_stage_done   — a stage has completed
        ap_preview      — intermediate image. Always emitted for the
                          four "layer" stages (composition_pass,
                          structure_lock, beauty_pass, detection_inpaint)
                          with a tiny local_url (saved to disk). In debug
                          mode it is also emitted for any other stage and
                          falls back to image_b64 when persistence fails.
        ap_refine       — refine loop iteration
        ap_result       — final image + manifest
        ap_error        — recoverable or fatal error
        ap_done         — stream complete sentinel
    """
    from image_pipeline.anime_pipeline import AnimePipelineOrchestrator

    job = build_job(req)

    # Yield ap_status FIRST so the browser starts rendering immediately.
    # The orchestrator is constructed *after* this yield so the client
    # receives the initial status frame before any blocking init work runs.
    yield _sse_line(
        "ap_status",
        {
            "job_id": job.job_id,
            "message": "Pipeline started",
            "stages": list(_STAGE_LABELS.keys()),
        },
    )

    # Construct orchestrator after the first yield — takes ~2 s on cold
    # import because it loads YAML config and instantiates all agents.
    try:
        orchestrator = AnimePipelineOrchestrator()
    except Exception as _orch_exc:
        logger.error(
            "[AnimePipelineService] Orchestrator init failed for job=%s: %s",
            job.job_id,
            _orch_exc,
        )
        yield _sse_line(
            "ap_error",
            {
                "job_id": job.job_id,
                "stage": "init",
                "error": f"Pipeline init failed: {_orch_exc}",
                "recoverable": False,
            },
        )
        yield _sse_line("ap_done", {"job_id": job.job_id})
        return

    # ── Concurrency gate: at most _PIPELINE_MAX_CONCURRENT jobs on GPU ──
    global _PIPELINE_WAITING_COUNT
    if not _PIPELINE_SEMAPHORE.acquire(blocking=False):
        with _PIPELINE_QUEUE_LOCK:
            _PIPELINE_WAITING_COUNT += 1
            _queue_pos = _PIPELINE_WAITING_COUNT
        yield _sse_line(
            "ap_queued",
            {
                "job_id": job.job_id,
                "position": _queue_pos,
                "message": f"Pipeline queued — vị trí {_queue_pos}. Đang chờ GPU…",
            },
        )
        _wait_start = time.time()
        _last_keepalive = 0.0
        _acquired = False
        while True:
            if _PIPELINE_SEMAPHORE.acquire(blocking=False):
                _acquired = True
                break
            _elapsed = time.time() - _wait_start
            if _elapsed >= _PIPELINE_QUEUE_TIMEOUT_SEC:
                break
            if _elapsed - _last_keepalive >= 15:
                _last_keepalive = _elapsed
                yield ": keepalive\n"
            time.sleep(1.0)
        with _PIPELINE_QUEUE_LOCK:
            _PIPELINE_WAITING_COUNT -= 1
            logger.debug(
                "[AnimePipelineService] queue_waiting_count=%d", _PIPELINE_WAITING_COUNT
            )
        if not _acquired:
            logger.warning(
                "[AnimePipelineService] queue timeout after %.0fs for job=%s",
                _PIPELINE_QUEUE_TIMEOUT_SEC,
                job.job_id,
            )
            yield _sse_line(
                "ap_error",
                {
                    "job_id": job.job_id,
                    "stage": "queue",
                    "error": (
                        f"Pipeline đang bận — không xin được GPU sau "
                        f"{int(_PIPELINE_QUEUE_TIMEOUT_SEC)}s. Hãy thử lại sau."
                    ),
                    "recoverable": False,
                },
            )
            yield _sse_line("ap_done", {"job_id": job.job_id})
            return

    try:
        yield from _run_pipeline_inner(orchestrator, job, req)
    finally:
        _PIPELINE_SEMAPHORE.release()


def _run_pipeline_inner(
    orchestrator: Any,
    job: Any,
    req: PipelineRequest,
) -> Generator[str, None, None]:
    """Inner generator: run the pipeline event loop and yield SSE frames.

    Called by stream_pipeline() inside a try/finally that always releases
    the global concurrency semaphore.
    """
    try:
        for event in orchestrator.run_stream(job):
            etype = event.get("event", "")
            edata = event.get("data", {})

            if etype == "anime_pipeline_pipeline_start":
                yield _sse_line(
                    "ap_status",
                    {
                        "job_id": job.job_id,
                        "message": "Pipeline initialised",
                        "stages": edata.get("stages", []),
                    },
                )

            elif etype == "anime_pipeline_stage_start":
                stage = edata.get("stage", "")
                yield _sse_line(
                    "ap_stage_start",
                    {
                        "stage": stage,
                        "stage_num": edata.get("stage_num", 0),
                        "total_stages": edata.get("total_stages", 7),
                        "label": _STAGE_LABELS.get(stage, stage),
                        "vram_profile": edata.get("vram_profile", ""),
                    },
                )
                # ChatGPT-style: surface a placeholder "Layer N" card the
                # moment the stage starts. We reuse the previous layer's
                # pixels so the user sees the image-being-worked-on right
                # away. Frame is marked pending=True so the UI shows
                # "Đang tạo" status; the same slot is later refreshed by
                # the real preview emitted on stage_done.
                layer_meta_start = _LAYER_STAGES.get(stage)
                if layer_meta_start is not None:
                    placeholder_b64 = _latest_any_intermediate_b64(job)
                    placeholder_url: str | None = None
                    placeholder_thumb: str | None = None
                    if placeholder_b64:
                        placeholder_url = _persist_intermediate_preview(
                            job.job_id,
                            f"{stage}_pending",
                            placeholder_b64,
                        )
                        # Inline thumb so the UI never depends on the
                        # /storage/images route during pipeline run (the
                        # SSE worker keeps that path stalled).
                        placeholder_thumb = _make_thumb_b64(placeholder_b64)
                    if placeholder_url or placeholder_thumb or req.debug:
                        frame_start: dict[str, Any] = {
                            "stage": stage,
                            "label": _STAGE_LABELS.get(stage, stage),
                            "job_id": job.job_id,
                            "layer_num": layer_meta_start[0],
                            "layer_label": layer_meta_start[1],
                            "pending": True,
                        }
                        if placeholder_thumb:
                            frame_start["thumb_b64"] = placeholder_thumb
                        if placeholder_url:
                            frame_start["local_url"] = placeholder_url
                        elif placeholder_b64 and req.debug:
                            frame_start["image_b64"] = placeholder_b64
                        yield _sse_line("ap_preview", frame_start)

            elif etype == "anime_pipeline_stage_complete":
                stage = edata.get("stage", "")
                yield _sse_line(
                    "ap_stage_done",
                    {
                        "stage": stage,
                        "stage_num": edata.get("stage_num", 0),
                        "latency_ms": edata.get("latency_ms", 0),
                    },
                )
                # After critique, emit critique result for UI score badge
                if stage == "critique" and job.critique_results:
                    cr = job.critique_results[-1]
                    yield _sse_line(
                        "ap_critique_result",
                        {
                            "stage": "critique",
                            "round": len(job.critique_results) - 1,
                            "score": round(cr.overall_score, 1),
                            "passed": cr.passed,
                            "retry": cr.retry_recommendation,
                            "issues": (cr.all_issues or [])[:4],
                            "suggestions": (cr.prompt_patch or [])[:3],
                            "model_used": cr.model_used or "",
                        },
                    )

                # After layer planning, emit the full pass plan for UI chips
                if stage == "layer_planning" and job.layer_plan:
                    plan = job.layer_plan
                    _PASS_ICONS = {
                        "composition": "🎨",
                        "cleanup": "🧹",
                        "beauty": "✨",
                        "structure_lock": "🔒",
                        "upscale": "📐",
                    }
                    passes_summary = [
                        {
                            "name": p.pass_name,
                            "steps": p.steps,
                            "denoise": round(p.denoise, 2),
                            "icon": _PASS_ICONS.get(p.pass_name, "⚙️"),
                        }
                        for p in plan.passes[:5]
                    ]
                    yield _sse_line(
                        "ap_layer_plan",
                        {
                            "passes": passes_summary,
                            "total_passes": len(plan.passes),
                            "resolution": f"{plan.resolution_width}\u00d7{plan.resolution_height}",
                            "subject": (
                                plan.subject_list[0] if plan.subject_list else ""
                            ),
                        },
                    )
                # Auto-emit a "Layer N" preview for visually-meaningful
                # stages (composition, structure, beauty, detection_inpaint).
                # In debug mode we additionally surface previews for any
                # stage that produced an intermediate. Each preview is
                # persisted to disk so the SSE frame can carry a tiny
                # local_url instead of a multi-MB base64 blob.
                layer_meta = _LAYER_STAGES.get(stage)
                want_preview = layer_meta is not None or req.debug
                if want_preview:
                    preview_b64 = _latest_intermediate_b64(job, stage)
                    # For layer stages that don't add a fresh intermediate
                    # (notably structure_lock, often a 0-step pass-through)
                    # fall back to whatever the most recent intermediate
                    # is, so the layer card always shows *something*.
                    if not preview_b64 and layer_meta is not None:
                        preview_b64 = _latest_any_intermediate_b64(job)
                    if preview_b64:
                        local_url = _persist_intermediate_preview(
                            job.job_id,
                            stage,
                            preview_b64,
                        )
                        thumb_b64 = _make_thumb_b64(preview_b64)
                        frame = {
                            "stage": stage,
                            "label": _STAGE_LABELS.get(stage, stage),
                            "job_id": job.job_id,
                        }
                        if layer_meta is not None:
                            frame["layer_num"] = layer_meta[0]
                            frame["layer_label"] = layer_meta[1]
                        if thumb_b64:
                            frame["thumb_b64"] = thumb_b64
                        if local_url:
                            frame["local_url"] = local_url
                        elif req.debug:
                            # Fallback: embed b64 only when debug forced
                            # the preview AND on-disk persistence failed.
                            frame["image_b64"] = preview_b64
                        if local_url or thumb_b64 or req.debug:
                            yield _sse_line("ap_preview", frame)

            elif etype == "anime_pipeline_refine_start":
                yield _sse_line(
                    "ap_refine",
                    {
                        "round": edata.get("round", 0),
                        "max_rounds": edata.get("max_rounds", 0),
                        "previous_score": edata.get("previous_score", 0),
                    },
                )

            elif etype == "anime_pipeline_refine_reasoning":
                yield _sse_line(
                    "ap_refine_reasoning",
                    {
                        "round": edata.get("round", 0),
                        "reason": edata.get("reason", ""),
                        "worst_dimensions": edata.get("worst_dimensions", []),
                        "actions": edata.get("actions", []),
                        "score_history": edata.get("score_history", []),
                    },
                )

            elif etype == "anime_pipeline_full_restart":
                yield _sse_line(
                    "ap_full_restart",
                    {
                        "restart_num": edata.get("restart_num", 0),
                        "best_score": edata.get("best_score", 0),
                        "reason": edata.get("reason", ""),
                    },
                )

            elif etype == "anime_pipeline_research_status":
                # 2026-04-29: relay character_research diagnostics to UI so
                # the user sees "Đã dùng N ảnh local cache + K ảnh web" or
                # "Bỏ qua web search (đủ ref local)" instead of a silent
                # stage_done. Read by anime-pipeline.js → ap_research_status.
                yield _sse_line(
                    "ap_research_status",
                    {
                        "stage": edata.get("stage", "character_research"),
                        "danbooru_tag": edata.get("danbooru_tag", ""),
                        "display_name": edata.get("display_name", ""),
                        "local_refs": int(edata.get("local_refs", 0)),
                        "web_refs": int(edata.get("web_refs", 0)),
                        "web_search_skipped": bool(
                            edata.get("web_search_skipped", False)
                        ),
                        "nsfw_intent": bool(edata.get("nsfw_intent", False)),
                        "cached": bool(edata.get("cached", False)),
                        "confidence": float(edata.get("confidence", 0.0)),
                        "latency_ms": float(edata.get("latency_ms", 0.0)),
                    },
                )

            elif etype == "anime_pipeline_vision_reasoning":
                # 2026-04-29: surface which vision provider answered so
                # the UI can show e.g. "Vision: grok-2-vision-1212 (NSFW
                # chain)" instead of leaving the chain opaque.
                yield _sse_line(
                    "ap_vision_status",
                    {
                        "stage": "vision_analysis",
                        "model_used": edata.get("model_used", "unknown"),
                        "confidence": float(edata.get("confidence", 0.0)),
                        "nsfw_level": edata.get("nsfw_level", "unknown"),
                        "character_detected": bool(
                            edata.get("character_detected", False)
                        ),
                        "character_name": edata.get("character_name") or "",
                        "tag_count": len(edata.get("anime_tags", []) or []),
                    },
                )

            elif etype == "anime_pipeline_stage_error":
                yield _sse_line(
                    "ap_error",
                    {
                        "stage": edata.get("stage", ""),
                        "error": edata.get("error", "Unknown error"),
                        "recoverable": True,
                    },
                )

            elif etype == "anime_pipeline_pipeline_error":
                yield _sse_line(
                    "ap_error",
                    {
                        "error": edata.get("error", "Pipeline failed"),
                        "recoverable": False,
                        "has_fallback": edata.get("has_fallback_image", False),
                    },
                )

            elif etype == "anime_pipeline_pipeline_cancelled":
                # User pressed "Stop & export" — orchestrator already set
                # job.final_image_b64 to the best-so-far snapshot. Forward a
                # dedicated frame so the UI can swap labels; the regular
                # ap_result with the partial image still flows below.
                yield _sse_line(
                    "ap_cancelled",
                    {
                        "job_id": job.job_id,
                        "stage": edata.get("stage", ""),
                        "has_image": edata.get("has_image", False),
                        "message": edata.get("message", "Đã ngưng pipeline"),
                    },
                )

            elif etype == "anime_pipeline_pipeline_complete":
                pass  # Handled below after loop

    except Exception as exc:
        logger.error("[AnimePipelineService] Error: %s", exc, exc_info=True)
        yield _sse_line(
            "ap_error",
            {
                "error": str(exc),
                "recoverable": False,
            },
        )

    # ── Final result ────────────────────────────────────────────────
    manifest = job.to_dict()
    result_data: dict[str, Any] = {
        "job_id": job.job_id,
        "status": job.status.value,
        "manifest": manifest,
        "has_image": job.final_image_b64 is not None,
        "total_latency_ms": round(job.total_latency_ms, 1),
        "stages_executed": job.stages_executed,
        "refine_rounds": job.refine_rounds,
        "models_used": job.models_used,
    }

    if job.final_image_b64:
        result_data["image_b64"] = job.final_image_b64
        result_data.update(persist_pipeline_result(job, req))

    # Image-only batch mode: persist every candidate image so the
    # frontend can render a clickable gallery. The first one is
    # already the canonical final_image_b64 above; we surface the
    # full list (with local URLs) under ``images`` so the UI can
    # show all of them at once and each opens in the lightbox at
    # full resolution. Each candidate is saved to /storage/images
    # under its own filename so the gallery survives a page reload.
    extra_images: list[str] = list(getattr(job, "final_images_b64", []) or [])
    if req.image_only and len(extra_images) > 1:
        gallery: list[dict[str, Any]] = []
        try:
            _IMAGE_STORAGE_DIR.mkdir(parents=True, exist_ok=True)
            ts = time.strftime("%Y%m%d_%H%M%S")
            safe_jid = "".join(c for c in job.job_id if c.isalnum() or c in "-_")[:16]
            for idx, b64 in enumerate(extra_images):
                if not b64:
                    continue
                fname = f"anime_pipeline_io_{ts}_{safe_jid}_{idx}.png"
                try:
                    (_IMAGE_STORAGE_DIR / fname).write_bytes(base64.b64decode(b64))
                    # Also drop every candidate into ComfyUI/final/ — the
                    # last write also refreshes latest.png so it points at
                    # the most recent image-only batch tile.
                    _mirror_final_to_comfyui(b64, fname)
                    gallery.append(
                        {
                            "index": idx,
                            "local_url": f"/storage/images/{fname}",
                            "filename": fname,
                        }
                    )
                except Exception as save_err:
                    logger.warning(
                        "[AnimePipelineService] image_only save %d failed: %s",
                        idx,
                        save_err,
                    )
                    gallery.append({"index": idx, "image_b64": b64})
        except Exception as exc:
            logger.warning(
                "[AnimePipelineService] image_only gallery setup failed: %s", exc
            )
            gallery = [
                {"index": i, "image_b64": b} for i, b in enumerate(extra_images) if b
            ]
        if gallery:
            result_data["images"] = gallery
            result_data["image_only"] = True
            result_data["batch_count"] = len(gallery)

    yield _sse_line("ap_result", result_data)
    yield _sse_line("ap_done", {"job_id": job.job_id})


def _latest_intermediate_b64(job: Any, stage: str) -> str | None:
    """Return the most recent intermediate image b64 for *stage*, if any.

    For ``detection_inpaint`` the orchestrator stores per-region snapshots
    under stage names like ``detail_face`` / ``detail_eye``, so we accept
    that prefix as a match.
    """
    accept_prefix = "detail_" if stage == "detection_inpaint" else None
    for img in reversed(job.intermediates):
        if not img.image_b64:
            continue
        if img.stage == stage:
            return img.image_b64
        if accept_prefix and img.stage.startswith(accept_prefix):
            return img.image_b64
    return None


def _latest_any_intermediate_b64(job: Any) -> str | None:
    """Return the most recent intermediate b64 of any stage, if any.

    Used as a placeholder image for layer stages that are *about to start*
    or that finish without producing a fresh intermediate (e.g.
    ``structure_lock`` which is often a near-noop pass-through). Showing
    the previous layer's pixels gives the user immediate feedback that the
    next layer is being worked on, instead of an empty card.
    """
    for img in reversed(job.intermediates):
        if img.image_b64:
            return img.image_b64
    return None
