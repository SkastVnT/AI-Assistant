"""
image_pipeline.anime_pipeline.schemas — Data contracts for the anime multi-pass pipeline.

All vision analysis is stored as structured JSON, never as hidden reasoning text.
Every schema uses typed fields; planner output is deterministic structured JSON.
"""

from __future__ import annotations

import enum
import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════
# Enums
# ═════════════════════════════════════════════════════════════════════

class AnimePipelineStatus(str, enum.Enum):
    """Lifecycle of an AnimePipelineJob."""
    PENDING            = "pending"
    VISION_ANALYZING   = "vision_analyzing"
    PLANNING           = "planning"
    COMPOSING          = "composing"
    STRUCTURE_LOCKING  = "structure_locking"
    CLEANUP            = "cleanup"
    BEAUTY_RENDERING   = "beauty_rendering"
    CRITIQUING         = "critiquing"
    REFINING           = "refining"
    UPSCALING          = "upscaling"
    COMPLETED          = "completed"
    FAILED             = "failed"


class StructureLayerType(str, enum.Enum):
    """Control layer types for structure locking."""
    LINEART_ANIME = "lineart_anime"
    LINEART       = "lineart"
    DEPTH         = "depth"
    CANNY         = "canny"


class CritiqueDimension(str, enum.Enum):
    """Evaluation dimensions for critique scoring."""
    ANATOMY              = "anatomy"
    FACE                 = "face"
    HANDS                = "hands"
    COMPOSITION          = "composition"
    COLOR                = "color"
    STYLE                = "style"
    BACKGROUND           = "background"
    INSTRUCTION_ADHERENCE = "instruction_adherence"
    DETAIL_HANDLING       = "detail_handling"
    IDENTITY_CONSISTENCY  = "identity_consistency"


# ═════════════════════════════════════════════════════════════════════
# Vision Analysis (structured JSON, no hidden reasoning)
# ═════════════════════════════════════════════════════════════════════

@dataclass
class VisionAnalysis:
    """Structured output from the Vision Analyst service.

    All fields are explicit and JSON-serializable.
    No hidden chain-of-thought or reasoning text.
    """
    caption_short: str = ""
    caption_detailed: str = ""
    subjects: list[str] = field(default_factory=list)
    pose: str = ""
    camera_angle: str = ""
    framing: str = ""
    background_elements: list[str] = field(default_factory=list)
    dominant_colors: list[str] = field(default_factory=list)
    anime_tags: list[str] = field(default_factory=list)
    quality_risks: list[str] = field(default_factory=list)
    missing_details: list[str] = field(default_factory=list)
    identity_anchors: list[str] = field(default_factory=list)
    suggested_negative: str = ""
    layer_analysis: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    model_used: str = ""
    latency_ms: float = 0.0

    # Backward-compat aliases
    @property
    def subject_description(self) -> str:
        return ", ".join(self.subjects)

    @property
    def color_palette(self) -> list[str]:
        return self.dominant_colors

    def to_dict(self) -> dict[str, Any]:
        return {
            "caption_short": self.caption_short,
            "caption_detailed": self.caption_detailed,
            "subjects": self.subjects,
            "pose": self.pose,
            "camera_angle": self.camera_angle,
            "framing": self.framing,
            "background_elements": self.background_elements,
            "dominant_colors": self.dominant_colors,
            "anime_tags": self.anime_tags,
            "quality_risks": self.quality_risks,
            "missing_details": self.missing_details,
            "identity_anchors": self.identity_anchors,
            "suggested_negative": self.suggested_negative,
            "layer_analysis": self.layer_analysis,
            "confidence": self.confidence,
            "model_used": self.model_used,
            "latency_ms": self.latency_ms,
        }


# ═════════════════════════════════════════════════════════════════════
# Control Input — a single ControlNet / preprocessor reference
# ═════════════════════════════════════════════════════════════════════

@dataclass
class ControlInput:
    """A single ControlNet input for a rendering pass."""
    layer_type: str = ""                # lineart_anime | depth | canny
    controlnet_model: str = ""
    strength: float = 0.8
    start_percent: float = 0.0
    end_percent: float = 0.8
    preprocessor: str = ""              # required for structure extraction
    image_b64: str = ""                 # populated after structure lock

    def to_dict(self) -> dict[str, Any]:
        return {
            "layer_type": self.layer_type,
            "controlnet_model": self.controlnet_model,
            "strength": self.strength,
            "start_percent": self.start_percent,
            "end_percent": self.end_percent,
            "preprocessor": self.preprocessor,
            "has_image": bool(self.image_b64),
        }


# ═════════════════════════════════════════════════════════════════════
# PassConfig — per-pass rendering parameters
# ═════════════════════════════════════════════════════════════════════

@dataclass
class PassConfig:
    """Configuration for a single rendering pass in the pipeline.

    Used by the workflow builder to generate ComfyUI workflow JSON.
    """
    pass_name: str = ""                 # composition | cleanup | beauty | upscale
    model_slot: str = ""                # base | cleanup | final — maps to config model
    checkpoint: str = ""                # resolved checkpoint filename
    width: int = 832
    height: int = 1216
    sampler: str = "euler_ancestral"
    scheduler: str = "normal"
    steps: int = 28
    cfg: float = 5.0
    denoise: float = 1.0
    seed: int = -1                      # -1 = random
    positive_prompt: str = ""
    negative_prompt: str = ""
    control_inputs: list[ControlInput] = field(default_factory=list)
    prompt_strategy: str = "broad"      # broad | correction | detail
    expected_output: str = ""           # human-readable note
    source_image_b64: str = ""          # for img2img passes
    lora_models: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "pass_name": self.pass_name,
            "model_slot": self.model_slot,
            "checkpoint": self.checkpoint,
            "width": self.width,
            "height": self.height,
            "sampler": self.sampler,
            "scheduler": self.scheduler,
            "steps": self.steps,
            "cfg": self.cfg,
            "denoise": self.denoise,
            "seed": self.seed,
            "control_inputs": [c.to_dict() for c in self.control_inputs],
            "prompt_strategy": self.prompt_strategy,
            "expected_output": self.expected_output,
            "lora_models": self.lora_models,
        }


# ═════════════════════════════════════════════════════════════════════
# LayerPlan — structured generation plan
# ═════════════════════════════════════════════════════════════════════

@dataclass
class LayerPlan:
    """Structured generation plan produced by the layer planner.

    This is a deterministic JSON object, not chain-of-thought prose.
    Contains the full scene description and ordered pass list.
    """
    scene_summary: str = ""
    subject_list: list[str] = field(default_factory=list)
    camera: str = "medium_shot"         # close_up | medium_shot | full_body | wide
    pose: str = ""
    palette: list[str] = field(default_factory=list)
    lighting: str = "soft"
    style_tags: list[str] = field(default_factory=lambda: ["anime", "vibrant_colors", "colorful"])
    background_plan: str = ""
    negative_constraints: list[str] = field(default_factory=list)
    passes: list[PassConfig] = field(default_factory=list)

    # Convenience resolution (derived from first pass)
    @property
    def resolution_width(self) -> int:
        return self.passes[0].width if self.passes else 832

    @property
    def resolution_height(self) -> int:
        return self.passes[0].height if self.passes else 1216

    # Backward-compat aliases
    @property
    def positive_prompt_base(self) -> str:
        return self.passes[0].positive_prompt if self.passes else ""

    @property
    def negative_prompt_base(self) -> str:
        return self.passes[0].negative_prompt if self.passes else ""

    @property
    def composition_pass(self) -> Optional[PassConfig]:
        return self._find_pass("composition")

    @property
    def cleanup_pass(self) -> Optional[PassConfig]:
        return self._find_pass("cleanup")

    @property
    def beauty_pass(self) -> Optional[PassConfig]:
        return self._find_pass("beauty")

    @property
    def upscale_pass(self) -> bool:
        return self._find_pass("upscale") is not None

    def _find_pass(self, name: str) -> Optional[PassConfig]:
        for p in self.passes:
            if p.pass_name == name:
                return p
        return None

    def get_pass(self, name: str) -> Optional[PassConfig]:
        """Public accessor for any pass by name."""
        return self._find_pass(name)

    def validate(self) -> list[str]:
        """Validate plan structure. Returns list of error messages (empty = valid)."""
        errors: list[str] = []
        if not self.scene_summary:
            errors.append("scene_summary is empty")
        if not self.passes:
            errors.append("no passes defined")
        else:
            names = [p.pass_name for p in self.passes]
            if "composition" not in names:
                errors.append("missing composition pass")
            for i, p in enumerate(self.passes):
                if not p.pass_name:
                    errors.append(f"pass[{i}] has no pass_name")
                # structure_lock and upscale are non-rendering passes
                if p.pass_name in ("structure_lock", "upscale"):
                    continue
                if not p.checkpoint:
                    errors.append(f"pass[{i}] ({p.pass_name}) has no checkpoint")
                if p.width < 64 or p.height < 64:
                    errors.append(f"pass[{i}] ({p.pass_name}) resolution too small")
                if p.steps < 1:
                    errors.append(f"pass[{i}] ({p.pass_name}) steps < 1")
        return errors

    def to_dict(self) -> dict[str, Any]:
        return {
            "scene_summary": self.scene_summary,
            "subject_list": self.subject_list,
            "camera": self.camera,
            "pose": self.pose,
            "palette": self.palette,
            "lighting": self.lighting,
            "style_tags": self.style_tags,
            "background_plan": self.background_plan,
            "negative_constraints": self.negative_constraints,
            "passes": [p.to_dict() for p in self.passes],
        }


# ═════════════════════════════════════════════════════════════════════
# CritiqueReport — structured per-dimension scoring
# ═════════════════════════════════════════════════════════════════════

class RefineActionType(str, enum.Enum):
    """Atomic actions the refine loop can apply."""
    ADJUST_DENOISE       = "adjust_denoise"
    ADJUST_CONTROL       = "adjust_control"
    PATCH_POSITIVE       = "patch_positive"
    PATCH_NEGATIVE       = "patch_negative"
    SWITCH_PRESET        = "switch_preset"


@dataclass
class RefineAction:
    """A single deterministic adjustment for a refine round."""
    action_type: RefineActionType = RefineActionType.ADJUST_DENOISE
    target: str = ""                    # e.g. "denoise", "lineart_anime", "positive"
    value: Any = None                   # e.g. 0.05 (delta), "fix hands" (tag), "subtle"
    reason: str = ""                    # human-readable explanation

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type.value,
            "target": self.target,
            "value": self.value,
            "reason": self.reason,
        }


@dataclass
class RefineDecision:
    """Outcome of decide_refine_action(): should we refine, and how."""
    should_refine: bool = False
    actions: list[RefineAction] = field(default_factory=list)
    reason: str = ""                    # summary of why we refine or stop
    worst_dimensions: list[str] = field(default_factory=list)  # sorted worst→best

    def to_dict(self) -> dict[str, Any]:
        return {
            "should_refine": self.should_refine,
            "actions": [a.to_dict() for a in self.actions],
            "reason": self.reason,
            "worst_dimensions": self.worst_dimensions,
        }


@dataclass
class CritiqueReport:
    """Structured critique report with per-dimension scores and patches.

    All analysis stored as explicit fields, no hidden reasoning.
    Scores are 0-10 integers; retry_recommendation is bool.

    10 scored dimensions:
      anatomy, face_symmetry (face_score), eye_consistency, hand_quality
      (hands_score), clothing_consistency, style_drift (style_score),
      color_drift (color_score), background_clutter (background_score),
      missing_accessories, pose_drift.

    Legacy names (face_score, hands_score, etc.) kept for backward compat.
    """
    # Issue lists (per-dimension)
    anatomy_issues: list[str] = field(default_factory=list)
    face_issues: list[str] = field(default_factory=list)
    eye_issues: list[str] = field(default_factory=list)
    hand_issues: list[str] = field(default_factory=list)
    clothing_issues: list[str] = field(default_factory=list)
    composition_issues: list[str] = field(default_factory=list)
    color_issues: list[str] = field(default_factory=list)
    style_drift: list[str] = field(default_factory=list)
    background_issues: list[str] = field(default_factory=list)
    accessories_issues: list[str] = field(default_factory=list)
    pose_issues: list[str] = field(default_factory=list)

    # Recommendations
    retry_recommendation: bool = False
    prompt_patch: list[str] = field(default_factory=list)
    control_patch: dict[str, float] = field(default_factory=dict)

    # ── Numeric scores (0-10) ─ 10 dimensions ───────────────────
    anatomy_score: int = 0
    face_score: int = 0               # face symmetry
    eye_consistency_score: int = 0
    # Vision-based reference comparison: 0-100% match of generated eyes vs reference.
    # 0.0 means "not measured" (no reference images). Gate: must be >=95 to pass.
    eye_reference_match_pct: float = 0.0
    hands_score: int = 0              # hand quality
    clothing_score: int = 0           # clothing consistency
    composition_score: int = 0
    color_score: int = 0              # color drift
    style_score: int = 0              # style drift
    background_score: int = 0         # background clutter
    accessories_score: int = 0        # missing accessories
    pose_score: int = 0               # pose drift

    @property
    def overall_score(self) -> float:
        """Weighted average of all dimension scores (0-10 scale).

        Only includes dimensions that were actually scored (> 0).
        Dimensions left at the default value of 0 are excluded so that
        LLM responses that only fill in a subset of fields don't get
        artificially penalised by unchecked dimensions dragging the
        average down.

        Face/eye weighted higher because face quality is the primary
        quality signal for anime outputs.
        """
        scores_weights: list[tuple[int, float]] = [
            (self.anatomy_score,          1.0),
            (self.face_score,             1.5),   # face weighted higher
            (self.eye_consistency_score,   1.2),   # eyes are critical
            (self.hands_score,            1.0),
            (self.clothing_score,         0.8),
            (self.composition_score,      1.0),
            (self.color_score,            0.8),
            (self.style_score,            1.0),
            (self.background_score,       0.7),
            (self.accessories_score,      0.5),
            (self.pose_score,             0.9),
        ]
        # Skip dimensions with score == 0 (not set by LLM)
        active = [(s, w) for s, w in scores_weights if s > 0]
        if not active:
            return 0.0
        total_weighted = sum(s * w for s, w in active)
        total_weight = sum(w for _, w in active)
        return total_weighted / total_weight if total_weight else 0.0

    @property
    def passed(self) -> bool:
        """True if overall score >= 8.0 AND every scored dimension >= 8.

        Strict mode: no dimension is allowed to be below 8/10.
        Dimensions scored 0 are considered 'not evaluated' and skipped.
        """
        if self.retry_recommendation:
            return False
        if self.overall_score < 8.0:
            return False
        # Strict: every scored dimension must be >= 8
        _STRICT_MIN = 8
        for _name, score in self.dimension_scores.items():
            if score > 0 and score < _STRICT_MIN:
                return False
        # Hard-fail if eye reference comparison was measured and below 95%
        if self.eye_reference_match_pct > 0.0 and self.eye_reference_match_pct < 95.0:
            return False
        return True

    @property
    def all_issues(self) -> list[str]:
        """Flatten all issue lists."""
        return (
            self.anatomy_issues + self.face_issues + self.eye_issues +
            self.hand_issues + self.clothing_issues +
            self.composition_issues + self.color_issues + self.style_drift +
            self.background_issues + self.accessories_issues +
            self.pose_issues
        )

    @property
    def dimension_scores(self) -> dict[str, int]:
        """All dimension scores as a dict (useful for iteration).

        Returns 11 dimensions (10 named + eye_reference_match_pct).
        """
        return {
            "anatomy": self.anatomy_score,
            "face_symmetry": self.face_score,
            "eye_consistency": self.eye_consistency_score,
            "hand_quality": self.hands_score,
            "clothing_consistency": self.clothing_score,
            "composition": self.composition_score,
            "color_drift": self.color_score,
            "style_drift": self.style_score,
            "background_clutter": self.background_score,
            "missing_accessories": self.accessories_score,
            "pose_drift": self.pose_score,
        }

    # Backward compat
    model_used: str = ""
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "anatomy_issues": self.anatomy_issues,
            "face_issues": self.face_issues,
            "eye_issues": self.eye_issues,
            "hand_issues": self.hand_issues,
            "clothing_issues": self.clothing_issues,
            "composition_issues": self.composition_issues,
            "color_issues": self.color_issues,
            "style_drift": self.style_drift,
            "background_issues": self.background_issues,
            "accessories_issues": self.accessories_issues,
            "pose_issues": self.pose_issues,
            "retry_recommendation": self.retry_recommendation,
            "prompt_patch": self.prompt_patch,
            "control_patch": self.control_patch,
            "anatomy_score": self.anatomy_score,
            "face_score": self.face_score,
            "eye_consistency_score": self.eye_consistency_score,
            "eye_reference_match_pct": self.eye_reference_match_pct,
            "hands_score": self.hands_score,
            "clothing_score": self.clothing_score,
            "composition_score": self.composition_score,
            "color_score": self.color_score,
            "style_score": self.style_score,
            "background_score": self.background_score,
            "accessories_score": self.accessories_score,
            "pose_score": self.pose_score,
            "overall_score": self.overall_score,
            "dimension_scores": self.dimension_scores,
            "passed": self.passed,
            "model_used": self.model_used,
            "latency_ms": self.latency_ms,
        }


# Backward compat alias
CritiqueResult = CritiqueReport


# ═════════════════════════════════════════════════════════════════════
# Structure Layer
# ═════════════════════════════════════════════════════════════════════

@dataclass
class StructureLayer:
    """A control layer extracted from the composition image."""
    layer_type: StructureLayerType = StructureLayerType.LINEART_ANIME
    image_b64: str = ""
    preprocessor: str = ""
    controlnet_model: str = ""
    strength: float = 0.8
    start_percent: float = 0.0
    end_percent: float = 0.8


# ═════════════════════════════════════════════════════════════════════
# Intermediate Image
# ═════════════════════════════════════════════════════════════════════

@dataclass
class IntermediateImage:
    """An intermediate image produced during pipeline execution."""
    stage: str = ""
    image_b64: str = ""
    file_path: str = ""
    width: int = 0
    height: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# ═════════════════════════════════════════════════════════════════════
# AnimePipelineJob — Master container
# ═════════════════════════════════════════════════════════════════════

@dataclass
class AnimePipelineJob:
    """Master data container for the anime multi-pass pipeline.

    Travels through all stages, accumulating results.
    """
    # Identity
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex[:16])
    session_id: str = ""
    status: AnimePipelineStatus = AnimePipelineStatus.PENDING
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    completed_at: Optional[str] = None

    # Input
    user_prompt: str = ""
    language: str = "en"
    reference_images_b64: list[str] = field(default_factory=list)
    reference_images_url: list[str] = field(default_factory=list)
    source_image_b64: Optional[str] = None  # For img2img / edit mode
    style_hint: str = "anime"
    quality_hint: str = "quality"
    orientation_hint: str = ""  # auto-detected if empty
    preset: str = "anime_quality"
    user_loras: list[dict[str, Any]] = field(default_factory=list)

    # Stage outputs
    vision_analysis: Optional[VisionAnalysis] = None
    layer_plan: Optional[LayerPlan] = None
    structure_layers: list[StructureLayer] = field(default_factory=list)
    critique_results: list[CritiqueReport] = field(default_factory=list)
    intermediates: list[IntermediateImage] = field(default_factory=list)

    # Final output
    final_image_b64: Optional[str] = None
    final_image_url: Optional[str] = None
    final_image_path: Optional[str] = None

    # Execution metadata
    stages_executed: list[str] = field(default_factory=list)
    stage_timings_ms: dict[str, float] = field(default_factory=dict)
    total_latency_ms: float = 0.0
    refine_rounds: int = 0
    models_used: list[str] = field(default_factory=list)
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-friendly dict (manifest)."""
        return {
            "job_id": self.job_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "user_prompt": self.user_prompt,
            "language": self.language,
            "style_hint": self.style_hint,
            "quality_hint": self.quality_hint,
            "preset": self.preset,
            "vision_analysis": self.vision_analysis.to_dict() if self.vision_analysis else None,
            "layer_plan": self.layer_plan.to_dict() if self.layer_plan else None,
            "critique_results": [c.to_dict() for c in self.critique_results],
            "stages_executed": self.stages_executed,
            "stage_timings_ms": self.stage_timings_ms,
            "total_latency_ms": self.total_latency_ms,
            "refine_rounds": self.refine_rounds,
            "models_used": self.models_used,
            "has_final_image": self.final_image_b64 is not None,
            "final_image_url": self.final_image_url,
            "error": self.error,
        }

    def mark_stage(self, stage: str, latency_ms: float) -> None:
        """Record stage completion."""
        self.stages_executed.append(stage)
        self.stage_timings_ms[stage] = latency_ms

    def add_intermediate(
        self, stage: str, image_b64: str, **metadata: Any
    ) -> None:
        """Store an intermediate image and track model if given."""
        self.intermediates.append(IntermediateImage(
            stage=stage,
            image_b64=image_b64,
            metadata=metadata,
        ))
        model = metadata.get("model") or metadata.get("checkpoint")
        if model and model not in self.models_used:
            self.models_used.append(model)


# ═════════════════════════════════════════════════════════════════════
# Final Ranking — candidate scoring and selection
# ═════════════════════════════════════════════════════════════════════

@dataclass
class RankCandidate:
    """A single candidate image for final ranking.

    Scored on four axes: face quality, clarity, style consistency,
    and artifact count.  ``composite_score`` is the weighted aggregate.
    """
    image_b64: str = ""
    stage: str = ""                     # e.g. "beauty_pass", "upscale"
    critique: Optional[CritiqueReport] = None
    face_quality: float = 0.0           # 0-10
    clarity: float = 0.0                # 0-10
    style_consistency: float = 0.0      # 0-10
    artifact_count: int = 0
    composite_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "face_quality": round(self.face_quality, 2),
            "clarity": round(self.clarity, 2),
            "style_consistency": round(self.style_consistency, 2),
            "artifact_count": self.artifact_count,
            "composite_score": round(self.composite_score, 2),
            "has_image": bool(self.image_b64),
        }


@dataclass
class RankResult:
    """Outcome of the final ranking stage.

    ``winner`` is the highest-scoring candidate.
    ``runner_ups`` contains remaining candidates sorted by score descending.
    """
    winner: Optional[RankCandidate] = None
    runner_ups: list[RankCandidate] = field(default_factory=list)
    total_candidates: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "winner": self.winner.to_dict() if self.winner else None,
            "runner_ups": [r.to_dict() for r in self.runner_ups],
            "total_candidates": self.total_candidates,
        }


# Legacy alias kept for backward compat with existing LayerPassConfig references
LayerPassConfig = PassConfig
