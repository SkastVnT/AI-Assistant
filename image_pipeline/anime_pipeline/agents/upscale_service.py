"""
UpscaleService — Enhanced upscale stage using WorkflowBuilder + ComfyClient.

Primary path: Ultimate SD Upscale (tiled img2img during upscale).
Fallback path: ImageUpscaleWithModel + ImageScale (simple model upscale).

Supports 1.5x and 2x factors for 12 GB VRAM.
Saves both pre-upscale and post-upscale outputs as intermediates.
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from ..comfy_client import ComfyClient
from ..config import AnimePipelineConfig
from ..schemas import AnimePipelineJob, AnimePipelineStatus
from ..workflow_builder import WorkflowBuilder

logger = logging.getLogger(__name__)

# Supported upscale factors for 12 GB VRAM
_SUPPORTED_FACTORS = (1.5, 2)
_MAX_FACTOR_12GB = 2


class UpscaleService:
    """Enhanced upscale service with Ultimate SD Upscale + fallback.

    Uses WorkflowBuilder for workflow construction and ComfyClient for
    submission/polling — consistent with other pipeline agents.

    Two upscale strategies:
      1. **Ultimate SD Upscale** — tiles the image and runs img2img on
         each tile for detail enhancement.  Requires the custom node.
      2. **Simple upscale** — ImageUpscaleWithModel (4x) + ImageScale
         to target dimensions.  Always available.

    The service tries Ultimate SD Upscale first, then falls back to
    the simple path if the custom node is unavailable or errors out.
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._builder = WorkflowBuilder()
        self._client = ComfyClient(base_url=config.comfyui_url)

    def execute(self, job: AnimePipelineJob) -> AnimePipelineJob:
        """Run upscale on the latest pipeline output."""
        job.status = AnimePipelineStatus.UPSCALING
        t0 = time.time()

        # Check if upscale is requested in layer plan
        if job.layer_plan and not job.layer_plan.upscale_pass:
            logger.info("[UpscaleService] Skipped (not in layer plan)")
            self._set_final_from_latest(job)
            job.mark_stage("upscale", 0.0)
            return job

        # Get latest output (beauty or refine output)
        source_b64 = self._get_latest_output(job)
        if not source_b64:
            logger.warning("[UpscaleService] No source image to upscale")
            job.mark_stage("upscale", 0.0)
            return job

        # Save pre-upscale intermediate
        job.add_intermediate("pre_upscale", source_b64)

        # Resolve upscale factor (clamp for VRAM safety)
        factor = self._resolve_factor()

        # Resolve source dimensions for fallback rescale
        src_width, src_height = self._get_source_dimensions(job)

        # Try Ultimate SD Upscale first, fallback to simple
        upscaled_b64 = self._try_ultimate_sd_upscale(
            source_b64, factor, job.job_id,
        )
        if upscaled_b64 is None:
            logger.info("[UpscaleService] Falling back to simple upscale")
            upscaled_b64 = self._try_simple_upscale(
                source_b64, factor, src_width, src_height, job.job_id,
            )

        if upscaled_b64:
            job.add_intermediate(
                "upscale", upscaled_b64,
                model=self._config.upscale_model,
                factor=factor,
            )
            job.final_image_b64 = upscaled_b64
        else:
            logger.warning("[UpscaleService] Both upscale paths failed, using pre-upscale")
            self._set_final_from_latest(job)

        latency = (time.time() - t0) * 1000
        job.mark_stage("upscale", latency)
        logger.info("[UpscaleService] Done in %.0fms (factor=%.1fx)", latency, factor)
        return job

    # ── Internal helpers ──────────────────────────────────────────

    def _resolve_factor(self) -> float:
        """Clamp upscale factor to supported range."""
        raw = self._config.upscale_factor
        factor = float(raw)
        if factor not in _SUPPORTED_FACTORS:
            # Snap to nearest supported
            factor = min(_SUPPORTED_FACTORS, key=lambda f: abs(f - factor))
            logger.info("[UpscaleService] Snapped factor to %.1fx", factor)
        return min(factor, _MAX_FACTOR_12GB)

    def _get_latest_output(self, job: AnimePipelineJob) -> Optional[str]:
        """Get the most recent renderable output image."""
        preferred = ("beauty_pass", "refine_beauty", "cleanup_pass", "composition_pass")
        for img in reversed(job.intermediates):
            if img.stage in preferred:
                return img.image_b64
        # Fallback: any intermediate with image data
        for img in reversed(job.intermediates):
            if img.image_b64:
                return img.image_b64
        return None

    def _get_source_dimensions(self, job: AnimePipelineJob) -> tuple[int, int]:
        """Resolve source image dimensions from job metadata."""
        # Try to get from layer plan resolution
        if job.layer_plan:
            return job.layer_plan.resolution_width, job.layer_plan.resolution_height
        # Default SDXL portrait
        return self._config.portrait_res

    def _set_final_from_latest(self, job: AnimePipelineJob) -> None:
        """Set final_image_b64 from the best available intermediate."""
        source = self._get_latest_output(job)
        if source:
            job.final_image_b64 = source

    def _try_ultimate_sd_upscale(
        self, source_b64: str, factor: float, job_id: str,
    ) -> Optional[str]:
        """Attempt upscale via Ultimate SD Upscale custom node."""
        cfg = self._config

        # Need a checkpoint for the tiled img2img denoise pass
        checkpoint = cfg.beauty_model.checkpoint or cfg.composition_model.checkpoint
        if not checkpoint:
            logger.warning("[UpscaleService] No checkpoint for Ultimate SD Upscale")
            return None

        positive = cfg.quality_prefix or "masterpiece, best quality"
        negative = cfg.negative_base or "lowres, worst quality"

        try:
            workflow = self._builder.build_ultimate_sd_upscale(
                image_b64=source_b64,
                upscale_model=cfg.upscale_model,
                upscale_by=factor,
                checkpoint=checkpoint,
                positive_prompt=positive,
                negative_prompt=negative,
                seed=42,
                steps=20,
                cfg=5.0,
                denoise=cfg.upscale_denoise,
                tile_width=cfg.upscale_tile_size,
                tile_height=cfg.upscale_tile_size,
            )
            result = self._client.submit_workflow(
                workflow, job_id=job_id, pass_name="upscale_ultimate",
            )
            if result.success and result.images_b64:
                return result.images_b64[0]

            if result.validation_error:
                logger.warning(
                    "[UpscaleService] Ultimate SD Upscale rejected: %s",
                    result.validation_error,
                )
            return None

        except Exception as exc:
            logger.warning("[UpscaleService] Ultimate SD Upscale failed: %s", exc)
            return None

    def _try_simple_upscale(
        self,
        source_b64: str,
        factor: float,
        src_width: int,
        src_height: int,
        job_id: str,
    ) -> Optional[str]:
        """Attempt upscale via simple model upscale + rescale."""
        target_w = int(src_width * factor)
        target_h = int(src_height * factor)

        try:
            workflow = self._builder.build_simple_upscale(
                image_b64=source_b64,
                upscale_model=self._config.upscale_model,
                target_width=target_w,
                target_height=target_h,
            )
            result = self._client.submit_workflow(
                workflow, job_id=job_id, pass_name="upscale_simple",
            )
            if result.success and result.images_b64:
                return result.images_b64[0]
            return None

        except Exception as exc:
            logger.warning("[UpscaleService] Simple upscale failed: %s", exc)
            return None
