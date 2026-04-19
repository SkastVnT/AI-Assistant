"""
CompositionPassAgent — Stage 3: Generate base composition draft via ComfyUI.

Submits a txt2img (or img2img) workflow to ComfyUI using the composition checkpoint.
The goal is a structurally sound draft — details will be refined in the beauty pass.

Delegates workflow construction to WorkflowBuilder.build_composition() and
ComfyUI submission to ComfyClient.submit_workflow().

Prompt construction rules for pass 1:
    - Prioritize scene layout and pose.
    - Avoid overloading details (leave micro-details for beauty pass).
    - Keep background broad and readable.
    - Keep face quality requirements but do not overfit small accessories yet.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from ..comfy_client import ComfyClient, ComfyJobResult
from ..config import AnimePipelineConfig
from ..schemas import AnimePipelineJob, AnimePipelineStatus, PassConfig
from ..workflow_builder import WorkflowBuilder

logger = logging.getLogger(__name__)

# ── Composition prompt rules ──────────────────────────────────────

# Tags that should be promoted to the front of the positive prompt
# in the composition pass — they affect large shapes.
_COMPOSITION_PRIORITY_TAGS = {
    "pose", "stance", "sitting", "standing", "walking", "running",
    "full body", "full-body", "upper body", "portrait", "close-up",
    "from above", "from below", "from side", "looking at viewer",
    "facing away", "back view", "looking_up", "looking_down",
    "scenery", "outdoors", "indoors", "blue_sky", "flower_field",
    "highland", "meadow", "landscape",
}

# Tags that should be deprioritized or removed in pass 1
# — micro-details that the beauty pass handles better.
_DETAIL_DEFER_TAGS = {
    "intricate details", "detailed fingers", "detailed eyes",
    "detailed hair strands", "detailed jewelry", "detailed lace",
    "filigree", "embroidery", "tiny accessories", "brooch",
    "earring detail", "ring detail", "nail art",
}

# Broad background descriptors kept for composition (readable shapes)
_BACKGROUND_BROAD_TAGS = {
    "outdoors", "indoors", "sky", "blue_sky", "forest", "city", "school",
    "classroom", "park", "beach", "night sky", "sunset", "sunrise",
    "simple background", "gradient background", "scenery",
    "flower_field", "flower", "highland", "mountain", "meadow",
    "ocean", "river", "lake", "field", "garden", "temple", "shrine",
    "rain", "snow", "clouds", "starry_sky", "cherry_blossoms",
    "wind", "sunlight", "moonlight",
}


def refine_composition_prompt(positive: str) -> str:
    """Adjust the positive prompt for pass 1 composition rules.

    Rules:
        1. Promote scene-layout and pose tokens to the front.
        2. Remove micro-detail tags (deferred to beauty pass).
        3. Keep background broad and readable.
        4. Preserve face-quality anchors but not accessory-level detail.

    Returns the adjusted prompt string.
    """
    parts = [p.strip() for p in positive.split(",") if p.strip()]

    priority: list[str] = []
    regular: list[str] = []
    deferred: list[str] = []

    for part in parts:
        lower = part.lower().strip()
        if any(tag in lower for tag in _COMPOSITION_PRIORITY_TAGS):
            priority.append(part)
        elif any(tag in lower for tag in _DETAIL_DEFER_TAGS):
            deferred.append(part)  # dropped for composition
        else:
            regular.append(part)

    # Warn about deferred tags (debug-level)
    if deferred:
        logger.debug(
            "[CompositionPrompt] Deferred %d detail tags for beauty pass: %s",
            len(deferred), deferred,
        )

    return ", ".join(priority + regular)


# ═══════════════════════════════════════════════════════════════════════
# CompositionPassAgent
# ═══════════════════════════════════════════════════════════════════════

class CompositionPassAgent:
    """Generate base composition image via ComfyUI.

    Uses WorkflowBuilder.build_composition() for workflow construction
    and ComfyClient for submission + polling.

    Exposed pass settings (from PassConfig):
        width, height, sampler, scheduler, steps, cfg, seed, denoise
        clip_skip (from config.composition_model)
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._builder = WorkflowBuilder()
        self._client = ComfyClient(
            base_url=config.comfyui_url,
        )

    def execute(self, job: AnimePipelineJob) -> AnimePipelineJob:
        """Run composition pass — txt2img or img2img."""
        job.status = AnimePipelineStatus.COMPOSING
        t0 = time.time()

        plan = job.layer_plan
        if not plan or not plan.composition_pass:
            job.error = "No layer plan / composition pass configured"
            job.status = AnimePipelineStatus.FAILED
            return job

        comp = plan.composition_pass
        seed = self._resolve_seed(comp.seed)

        # Apply composition prompt rules
        refined_comp = self._prepare_pass_config(comp)

        # Determine clip_skip from config
        clip_skip = self._config.composition_model.clip_skip

        # Build workflow via WorkflowBuilder
        workflow = self._builder.build_composition(
            refined_comp,
            seed,
            source_image_b64=job.source_image_b64 or "",
            clip_skip=clip_skip,
        )

        # Submit to ComfyUI via ComfyClient
        result = self._client.submit_workflow(
            workflow,
            job_id=job.job_id,
            pass_name="composition",
        )

        if not result.success:
            logger.error(
                "[CompositionPass] Failed: %s (validation: %s)",
                result.error, result.validation_error,
            )
            job.error = f"Composition pass failed: {result.error}"
            job.status = AnimePipelineStatus.FAILED
            return job

        if not result.images_b64:
            job.error = "Composition pass produced no image"
            job.status = AnimePipelineStatus.FAILED
            return job

        image_b64 = result.images_b64[0]
        job.add_intermediate(
            "composition_pass", image_b64,
            seed=seed,
            checkpoint=comp.checkpoint,
            duration_ms=result.duration_ms,
        )

        latency = (time.time() - t0) * 1000
        job.mark_stage("composition_pass", latency)
        logger.info(
            "[CompositionPass] Done in %.0fms, checkpoint=%s, %dx%d, seed=%d",
            latency, comp.checkpoint, comp.width, comp.height, seed,
        )
        return job

    # ── Internals ─────────────────────────────────────────────────────

    def _prepare_pass_config(self, comp: PassConfig) -> PassConfig:
        """Return a PassConfig with composition-refined prompts.

        Applies prompt construction rules:
        - Promotes pose/scene layout tokens
        - Removes micro-detail tokens (deferred to beauty)
        - Preserves face quality anchors
        """
        return PassConfig(
            pass_name=comp.pass_name,
            model_slot=comp.model_slot,
            checkpoint=comp.checkpoint,
            width=comp.width,
            height=comp.height,
            sampler=comp.sampler,
            scheduler=comp.scheduler,
            steps=comp.steps,
            cfg=comp.cfg,
            denoise=comp.denoise,
            seed=comp.seed,
            positive_prompt=refine_composition_prompt(comp.positive_prompt),
            negative_prompt=comp.negative_prompt,
            control_inputs=comp.control_inputs,
            prompt_strategy=comp.prompt_strategy,
            expected_output=comp.expected_output,
            source_image_b64=comp.source_image_b64,
            lora_models=comp.lora_models,
        )

    @staticmethod
    def _resolve_seed(seed: int) -> int:
        """Resolve seed: -1 means random."""
        if seed < 0:
            return int.from_bytes(os.urandom(4), "big") % (2**32)
        return seed

    def build_workflow(
        self,
        comp: PassConfig,
        seed: int,
        *,
        source_image_b64: str = "",
        clip_skip: int = 1,
    ) -> dict:
        """Build composition workflow JSON without submitting.

        Useful for debugging, testing, and external orchestration.
        Applies composition prompt rules before building.
        """
        refined = self._prepare_pass_config(comp)
        return self._builder.build_composition(
            refined, seed,
            source_image_b64=source_image_b64,
            clip_skip=clip_skip,
        )
