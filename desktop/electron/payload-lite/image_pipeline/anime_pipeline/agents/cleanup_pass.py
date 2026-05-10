"""
CleanupPassAgent — Stage between structure lock and beauty pass.

.. admonition:: NOT WIRED (utility module)

   This agent is **not** imported by the live orchestrator
   (``image_pipeline.anime_pipeline.orchestrator``). It remains available
   as a tested utility for opt-in experimentation and may be re-enabled
   in a future iteration. See ``image_pipeline/DEPRECATED.md``.

Fixes composition drift, simplifies noisy regions, stabilizes face
and costume shapes, and produces a cleaner intermediate before the
strongest anime model redraws it.

Behavior:
    - img2img with low-to-medium denoise (preserves pose / composition)
    - Reuses structure-lock control layers (lineart, depth) when available
    - Adjusts denoise and control strength based on optional critique feedback:
        * "composition already good" → lower denoise
        * "major anatomy issue" → raise denoise + strengthen lineart
        * "busy background" → simplify (add background-simplification negative)

Delegates workflow construction to WorkflowBuilder.build_cleanup()
and ComfyUI submission to ComfyClient.submit_workflow().
"""

from __future__ import annotations

import logging
import random
import time
from typing import Optional

from ..comfy_client import ComfyClient
from ..config import AnimePipelineConfig
from ..schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    ControlInput,
    CritiqueReport,
    PassConfig,
    StructureLayer,
)
from ..workflow_builder import WorkflowBuilder

logger = logging.getLogger(__name__)

# ── Cleanup tuning defaults ───────────────────────────────────────

_DEFAULT_DENOISE = 0.45
_LOW_DENOISE = 0.30          # "composition already good"
_HIGH_DENOISE = 0.60         # "major anatomy issue"
_DENOISE_FLOOR = 0.15        # never go below — would be a no-op
_DENOISE_CEILING = 0.75      # never go above — would destroy composition

_LINEART_STRENGTH_BOOST = 0.15  # extra strength on anatomy fix


# ── Critique-aware adjustments ────────────────────────────────────

def compute_cleanup_adjustments(
    critique: Optional[CritiqueReport],
    base_denoise: float = _DEFAULT_DENOISE,
) -> dict:
    """Derive cleanup denoise and control overrides from a critique report.

    Returns a dict with:
        denoise: float  — adjusted denoise for KSampler
        lineart_strength_delta: float — how much to add to lineart strength
        negative_extra: str — extra negative tokens (e.g. background simplify)
        reason: str — human-readable explanation of adjustments
    """
    result: dict = {
        "denoise": base_denoise,
        "lineart_strength_delta": 0.0,
        "negative_extra": "",
        "reason": "default cleanup settings",
    }

    if critique is None:
        return result

    reasons: list[str] = []

    # ── Composition-already-good: lower denoise ──────────────────
    if critique.composition_score >= 8 and critique.anatomy_score >= 7:
        result["denoise"] = max(_DENOISE_FLOOR, base_denoise - 0.15)
        reasons.append("composition good → lower denoise")

    # ── Major anatomy issue: raise denoise + strengthen lineart ──
    has_anatomy_issue = (
        critique.anatomy_score <= 4
        or critique.hands_score <= 3
        or len(critique.anatomy_issues) >= 3
    )
    if has_anatomy_issue:
        result["denoise"] = min(_DENOISE_CEILING, base_denoise + 0.15)
        result["lineart_strength_delta"] = _LINEART_STRENGTH_BOOST
        reasons.append("anatomy issues → higher denoise + lineart boost")

    # ── Busy background: add simplification negative ─────────────
    has_busy_bg = (
        critique.background_score <= 4
        or any("busy" in i.lower() or "cluttered" in i.lower()
               for i in critique.background_issues)
    )
    if has_busy_bg:
        result["negative_extra"] = (
            "cluttered background, busy background, "
            "too many details in background, noisy background"
        )
        reasons.append("busy background → simplification negative")

    # ── Face issues: keep denoise moderate to allow face fix ──────
    if critique.face_score <= 4:
        result["denoise"] = max(result["denoise"], _DEFAULT_DENOISE)
        reasons.append("face issues → maintain moderate denoise")

    result["reason"] = "; ".join(reasons) if reasons else "no critique adjustments needed"

    # Clamp
    result["denoise"] = max(_DENOISE_FLOOR, min(_DENOISE_CEILING, result["denoise"]))

    return result


# ═══════════════════════════════════════════════════════════════════
# CleanupPassAgent
# ═══════════════════════════════════════════════════════════════════

class CleanupPassAgent:
    """Fix drift and simplify before the beauty pass.

    Uses WorkflowBuilder.build_cleanup() for workflow construction
    and ComfyClient for submission + polling.

    The cleanup pass:
      - Runs img2img at low-to-medium denoise
      - Reuses lineart/depth control layers from structure lock
      - Adjusts denoise and ControlNet strength from critique feedback
      - Preserves pose and composition
      - Improves readability of hair, clothing edges, background
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._builder = WorkflowBuilder()
        self._client = ComfyClient(base_url=config.comfyui_url)

    def execute(
        self,
        job: AnimePipelineJob,
        critique: Optional[CritiqueReport] = None,
    ) -> AnimePipelineJob:
        """Run cleanup pass — critique-aware img2img with ControlNet."""
        job.status = AnimePipelineStatus.CLEANUP
        t0 = time.time()

        plan = job.layer_plan
        if not plan or not plan.cleanup_pass:
            job.error = "No layer plan / cleanup pass configured"
            job.status = AnimePipelineStatus.FAILED
            return job

        cleanup_pc = plan.cleanup_pass

        # Get source image (composition or previous intermediate)
        source_b64 = self._get_source_image(job)
        if not source_b64:
            job.error = "No source image for cleanup pass"
            job.status = AnimePipelineStatus.FAILED
            return job

        seed = self._resolve_seed(cleanup_pc.seed)

        # Compute critique-aware adjustments
        adjustments = compute_cleanup_adjustments(
            critique, base_denoise=cleanup_pc.denoise,
        )
        logger.info(
            "[CleanupPass] Adjustments: %s (denoise=%.2f)",
            adjustments["reason"], adjustments["denoise"],
        )

        # Build adjusted PassConfig
        adjusted_pc = self._apply_adjustments(
            cleanup_pc, adjustments, job.structure_layers,
        )

        # Determine clip_skip
        clip_skip = self._config.composition_model.clip_skip

        # Build workflow
        workflow = self._builder.build_cleanup(
            adjusted_pc,
            source_b64,
            seed,
            clip_skip=clip_skip,
        )

        # Submit to ComfyUI
        result = self._client.submit_workflow(
            workflow,
            job_id=job.job_id,
            pass_name="cleanup",
        )

        if not result.success:
            logger.error(
                "[CleanupPass] Failed: %s (validation: %s)",
                result.error, result.validation_error,
            )
            job.error = f"Cleanup pass failed: {result.error}"
            job.status = AnimePipelineStatus.FAILED
            return job

        if not result.images_b64:
            job.error = "Cleanup pass produced no image"
            job.status = AnimePipelineStatus.FAILED
            return job

        image_b64 = result.images_b64[0]
        job.add_intermediate(
            "cleanup_pass", image_b64,
            seed=seed,
            checkpoint=adjusted_pc.checkpoint,
            denoise=adjustments["denoise"],
            duration_ms=result.duration_ms,
        )

        latency = (time.time() - t0) * 1000
        job.mark_stage("cleanup_pass", latency)
        logger.info(
            "[CleanupPass] Done in %.0fms, checkpoint=%s, denoise=%.2f, %d controls",
            latency, adjusted_pc.checkpoint, adjustments["denoise"],
            len(adjusted_pc.control_inputs),
        )
        return job

    # ── Public API ────────────────────────────────────────────────────

    def build_workflow(
        self,
        pc: PassConfig,
        source_image_b64: str,
        seed: int,
        *,
        critique: Optional[CritiqueReport] = None,
        structure_layers: Optional[list[StructureLayer]] = None,
        clip_skip: int = 1,
    ) -> dict:
        """Build cleanup workflow without submitting.

        Useful for testing, debugging, or external submission.
        """
        adjustments = compute_cleanup_adjustments(
            critique, base_denoise=pc.denoise,
        )
        adjusted_pc = self._apply_adjustments(
            pc, adjustments, structure_layers or [],
        )
        return self._builder.build_cleanup(
            adjusted_pc, source_image_b64, seed, clip_skip=clip_skip,
        )

    # ── Internals ─────────────────────────────────────────────────────

    def _apply_adjustments(
        self,
        pc: PassConfig,
        adjustments: dict,
        structure_layers: list[StructureLayer],
    ) -> PassConfig:
        """Build a new PassConfig with critique-adjusted denoise + controls."""
        # Build control inputs from structure layers
        control_inputs: list[ControlInput] = []
        lineart_delta = adjustments.get("lineart_strength_delta", 0.0)

        for layer in structure_layers[:self._config.max_simultaneous_layers]:
            if not layer.controlnet_model or not layer.image_b64:
                continue
            strength = layer.strength
            if "lineart" in layer.layer_type.value and lineart_delta > 0:
                strength = min(1.0, strength + lineart_delta)
            control_inputs.append(ControlInput(
                layer_type=layer.layer_type.value,
                controlnet_model=layer.controlnet_model,
                strength=strength,
                start_percent=layer.start_percent,
                end_percent=layer.end_percent,
                image_b64=layer.image_b64,
            ))

        # Also include any controls already in the PassConfig
        for ci in pc.control_inputs:
            if ci.image_b64 and ci.controlnet_model:
                # Apply lineart boost if applicable
                strength = ci.strength
                if "lineart" in ci.layer_type and lineart_delta > 0:
                    strength = min(1.0, strength + lineart_delta)
                control_inputs.append(ControlInput(
                    layer_type=ci.layer_type,
                    controlnet_model=ci.controlnet_model,
                    strength=strength,
                    start_percent=ci.start_percent,
                    end_percent=ci.end_percent,
                    image_b64=ci.image_b64,
                ))

        # Append background-simplification negative if needed
        negative = pc.negative_prompt
        extra_neg = adjustments.get("negative_extra", "")
        if extra_neg:
            negative = f"{negative}, {extra_neg}" if negative else extra_neg

        return PassConfig(
            pass_name=pc.pass_name,
            model_slot=pc.model_slot,
            checkpoint=pc.checkpoint,
            width=pc.width,
            height=pc.height,
            sampler=pc.sampler,
            scheduler=pc.scheduler,
            steps=pc.steps,
            cfg=pc.cfg,
            denoise=adjustments["denoise"],
            seed=pc.seed,
            positive_prompt=pc.positive_prompt,
            negative_prompt=negative,
            control_inputs=control_inputs,
            prompt_strategy=pc.prompt_strategy,
            expected_output=pc.expected_output,
            source_image_b64=pc.source_image_b64,
            lora_models=pc.lora_models,
        )

    def _get_source_image(self, job: AnimePipelineJob) -> Optional[str]:
        """Get the best source image for cleanup.

        Priority:
          1. Composition pass output (most common path)
          2. User-supplied source image
        """
        for img in reversed(job.intermediates):
            if img.stage == "composition_pass":
                return img.image_b64
        return job.source_image_b64 or None

    def _resolve_seed(self, seed: int) -> int:
        if seed < 0:
            return random.randint(0, 2**32 - 1)
        return seed
