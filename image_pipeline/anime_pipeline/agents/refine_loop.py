"""
RefineLoopAgent — Iterative critique-and-refine loop.

After each major pass the loop:
  1) Scores the generated image against the LayerPlan (critique_image).
  2) Decides whether another round is needed (decide_refine_action).
  3) Patches the prompt and control settings (patch_plan_from_critique).
  4) Runs the next refinement pass (run_refine_round).

All decisions are deterministic, stored as structured fields, and
fully debuggable.  No hidden reasoning is exposed.

Public functions (stateless, testable in isolation):
    critique_image          — score an image via CritiqueAgent
    decide_refine_action    — pure logic: scores → RefineDecision
    patch_plan_from_critique — pure logic: apply actions to PassConfig
    run_refine_round        — one round: patch → beauty → critique
"""

from __future__ import annotations

import copy
import logging
import random
import time
from dataclasses import replace
from typing import Optional

from ..config import AnimePipelineConfig, BeautyStrength, get_beauty_preset
from ..schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    ControlInput,
    CritiqueReport,
    PassConfig,
    RefineAction,
    RefineActionType,
    RefineDecision,
    StructureLayer,
)
from .critique import CritiqueAgent
from .beauty_pass import BeautyPassAgent

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════
# 1) critique_image
# ═══════════════════════════════════════════════════════════════════

def critique_image(
    job: AnimePipelineJob,
    config: AnimePipelineConfig,
) -> CritiqueReport:
    """Score the latest image on the job via CritiqueAgent.

    Returns the CritiqueReport (also appended to job.critique_results
    by the CritiqueAgent).
    """
    agent = CritiqueAgent(config)
    agent.execute(job)
    if job.critique_results:
        return job.critique_results[-1]
    # Fallback: no model succeeded — return neutral scores
    return CritiqueReport(
        anatomy_score=5, face_score=5, eye_consistency_score=5,
        hands_score=5, clothing_score=5, composition_score=5,
        color_score=5, style_score=5, background_score=5,
        accessories_score=5, pose_score=5,
        model_used="fallback",
    )


# ═══════════════════════════════════════════════════════════════════
# 2) decide_refine_action
# ═══════════════════════════════════════════════════════════════════

# Map dimension names → (score_attr, issue_attr, negative_tag_to_add)
_DIMENSION_FIX_MAP: dict[str, tuple[str, str, str]] = {
    "anatomy":              ("anatomy_score",          "anatomy_issues",      "bad anatomy"),
    "face_symmetry":        ("face_score",             "face_issues",         "asymmetrical face"),
    "eye_consistency":      ("eye_consistency_score",  "eye_issues",          "mismatched eyes"),
    "hand_quality":         ("hands_score",            "hand_issues",         "bad hands, extra fingers"),
    "clothing_consistency": ("clothing_score",         "clothing_issues",     "inconsistent clothing"),
    "style_drift":          ("style_score",            "style_drift",         "style inconsistency"),
    "color_drift":          ("color_score",            "color_issues",        "color mismatch"),
    "background_clutter":   ("background_score",       "background_issues",   "cluttered background"),
    "missing_accessories":  ("accessories_score",      "accessories_issues",  "missing details"),
    "pose_drift":           ("pose_score",             "pose_issues",         "wrong pose"),
}


def decide_refine_action(
    critique: CritiqueReport,
    round_num: int,
    config: AnimePipelineConfig,
) -> RefineDecision:
    """Pure-logic decision: should we refine, and how?

    Produces a deterministic RefineDecision based on dimension scores
    and configurable thresholds.  No IO, no side effects.
    """
    max_rounds = config.max_refine_rounds
    threshold = config.refine_score_threshold
    dim_thresholds = config.refine_dimension_thresholds

    # ── Stop conditions ───────────────────────────────────────────
    if round_num >= max_rounds:
        return RefineDecision(
            should_refine=False,
            reason=f"Max refine rounds reached ({max_rounds})",
        )

    if critique.overall_score >= threshold:
        return RefineDecision(
            should_refine=False,
            reason=f"Score {critique.overall_score:.1f} >= threshold {threshold}",
        )

    # ── Collect failing dimensions sorted worst-first ─────────────
    scores = critique.dimension_scores
    failing: list[tuple[str, int]] = []
    for dim_name, score in scores.items():
        t = dim_thresholds.get(dim_name, 5)
        if score < t:
            failing.append((dim_name, score))
    failing.sort(key=lambda x: x[1])

    if not failing:
        # Overall below threshold but no single dimension is critically bad
        return RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.ADJUST_DENOISE,
                target="denoise",
                value=config.refine_denoise_step_up,
                reason="Overall below threshold, slight denoise bump",
            )],
            reason=f"Score {critique.overall_score:.1f} < {threshold}, general boost",
            worst_dimensions=[],
        )

    worst_dims = [d for d, _ in failing]
    actions: list[RefineAction] = []

    # ── Check artifact accumulation ───────────────────────────────
    total_issues = len(critique.all_issues)
    if total_issues >= config.refine_artifact_accumulation_limit:
        actions.append(RefineAction(
            action_type=RefineActionType.SWITCH_PRESET,
            target="beauty_strength",
            value="subtle",
            reason=f"Artifact accumulation ({total_issues} issues) → switch to subtle",
        ))
        return RefineDecision(
            should_refine=True,
            actions=actions,
            reason=f"{total_issues} issues accumulated, switching to safer preset",
            worst_dimensions=worst_dims,
        )

    # ── Per-dimension fixes ───────────────────────────────────────
    needs_denoise_up = False
    needs_denoise_down = False
    needs_control_boost = False
    needs_control_reduce = False

    for dim_name, score in failing:
        fix_info = _DIMENSION_FIX_MAP.get(dim_name)
        if not fix_info:
            continue
        score_attr, issue_attr, neg_tag = fix_info

        # Always patch negative with dimension-specific tag
        actions.append(RefineAction(
            action_type=RefineActionType.PATCH_NEGATIVE,
            target="negative",
            value=neg_tag,
            reason=f"{dim_name} score {score} < {dim_thresholds.get(dim_name, 5)}",
        ))

        # Add positive prompt patches from the critique
        issues = getattr(critique, issue_attr, [])
        for issue_text in issues[:2]:  # limit to top 2 issues per dimension
            actions.append(RefineAction(
                action_type=RefineActionType.PATCH_POSITIVE,
                target="positive",
                value=issue_text,
                reason=f"Fix {dim_name}: {issue_text}",
            ))

        # Anatomy / hands / face / eye → bump denoise
        if dim_name in ("anatomy", "hand_quality", "face_symmetry", "eye_consistency"):
            needs_denoise_up = True

        # Pose / structure drift → strengthen controls
        if dim_name in ("pose_drift", "anatomy"):
            needs_control_boost = True

        # Style drift → reduce control (over-constrained)
        if dim_name == "style_drift":
            needs_control_reduce = True

        # Good composition + color → can lower denoise
        if dim_name in ("color_drift", "background_clutter") and score >= 6:
            needs_denoise_down = True

    # ── Denoise adjustment ────────────────────────────────────────
    if needs_denoise_up and not needs_denoise_down:
        actions.append(RefineAction(
            action_type=RefineActionType.ADJUST_DENOISE,
            target="denoise",
            value=config.refine_denoise_step_up,
            reason="Anatomy/face/hands issues → raise denoise",
        ))
    elif needs_denoise_down and not needs_denoise_up:
        actions.append(RefineAction(
            action_type=RefineActionType.ADJUST_DENOISE,
            target="denoise",
            value=-config.refine_denoise_step_down,
            reason="Minor color/bg issues only → lower denoise",
        ))

    # ── Control adjustments ───────────────────────────────────────
    if needs_control_boost and not needs_control_reduce:
        actions.append(RefineAction(
            action_type=RefineActionType.ADJUST_CONTROL,
            target="control_strength",
            value=config.refine_control_boost,
            reason="Pose/anatomy drift → strengthen controls",
        ))
    elif needs_control_reduce and not needs_control_boost:
        actions.append(RefineAction(
            action_type=RefineActionType.ADJUST_CONTROL,
            target="control_strength",
            value=-config.refine_control_reduce,
            reason="Style drift → relax controls",
        ))

    return RefineDecision(
        should_refine=True,
        actions=actions,
        reason=f"Score {critique.overall_score:.1f} < {threshold}, "
               f"failing: {', '.join(worst_dims)}",
        worst_dimensions=worst_dims,
    )


# ═══════════════════════════════════════════════════════════════════
# 3) patch_plan_from_critique
# ═══════════════════════════════════════════════════════════════════

def patch_plan_from_critique(
    pc: PassConfig,
    critique: CritiqueReport,
    decision: RefineDecision,
    config: AnimePipelineConfig,
) -> PassConfig:
    """Apply refine actions to a PassConfig.  Returns a new PassConfig.

    Pure function — no IO, no side effects.  The original pc is not mutated.
    """
    # Start from a shallow copy so we don't mutate the original
    new_denoise = pc.denoise
    new_positive = pc.positive_prompt
    new_negative = pc.negative_prompt
    new_controls = list(pc.control_inputs)  # shallow copy of list
    new_steps = pc.steps
    new_cfg = pc.cfg
    new_sampler = pc.sampler
    new_scheduler = pc.scheduler

    positive_additions: list[str] = []
    negative_additions: list[str] = []

    for action in decision.actions:
        if action.action_type == RefineActionType.ADJUST_DENOISE:
            delta = float(action.value)
            new_denoise = max(
                config.refine_denoise_floor,
                min(config.refine_denoise_ceiling, new_denoise + delta),
            )

        elif action.action_type == RefineActionType.ADJUST_CONTROL:
            delta = float(action.value)
            new_controls = [
                ControlInput(
                    layer_type=ci.layer_type,
                    controlnet_model=ci.controlnet_model,
                    strength=max(0.1, min(1.0, ci.strength + delta)),
                    start_percent=ci.start_percent,
                    end_percent=ci.end_percent,
                    preprocessor=ci.preprocessor,
                    image_b64=ci.image_b64,
                )
                for ci in new_controls
            ]

        elif action.action_type == RefineActionType.PATCH_POSITIVE:
            tag = str(action.value).strip()
            if tag and tag.lower() not in new_positive.lower():
                positive_additions.append(tag)

        elif action.action_type == RefineActionType.PATCH_NEGATIVE:
            tag = str(action.value).strip()
            if tag and tag.lower() not in new_negative.lower():
                negative_additions.append(tag)

        elif action.action_type == RefineActionType.SWITCH_PRESET:
            preset_name = str(action.value)
            try:
                preset = get_beauty_preset(preset_name)
                new_denoise = preset["denoise"]
                new_steps = preset["steps"]
                new_cfg = preset["cfg"]
            except (ValueError, KeyError):
                logger.warning("[RefineLoop] Unknown preset: %s", preset_name)

    # Apply prompt patches
    if positive_additions:
        new_positive = new_positive + ", " + ", ".join(positive_additions)
    if negative_additions:
        new_negative = new_negative + ", " + ", ".join(negative_additions)

    # Also apply critique's own prompt_patch suggestions
    for tag in critique.prompt_patch:
        tag = tag.strip()
        if tag and tag.lower() not in new_positive.lower():
            new_positive = new_positive + ", " + tag

    # Apply critique's control_patch (dimension → strength delta)
    for layer_type, delta in critique.control_patch.items():
        for i, ci in enumerate(new_controls):
            if ci.layer_type == layer_type:
                new_controls[i] = ControlInput(
                    layer_type=ci.layer_type,
                    controlnet_model=ci.controlnet_model,
                    strength=max(0.1, min(1.0, ci.strength + delta)),
                    start_percent=ci.start_percent,
                    end_percent=ci.end_percent,
                    preprocessor=ci.preprocessor,
                    image_b64=ci.image_b64,
                )

    return PassConfig(
        pass_name=pc.pass_name,
        model_slot=pc.model_slot,
        checkpoint=pc.checkpoint,
        width=pc.width,
        height=pc.height,
        sampler=new_sampler,
        scheduler=new_scheduler,
        steps=new_steps,
        cfg=new_cfg,
        denoise=new_denoise,
        seed=pc.seed,
        positive_prompt=new_positive,
        negative_prompt=new_negative,
        control_inputs=new_controls,
        prompt_strategy=pc.prompt_strategy,
        expected_output=pc.expected_output,
        source_image_b64=pc.source_image_b64,
        lora_models=pc.lora_models,
    )


# ═══════════════════════════════════════════════════════════════════
# 4) run_refine_round
# ═══════════════════════════════════════════════════════════════════

def run_refine_round(
    job: AnimePipelineJob,
    config: AnimePipelineConfig,
    round_num: int,
    beauty_agent: BeautyPassAgent,
    critique_agent: CritiqueAgent,
    last_critique: CritiqueReport,
    beauty_pc: PassConfig,
) -> tuple[AnimePipelineJob, CritiqueReport, PassConfig]:
    """Execute one refine round: decide → patch → beauty → critique.

    Returns:
        (job, new_critique, patched_pc) — the job is mutated in place,
        new critique appended to job.critique_results.
    """
    t0 = time.time()
    job.status = AnimePipelineStatus.REFINING

    # 1) Decide
    decision = decide_refine_action(last_critique, round_num, config)

    if not decision.should_refine:
        logger.info(
            "[RefineLoop] Round %d: no refine needed — %s",
            round_num, decision.reason,
        )
        return job, last_critique, beauty_pc

    logger.info(
        "[RefineLoop] Round %d: refining — %s (%d actions)",
        round_num, decision.reason, len(decision.actions),
    )

    # 2) Patch
    patched_pc = patch_plan_from_critique(beauty_pc, last_critique, decision, config)

    # 3) Beauty pass with patched config
    # Get source image (latest beauty output or cleanup)
    source_b64 = _get_latest_beauty_image(job)
    if not source_b64:
        job.error = "No source image for refine round"
        job.status = AnimePipelineStatus.FAILED
        return job, last_critique, beauty_pc

    # Resolve seed — use a new seed for diversity on refine
    seed = random.randint(0, 2**32 - 1)

    clip_skip = config.final_model.clip_skip

    workflow = beauty_agent._builder.build_beauty(
        patched_pc, source_b64, seed, clip_skip=clip_skip,
    )

    result = beauty_agent._client.submit_workflow(
        workflow, job_id=job.job_id, pass_name=f"beauty_refine_{round_num}",
    )

    if not result.success:
        logger.error(
            "[RefineLoop] Round %d beauty failed: %s", round_num, result.error,
        )
        job.error = f"Refine round {round_num} failed: {result.error}"
        job.status = AnimePipelineStatus.FAILED
        return job, last_critique, patched_pc

    if not result.images_b64:
        job.error = f"Refine round {round_num} produced no image"
        job.status = AnimePipelineStatus.FAILED
        return job, last_critique, patched_pc

    image_b64 = result.images_b64[0]
    job.add_intermediate(
        f"refine_round_{round_num}", image_b64,
        seed=seed,
        checkpoint=patched_pc.checkpoint,
        denoise=patched_pc.denoise,
        round=round_num,
        actions=[a.to_dict() for a in decision.actions],
        duration_ms=result.duration_ms,
    )
    job.refine_rounds = round_num

    # 4) Critique the new output
    critique_agent.execute(job)
    new_critique = (
        job.critique_results[-1]
        if job.critique_results
        else CritiqueReport(model_used="fallback")
    )

    latency = (time.time() - t0) * 1000
    job.mark_stage(f"refine_round_{round_num}", latency)

    logger.info(
        "[RefineLoop] Round %d done in %.0fms: score %.1f → %.1f, "
        "%d actions applied",
        round_num, latency,
        last_critique.overall_score, new_critique.overall_score,
        len(decision.actions),
    )

    return job, new_critique, patched_pc


def _get_latest_beauty_image(job: AnimePipelineJob) -> Optional[str]:
    """Get the latest beauty/refine image from job intermediates."""
    for img in reversed(job.intermediates):
        if img.stage.startswith("refine_round_") or img.stage == "beauty_pass":
            return img.image_b64
    for img in reversed(job.intermediates):
        if img.stage == "cleanup_pass":
            return img.image_b64
    return None


# ═══════════════════════════════════════════════════════════════════
# RefineLoopAgent — orchestrator-level wrapper
# ═══════════════════════════════════════════════════════════════════

class RefineLoopAgent:
    """Run the full critique→refine loop after beauty pass.

    Integrates with the orchestrator by accepting a job that already
    has a beauty pass output.  Runs up to max_refine_rounds of
    critique + conditional refinement.
    """

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._beauty = BeautyPassAgent(config)
        self._critique = CritiqueAgent(config)

    def execute(self, job: AnimePipelineJob) -> AnimePipelineJob:
        """Run critique→refine loop until quality passes or rounds exhausted.

        Expects job to have at least one beauty_pass intermediate.
        """
        if not job.layer_plan or not job.layer_plan.beauty_pass:
            job.error = "No layer plan / beauty pass for refine loop"
            job.status = AnimePipelineStatus.FAILED
            return job

        beauty_pc = job.layer_plan.beauty_pass
        max_rounds = self._config.max_refine_rounds
        best_score = 0.0
        best_image_b64 = None

        # Initial critique of the beauty pass output
        self._critique.execute(job)
        if not job.critique_results:
            logger.warning("[RefineLoop] Initial critique produced no result")
            return job

        last_critique = job.critique_results[-1]
        best_score = last_critique.overall_score

        # Track best image
        for img in reversed(job.intermediates):
            if img.stage == "beauty_pass":
                best_image_b64 = img.image_b64
                break

        # Refine loop
        for round_num in range(1, max_rounds + 1):
            decision = decide_refine_action(last_critique, round_num, self._config)

            if not decision.should_refine:
                logger.info(
                    "[RefineLoop] Stopping at round %d: %s",
                    round_num, decision.reason,
                )
                break

            job, last_critique, beauty_pc = run_refine_round(
                job, self._config, round_num,
                self._beauty, self._critique,
                last_critique, beauty_pc,
            )

            if job.status == AnimePipelineStatus.FAILED:
                break

            # Track best
            if last_critique.overall_score > best_score:
                best_score = last_critique.overall_score
                for img in reversed(job.intermediates):
                    if img.stage.startswith("refine_round_"):
                        best_image_b64 = img.image_b64
                        break

            if last_critique.passed:
                logger.info(
                    "[RefineLoop] Passed on round %d (score=%.1f)",
                    round_num, last_critique.overall_score,
                )
                break

        # Use best image as final if nothing better came along
        if self._config.return_best_on_fail and best_image_b64:
            if not job.final_image_b64:
                job.final_image_b64 = best_image_b64

        return job
