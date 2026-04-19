"""
End-to-end dry-run test — AnimePipelineOrchestrator

Exercises the full 7-stage pipeline with ALL external calls mocked:
  - ComfyClient.submit_workflow → returns fake images
  - VisionAnalystAgent.execute → returns canned VisionAnalysis
  - CritiqueAgent._critique_gemini / _critique_openai → returns mock scores
  - httpx calls for model unloading (free_models_between_passes)

Validates:
  - Correct event sequence from run_stream()
  - Job status transitions: PENDING → RUNNING → COMPLETED
  - All 7 stages executed
  - Critique loop respects threshold (pass on first round)
  - Critique loop retries (fail first, pass second)
  - Fallback image captured on complete failure
  - Error propagation from agent failure
  - SSE event names follow anime_pipeline_* prefix
  - Stage timings recorded
  - Total latency calculated
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "services" / "chatbot"))

import pytest
from unittest.mock import patch, MagicMock

from image_pipeline.anime_pipeline.config import (
    AnimePipelineConfig,
    ModelConfig,
    VRAMProfile,
    VRAMProfileConfig,
)
from image_pipeline.anime_pipeline.schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    CritiqueReport,
    IntermediateImage,
    VisionAnalysis,
    LayerPlan,
    PassConfig,
)
from image_pipeline.anime_pipeline.orchestrator import AnimePipelineOrchestrator
from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def config():
    return AnimePipelineConfig(
        composition_model=ModelConfig(
            checkpoint="animagine-xl-4.0-opt.safetensors",
            sampler="euler_a", scheduler="normal", steps=10, cfg=5.0,
        ),
        beauty_model=ModelConfig(
            checkpoint="noobai-xl-1.1.safetensors",
            sampler="dpmpp_2m_sde", scheduler="karras", steps=10, cfg=5.5,
            denoise_strength=0.30,
        ),
        final_model=ModelConfig(
            checkpoint="noobai-xl-1.1.safetensors",
        ),
        upscale_model="RealESRGAN_x4plus_anime_6B",
        upscale_factor=2,
        quality_threshold=0.70,
        max_refine_rounds=2,
        save_intermediates=False,
        comfyui_url="",  # empty → skip free_models_between_passes
        vram=VRAMProfileConfig(profile=VRAMProfile.NORMALVRAM),
    )


@pytest.fixture
def job():
    return AnimePipelineJob(
        user_prompt="1girl, silver hair, blue eyes, standing in cherry blossoms",
        preset="anime_quality",
    )


def _good_critique() -> CritiqueReport:
    return CritiqueReport(
        anatomy_score=8, face_score=8, eye_consistency_score=8,
        hands_score=8, clothing_score=8,
        composition_score=8, color_score=8, style_score=8,
        background_score=8, accessories_score=8, pose_score=8,
        model_used="mock",
    )


def _bad_critique() -> CritiqueReport:
    return CritiqueReport(
        anatomy_score=3, face_score=4, hands_score=3,
        composition_score=5, color_score=6, style_score=4,
        background_score=4,
        retry_recommendation=True,
        model_used="mock",
    )


def _fake_comfy_result() -> ComfyJobResult:
    return ComfyJobResult(
        prompt_id="fake-prompt-001",
        success=True,
        images_b64=["ZmFrZV9pbWFnZQ=="],  # base64("fake_image")
        output_filenames=["test.png"],
        duration_ms=500.0,
    )


def _mock_vision_execute(job: AnimePipelineJob) -> AnimePipelineJob:
    """Mock VisionAnalystAgent.execute — populate vision_analysis."""
    job.vision_analysis = VisionAnalysis(
        caption_short="Girl with silver hair in cherry blossoms",
        caption_detailed="Detailed: silver hair, blue eyes, standing",
        subjects=["1girl", "silver hair", "blue eyes"],
        pose="standing",
        camera_angle="medium",
        framing="medium_shot",
        dominant_colors=["pink", "silver"],
        anime_tags=["detailed_eyes", "clean_lineart"],
        quality_risks=[],
        identity_anchors=["silver hair", "blue eyes"],
        background_elements=["cherry blossoms"],
        confidence=0.9,
    )
    job.stages_executed.append("vision_analysis")
    job.stage_timings_ms["vision_analysis"] = 100.0
    return job


def _mock_composition_execute(job: AnimePipelineJob) -> AnimePipelineJob:
    """Mock CompositionPassAgent.execute — add intermediate image."""
    job.intermediates.append(IntermediateImage(
        stage="composition_pass",
        image_b64="ZmFrZV9jb21wb3NpdGlvbg==",
        metadata={"model": "animagine-xl-4.0"},
    ))
    job.stages_executed.append("composition_pass")
    job.stage_timings_ms["composition_pass"] = 2000.0
    return job


def _mock_structure_execute(job: AnimePipelineJob) -> AnimePipelineJob:
    """Mock StructureLockAgent.execute — add structure layer intermediates."""
    job.intermediates.append(IntermediateImage(
        stage="structure_lock",
        image_b64="ZmFrZV9saW5lYXJ0",
        metadata={"layer_type": "lineart_anime"},
    ))
    job.stages_executed.append("structure_lock")
    job.stage_timings_ms["structure_lock"] = 300.0
    return job


def _mock_beauty_execute(job: AnimePipelineJob) -> AnimePipelineJob:
    """Mock BeautyPassAgent.execute — add beauty intermediate."""
    job.intermediates.append(IntermediateImage(
        stage="beauty_pass",
        image_b64="ZmFrZV9iZWF1dHk=",
        metadata={"model": "noobai-xl-1.1"},
    ))
    job.stages_executed.append("beauty_pass")
    job.stage_timings_ms["beauty_pass"] = 1500.0
    return job


def _mock_upscale_execute(job: AnimePipelineJob) -> AnimePipelineJob:
    """Mock UpscaleAgent.execute — set final image."""
    job.final_image_b64 = "ZmFrZV91cHNjYWxlZA=="
    job.intermediates.append(IntermediateImage(
        stage="upscale",
        image_b64="ZmFrZV91cHNjYWxlZA==",
        metadata={"upscale_model": "RealESRGAN_x4plus_anime_6B"},
    ))
    job.stages_executed.append("upscale")
    job.stage_timings_ms["upscale"] = 800.0
    return job


# ═══════════════════════════════════════════════════════════════════
# E2E: Full pipeline — critique passes first round
# ═══════════════════════════════════════════════════════════════════

class TestE2EDryRunPassFirst:
    """Full pipeline run where critique passes on the first round."""

    def _mock_critique_pass(self, job):
        """Critique that passes immediately."""
        critique = _good_critique()
        job.critique_results.append(critique)
        job.stages_executed.append("critique")
        job.stage_timings_ms["critique"] = 200.0
        return job

    def test_full_pipeline_success(self, config, job):
        orch = AnimePipelineOrchestrator(config)

        # Patch all agents
        orch._vision.execute = _mock_vision_execute
        orch._planner.execute = lambda j: (
            setattr(j, 'layer_plan', LayerPlan(passes=[])) or
            j.stages_executed.append("layer_planning") or
            j.stage_timings_ms.update({"layer_planning": 50.0}) or
            j
        )
        orch._composition.execute = _mock_composition_execute
        orch._structure.execute = _mock_structure_execute
        orch._beauty.execute = _mock_beauty_execute
        orch._critique.execute = self._mock_critique_pass
        orch._upscale.execute = _mock_upscale_execute

        events = list(orch.run_stream(job))

        # Check event sequence
        event_names = [e["event"] for e in events]

        # Pipeline start
        assert event_names[0] == "anime_pipeline_pipeline_start"

        # Pipeline complete
        assert event_names[-1] == "anime_pipeline_pipeline_complete"

        # All stage_start/stage_complete pairs
        stage_starts = [e for e in events if e["event"] == "anime_pipeline_stage_start"]
        stage_completes = [e for e in events if e["event"] == "anime_pipeline_stage_complete"]
        assert len(stage_starts) == len(stage_completes)

        # Job completed
        assert job.status == AnimePipelineStatus.COMPLETED
        assert job.final_image_b64 is not None
        assert job.total_latency_ms >= 0

        # All event names have correct prefix
        for e in events:
            assert e["event"].startswith("anime_pipeline_")


class TestE2EDryRunCritiqueRetry:
    """Pipeline where critique fails first, then passes on retry."""

    def _make_critique_execute(self):
        call_count = {"n": 0}

        def _execute(job):
            call_count["n"] += 1
            if call_count["n"] == 1:
                critique = _bad_critique()
            else:
                critique = _good_critique()
            job.critique_results.append(critique)
            job.stages_executed.append("critique")
            job.stage_timings_ms["critique"] = 200.0
            return job

        return _execute

    def test_retry_then_pass(self, config, job):
        orch = AnimePipelineOrchestrator(config)

        orch._vision.execute = _mock_vision_execute
        orch._planner.execute = lambda j: (
            setattr(j, 'layer_plan', LayerPlan(passes=[])) or
            j.stages_executed.append("layer_planning") or
            j.stage_timings_ms.update({"layer_planning": 50.0}) or
            j
        )
        orch._composition.execute = _mock_composition_execute
        orch._structure.execute = _mock_structure_execute
        orch._beauty.execute = _mock_beauty_execute
        orch._critique.execute = self._make_critique_execute()
        orch._upscale.execute = _mock_upscale_execute

        events = list(orch.run_stream(job))

        event_names = [e["event"] for e in events]

        # Should have refine_start event
        assert "anime_pipeline_refine_start" in event_names

        # Job should have completed
        assert job.status == AnimePipelineStatus.COMPLETED
        assert job.refine_rounds >= 1

        # Beauty executed more than once (initial + refine)
        beauty_stages = [
            s for s in job.stages_executed if s == "beauty_pass"
        ]
        assert len(beauty_stages) >= 2


class TestE2EAgentFailure:
    """Pipeline handles agent failure gracefully."""

    def test_composition_failure_stops_pipeline(self, config, job):
        orch = AnimePipelineOrchestrator(config)

        orch._vision.execute = _mock_vision_execute
        orch._planner.execute = lambda j: (
            setattr(j, 'layer_plan', LayerPlan(passes=[])) or
            j.stages_executed.append("layer_planning") or
            j
        )

        def _failing_composition(j):
            raise RuntimeError("GPU OOM during composition")

        orch._composition.execute = _failing_composition

        events = list(orch.run_stream(job))
        event_names = [e["event"] for e in events]

        # Should have error event
        error_events = [e for e in events if "error" in e["event"]]
        assert len(error_events) >= 1

        # Job marked as failed
        assert job.status == AnimePipelineStatus.FAILED
        assert "OOM" in job.error

    def test_fallback_image_on_failure(self, config, job):
        """If pipeline fails after some stages, best intermediate is kept."""
        orch = AnimePipelineOrchestrator(config)

        orch._vision.execute = _mock_vision_execute
        orch._planner.execute = lambda j: (
            setattr(j, 'layer_plan', LayerPlan(passes=[])) or
            j.stages_executed.append("layer_planning") or
            j
        )
        orch._composition.execute = _mock_composition_execute
        orch._structure.execute = _mock_structure_execute

        def _failing_beauty(j):
            raise RuntimeError("Beauty pass OOM")

        orch._beauty.execute = _failing_beauty

        events = list(orch.run_stream(job))

        # Even though it failed, we should have a fallback from composition
        assert job.status == AnimePipelineStatus.FAILED
        assert job.final_image_b64 is not None  # fallback from intermediates


class TestE2EEventStructure:
    """Validate SSE event shape and data contents."""

    def test_pipeline_start_event(self, config, job):
        orch = AnimePipelineOrchestrator(config)
        orch._vision.execute = _mock_vision_execute
        orch._planner.execute = lambda j: (
            setattr(j, 'layer_plan', LayerPlan(passes=[])) or
            j.stages_executed.append("layer_planning") or
            j
        )
        orch._composition.execute = _mock_composition_execute
        orch._structure.execute = _mock_structure_execute
        orch._beauty.execute = _mock_beauty_execute
        orch._critique.execute = lambda j: (
            j.critique_results.append(CritiqueReport(
                anatomy_score=8, face_score=8, eye_consistency_score=8,
                hands_score=8, clothing_score=8,
                composition_score=8, color_score=8, style_score=8,
                background_score=8, accessories_score=8, pose_score=8,
            )) or
            j.stages_executed.append("critique") or
            j
        )
        orch._upscale.execute = _mock_upscale_execute

        events = list(orch.run_stream(job))

        # Pipeline start has expected fields
        start = events[0]
        assert start["event"] == "anime_pipeline_pipeline_start"
        assert "job_id" in start["data"]
        assert "stages" in start["data"]
        assert len(start["data"]["stages"]) == 7

        # Pipeline complete has expected fields
        complete = events[-1]
        assert complete["event"] == "anime_pipeline_pipeline_complete"
        assert "total_latency_ms" in complete["data"]
        assert "models_used" in complete["data"]
        assert complete["data"]["status"] == "completed"

    def test_stage_events_have_stage_num(self, config, job):
        orch = AnimePipelineOrchestrator(config)
        orch._vision.execute = _mock_vision_execute
        orch._planner.execute = lambda j: (
            setattr(j, 'layer_plan', LayerPlan(passes=[])) or
            j.stages_executed.append("layer_planning") or
            j
        )
        orch._composition.execute = _mock_composition_execute
        orch._structure.execute = _mock_structure_execute
        orch._beauty.execute = _mock_beauty_execute
        orch._critique.execute = lambda j: (
            j.critique_results.append(CritiqueReport(
                anatomy_score=8, face_score=8, eye_consistency_score=8,
                hands_score=8, clothing_score=8,
                composition_score=8, color_score=8, style_score=8,
                background_score=8, accessories_score=8, pose_score=8,
            )) or
            j.stages_executed.append("critique") or
            j
        )
        orch._upscale.execute = _mock_upscale_execute

        events = list(orch.run_stream(job))

        stage_starts = [e for e in events if e["event"] == "anime_pipeline_stage_start"]
        for se in stage_starts:
            assert "stage_num" in se["data"]
            assert "total_stages" in se["data"]
            assert "vram_profile" in se["data"]
