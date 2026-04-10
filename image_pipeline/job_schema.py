"""
image_pipeline.job_schema — Canonical data contracts for the Nano Banana-like pipeline.

Five core schemas (per SKILL.md §11.3, §12, §13, §14):
    1. ImageJob          — The unit of work; travels through all 9 stages
    2. PromptSpec        — 4-layer internal prompt system
    3. RefinementPlan    — What to fix, how, and where
    4. EvalResult        — 8-dimension scoring + pass/fail
    5. RunMetadata       — Timing, costs, models, execution locations, experiment log

Supporting types:
    ReferenceImage, ReferenceRole, GenerationParams, StageResult,
    StageStatus, JobStatus, ExecutionLocation, ModelUsage,
    EvalDimension, RefinementTarget, RefinementStrategy, OutputTargets
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

class JobStatus(str, enum.Enum):
    """Lifecycle of an ImageJob."""
    PENDING     = "pending"       # Created, not yet started
    NORMALIZING = "normalizing"   # Stage 0
    PLANNING    = "planning"      # Stage 0-1
    LOADING     = "loading"       # Stage 2 — reference loading
    GENERATING  = "generating"    # Stage 3 — first pass
    COMPOSING   = "composing"     # Stage 4 — multi-ref compose
    REFINING    = "refining"      # Stage 5
    EVALUATING  = "evaluating"    # Stage 6
    CORRECTING  = "correcting"    # Stage 7
    FINALIZING  = "finalizing"    # Stage 8
    COMPLETED   = "completed"
    FAILED      = "failed"


class StageStatus(str, enum.Enum):
    """Status per individual pipeline stage."""
    PENDING   = "pending"
    RUNNING   = "running"
    COMPLETED = "completed"
    SKIPPED   = "skipped"
    FAILED    = "failed"


class ReferenceRole(str, enum.Enum):
    """What part of the output a reference image controls."""
    FACE       = "face"
    OUTFIT     = "outfit"
    BACKGROUND = "background"
    STYLE      = "style"
    PROP       = "prop"
    POSE       = "pose"
    COLOR      = "color"
    FULL       = "full"          # Whole-image reference (img2img)


class ExecutionLocation(str, enum.Enum):
    """Where a stage ran."""
    LOCAL  = "local"     # Local GPU / ComfyUI
    VPS    = "vps"       # Remote VPS (vLLM, heavy models)
    API    = "api"       # Third-party API (fal, BFL, OpenAI)
    HYBRID = "hybrid"    # Multi-location stage


class RefinementStrategy(str, enum.Enum):
    """How to refine a region."""
    FILL       = "fill"        # FLUX.1 Fill mask-based inpaint
    ADETAILER  = "adetailer"   # ComfyUI auto-detect + re-inpaint
    IPADAPTER  = "ipadapter"   # Identity injection via IP-Adapter
    CONTROLNET = "controlnet"  # Structure-preserving re-generation
    SEMANTIC   = "semantic"    # Re-run semantic editor on region
    COMPOSITE  = "composite"   # Multi-strategy refinement


class EvalDimension(str, enum.Enum):
    """8 benchmark dimensions per §13."""
    INSTRUCTION_ADHERENCE = "instruction_adherence"
    SEMANTIC_EDIT         = "semantic_edit_accuracy"
    IDENTITY_CONSISTENCY  = "identity_consistency"
    MULTI_REF_QUALITY     = "multi_ref_quality"
    DETAIL_HANDLING       = "detail_handling"
    TEXT_RENDERING        = "text_rendering"
    MULTI_TURN_STABILITY  = "multi_turn_stability"
    CORRECTION_SUCCESS    = "correction_success"


# ═════════════════════════════════════════════════════════════════════
# Supporting dataclasses
# ═════════════════════════════════════════════════════════════════════

@dataclass
class ReferenceImage:
    """A tagged reference image with its role in the composition."""
    role:         ReferenceRole
    image_b64:    Optional[str] = None
    image_url:    Optional[str] = None
    label:        str           = ""      # Human-readable ("headshot of Alice")
    weight:       float         = 1.0     # Influence strength (0.0-1.0)
    crop_region:  Optional[str] = None    # "face" | "upper_body" | None (full)
    cached_path:  Optional[str] = None    # Local cache path in storage/references/

    @property
    def has_data(self) -> bool:
        return bool(self.image_b64 or self.image_url or self.cached_path)


@dataclass
class GenerationParams:
    """Model-agnostic generation parameters."""
    width:           int            = 1024
    height:          int            = 1024
    steps:           int            = 28
    guidance:        float          = 3.5
    strength:        float          = 0.8    # img2img denoising (0-1)
    seed:            Optional[int]  = None
    num_images:      int            = 1
    style_preset:    Optional[str]  = None   # "photorealistic", "anime", etc.
    negative_prompt: str            = ""
    extra:           dict           = field(default_factory=dict)


@dataclass
class ModelUsage:
    """Record of a model invocation."""
    provider:     str                        # "fal", "bfl", "comfyui", "vps"
    model:        str                        # "flux2-pro", "qwen-image-edit"
    location:     ExecutionLocation = ExecutionLocation.API
    latency_ms:   float             = 0.0
    cost_usd:     float             = 0.0
    stage:        str               = ""     # Which pipeline stage used this model
    success:      bool              = True
    error:        Optional[str]     = None


@dataclass
class StageResult:
    """Output of a single pipeline stage."""
    stage:          str                        # "normalize", "constrain", etc.
    status:         StageStatus     = StageStatus.PENDING
    started_at:     Optional[str]   = None
    completed_at:   Optional[str]   = None
    latency_ms:     float           = 0.0
    location:       ExecutionLocation = ExecutionLocation.API

    # Image data — populated by generation/composition/refinement stages
    image_b64:      Optional[str]   = None
    image_url:      Optional[str]   = None
    intermediate_path: Optional[str] = None   # storage/intermediate/<job_id>/<stage>.png

    # Model used (if any)
    model_usage:    Optional[ModelUsage] = None

    # Stage-specific output (flexible)
    output:         dict            = field(default_factory=dict)
    error:          Optional[str]   = None

    def mark_running(self) -> None:
        self.status = StageStatus.RUNNING
        self.started_at = datetime.now(timezone.utc).isoformat()

    def mark_completed(self, latency_ms: float = 0.0) -> None:
        self.status = StageStatus.COMPLETED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.latency_ms = latency_ms

    def mark_failed(self, error: str) -> None:
        self.status = StageStatus.FAILED
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.error = error

    def mark_skipped(self, reason: str = "") -> None:
        self.status = StageStatus.SKIPPED
        self.output["skip_reason"] = reason


@dataclass
class OutputTargets:
    """Where and how to store final outputs."""
    save_local:        bool = True
    save_cloud:        bool = False
    save_intermediate: bool = True     # Keep per-stage images
    output_format:     str  = "png"    # "png" | "jpeg" | "webp"
    output_quality:    int  = 95       # JPEG/WebP quality
    max_dimension:     int  = 2048     # Cap output resolution
    output_dir:        str  = "storage/outputs"
    metadata_dir:      str  = "storage/metadata"


# ═════════════════════════════════════════════════════════════════════
# SCHEMA 2 — PromptSpec (§14: 4-layer prompt system)
# ═════════════════════════════════════════════════════════════════════

@dataclass
class PromptSpec:
    """
    4-layer internal prompt system per §14.

    Layer 1 — Planning prompt:    understand intent + constraints
    Layer 2 — Execution prompt:   feed to gen/edit model
    Layer 3 — Refinement prompt:  targeted fix for stubborn regions
    Layer 4 — Correction prompt:  re-run when eval fails

    Rules:
    - Prompt describes ONLY what needs to change (not the full image when refs exist)
    - Identity constraints separated from change instructions
    - Regional edits → regional prompts only
    """

    # The 4 layers
    planning_prompt:    str = ""    # Layer 1: intent + constraints (internal use)
    execution_prompt:   str = ""    # Layer 2: sent to primary model
    refinement_prompt:  str = ""    # Layer 3: sent to fill/adetailer
    correction_prompt:  str = ""    # Layer 4: re-generation after eval fail

    # Context
    original_instruction: str           = ""    # Raw user message
    language:             str           = "en"  # "en" | "vi"
    negative_prompt:      str           = ""
    style_tags:           list[str]     = field(default_factory=list)
    quality_tags:         list[str]     = field(default_factory=list)

    # Multi-turn lineage (for consistency across turns)
    prompt_lineage:     list[str]       = field(default_factory=list)
    # Previous prompts in this edit chain — newest last

    # Identity anchors (what NOT to re-describe because refs carry it)
    identity_anchors:   list[str]       = field(default_factory=list)
    # e.g. ["face from ref_0", "outfit from ref_1"]

    # Change instructions (what to actually modify)
    change_instructions: list[str]      = field(default_factory=list)
    # e.g. ["change background to beach sunset", "add sunglasses"]

    # Budget control
    max_tokens_execution:  int = 300    # Cap execution prompt length
    max_tokens_refinement: int = 150    # Refinement prompts are shorter

    @property
    def active_layer(self) -> str:
        """Which prompt layer is currently most relevant."""
        if self.correction_prompt:
            return "correction"
        if self.refinement_prompt:
            return "refinement"
        if self.execution_prompt:
            return "execution"
        return "planning"

    def to_dict(self) -> dict:
        return {
            "planning": self.planning_prompt,
            "execution": self.execution_prompt,
            "refinement": self.refinement_prompt,
            "correction": self.correction_prompt,
            "original": self.original_instruction,
            "language": self.language,
            "negative": self.negative_prompt,
            "lineage_depth": len(self.prompt_lineage),
            "active_layer": self.active_layer,
        }


# ═════════════════════════════════════════════════════════════════════
# SCHEMA 3 — RefinementPlan (§12 Stage 5 + §5.3-5.4)
# ═════════════════════════════════════════════════════════════════════

@dataclass
class RefinementTarget:
    """A single region/aspect to refine."""
    region:       str                           # "face", "hands", "text", "eyes", "background", "full"
    strategy:     RefinementStrategy = RefinementStrategy.FILL
    prompt:       str                = ""       # Region-specific prompt
    mask_b64:     Optional[str]      = None     # Pre-computed mask (if manual)
    mask_source:  str                = "auto"   # "auto" (model-detected) | "manual" | "bbox"
    priority:     int                = 1        # 1 = highest priority
    location:     ExecutionLocation  = ExecutionLocation.LOCAL  # Where to run this fix
    model_hint:   Optional[str]      = None     # Force specific model for this target


@dataclass
class RefinementPlan:
    """
    What to fix after the first-pass generation.

    Built by the planner (Stage 1) or the evaluator (Stage 6-7).
    Consumed by the refinement engine (Stage 5).
    """

    targets:        list[RefinementTarget] = field(default_factory=list)
    max_rounds:     int                    = 2        # Max refinement iterations
    current_round:  int                    = 0
    auto_detect:    bool                   = True     # Let ADetailer find problems
    detail_level:   str                    = "high"   # "low" | "medium" | "high"

    # Execution constraints
    timeout_ms:     int                    = 30_000   # Per-round timeout
    budget_usd:     float                  = 0.10     # Max cost for all refinement
    spent_usd:      float                  = 0.0

    # History of completed refinement attempts
    history:        list[dict]             = field(default_factory=list)
    # Each entry: {"round": int, "targets": [...], "success": bool, "latency_ms": float}

    @property
    def has_targets(self) -> bool:
        return len(self.targets) > 0

    @property
    def budget_remaining(self) -> float:
        return max(0.0, self.budget_usd - self.spent_usd)

    @property
    def can_continue(self) -> bool:
        return (
            self.current_round < self.max_rounds
            and self.budget_remaining > 0.0
            and self.has_targets
        )

    def add_round(self, targets: list[str], success: bool, latency_ms: float) -> None:
        self.history.append({
            "round": self.current_round,
            "targets": targets,
            "success": success,
            "latency_ms": latency_ms,
        })
        self.current_round += 1


# ═════════════════════════════════════════════════════════════════════
# SCHEMA 4 — EvalResult (§13: 8-dimension benchmark)
# ═════════════════════════════════════════════════════════════════════

# Default thresholds — override via configs/pipeline.yaml
_DEFAULT_THRESHOLDS: dict[str, float] = {
    EvalDimension.INSTRUCTION_ADHERENCE: 0.7,
    EvalDimension.SEMANTIC_EDIT:         0.7,
    EvalDimension.IDENTITY_CONSISTENCY:  0.8,
    EvalDimension.MULTI_REF_QUALITY:     0.6,
    EvalDimension.DETAIL_HANDLING:       0.7,
    EvalDimension.TEXT_RENDERING:        0.5,
    EvalDimension.MULTI_TURN_STABILITY:  0.7,
    EvalDimension.CORRECTION_SUCCESS:    0.6,
}


@dataclass
class EvalResult:
    """
    8-dimension scoring per §13.

    Each dimension is scored 0.0–1.0 by an LLM-as-judge
    (Qwen2.5-VL or GPT-4o with vision).
    A dimension passes if score ≥ threshold.
    The job passes overall if ALL applicable dimensions pass.
    """

    # Per-dimension scores (0.0–1.0)
    scores:         dict[str, float]        = field(default_factory=dict)
    # e.g. {"instruction_adherence": 0.85, "identity_consistency": 0.92, ...}

    # Which dimensions were actually evaluated (not all apply to every job)
    evaluated:      list[str]               = field(default_factory=list)

    # Thresholds used
    thresholds:     dict[str, float]        = field(default_factory=lambda: dict(_DEFAULT_THRESHOLDS))

    # Verdict
    passed:         bool                    = False
    failed_dimensions: list[str]            = field(default_factory=list)
    overall_score:  float                   = 0.0   # Weighted mean of evaluated dims

    # Judge metadata
    judge_model:    str                     = ""     # "qwen2.5-vl-72b", "gpt-4o", etc.
    judge_reasoning: dict[str, str]         = field(default_factory=dict)
    # Per-dimension reasoning: {"instruction_adherence": "Subject matches but...", ...}

    # Correction recommendations (populated when passed=False)
    correction_targets: list[str]           = field(default_factory=list)
    # Regions/aspects to fix: ["hands", "text", "background_consistency"]
    correction_strategy: Optional[str]      = None
    # Suggested strategy: "fill", "semantic", "composite"

    # Timing
    eval_latency_ms: float                  = 0.0

    def evaluate(self) -> None:
        """Compute pass/fail from scores vs thresholds."""
        self.failed_dimensions = []
        weighted_sum = 0.0
        count = 0

        for dim_name in self.evaluated:
            score = self.scores.get(dim_name, 0.0)
            threshold = self.thresholds.get(dim_name, 0.7)
            if score < threshold:
                self.failed_dimensions.append(dim_name)
            weighted_sum += score
            count += 1

        self.overall_score = weighted_sum / count if count > 0 else 0.0
        self.passed = len(self.failed_dimensions) == 0

    def dimension_detail(self, dim: str) -> dict:
        """Get score, threshold, and reasoning for one dimension."""
        return {
            "dimension": dim,
            "score": self.scores.get(dim, 0.0),
            "threshold": self.thresholds.get(dim, 0.7),
            "passed": self.scores.get(dim, 0.0) >= self.thresholds.get(dim, 0.7),
            "reasoning": self.judge_reasoning.get(dim, ""),
        }

    def to_log_dict(self) -> dict:
        """Structured dict for experiment logging."""
        return {
            "passed": self.passed,
            "overall_score": round(self.overall_score, 4),
            "scores": {k: round(v, 4) for k, v in self.scores.items()},
            "failed_dimensions": self.failed_dimensions,
            "judge_model": self.judge_model,
            "correction_targets": self.correction_targets,
            "eval_latency_ms": round(self.eval_latency_ms, 2),
        }


# ═════════════════════════════════════════════════════════════════════
# SCHEMA 5 — RunMetadata (execution tracking + benchmark logging)
# ═════════════════════════════════════════════════════════════════════

@dataclass
class RunMetadata:
    """
    Full execution record for an ImageJob.
    Written to storage/metadata/<job_id>.json after finalization.
    Supports A/B comparison, cost analysis, and stack benchmarking.
    """

    # Identity
    job_id:           str           = ""
    session_id:       str           = ""
    experiment_id:    Optional[str] = None   # For grouped A/B tests

    # Timestamps
    created_at:       str           = ""
    completed_at:     Optional[str] = None

    # Aggregate timing
    total_latency_ms: float         = 0.0
    stage_timings:    dict[str, float] = field(default_factory=dict)
    # {"normalize": 12.5, "generate": 3200.0, "refine": 1500.0, ...}

    # Models invoked (ordered by call sequence)
    models_used:      list[ModelUsage] = field(default_factory=list)

    # Cost
    total_cost_usd:   float         = 0.0

    # Execution locations per stage
    execution_map:    dict[str, str] = field(default_factory=dict)
    # {"generate": "api", "refine": "local", "evaluate": "api"}

    # Correction tracking
    correction_rounds:   int        = 0
    correction_improved: bool       = False  # Did correction loop help?

    # Final provider/model that produced the output
    final_provider:   str           = ""
    final_model:      str           = ""

    # Tags for filtering/search
    tags:             list[str]     = field(default_factory=list)
    # e.g. ["semantic_edit", "multi_ref", "correction_applied"]

    # Eval snapshot (inline summary — full EvalResult stored separately)
    eval_passed:      Optional[bool]  = None
    eval_score:       Optional[float] = None

    # Error trail (if any stage failed)
    errors:           list[dict]    = field(default_factory=list)
    # [{"stage": "generate", "error": "timeout", "model": "qwen-image-edit"}]

    def add_model_usage(self, usage: ModelUsage) -> None:
        self.models_used.append(usage)
        self.total_cost_usd += usage.cost_usd

    def add_stage_timing(self, stage: str, latency_ms: float, location: str = "api") -> None:
        self.stage_timings[stage] = latency_ms
        self.execution_map[stage] = location
        self.total_latency_ms = sum(self.stage_timings.values())

    def add_error(self, stage: str, error: str, model: str = "") -> None:
        self.errors.append({"stage": stage, "error": error, "model": model})

    def finalize(self) -> None:
        self.completed_at = datetime.now(timezone.utc).isoformat()
        self.total_latency_ms = sum(self.stage_timings.values())

    def to_log_dict(self) -> dict:
        """Full dict for JSON serialization to storage/metadata/."""
        return {
            "job_id": self.job_id,
            "session_id": self.session_id,
            "experiment_id": self.experiment_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "total_latency_ms": round(self.total_latency_ms, 2),
            "total_cost_usd": round(self.total_cost_usd, 6),
            "stage_timings": {k: round(v, 2) for k, v in self.stage_timings.items()},
            "execution_map": self.execution_map,
            "models_used": [
                {
                    "provider": m.provider, "model": m.model,
                    "location": m.location.value, "latency_ms": round(m.latency_ms, 2),
                    "cost_usd": round(m.cost_usd, 6), "stage": m.stage,
                    "success": m.success,
                }
                for m in self.models_used
            ],
            "correction_rounds": self.correction_rounds,
            "correction_improved": self.correction_improved,
            "final_provider": self.final_provider,
            "final_model": self.final_model,
            "eval_passed": self.eval_passed,
            "eval_score": round(self.eval_score, 4) if self.eval_score is not None else None,
            "tags": self.tags,
            "errors": self.errors,
        }


# ═════════════════════════════════════════════════════════════════════
# SCHEMA 1 — ImageJob (§11.3: the canonical unit of work)
# ═════════════════════════════════════════════════════════════════════

PIPELINE_STAGES = (
    "normalize",    # Stage 0
    "constrain",    # Stage 1
    "load_refs",    # Stage 2
    "generate",     # Stage 3
    "compose",      # Stage 4
    "refine",       # Stage 5
    "evaluate",     # Stage 6
    "correct",      # Stage 7
    "finalize",     # Stage 8
)


@dataclass
class ImageJob:
    """
    The canonical unit of work for the entire pipeline.

    Created at Stage 0 (normalize), enriched at each subsequent stage,
    and written to storage/metadata/ at Stage 8 (finalize).

    Fields per §11.3:
        job_id, user_instruction, parsed_constraints, must_keep, may_change,
        forbidden_changes, reference_images, preferred_models, fallback_models,
        generation_params, refinement_plan, output_targets

    Extended with: prompt_spec, eval_result, run_metadata, stage_results, status.
    """

    # ── Identity ──────────────────────────────────────────────────────
    job_id:              str              = field(default_factory=lambda: uuid.uuid4().hex[:16])
    session_id:          str              = ""
    status:              JobStatus        = JobStatus.PENDING

    # ── Input (Stage 0) ──────────────────────────────────────────────
    user_instruction:    str              = ""     # Raw natural-language input
    language:            str              = "en"   # "en" | "vi"
    intent:              str              = ""     # "generate" | "edit" | "followup" | "none"

    # ── Constraints (Stage 1) ────────────────────────────────────────
    must_keep:           list[str]        = field(default_factory=list)
    # Elements that MUST be preserved: ["face", "pose", "background_layout"]

    may_change:          list[str]        = field(default_factory=list)
    # Elements allowed to change: ["hair_color", "outfit", "lighting"]

    forbidden_changes:   list[str]        = field(default_factory=list)
    # Elements that MUST NOT change: ["identity", "text_content"]

    # ── References (Stage 2) ─────────────────────────────────────────
    reference_images:    list[ReferenceImage] = field(default_factory=list)

    # ── Source image (for edit/followup) ─────────────────────────────
    source_image_b64:    Optional[str]    = None
    source_image_url:    Optional[str]    = None

    # ── Model selection ──────────────────────────────────────────────
    preferred_models:    list[str]        = field(default_factory=list)
    # Ordered preference: ["qwen-image-edit", "flux2-pro"]

    fallback_models:     list[str]        = field(default_factory=list)
    # If preferred unavailable: ["flux1-kontext", "nano-banana-2"]

    # ── Params ───────────────────────────────────────────────────────
    generation_params:   GenerationParams = field(default_factory=GenerationParams)

    # ── Prompts (Stage 0-1) ──────────────────────────────────────────
    prompt_spec:         PromptSpec       = field(default_factory=PromptSpec)

    # ── Refinement (Stage 5) ─────────────────────────────────────────
    refinement_plan:     RefinementPlan   = field(default_factory=RefinementPlan)

    # ── Evaluation (Stage 6-7) ───────────────────────────────────────
    eval_result:         Optional[EvalResult] = None

    # ── Output targets ───────────────────────────────────────────────
    output_targets:      OutputTargets    = field(default_factory=OutputTargets)

    # ── Stage results (filled as pipeline progresses) ────────────────
    stage_results:       dict[str, StageResult] = field(default_factory=dict)

    # ── Run metadata (timing, costs, models) ─────────────────────────
    run_metadata:        RunMetadata      = field(default_factory=RunMetadata)

    # ── Final output ─────────────────────────────────────────────────
    final_image_b64:     Optional[str]    = None
    final_image_url:     Optional[str]    = None

    def __post_init__(self):
        # Sync job_id into run_metadata
        if not self.run_metadata.job_id:
            self.run_metadata.job_id = self.job_id
        if not self.run_metadata.session_id:
            self.run_metadata.session_id = self.session_id
        if not self.run_metadata.created_at:
            self.run_metadata.created_at = datetime.now(timezone.utc).isoformat()

    # ── Stage management ─────────────────────────────────────────────

    def init_stages(self) -> None:
        """Pre-populate stage_results for all pipeline stages."""
        for stage_name in PIPELINE_STAGES:
            if stage_name not in self.stage_results:
                self.stage_results[stage_name] = StageResult(stage=stage_name)

    def get_stage(self, name: str) -> StageResult:
        """Get or create a StageResult by name."""
        if name not in self.stage_results:
            self.stage_results[name] = StageResult(stage=name)
        return self.stage_results[name]

    def current_image(self) -> tuple[Optional[str], Optional[str]]:
        """
        Return (b64, url) of the latest image — walks stages in reverse
        to find the most recent non-None image output.
        """
        for stage_name in reversed(PIPELINE_STAGES):
            sr = self.stage_results.get(stage_name)
            if sr and (sr.image_b64 or sr.image_url):
                return sr.image_b64, sr.image_url
        return self.source_image_b64, self.source_image_url

    # ── Reference helpers ────────────────────────────────────────────

    def refs_by_role(self, role: ReferenceRole) -> list[ReferenceImage]:
        return [r for r in self.reference_images if r.role == role]

    @property
    def has_references(self) -> bool:
        return len(self.reference_images) > 0

    @property
    def is_edit(self) -> bool:
        return self.intent in ("edit", "followup")

    @property
    def needs_multi_ref(self) -> bool:
        return len(self.reference_images) > 1

    @property
    def needs_refinement(self) -> bool:
        return self.refinement_plan.has_targets

    # ── Serialization ────────────────────────────────────────────────

    def to_log_dict(self) -> dict:
        """Full serialization for experiment logging / metadata storage."""
        return {
            "job_id": self.job_id,
            "session_id": self.session_id,
            "status": self.status.value,
            "user_instruction": self.user_instruction,
            "language": self.language,
            "intent": self.intent,
            "must_keep": self.must_keep,
            "may_change": self.may_change,
            "forbidden_changes": self.forbidden_changes,
            "reference_count": len(self.reference_images),
            "references": [
                {"role": r.role.value, "label": r.label, "weight": r.weight}
                for r in self.reference_images
            ],
            "preferred_models": self.preferred_models,
            "fallback_models": self.fallback_models,
            "generation_params": {
                "width": self.generation_params.width,
                "height": self.generation_params.height,
                "steps": self.generation_params.steps,
                "guidance": self.generation_params.guidance,
                "strength": self.generation_params.strength,
                "seed": self.generation_params.seed,
                "style_preset": self.generation_params.style_preset,
            },
            "prompt_spec": self.prompt_spec.to_dict(),
            "eval": self.eval_result.to_log_dict() if self.eval_result else None,
            "run_metadata": self.run_metadata.to_log_dict(),
            "stages": {
                name: {
                    "status": sr.status.value,
                    "latency_ms": round(sr.latency_ms, 2),
                    "location": sr.location.value,
                    "has_image": sr.image_b64 is not None or sr.image_url is not None,
                    "error": sr.error,
                }
                for name, sr in self.stage_results.items()
            },
            "has_final_image": self.final_image_b64 is not None or self.final_image_url is not None,
        }
