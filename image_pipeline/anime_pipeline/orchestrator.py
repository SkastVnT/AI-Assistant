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

import logging
import os
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
from .result_store import ResultStore
from .character_research import (
    research_character,
    CharacterResearchResult,
)
from .lora_manager import (
    find_and_verify_character_lora,
    LoRAVerificationResult,
    get_cached_character_lora,
)

logger = logging.getLogger(__name__)


def _pipeline_enabled() -> bool:
    """Check IMAGE_PIPELINE_V2 feature flag."""
    flag = os.getenv("IMAGE_PIPELINE_V2", "").lower()
    return flag in ("1", "true", "yes", "on")


class AnimePipelineOrchestrator:
    """
    7-stage anime multi-pass pipeline orchestrator.

    Stages:
        1. vision_analysis    — Analyze input/references
        2. layer_planning     — Build structured LayerPlan
        3. composition_pass   — Generate draft via ComfyUI
        4. structure_lock     — Extract control layers
        5. beauty_pass        — ControlNet-guided redraw
        6. critique           — Vision-based quality scoring
        7. upscale            — RealESRGAN final upscale

    If critique fails, stages 5-6 repeat up to max_refine_rounds times.
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
        self._result_store = ResultStore(
            base_dir=self._config.intermediate_dir
        )
        self._detected_character: Optional[str] = None
        self._research: Optional[CharacterResearchResult] = None
        self._verified_lora: Optional[LoRAVerificationResult] = None

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

        yield self._event("pipeline_start", {
            "job_id": job.job_id,
            "user_prompt": job.user_prompt,
            "stages": [
                "vision_analysis", "character_research", "lora_search",
                "layer_planning", "composition_pass", "structure_lock",
                "beauty_pass", "critique", "detection_inpaint", "upscale",
            ],
        })

        try:
            # Stage 1: Vision Analysis
            yield from self._run_stage(
                "vision_analysis", self._vision, job, stage_num=1, total=8,
            )

            # Stage 1.5: Character Research (web search + reference download)
            yield from self._run_character_research(job)

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

            # Stage 2: Layer Planning
            yield from self._run_stage(
                "layer_planning", self._planner, job, stage_num=4, total=9,
            )

            # Inject verified character LoRA into all passes
            if self._verified_lora and self._verified_lora.accepted:
                self._inject_character_lora(job)

            # Stage 3: Composition Pass
            yield from self._run_stage(
                "composition_pass", self._composition, job, stage_num=5, total=9,
            )
            if job.status == AnimePipelineStatus.FAILED:
                yield self._event("pipeline_error", {"error": job.error, "job_id": job.job_id})
                return

            # Stage 4: Structure Lock
            yield from self._run_stage(
                "structure_lock", self._structure, job, stage_num=6, total=9,
            )

            # Stage 5-8: Beauty + Critique loop
            yield from self._beauty_critique_loop(job)

            # Stage 8.5: Detection-based detail inpaint (ADetailer-style)
            # Runs YOLO detection on beauty output, inpaints face/eyes/hands
            yield from self._run_detection_inpaint(job)

            # Stage 9: Upscale
            yield from self._run_stage(
                "upscale", self._upscale, job, stage_num=9, total=9,
            )

            # Finalize
            job.status = AnimePipelineStatus.COMPLETED
            job.completed_at = self._now_iso()
            job.total_latency_ms = (time.time() - t0) * 1000

            # Save intermediates if configured
            if self._config.save_intermediates:
                self._result_store.save_all(job)

            yield self._event("pipeline_complete", {
                "job_id": job.job_id,
                "status": "completed",
                "has_image": job.final_image_b64 is not None,
                "total_latency_ms": job.total_latency_ms,
                "stages_executed": job.stages_executed,
                "refine_rounds": job.refine_rounds,
                "models_used": job.models_used,
                "vram_profile": self._config.vram.profile.value,
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

        For character-detected prompts, the loop is more aggressive:
        eye/face must reach 8+ to pass. Max rounds increased to 4.
        """
        max_rounds = self._config.max_refine_rounds
        best_score = 0.0
        best_image_b64 = None
        critique_for_next_round = None
        eye_refine_round_used = False
        has_character = self._detected_character is not None

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

            # Beauty pass
            yield from self._run_stage(
                "beauty_pass", self._beauty, job, stage_num=5, total=7,
                extra={"round": round_num},
            )

            beauty_failed = (job.status == AnimePipelineStatus.FAILED)
            if beauty_failed:
                # Reset status so critique can still run using the last available image
                job.status = AnimePipelineStatus.CRITIQUING

            # Critique always runs — falls back to composition image if beauty failed
            yield from self._run_stage(
                "critique", self._critique, job, stage_num=6, total=7,
                extra={"round": round_num},
            )

            if beauty_failed:
                break  # don't loop for refinement if beauty couldn't produce an image

            # Check critique result
            latest_critique = job.critique_results[-1] if job.critique_results else None
            if latest_critique:
                critique_for_next_round = latest_critique
                score = latest_critique.overall_score
                if score > best_score:
                    best_score = score
                    # Get the beauty pass image
                    for img in reversed(job.intermediates):
                        if img.stage == "beauty_pass":
                            best_image_b64 = img.image_b64
                            break

                # Character-specific face/eye quality gate:
                # Even if overall passes, force refine if face or eyes are weak.
                # eye_reference_match_pct >= 95 required when reference images exist.
                face_weak = has_character and latest_critique.face_score < 8
                eye_ref_pct = getattr(latest_critique, "eye_reference_match_pct", 0.0)
                eye_ref_weak = eye_ref_pct > 0.0 and eye_ref_pct < 95.0
                eyes_weak = has_character and (
                    latest_critique.eye_consistency_score < 8 or eye_ref_weak
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

        yield self._event("stage_start", {
            "stage": "detection_inpaint",
            "stage_num": 8,
            "total_stages": 10,
            "description": "ADetailer: 27-model multi-region detection + inpaint",
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

        latency = job.stage_timings_ms.get("detection_inpaint", 0.0)
        yield self._event("stage_complete", {
            "stage": "detection_inpaint",
            "stage_num": 8,
            "total_stages": 10,
            "latency_ms": latency,
            "regions_processed": "detection_inpaint" in job.stages_executed,
        })

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
        })

        t0 = time.time()
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
        })

        t0 = time.time()

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
        """
        if not self._verified_lora or not self._verified_lora.accepted:
            return
        if not job.layer_plan or not job.layer_plan.passes:
            return

        lora_dict = {
            "name": self._verified_lora.lora_filename,
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
