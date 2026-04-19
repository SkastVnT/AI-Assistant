"""
FinalRanker — Score and rank candidate images for final selection.

Evaluates candidates on four axes:
  - face quality (weighted from face_score + eye_consistency_score)
  - clarity (structural quality: anatomy, composition, hands)
  - style consistency (style_score from critique)
  - artifact count (total issues found)

Selects the best candidate as winner and sorts remaining as runner-ups.
All candidates are always scored; debug mode is handled by the caller.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..schemas import (
    AnimePipelineJob,
    CritiqueReport,
    IntermediateImage,
    RankCandidate,
    RankResult,
)

logger = logging.getLogger(__name__)

# Scoring weights for composite score
_WEIGHT_FACE = 1.5
_WEIGHT_CLARITY = 1.2
_WEIGHT_STYLE = 1.0
_ARTIFACT_PENALTY_PER = 0.3
_ARTIFACT_PENALTY_CAP = 3.0
_TOTAL_POSITIVE_WEIGHT = _WEIGHT_FACE + _WEIGHT_CLARITY + _WEIGHT_STYLE

# Stages eligible for ranking
_RANKABLE_STAGES = frozenset({
    "beauty_pass", "refine_beauty", "upscale", "composition_pass", "cleanup_pass",
})

# Default scores when no critique is available
_DEFAULT_SCORE = 5.0


def score_candidate(
    image_b64: str,
    stage: str,
    critique: Optional[CritiqueReport] = None,
) -> RankCandidate:
    """Score a single candidate image.

    When a CritiqueReport is available, scores are derived from its
    per-dimension fields.  Otherwise, defaults are used.

    Returns a fully populated RankCandidate.
    """
    if critique:
        face_quality = _face_quality_from_critique(critique)
        clarity = _clarity_from_critique(critique)
        style_consistency = float(critique.style_score)
        artifact_count = len(critique.all_issues)
    else:
        face_quality = _DEFAULT_SCORE
        clarity = _DEFAULT_SCORE
        style_consistency = _DEFAULT_SCORE
        artifact_count = 0

    composite = _compute_composite(face_quality, clarity, style_consistency, artifact_count)

    return RankCandidate(
        image_b64=image_b64,
        stage=stage,
        critique=critique,
        face_quality=face_quality,
        clarity=clarity,
        style_consistency=style_consistency,
        artifact_count=artifact_count,
        composite_score=composite,
    )


def rank_candidates(candidates: list[RankCandidate]) -> RankResult:
    """Sort candidates by composite_score descending and pick winner.

    Returns a RankResult with the top candidate as winner and the
    rest as runner_ups.
    """
    if not candidates:
        return RankResult(total_candidates=0)

    sorted_cands = sorted(candidates, key=lambda c: c.composite_score, reverse=True)
    return RankResult(
        winner=sorted_cands[0],
        runner_ups=sorted_cands[1:],
        total_candidates=len(sorted_cands),
    )


class FinalRanker:
    """Rank all eligible candidate images from a pipeline job.

    Collects candidates from job intermediates, scores each using
    the most relevant CritiqueReport, and selects the best final image.
    """

    def execute(self, job: AnimePipelineJob) -> RankResult:
        """Score and rank all eligible candidates in the job."""
        candidates: list[RankCandidate] = []

        for img in job.intermediates:
            if img.stage not in _RANKABLE_STAGES:
                continue
            if not img.image_b64:
                continue

            critique = self._find_critique_for(img, job)
            cand = score_candidate(img.image_b64, img.stage, critique)
            candidates.append(cand)

        result = rank_candidates(candidates)

        if result.winner:
            logger.info(
                "[FinalRanker] Winner: stage=%s score=%.2f (of %d candidates)",
                result.winner.stage,
                result.winner.composite_score,
                result.total_candidates,
            )
        else:
            logger.warning("[FinalRanker] No candidates to rank")

        return result

    def _find_critique_for(
        self, img: IntermediateImage, job: AnimePipelineJob,
    ) -> Optional[CritiqueReport]:
        """Find the most relevant critique for an intermediate image.

        Beauty-pass and refine images get the latest critique.
        Upscale images inherit the last critique (they are upscaled
        versions of the beauty output).
        """
        if not job.critique_results:
            return None

        # Upscale and beauty stages use the latest critique
        if img.stage in ("beauty_pass", "refine_beauty", "upscale"):
            return job.critique_results[-1]

        # Earlier stages: use first available
        if job.critique_results:
            return job.critique_results[0]

        return None


# ── Scoring helpers ───────────────────────────────────────────────

def _face_quality_from_critique(c: CritiqueReport) -> float:
    """Weighted face quality from face_score and eye_consistency_score."""
    return (c.face_score * 1.5 + c.eye_consistency_score * 1.2) / 2.7


def _clarity_from_critique(c: CritiqueReport) -> float:
    """Structural clarity from anatomy, composition, and hands scores."""
    return (c.anatomy_score + c.composition_score + c.hands_score) / 3.0


def _compute_composite(
    face_quality: float,
    clarity: float,
    style_consistency: float,
    artifact_count: int,
) -> float:
    """Compute weighted composite score with artifact penalty."""
    positive = (
        face_quality * _WEIGHT_FACE
        + clarity * _WEIGHT_CLARITY
        + style_consistency * _WEIGHT_STYLE
    ) / _TOTAL_POSITIVE_WEIGHT

    penalty = min(artifact_count * _ARTIFACT_PENALTY_PER, _ARTIFACT_PENALTY_CAP)
    return max(positive - penalty, 0.0)
