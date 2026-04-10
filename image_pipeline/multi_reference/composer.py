"""
image_pipeline.multi_reference.composer — MultiRefComposer facade (Stage 4).

This is the **single entry point** for Stage 4 of the pipeline.
Called by the future orchestrator when ``job.needs_multi_ref`` is True.

Flow:
    1. ReferenceManager resolves all refs → RefPlan
    2. Build augmented prompt with image indices
    3. Route to FLUX.2 model via CapabilityRouter
    4. Flux2Composer.compose() → ComposeResponse
    5. Wrap into StageResult

Integration:
    composer = MultiRefComposer(bfl_api_key="...")
    stage_result = composer.run(job)
    job.stage_results["compose"] = stage_result
"""

from __future__ import annotations

import logging
import os
import time
from typing import Optional

from image_pipeline.job_schema import (
    ExecutionLocation,
    ImageJob,
    ModelUsage,
    StageResult,
    StageStatus,
)
from image_pipeline.multi_reference.reference_manager import ReferenceManager
from image_pipeline.multi_reference.flux2_composer import (
    ComposeResponse,
    Flux2Composer,
    FLUX2_MAX_REFS,
)

logger = logging.getLogger(__name__)


class MultiRefComposer:
    """
    Pipeline-integrated multi-reference composition.

    Owns Stage 4 (compose) of the 9-stage pipeline.

    Given an ImageJob whose ``reference_images`` list has >1 entry,
    resolves the images, builds a FLUX.2-optimized prompt, calls
    FLUX.2 via BFL API, and returns a StageResult.

    Config via env vars:
        BFL_API_KEY     — BFL API key (required for FLUX.2)
    """

    def __init__(
        self,
        bfl_api_key: Optional[str] = None,
        cache_dir: str = "storage/references",
        default_model: str = "flux2-pro",
    ):
        self._api_key = bfl_api_key or os.environ.get("BFL_API_KEY", "")
        self._ref_mgr = ReferenceManager(cache_dir=cache_dir)
        self._composer = Flux2Composer(api_key=self._api_key) if self._api_key else None
        self._default_model = default_model

    # ── Main entry point ──────────────────────────────────────────

    def run(self, job: ImageJob) -> StageResult:
        """
        Execute Stage 4: multi-reference composition.

        Reads:
            job.reference_images          — Tagged references
            job.source_image_b64          — Source image (becomes image 1)
            job.prompt_spec.execution_prompt — Base instruction
            job.generation_params         — Width, height, seed

        Returns:
            StageResult with composed image URL and model_usage.
        """
        stage = job.get_stage("compose")
        stage.mark_running()
        t0 = time.time()

        # ── Guard: skip if not multi-ref ──────────────────────────
        if not job.needs_multi_ref and not job.has_references:
            stage.mark_skipped("No multi-reference composition needed")
            return stage

        if not self._composer:
            stage.mark_failed("BFL_API_KEY not configured — cannot call FLUX.2")
            job.run_metadata.add_error(
                stage="compose", error="BFL_API_KEY missing",
            )
            return stage

        # ── 1. Resolve references ─────────────────────────────────
        try:
            max_refs = FLUX2_MAX_REFS.get(self._default_model, 8)
            ref_plan = self._ref_mgr.resolve(
                references=job.reference_images,
                max_refs=max_refs,
                source_image_b64=job.source_image_b64,
            )
        except Exception as e:
            stage.mark_failed(f"Reference resolution failed: {e}")
            job.run_metadata.add_error(stage="compose", error=str(e))
            return stage

        if ref_plan.count == 0:
            stage.mark_skipped("No resolvable references")
            return stage

        # ── 2. Build prompt ───────────────────────────────────────
        base_prompt = (
            job.prompt_spec.execution_prompt
            or job.prompt_spec.planning_prompt
            or job.user_instruction
        )
        augmented_prompt = ReferenceManager.build_ref_prompt(
            ref_plan, base_prompt,
        )

        # ── 3. Select model ───────────────────────────────────────
        model = self._select_model(job, ref_plan.count)

        # ── 4. Compose ────────────────────────────────────────────
        try:
            resp = self._composer.compose(
                prompt=augmented_prompt,
                ref_plan=ref_plan,
                model=model,
                width=job.generation_params.width,
                height=job.generation_params.height,
                seed=job.generation_params.seed,
                output_format=job.output_targets.output_format,
            )
        except Exception as e:
            stage.mark_failed(f"FLUX.2 composition failed: {e}")
            job.run_metadata.add_error(
                stage="compose", error=str(e), model=model,
            )
            return stage

        # ── 5. Wrap result ────────────────────────────────────────
        latency = (time.time() - t0) * 1000

        if resp.success:
            stage.image_url = resp.image_url
            stage.image_b64 = resp.image_b64
            stage.location = ExecutionLocation.API
            stage.model_usage = ModelUsage(
                provider=resp.provider,
                model=resp.model,
                location=ExecutionLocation.API,
                latency_ms=resp.latency_ms,
                cost_usd=resp.cost_usd,
                stage="compose",
                success=True,
            )
            stage.output["task_id"] = resp.task_id
            stage.output["refs_used"] = ref_plan.count
            stage.output["prompt_augmented"] = augmented_prompt[:500]
            stage.mark_completed(latency_ms=latency)

            # Record in run_metadata
            job.run_metadata.add_model_usage(stage.model_usage)

            logger.info(
                "[MultiRefComposer] Success: %s, %d refs, %.0f ms, $%.4f",
                model, ref_plan.count, latency, resp.cost_usd,
            )
        else:
            error_msg = resp.error or "FLUX.2 returned no image"
            stage.mark_failed(error_msg)
            job.run_metadata.add_error(
                stage="compose", error=error_msg, model=model,
            )

        return stage

    # ── Model selection ───────────────────────────────────────────

    def _select_model(self, job: ImageJob, ref_count: int) -> str:
        """
        Pick the best FLUX.2 model based on job + ref count.

        Rules:
            - If job prefers a specific model → use it
            - If >4 refs → must use pro or max (klein limited to 4)
            - Default to self._default_model
        """
        # Check job preferences
        for pref in job.preferred_models:
            if pref.startswith("flux2"):
                max_for_model = FLUX2_MAX_REFS.get(pref, 0)
                if max_for_model >= ref_count:
                    return pref

        # Klein can't handle >4 refs
        if ref_count > 4 and "klein" in self._default_model:
            return "flux2-pro"

        return self._default_model

    # ── Cleanup ───────────────────────────────────────────────────

    def close(self) -> None:
        """Release resources."""
        self._ref_mgr.close()
        if self._composer:
            self._composer.close()
