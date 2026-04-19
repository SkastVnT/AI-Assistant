"""
LayerPlannerAgent — Stage 2: Create structured LayerPlan from vision analysis + prompt.

Determines resolution, prompt engineering, pass configuration, and structure layers.
All decisions are deterministic (no API calls) based on vision analysis + config.
Produces a LayerPlan with subject_list, camera, pose, palette, style_tags,
background_plan, negative_constraints, and an ordered passes[] list.

Public entry point:
    make_layer_plan(user_prompt, references, preset, vram_profile) -> LayerPlan

Each pass defines:
    - exact objective (expected_output)
    - which model slot to use
    - whether img2img is used (denoise < 1.0 + source_image)
    - control layers required
    - denoise range
    - prompt emphasis (prompt_strategy)
    - expected improvements
"""

from __future__ import annotations

import logging
import time
from typing import Optional

from ..config import AnimePipelineConfig, load_config
from ..planner_presets import (
    PlannerPreset,
    PassOverride,
    get_preset,
)
from ..schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    ControlInput,
    CritiqueReport,
    LayerPlan,
    PassConfig,
    VisionAnalysis,
)

logger = logging.getLogger(__name__)

# ── Orientation detection keywords ─────────────────────────────────

_PORTRAIT_HINTS = {
    "portrait", "vertical", "dọc", "phone", "9:16", "full body", "full-body",
    "standing", "đứng", "toàn thân",
}

# Text overlay request keywords — when detected, text-blocking negative tags are removed
_TEXT_REQUEST_KEYWORDS = {
    "add text", "thêm chữ", "thêm text", "có chữ", "write text",
    "put text", "text overlay", "với chữ", "tiêu đề", "tên nhân vật",
    "caption", "label", "title on", "add caption", "add label",
    "ghi chữ", "viết chữ",
}

# Tags blocked when no text overlay is requested
_NO_TEXT_NEGATIVE = (
    "text, watermark, signature, username, artist_name, logo, copyright, "
    "credit, stamp, title_text, author_name, english_text, twitter_username, "
    "instagram_username, url, website"
)


def _user_requests_text(user_prompt: str) -> bool:
    """Return True if the user explicitly wants text in the generated image."""
    lower = user_prompt.lower()
    return any(kw in lower for kw in _TEXT_REQUEST_KEYWORDS)
_LANDSCAPE_HINTS = {
    "landscape", "horizontal", "ngang", "banner", "16:9", "panorama",
    "wide", "scenery", "phong cảnh",
}
_SQUARE_HINTS = {
    "square", "vuông", "1:1", "avatar", "icon", "pfp", "profile",
}

# ── VRAM profiles ──────────────────────────────────────────────────

_VRAM_PROFILES: dict[str, dict] = {
    "12gb": {
        "max_dim": 1216,
        "step_cap": 35,
        "description": "12 GB VRAM — SDXL-class, 832×1216 default",
    },
    "8gb": {
        "max_dim": 1024,
        "step_cap": 25,
        "description": "8 GB VRAM — smaller resolution, fewer steps",
    },
    "16gb": {
        "max_dim": 1344,
        "step_cap": 40,
        "description": "16 GB VRAM — can push resolution slightly",
    },
    "24gb": {
        "max_dim": 1536,
        "step_cap": 50,
        "description": "24 GB VRAM — generous headroom",
    },
}


def _get_vram_profile(name: str) -> dict:
    return _VRAM_PROFILES.get(name, _VRAM_PROFILES["12gb"])


# ═══════════════════════════════════════════════════════════════════════
# make_layer_plan — standalone entry point
# ═══════════════════════════════════════════════════════════════════════

def make_layer_plan(
    user_prompt: str,
    references: Optional[VisionAnalysis] = None,
    preset: str = "anime_quality",
    vram_profile: str = "12gb",
    config: Optional[AnimePipelineConfig] = None,
    critique: Optional[CritiqueReport] = None,
    source_image_b64: str = "",
    quality_hint: str = "quality",
    style_hint: str = "anime",
    orientation_hint: str = "",
) -> LayerPlan:
    """Build a LayerPlan without needing a full AnimePipelineJob.

    Args:
        user_prompt: The user's text prompt.
        references: VisionAnalysis from reference image(s), if available.
        preset: One of anime_quality, anime_speed, anime_reference_strict,
                anime_background_heavy.
        vram_profile: VRAM tier — "8gb", "12gb", "16gb", "24gb".
        config: AnimePipelineConfig; loaded from YAML if not provided.
        critique: Optional previous CritiqueReport to incorporate fixes.
        source_image_b64: If provided, composition pass uses img2img.
        quality_hint: "quality" or "fast".
        style_hint: Style tag to prepend.
        orientation_hint: "portrait", "landscape", "square", or "" (auto).

    Returns:
        A fully populated LayerPlan with ordered passes.
    """
    cfg = config or load_config()
    planner = LayerPlannerAgent(cfg)

    # Build a minimal job to reuse the agent
    job = AnimePipelineJob(
        user_prompt=user_prompt,
        vision_analysis=references,
        source_image_b64=source_image_b64 or None,
        quality_hint=quality_hint,
        style_hint=style_hint,
        orientation_hint=orientation_hint,
        preset=preset,
    )

    return planner.build_plan(
        job=job,
        preset_name=preset,
        vram_profile=vram_profile,
        critique=critique,
    )


# ═══════════════════════════════════════════════════════════════════════
# LayerPlannerAgent
# ═══════════════════════════════════════════════════════════════════════

class LayerPlannerAgent:
    """Creates a structured LayerPlan from vision analysis and user prompt.

    The plan is a deterministic JSON object — not chain-of-thought prose.
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config

    # ── Agent interface (used by orchestrator) ────────────────────────

    def execute(self, job: AnimePipelineJob) -> AnimePipelineJob:
        """Build a LayerPlan for the pipeline job (orchestrator entry)."""
        job.status = AnimePipelineStatus.PLANNING
        t0 = time.time()

        critique = job.critique_results[-1] if job.critique_results else None
        plan = self.build_plan(
            job=job,
            preset_name=job.preset,
            vram_profile="12gb",
            critique=critique,
        )

        job.layer_plan = plan
        latency = (time.time() - t0) * 1000
        job.mark_stage("layer_planning", latency)

        logger.info(
            "[LayerPlanner] Plan: %dx%d, %d passes, subjects=%s",
            plan.resolution_width, plan.resolution_height,
            len(plan.passes), plan.subject_list,
        )
        return job

    # ── Core plan builder ─────────────────────────────────────────────

    def build_plan(
        self,
        job: AnimePipelineJob,
        preset_name: str = "anime_quality",
        vram_profile: str = "12gb",
        critique: Optional[CritiqueReport] = None,
    ) -> LayerPlan:
        """Build a LayerPlan from a job, preset, and optional critique."""
        va = job.vision_analysis
        preset = get_preset(preset_name)
        vram = _get_vram_profile(vram_profile)

        plan = LayerPlan()

        # ── Scene metadata ────────────────────────────────────────
        plan.scene_summary = (
            va.caption_short if va and va.caption_short
            else job.user_prompt[:200]
        )
        plan.subject_list = (
            va.subjects if va and va.subjects
            else [job.user_prompt.split(",")[0].strip()]
        )
        plan.camera = (
            va.framing if va and va.framing
            else self._guess_camera(job.user_prompt)
        )
        plan.pose = va.pose if va and va.pose else ""
        plan.palette = va.dominant_colors if va and va.dominant_colors else []
        plan.lighting = self._detect_lighting(job.user_prompt)
        plan.style_tags = self._build_style_tags(job, va)
        plan.background_plan = (
            ", ".join(va.background_elements) if va and va.background_elements else ""
        )
        plan.negative_constraints = self._build_negative_constraints(job, va)

        # ── Orientation and resolution ────────────────────────────
        orientation = self._detect_orientation(job)
        w, h = self._get_resolution(orientation)
        w, h = self._clamp_resolution(w, h, vram, preset)

        # ── Prompts ───────────────────────────────────────────────
        quality_prefix = preset.quality_prefix or self._config.quality_prefix
        positive = self._build_positive_prompt(job, plan, quality_prefix)
        negative = self._build_negative_prompt(plan, preset, job)

        # ── Apply critique corrections if available ───────────────
        if critique:
            positive, negative = self._apply_critique(
                positive, negative, critique,
            )

        # ── Reference identity emphasis ───────────────────────────
        if va and va.identity_anchors and preset.identity_emphasis > 1.0:
            anchor_parts = []
            for anchor in va.identity_anchors[:5]:
                anchor_parts.append(f"(({anchor}:{preset.identity_emphasis:.1f}))")
            positive = ", ".join(anchor_parts) + ", " + positive

        # ── Structure layers ──────────────────────────────────────
        structure_types = self._select_structure_layers()
        control_inputs = self._build_control_inputs(
            structure_types, preset,
        )

        # ── Pass 1: composition ───────────────────────────────────
        comp_cfg = self._config.composition_model
        has_source = bool(job.source_image_b64)
        comp_override = preset.pass_overrides.get("composition", PassOverride())

        comp_denoise: float
        if comp_override.denoise is not None:
            comp_denoise = comp_override.denoise
        else:
            comp_denoise = 1.0
        # img2img: cap denoise to avoid destroying source composition
        if has_source and comp_denoise >= 1.0:
            comp_denoise = 0.75

        composition_pass = PassConfig(
            pass_name="composition",
            model_slot="base",
            checkpoint=comp_cfg.checkpoint,
            width=w, height=h,
            sampler=comp_override.sampler or comp_cfg.sampler,
            scheduler=comp_override.scheduler or comp_cfg.scheduler,
            steps=self._cap_steps(
                comp_override.steps or comp_cfg.steps, vram, preset,
            ),
            cfg=comp_override.cfg if comp_override.cfg is not None else comp_cfg.cfg,
            denoise=comp_denoise,
            positive_prompt=self._apply_pass_prompt(positive, comp_override),
            negative_prompt=negative,
            prompt_strategy="broad",
            expected_output=(
                "Structurally sound draft with correct pose and composition"
            ),
            lora_models=self._config.default_loras,
        )
        plan.passes.append(composition_pass)

        # ── Pass 2: structure_lock ────────────────────────────────
        structure_pass = PassConfig(
            pass_name="structure_lock",
            model_slot="preprocessor",
            checkpoint="",
            width=w, height=h,
            steps=0, cfg=0, denoise=0,
            expected_output=(
                "Lineart + depth hint layers extracted from composition"
            ),
        )
        plan.passes.append(structure_pass)

        # ── Pass 3: cleanup (skippable) ───────────────────────────
        if not preset.skip_cleanup:
            cleanup_cfg = self._config.composition_model
            cleanup_override = preset.pass_overrides.get(
                "cleanup", PassOverride(),
            )
            cleanup_pass = PassConfig(
                pass_name="cleanup",
                model_slot="cleanup",
                checkpoint=cleanup_cfg.checkpoint,
                width=w, height=h,
                sampler=(
                    cleanup_override.sampler or cleanup_cfg.sampler
                ),
                scheduler=(
                    cleanup_override.scheduler or cleanup_cfg.scheduler
                ),
                steps=self._cap_steps(
                    cleanup_override.steps
                    or max(20, cleanup_cfg.steps - 4),
                    vram, preset,
                ),
                cfg=(
                    cleanup_override.cfg
                    if cleanup_override.cfg is not None
                    else cleanup_cfg.cfg + 0.5
                ),
                denoise=(
                    cleanup_override.denoise
                    if cleanup_override.denoise is not None
                    else 0.35
                ),
                positive_prompt=self._apply_pass_prompt(
                    positive, cleanup_override,
                ),
                negative_prompt=negative,
                control_inputs=control_inputs,
                prompt_strategy="correction",
                expected_output=(
                    "Cleaned silhouette, simplified background, "
                    "stable face block-in"
                ),
                lora_models=self._config.default_loras,
            )
            plan.passes.append(cleanup_pass)

        # ── Pass 4: beauty ────────────────────────────────────────
        beauty_cfg = self._config.beauty_model
        beauty_override = preset.pass_overrides.get(
            "beauty", PassOverride(),
        )
        beauty_pass = PassConfig(
            pass_name="beauty",
            model_slot="final",
            checkpoint=beauty_cfg.checkpoint,
            width=w, height=h,
            sampler=beauty_override.sampler or beauty_cfg.sampler,
            scheduler=beauty_override.scheduler or beauty_cfg.scheduler,
            steps=self._cap_steps(
                beauty_override.steps or beauty_cfg.steps, vram, preset,
            ),
            cfg=(
                beauty_override.cfg
                if beauty_override.cfg is not None
                else beauty_cfg.cfg
            ),
            denoise=(
                beauty_override.denoise
                if beauty_override.denoise is not None
                else beauty_cfg.denoise_strength
            ),
            positive_prompt=self._apply_pass_prompt(
                positive, beauty_override,
            ),
            negative_prompt=negative,
            control_inputs=control_inputs,
            prompt_strategy="detail",
            expected_output=(
                "Final anime polish: eyes, hair, costume shading, "
                "clean linework"
            ),
            lora_models=self._config.default_loras,
        )
        plan.passes.append(beauty_pass)

        # ── Pass 5: upscale ───────────────────────────────────────
        if not preset.skip_upscale and job.quality_hint != "fast":
            upscale_pass = PassConfig(
                pass_name="upscale",
                model_slot="upscaler",
                checkpoint=self._config.upscale_model,
                width=w * self._config.upscale_factor,
                height=h * self._config.upscale_factor,
                steps=0, cfg=0, denoise=0,
                expected_output=(
                    f"{self._config.upscale_factor}x upscaled final image"
                ),
            )
            plan.passes.append(upscale_pass)

        # ── Validation ────────────────────────────────────────────
        errors = plan.validate()
        if errors:
            logger.warning("[LayerPlanner] Plan validation issues: %s", errors)

        return plan

    # ── Orientation ───────────────────────────────────────────────────

    def _detect_orientation(self, job: AnimePipelineJob) -> str:
        if job.orientation_hint:
            return job.orientation_hint
        text = job.user_prompt.lower()
        for hint in _PORTRAIT_HINTS:
            if hint in text:
                return "portrait"
        for hint in _LANDSCAPE_HINTS:
            if hint in text:
                return "landscape"
        for hint in _SQUARE_HINTS:
            if hint in text:
                return "square"
        return "portrait"

    def _get_resolution(self, orientation: str) -> tuple[int, int]:
        if orientation == "landscape":
            return self._config.landscape_res
        elif orientation == "square":
            return self._config.square_res
        return self._config.portrait_res

    @staticmethod
    def _clamp_resolution(
        w: int, h: int, vram: dict, preset: PlannerPreset,
    ) -> tuple[int, int]:
        """Clamp resolution to VRAM and preset caps."""
        cap = preset.vram_resolution_cap or vram.get("max_dim", 1216)
        if w > cap:
            scale = cap / w
            w = cap
            h = int(h * scale)
        if h > cap:
            scale = cap / h
            h = cap
            w = int(w * scale)
        # Round to nearest 8 for SDXL
        w = max(64, (w // 8) * 8)
        h = max(64, (h // 8) * 8)
        return w, h

    @staticmethod
    def _cap_steps(steps: int, vram: dict, preset: PlannerPreset) -> int:
        """Clamp step count to VRAM and preset caps."""
        cap = preset.vram_step_cap or vram.get("step_cap", 35)
        return min(steps, cap)

    # ── Camera / lighting helpers ─────────────────────────────────────

    @staticmethod
    def _guess_camera(prompt: str) -> str:
        lower = prompt.lower()
        if any(k in lower for k in ("close up", "close-up", "face", "headshot")):
            return "close_up"
        if any(k in lower for k in ("full body", "full-body", "standing", "toàn thân")):
            return "full_body"
        if any(k in lower for k in ("wide", "panorama", "landscape")):
            return "wide"
        return "medium_shot"

    @staticmethod
    def _detect_lighting(prompt: str) -> str:
        lower = prompt.lower()
        if any(k in lower for k in ("dramatic", "rim light", "contrast")):
            return "dramatic"
        if any(k in lower for k in ("sunset", "golden", "warm")):
            return "golden_hour"
        if any(k in lower for k in ("night", "neon", "dark")):
            return "night"
        if any(k in lower for k in ("studio", "flat")):
            return "studio"
        return "soft"

    # ── Prompt construction ───────────────────────────────────────────

    def _build_positive_prompt(
        self,
        job: AnimePipelineJob,
        plan: LayerPlan,
        quality_prefix: str,
    ) -> str:
        parts = [quality_prefix]
        va = job.vision_analysis

        # If VA provided translated/analysed tags (confidence > 0.5 and tags exist),
        # use them instead of the raw user_prompt. This is critical for non-ASCII
        # prompts (Vietnamese, Japanese, etc.) that SD models cannot understand.
        if va and va.confidence > 0.5 and va.anime_tags:
            # Use ALL anime_tags — they include both identity and scene tags.
            parts.extend(va.anime_tags)
        else:
            # English prompt or no translation available — append raw text directly
            parts.append(job.user_prompt)

        # ── Inject eye color from vision layer_analysis ───────────
        # The VA detects exact eye colors but doesn't put them in anime_tags.
        # Inject here as weighted tags so SD generates the correct eye color.
        if va and va.layer_analysis:
            eye_data = va.layer_analysis.get("eyes", {})
            if isinstance(eye_data, dict):
                eye_color = eye_data.get("color", "") or eye_data.get("colour", "")
                eye_special = eye_data.get("special", "")
                existing_lower = " ".join(parts).lower()
                if eye_color and str(eye_color).lower() not in existing_lower:
                    # Format as weighted danbooru tag for emphasis
                    color_tag = str(eye_color).lower().strip().replace(" ", "_")
                    parts.append(f"({color_tag}_eyes:1.2)")
                # Heterochromia — inject both eyes
                if eye_special and "heterochromia" in str(eye_special).lower():
                    if "heterochromia" not in existing_lower:
                        parts.append("(heterochromia:1.3)")

        # Ensure background/scene elements reach the prompt
        if va and va.background_elements:
            existing_lower = {p.lower().strip() for p in parts}
            for bg in va.background_elements:
                if bg.lower().strip() not in existing_lower:
                    parts.append(bg)
                    existing_lower.add(bg.lower().strip())

        # Subjects from reference image analysis (only high-confidence VA)
        if va and va.confidence > 0.5 and va.subjects:
            existing = " ".join(parts).lower()
            for s in va.subjects:
                if s.lower() not in existing:
                    parts.append(s)

        if plan.style_tags:
            parts.extend(plan.style_tags)
        return ", ".join(p.strip() for p in parts if p.strip())

    def _build_negative_prompt(
        self, plan: LayerPlan, preset: PlannerPreset,
        job: Optional[AnimePipelineJob] = None,
    ) -> str:
        parts = [self._config.negative_base]
        if plan.negative_constraints:
            parts.extend(plan.negative_constraints)
        style = plan.style_tags[0] if plan.style_tags else "anime"
        style_neg = self._config.style_negatives.get(style, "")
        if style_neg:
            parts.append(style_neg)
        if preset.negative_extra:
            parts.append(preset.negative_extra)
        combined = ", ".join(parts)

        # Strip text-blocking tags only when user explicitly requests text overlay
        if job and _user_requests_text(job.user_prompt):
            no_text_tags = {t.strip().lower() for t in _NO_TEXT_NEGATIVE.split(",")}
            filtered = [
                t for t in combined.split(",")
                if t.strip().lower() not in no_text_tags
            ]
            combined = ", ".join(filtered)
        else:
            # Ensure comprehensive text/credit blocking is present
            existing_lower = combined.lower()
            additions = [
                t for t in _NO_TEXT_NEGATIVE.split(",")
                if t.strip().lower() not in existing_lower
            ]
            if additions:
                combined = combined + ", " + ", ".join(additions)

        return combined

    @staticmethod
    def _apply_pass_prompt(base_prompt: str, override: PassOverride) -> str:
        """Apply per-pass prompt prefix/suffix from preset override."""
        parts = []
        if override.prompt_prefix:
            parts.append(override.prompt_prefix)
        parts.append(base_prompt)
        if override.prompt_suffix:
            parts.append(override.prompt_suffix)
        return ", ".join(parts)

    def _build_style_tags(self, job: AnimePipelineJob, va) -> list[str]:
        tags = ["anime", "vibrant_colors", "colorful"]
        if va and va.anime_tags:
            tags.extend(va.anime_tags[:3])
        if job.style_hint and job.style_hint not in tags:
            tags.insert(0, job.style_hint)
        return list(dict.fromkeys(tags))  # deduplicate preserving order

    def _build_negative_constraints(self, job: AnimePipelineJob, va) -> list[str]:
        constraints = []
        if va and va.suggested_negative:
            constraints.extend(va.suggested_negative.split(","))
        if va and va.quality_risks:
            constraints.extend(va.quality_risks)
        return [c.strip() for c in constraints if c.strip()]

    # ── Critique integration ──────────────────────────────────────────

    @staticmethod
    def _apply_critique(
        positive: str,
        negative: str,
        critique: CritiqueReport,
    ) -> tuple[str, str]:
        """Incorporate critique corrections into prompts."""
        # Add prompt patches
        if critique.prompt_patch:
            positive = positive + ", " + ", ".join(critique.prompt_patch)

        # Add all flagged issues to negative
        all_issues = critique.all_issues
        if all_issues:
            negative = negative + ", " + ", ".join(all_issues[:5])

        return positive, negative

    # ── Structure layers ──────────────────────────────────────────────

    def _select_structure_layers(self) -> list[str]:
        available = sorted(
            self._config.structure_layers, key=lambda x: x.priority,
        )
        selected = []
        for layer in available:
            if len(selected) >= self._config.max_simultaneous_layers:
                break
            if not layer.optional or len(selected) < self._config.max_simultaneous_layers:
                selected.append(layer.layer_type)
        return selected or ["lineart_anime", "depth"]

    def _build_control_inputs(
        self,
        structure_types: list[str],
        preset: PlannerPreset,
    ) -> list[ControlInput]:
        """Build ControlInput list from selected structure layer types.

        image_b64 is left empty — populated later by the structure lock stage.
        Applies preset controlnet_strength_scale to all passes that use them.
        """
        # Use beauty override scale as default (most impactful pass)
        beauty_ov = preset.pass_overrides.get("beauty", PassOverride())
        scale = beauty_ov.controlnet_strength_scale

        inputs = []
        for lt in structure_types:
            for cfg in self._config.structure_layers:
                if cfg.layer_type == lt:
                    inputs.append(ControlInput(
                        layer_type=lt,
                        controlnet_model=cfg.controlnet_model,
                        strength=min(1.0, cfg.strength * scale),
                        start_percent=cfg.start_percent,
                        end_percent=cfg.end_percent,
                        preprocessor=cfg.preprocessor,
                    ))
                    break
        return inputs
