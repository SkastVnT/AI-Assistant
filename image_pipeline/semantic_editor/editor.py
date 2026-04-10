"""
image_pipeline.semantic_editor.editor — SemanticEditor facade.

Stage 3 (§12): Semantic edit / generation pass.

This is the **single entry point** for the pipeline's generate/edit stage.
It routes to the primary backend (Qwen VPS) or falls through the API
fallback chain, wrapping results into the pipeline's StageResult contract.

Flow:
    1. Check if Qwen VPS is reachable → call QwenClient
    2. If VPS down or call fails → delegate to FallbackChain
    3. Wrap successful result into StageResult with ModelUsage

Integration:
    The future orchestrator.py will call:
        editor = SemanticEditor(...)
        stage_result = await editor.run(job)
        job.stage_results["generate"] = stage_result
"""

from __future__ import annotations

import asyncio
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
from image_pipeline.semantic_editor.qwen_client import (
    ConversationTurn,
    EditResponse,
    QwenClient,
)
from image_pipeline.semantic_editor.fallback_editors import (
    FallbackChain,
)

logger = logging.getLogger(__name__)


# ── Location mapping ─────────────────────────────────────────────────

_PROVIDER_TO_LOCATION = {
    "vps":     ExecutionLocation.VPS,
    "fal":     ExecutionLocation.API,
    "stepfun": ExecutionLocation.API,
}


class SemanticEditor:
    """
    Pipeline-integrated semantic editor.

    Owns Stage 3 of the 9-stage pipeline.  Given an ImageJob with its
    PromptSpec filled (Layers 1-2), runs the primary editor or falls
    back, and returns a StageResult.

    Config:
        All connection details are read from environment variables,
        following the same pattern as existing providers.

        VPS_BASE_URL       — vLLM endpoint  (default http://localhost:8000)
        VPS_API_KEY        — vLLM auth key  (default "EMPTY")
        FAL_API_KEY        — fal.ai key     (for Kontext + Nano-Banana)
        STEPFUN_API_KEY    — StepFun key    (for Step1X-Edit)
    """

    def __init__(
        self,
        vps_base_url: Optional[str] = None,
        vps_api_key: Optional[str] = None,
        fal_api_key: Optional[str] = None,
        stepfun_api_key: Optional[str] = None,
        prefer_vps: bool = True,
    ):
        # Primary: Qwen on VPS
        self._qwen = QwenClient(
            base_url=vps_base_url or os.environ.get("VPS_BASE_URL", "http://localhost:8000"),
            api_key=vps_api_key or os.environ.get("VPS_API_KEY", "EMPTY"),
        )

        # Fallback chain: Kontext → Step1X-Edit → Nano-Banana
        self._fallback = FallbackChain(
            fal_api_key=fal_api_key or os.environ.get("FAL_API_KEY", ""),
            stepfun_api_key=stepfun_api_key or os.environ.get("STEPFUN_API_KEY", ""),
        )

        self._prefer_vps = prefer_vps
        self._vps_available: Optional[bool] = None   # Cached health state

    # ── Main entry point ──────────────────────────────────────────

    async def run(self, job: ImageJob) -> StageResult:
        """
        Execute Stage 3: semantic edit or generation.

        Reads:
            job.prompt_spec.execution_prompt   — The model prompt (Layer 2)
            job.source_image_b64               — Source image (for edit)
            job.reference_images               — Additional references
            job.generation_params              — Width, height, seed, etc.

        Returns:
            StageResult with image_b64 / image_url and model_usage.
        """
        stage = job.get_stage("generate")
        stage.mark_running()
        t0 = time.time()

        instruction = (
            job.prompt_spec.execution_prompt
            or job.prompt_spec.planning_prompt
            or job.user_instruction
        )

        if not instruction:
            stage.mark_failed("No instruction available for generation")
            return stage

        # Decide whether this is an edit or a pure generation
        source_b64 = job.source_image_b64
        is_edit = job.is_edit and source_b64 is not None

        try:
            resp = await self._try_primary(job, instruction, source_b64, is_edit)
            if not resp or not resp.success:
                logger.info(
                    "[SemanticEditor] Primary failed (%s), trying fallback chain",
                    resp.error if resp else "unreachable",
                )
                resp = self._try_fallback(job, instruction, source_b64, is_edit)

        except Exception as e:
            logger.error("[SemanticEditor] Unexpected error: %s", e, exc_info=True)
            stage.mark_failed(str(e))
            return stage

        # ── Wrap result into StageResult ──────────────────────────
        latency = (time.time() - t0) * 1000

        if resp and resp.success:
            stage.image_b64 = resp.image_b64
            if not resp.image_b64 and resp.raw_text:
                # Kontext / Nano-Banana return URL in raw_text
                stage.image_url = resp.raw_text

            stage.location = _PROVIDER_TO_LOCATION.get(
                resp.provider, ExecutionLocation.API,
            )
            stage.model_usage = ModelUsage(
                provider=resp.provider,
                model=resp.model,
                location=stage.location,
                latency_ms=resp.latency_ms,
                cost_usd=self._estimate_cost(resp.model),
                stage="generate",
                success=True,
            )
            stage.mark_completed(latency_ms=latency)
            logger.info(
                "[SemanticEditor] Success via %s/%s (%.0f ms)",
                resp.provider, resp.model, latency,
            )
        else:
            error_msg = resp.error if resp else "All backends failed"
            stage.mark_failed(error_msg)

            # Record failed attempt in metadata
            job.run_metadata.add_error(
                stage="generate",
                error=error_msg,
                model=resp.model if resp else "",
            )

        return stage

    # ── Primary: Qwen VPS ─────────────────────────────────────────

    async def _try_primary(
        self,
        job: ImageJob,
        instruction: str,
        source_b64: Optional[str],
        is_edit: bool,
    ) -> Optional[EditResponse]:
        """Try Qwen-Image-Edit on VPS."""
        if not self._prefer_vps:
            return None

        # Check VPS health (cache result for this session)
        if self._vps_available is None:
            self._vps_available = await self._qwen.health_check()

        if not self._vps_available:
            logger.info("[SemanticEditor] VPS unavailable, skipping Qwen")
            return None

        # Collect reference image base64 data
        ref_b64_list = []
        for ref in job.reference_images:
            if ref.image_b64:
                ref_b64_list.append(ref.image_b64)

        # Build multi-turn history from prompt lineage
        history = self._build_history(job)

        try:
            if is_edit:
                resp = await self._qwen.edit(
                    instruction=instruction,
                    source_image_b64=source_b64,
                    reference_images_b64=ref_b64_list,
                    history=history,
                )
            else:
                resp = await self._qwen.generate(
                    prompt=instruction,
                    generation_params={
                        "temperature": 0.7,
                    },
                )

            if not resp.success:
                # Mark VPS as problematic to skip on subsequent calls
                self._vps_available = False

            return resp

        except Exception as e:
            logger.warning("[SemanticEditor] Qwen call failed: %s", e)
            self._vps_available = False
            return EditResponse(
                success=False,
                error=str(e),
                model="qwen-image-edit",
                provider="vps",
            )

    # ── Fallback chain ────────────────────────────────────────────

    def _try_fallback(
        self,
        job: ImageJob,
        instruction: str,
        source_b64: Optional[str],
        is_edit: bool,
    ) -> EditResponse:
        """Delegate to the FallbackChain (synchronous API calls)."""
        params = job.generation_params
        resp, attempts = self._fallback.edit(
            instruction=instruction,
            source_image_b64=source_b64 if is_edit else None,
            width=params.width,
            height=params.height,
            seed=params.seed,
        )

        # Log each attempt into run_metadata
        for attempt in attempts:
            if not attempt.success:
                job.run_metadata.add_error(
                    stage="generate",
                    error=attempt.error,
                    model=attempt.editor,
                )

        return resp

    # ── History builder ───────────────────────────────────────────

    @staticmethod
    def _build_history(job: ImageJob) -> list[ConversationTurn]:
        """
        Convert prompt lineage into ConversationTurn list for
        multi-turn context in Qwen.
        """
        turns: list[ConversationTurn] = []
        for prev_prompt in job.prompt_spec.prompt_lineage:
            turns.append(ConversationTurn(role="user", text=prev_prompt))
            # We don't have the previous assistant images in lineage,
            # but sending the text maintains semantic context.
            turns.append(ConversationTurn(role="assistant", text="[previous edit applied]"))
        return turns

    # ── Cost estimation ───────────────────────────────────────────

    @staticmethod
    def _estimate_cost(model: str) -> float:
        """Rough per-image cost based on model name."""
        return {
            "qwen-image-edit":  0.00,    # Self-hosted VPS
            "flux1-kontext":    0.025,
            "step1x-edit":      0.020,
            "nano-banana":      0.011,
        }.get(model, 0.025)

    # ── Resource cleanup ──────────────────────────────────────────

    async def close(self) -> None:
        """Release HTTP sessions."""
        await self._qwen.close()

    # ── VPS health reset (for retry after cooldown) ───────────────

    def reset_vps_state(self) -> None:
        """Clear cached VPS availability to re-check on next call."""
        self._vps_available = None
