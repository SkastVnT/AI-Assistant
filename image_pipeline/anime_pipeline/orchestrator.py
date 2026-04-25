"""
image_pipeline.anime_pipeline.orchestrator — Multi-pass anime pipeline controller.

Chains 7 agents sequentially, handles the critique→refine loop,
streams SSE events per stage, and manages error recovery.

Usage:
    orchestrator = AnimePipelineOrchestrator()
    job = AnimePipelineJob(user_prompt="anime girl in cherry blossoms")

    # Blocking run
    result = orchestrator.run(job)

    # Streaming run (yields SSE-ready dicts)
    for event in orchestrator.run_stream(job):
        send_sse(event)
"""

from __future__ import annotations

import copy
import logging
import os
import random
import re
import time
from pathlib import Path
from typing import Any, Generator, Optional

from .config import AnimePipelineConfig, load_config
from .schemas import AnimePipelineJob, AnimePipelineStatus
from .vram_manager import free_models_between_passes, log_pass_memory_mode
from .agents.vision_analyst import VisionAnalystAgent
from .agents.layer_planner import LayerPlannerAgent
from .agents.composition_pass import CompositionPassAgent
from .agents.structure_lock import StructureLockAgent
from .agents.beauty_pass import BeautyPassAgent
from .agents.critique import CritiqueAgent
from .agents.upscale import UpscaleAgent
from .agents.detection_inpaint import DetectionInpaintAgent
from .agents.final_ranker import FinalRanker
from .agents.output_manifest import build_output_manifest
from .result_store import ResultStore
from .layer_painter import (
    EyeBBox,
    EyeFXSpec,
    apply_artistic_layers,
)
from .character_research import (
    research_character,
    CharacterResearchResult,
)
from .character_parser import parse_character_identity
from .lora_manager import (
    find_and_verify_character_lora,
    LoRAVerificationResult,
    get_cached_character_lora,
    lora_file_exists,
)

logger = logging.getLogger(__name__)


def _is_cancel_requested(job_id: str) -> bool:
    """Best-effort check of the chatbot job queue's cancel flag.

    Returns ``False`` when the chatbot service is not importable
    (e.g. when this orchestrator is exercised from a test or a
    standalone script without the Flask process). Any error is
    swallowed so the pipeline never fails just because the queue
    is unreachable.
    """
    if not job_id:
        return False
    try:
        from core.job_queue import get_queue  # type: ignore[import-not-found]
        return bool(get_queue().is_cancel_requested(job_id))
    except Exception:
        return False


def _pipeline_enabled() -> bool:
    """Check IMAGE_PIPELINE_V2 feature flag."""
    flag = os.getenv("IMAGE_PIPELINE_V2", "").lower()
    return flag in ("1", "true", "yes", "on")


def _eye_fx_from_meta(meta: Any) -> EyeFXSpec:
    """Parse ``job.metadata['eye_fx']`` (dict) into a typed :class:`EyeFXSpec`.

    ``meta`` may be ``None`` (no override) or a dict like::

        {
          "eye_rolling": True,
          "rolling_direction": "up",
          "rolling_strength": 0.55,
          "bloodshot": True,
          "bloodshot_intensity": 0.65,
        }
    """
    if not isinstance(meta, dict):
        return EyeFXSpec()
    try:
        return EyeFXSpec(
            eye_rolling=bool(meta.get("eye_rolling", False)),
            rolling_direction=str(meta.get("rolling_direction", "up")),
            rolling_strength=float(meta.get("rolling_strength", 0.55)),
            bloodshot=bool(meta.get("bloodshot", False)),
            bloodshot_intensity=float(meta.get("bloodshot_intensity", 0.65)),
        )
    except Exception:
        return EyeFXSpec()


_LORA_TAG_RE = re.compile(r"<lora:([^:>]+):([0-9]*\.?[0-9]+)>")


def _parse_lora_tags(prompt: str) -> tuple[str, list[dict[str, Any]]]:
    """Extract ``<lora:name:weight>`` tags from a user prompt.

    Returns:
        (cleaned_prompt, list_of_lora_dicts)

    Each lora dict has keys: name, strength_model, strength_clip, enabled.
    The cleaned prompt has the ``<lora:…>`` tags removed.
    """
    loras: list[dict[str, Any]] = []
    for m in _LORA_TAG_RE.finditer(prompt):
        name = m.group(1).strip()
        weight = float(m.group(2))
        # Ensure the name ends with a known extension
        if not any(name.endswith(ext) for ext in (".safetensors", ".pt", ".ckpt")):
            name += ".safetensors"
        loras.append({
            "name": name,
            "strength_model": round(min(max(weight, 0.0), 1.5), 2),
            "strength_clip": round(min(max(weight, 0.0), 1.5), 2),
            "enabled": True,
        })
    cleaned = _LORA_TAG_RE.sub("", prompt).strip()
    # Collapse multiple spaces left by removal
    cleaned = re.sub(r"  +", " ", cleaned)
    return cleaned, loras


class AnimePipelineOrchestrator:
    """
    7-stage anime multi-pass pipeline orchestrator.

    Stages:
        1. vision_analysis    — Analyze input/references
        2. layer_planning     — Build structured LayerPlan
        3. composition_pass   — Generate draft via ComfyUI
        4. structure_lock     — Extract control layers
        5. beauty_pass        — ControlNet-guided redraw
        6. detection_inpaint  — YOLO detail fix (face/eyes/hands)
        7. critique           — Vision-based quality scoring
        8. upscale            — RealESRGAN final upscale

    If critique fails, stages 5-7 repeat up to max_refine_rounds times.
    """

    def __init__(self, config: Optional[AnimePipelineConfig] = None):
        self._config = config or load_config()
        self._vision = VisionAnalystAgent(self._config)
        self._planner = LayerPlannerAgent(self._config)
        self._composition = CompositionPassAgent(self._config)
        self._structure = StructureLockAgent(self._config)
        self._beauty = BeautyPassAgent(self._config)
        self._detection_inpaint = DetectionInpaintAgent(self._config)
        self._critique = CritiqueAgent(self._config)
        self._upscale = UpscaleAgent(self._config)
        self._ranker = FinalRanker()
        self._result_store = ResultStore(
            base_dir=self._config.intermediate_dir
        )
        self._detected_character: Optional[str] = None
        self._research: Optional[CharacterResearchResult] = None
        self._verified_lora: Optional[LoRAVerificationResult] = None
        # Anti-duplicate: track seeds already used in this pipeline run
        self._used_seeds: set[int] = set()
        # Re-plan state: set by _beauty_critique_loop when 4 consecutive fails occur
        self._replan_needed: bool = False
        self._replan_count: int = 0
        self._attempt_1_best_image: Optional[str] = None
        # Instant-cancel state. Set to True by _run_stage when the user
        # presses the Stop button between stages. run_stream and the
        # beauty/critique loop check this after every yield-from to bail
        # out as fast as possible.
        self._cancelled: bool = False
        self._run_t0: float = 0.0

    @property
    def enabled(self) -> bool:
        return _pipeline_enabled()

    def run(self, job: AnimePipelineJob) -> AnimePipelineJob:
        """Run the full pipeline synchronously."""
        events = list(self.run_stream(job))
        return job

    def run_stream(
        self, job: AnimePipelineJob
    ) -> Generator[dict[str, Any], None, None]:
        """Run pipeline, yielding SSE events per stage."""
        t0 = time.time()
        # Reset per-run cancel state and store t0 so any helper
        # (notably _run_stage) can build a cancellation event without
        # threading t0 through every call.
        self._cancelled = False
        self._run_t0 = t0

        yield self._event("pipeline_start", {
            "job_id": job.job_id,
            "user_prompt": job.user_prompt,
            "stages": [
                "vision_analysis", "character_research", "lora_search",
                "layer_planning", "composition_pass", "structure_lock",
                "beauty_pass", "detection_inpaint", "critique", "upscale",
            ],
        })

        try:
            # Parse <lora:name:weight> tags from user prompt
            cleaned_prompt, user_loras = _parse_lora_tags(job.user_prompt)
            if user_loras:
                job.user_loras = user_loras
                job.user_prompt = cleaned_prompt
                logger.info(
                    "[AnimePipeline] Parsed %d user LoRA tags: %s",
                    len(user_loras),
                    [l["name"] for l in user_loras],
                )
            # Also merge any pre-set user_loras (from API request)
            if job.user_loras and not user_loras:
                logger.info(
                    "[AnimePipeline] Using %d pre-set user LoRAs",
                    len(job.user_loras),
                )

            # Stage 1: Vision Analysis
            yield from self._run_stage(
                "vision_analysis", self._vision, job, stage_num=1, total=8,
            )

            # Snapshot ref count BEFORE character research so we can detect
            # when web-research injects new references and re-run vision.
            _refs_before_research = len(job.reference_images_b64 or [])

            # Emit vision reasoning event
            vision_reasoning = self._build_vision_reasoning(job)
            if vision_reasoning:
                yield self._event("vision_reasoning", vision_reasoning)

            # Stage 1.5: Character Research (web search + reference download)
            yield from self._run_character_research(job)

            # ── Re-run vision analysis when fresh refs were injected ─────
            # The first Stage 1 pass may have logged "No reference images"
            # because character_research hadn't downloaded them yet. Now
            # that refs exist, re-execute vision so the LLM actually
            # tags the character art instead of hallucinating from prompt.
            _refs_after_research = len(job.reference_images_b64 or [])
            if (
                _refs_after_research > _refs_before_research
                and getattr(self._vision, "execute", None) is not None
            ):
                try:
                    logger.info(
                        "[AnimePipeline] Re-running vision_analysis on %d injected ref(s)",
                        _refs_after_research - _refs_before_research,
                    )
                    self._vision.execute(job)
                    yield self._event("vision_reanalyzed", {
                        "ref_count": _refs_after_research,
                        "tags_count": len(
                            (job.vision_analysis.anime_tags if job.vision_analysis else [])
                        ),
                    })
                except Exception as _re_exc:  # pragma: no cover — defensive
                    logger.warning(
                        "[AnimePipeline] Vision re-analysis failed (non-fatal): %s",
                        _re_exc,
                    )

            # Apply identity-derived overrides (solo enforcement +
            # homonym/collision negatives) to vision_analysis. Runs
            # whether or not character research produced results because
            # solo_intent and off-domain collision blocks can apply even
            # without a web-researched character.
            self._apply_identity_overrides(job)

            # Detect character for identity-aware critique
            self._detected_character = self._detect_character_from_vision(job)
            if self._detected_character:
                self._critique.set_character_context(self._detected_character)
                if self._research:
                    self._critique.set_research_context(
                        self._research.build_critique_context()
                    )
                logger.info("[AnimePipeline] Character detected: %s -- identity-aware critique enabled",
                            self._detected_character)

            # Stage 1.75: LoRA search, download, and vision verification
            yield from self._run_lora_stage(job)

            # Stage 1.9: 4-Agents council reasoning (when multi-thinking active)
            if job.thinking_mode == "multi-thinking":
                yield from self._run_council_reasoning(job)

            # Stage 2: Layer Planning
            yield from self._run_stage(
                "layer_planning", self._planner, job, stage_num=4, total=9,
            )

            # Inject verified character LoRA into all passes
            if self._verified_lora and self._verified_lora.accepted:
                self._inject_character_lora(job)

            # Inject user-specified LoRAs (<lora:name:weight> from prompt)
            if job.user_loras:
                self._inject_user_loras(job)

            # Stage 3: Composition Pass
            yield from self._run_stage(
                "composition_pass", self._composition, job, stage_num=5, total=9,
            )
            if self._cancelled:
                return
            if job.status == AnimePipelineStatus.FAILED:
                yield self._event("pipeline_error", {"error": job.error, "job_id": job.job_id})
                return

            # User cancellation checkpoint after composition (~30-60s in)
            if _is_cancel_requested(job.job_id):
                yield self._build_cancellation_event(job, "composition_pass", t0)
                return

            # ── Image-only fast path ──────────────────────────────────
            # When the user picked "Chỉ tạo ảnh" in the choice card, we
            # stop here and skip structure_lock / beauty / detection /
            # critique / upscale entirely. The composition_pass agent
            # already populated job.final_images_b64 with all batch
            # candidates (1 to 6 images). We just promote the first one
            # to final_image_b64 and emit pipeline_complete.
            if getattr(job, "image_only", False):
                last_intermediate = self._pick_best_intermediate(job)
                if last_intermediate and not job.final_image_b64:
                    job.final_image_b64 = last_intermediate
                if not job.final_images_b64 and job.final_image_b64:
                    job.final_images_b64 = [job.final_image_b64]
                job.status = AnimePipelineStatus.COMPLETED
                job.completed_at = self._now_iso()
                job.total_latency_ms = (time.time() - t0) * 1000
                logger.info(
                    "[AnimePipeline] image_only fast path complete: %d candidate(s), %.0fms",
                    len(job.final_images_b64), job.total_latency_ms,
                )
                yield self._event("pipeline_complete", {
                    "job_id": job.job_id,
                    "status": "completed",
                    "has_image": job.final_image_b64 is not None,
                    "has_secondary_image": False,
                    "image_only": True,
                    "batch_count": len(job.final_images_b64),
                    "total_latency_ms": job.total_latency_ms,
                    "stages_executed": job.stages_executed,
                    "refine_rounds": 0,
                    "models_used": job.models_used,
                    "vram_profile": self._config.vram.profile.value,
                })
                return

            # Stage 4: Structure Lock
            yield from self._run_stage(
                "structure_lock", self._structure, job, stage_num=6, total=9,
            )
            if self._cancelled:
                return

            # User cancellation checkpoint after structure_lock
            if _is_cancel_requested(job.job_id):
                yield self._build_cancellation_event(job, "structure_lock", t0)
                return

            # Stage 5-8: Beauty + YOLO Detail Fix + Critique loop
            # YOLO runs INSIDE the loop so Critique evaluates the
            # YOLO-enhanced image, not raw Beauty output.
            yield from self._beauty_critique_loop(job)
            if self._cancelled:
                return

            # User cancellation checkpoint after beauty/critique loop
            # (most users hit Stop somewhere during the long beauty pass)
            if _is_cancel_requested(job.job_id):
                yield self._build_cancellation_event(job, "beauty_pass", t0)
                return

            # ── Re-plan on 4-consecutive-fail: attempt 2 ───────────────
            if self._replan_needed and self._replan_count < 1:
                self._replan_needed = False
                self._replan_count += 1

                # Save best image from attempt 1
                self._attempt_1_best_image = self._pick_best_intermediate(job)

                # Retry attempt 2 reuses the EXACT original user prompt (100% match,
                # no paraphrase). This was changed from a 95%-similarity variant
                # because attempt-1 outputs already drifted; rephrasing on retry
                # made the second image less faithful to the user's text.
                variant_prompt = self._generate_variant_prompt(job.user_prompt)
                original_prompt = job.user_prompt

                yield self._event("replan_start", {
                    "attempt": 2,
                    "reason": "4 consecutive beauty passes below quality threshold",
                    "original_prompt": original_prompt,
                    "variant_prompt": variant_prompt,
                    "prompt_fidelity": "verbatim_100pct",
                    "attempt_1_best_score": max(
                        (c.overall_score for c in job.critique_results), default=0.0
                    ),
                })
                logger.info(
                    "[AnimePipeline] Re-plan attempt 2 (verbatim prompt): '%s'",
                    original_prompt[:80],
                )

                # Re-run layer planning + composition + structure from scratch
                yield from self._run_full_replan(job, variant_prompt)

                if job.status != AnimePipelineStatus.FAILED:
                    # Inject LoRAs for new plan
                    if self._verified_lora and self._verified_lora.accepted:
                        self._inject_character_lora(job)
                    if job.user_loras:
                        self._inject_user_loras(job)

                    # Snapshot critique count BEFORE attempt 2 so we can tag
                    # only the new ones (added during attempt 2 loop) below.
                    _critiques_before_attempt2 = len(job.critique_results)

                    # Beauty loop attempt 2
                    yield from self._beauty_critique_loop(job)

                    # Tag all new critiques as attempt-2 results
                    for _c in job.critique_results[_critiques_before_attempt2:]:
                        try:
                            setattr(_c, "_attempt2", True)
                        except Exception:
                            pass

                # If attempt 2 also didn't pass quality, emit dual output
                attempt_2_passed = bool(
                    job.critique_results and job.critique_results[-1].passed
                )
                if not attempt_2_passed and self._attempt_1_best_image:
                    job.secondary_image_b64 = self._attempt_1_best_image
                    yield self._event("dual_output", {
                        "reason": "Both attempts failed quality threshold",
                        "attempt_1_score": max(
                            (c.overall_score for c in job.critique_results
                             if not getattr(c, "_attempt2", False)),
                            default=0.0,
                        ),
                        "attempt_2_score": (
                            job.critique_results[-1].overall_score
                            if job.critique_results else 0.0
                        ),
                        "has_secondary": True,
                    })
                    logger.info(
                        "[AnimePipeline] Dual output: both attempts below threshold. "
                        "Returning best of each."
                    )

            # Stage 9: Upscale
            yield from self._run_stage(
                "upscale", self._upscale, job, stage_num=9, total=9,
            )
            if self._cancelled:
                return

            # Stage 9b: Artistic layer painter (spec §8/§9/§10/§11).
            # Post-upscale PIL pass: shadow + highlight + optional eye FX
            # + vision-based eye-state classifier. All side-effects are
            # best-effort; missing PIL/keys skip the pass without failing.
            yield from self._run_layer_painter(job)

            # Finalize
            job.status = AnimePipelineStatus.COMPLETED
            job.completed_at = self._now_iso()
            job.total_latency_ms = (time.time() - t0) * 1000

            # Final ranking — score all eligible candidate images and pick winner.
            # The orchestrator's own loop already selects job.final_image_b64; the
            # ranker adds explainable metadata (composite score, runner-ups) and
            # feeds the output_manifest.  Purely additive: final image is not
            # overridden unless the ranker identifies a better candidate.
            rank_result = None
            try:
                rank_result = self._ranker.execute(job)
                if rank_result and rank_result.winner:
                    job.metadata["rank_result"] = rank_result.to_dict()
                    yield self._event("final_ranking", {
                        "job_id": job.job_id,
                        "winner_stage": rank_result.winner.stage,
                        "winner_score": round(rank_result.winner.composite_score, 2),
                        "total_candidates": rank_result.total_candidates,
                        "runner_ups": [
                            {"stage": r.stage, "score": round(r.composite_score, 2)}
                            for r in rank_result.runner_ups[:3]
                        ],
                    })
            except Exception as rank_err:
                logger.warning("[AnimePipeline] FinalRanker failed: %s", rank_err)

            # Save intermediates if configured
            if self._config.save_intermediates:
                self._result_store.save_all(job, rank_result=rank_result)

            yield self._event("pipeline_complete", {
                "job_id": job.job_id,
                "status": "completed",
                "has_image": job.final_image_b64 is not None,
                "has_secondary_image": job.secondary_image_b64 is not None,
                "total_latency_ms": job.total_latency_ms,
                "stages_executed": job.stages_executed,
                "refine_rounds": job.refine_rounds,
                "models_used": job.models_used,
                "vram_profile": self._config.vram.profile.value,
                "replan_count": self._replan_count,
                "rank_winner_stage": (
                    rank_result.winner.stage
                    if rank_result and rank_result.winner else None
                ),
                "rank_winner_score": (
                    round(rank_result.winner.composite_score, 2)
                    if rank_result and rank_result.winner else None
                ),
            })

        except Exception as e:
            logger.error("[AnimePipeline] Unhandled error: %s", e, exc_info=True)
            job.status = AnimePipelineStatus.FAILED
            job.error = str(e)
            job.total_latency_ms = (time.time() - t0) * 1000

            # If we have any intermediate, use it as fallback
            if not job.final_image_b64:
                for img in reversed(job.intermediates):
                    if img.image_b64:
                        job.final_image_b64 = img.image_b64
                        break

            yield self._event("pipeline_error", {
                "job_id": job.job_id,
                "error": str(e),
                "has_fallback_image": job.final_image_b64 is not None,
            })

    def _beauty_critique_loop(
        self, job: AnimePipelineJob
    ) -> Generator[dict[str, Any], None, None]:
        """Run beauty pass + critique, repeating until quality target is met.

        Stagnation detection: if score does not improve for
        ``max_stagnant_rounds`` consecutive rounds, trigger a full restart
        (new random seed, reset refine context) up to ``max_full_restarts``
        times.

        For character-detected prompts, the loop is more aggressive:
        eye/face must reach 8+ to pass. Max rounds increased to 4.
        """
        max_rounds = self._config.max_refine_rounds
        max_stagnant = getattr(self._config, "max_stagnant_rounds", 5)
        max_restarts = getattr(self._config, "max_full_restarts", 2)
        best_score = 0.0
        best_image_b64 = None
        critique_for_next_round = None
        eye_refine_round_used = False
        has_character = self._detected_character is not None
        score_history: list[float] = []
        stagnant_count = 0
        restart_count = 0
        # Re-plan trigger: count rounds where score stays below threshold
        consecutive_fail_count = 0
        # Eye emergency: track which rounds already had eye-focus inpaint
        eye_emergency_done_rounds: set[int] = set()

        # Anti-duplicate: share used-seed set with beauty agent
        self._beauty._used_seeds = self._used_seeds

        for round_num in range(max_rounds + 1):
            is_refine = round_num > 0
            stage_label = f"beauty_pass{'_refine_' + str(round_num) if is_refine else ''}"

            if is_refine:
                job.status = AnimePipelineStatus.REFINING
                yield self._event("refine_start", {
                    "round": round_num,
                    "max_rounds": max_rounds,
                    "previous_score": best_score,
                })

            # Feed latest critique into the next beauty round so it can
            # prioritize eye-focused correction when needed.
            self._beauty.set_refine_context(critique_for_next_round)

            # On refine rounds, force a NEW random seed so the output varies.
            # The original seed is preserved and restored if we ever need it.
            if is_refine and job.layer_plan and job.layer_plan.beauty_pass:
                job.layer_plan.beauty_pass.seed = -1  # -1 → random in _resolve_seed

            # Beauty pass
            yield from self._run_stage(
                "beauty_pass", self._beauty, job, stage_num=5, total=7,
                extra={"round": round_num},
            )
            if self._cancelled:
                return

            beauty_failed = (job.status == AnimePipelineStatus.FAILED)
            if beauty_failed:
                # Reset status so critique can still run using the last available image
                job.status = AnimePipelineStatus.CRITIQUING

            # YOLO Detail Fix — runs BEFORE critique so that Critique
            # evaluates the YOLO-enhanced image, not raw beauty output.
            # Skips gracefully if YOLO unavailable or beauty failed.
            if not beauty_failed:
                yield from self._run_detection_inpaint(job)
                if self._cancelled:
                    return

            # Critique evaluates the post-YOLO image (or composition fallback)
            yield from self._run_stage(
                "critique", self._critique, job, stage_num=6, total=7,
                extra={"round": round_num},
            )
            if self._cancelled:
                return

            if beauty_failed:
                break  # don't loop for refinement if beauty couldn't produce an image

            # Check critique result
            latest_critique = job.critique_results[-1] if job.critique_results else None
            if latest_critique:
                critique_for_next_round = latest_critique
                score = latest_critique.overall_score

                # ── Eye Emergency: before any loop decision ──────────────
                # When eye_consistency_score < 7, run a targeted high-denoise
                # eye/face inpaint pass and immediately re-critique.
                # Only once per round to avoid infinite loops.
                eye_score_before = latest_critique.eye_consistency_score
                if (
                    eye_score_before < 7
                    and round_num not in eye_emergency_done_rounds
                    and self._detection_inpaint.is_available()
                    and getattr(self._config, "detection_inpaint_enabled", False)
                ):
                    eye_emergency_done_rounds.add(round_num)
                    yield from self._run_eye_emergency_inpaint(job, latest_critique)

                    # Re-run critique on eye-enhanced image
                    yield from self._run_stage(
                        "critique", self._critique, job, stage_num=6, total=7,
                        extra={"round": round_num, "eye_emergency": True},
                    )
                    if job.critique_results:
                        latest_critique = job.critique_results[-1]
                        critique_for_next_round = latest_critique
                        score = latest_critique.overall_score
                        yield self._event("eye_emergency_result", {
                            "round": round_num,
                            "eye_score_before": eye_score_before,
                            "eye_score_after": latest_critique.eye_consistency_score,
                            "overall_before": score_history[-1] if score_history else 0,
                            "overall_after": round(score, 2),
                        })

                score_history.append(score)

                # Emit deep critique reasoning with all dimension scores
                yield self._event("critique_reasoning", {
                    "round": round_num,
                    "overall_score": round(score, 2),
                    "passed": latest_critique.passed,
                    "dimension_scores": {
                        k: round(v, 1) for k, v in latest_critique.dimension_scores.items() if v > 0
                    },
                    "face_score": latest_critique.face_score,
                    "eye_consistency_score": latest_critique.eye_consistency_score,
                    "eye_issues": latest_critique.eye_issues[:5],
                    "weakest_dimensions": sorted(
                        ((k, v) for k, v in latest_critique.dimension_scores.items() if v > 0),
                        key=lambda x: x[1],
                    )[:3],
                    "score_history": [round(s, 2) for s in score_history],
                    "best_score": round(best_score, 2),
                    "stagnant_count": stagnant_count + (0 if score > best_score else 1),
                })

                if score > best_score:
                    best_score = score
                    stagnant_count = 0
                    consecutive_fail_count = 0
                    # Get the best image: prefer YOLO-enhanced (detail_*),
                    # fall back to beauty_pass, then composition_pass
                    for img in reversed(job.intermediates):
                        if img.stage.startswith("detail_") or img.stage == "beauty_pass":
                            best_image_b64 = img.image_b64
                            break
                else:
                    stagnant_count += 1

                # Track consecutive rounds below quality threshold
                threshold_score = self._config.quality_threshold * 10
                if score < threshold_score:
                    consecutive_fail_count += 1
                else:
                    consecutive_fail_count = 0

                # ── Re-plan trigger: 4 consecutive sub-threshold rounds ──
                # Signal the orchestrator to re-plan with a fresh prompt.
                _REPLAN_FAIL_LIMIT = 4
                if (
                    consecutive_fail_count >= _REPLAN_FAIL_LIMIT
                    and not self._replan_needed
                    and round_num < max_rounds
                ):
                    self._replan_needed = True
                    logger.info(
                        "[AnimePipeline] %d consecutive fails (best=%.1f) — scheduling re-plan",
                        consecutive_fail_count, best_score,
                    )
                    yield self._event("replan_scheduled", {
                        "consecutive_fails": consecutive_fail_count,
                        "best_score": round(best_score, 2),
                        "score_history": [round(s, 2) for s in score_history],
                        "reason": f"{consecutive_fail_count} consecutive rounds below {threshold_score:.1f}",
                    })
                    break  # exit loop; orchestrator will re-plan

                # ── Hard cap re-plan trigger: N TOTAL rounds without a pass ──
                # Prevents endless refine when score oscillates around threshold
                # (e.g. 7.9/8.1/7.8 never tripping the consecutive-fail rule).
                # After this many beauty rounds without latest_critique.passed,
                # force re-plan → produces 2nd image via dual_output.
                hard_cap_total = getattr(self._config, "force_replan_after_rounds", 5)
                rounds_done = round_num + 1  # 1-indexed for human readability
                if (
                    rounds_done >= hard_cap_total
                    and not latest_critique.passed
                    and round_num < max_rounds
                ):
                    if (
                        not self._replan_needed
                        and self._replan_count < 1
                    ):
                        # Attempt 1: trigger replan
                        self._replan_needed = True
                        logger.info(
                            "[AnimePipeline] Hard cap reached (attempt 1): %d rounds without pass (best=%.1f) — scheduling re-plan",
                            rounds_done, best_score,
                        )
                        yield self._event("replan_scheduled", {
                            "consecutive_fails": consecutive_fail_count,
                            "best_score": round(best_score, 2),
                            "score_history": [round(s, 2) for s in score_history],
                            "reason": f"Reached {rounds_done} total beauty rounds without passing (hard cap {hard_cap_total})",
                            "hard_cap": True,
                        })
                    else:
                        # Attempt 2 (or beyond): plain hard stop, no further replan.
                        # Dual output will be emitted by orchestrator using best images.
                        logger.info(
                            "[AnimePipeline] Hard cap reached (attempt 2): %d rounds without pass (best=%.1f) — stopping refine loop",
                            rounds_done, best_score,
                        )
                        yield self._event("refine_hard_stop", {
                            "rounds_done": rounds_done,
                            "best_score": round(best_score, 2),
                            "score_history": [round(s, 2) for s in score_history],
                            "reason": f"Attempt 2 reached {rounds_done} rounds without passing (hard cap {hard_cap_total})",
                        })
                    break  # exit loop

                # ── Stagnation detection: full restart ──────────────
                if (
                    stagnant_count >= max_stagnant
                    and restart_count < max_restarts
                    and round_num < max_rounds
                ):
                    restart_count += 1
                    stagnant_count = 0
                    consecutive_fail_count = 0
                    critique_for_next_round = None
                    eye_refine_round_used = False
                    # Emit restart event for UI
                    yield self._event("full_restart", {
                        "restart_num": restart_count,
                        "best_score": best_score,
                        "reason": f"Score stagnant for {max_stagnant} rounds (best={best_score:.1f})",
                        "score_history": [round(s, 2) for s in score_history],
                    })
                    # Emit reasoning for the refine decision
                    worst_dims = sorted(
                        ((k, v) for k, v in latest_critique.dimension_scores.items() if v > 0),
                        key=lambda x: x[1],
                    )[:3]
                    yield self._event("refine_reasoning", {
                        "round": round_num,
                        "reason": f"Full restart #{restart_count}: score stuck at {score:.1f}",
                        "worst_dimensions": [{"name": k, "score": v} for k, v in worst_dims],
                        "actions": ["new_seed", "reset_refine_context"],
                        "score_history": [round(s, 2) for s in score_history],
                    })
                    logger.info(
                        "[AnimePipeline] Full restart #%d: score stagnant for %d rounds (best=%.1f)",
                        restart_count, max_stagnant, best_score,
                    )
                    job.refine_rounds += 1
                    continue

                # Character-specific face/eye quality gate:
                # Even if overall passes, force refine if face or eyes are weak.
                #
                # Calibration history:
                #  - face_score < 8 + eye_ref < 95% used to force refine even
                #    when the image was already good enough (e.g. score=7.79
                #    + eye_ref=85% looped 3 rounds without measurable gain,
                #    adding ~10 minutes to total runtime).
                #  - Real-world critique scores rarely cross 8.5 even on
                #    excellent images, and eye_ref above 80% is already a
                #    strong character match.
                # New thresholds: face ≥ 7, eye ≥ 7, eye_ref ≥ 80%.
                # If the user wants stricter behavior, raise via env:
                #   ANIME_PIPELINE_GATE_FACE_MIN, ANIME_PIPELINE_GATE_EYE_MIN,
                #   ANIME_PIPELINE_GATE_EYE_REF_MIN.
                import os as _os
                _gate_face_min = float(_os.getenv("ANIME_PIPELINE_GATE_FACE_MIN", "7"))
                _gate_eye_min = float(_os.getenv("ANIME_PIPELINE_GATE_EYE_MIN", "7"))
                _gate_eye_ref_min = float(_os.getenv("ANIME_PIPELINE_GATE_EYE_REF_MIN", "80"))

                face_weak = has_character and latest_critique.face_score < _gate_face_min
                eye_ref_pct = getattr(latest_critique, "eye_reference_match_pct", 0.0)
                eye_ref_weak = eye_ref_pct > 0.0 and eye_ref_pct < _gate_eye_ref_min
                eyes_weak = has_character and (
                    latest_critique.eye_consistency_score < _gate_eye_min or eye_ref_weak
                )

                # Eye-refine scheduling: run focused refine when eyes are weak
                if (
                    not eye_refine_round_used
                    and round_num < max_rounds
                    and (self._beauty.should_apply_eye_refine(latest_critique) or eyes_weak)
                ):
                    eye_refine_round_used = True
                    job.refine_rounds += 1
                    yield self._event("eye_refine_scheduled", {
                        "round": round_num + 1,
                        "eye_score": latest_critique.eye_consistency_score,
                        "eye_reference_match_pct": getattr(latest_critique, "eye_reference_match_pct", 0.0),
                        "face_score": latest_critique.face_score,
                        "eye_issues": latest_critique.eye_issues[:3],
                        "character": self._detected_character or "",
                    })
                    continue

                # Force additional refine if face/eyes are below character threshold
                if (face_weak or eyes_weak) and round_num < max_rounds:
                    logger.info(
                        "[AnimePipeline] Character face/eye quality gate: face=%d eyes=%d ref_match=%.0f%%, refining round %d",
                        latest_critique.face_score, latest_critique.eye_consistency_score,
                        getattr(latest_critique, "eye_reference_match_pct", 0.0), round_num + 1,
                    )
                    job.refine_rounds += 1
                    continue

                if latest_critique.passed:
                    logger.info(
                        "[AnimePipeline] Critique passed (score=%.2f) on round %d",
                        score, round_num,
                    )
                    break

                if round_num < max_rounds:
                    # Emit reasoning for why we're refining
                    worst_dims = sorted(
                        ((k, v) for k, v in latest_critique.dimension_scores.items() if v > 0),
                        key=lambda x: x[1],
                    )[:3]
                    yield self._event("refine_reasoning", {
                        "round": round_num,
                        "reason": f"Score {score:.1f}/10 below threshold",
                        "worst_dimensions": [{"name": k, "score": v} for k, v in worst_dims],
                        "actions": ["refine_with_critique_context"],
                        "score_history": [round(s, 2) for s in score_history],
                    })
                    logger.info(
                        "[AnimePipeline] Critique failed (score=%.2f), refining round %d",
                        score, round_num + 1,
                    )
                    job.refine_rounds += 1
                else:
                    logger.info(
                        "[AnimePipeline] Max refine rounds reached (score=%.2f)",
                        score,
                    )
            else:
                break


        # If we never passed but have a best image, use it
        if self._config.return_best_on_fail and best_image_b64 and not job.final_image_b64:
            job.final_image_b64 = best_image_b64

        # Auto-save high-quality output as character reference for future use
        self._maybe_save_character_reference(job, best_score)

    def _run_detection_inpaint(
        self, job: AnimePipelineJob
    ) -> Generator[dict[str, Any], None, None]:
        """Run ADetailer-style detection + inpaint on the beauty pass output.

        Uses YOLO to detect faces, eyes, and hands, then runs masked inpaint
        workflows for each detected region to enhance detail quality.

        Skips gracefully if:
          - ultralytics / PIL not installed
          - No regions detected
          - Detection is disabled in config
        """
        if not self._detection_inpaint.is_available():
            logger.info("[AnimePipeline] Detection inpaint skipped — dependencies not available")
            yield self._event("stage_skip", {
                "stage": "detection_inpaint",
                "reason": "dependencies_unavailable",
            })
            return

        # User contract: each layer must be a fully independent generation
        # (no inpaint reuse). Honor the config flag — when disabled, emit
        # a stage_skip event so the UI still knows the stage was reached
        # but did not run.
        if not getattr(self._config, "detection_inpaint_enabled", False):
            logger.info("[AnimePipeline] Detection inpaint disabled by config — skipping")
            yield self._event("stage_skip", {
                "stage": "detection_inpaint",
                "reason": "disabled_by_config",
            })
            return

        yield self._event("stage_start", {
            "stage": "detection_inpaint",
            "stage_num": 8,
            "total_stages": 10,
            "description": "ADetailer: 27-model multi-region detection + inpaint",
            "vram_profile": self._config.vram.profile.value,
        })

        try:
            self._detection_inpaint.execute(job)
        except Exception as e:
            logger.warning("[AnimePipeline] Detection inpaint failed (non-fatal): %s", e)
            yield self._event("stage_error", {
                "stage": "detection_inpaint",
                "error": str(e),
                "fatal": False,
            })
            return

        # Spec (2026-04-23): persist every detected feature as a cropped
        # layer file under storage/feature_layers/<session>/.  Failure is
        # logged but never fatal — the pipeline must still hand back the
        # main image even when crop persistence breaks.
        try:
            from .feature_crop_storage import persist_feature_crops
            crops = persist_feature_crops(
                job,
                getattr(self._detection_inpaint, "last_result", None),
            )
            if crops:
                job.metadata["feature_crops"] = crops
                yield self._event("feature_crops_persisted", {
                    "stage": "detection_inpaint",
                    "count": len(crops),
                    "feature_types": sorted({c["feature"] for c in crops}),
                })
        except Exception as exc:  # noqa: BLE001
            logger.warning("[AnimePipeline] feature crop persistence failed: %s", exc)

        latency = job.stage_timings_ms.get("detection_inpaint", 0.0)

        # Emit deep reasoning event with all YOLO detection results
        detection_summary = self._build_detection_reasoning(job)
        if detection_summary:
            yield self._event("detection_reasoning", detection_summary)

        yield self._event("stage_complete", {
            "stage": "detection_inpaint",
            "stage_num": 8,
            "total_stages": 10,
            "latency_ms": latency,
            "regions_processed": "detection_inpaint" in job.stages_executed,
        })

    def _run_layer_painter(
        self, job: AnimePipelineJob
    ) -> Generator[dict[str, Any], None, None]:
        """Spec §8/§9/§10/§11 post-upscale artistic layer pass.

        Runs Layer-2 shadow, Layer-3 highlight, optional Layer-4 eye FX
        (eye-rolling + bloodshot), and Layer-5 vision-based eye-state
        classifier. All sub-layers are best-effort; the final image is
        only replaced when at least one pass succeeded.
        """
        t0 = time.time()
        if not job.final_image_b64:
            return

        yield self._event("stage_start", {
            "stage": "layer_painter",
            "stage_num": 10,
            "total_stages": 10,
            "description": "Artistic layers (shadow/highlight/eye FX) + eye-state classifier",
            "vram_profile": self._config.vram.profile.value,
        })

        # Harvest face + eye bboxes from the most recent detection results.
        face_bbox = self._extract_face_bbox_for_layers(job)
        eye_boxes = self._extract_eye_bboxes_for_layers(job)

        # Read FX spec from job metadata (set upstream by prompt analyzer
        # or user options). Missing metadata ⇒ no eye-FX.
        fx_meta = (job.metadata or {}).get("eye_fx") if hasattr(job, "metadata") else None
        eye_fx = _eye_fx_from_meta(fx_meta)

        requested_state = (
            (job.metadata or {}).get("requested_eye_state", "open")
            if hasattr(job, "metadata") else "open"
        )

        try:
            result = apply_artistic_layers(
                job.final_image_b64,
                face_bbox=face_bbox,
                eye_boxes=eye_boxes,
                eye_fx=eye_fx,
                requested_eye_state=requested_state,
                do_shadow=True,
                do_highlight=True,
                do_classify=True,
            )
        except Exception as e:
            logger.warning("[AnimePipeline] Layer painter crashed (non-fatal): %s", e)
            yield self._event("stage_error", {
                "stage": "layer_painter",
                "error": str(e),
                "fatal": False,
            })
            return

        # Only overwrite when at least one pass actually modified bytes.
        any_change = (
            result.shadow_applied or result.highlight_applied
            or result.eye_rolling_applied or result.bloodshot_applied
        )
        if any_change:
            job.final_image_b64 = result.final_b64

        # Stash classifier output on the job for the manifest/UI.
        if result.eye_state is not None and hasattr(job, "metadata"):
            job.metadata = {**(job.metadata or {}),
                            "eye_state_report": result.eye_state.to_dict()}

        latency = (time.time() - t0) * 1000
        job.stage_timings_ms["layer_painter"] = latency

        yield self._event("stage_complete", {
            "stage": "layer_painter",
            "stage_num": 10,
            "total_stages": 10,
            "latency_ms": latency,
            **result.to_dict(),
        })

    def _extract_face_bbox_for_layers(self, job: AnimePipelineJob) -> Optional[EyeBBox]:
        """Pull the highest-confidence face bbox out of the detection agent.

        Returns ``None`` if detection didn't run or no face was found.
        """
        try:
            latest = getattr(self._detection_inpaint, "last_result", None)
            if not latest:
                return None
            regions_map = getattr(latest, "regions", {}) or {}
            # Try face first, then face_bbox.
            for rtype in ("face", "face_bbox"):
                candidates = regions_map.get(rtype) or []
                if not candidates:
                    continue
                best = max(candidates, key=lambda r: getattr(r, "confidence", 0.0))
                return EyeBBox(
                    int(getattr(best, "x1", 0)), int(getattr(best, "y1", 0)),
                    int(getattr(best, "x2", 0)), int(getattr(best, "y2", 0)),
                )
        except Exception as e:
            logger.debug("[AnimePipeline] face bbox extract failed: %s", e)
        return None

    def _extract_eye_bboxes_for_layers(self, job: AnimePipelineJob) -> list[EyeBBox]:
        """Pull every eye bbox (single or pair) out of the detection agent."""
        out: list[EyeBBox] = []
        try:
            latest = getattr(self._detection_inpaint, "last_result", None)
            if not latest:
                return out
            regions_map = getattr(latest, "regions", {}) or {}
            for rtype in ("eyes", "full_eyes"):
                for region in (regions_map.get(rtype) or []):
                    out.append(EyeBBox(
                        int(getattr(region, "x1", 0)), int(getattr(region, "y1", 0)),
                        int(getattr(region, "x2", 0)), int(getattr(region, "y2", 0)),
                    ))
        except Exception as e:
            logger.debug("[AnimePipeline] eye bbox extract failed: %s", e)
        return out

    def _apply_identity_overrides(self, job: AnimePipelineJob) -> None:
        """Inject solo-intent markers and collision-block negatives into
        ``job.vision_analysis``.

        Positive tags:
          * prepend ``solo`` when ``job.solo_intent`` is True.

        Negative tags (``vision_analysis.suggested_negative``):
          * append every entry in ``job.collision_blocks`` as a
            comma-separated fragment.

        Safe to call when ``vision_analysis`` is missing (e.g. the
        vision stage failed) — logs and no-ops in that case.
        Deterministic and idempotent (deduplicates on repeat calls).
        """
        va = job.vision_analysis
        if va is None:
            if job.solo_intent or job.collision_blocks:
                logger.debug(
                    "[AnimePipeline] Skipping identity overrides: "
                    "vision_analysis not populated",
                )
            return

        # Positive: solo marker. Use "solo" (danbooru convention) — we
        # deliberately do not guess 1girl/1boy here because that requires
        # gendered knowledge of the character; the research stage already
        # injected character-specific tags upstream.
        if job.solo_intent and "solo" not in va.anime_tags:
            va.anime_tags.insert(0, "solo")

        # Negative: merge collision_blocks into suggested_negative. Keep
        # existing entries, deduplicate case-insensitively.
        if job.collision_blocks:
            existing = [
                frag.strip()
                for frag in (va.suggested_negative or "").split(",")
                if frag.strip()
            ]
            seen_lower = {frag.lower() for frag in existing}
            for block in job.collision_blocks:
                key = block.strip().lower()
                if key and key not in seen_lower:
                    existing.append(block.strip())
                    seen_lower.add(key)
            va.suggested_negative = ", ".join(existing)

    def _run_character_research(
        self, job: AnimePipelineJob
    ) -> Generator[dict[str, Any], None, None]:
        """Run character web research between vision analysis and layer planning.

        If a known character is detected, searches the web for detailed appearance
        info, downloads reference images, and enriches the job with identity tags
        and reference images for better prompt generation.
        """
        yield self._event("stage_start", {
            "stage": "character_research",
            "stage_num": 2,
            "total_stages": 9,
            "vram_profile": self._config.vram.profile.value,
        })

        t0 = time.time()

        # Parse structured identity from the user prompt BEFORE web research.
        # Populates job.character_name / series_name / character_tag /
        # series_tag / alias_source / solo_intent / collision_blocks so
        # downstream stages (layer_planner, lora_manager) can use them
        # regardless of whether web research succeeds.
        try:
            identity = parse_character_identity(job.user_prompt)
            job.character_name = identity.character_name
            job.series_name = identity.series_name
            job.character_tag = identity.character_tag
            job.series_tag = identity.series_tag
            job.alias_source = identity.alias_source
            job.solo_intent = identity.solo_intent
            job.collision_blocks = list(identity.collision_blocks)
            if identity.resolved:
                logger.info(
                    "[AnimePipeline] Identity parsed: %s (%s) via %s "
                    "solo=%s homonym_collision=%s blocks=%d",
                    identity.character_name,
                    identity.series_name,
                    identity.alias_source,
                    identity.solo_intent,
                    identity.homonym_collision,
                    len(identity.collision_blocks),
                )
            elif identity.solo_intent:
                logger.info(
                    "[AnimePipeline] Solo intent detected with no named character; "
                    "collision_blocks=%d",
                    len(identity.collision_blocks),
                )
        except Exception as parse_err:
            logger.warning(
                "[AnimePipeline] Character parse failed (non-fatal): %s",
                parse_err,
            )

        try:
            result = research_character(
                job.user_prompt,
                user_reference_images=job.reference_images_b64 or None,
            )
            self._research = result

            if result:
                self._detected_character = result.danbooru_tag

                # Inject web-researched reference images into the job
                if result.reference_images_b64 and not job.reference_images_b64:
                    job.reference_images_b64 = result.reference_images_b64[:3]
                    logger.info(
                        "[AnimePipeline] Injected %d web reference images for %s",
                        len(job.reference_images_b64), result.display_name,
                    )

                # Augment from local reference cache + attach identity detail.
                # Safe-only: consults storage/character_refs/<tag>/ which is
                # populated by character_research web downloads or by past
                # high-score pipeline outputs (save_as_reference). Never
                # scrapes new sources here.
                self._augment_references_from_cache(job, result.danbooru_tag)

                # Enrich vision analysis tags with researched identity
                if job.vision_analysis and result.identity_tags:
                    existing = set(job.vision_analysis.anime_tags)
                    research_tags = result.build_positive_tags()
                    new_tags = [t for t in research_tags if t not in existing]
                    if new_tags:
                        # Prepend character identity tags before scene tags
                        job.vision_analysis.anime_tags = (
                            research_tags + job.vision_analysis.anime_tags
                        )
                        # Deduplicate while preserving order
                        seen: set[str] = set()
                        deduped: list[str] = []
                        for t in job.vision_analysis.anime_tags:
                            if t not in seen:
                                seen.add(t)
                                deduped.append(t)
                        job.vision_analysis.anime_tags = deduped
                        logger.info(
                            "[AnimePipeline] Enriched tags with %d research tags",
                            len(new_tags),
                        )

                latency = (time.time() - t0) * 1000
                job.stage_timings_ms["character_research"] = latency
                job.stages_executed.append("character_research")

                # SAA thumbnail lookup (best-effort, offline).
                saa_thumbnail: Optional[str] = None
                try:
                    from .saa_character_db import get_character_thumbnail
                    # The WAI DB keys are the space-form tag, so convert.
                    tag_space = (result.danbooru_tag or "").replace("_", " ")
                    saa_thumbnail = get_character_thumbnail(tag_space)
                except Exception:
                    saa_thumbnail = None

                yield self._event("stage_complete", {
                    "stage": "character_research",
                    "stage_num": 2,
                    "total_stages": 9,
                    "latency_ms": latency,
                    "character": result.display_name,
                    "series": result.series_name,
                    "confidence": result.confidence,
                    "ref_images_count": len(result.reference_images_b64),
                    "identity_tags_count": len(result.identity_tags),
                    "cached": result.cached,
                    # New: expose resolution provenance so the UI can show
                    # whether the match came from the hand-curated table,
                    # the SAA 5149-char offline DB, or the web fallback.
                    "alias_source": getattr(job, "alias_source", None),
                    "character_tag": getattr(job, "character_tag", None),
                    "saa_thumbnail": saa_thumbnail,
                })
            else:
                latency = (time.time() - t0) * 1000
                job.stage_timings_ms["character_research"] = latency
                job.stages_executed.append("character_research")
                yield self._event("stage_complete", {
                    "stage": "character_research",
                    "stage_num": 2,
                    "total_stages": 9,
                    "latency_ms": latency,
                    "character": None,
                    "skipped": True,
                })
                logger.info("[AnimePipeline] No character detected, research skipped")

        except Exception as e:
            logger.warning("[AnimePipeline] Character research failed (non-fatal): %s", e)
            latency = (time.time() - t0) * 1000
            job.stage_timings_ms["character_research"] = latency
            yield self._event("stage_complete", {
                "stage": "character_research",
                "stage_num": 2,
                "total_stages": 9,
                "latency_ms": latency,
                "error": str(e),
                "skipped": True,
            })

    def _run_lora_stage(
        self, job: AnimePipelineJob
    ) -> Generator[dict[str, Any], None, None]:
        """Stage 3: search, download, test-generate, and verify a character LoRA.

        Only runs when a character was identified in character_research.
        Stores result in self._verified_lora.
        Non-fatal: if anything goes wrong, pipeline continues without a character LoRA.
        """
        yield self._event("stage_start", {
            "stage": "lora_search",
            "stage_num": 3,
            "total_stages": 9,
            "vram_profile": self._config.vram.profile.value,
        })

        t0 = time.time()

        # Fall through to parser-only identity when web research failed but
        # the character parser still produced a tag. This keeps LoRA search
        # working on offline / rate-limited / search-disabled environments.
        if not self._research and job.character_tag and job.series_tag:
            logger.info(
                "[AnimePipeline] LoRA stage running with parser-only identity: "
                "%s (%s)",
                job.character_name or job.character_tag,
                job.series_name or job.series_tag,
            )
            self._research = CharacterResearchResult(
                danbooru_tag=job.character_tag,
                display_name=job.character_name or job.character_tag.replace("_", " "),
                series_name=job.series_name or job.series_tag.replace("_", " "),
                series_tag=job.series_tag,
                appearance_summary="",
                confidence=0.5,
                cached=False,
            )
            # Record detection so _inject_character_lora and reference save
            # use the parser tag when research never ran.
            if not self._detected_character:
                self._detected_character = job.character_tag
            # Consult the local reference cache in offline mode too.
            self._augment_references_from_cache(job, job.character_tag)

        if not self._research:
            latency = (time.time() - t0) * 1000
            job.stage_timings_ms["lora_search"] = latency
            job.stages_executed.append("lora_search")
            yield self._event("stage_complete", {
                "stage": "lora_search",
                "stage_num": 3,
                "total_stages": 9,
                "latency_ms": latency,
                "skipped": True,
                "reason": "no_character_detected",
            })
            return

        research = self._research
        comfyui_url = getattr(self._config, "comfyui_url", "") or os.getenv(
            "ANIME_PIPELINE_COMFYUI_URL",
            os.getenv("COMFYUI_URL", "http://127.0.0.1:8188"),
        )
        # Resolve the base checkpoint from config
        base_checkpoint = ""
        try:
            base_checkpoint = self._config.composition_model.checkpoint
        except AttributeError:
            try:
                base_checkpoint = self._config.default_checkpoint
            except AttributeError:
                pass

        try:
            lora_result = find_and_verify_character_lora(
                danbooru_tag=research.danbooru_tag,
                display_name=research.display_name,
                series_name=research.series_name,
                appearance_description=research.appearance_summary or "",
                comfyui_url=comfyui_url,
                base_checkpoint=base_checkpoint,
                reference_images=research.reference_images_b64 or job.reference_images_b64,
            )
            self._verified_lora = lora_result
            latency = (time.time() - t0) * 1000
            job.stage_timings_ms["lora_search"] = latency
            job.stages_executed.append("lora_search")

            if lora_result.accepted:
                logger.info(
                    "[AnimePipeline] Character LoRA accepted: %s (score=%.1f)",
                    lora_result.lora_filename, lora_result.vision_score,
                )
                yield self._event("stage_complete", {
                    "stage": "lora_search",
                    "stage_num": 3,
                    "total_stages": 9,
                    "latency_ms": latency,
                    "accepted": True,
                    "lora_name": lora_result.lora_filename,
                    "vision_score": lora_result.vision_score,
                    "trigger_words": lora_result.trigger_words,
                })
            else:
                logger.info(
                    "[AnimePipeline] No character LoRA accepted for %s: %s",
                    research.display_name, lora_result.rejection_reason,
                )
                yield self._event("stage_complete", {
                    "stage": "lora_search",
                    "stage_num": 3,
                    "total_stages": 9,
                    "latency_ms": latency,
                    "accepted": False,
                    "rejection_reason": lora_result.rejection_reason,
                })

        except Exception as e:
            logger.warning("[AnimePipeline] LoRA stage failed (non-fatal): %s", e)
            latency = (time.time() - t0) * 1000
            job.stage_timings_ms["lora_search"] = latency
            yield self._event("stage_complete", {
                "stage": "lora_search",
                "stage_num": 3,
                "total_stages": 9,
                "latency_ms": latency,
                "accepted": False,
                "error": str(e),
                "skipped": True,
            })

    def _inject_character_lora(
        self, job: AnimePipelineJob
    ) -> None:
        """Prepend the verified character LoRA to every PassConfig in the layer plan.

        The character LoRA is placed first (highest priority) so it establishes
        the character identity before the stylistic base LoRAs apply.
        Trigger words are also injected into each pass's positive_override or
        tracked via job metadata.

        File-existence guard: if the cached ``lora_filename`` is no longer on
        disk (e.g., user cleared the ComfyUI loras folder), skip injection
        instead of letting ComfyUI error the whole pipeline.
        """
        if not self._verified_lora or not self._verified_lora.accepted:
            return
        if not job.layer_plan or not job.layer_plan.passes:
            return

        lora_name = self._verified_lora.lora_filename
        if not lora_file_exists(lora_name):
            logger.warning(
                "[AnimePipeline] Verified character LoRA '%s' missing on disk — skipping injection",
                lora_name,
            )
            # Record the miss in metadata so downstream stages can react.
            meta = job.metadata or {}
            meta["character_lora_missing"] = lora_name
            job.metadata = meta
            # Disable the verified slot so subsequent helpers do not re-attempt.
            self._verified_lora = None
            return

        lora_dict = {
            "name": lora_name,
            "strength_model": 0.85,
            "strength_clip": 0.85,
            "enabled": True,
        }

        for pass_cfg in job.layer_plan.passes:
            existing = pass_cfg.lora_models or []
            # Avoid duplicate injection on re-runs
            existing_names = {lora.get("name", "") for lora in existing}
            if lora_dict["name"] not in existing_names:
                pass_cfg.lora_models = [lora_dict] + existing

        # Inject trigger words into job metadata for downstream use
        if self._verified_lora.trigger_words:
            existing_meta = job.metadata or {}
            existing_meta["character_lora_triggers"] = self._verified_lora.trigger_words
            job.metadata = existing_meta

        logger.info(
            "[AnimePipeline] Injected character LoRA '%s' into %d passes",
            lora_dict["name"], len(job.layer_plan.passes),
        )

    def _inject_user_loras(self, job: AnimePipelineJob) -> None:
        """Inject user-specified LoRAs (from ``<lora:name:weight>`` tags) into all passes.

        File-existence guard: drop user LoRAs whose ``.safetensors`` is not
        actually present under ComfyUI/models/loras/. Missing files are
        recorded on ``job.metadata['user_loras_missing']`` so the frontend
        can warn the user, but the pipeline still runs with whatever survives.
        """
        if not job.user_loras or not job.layer_plan or not job.layer_plan.passes:
            return

        present: list[dict[str, Any]] = []
        missing: list[str] = []
        for ulora in job.user_loras:
            name = ulora.get("name", "")
            if lora_file_exists(name):
                present.append(ulora)
            else:
                missing.append(name)

        if missing:
            logger.warning(
                "[AnimePipeline] Skipping %d missing user LoRA(s): %s",
                len(missing), missing,
            )
            meta = job.metadata or {}
            meta["user_loras_missing"] = missing
            job.metadata = meta

        if not present:
            return

        # Replace job.user_loras with the filtered set so any later consumer
        # (e.g., manifest) sees only the LoRAs that were actually injected.
        job.user_loras = present

        injected = 0
        for pass_cfg in job.layer_plan.passes:
            existing = pass_cfg.lora_models or []
            existing_names = {lora.get("name", "") for lora in existing}
            for ulora in present:
                if ulora["name"] not in existing_names:
                    existing.append(ulora)
                    existing_names.add(ulora["name"])
                    injected += 1
            pass_cfg.lora_models = existing

        if injected:
            logger.info(
                "[AnimePipeline] Injected %d user LoRAs into %d passes: %s",
                len(present), len(job.layer_plan.passes),
                [l["name"] for l in present],
            )

    def _run_stage(
        self,
        stage_name: str,
        agent: Any,
        job: AnimePipelineJob,
        stage_num: int,
        total: int,
        extra: Optional[dict] = None,
    ) -> Generator[dict[str, Any], None, None]:
        """Run a single stage with event emission."""
        vram = self._config.vram

        # Log estimated memory mode for this pass
        res_w = self._config.portrait_res[0]
        res_h = self._config.portrait_res[1]
        if job.layer_plan:
            res_w = job.layer_plan.resolution_width or res_w
            res_h = job.layer_plan.resolution_height or res_h
        log_pass_memory_mode(stage_name, vram, res_w, res_h)

        # Free models between passes if configured
        if vram.unload_models_between_passes and self._config.comfyui_url:
            free_models_between_passes(
                self._config.comfyui_url,
                unload=True,
            )

        # Instant-cancel checkpoint: every stage transition is an
        # opportunity to bail out. The user's Stop button POSTs to
        # /api/anime-pipeline/cancel which flips the queue flag; we
        # honour it BEFORE starting the next agent so blocking calls
        # like critique (vision API) or upscale never even fire.
        if _is_cancel_requested(job.job_id):
            self._cancelled = True
            yield self._build_cancellation_event(job, stage_name, self._run_t0)
            return

        yield self._event("stage_start", {
            "stage": stage_name,
            "stage_num": stage_num,
            "total_stages": total,
            "vram_profile": vram.profile.value,
            **(extra or {}),
        })

        try:
            agent.execute(job)
        except Exception as e:
            logger.error("[AnimePipeline] Stage %s failed: %s", stage_name, e)
            yield self._event("stage_error", {
                "stage": stage_name,
                "error": str(e),
            })
            raise

        # Agent may fail silently by setting job.status = FAILED instead of raising
        if job.status == AnimePipelineStatus.FAILED:
            yield self._event("stage_error", {
                "stage": stage_name,
                "error": job.error or f"{stage_name} failed",
            })
            return

        latency = job.stage_timings_ms.get(stage_name, 0.0)
        yield self._event("stage_complete", {
            "stage": stage_name,
            "stage_num": stage_num,
            "total_stages": total,
            "latency_ms": latency,
            **(extra or {}),
        })

    def _save_intermediates(self, job: AnimePipelineJob) -> None:
        """Save intermediate images to disk via ResultStore."""
        try:
            paths = self._result_store.save_all(job)
            logger.info("[AnimePipeline] Saved %d items to %s", len(paths), self._config.intermediate_dir)
        except Exception as e:
            logger.warning("[AnimePipeline] Failed to save intermediates: %s", e)

    # ── 4-Agents council integration ────────────────────────────────

    def _run_council_reasoning(
        self, job: AnimePipelineJob
    ) -> Generator[dict[str, Any], None, None]:
        """Run 4-agent council pre-analysis for enhanced creative direction.

        Only runs when thinking_mode == 'multi-thinking'.
        Uses the council to deeply analyze the user's creative intent,
        producing structured guidance for the layer planner.
        """
        yield self._event("stage_start", {
            "stage": "council_reasoning",
            "stage_num": 3.5,
            "total_stages": 10,
            "description": "4-Agents council: analyzing creative intent",
            "vram_profile": self._config.vram.profile.value,
        })

        t0 = time.time()
        try:
            import asyncio

            # Build council prompt from pipeline context
            va = job.vision_analysis
            va_summary = ""
            if va:
                va_summary = (
                    f"Vision analysis detected: {', '.join(va.anime_tags[:15])}\n"
                    f"Character: {getattr(va, 'character_name', 'unknown')}\n"
                    f"Scene: {getattr(va, 'scene_description', '')}"
                )
            character_info = ""
            if self._research:
                character_info = (
                    f"Character: {self._research.display_name} from {self._research.series_name}\n"
                    f"Appearance: {self._research.appearance_summary or 'N/A'}"
                )

            council_prompt = (
                f"Analyze this anime image generation request and provide creative direction.\n\n"
                f"User prompt: {job.user_prompt}\n\n"
                f"{va_summary}\n{character_info}\n\n"
                f"Provide:\n"
                f"1. Key artistic elements to emphasize\n"
                f"2. Composition and framing suggestions\n"
                f"3. Color palette and lighting direction\n"
                f"4. Potential quality issues to watch for\n"
                f"5. Style-specific recommendations for anime rendering"
            )

            # Try to run council (async → sync bridge)
            guidance = self._invoke_council_sync(council_prompt, job.language)

            if guidance:
                job.council_guidance = guidance
                latency = (time.time() - t0) * 1000
                job.stage_timings_ms["council_reasoning"] = latency
                job.stages_executed.append("council_reasoning")

                yield self._event("council_reasoning", {
                    "key_points": guidance.get("key_points", []),
                    "confidence": guidance.get("confidence", 0.0),
                    "creative_direction": guidance.get("content", "")[:500],
                })
                yield self._event("stage_complete", {
                    "stage": "council_reasoning",
                    "stage_num": 3.5,
                    "total_stages": 10,
                    "latency_ms": latency,
                    "has_guidance": True,
                })
                logger.info(
                    "[AnimePipeline] Council reasoning complete (%.1fms, confidence=%.2f)",
                    latency, guidance.get("confidence", 0.0),
                )
            else:
                latency = (time.time() - t0) * 1000
                yield self._event("stage_complete", {
                    "stage": "council_reasoning",
                    "stage_num": 3.5,
                    "total_stages": 10,
                    "latency_ms": latency,
                    "has_guidance": False,
                    "skipped": True,
                })

        except Exception as e:
            logger.warning("[AnimePipeline] Council reasoning failed (non-fatal): %s", e)
            latency = (time.time() - t0) * 1000
            yield self._event("stage_complete", {
                "stage": "council_reasoning",
                "stage_num": 3.5,
                "total_stages": 10,
                "latency_ms": latency,
                "error": str(e),
                "skipped": True,
            })

    @staticmethod
    def _invoke_council_sync(prompt: str, language: str = "en") -> dict[str, Any] | None:
        """Invoke the 4-agent council synchronously.

        Returns a dict with 'content', 'key_points', 'confidence' or None on failure.
        """
        try:
            import asyncio
            from core.agentic.entrypoint import run_council, is_council_enabled

            if not is_council_enabled():
                logger.debug("[AnimePipeline] Council not enabled (AGENTIC_V1_ENABLED=false)")
                return None

            async def _run() -> dict[str, Any]:
                return await run_council(
                    original_message=prompt,
                    augmented_message=prompt,
                    language=language,
                    context_type="creative",
                    max_agent_iterations=1,  # single fast pass for image guidance
                )

            # Run async council in sync context
            try:
                loop = asyncio.get_running_loop()
                # Already in an async context — schedule as task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = loop.run_in_executor(pool, lambda: asyncio.run(_run()))
                    # Can't await here in sync — fall through to new loop
                    raise RuntimeError("Cannot run council in existing event loop")
            except RuntimeError:
                result = asyncio.run(_run())

            if isinstance(result, dict) and result.get("response"):
                return {
                    "content": result["response"],
                    "key_points": result.get("agent_trace_summary", {}).get("key_points", [])
                        if isinstance(result.get("agent_trace_summary"), dict) else [],
                    "confidence": result.get("agent_trace_summary", {}).get("confidence", 0.0)
                        if isinstance(result.get("agent_trace_summary"), dict) else 0.5,
                }
            return None

        except ImportError:
            logger.debug("[AnimePipeline] Council modules not available in this environment")
            return None
        except Exception as e:
            logger.warning("[AnimePipeline] Council invocation failed: %s", e)
            return None

    # ── Deep reasoning builders ─────────────────────────────────────

    @staticmethod
    def _build_vision_reasoning(job: AnimePipelineJob) -> dict[str, Any] | None:
        """Build reasoning payload from vision analysis results."""
        va = job.vision_analysis
        if not va:
            return None
        return {
            "stage": "vision_analysis",
            "anime_tags": va.anime_tags[:20] if va.anime_tags else [],
            "nsfw_level": getattr(va, "nsfw_level", "unknown"),
            "confidence": getattr(va, "confidence", 0.0),
            "character_detected": bool(getattr(va, "character_name", None)),
            "character_name": getattr(va, "character_name", None),
            "scene_description": getattr(va, "scene_description", ""),
            "style_tags": getattr(va, "style_tags", [])[:10],
            "quality_tags": getattr(va, "quality_tags", [])[:10],
        }

    @staticmethod
    def _build_detection_reasoning(job: AnimePipelineJob) -> dict[str, Any] | None:
        """Build reasoning payload from YOLO detection inpaint results."""
        # Check job metadata for detection results
        det_meta = job.stage_metadata.get("detection_inpaint", {}) if hasattr(job, "stage_metadata") else {}
        # Also check intermediates for detail_* stages
        detail_stages = [img for img in job.intermediates if img.stage.startswith("detail_")]
        if not detail_stages and not det_meta:
            return None

        regions_fixed = []
        for img in detail_stages:
            regions_fixed.append({
                "region_type": img.stage.replace("detail_", ""),
                "stage": img.stage,
            })

        return {
            "stage": "detection_inpaint",
            "total_regions_fixed": len(regions_fixed),
            "regions": regions_fixed,
            "models_used": len(regions_fixed),
            "reasoning": (
                f"YOLO detected and inpainted {len(regions_fixed)} regions: "
                + ", ".join(r["region_type"] for r in regions_fixed[:10])
            ) if regions_fixed else "No regions detected for inpainting",
        }

    @staticmethod
    def _event(event_type: str, data: dict) -> dict[str, Any]:
        """Build an SSE-ready event dict."""
        return {
            "event": f"anime_pipeline_{event_type}",
            "data": data,
        }

    @staticmethod
    def _now_iso() -> str:
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

    def _detect_character_from_vision(self, job: AnimePipelineJob) -> Optional[str]:
        """Extract detected character danbooru tag from vision analysis or research."""
        # Research already set it
        if self._research and self._research.danbooru_tag:
            return self._research.danbooru_tag

        va = job.vision_analysis
        if not va or not va.anime_tags:
            return None

        # Check if any vision tag matches a known character
        try:
            from .character_references import _CHARACTER_IDENTITY
            for tag in va.anime_tags[:5]:
                if tag in _CHARACTER_IDENTITY:
                    return tag
        except ImportError:
            pass

        # Also try detect_character from research module
        try:
            from .character_research import detect_character
            result = detect_character(job.user_prompt)
            if result:
                return result[0]  # danbooru_tag
        except ImportError:
            pass

        return None

    def _maybe_save_character_reference(self, job: AnimePipelineJob, best_score: float) -> None:
        """Auto-save the final image as a character reference if score is high enough."""
        if not self._detected_character:
            return
        if not job.final_image_b64:
            return
        try:
            from .character_references import save_as_reference
            saved = save_as_reference(self._detected_character, job.final_image_b64, best_score)
            if saved:
                logger.info("[AnimePipeline] Auto-saved character reference: %s (score=%.1f)",
                            saved, best_score)
        except Exception as e:
            logger.warning("[AnimePipeline] Could not save character reference: %s", e)

    def _augment_references_from_cache(
        self, job: AnimePipelineJob, danbooru_tag: str,
    ) -> None:
        """Safe-only reference augmentation from ``storage/character_refs/<tag>/``.

        - Never downloads new images from the internet.
        - Fills ``job.reference_images_b64`` only when empty.
        - Always attaches ``eye_detail`` (if the character has a detailed
          identity entry) to ``job.metadata['character_eye_detail']`` for
          the critique and detection-inpaint stages to consume.
        """
        if not danbooru_tag:
            return
        try:
            from .character_references import get_character_ref_set

            ref_set = get_character_ref_set(danbooru_tag)
        except Exception as exc:  # pragma: no cover - defensive
            logger.debug(
                "[AnimePipeline] character_refs cache lookup failed for %s: %s",
                danbooru_tag, exc,
            )
            return

        if ref_set.images_b64 and not job.reference_images_b64:
            job.reference_images_b64 = ref_set.images_b64[:3]
            logger.info(
                "[AnimePipeline] Loaded %d cached reference(s) for %s",
                len(job.reference_images_b64), danbooru_tag,
            )

        if ref_set.eye_detail:
            meta = job.metadata or {}
            meta["character_eye_detail"] = ref_set.eye_detail
            if ref_set.series_tag and "character_series_tag" not in meta:
                meta["character_series_tag"] = ref_set.series_tag
            job.metadata = meta

    # ── Eye Emergency Inpaint ────────────────────────────────────────

    def _run_eye_emergency_inpaint(
        self,
        job: AnimePipelineJob,
        critique: "Any",
    ) -> Generator[dict[str, Any], None, None]:
        """Run targeted eye/face inpaint with boosted denoise (0.55) when eye score < 7.

        Uses 4-agents council reasoning to generate improved eye-fix prompt when
        the council is available and eye score is critically low (< 5).
        Crops eye region from reference images when available.
        """
        eye_score = getattr(critique, "eye_consistency_score", 10)
        eye_issues = list(getattr(critique, "eye_issues", []))

        yield self._event("eye_emergency_start", {
            "eye_score": eye_score,
            "eye_issues": eye_issues[:5],
            "character": self._detected_character or "",
        })

        # Get character eye description from research
        char_eye_desc = ""
        if self._research and self._research.eyes:
            char_eye_desc = self._research.eyes.description

        # Crop reference eye/face regions when available
        reference_crops: list[str] = []
        if job.reference_images_b64 and eye_score < 6:
            reference_crops = self._crop_eye_regions_from_refs(job.reference_images_b64)
            if reference_crops:
                logger.info(
                    "[AnimePipeline] Eye emergency: %d reference eye crops prepared",
                    len(reference_crops),
                )

        # When eye score is critically low (< 5) AND council is available,
        # run a quick council pass focused on eye correction.
        if eye_score < 5 and self._is_council_available():
            council_prompt = (
                f"URGENT: Eye quality is critically low (score={eye_score}/10).\n"
                f"User prompt: {job.user_prompt}\n"
                f"Character: {self._detected_character or 'unknown'}\n"
                f"Eye description: {char_eye_desc or 'not available'}\n"
                f"Eye issues reported: {', '.join(eye_issues[:5])}\n\n"
                f"Provide precise inpainting guidance:\n"
                f"1. What exact eye features need correction?\n"
                f"2. Best positive prompt tags for anime eye quality?\n"
                f"3. Negative prompt tags to avoid these eye issues?\n"
                f"4. Recommended denoise strength (0.4-0.7 range)?"
            )
            guidance = self._invoke_council_sync(council_prompt, job.language)
            if guidance:
                yield self._event("eye_council_guidance", {
                    "eye_score": eye_score,
                    "guidance_summary": guidance.get("content", "")[:300],
                    "confidence": guidance.get("confidence", 0.0),
                })
                # Parse denoise recommendation from council if present
                content = guidance.get("content", "")
                import re as _re
                denoise_match = _re.search(r"denoise[:\s]+([0-9]\.[0-9]+)", content, _re.IGNORECASE)
                if denoise_match:
                    try:
                        recommended_denoise = float(denoise_match.group(1))
                        if 0.4 <= recommended_denoise <= 0.75:
                            eye_score_denoise = recommended_denoise
                        else:
                            eye_score_denoise = 0.55
                    except ValueError:
                        eye_score_denoise = 0.55
                else:
                    eye_score_denoise = 0.55
            else:
                eye_score_denoise = 0.55
        else:
            # Scale denoise inversely with eye score (lower eye score = higher denoise)
            # eye_score 6 → 0.50, eye_score 5 → 0.52, eye_score ≤4 → 0.55
            eye_score_denoise = max(0.45, min(0.60, 0.62 - (eye_score * 0.02)))

        try:
            self._detection_inpaint.execute_eye_focus(
                job,
                denoise_override=eye_score_denoise,
                reference_eye_crops=reference_crops or None,
                eye_issues=eye_issues,
                character_eye_description=char_eye_desc,
            )
        except Exception as exc:
            logger.warning("[AnimePipeline] Eye emergency inpaint failed (non-fatal): %s", exc)

        yield self._event("eye_emergency_complete", {
            "eye_score": eye_score,
            "denoise_used": eye_score_denoise,
            "crops_used": len(reference_crops),
        })

    def _crop_eye_regions_from_refs(self, reference_images_b64: list[str]) -> list[str]:
        """Crop eye/face region from reference images using YOLO detection.

        Priority: full_eyes > eyes > face (most precise first).
        Applies 20% padding and enforces minimum 256×256 via LANCZOS upscale.
        Returns base64 PNG crops (max 3). Falls back to empty list if YOLO unavailable.
        """
        try:
            import base64
            import io
            from PIL import Image

            crops: list[str] = []
            detector = self._detection_inpaint._detector

            for ref_b64 in reference_images_b64[:3]:
                detection = detector.detect(ref_b64)
                # Priority: most precise eye region first
                face_regions = (
                    detection.get("full_eyes") or
                    detection.get("eyes") or
                    detection.get("face")
                )
                if not face_regions:
                    continue

                # Decode image
                raw = ref_b64.split(",", 1)[-1] if "," in ref_b64 else ref_b64
                img = Image.open(io.BytesIO(base64.b64decode(raw))).convert("RGB")
                W, H = img.size

                best = max(face_regions, key=lambda r: r.confidence)

                # 20% padding on each side for context
                bw = max(best.x2 - best.x1, 1)
                bh = max(best.y2 - best.y1, 1)
                pad_x = int(bw * 0.20)
                pad_y = int(bh * 0.20)
                cx1 = max(0, best.x1 - pad_x)
                cy1 = max(0, best.y1 - pad_y)
                cx2 = min(W, best.x2 + pad_x)
                cy2 = min(H, best.y2 + pad_y)

                crop = img.crop((cx1, cy1, cx2, cy2))

                # Enforce minimum 256×256 — upscale small crops via LANCZOS
                cw, ch = crop.size
                if cw < 256 or ch < 256:
                    scale = max(256 / max(cw, 1), 256 / max(ch, 1))
                    crop = crop.resize(
                        (max(256, int(cw * scale)), max(256, int(ch * scale))),
                        Image.LANCZOS,
                    )

                buf = io.BytesIO()
                crop.save(buf, format="PNG")
                crops.append(base64.b64encode(buf.getvalue()).decode("ascii"))

            return crops
        except Exception as exc:
            logger.debug("[AnimePipeline] Reference eye crop failed: %s", exc)
            return []

    @staticmethod
    def _is_council_available() -> bool:
        """Check if the 4-agents council is available (fast, no import errors)."""
        try:
            from core.agentic.entrypoint import is_council_enabled
            return is_council_enabled()
        except Exception:
            return False

    # ── Full Re-plan ─────────────────────────────────────────────────

    def _run_full_replan(
        self,
        job: AnimePipelineJob,
        new_prompt: str,
    ) -> Generator[dict[str, Any], None, None]:
        """Re-run Layer Planning + Composition + Structure Lock with a new prompt.

        Called when beauty loop had 4 consecutive failures.
        Resets only the generation state; preserves vision analysis + character research.
        """
        # Swap to new prompt (original stored in metadata)
        job.metadata["original_prompt_attempt_1"] = job.user_prompt
        job.user_prompt = new_prompt

        # Reset generation state for attempt 2
        job.layer_plan = None
        job.structure_layers = []
        # Keep critique_results (for scoring history) but clear refine_rounds counter
        job.refine_rounds = 0

        logger.info("[AnimePipeline] Re-planning with new prompt: %s", new_prompt[:80])

        # Stage: Layer Planning (attempt 2)
        yield from self._run_stage(
            "layer_planning", self._planner, job, stage_num=4, total=9,
            extra={"attempt": 2},
        )

        if job.status == AnimePipelineStatus.FAILED:
            return

        # Stage: Composition Pass (attempt 2)
        yield from self._run_stage(
            "composition_pass", self._composition, job, stage_num=5, total=9,
            extra={"attempt": 2},
        )

        if job.status == AnimePipelineStatus.FAILED:
            return

        # Stage: Structure Lock (attempt 2)
        yield from self._run_stage(
            "structure_lock", self._structure, job, stage_num=6, total=9,
            extra={"attempt": 2},
        )

    def _generate_variant_prompt(self, original_prompt: str) -> str:
        """Return the user's original prompt VERBATIM for retry attempt 2.

        Previously this method called an LLM to paraphrase the prompt at
        ~95% semantic similarity, which caused attempt-2 outputs to drift
        away from the user's exact wording. The user explicitly requested
        100% fidelity on retry — no rephrasing, no additions, no removals.

        We keep the method name and signature so the orchestrator's
        re-plan flow stays unchanged; only the behavior is now identity.
        """
        logger.info(
            "[AnimePipeline] Retry-2 prompt fidelity: returning original prompt verbatim (100%% match)."
        )
        return original_prompt

    def _generate_variant_prompt_legacy_paraphrase(self, original_prompt: str) -> str:
        """DEPRECATED: paraphrasing variant kept for reference only. Not called."""
        try:
            import os
            import httpx

            system = (
                "You are a creative prompt engineer for anime image generation. "
                "Rephrase the given prompt with different wording while keeping "
                "95%+ of the semantic meaning intact. "
                "Keep all character names, series names, poses, expressions, colors, "
                "and key visual elements. Only change phrasing and word order. "
                "Output ONLY the rephrased prompt, no explanation."
            )
            user_msg = f"Original: {original_prompt}\n\nRephrased version:"

            # Try OpenAI first (cheapest model)
            openai_key = os.getenv("OPENAI_API_KEY")
            if openai_key:
                resp = httpx.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {openai_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user_msg},
                        ],
                        "max_tokens": 300,
                        "temperature": 0.7,
                    },
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    rephrased = data["choices"][0]["message"]["content"].strip()
                    if rephrased:
                        return rephrased

            # Try Gemini
            gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if gemini_key:
                resp = httpx.post(
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    "gemini-2.0-flash:generateContent",
                    headers={"X-goog-api-key": gemini_key},
                    json={
                        "contents": [{"parts": [{"text": system + "\n\n" + user_msg}]}],
                        "generationConfig": {"maxOutputTokens": 300, "temperature": 0.7},
                    },
                    timeout=15.0,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    text = (
                        data.get("candidates", [{}])[0]
                        .get("content", {})
                        .get("parts", [{}])[0]
                        .get("text", "")
                        .strip()
                    )
                    if text:
                        return text

        except Exception as exc:
            logger.warning("[AnimePipeline] Variant prompt generation failed: %s", exc)

        # Fallback: add style adjectives to create minor variation
        style_variants = [
            "highly detailed, masterpiece",
            "best quality, ultra detailed",
            "beautiful, intricate detail",
        ]
        import random as _rand
        suffix = _rand.choice(style_variants)
        return f"{original_prompt}, {suffix}"

    def _pick_best_intermediate(self, job: AnimePipelineJob) -> Optional[str]:
        """Pick the highest-scoring intermediate image from the job's history."""
        # Prefer the most recent YOLO-enhanced image with the highest critique score
        if job.final_image_b64:
            return job.final_image_b64
        for img in reversed(job.intermediates):
            if img.stage.startswith("detail_") or img.stage == "beauty_pass":
                return img.image_b64
        for img in reversed(job.intermediates):
            if img.image_b64:
                return img.image_b64
        return None

    def _build_cancellation_event(
        self, job: AnimePipelineJob, stage: str, t0: float,
    ) -> dict[str, Any]:
        """Snapshot the best-so-far image, mark the job complete, and
        return a ``pipeline_cancelled`` event dict.

        Called when the chatbot's job queue reports
        ``is_cancel_requested(job_id) == True`` between stages. The
        partial image is promoted to ``job.final_image_b64`` so the
        normal ``ap_result`` path downstream still emits a usable
        result instead of an empty manifest.
        """
        best = self._pick_best_intermediate(job)
        if best:
            job.final_image_b64 = best
        job.status = AnimePipelineStatus.COMPLETED
        job.completed_at = self._now_iso()
        job.total_latency_ms = (time.time() - t0) * 1000
        logger.info(
            "[AnimePipeline] job=%s cancelled at stage=%s (has_image=%s)",
            job.job_id, stage, bool(job.final_image_b64),
        )
        return self._event("pipeline_cancelled", {
            "job_id": job.job_id,
            "stage": stage,
            "has_image": bool(job.final_image_b64),
            "message": f"Đã ngưng pipeline tại stage {stage}",
        })
