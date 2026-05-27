"""
image_pipeline.reasoning.execution.correction_router
=====================================================

Spec-driven correction loop for a single rendered panel.

The router is a thin, pure orchestrator. All heavy work (scoring,
inpainting) is performed by injected callables — no model is loaded
here, no .env is read, no cross-layer imports. This keeps the layer
testable with stubs and reusable across Flask / FastAPI / batch contexts.

Loop
----
1. Score the current image via ``scorer_fn``.
2. If the score passes (``CorrectionScore.passed``) → stop.
3. If no actionable targets are returned → stop with reason
   ``"no_targets"``.
4. If we've already run ``max_passes`` correction rounds → stop with
   reason ``"max_passes_reached"``.
5. Otherwise call ``inpaint_runner_fn`` to produce new image bytes and
   re-score.

Stage gating
------------
``required_stages`` (the parser's stage list for the panel) is checked
once before entering the loop. If none of the inpaint-family stages
(``inpaint``, ``face_patch``, ``prop_patch``) are present, the panel
opted out of correction and the router returns immediately with
``gave_up_reason="not_eligible"``.

The full Cycle-1 alias set is honored via
:func:`image_pipeline.reasoning.execution.execution_plan.normalize_stages`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Iterable, Mapping, Optional, Protocol, Tuple

from image_pipeline.reasoning.schemas import SinglePanelSpec

from .execution_plan import StageKind, normalize_stages

# ---------------------------------------------------------------------------
# Protocols
# ---------------------------------------------------------------------------


class CorrectionScoreLike(Protocol):
    """Duck-typed result of a single scoring pass.

    Implementations only need attributes; ``CorrectionScore`` below is a
    convenience dataclass tests and callers can use directly.
    """

    passed: bool
    score: float
    failed_targets: Tuple[str, ...]
    reason: str


ScorerFn = Callable[[SinglePanelSpec, bytes], CorrectionScoreLike]
"""Callable ``scorer_fn(panel, image_bytes) -> CorrectionScoreLike``.

Wrap an async :class:`image_pipeline.evaluator.scorer.Scorer` with a
synchronous adapter at the call site if needed.
"""


InpaintRunnerFn = Callable[[SinglePanelSpec, bytes, Tuple[str, ...]], bytes]
"""Callable ``inpaint_runner_fn(panel, image_bytes, targets) -> bytes``.

Returns the corrected image bytes. Raises on unrecoverable failure;
the router catches and records the exception in
:attr:`CorrectionRound.error`.
"""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CorrectionScore:
    """Convenience implementation of :class:`CorrectionScoreLike`."""

    passed: bool
    score: float = 0.0
    failed_targets: Tuple[str, ...] = ()
    reason: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "score": self.score,
            "failed_targets": list(self.failed_targets),
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class CorrectionRound:
    """Record of a single score → (optional) inpaint iteration."""

    round_number: int
    score_before: float
    score_after: float
    targets: Tuple[str, ...]
    improved: bool
    inpainted: bool
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_number": self.round_number,
            "score_before": self.score_before,
            "score_after": self.score_after,
            "targets": list(self.targets),
            "improved": self.improved,
            "inpainted": self.inpainted,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class CorrectionResult:
    """Aggregate result of a correction loop."""

    panel_id: str
    image_bytes: bytes
    final_score: float
    passed: bool
    rounds: Tuple[CorrectionRound, ...] = ()
    gave_up_reason: str = ""
    initial_score: float = 0.0

    @property
    def total_rounds(self) -> int:
        return len(self.rounds)

    @property
    def improved(self) -> bool:
        if not self.rounds:
            return False
        return self.final_score > self.initial_score

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            # NOTE: image_bytes intentionally omitted — caller serializes
            # via base64 / file path according to its transport.
            "final_score": self.final_score,
            "passed": self.passed,
            "rounds": [r.to_dict() for r in self.rounds],
            "gave_up_reason": self.gave_up_reason,
            "initial_score": self.initial_score,
            "total_rounds": self.total_rounds,
            "improved": self.improved,
        }


# ---------------------------------------------------------------------------
# Eligibility helper
# ---------------------------------------------------------------------------


_INPAINT_FAMILY: frozenset[StageKind] = frozenset(
    {
        StageKind.INPAINT,
        StageKind.FACE_PATCH,
        StageKind.PROP_PATCH,
    }
)


def _is_eligible(required_stages: Iterable[str]) -> bool:
    """A panel is correction-eligible iff at least one inpaint-family
    stage was requested by the parser."""
    stages = normalize_stages(required_stages)
    return any(s in _INPAINT_FAMILY for s in stages)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def maybe_correct(
    panel: SinglePanelSpec,
    image_bytes: bytes,
    *,
    scorer_fn: ScorerFn,
    inpaint_runner_fn: InpaintRunnerFn,
    required_stages: Iterable[str] = (),
    max_passes: int = 2,
    extra_targets: Optional[Mapping[str, Any]] = None,  # noqa: ARG001 — reserved
) -> CorrectionResult:
    """Run the spec-driven correction loop on a single panel.

    Parameters
    ----------
    panel
        The :class:`SinglePanelSpec` whose render is being corrected.
    image_bytes
        The current rendered image.
    scorer_fn
        Injected scoring callable. See :data:`ScorerFn`.
    inpaint_runner_fn
        Injected inpaint callable. See :data:`InpaintRunnerFn`.
    required_stages
        Free-form stage names from the parser. Used only for
        eligibility gating. If none of ``{inpaint, face_patch,
        prop_patch}`` is requested, the loop short-circuits.
    max_passes
        Maximum number of inpaint rounds. ``0`` means score-only
        (no correction will ever be applied). Default ``2``.
    extra_targets
        Reserved for future use (per-stage hints). Currently ignored.

    Returns
    -------
    CorrectionResult
        Always returned — failures surface via ``passed`` /
        ``gave_up_reason`` rather than raising.
    """
    if scorer_fn is None:
        raise ValueError("maybe_correct requires a scorer_fn")
    if inpaint_runner_fn is None:
        raise ValueError("maybe_correct requires an inpaint_runner_fn")
    if max_passes < 0:
        raise ValueError(f"max_passes must be >= 0 (got {max_passes})")

    panel_id = panel.panel_id

    # Always score once so the caller has a meaningful initial_score.
    initial = _safe_score(scorer_fn, panel, image_bytes)
    current_image = image_bytes
    current_score = initial

    if not _is_eligible(required_stages):
        return CorrectionResult(
            panel_id=panel_id,
            image_bytes=current_image,
            final_score=current_score.score,
            passed=current_score.passed,
            rounds=(),
            gave_up_reason="" if current_score.passed else "not_eligible",
            initial_score=initial.score,
        )

    if current_score.passed:
        return CorrectionResult(
            panel_id=panel_id,
            image_bytes=current_image,
            final_score=current_score.score,
            passed=True,
            rounds=(),
            gave_up_reason="",
            initial_score=initial.score,
        )

    rounds: list[CorrectionRound] = []
    gave_up = ""

    for round_idx in range(max_passes):
        targets = tuple(current_score.failed_targets or ())
        if not targets:
            gave_up = "no_targets"
            break

        score_before = current_score.score
        try:
            new_image = inpaint_runner_fn(panel, current_image, targets)
        except Exception as exc:
            rounds.append(
                CorrectionRound(
                    round_number=round_idx + 1,
                    score_before=score_before,
                    score_after=score_before,
                    targets=targets,
                    improved=False,
                    inpainted=False,
                    error=f"inpaint_runner_fn raised: {exc}",
                )
            )
            gave_up = "inpaint_failed"
            break

        if not isinstance(new_image, (bytes, bytearray)) or not new_image:
            rounds.append(
                CorrectionRound(
                    round_number=round_idx + 1,
                    score_before=score_before,
                    score_after=score_before,
                    targets=targets,
                    improved=False,
                    inpainted=False,
                    error="inpaint_runner_fn returned empty bytes",
                )
            )
            gave_up = "inpaint_failed"
            break

        new_image = bytes(new_image)
        new_score = _safe_score(scorer_fn, panel, new_image)
        improved = new_score.score > score_before

        rounds.append(
            CorrectionRound(
                round_number=round_idx + 1,
                score_before=score_before,
                score_after=new_score.score,
                targets=targets,
                improved=improved,
                inpainted=True,
            )
        )

        # Always adopt the new image — the loop is monotonic toward more
        # iteration, but the final scoring decides pass/fail. Callers
        # that only want strictly-improving updates can wrap the runner.
        current_image = new_image
        current_score = new_score

        if current_score.passed:
            break
    else:
        # for/else: the loop ran max_passes times without break.
        if not current_score.passed:
            gave_up = "max_passes_reached"

    return CorrectionResult(
        panel_id=panel_id,
        image_bytes=current_image,
        final_score=current_score.score,
        passed=current_score.passed,
        rounds=tuple(rounds),
        gave_up_reason=gave_up,
        initial_score=initial.score,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _safe_score(
    scorer_fn: ScorerFn,
    panel: SinglePanelSpec,
    image_bytes: bytes,
) -> CorrectionScore:
    """Call ``scorer_fn`` and coerce its result to a :class:`CorrectionScore`."""
    try:
        raw = scorer_fn(panel, image_bytes)
    except Exception as exc:
        return CorrectionScore(
            passed=False,
            score=0.0,
            failed_targets=(),
            reason=f"scorer_fn raised: {exc}",
        )
    return CorrectionScore(
        passed=bool(getattr(raw, "passed", False)),
        score=float(getattr(raw, "score", 0.0) or 0.0),
        failed_targets=tuple(getattr(raw, "failed_targets", ()) or ()),
        reason=str(getattr(raw, "reason", "") or ""),
    )


__all__ = [
    "CorrectionResult",
    "CorrectionRound",
    "CorrectionScore",
    "CorrectionScoreLike",
    "InpaintRunnerFn",
    "ScorerFn",
    "maybe_correct",
]
