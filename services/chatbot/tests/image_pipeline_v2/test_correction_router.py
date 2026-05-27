"""
Tests for image_pipeline.reasoning.execution.correction_router — Cycle 4.

Coverage:
* Eligibility gating via required_stages.
* Score-only when initial pass succeeds.
* Single-pass correction when score → fail → success.
* Multi-pass correction up to max_passes; gives up with
  "max_passes_reached".
* Empty failed_targets → "no_targets".
* Inpaint runner exception → "inpaint_failed", loop halts.
* Inpaint runner returning empty bytes → "inpaint_failed".
* Scorer exception → score 0.0, reason captured (does not raise).
* max_passes=0 → score-only behaviour even when eligible and failing.
* Required-arg validation: missing scorer_fn / inpaint_runner_fn / negative max_passes.
* Round bookkeeping: round_number, score_before/after, improved flag,
  inpainted flag, error string.
* CorrectionResult.to_dict is JSON-serializable and omits image_bytes.
* Cross-layer hygiene: no load_dotenv / dotenv / services.chatbot import.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from image_pipeline.reasoning.execution import (
    CorrectionScore,
    maybe_correct,
)
from image_pipeline.reasoning.schemas import ShotType, SinglePanelSpec

# ---------------------------------------------------------------------------
# Fixtures + stubs
# ---------------------------------------------------------------------------


@pytest.fixture
def panel() -> SinglePanelSpec:
    return SinglePanelSpec(
        panel_id="p_corr_1",
        shot_type=ShotType.MEDIUM,
        scene_description="bedroom",
        action_description="a girl reading",
        aspect_ratio="1:1",
    )


class _ScriptedScorer:
    """Yields successive scripted CorrectionScore values; repeats the last."""

    def __init__(self, scripted):
        self.scripted = list(scripted)
        self.calls = []

    def __call__(self, panel, image_bytes):
        self.calls.append((panel.panel_id, len(image_bytes)))
        if not self.scripted:
            raise AssertionError("scorer called more times than scripted")
        if len(self.scripted) == 1:
            return self.scripted[0]
        return self.scripted.pop(0)


class _ScriptedInpainter:
    """Returns deterministic bytes; can be configured to raise."""

    def __init__(self, outputs=None, raise_on=None, return_empty_on=None):
        self.outputs = list(outputs or [b"img_v2", b"img_v3", b"img_v4"])
        self.raise_on = raise_on  # e.g. round index 0-based
        self.return_empty_on = return_empty_on
        self.calls = []

    def __call__(self, panel, image_bytes, targets):
        idx = len(self.calls)
        self.calls.append((panel.panel_id, len(image_bytes), tuple(targets)))
        if self.raise_on is not None and idx == self.raise_on:
            raise RuntimeError("inpaint backend down")
        if self.return_empty_on is not None and idx == self.return_empty_on:
            return b""
        if idx < len(self.outputs):
            return self.outputs[idx]
        return self.outputs[-1]


# ---------------------------------------------------------------------------
# Eligibility
# ---------------------------------------------------------------------------


class TestEligibility:
    def test_no_inpaint_stage_short_circuits_when_failing(self, panel):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.4, failed_targets=("face",)),
            ]
        )
        inpainter = _ScriptedInpainter()
        result = maybe_correct(
            panel,
            b"img_v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=(),  # no inpaint family
        )
        assert result.passed is False
        assert result.gave_up_reason == "not_eligible"
        assert result.total_rounds == 0
        assert inpainter.calls == []
        assert result.image_bytes == b"img_v1"

    def test_no_inpaint_stage_passes_through_when_passing(self, panel):
        scorer = _ScriptedScorer([CorrectionScore(passed=True, score=0.95)])
        inpainter = _ScriptedInpainter()
        result = maybe_correct(
            panel,
            b"img_v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=(),
        )
        assert result.passed is True
        assert result.gave_up_reason == ""

    @pytest.mark.parametrize(
        "stage", ["inpaint", "face_patch", "face", "background_patch", "prop_patch"]
    )
    def test_inpaint_family_is_eligible(self, panel, stage):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.3, failed_targets=("face",)),
                CorrectionScore(passed=True, score=0.9),
            ]
        )
        inpainter = _ScriptedInpainter()
        result = maybe_correct(
            panel,
            b"img_v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=(stage,),
        )
        assert result.gave_up_reason == ""
        assert result.passed is True


# ---------------------------------------------------------------------------
# Score-only paths
# ---------------------------------------------------------------------------


class TestScoreOnly:
    def test_initial_pass_skips_loop(self, panel):
        scorer = _ScriptedScorer([CorrectionScore(passed=True, score=0.92)])
        inpainter = _ScriptedInpainter()
        result = maybe_correct(
            panel,
            b"img_v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("face_patch",),
        )
        assert result.passed is True
        assert result.total_rounds == 0
        assert result.gave_up_reason == ""
        assert result.initial_score == 0.92
        assert result.final_score == 0.92
        assert inpainter.calls == []

    def test_max_passes_zero_is_score_only(self, panel):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.3, failed_targets=("face",)),
            ]
        )
        inpainter = _ScriptedInpainter()
        result = maybe_correct(
            panel,
            b"img_v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("face_patch",),
            max_passes=0,
        )
        assert result.passed is False
        assert result.total_rounds == 0
        # for/else branch sets max_passes_reached when loop body never runs.
        assert result.gave_up_reason == "max_passes_reached"
        assert inpainter.calls == []


# ---------------------------------------------------------------------------
# Correction loop
# ---------------------------------------------------------------------------


class TestCorrectionLoop:
    def test_single_pass_recovery(self, panel):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.4, failed_targets=("face",)),
                CorrectionScore(passed=True, score=0.88),
            ]
        )
        inpainter = _ScriptedInpainter(outputs=[b"img_v2"])
        result = maybe_correct(
            panel,
            b"img_v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("face_patch",),
            max_passes=2,
        )
        assert result.passed is True
        assert result.total_rounds == 1
        assert result.image_bytes == b"img_v2"
        assert result.improved is True
        assert result.initial_score == 0.4
        assert result.final_score == 0.88
        assert len(inpainter.calls) == 1
        # Targets propagated to inpainter.
        assert inpainter.calls[0][2] == ("face",)
        round0 = result.rounds[0]
        assert round0.round_number == 1
        assert round0.score_before == 0.4
        assert round0.score_after == 0.88
        assert round0.improved is True
        assert round0.inpainted is True
        assert round0.error == ""

    def test_max_passes_exhausted(self, panel):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.3, failed_targets=("face",)),
                CorrectionScore(passed=False, score=0.4, failed_targets=("face",)),
                CorrectionScore(passed=False, score=0.5, failed_targets=("face",)),
            ]
        )
        inpainter = _ScriptedInpainter(outputs=[b"v2", b"v3"])
        result = maybe_correct(
            panel,
            b"v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("face_patch",),
            max_passes=2,
        )
        assert result.passed is False
        assert result.total_rounds == 2
        assert result.gave_up_reason == "max_passes_reached"
        # Monotonic image adoption: keeps the last attempt.
        assert result.image_bytes == b"v3"
        # Improvement still recorded even though never passed.
        assert result.improved is True
        assert result.final_score == 0.5

    def test_no_targets_halts(self, panel):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.4, failed_targets=()),
            ]
        )
        inpainter = _ScriptedInpainter()
        result = maybe_correct(
            panel,
            b"v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("inpaint",),
        )
        assert result.passed is False
        assert result.gave_up_reason == "no_targets"
        assert result.total_rounds == 0
        assert inpainter.calls == []

    def test_inpaint_exception_halts_loop(self, panel):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.3, failed_targets=("face",)),
            ]
        )
        inpainter = _ScriptedInpainter(raise_on=0)
        result = maybe_correct(
            panel,
            b"v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("face_patch",),
            max_passes=2,
        )
        assert result.passed is False
        assert result.gave_up_reason == "inpaint_failed"
        assert result.total_rounds == 1
        assert result.rounds[0].inpainted is False
        assert "inpaint backend down" in result.rounds[0].error
        # Image untouched on failure.
        assert result.image_bytes == b"v1"

    def test_inpaint_empty_bytes_halts_loop(self, panel):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.3, failed_targets=("face",)),
            ]
        )
        inpainter = _ScriptedInpainter(return_empty_on=0)
        result = maybe_correct(
            panel,
            b"v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("face_patch",),
        )
        assert result.passed is False
        assert result.gave_up_reason == "inpaint_failed"
        assert result.rounds[0].inpainted is False
        assert "empty bytes" in result.rounds[0].error

    def test_scorer_exception_does_not_raise(self, panel):
        def bad_scorer(p, b):
            raise RuntimeError("VLM offline")

        inpainter = _ScriptedInpainter()
        result = maybe_correct(
            panel,
            b"v1",
            scorer_fn=bad_scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("face_patch",),
        )
        assert result.passed is False
        assert result.initial_score == 0.0
        # No targets → no_targets after initial failure.
        assert result.gave_up_reason == "no_targets"
        assert inpainter.calls == []

    def test_targets_evolve_per_round(self, panel):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.3, failed_targets=("face",)),
                CorrectionScore(
                    passed=False, score=0.5, failed_targets=("hands", "background")
                ),
                CorrectionScore(passed=True, score=0.9),
            ]
        )
        inpainter = _ScriptedInpainter(outputs=[b"v2", b"v3"])
        result = maybe_correct(
            panel,
            b"v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("inpaint",),
            max_passes=3,
        )
        assert result.passed is True
        assert [c[2] for c in inpainter.calls] == [
            ("face",),
            ("hands", "background"),
        ]


# ---------------------------------------------------------------------------
# Argument validation
# ---------------------------------------------------------------------------


class TestArgValidation:
    def test_missing_scorer_raises(self, panel):
        with pytest.raises(ValueError):
            maybe_correct(
                panel,
                b"v1",
                scorer_fn=None,  # type: ignore[arg-type]
                inpaint_runner_fn=_ScriptedInpainter(),
            )

    def test_missing_inpaint_raises(self, panel):
        with pytest.raises(ValueError):
            maybe_correct(
                panel,
                b"v1",
                scorer_fn=_ScriptedScorer([CorrectionScore(passed=True)]),
                inpaint_runner_fn=None,  # type: ignore[arg-type]
            )

    def test_negative_max_passes_rejected(self, panel):
        with pytest.raises(ValueError):
            maybe_correct(
                panel,
                b"v1",
                scorer_fn=_ScriptedScorer([CorrectionScore(passed=True)]),
                inpaint_runner_fn=_ScriptedInpainter(),
                max_passes=-1,
            )


# ---------------------------------------------------------------------------
# Result serialization
# ---------------------------------------------------------------------------


class TestResultSerialization:
    def test_to_dict_omits_image_bytes_and_is_json_safe(self, panel):
        scorer = _ScriptedScorer(
            [
                CorrectionScore(passed=False, score=0.3, failed_targets=("face",)),
                CorrectionScore(passed=True, score=0.88),
            ]
        )
        inpainter = _ScriptedInpainter(outputs=[b"v2"])
        result = maybe_correct(
            panel,
            b"v1",
            scorer_fn=scorer,
            inpaint_runner_fn=inpainter,
            required_stages=("face_patch",),
        )
        as_dict = result.to_dict()
        assert "image_bytes" not in as_dict
        assert as_dict["panel_id"] == panel.panel_id
        assert as_dict["passed"] is True
        assert as_dict["total_rounds"] == 1
        json.dumps(as_dict)  # must be JSON-serializable.

    def test_correction_score_round_trip(self):
        s = CorrectionScore(
            passed=False, score=0.4, failed_targets=("face", "hands"), reason="VLM said"
        )
        d = s.to_dict()
        json.dumps(d)
        assert d["failed_targets"] == ["face", "hands"]


# ---------------------------------------------------------------------------
# Cross-layer + shared-env hygiene
# ---------------------------------------------------------------------------


class TestCorrectionRouterHygiene:
    EXECUTION_DIR = _ROOT / "app" / "image_pipeline" / "reasoning" / "execution"

    def test_no_load_dotenv(self):
        offenders = [
            p.name
            for p in self.EXECUTION_DIR.glob("*.py")
            if "load_dotenv" in p.read_text(encoding="utf-8")
        ]
        assert offenders == []

    def test_no_dotenv_import(self):
        offenders = []
        for p in self.EXECUTION_DIR.glob("*.py"):
            txt = p.read_text(encoding="utf-8")
            if "from dotenv" in txt or "import dotenv" in txt:
                offenders.append(p.name)
        assert offenders == []

    def test_no_chatbot_or_evaluator_import(self):
        """Cycle 4 must NOT import the existing async CorrectionLoop or any
        chatbot module. The router is intentionally a pure orchestrator.

        Inspects ``import``/``from ... import`` statements only — docstring
        mentions of those module paths are allowed.
        """
        forbidden = ("services.chatbot", "core.", "image_pipeline.evaluator")
        offenders: list[tuple[str, str]] = []
        for p in self.EXECUTION_DIR.glob("*.py"):
            for line in p.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if not (stripped.startswith("import ") or stripped.startswith("from ")):
                    continue
                for needle in forbidden:
                    if needle in stripped:
                        offenders.append((p.name, stripped))
        assert offenders == [], f"forbidden imports: {offenders}"
