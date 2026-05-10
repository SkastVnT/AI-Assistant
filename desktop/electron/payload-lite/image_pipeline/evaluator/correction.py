"""
image_pipeline.evaluator.correction — Post-evaluation auto-correction loop.

When the Scorer finds failing dimensions, the CorrectionLoop decides:
    1. Which correction strategy to apply
    2. Which model/provider to use
    3. Whether to re-evaluate after correction
    4. When to give up (budget/round limits)

Integrates with: Scorer, CapabilityRouter, prompt_layers (Layer 5).
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from image_pipeline.job_schema import (
    EvalDimension,
    EvalResult,
    ImageJob,
    RefinementPlan,
    RefinementStrategy,
    RefinementTarget,
)

logger = logging.getLogger(__name__)

_CONFIGS_DIR = Path(__file__).resolve().parent.parent.parent / "configs"
_PIPELINE_YAML = _CONFIGS_DIR / "pipeline.yaml"


# ── Dimension → correction strategy mapping ───────────────────────

_DIM_TO_STRATEGY: dict[str, str] = {
    EvalDimension.INSTRUCTION_ADHERENCE: "semantic",
    EvalDimension.SEMANTIC_EDIT:         "semantic",
    EvalDimension.IDENTITY_CONSISTENCY:  "semantic",
    EvalDimension.MULTI_REF_QUALITY:     "composite",
    EvalDimension.DETAIL_HANDLING:       "fill",
    EvalDimension.TEXT_RENDERING:        "fill",
    EvalDimension.MULTI_TURN_STABILITY:  "semantic",
    EvalDimension.CORRECTION_SUCCESS:    "composite",
}

# Dimension → which region to target for spatial corrections
_DIM_TO_REGION: dict[str, str] = {
    EvalDimension.DETAIL_HANDLING:      "auto",  # ADetailer auto-detect
    EvalDimension.TEXT_RENDERING:       "text",
    EvalDimension.IDENTITY_CONSISTENCY: "face",
}

# Strategy → task type for routing
_STRATEGY_TO_TASK: dict[str, str] = {
    "semantic":  "semantic_edit",
    "fill":      "inpaint",
    "composite": "detail_fix",
}


@dataclass
class CorrectionRound:
    """Record of a single correction attempt."""
    round_number: int
    strategy: str
    targets: list[str]
    model_used: str
    location: str
    cost_usd: float
    latency_ms: float
    score_before: float
    score_after: float
    improved: bool
    failed_dims_before: list[str]
    failed_dims_after: list[str]


@dataclass
class CorrectionResult:
    """Aggregate result of the correction loop."""
    rounds: list[CorrectionRound] = field(default_factory=list)
    total_rounds: int = 0
    total_cost_usd: float = 0.0
    total_latency_ms: float = 0.0
    final_passed: bool = False
    final_score: float = 0.0
    final_eval: Optional[EvalResult] = None
    gave_up_reason: Optional[str] = None

    @property
    def improved(self) -> bool:
        if not self.rounds:
            return False
        return self.rounds[-1].score_after > self.rounds[0].score_before


class CorrectionLoop:
    """
    Orchestrates the evaluate → correct → re-evaluate cycle.

    Pipeline:
        1. Receive failed EvalResult
        2. Determine correction strategy from failing dimensions
        3. Build correction prompt (Layer 5)
        4. Route to appropriate model via CapabilityRouter
        5. Apply correction
        6. Re-evaluate
        7. Repeat or give up
    """

    def __init__(
        self,
        pipeline_cfg_path: str | Path | None = None,
    ):
        cfg = self._load_yaml(Path(pipeline_cfg_path or _PIPELINE_YAML))
        correction_cfg = cfg.get("correction", {})

        self._max_rounds: int = int(correction_cfg.get("max_rounds", 2))
        self._budget_usd: float = float(correction_cfg.get("budget_usd", 0.15))
        self._strategies: list[str] = correction_cfg.get(
            "strategies", ["semantic", "fill", "composite"]
        )
        self._escalation_cfg: dict = correction_cfg.get("escalation", {})
        self._local_fail_threshold: int = int(
            self._escalation_cfg.get("local_fail_threshold", 1)
        )

        logger.info(
            "CorrectionLoop: max_rounds=%d, budget=$%.2f, strategies=%s",
            self._max_rounds, self._budget_usd, self._strategies,
        )

    # ───────────────────────────────────────────────────────────────
    # Public API
    # ───────────────────────────────────────────────────────────────

    async def run(
        self,
        job: ImageJob,
        eval_result: EvalResult,
        output_image_path: str | Path,
        *,
        scorer: Any = None,          # evaluator.scorer.Scorer
        router: Any = None,          # workflow.capability_router.CapabilityRouter
        apply_correction_fn: Any = None,  # async (job, strategy, model, image_path) -> new_path
    ) -> CorrectionResult:
        """
        Run the correction loop.

        Args:
            job:                  The ImageJob being corrected.
            eval_result:          The EvalResult that triggered correction.
            output_image_path:    Path to the current (failing) output.
            scorer:               Scorer instance for re-evaluation.
            router:               CapabilityRouter for model selection.
            apply_correction_fn:  Async callback that applies the correction
                                  and returns the path to the corrected image.

        Returns:
            CorrectionResult with full round history.
        """
        result = CorrectionResult()
        current_eval = eval_result
        current_image = Path(output_image_path)
        spent_usd = 0.0
        local_fail_count = 0

        for round_num in range(self._max_rounds):
            # Budget check
            if spent_usd >= self._budget_usd:
                result.gave_up_reason = (
                    f"Budget exhausted: ${spent_usd:.3f} >= ${self._budget_usd:.3f}"
                )
                logger.info("Correction budget exhausted at round %d", round_num)
                break

            # Already passing?
            if current_eval.passed:
                break

            start_ms = time.monotonic() * 1000

            # 1. Determine strategy
            strategy, targets = self._pick_strategy(current_eval, local_fail_count)
            logger.info(
                "Correction round %d: strategy=%s, targets=%s",
                round_num, strategy, targets,
            )

            # 2. Route to model
            task_type = _STRATEGY_TO_TASK.get(strategy, "semantic_edit")
            model_name = "unknown"
            location = "api"

            if router:
                try:
                    # Escalate to remote if too many local failures
                    unavailable = set()
                    if local_fail_count >= self._local_fail_threshold:
                        unavailable.add("local")

                    route = router.route(task_type, unavailable=unavailable)
                    model_name = route.model
                    location = route.location
                except ValueError:
                    logger.warning(
                        "Router failed for task_type=%s, using default",
                        task_type,
                    )

            # 3. Apply correction
            score_before = current_eval.overall_score
            cost_usd = 0.0
            new_image_path = current_image

            if apply_correction_fn:
                try:
                    new_image_path = Path(await apply_correction_fn(
                        job, strategy, model_name, str(current_image)
                    ))
                    # Estimate cost from router
                    if router:
                        model_info = router.get_model(model_name)
                        if model_info:
                            cost_usd = model_info.cost_usd
                except Exception as e:
                    logger.error(
                        "Correction round %d failed: %s", round_num, str(e)[:300]
                    )
                    if location == "local":
                        local_fail_count += 1
                    round_record = CorrectionRound(
                        round_number=round_num,
                        strategy=strategy,
                        targets=targets,
                        model_used=model_name,
                        location=location,
                        cost_usd=0.0,
                        latency_ms=(time.monotonic() * 1000) - start_ms,
                        score_before=score_before,
                        score_after=score_before,
                        improved=False,
                        failed_dims_before=list(current_eval.failed_dimensions),
                        failed_dims_after=list(current_eval.failed_dimensions),
                    )
                    result.rounds.append(round_record)
                    continue

            # 4. Re-evaluate
            if scorer:
                try:
                    new_eval = await scorer.score(
                        job,
                        new_image_path,
                        force_dimensions=current_eval.evaluated,
                    )
                except Exception as e:
                    logger.error("Re-evaluation failed: %s", str(e)[:300])
                    new_eval = current_eval
            else:
                new_eval = current_eval

            # 5. Record round
            latency_ms = (time.monotonic() * 1000) - start_ms
            spent_usd += cost_usd

            improved = new_eval.overall_score > current_eval.overall_score
            if not improved and location == "local":
                local_fail_count += 1

            round_record = CorrectionRound(
                round_number=round_num,
                strategy=strategy,
                targets=targets,
                model_used=model_name,
                location=location,
                cost_usd=cost_usd,
                latency_ms=latency_ms,
                score_before=score_before,
                score_after=new_eval.overall_score,
                improved=improved,
                failed_dims_before=list(current_eval.failed_dimensions),
                failed_dims_after=list(new_eval.failed_dimensions),
            )
            result.rounds.append(round_record)

            # Update state for next round
            current_eval = new_eval
            if new_image_path != current_image:
                current_image = new_image_path

            logger.info(
                "Round %d: %.3f → %.3f (%s), cost=$%.3f",
                round_num,
                score_before,
                new_eval.overall_score,
                "improved" if improved else "no improvement",
                cost_usd,
            )

        # Finalize
        result.total_rounds = len(result.rounds)
        result.total_cost_usd = spent_usd
        result.total_latency_ms = sum(r.latency_ms for r in result.rounds)
        result.final_passed = current_eval.passed
        result.final_score = current_eval.overall_score
        result.final_eval = current_eval

        if not result.final_passed and not result.gave_up_reason:
            result.gave_up_reason = (
                f"Max rounds ({self._max_rounds}) reached without passing"
            )

        return result

    # ───────────────────────────────────────────────────────────────
    # Strategy selection
    # ───────────────────────────────────────────────────────────────

    def _pick_strategy(
        self,
        eval_result: EvalResult,
        local_fail_count: int,
    ) -> tuple[str, list[str]]:
        """
        Choose a correction strategy based on failing dimensions.

        Priority:
            1. Identity issues → semantic (re-run editor)
            2. Detail issues → fill (ADetailer/inpaint)
            3. Multiple failures → composite
            4. If local already failed → escalate strategy
        """
        failed = eval_result.failed_dimensions
        targets = list(eval_result.correction_targets) if eval_result.correction_targets else []

        if not failed:
            return "semantic", targets

        # Count strategy votes from failing dimensions
        strategy_votes: dict[str, int] = {}
        for dim in failed:
            strategy = _DIM_TO_STRATEGY.get(dim, "semantic")
            strategy_votes[strategy] = strategy_votes.get(strategy, 0) + 1

            # Add region targets
            region = _DIM_TO_REGION.get(dim)
            if region and region not in targets:
                targets.append(region)

        # Pick the strategy with the most votes
        best = max(strategy_votes, key=strategy_votes.get)  # type: ignore

        # Escalate to composite if multiple strategies are needed
        if len(strategy_votes) > 1 and len(failed) >= 3:
            best = "composite"

        # Escalate if local corrections have been failing
        if local_fail_count >= self._local_fail_threshold and best == "fill":
            best = "semantic"  # Use remote semantic editor

        # Validate against allowed strategies
        if best not in self._strategies:
            best = self._strategies[0] if self._strategies else "semantic"

        return best, targets

    # ───────────────────────────────────────────────────────────────
    # Helpers
    # ───────────────────────────────────────────────────────────────

    @staticmethod
    def _load_yaml(path: Path) -> dict[str, Any]:
        if not path.exists():
            logger.warning("Config not found: %s", path)
            return {}
        with open(path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
