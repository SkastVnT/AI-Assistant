"""
BeautyPassAgent — Final redraw with the strongest anime checkpoint.

Uses WorkflowBuilder.build_beauty() for workflow construction and
ComfyClient for submission + polling.  The beauty pass:

- Runs img2img from the cleanup output at low denoise
- Uses the dedicated ``final_model`` config slot (falls back to beauty_model)
- Supports beauty_strength presets: subtle / balanced / aggressive
- Reuses structure controls at reduced strength to preserve identity
- Emphasizes quality, face, eyes, hair, costume details, clean linework
- Preserves planned palette and camera
- Supports seed lock, retry seed, and alternate retry seed

The model slot is swappable via config or env var without changing
orchestration logic.
"""

from __future__ import annotations

import logging
import random
import time
from typing import Optional

from ..comfy_client import ComfyClient
from ..config import (
    AnimePipelineConfig,
    BeautyStrength,
    get_beauty_preset,
)
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

# ── Beauty prompt construction ────────────────────────────────────

_BEAUTY_QUALITY_TAGS = (
    "masterpiece, best quality, very aesthetic, absurdres, "
    "detailed eyes, beautiful detailed face, detailed hair, "
    "vibrant colors, refined anime shading, controlled highlights"
)

_BEAUTY_IDENTITY_NEGATIVE = (
    "blurry face, asymmetrical eyes, bad hands, extra fingers, "
    "deformed iris, mutation, worst quality, lowres, "
    "bad anatomy, disfigured, ugly, "
    "monochrome, greyscale, grayscale, sketch, lineart, black_and_white"
)

_EYE_REFINEMENT_TAGS = (
    "ultra detailed eyes, intricate iris texture, clear limbal ring, "
    "balanced eye symmetry, sharp eyelash strands, vivid catchlight"
)

_EYE_REFINEMENT_NEGATIVE = (
    "lazy eye, cross-eye, uneven pupils, mismatched irises, "
    "blurry iris, malformed eyelids"
)

_EYE_LORA_HINTS = (
    "eye", "eyes", "iris", "pupil", "huespark", "anime_artistic",
)

# Default factor to reduce structure-lock strengths for beauty pass
_CONTROL_STRENGTH_FACTOR = 0.70


def refine_beauty_prompt(positive: str) -> str:
    """Enhance a positive prompt for the beauty pass.

    Prepends quality/detail tags that are critical for the final redraw
    stage without duplicating tags already present.
    """
    existing_lower = positive.lower()
    additions: list[str] = []
    for tag in _BEAUTY_QUALITY_TAGS.split(", "):
        if tag.lower() not in existing_lower:
            additions.append(tag)
    if additions:
        return ", ".join(additions) + ", " + positive
    return positive


_BEAUTY_NO_TEXT_NEGATIVE = (
    "text, watermark, signature, username, artist_name, logo, copyright, "
    "credit, stamp, title_text, author_name, english_text, twitter_username, "
    "instagram_username, url, website"
)


def build_beauty_negative(base_negative: str, allow_text: bool = False) -> str:
    """Ensure identity-protection and text-blocking negatives are present."""
    existing_lower = base_negative.lower()
    additions: list[str] = []
    for tag in _BEAUTY_IDENTITY_NEGATIVE.split(", "):
        if tag.lower() not in existing_lower:
            additions.append(tag)
    # Always block text/credits unless user explicitly requested them
    if not allow_text:
        for tag in _BEAUTY_NO_TEXT_NEGATIVE.split(", "):
            if tag.strip().lower() not in existing_lower:
                additions.append(tag.strip())
    if additions:
        return base_negative + ", " + ", ".join(additions)
    return base_negative


# ═══════════════════════════════════════════════════════════════════
# BeautyPassAgent
# ═══════════════════════════════════════════════════════════════════

class BeautyPassAgent:
    """Final beauty redraw using the strongest anime checkpoint.

    Uses WorkflowBuilder.build_beauty() for workflow construction
    and ComfyClient for submission + polling.

    The beauty pass:
      - Runs img2img from cleanup output at low denoise
      - Uses ``final_model`` config slot (falls back to beauty_model)
      - Supports beauty_strength presets (subtle/balanced/aggressive)
      - Reuses structure controls at reduced strength
      - Emphasizes face quality, hair rendering, material shading
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._builder = WorkflowBuilder()
        self._client = ComfyClient(base_url=config.comfyui_url)
        self._pending_critique: Optional[CritiqueReport] = None

    def set_refine_context(self, critique: Optional[CritiqueReport]) -> None:
        """Provide latest critique so the next beauty pass can target eye fixes."""
        self._pending_critique = critique

    def should_apply_eye_refine(self, critique: Optional[CritiqueReport]) -> bool:
        """Return True when critique indicates eye-detail refinement is needed."""
        if not critique:
            return False
        if not self._config.eye_refine_enabled:
            return False
        threshold = self._config.eye_refine_trigger_score
        eye_score_flag = (
            critique.eye_consistency_score > 0
            and critique.eye_consistency_score <= threshold
        )
        face_score_flag = (
            critique.face_score > 0
            and critique.face_score <= max(1, threshold - 1)
        )
        return (
            eye_score_flag
            or bool(critique.eye_issues)
            or face_score_flag
        )

    def execute(
        self,
        job: AnimePipelineJob,
        *,
        strength: BeautyStrength | str | None = None,
        retry_seed: int | None = None,
    ) -> AnimePipelineJob:
        """Run beauty pass — final redraw with strongest checkpoint.

        Args:
            job: Pipeline job with cleanup output in intermediates.
            strength: Override beauty strength preset (subtle/balanced/aggressive).
            retry_seed: Explicit seed for retry attempts (overrides plan seed).
        """
        job.status = AnimePipelineStatus.BEAUTY_RENDERING
        t0 = time.time()

        plan = job.layer_plan
        if not plan or not plan.beauty_pass:
            job.error = "No layer plan / beauty pass configured"
            job.status = AnimePipelineStatus.FAILED
            return job

        beauty_pc = plan.beauty_pass

        # Source image: cleanup > composition > user source
        source_b64 = self._get_source_image(job)
        if not source_b64:
            job.error = "No source image for beauty pass"
            job.status = AnimePipelineStatus.FAILED
            return job

        # Resolve seed
        seed = retry_seed if retry_seed is not None else self._resolve_seed(beauty_pc.seed)

        critique = self._pending_critique
        self._pending_critique = None

        # Apply strength preset + final_model
        resolved_strength = strength or self._config.beauty_strength
        from ..agents.layer_planner import _user_requests_text  # local import to avoid cycle
        allow_text = _user_requests_text(job.user_prompt)
        adjusted_pc = self._prepare_pass_config(
            beauty_pc, resolved_strength, job.structure_layers,
            critique=critique, allow_text=allow_text,
        )

        eye_refine_steps = self._choose_eye_refine_steps(critique)

        # Determine clip_skip from final model
        clip_skip = self._config.final_model.clip_skip

        # Build workflow
        workflow = self._builder.build_beauty(
            adjusted_pc,
            source_b64,
            seed,
            clip_skip=clip_skip,
            eye_refine_steps=eye_refine_steps,
        )

        # Submit to ComfyUI
        result = self._client.submit_workflow(
            workflow,
            job_id=job.job_id,
            pass_name="beauty",
        )

        if not result.success:
            logger.error(
                "[BeautyPass] Failed: %s (validation: %s)",
                result.error, result.validation_error,
            )
            job.error = f"Beauty pass failed: {result.error}"
            job.status = AnimePipelineStatus.FAILED
            return job

        if not result.images_b64:
            job.error = "Beauty pass produced no image"
            job.status = AnimePipelineStatus.FAILED
            return job

        image_b64 = result.images_b64[0]
        job.add_intermediate(
            "beauty_pass", image_b64,
            seed=seed,
            checkpoint=adjusted_pc.checkpoint,
            denoise=adjusted_pc.denoise,
            strength_preset=str(resolved_strength),
            duration_ms=result.duration_ms,
        )

        latency = (time.time() - t0) * 1000
        job.mark_stage("beauty_pass", latency)
        logger.info(
            "[BeautyPass] Done in %.0fms, checkpoint=%s, denoise=%.2f, "
            "strength=%s, eye_refine_steps=%d, %d controls",
            latency, adjusted_pc.checkpoint, adjusted_pc.denoise,
            resolved_strength, eye_refine_steps, len(adjusted_pc.control_inputs),
        )
        return job

    # ── Public API ────────────────────────────────────────────────────

    def build_workflow(
        self,
        pc: PassConfig,
        source_image_b64: str,
        seed: int,
        *,
        strength: BeautyStrength | str | None = None,
        structure_layers: list[StructureLayer] | None = None,
        clip_skip: int = 1,
        critique: Optional[CritiqueReport] = None,
    ) -> dict:
        """Build beauty workflow without submitting.

        Useful for testing, debugging, or external submission.
        """
        resolved_strength = strength or self._config.beauty_strength
        adjusted_pc = self._prepare_pass_config(
            pc, resolved_strength, structure_layers or [], critique=critique,
        )
        eye_refine_steps = self._choose_eye_refine_steps(critique)
        return self._builder.build_beauty(
            adjusted_pc,
            source_image_b64,
            seed,
            clip_skip=clip_skip,
            eye_refine_steps=eye_refine_steps,
        )

    # ── Internals ─────────────────────────────────────────────────────

    def _prepare_pass_config(
        self,
        pc: PassConfig,
        strength: BeautyStrength | str,
        structure_layers: list[StructureLayer],
        critique: Optional[CritiqueReport] = None,
        allow_text: bool = False,
    ) -> PassConfig:
        """Build a PassConfig with final_model, preset overrides, and reduced controls."""
        preset = get_beauty_preset(strength)
        fm = self._config.final_model

        # Build reduced-strength control inputs from structure layers
        control_inputs = self._build_controls(structure_layers, pc.control_inputs)

        # Enhance prompts for beauty
        positive = refine_beauty_prompt(pc.positive_prompt)
        negative = build_beauty_negative(pc.negative_prompt, allow_text=allow_text)

        if self.should_apply_eye_refine(critique):
            positive = self._augment_eye_prompt(positive, critique)
            negative = self._augment_eye_negative(negative)
            lora_models = self._prioritize_eye_loras(pc.lora_models)
        else:
            lora_models = pc.lora_models

        return PassConfig(
            pass_name=pc.pass_name or "beauty",
            model_slot="final",
            checkpoint=fm.checkpoint,
            width=pc.width,
            height=pc.height,
            sampler=fm.sampler,
            scheduler=fm.scheduler,
            steps=preset["steps"],
            cfg=preset["cfg"],
            denoise=preset["denoise"],
            seed=pc.seed,
            positive_prompt=positive,
            negative_prompt=negative,
            control_inputs=control_inputs,
            prompt_strategy="detail",
            expected_output=pc.expected_output,
            source_image_b64=pc.source_image_b64,
            lora_models=lora_models,
        )

    def _choose_eye_refine_steps(self, critique: Optional[CritiqueReport]) -> int:
        """Map critique severity to 0-3 latent micro-steps for eye refinement."""
        if not self.should_apply_eye_refine(critique):
            return 0
        max_steps = max(1, min(int(self._config.eye_refine_max_steps), 3))
        if not critique:
            return max_steps

        issue_count = len(critique.eye_issues)
        score = critique.eye_consistency_score
        if score <= 4 or issue_count >= 3:
            return max_steps
        if score <= 6 or issue_count >= 2:
            return min(2, max_steps)
        return min(1, max_steps)

    def _augment_eye_prompt(
        self,
        positive: str,
        critique: Optional[CritiqueReport],
    ) -> str:
        existing = positive.lower()
        additions: list[str] = []

        for tag in _EYE_REFINEMENT_TAGS.split(", "):
            if tag.lower() not in existing:
                additions.append(tag)

        if critique and critique.eye_issues:
            for issue in critique.eye_issues[:3]:
                issue_tag = f"fix {issue}"
                if issue_tag.lower() not in existing:
                    additions.append(issue_tag)

        if additions:
            return ", ".join(additions) + ", " + positive
        return positive

    def _augment_eye_negative(self, negative: str) -> str:
        existing = negative.lower()
        additions: list[str] = []
        for tag in _EYE_REFINEMENT_NEGATIVE.split(", "):
            if tag.lower() not in existing:
                additions.append(tag)
        if additions:
            return negative + ", " + ", ".join(additions)
        return negative

    def _prioritize_eye_loras(
        self,
        lora_models: list[dict[str, object]],
    ) -> list[dict[str, object]]:
        """Select and boost eye-relevant LoRAs from user stack for refine pass."""
        selected: list[dict[str, object]] = []
        for lora in lora_models or []:
            if not isinstance(lora, dict):
                continue
            name = str(
                lora.get("name")
                or lora.get("model")
                or lora.get("filename")
                or ""
            )
            lower_name = name.lower()
            if not any(hint in lower_name for hint in _EYE_LORA_HINTS):
                continue

            boosted = dict(lora)
            base_strength = float(boosted.get("strength", 0.6))
            boosted["strength"] = min(1.0, max(base_strength, base_strength + 0.12))
            selected.append(boosted)

        if selected:
            return selected[:2]

        # Fallback: keep first user LoRA with a slight boost if no eye-specific match found.
        if lora_models:
            fallback = dict(lora_models[0])
            base_strength = float(fallback.get("strength", 0.6))
            fallback["strength"] = min(1.0, max(base_strength, base_strength + 0.08))
            return [fallback]
        return []

    def _build_controls(
        self,
        structure_layers: list[StructureLayer],
        existing_controls: list[ControlInput],
    ) -> list[ControlInput]:
        """Convert structure layers to reduced-strength ControlNet inputs.

        Beauty pass uses weaker control than earlier passes to allow
        the final model more freedom to add detail.
        """
        controls: list[ControlInput] = []
        factor = _CONTROL_STRENGTH_FACTOR

        for layer in structure_layers[:self._config.max_simultaneous_layers]:
            if not layer.controlnet_model or not layer.image_b64:
                continue
            controls.append(ControlInput(
                layer_type=layer.layer_type.value,
                controlnet_model=layer.controlnet_model,
                strength=layer.strength * factor,
                start_percent=layer.start_percent,
                end_percent=layer.end_percent,
                image_b64=layer.image_b64,
            ))

        # Also include any controls already in the PassConfig
        for ci in existing_controls:
            if ci.image_b64 and ci.controlnet_model:
                controls.append(ControlInput(
                    layer_type=ci.layer_type,
                    controlnet_model=ci.controlnet_model,
                    strength=ci.strength * factor,
                    start_percent=ci.start_percent,
                    end_percent=ci.end_percent,
                    image_b64=ci.image_b64,
                ))

        return controls

    def _get_source_image(self, job: AnimePipelineJob) -> Optional[str]:
        """Get the best source image for beauty pass.

        Priority:
          1. Cleanup pass output
          2. Composition pass output
          3. User-supplied source image
        """
        for img in reversed(job.intermediates):
            if img.stage == "cleanup_pass":
                return img.image_b64
        for img in reversed(job.intermediates):
            if img.stage == "composition_pass":
                return img.image_b64
        return job.source_image_b64 or None

    def _resolve_seed(self, seed: int) -> int:
        if seed < 0:
            return random.randint(0, 2**32 - 1)
        return seed
