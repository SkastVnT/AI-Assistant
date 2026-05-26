"""
UpscaleAgent — Stage 7: RealESRGAN upscale via ComfyUI.

Upscales the final beauty-pass image using RealESRGAN anime model.
This is the last stage before returning the final result.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

from ..comfy_client import ComfyClient
from ..config import AnimePipelineConfig
from ..schemas import AnimePipelineJob, AnimePipelineStatus

logger = logging.getLogger(__name__)


def _query_available_upscale_models(base_url: str) -> list[str]:
    """Ask ComfyUI which upscale models are installed via /object_info."""
    try:
        with httpx.Client(timeout=5) as client:
            resp = client.get(f"{base_url}/object_info/UpscaleModelLoader")
            if resp.status_code != 200:
                return []
            info = resp.json()
            # Path: UpscaleModelLoader → input → required → model_name → [0] (list)
            models = (
                info.get("UpscaleModelLoader", {})
                .get("input", {})
                .get("required", {})
                .get("model_name", [[]])[0]
            )
            return models if isinstance(models, list) else []
    except Exception as e:
        logger.debug("[Upscale] Could not query available models: %s", e)
        return []


class UpscaleAgent:
    """Upscale final image via ComfyUI RealESRGAN."""

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._client = ComfyClient(base_url=config.comfyui_url)

    def _resolve_upscale_model(self) -> Optional[str]:
        """Return a model name that ComfyUI actually has installed.

        Priority: configured model → fallback model → any installed model.
        Returns None when nothing is installed (upscale stage is then skipped).
        """
        available = _query_available_upscale_models(self._client.base_url)
        if not available:
            logger.warning(
                "[Upscale] No upscale models found in ComfyUI — skipping upscale"
            )
            return None

        preferred = [
            self._config.upscale_model,
            self._config.upscale_fallback_model,
            "RealESRGAN_x4plus_anime_6B",
            "RealESRGAN_x4plus",
            "4x-AnimeSharp",
            "4x_NMKD-Siax_200k",
        ]
        for name in preferred:
            if name and name in available:
                if name != self._config.upscale_model:
                    logger.info(
                        "[Upscale] Configured model '%s' not found — using '%s' instead",
                        self._config.upscale_model,
                        name,
                    )
                return name

        # Use first available as last resort
        logger.info("[Upscale] Using first available upscale model: %s", available[0])
        return available[0]

    def execute(self, job: AnimePipelineJob) -> AnimePipelineJob:
        """Run upscale on the latest pipeline output."""
        job.status = AnimePipelineStatus.UPSCALING
        t0 = time.time()

        # Check if upscale is requested
        if job.layer_plan and not job.layer_plan.upscale_pass:
            logger.info("[Upscale] Skipped (not requested)")
            self._set_final_image(job)
            job.mark_stage("upscale", 0.0)
            return job

        # Pre-flight: verify a model is actually installed before submitting
        model_name = self._resolve_upscale_model()
        if not model_name:
            logger.warning(
                "[Upscale] No upscale model available — using non-upscaled image"
            )
            self._set_final_image(job)
            job.mark_stage("upscale", 0.0)
            return job

        # Get latest output
        source_b64 = self._get_latest_output(job)
        if not source_b64:
            logger.warning("[Upscale] No image to upscale")
            self._set_final_image(job)
            job.mark_stage("upscale", 0.0)
            return job

        workflow = self._build_upscale_workflow(source_b64, model_name)

        try:
            upscaled_b64 = self._submit_and_wait(workflow)
        except Exception as e:
            logger.warning("[Upscale] Failed: %s, using non-upscaled image", e)
            upscaled_b64 = None

        if upscaled_b64:
            job.add_intermediate("upscale", upscaled_b64, model=model_name)
            job.final_image_b64 = upscaled_b64
        else:
            self._set_final_image(job)

        latency = (time.time() - t0) * 1000
        job.mark_stage("upscale", latency)
        logger.info("[Upscale] Done in %.0fms", latency)
        return job

    def _get_latest_output(self, job: AnimePipelineJob) -> Optional[str]:
        """Get the most recent output image."""
        for img in reversed(job.intermediates):
            if img.stage in ("beauty_pass", "composition_pass"):
                return img.image_b64
        return None

    def _set_final_image(self, job: AnimePipelineJob) -> None:
        """Set the final image from the best intermediate."""
        for img in reversed(job.intermediates):
            if img.stage in ("beauty_pass", "composition_pass"):
                job.final_image_b64 = img.image_b64
                return

    def _build_upscale_workflow(self, source_b64: str, model_name: str) -> dict:
        """Build ComfyUI upscale workflow.

        Uses LoadImageFromBase64 — ComfyClient._preprocess_workflow will
        convert this to an upload + LoadImage node automatically.
        """
        return {
            "1": {
                "class_type": "LoadImageFromBase64",
                "inputs": {"base64_image": source_b64},
            },
            "2": {
                "class_type": "UpscaleModelLoader",
                "inputs": {"model_name": model_name},
            },
            "3": {
                "class_type": "ImageUpscaleWithModel",
                "inputs": {
                    "upscale_model": ["2", 0],
                    "image": ["1", 0],
                },
            },
            "4": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "anime_pipeline/upscaled",
                    "images": ["3", 0],
                },
            },
        }

    def _submit_and_wait(self, workflow: dict, timeout_s: int = 120) -> Optional[str]:
        """Submit upscale workflow via ComfyClient and return result as base64."""
        result = self._client.submit_workflow(
            workflow,
            job_id="upscale",
            pass_name="upscale",
        )
        if not result.success:
            raise RuntimeError(result.error or "Upscale workflow failed")
        if not result.images_b64:
            raise RuntimeError("Upscale completed but no output image")
        return result.images_b64[0]

    # ── New-pipeline SDXL Ultimate-SD-Upscale pass ──────────────────────
    # Used by orchestrator's reordered flow:
    #   composition → upscale_pre 2× → structure_lock → YOLO → beauty
    #     → critique loop → upscale_final 1.5×
    # Distinct from .execute() (which is the legacy single ESRGAN pass)
    # so both can coexist while the new flow is on by default.

    def execute_sdxl_pass(
        self,
        job: AnimePipelineJob,
        *,
        factor: float,
        denoise: float,
        stage_name: str,
        steps: int = 20,
        cfg: float = 5.5,
    ) -> AnimePipelineJob:
        """Run a SDXL Ultimate-SD-Upscale pass at ``factor`` & ``denoise``.

        The result is appended to ``job.intermediates`` with the given
        ``stage_name`` so downstream agents (which read the latest
        intermediate by stage tag) pick up the upscaled image
        transparently. ``job.final_image_b64`` is also updated.

        Failure modes (no upscale model, no SDXL checkpoint, no source
        image, ComfyUI error) all degrade gracefully — the job retains
        whatever image it already had and the stage timing records 0.
        """
        from ..workflow_builder import WorkflowBuilder

        t0 = time.time()
        job.status = AnimePipelineStatus.UPSCALING

        upscale_model = self._resolve_upscale_model()
        if not upscale_model:
            logger.warning("[UpscaleSDXL:%s] No upscale model — skipping", stage_name)
            job.mark_stage(stage_name, 0.0)
            return job

        cfg_obj = self._config
        checkpoint = (
            cfg_obj.beauty_model.checkpoint or cfg_obj.composition_model.checkpoint
        )
        if not checkpoint:
            logger.warning("[UpscaleSDXL:%s] No SDXL checkpoint — skipping", stage_name)
            job.mark_stage(stage_name, 0.0)
            return job

        # Prefer the latest beauty/composition image; fall back to any
        # intermediate so a re-run after detection_inpaint also works.
        source_b64: Optional[str] = None
        for img in reversed(job.intermediates):
            if img.stage in ("beauty_pass", "composition_pass") or img.stage.startswith(
                "detail_"
            ):
                source_b64 = img.image_b64
                break
        if not source_b64:
            for img in reversed(job.intermediates):
                if img.image_b64:
                    source_b64 = img.image_b64
                    break
        if not source_b64:
            logger.warning("[UpscaleSDXL:%s] No source image", stage_name)
            job.mark_stage(stage_name, 0.0)
            return job

        # Build a positive prompt that preserves the user's text *and*
        # the beauty pass prompt (if available) so NSFW vocalizations
        # like ``english text "NGHHH~♥♥"`` survive the redraw.
        beauty_positive = ""
        beauty_negative = ""
        if job.layer_plan and job.layer_plan.passes:
            for p in reversed(job.layer_plan.passes):
                if p.pass_name in ("beauty", "beauty_pass"):
                    beauty_positive = p.positive_prompt or ""
                    beauty_negative = p.negative_prompt or ""
                    break
        positive = ", ".join(
            filter(
                None,
                [
                    beauty_positive,
                    cfg_obj.quality_prefix or "masterpiece, best quality",
                    job.user_prompt,
                ],
            )
        )
        negative = beauty_negative or (cfg_obj.negative_base or "lowres, worst quality")

        try:
            builder = WorkflowBuilder()
            workflow = builder.build_ultimate_sd_upscale(
                image_b64=source_b64,
                upscale_model=upscale_model,
                upscale_by=factor,
                checkpoint=checkpoint,
                positive_prompt=positive,
                negative_prompt=negative,
                seed=int(time.time()) & 0x7FFF_FFFF,
                steps=steps,
                cfg=cfg,
                denoise=denoise,
                tile_width=cfg_obj.upscale_tile_size,
                tile_height=cfg_obj.upscale_tile_size,
            )
            result = self._client.submit_workflow(
                workflow,
                job_id=stage_name,
                pass_name=stage_name,
            )
            if not result.success or not result.images_b64:
                err = (
                    result.error
                    or getattr(result, "validation_error", None)
                    or "no images"
                )
                logger.warning(
                    "[UpscaleSDXL:%s] %s — keeping previous image", stage_name, err
                )
                job.mark_stage(stage_name, (time.time() - t0) * 1000)
                return job

            out_b64 = result.images_b64[0]
            job.add_intermediate(
                stage_name, out_b64, model=f"{upscale_model}+{checkpoint}"
            )
            job.final_image_b64 = out_b64

        except Exception as exc:
            logger.warning(
                "[UpscaleSDXL:%s] Failed: %s — keeping previous image", stage_name, exc
            )

        job.mark_stage(stage_name, (time.time() - t0) * 1000)
        logger.info(
            "[UpscaleSDXL:%s] Done factor=%.2f denoise=%.2f",
            stage_name,
            factor,
            denoise,
        )
        return job
