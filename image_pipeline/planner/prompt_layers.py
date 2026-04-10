"""
image_pipeline.planner.prompt_layers — 6-layer internal prompt transformation engine.

Converts natural-language user input into structured, stage-specific prompts
that each model in the pipeline can consume without ambiguity.

Layers (§14 expanded):
    1. Planning        — parse intent, constraints, identity anchors
    2. Execution       — model-ready generation/edit prompt
    3. Composition     — multi-reference assembly directive
    4. Refinement      — targeted regional fix
    5. Correction      — re-run after evaluation failure
    6. Verification    — evaluation judge instruction

Design rules (§14):
    - Prompt describes ONLY what needs to change (not the full image when refs exist)
    - Identity constraints and change instructions are always separated
    - Regional edits produce region-scoped prompts only
    - No redundant description if a reference image already carries that info
    - must_keep / may_change / forbidden_changes are always explicit
"""

from __future__ import annotations

import logging
import re
import textwrap
from typing import Optional

from image_pipeline.job_schema import (
    ImageJob,
    PromptSpec,
    ReferenceImage,
    ReferenceRole,
    RefinementTarget,
    EvalDimension,
)

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════
# Constants
# ═════════════════════════════════════════════════════════════════════

# Vietnamese → English visual vocabulary (fast, no API cost)
_VI_TO_EN: list[tuple[str, str]] = [
    # Hair
    (r"\btóc hồng\b",  "pink hair"),   (r"\btóc vàng\b",  "blonde hair"),
    (r"\btóc đen\b",   "black hair"),  (r"\btóc trắng\b", "white hair"),
    (r"\btóc xanh\b",  "blue hair"),   (r"\btóc đỏ\b",    "red hair"),
    (r"\btóc nâu\b",   "brown hair"),  (r"\btóc bạc\b",   "silver hair"),
    # Subjects
    (r"\bcô gái\b",                "girl"),
    (r"\bcậu bé\b|\bchàng trai\b", "young man"),
    (r"\bngười phụ nữ\b",         "woman"),
    (r"\bngười đàn ông\b",        "man"),
    (r"\bcon mèo\b",  "cat"),    (r"\bcon chó\b",  "dog"),
    (r"\bcon rồng\b", "dragon"), (r"\bcon ngựa\b", "horse"),
    # Settings
    (r"\bthành phố\b",              "city"),
    (r"\bbiển\b|\bbãi biển\b",      "beach"),
    (r"\bnúi\b",                    "mountains"),
    (r"\brừng\b",                   "forest"),
    (r"\bvũ trụ\b",                 "outer space"),
    # Actions
    (r"\bngồi\b", "sitting"), (r"\bđứng\b", "standing"),
    (r"\bchạy\b", "running"), (r"\bbay\b",   "flying"),
    # Lighting
    (r"\bánh trăng\b", "moonlight"),  (r"\bhoàng hôn\b", "sunset"),
    (r"\bbình minh\b", "sunrise"),    (r"\bban đêm\b",   "night"),
]

# Style preset prompt fragments (compatible with existing PromptBuilder)
STYLE_FRAGMENTS: dict[str, str] = {
    "photorealistic": "photorealistic, DSLR quality, natural lighting, 8K resolution",
    "anime":          "anime art style, vibrant colors, clean linework",
    "cinematic":      "cinematic composition, dramatic lighting, film grain",
    "watercolor":     "watercolor painting, soft washes, paper texture",
    "digital_art":    "digital art, artstation trending, concept art, highly detailed",
    "oil_painting":   "oil painting, rich impasto texture, classical composition",
    "sketch":         "pencil sketch, detailed cross-hatching, graphite on paper",
    "3d_render":      "3D render, octane render, ray tracing, PBR materials",
    "fantasy":        "fantasy art, magical atmosphere, ethereal glow",
    "studio_photo":   "professional studio photography, softbox lighting",
}

QUALITY_FRAGMENTS: dict[str, str] = {
    "quality": "highly detailed, sharp focus, 4K, masterpiece",
    "fast":    "simple composition, clean, well-lit",
    "auto":    "highly detailed, sharp focus",
}

_UNIVERSAL_NEGATIVE = (
    "blurry, low quality, pixelated, distorted, deformed, "
    "ugly, bad anatomy, watermark, signature"
)


def _translate_vi(text: str) -> str:
    """Rule-based Vietnamese → English for common visual words."""
    for pattern, repl in _VI_TO_EN:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def _trim(text: str, max_words: int) -> str:
    """Trim prompt to word budget, cutting at last comma boundary."""
    words = text.split()
    if len(words) <= max_words:
        return text
    trimmed = " ".join(words[:max_words])
    last_comma = trimmed.rfind(",")
    if last_comma > len(trimmed) * 0.7:
        trimmed = trimmed[:last_comma]
    return trimmed.strip(", ")


def _format_constraints(job: ImageJob) -> str:
    """Render must_keep / may_change / forbidden as a compact block."""
    parts: list[str] = []
    if job.must_keep:
        parts.append(f"KEEP: {', '.join(job.must_keep)}")
    if job.may_change:
        parts.append(f"CHANGE: {', '.join(job.may_change)}")
    if job.forbidden_changes:
        parts.append(f"FORBID: {', '.join(job.forbidden_changes)}")
    return " | ".join(parts)


def _format_ref_summary(refs: list[ReferenceImage]) -> str:
    """One-line summary of tagged references."""
    if not refs:
        return ""
    parts = []
    for i, ref in enumerate(refs):
        parts.append(f"ref_{i}={ref.role.value}(w={ref.weight})")
    return "REFS: " + ", ".join(parts)


# ═════════════════════════════════════════════════════════════════════
# Template functions — one per layer
# ═════════════════════════════════════════════════════════════════════

# ─────────────────────────────────────────────────────────────────────
# LAYER 1 — Planning prompt
# ─────────────────────────────────────────────────────────────────────

_PLANNING_TEMPLATE = textwrap.dedent("""\
    [PLANNING]
    User says: {instruction}
    Language: {language}
    Intent: {intent}
    Session turn: {turn_number}
    {constraints}
    {ref_summary}
    {source_note}
    {lineage_note}

    Task: Parse the user instruction into structured constraints.
    Determine what must be preserved, what may change, and what is forbidden.
    If the instruction is ambiguous, pick the most likely visual interpretation.
    Output a brief JSON plan with keys: subject, action, background, lighting,
    mood, style, must_keep, may_change, forbidden, edit_operations.
""")


def build_planning_prompt(job: ImageJob) -> str:
    """
    Layer 1 — Internal planning prompt.
    Used by the planner/LLM to parse intent and extract constraints.
    NOT sent to any image model.
    """
    instruction = job.user_instruction
    if job.language.startswith("vi"):
        instruction = _translate_vi(instruction)

    turn_number = len(job.prompt_spec.prompt_lineage) + 1
    constraints = _format_constraints(job)
    ref_summary = _format_ref_summary(job.reference_images)

    source_note = ""
    if job.source_image_b64 or job.source_image_url:
        source_note = "Source image: YES (edit/followup mode)"

    lineage_note = ""
    if job.prompt_spec.prompt_lineage:
        last = job.prompt_spec.prompt_lineage[-1]
        lineage_note = f"Previous prompt: {_trim(last, 40)}"

    return _PLANNING_TEMPLATE.format(
        instruction=instruction,
        language=job.language,
        intent=job.intent or "unknown",
        turn_number=turn_number,
        constraints=constraints or "CONSTRAINTS: (none extracted yet)",
        ref_summary=ref_summary or "REFS: none",
        source_note=source_note,
        lineage_note=lineage_note,
    ).strip()


# ─────────────────────────────────────────────────────────────────────
# LAYER 2 — Semantic execution prompt
# ─────────────────────────────────────────────────────────────────────

def build_execution_prompt(job: ImageJob) -> str:
    """
    Layer 2 — The prompt sent to the primary gen/edit model
    (Qwen-Image-Edit, FLUX.2, etc.).

    Rules (§14):
    - Only describe what needs to change; refs carry identity
    - Separate identity anchors from change instructions
    - Keep under max_tokens_execution words
    """
    parts: list[str] = []
    params = job.generation_params
    spec = job.prompt_spec

    # ── 1. Instruction core ──────────────────────────────────────────
    instruction = job.user_instruction
    if job.language.startswith("vi"):
        instruction = _translate_vi(instruction)

    if job.is_edit and spec.change_instructions:
        # Edit mode: only state the changes, not the full scene
        parts.append(", ".join(spec.change_instructions))
    else:
        parts.append(instruction)

    # ── 2. Identity anchors (things refs already carry) ──────────────
    if spec.identity_anchors:
        parts.append("maintain: " + ", ".join(spec.identity_anchors))

    # ── 3. Style ─────────────────────────────────────────────────────
    style = params.style_preset
    if style and style in STYLE_FRAGMENTS:
        parts.append(STYLE_FRAGMENTS[style])
    if spec.style_tags:
        parts.extend(spec.style_tags)

    # ── 4. Quality ───────────────────────────────────────────────────
    quality_key = "auto"
    if spec.quality_tags:
        quality_key = spec.quality_tags[0] if spec.quality_tags[0] in QUALITY_FRAGMENTS else "auto"
    parts.append(QUALITY_FRAGMENTS.get(quality_key, QUALITY_FRAGMENTS["auto"]))

    # ── 5. Assemble + trim ───────────────────────────────────────────
    prompt = ", ".join(p.strip(", ") for p in parts if p.strip())
    return _trim(prompt, spec.max_tokens_execution)


# ─────────────────────────────────────────────────────────────────────
# LAYER 3 — Multi-reference composition prompt
# ─────────────────────────────────────────────────────────────────────

_COMPOSITION_TEMPLATE = textwrap.dedent("""\
    Compose a single image from multiple reference sources.
    {instruction}

    Reference assignments:
    {ref_assignments}

    Constraints:
    {constraints}

    Style: {style}
    Quality: {quality}
    Dimensions: {width}x{height}
""")


def build_composition_prompt(job: ImageJob) -> str:
    """
    Layer 3 — Directive for FLUX.2 [pro/max] multi-reference composition.
    Explicitly maps each reference to its role so the model knows
    which image supplies face, outfit, background, etc.
    """
    if not job.has_references:
        return build_execution_prompt(job)

    instruction = job.user_instruction
    if job.language.startswith("vi"):
        instruction = _translate_vi(instruction)

    # Build per-ref assignment lines
    assignment_lines: list[str] = []
    for i, ref in enumerate(job.reference_images):
        label = ref.label or ref.role.value
        weight_note = f" (weight={ref.weight})" if ref.weight != 1.0 else ""
        crop_note = f" [crop={ref.crop_region}]" if ref.crop_region else ""
        assignment_lines.append(
            f"  ref_{i}: role={ref.role.value}, source=\"{label}\"{weight_note}{crop_note}"
        )
    ref_assignments = "\n".join(assignment_lines)

    constraints = _format_constraints(job) or "none specified"
    style = job.generation_params.style_preset or "auto"
    quality = "quality" if job.prompt_spec.quality_tags else "auto"

    return _COMPOSITION_TEMPLATE.format(
        instruction=instruction,
        ref_assignments=ref_assignments,
        constraints=constraints,
        style=style,
        quality=quality,
        width=job.generation_params.width,
        height=job.generation_params.height,
    ).strip()


# ─────────────────────────────────────────────────────────────────────
# LAYER 4 — Refinement prompt
# ─────────────────────────────────────────────────────────────────────

_REFINEMENT_TEMPLATE = textwrap.dedent("""\
    Fix the following region: {region}
    Strategy: {strategy}
    {region_prompt}
    {identity_note}
    Keep everything else unchanged.
""")


def build_refinement_prompt(
    job: ImageJob,
    target: RefinementTarget,
) -> str:
    """
    Layer 4 — Region-scoped prompt for Fill/ADetailer/IP-Adapter.
    Only describes the target region; the rest of the image is frozen.

    Rule (§14): When fixing locally, prompt talks ONLY about that region.
    """
    region_prompt = target.prompt
    if not region_prompt:
        # Auto-generate from target region
        region_prompt = _auto_refinement_prompt(target.region, job)

    if job.language.startswith("vi"):
        region_prompt = _translate_vi(region_prompt)

    identity_note = ""
    if job.prompt_spec.identity_anchors:
        identity_note = "Preserve identity: " + ", ".join(job.prompt_spec.identity_anchors)

    prompt = _REFINEMENT_TEMPLATE.format(
        region=target.region,
        strategy=target.strategy.value,
        region_prompt=region_prompt,
        identity_note=identity_note,
    ).strip()

    return _trim(prompt, job.prompt_spec.max_tokens_refinement)


def _auto_refinement_prompt(region: str, job: ImageJob) -> str:
    """Generate reasonable default refinement instructions per region."""
    defaults: dict[str, str] = {
        "face":       "fix facial features, correct eye symmetry, natural skin texture",
        "hands":      "fix hand anatomy, correct finger count, natural hand pose",
        "eyes":       "fix eye detail, correct iris shape, natural reflection",
        "text":       "sharpen text rendering, crisp legible characters",
        "fingers":    "correct finger anatomy, five fingers per hand, natural joints",
        "accessories": "fix accessory details, clean edges, proper proportions",
        "background": "fix background consistency, clean transitions, proper perspective",
        "full":       "overall detail improvement, fix any visible artifacts",
    }
    base = defaults.get(region, f"fix {region} details, improve quality")

    # Add style context from the job
    style = job.generation_params.style_preset
    if style and style in STYLE_FRAGMENTS:
        base += f", {style} style"

    return base


# ─────────────────────────────────────────────────────────────────────
# LAYER 5 — Correction prompt
# ─────────────────────────────────────────────────────────────────────

_CORRECTION_TEMPLATE = textwrap.dedent("""\
    The previous output failed evaluation on: {failed_dims}.
    Original instruction: {instruction}

    Correction targets: {targets}
    Correction strategy: {strategy}

    {constraints}
    {identity_note}

    Fix ONLY the failing aspects. Do not alter passing elements.
    {judge_feedback}
""")


def build_correction_prompt(
    job: ImageJob,
    failed_dimensions: list[str],
    correction_targets: list[str],
    correction_strategy: str = "semantic",
    judge_feedback: Optional[dict[str, str]] = None,
) -> str:
    """
    Layer 5 — Re-generation prompt after evaluation failure.

    Uses the evaluator's feedback to target specific deficiencies.
    Only re-states what needs fixing; everything else stays locked.
    """
    instruction = job.user_instruction
    if job.language.startswith("vi"):
        instruction = _translate_vi(instruction)

    constraints = _format_constraints(job) or "no constraints"

    identity_note = ""
    if job.prompt_spec.identity_anchors:
        identity_note = "PRESERVE identity: " + ", ".join(job.prompt_spec.identity_anchors)

    feedback_text = ""
    if judge_feedback:
        feedback_lines = []
        for dim, reason in judge_feedback.items():
            if dim in failed_dimensions:
                feedback_lines.append(f"  - {dim}: {reason}")
        if feedback_lines:
            feedback_text = "Judge feedback:\n" + "\n".join(feedback_lines)

    return _CORRECTION_TEMPLATE.format(
        failed_dims=", ".join(failed_dimensions),
        instruction=_trim(instruction, 60),
        targets=", ".join(correction_targets) if correction_targets else "general",
        strategy=correction_strategy,
        constraints=constraints,
        identity_note=identity_note,
        judge_feedback=feedback_text,
    ).strip()


# ─────────────────────────────────────────────────────────────────────
# LAYER 6 — Verification prompt (evaluation judge instruction)
# ─────────────────────────────────────────────────────────────────────

_VERIFICATION_TEMPLATE = textwrap.dedent("""\
    You are an image quality evaluator for a Nano Banana-like image generation system.
    Score the generated image on each applicable dimension (0.0–1.0).

    Original user instruction: {instruction}
    Intent: {intent}
    {constraints}
    {ref_note}
    {turn_note}

    Evaluate these dimensions:
    {dimensions}

    For each dimension, output:
    - dimension_name: score (0.0–1.0)
    - reasoning: one sentence explaining the score

    Scoring guidelines:
    - instruction_adherence: Does the image match what the user asked for?
    - semantic_edit_accuracy: For edits — did only the requested part change?
    - identity_consistency: Do faces/characters match references or previous turn?
    - multi_ref_quality: Are all referenced elements (face/outfit/bg) properly composed?
    - detail_handling: Are hands, eyes, fingers, accessories anatomically correct?
    - text_rendering: Is any text in the image legible and correctly spelled?
    - multi_turn_stability: Does this output stay consistent with the edit chain?
    - correction_success: If this is a correction round — did it fix the flagged issues?

    Be strict. A score of 0.7 means "acceptable". Above 0.9 means excellent.
    If a dimension does not apply to this job, skip it.
""")

# Which dimensions apply per intent type
_DIMENSIONS_BY_INTENT: dict[str, list[str]] = {
    "generate": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.DETAIL_HANDLING,
        EvalDimension.TEXT_RENDERING,
    ],
    "edit": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.SEMANTIC_EDIT,
        EvalDimension.IDENTITY_CONSISTENCY,
        EvalDimension.DETAIL_HANDLING,
        EvalDimension.TEXT_RENDERING,
    ],
    "followup": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.SEMANTIC_EDIT,
        EvalDimension.IDENTITY_CONSISTENCY,
        EvalDimension.MULTI_TURN_STABILITY,
        EvalDimension.DETAIL_HANDLING,
    ],
    "multi_ref": [
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.MULTI_REF_QUALITY,
        EvalDimension.IDENTITY_CONSISTENCY,
        EvalDimension.DETAIL_HANDLING,
    ],
    "correction": [
        EvalDimension.CORRECTION_SUCCESS,
        EvalDimension.INSTRUCTION_ADHERENCE,
        EvalDimension.IDENTITY_CONSISTENCY,
    ],
}


def build_verification_prompt(
    job: ImageJob,
    override_dimensions: Optional[list[str]] = None,
) -> str:
    """
    Layer 6 — Instruction sent to the LLM-as-judge (Qwen2.5-VL / GPT-4o).
    Tells the judge what to score and how.
    Automatically selects applicable dimensions based on job intent.
    """
    instruction = job.user_instruction
    if job.language.startswith("vi"):
        instruction = _translate_vi(instruction)

    # Determine which dimensions apply
    intent_key = job.intent or "generate"
    if job.needs_multi_ref:
        intent_key = "multi_ref"
    if job.refinement_plan.current_round > 0:
        intent_key = "correction"

    applicable_dims = override_dimensions or _DIMENSIONS_BY_INTENT.get(
        intent_key, _DIMENSIONS_BY_INTENT["generate"]
    )

    dim_lines = []
    for dim in applicable_dims:
        dim_name = dim.value if hasattr(dim, "value") else dim
        threshold = job.eval_result.thresholds.get(dim_name, 0.7) if job.eval_result else 0.7
        dim_lines.append(f"  - {dim_name} (threshold={threshold})")
    dimensions_text = "\n".join(dim_lines)

    constraints = _format_constraints(job) or "none"

    ref_note = ""
    if job.has_references:
        ref_note = _format_ref_summary(job.reference_images)

    turn_note = ""
    lineage_len = len(job.prompt_spec.prompt_lineage)
    if lineage_len > 0:
        turn_note = f"This is turn {lineage_len + 1} in an edit chain."

    return _VERIFICATION_TEMPLATE.format(
        instruction=instruction,
        intent=intent_key,
        constraints=constraints,
        ref_note=ref_note,
        turn_note=turn_note,
        dimensions=dimensions_text,
    ).strip()


# ═════════════════════════════════════════════════════════════════════
# Negative prompt builder
# ═════════════════════════════════════════════════════════════════════

def build_negative_prompt(job: ImageJob) -> str:
    """
    Build the negative prompt from job state.
    Keeps 'text' in negative UNLESS the user wants text in image.
    Adds style-conflict negatives.
    """
    parts: list[str] = []

    # User-specified negatives
    if job.generation_params.negative_prompt:
        parts.append(job.generation_params.negative_prompt)

    # Universal negatives (minus text-related if text is wanted)
    universal = _UNIVERSAL_NEGATIVE
    wants_text = any("text" in c.lower() for c in job.may_change) or \
                 "text_rendering" in (job.prompt_spec.quality_tags or [])
    if wants_text:
        universal = universal.replace("watermark, signature", "").replace("  ", " ")
    parts.append(universal)

    # Style-conflict negatives
    style = job.generation_params.style_preset or ""
    _STYLE_CONFLICTS: dict[str, str] = {
        "anime":          "realistic, photorealistic, photograph, 3d render",
        "photorealistic":  "cartoon, anime, illustration, painting, sketch",
        "sketch":          "color, painted, photo, photorealistic",
        "3d_render":       "flat 2d, cartoon, anime, sketch",
        "pixel_art":       "smooth gradients, photorealistic, blurry",
    }
    if style in _STYLE_CONFLICTS:
        parts.append(_STYLE_CONFLICTS[style])

    return ", ".join(p.strip(", ") for p in parts if p.strip())


# ═════════════════════════════════════════════════════════════════════
# PromptLayerEngine — unified interface
# ═════════════════════════════════════════════════════════════════════

class PromptLayerEngine:
    """
    Stateless engine that fills all prompt layers on an ImageJob.

    Usage:
        engine = PromptLayerEngine()
        engine.fill_planning(job)        # Layer 1
        engine.fill_execution(job)       # Layer 2
        engine.fill_composition(job)     # Layer 3 (only if multi-ref)
        engine.fill_refinement(job, t)   # Layer 4 (per target)
        engine.fill_correction(job, ...) # Layer 5 (after eval fail)
        engine.fill_verification(job)    # Layer 6 (for judge)

    Each method mutates job.prompt_spec in place and returns the prompt string.
    """

    def fill_planning(self, job: ImageJob) -> str:
        """Stage 0-1: Parse intent and constraints."""
        prompt = build_planning_prompt(job)
        job.prompt_spec.planning_prompt = prompt
        job.prompt_spec.original_instruction = job.user_instruction
        job.prompt_spec.language = job.language
        logger.debug("[PromptLayer] Planning prompt: %d chars", len(prompt))
        return prompt

    def fill_execution(self, job: ImageJob) -> str:
        """Stage 3: Build model-ready generation/edit prompt."""
        prompt = build_execution_prompt(job)
        job.prompt_spec.execution_prompt = prompt
        job.prompt_spec.negative_prompt = build_negative_prompt(job)

        # Track lineage
        if prompt and prompt not in job.prompt_spec.prompt_lineage:
            job.prompt_spec.prompt_lineage.append(prompt)

        logger.debug("[PromptLayer] Execution prompt: %d chars", len(prompt))
        return prompt

    def fill_composition(self, job: ImageJob) -> str:
        """Stage 4: Build multi-reference composition directive."""
        prompt = build_composition_prompt(job)
        # Composition uses execution_prompt slot (it IS the execution for this stage)
        job.prompt_spec.execution_prompt = prompt
        logger.debug("[PromptLayer] Composition prompt: %d chars", len(prompt))
        return prompt

    def fill_refinement(self, job: ImageJob, target: RefinementTarget) -> str:
        """Stage 5: Build region-scoped refinement prompt."""
        prompt = build_refinement_prompt(job, target)
        job.prompt_spec.refinement_prompt = prompt
        logger.debug("[PromptLayer] Refinement prompt for %s: %d chars", target.region, len(prompt))
        return prompt

    def fill_correction(
        self,
        job: ImageJob,
        failed_dimensions: list[str],
        correction_targets: list[str],
        correction_strategy: str = "semantic",
        judge_feedback: Optional[dict[str, str]] = None,
    ) -> str:
        """Stage 7: Build correction prompt after eval failure."""
        prompt = build_correction_prompt(
            job, failed_dimensions, correction_targets,
            correction_strategy, judge_feedback,
        )
        job.prompt_spec.correction_prompt = prompt
        logger.debug("[PromptLayer] Correction prompt: %d chars", len(prompt))
        return prompt

    def fill_verification(
        self,
        job: ImageJob,
        override_dimensions: Optional[list[str]] = None,
    ) -> str:
        """Stage 6: Build evaluation judge instruction."""
        prompt = build_verification_prompt(job, override_dimensions)
        logger.debug("[PromptLayer] Verification prompt: %d chars", len(prompt))
        return prompt

    def fill_all_pre_generation(self, job: ImageJob) -> PromptSpec:
        """
        Convenience: fill layers 1+2 (or 1+3 if multi-ref) in one call.
        Returns the updated PromptSpec.
        """
        self.fill_planning(job)
        if job.needs_multi_ref:
            self.fill_composition(job)
        else:
            self.fill_execution(job)
        return job.prompt_spec
