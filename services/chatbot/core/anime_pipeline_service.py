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
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generator, Optional

logger = logging.getLogger(__name__)

# ── Feature-flag helpers ────────────────────────────────────────────────

_PIPELINE_FLAG = "IMAGE_PIPELINE_V2"
_COMFYUI_URL_KEY = "COMFYUI_URL"
_DEFAULT_COMFYUI_URL = "http://127.0.0.1:8188"

# Image storage: services/chatbot/Storage/Image_Gen/
_IMAGE_STORAGE_DIR = Path(__file__).parent.parent / "Storage" / "Image_Gen"


def pipeline_enabled() -> bool:
    """Return True when the anime pipeline feature flag is on.

    Defaults to True — set IMAGE_PIPELINE_V2=false to explicitly disable.
    """
    val = os.getenv(_PIPELINE_FLAG, "").lower()
    if val in ("0", "false", "no", "off"):
        return False
    # Enabled by default (or explicitly via "1"/"true"/"yes"/"on")
    return True


def comfyui_url() -> str:
    return os.getenv(_COMFYUI_URL_KEY, _DEFAULT_COMFYUI_URL)


def comfyui_reachable(timeout: float = 3.0) -> bool:
    """Quick connectivity probe against the ComfyUI /system_stats endpoint."""
    try:
        import httpx
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
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "available": self.available,
            "feature_flag": self.feature_flag,
            "comfyui_reachable": self.comfyui_reachable,
            "errors": self.errors,
        }


def check_availability() -> AvailabilityResult:
    """Pre-flight check before accepting a pipeline request."""
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

    result.available = result.feature_flag and result.comfyui_reachable
    return result


# ── Request validation ──────────────────────────────────────────────────

_VALID_QUALITY = {"auto", "fast", "quality"}
_VALID_PRESETS = {"anime_quality", "anime_speed", "anime_balanced"}
_MAX_PROMPT = 2000
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


def validate_request(data: dict) -> tuple[Optional[PipelineRequest], Optional[str]]:
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
    )
    return req, None


# ── Job construction ────────────────────────────────────────────────────

def build_job(req: PipelineRequest) -> Any:
    """Create an AnimePipelineJob from validated request params."""
    from image_pipeline.anime_pipeline import AnimePipelineJob

    job = AnimePipelineJob(
        user_prompt=req.prompt,
        reference_images_b64=req.reference_images_b64,
        preset=req.preset,
        quality_hint=req.quality_mode,
        session_id=req.session_id,
    )
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


def _sse_line(event: str, data: dict) -> str:
    """Format a single SSE frame."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def persist_pipeline_result(job: Any, req: PipelineRequest) -> dict[str, Any]:
    """Persist a final anime-pipeline image to local storage and cloud/db backends."""
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
    except Exception as save_err:
        logger.warning("[AnimePipelineService] Could not save image locally: %s", save_err)

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
        logger.warning("[AnimePipelineService] Cloud/DB persistence failed: %s", storage_err)
        persisted["share_url"] = local_url

    return persisted


def stream_pipeline(req: PipelineRequest) -> Generator[str, None, None]:
    """Run the anime pipeline and yield SSE text frames.

    Event types emitted:
        ap_status       — availability / init status
        ap_stage_start  — a stage has begun
        ap_stage_done   — a stage has completed
        ap_preview      — intermediate image (debug mode only)
        ap_refine       — refine loop iteration
        ap_result       — final image + manifest
        ap_error        — recoverable or fatal error
        ap_done         — stream complete sentinel
    """
    from image_pipeline.anime_pipeline import AnimePipelineOrchestrator

    job = build_job(req)
    orchestrator = AnimePipelineOrchestrator()

    yield _sse_line("ap_status", {
        "job_id": job.job_id,
        "message": "Pipeline started",
        "stages": list(_STAGE_LABELS.keys()),
    })

    try:
        for event in orchestrator.run_stream(job):
            etype = event.get("event", "")
            edata = event.get("data", {})

            if etype == "anime_pipeline_pipeline_start":
                yield _sse_line("ap_status", {
                    "job_id": job.job_id,
                    "message": "Pipeline initialised",
                    "stages": edata.get("stages", []),
                })

            elif etype == "anime_pipeline_stage_start":
                stage = edata.get("stage", "")
                yield _sse_line("ap_stage_start", {
                    "stage": stage,
                    "stage_num": edata.get("stage_num", 0),
                    "total_stages": edata.get("total_stages", 7),
                    "label": _STAGE_LABELS.get(stage, stage),
                    "vram_profile": edata.get("vram_profile", ""),
                })

            elif etype == "anime_pipeline_stage_complete":
                stage = edata.get("stage", "")
                yield _sse_line("ap_stage_done", {
                    "stage": stage,
                    "stage_num": edata.get("stage_num", 0),
                    "latency_ms": edata.get("latency_ms", 0),
                })
                # After critique, emit critique result for UI score badge
                if stage == "critique" and job.critique_results:
                    cr = job.critique_results[-1]
                    yield _sse_line("ap_critique_result", {
                        "stage": "critique",
                        "round": len(job.critique_results) - 1,
                        "score": round(cr.overall_score, 1),
                        "passed": cr.passed,
                        "retry": cr.retry_recommendation,
                        "issues": (cr.all_issues or [])[:4],
                        "suggestions": (cr.prompt_patch or [])[:3],
                        "model_used": cr.model_used or "",
                    })

                # After layer planning, emit the full pass plan for UI chips
                if stage == "layer_planning" and job.layer_plan:
                    plan = job.layer_plan
                    _PASS_ICONS = {
                        "composition": "🎨", "cleanup": "🧹", "beauty": "✨",
                        "structure_lock": "🔒", "upscale": "📐",
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
                    yield _sse_line("ap_layer_plan", {
                        "passes": passes_summary,
                        "total_passes": len(plan.passes),
                        "resolution": f"{plan.resolution_width}\u00d7{plan.resolution_height}",
                        "subject": plan.subject_list[0] if plan.subject_list else "",
                    })
                # Send intermediate preview in debug mode
                if req.debug:
                    preview = _latest_intermediate_b64(job, stage)
                    if preview:
                        yield _sse_line("ap_preview", {
                            "stage": stage,
                            "image_b64": preview,
                        })

            elif etype == "anime_pipeline_refine_start":
                yield _sse_line("ap_refine", {
                    "round": edata.get("round", 0),
                    "max_rounds": edata.get("max_rounds", 0),
                    "previous_score": edata.get("previous_score", 0),
                })

            elif etype == "anime_pipeline_stage_error":
                yield _sse_line("ap_error", {
                    "stage": edata.get("stage", ""),
                    "error": edata.get("error", "Unknown error"),
                    "recoverable": True,
                })

            elif etype == "anime_pipeline_pipeline_error":
                yield _sse_line("ap_error", {
                    "error": edata.get("error", "Pipeline failed"),
                    "recoverable": False,
                    "has_fallback": edata.get("has_fallback_image", False),
                })

            elif etype == "anime_pipeline_pipeline_complete":
                pass  # Handled below after loop

    except Exception as exc:
        logger.error("[AnimePipelineService] Error: %s", exc, exc_info=True)
        yield _sse_line("ap_error", {
            "error": str(exc),
            "recoverable": False,
        })

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

    yield _sse_line("ap_result", result_data)
    yield _sse_line("ap_done", {"job_id": job.job_id})


def _latest_intermediate_b64(job: Any, stage: str) -> Optional[str]:
    """Return the most recent intermediate image b64 for *stage*, if any."""
    for img in reversed(job.intermediates):
        if img.stage == stage and img.image_b64:
            return img.image_b64
    return None
