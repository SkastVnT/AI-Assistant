"""
Tests for the anime multi-pass pipeline (Phase 2 — new schemas + services).

Covers schemas, config loading, orchestrator flow, agent contracts, and new service modules.
Run: cd services/chatbot && pytest tests/test_anime_pipeline.py -v
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import httpx

# ── Ensure project root is importable ─────────────────────────────────
_root = Path(__file__).resolve().parents[3]  # AI-Assistant/
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "services" / "chatbot"))


# ═══════════════════════════════════════════════════════════════════════
# Schema tests
# ═══════════════════════════════════════════════════════════════════════

class TestAnimePipelineSchemas:
    """Test dataclass constructors and serialisation."""

    def test_job_creation_defaults(self):
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob, AnimePipelineStatus

        job = AnimePipelineJob(user_prompt="anime girl in sakura garden")
        assert job.user_prompt == "anime girl in sakura garden"
        assert job.status == AnimePipelineStatus.PENDING
        assert job.job_id  # auto-generated
        assert job.intermediates == []
        assert job.stage_timings_ms == {}

    def test_job_to_dict(self):
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob

        job = AnimePipelineJob(user_prompt="test prompt")
        d = job.to_dict()
        assert isinstance(d, dict)
        assert d["user_prompt"] == "test prompt"
        assert "job_id" in d

    def test_mark_stage_records_timing(self):
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob

        job = AnimePipelineJob(user_prompt="test")
        job.mark_stage("vision_analysis", 123.4)
        assert job.stage_timings_ms["vision_analysis"] == 123.4
        assert "vision_analysis" in job.stages_executed

    def test_add_intermediate_tracks_model(self):
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob

        job = AnimePipelineJob(user_prompt="test")
        job.add_intermediate("composition_pass", "base64data", checkpoint="animagine-xl-4.0")
        assert len(job.intermediates) == 1
        assert job.intermediates[0].stage == "composition_pass"
        assert "animagine-xl-4.0" in job.models_used

    def test_status_enum_values(self):
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        assert AnimePipelineStatus.PENDING.value == "pending"
        assert AnimePipelineStatus.CLEANUP.value == "cleanup"
        assert AnimePipelineStatus.COMPLETED.value == "completed"
        assert AnimePipelineStatus.FAILED.value == "failed"


class TestVisionAnalysis:
    """Test VisionAnalysis schema fields and backward compat."""

    def test_new_fields(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis

        va = VisionAnalysis(
            caption_short="A girl standing",
            subjects=["anime girl", "sakura tree"],
            pose="standing",
            camera_angle="front",
            framing="medium_shot",
            dominant_colors=["pink", "white"],
            anime_tags=["1girl", "cherry_blossoms"],
        )
        assert va.caption_short == "A girl standing"
        assert len(va.subjects) == 2
        assert va.dominant_colors == ["pink", "white"]

    def test_backward_compat_properties(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis

        va = VisionAnalysis(subjects=["girl", "cat"], dominant_colors=["red"])
        assert va.subject_description == "girl, cat"
        assert va.color_palette == ["red"]

    def test_to_dict(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis

        va = VisionAnalysis(caption_short="test", confidence=0.9)
        d = va.to_dict()
        assert d["caption_short"] == "test"
        assert d["confidence"] == 0.9


class TestPassConfig:
    """Test PassConfig dataclass."""

    def test_creation(self):
        from image_pipeline.anime_pipeline.schemas import PassConfig

        pc = PassConfig(
            pass_name="composition",
            model_slot="base",
            checkpoint="animagine-xl-4.0-opt.safetensors",
            width=832, height=1216,
            steps=28, cfg=5.0, denoise=1.0,
            positive_prompt="masterpiece, 1girl",
            negative_prompt="low quality",
        )
        assert pc.pass_name == "composition"
        assert pc.denoise == 1.0
        assert pc.control_inputs == []

    def test_to_dict(self):
        from image_pipeline.anime_pipeline.schemas import PassConfig

        pc = PassConfig(pass_name="beauty", steps=30)
        d = pc.to_dict()
        assert d["pass_name"] == "beauty"
        assert d["steps"] == 30

    def test_backward_compat_alias(self):
        from image_pipeline.anime_pipeline.schemas import LayerPassConfig, PassConfig

        assert LayerPassConfig is PassConfig


class TestControlInput:
    """Test ControlInput dataclass."""

    def test_creation(self):
        from image_pipeline.anime_pipeline.schemas import ControlInput

        ci = ControlInput(
            layer_type="lineart_anime",
            controlnet_model="control_v11p_sd15_lineart.safetensors",
            strength=0.85,
            start_percent=0.0,
            end_percent=0.8,
        )
        assert ci.layer_type == "lineart_anime"
        assert ci.strength == 0.85
        assert ci.image_b64 == ""  # not yet populated

    def test_to_dict_hides_image(self):
        from image_pipeline.anime_pipeline.schemas import ControlInput

        ci = ControlInput(layer_type="depth", image_b64="abc123")
        d = ci.to_dict()
        assert d["has_image"] is True
        assert "image_b64" not in d  # should not leak full base64


class TestLayerPlan:
    """Test LayerPlan with passes[] array, validation, and backward compat."""

    def _make_plan(self):
        from image_pipeline.anime_pipeline.schemas import LayerPlan, PassConfig, ControlInput

        return LayerPlan(
            scene_summary="Girl in cherry blossoms",
            subject_list=["anime girl"],
            camera="medium_shot",
            pose="standing",
            palette=["pink", "white"],
            lighting="soft",
            style_tags=["anime", "clean_lineart"],
            background_plan="cherry blossom park",
            negative_constraints=["low quality"],
            passes=[
                PassConfig(
                    pass_name="composition",
                    model_slot="base",
                    checkpoint="animagine-xl-4.0.safetensors",
                    width=832, height=1216, steps=28, cfg=5.0, denoise=1.0,
                    positive_prompt="masterpiece, 1girl",
                    negative_prompt="low quality",
                ),
                PassConfig(
                    pass_name="structure_lock",
                    model_slot="preprocessor",
                    checkpoint="",
                    width=832, height=1216, steps=0, cfg=0, denoise=0,
                ),
                PassConfig(
                    pass_name="cleanup",
                    model_slot="cleanup",
                    checkpoint="animagine-xl-4.0.safetensors",
                    width=832, height=1216, steps=24, cfg=5.5, denoise=0.35,
                    positive_prompt="masterpiece, 1girl",
                    negative_prompt="low quality",
                    control_inputs=[
                        ControlInput(layer_type="lineart_anime", strength=0.8),
                    ],
                ),
                PassConfig(
                    pass_name="beauty",
                    model_slot="final",
                    checkpoint="noobai-xl-1.1.safetensors",
                    width=832, height=1216, steps=30, cfg=5.0, denoise=0.45,
                    positive_prompt="masterpiece, 1girl",
                    negative_prompt="low quality",
                ),
                PassConfig(
                    pass_name="upscale",
                    model_slot="upscaler",
                    checkpoint="RealESRGAN_x4plus_anime_6B.pth",
                    width=1664, height=2432, steps=0, cfg=0, denoise=0,
                ),
            ],
        )

    def test_validate_valid_plan(self):
        plan = self._make_plan()
        errors = plan.validate()
        assert errors == [], f"Expected no errors, got: {errors}"

    def test_validate_missing_scene_summary(self):
        from image_pipeline.anime_pipeline.schemas import LayerPlan, PassConfig

        plan = LayerPlan(passes=[
            PassConfig(pass_name="composition", checkpoint="x.safetensors", steps=20),
        ])
        errors = plan.validate()
        assert "scene_summary is empty" in errors

    def test_validate_missing_composition_pass(self):
        from image_pipeline.anime_pipeline.schemas import LayerPlan, PassConfig

        plan = LayerPlan(
            scene_summary="test",
            passes=[PassConfig(pass_name="beauty", checkpoint="x.safetensors", steps=20)],
        )
        errors = plan.validate()
        assert "missing composition pass" in errors

    def test_validate_no_passes(self):
        from image_pipeline.anime_pipeline.schemas import LayerPlan

        plan = LayerPlan(scene_summary="test")
        errors = plan.validate()
        assert "no passes defined" in errors

    def test_resolution_from_first_pass(self):
        plan = self._make_plan()
        assert plan.resolution_width == 832
        assert plan.resolution_height == 1216

    def test_backward_compat_properties(self):
        plan = self._make_plan()
        assert plan.positive_prompt_base == "masterpiece, 1girl"
        assert plan.negative_prompt_base == "low quality"
        assert plan.composition_pass is not None
        assert plan.composition_pass.pass_name == "composition"
        assert plan.beauty_pass is not None
        assert plan.beauty_pass.pass_name == "beauty"
        assert plan.upscale_pass is True  # upscale pass exists

    def test_get_pass(self):
        plan = self._make_plan()
        assert plan.get_pass("cleanup") is not None
        assert plan.get_pass("nonexistent") is None

    def test_pass_sequencing(self):
        """Verify passes are in the expected order."""
        plan = self._make_plan()
        names = [p.pass_name for p in plan.passes]
        assert names == ["composition", "structure_lock", "cleanup", "beauty", "upscale"]

    def test_to_dict(self):
        plan = self._make_plan()
        d = plan.to_dict()
        assert d["scene_summary"] == "Girl in cherry blossoms"
        assert len(d["passes"]) == 5
        assert d["passes"][0]["pass_name"] == "composition"


class TestCritiqueReport:
    """Test CritiqueReport scoring math and properties."""

    def test_overall_score_weighted(self):
        from image_pipeline.anime_pipeline.schemas import CritiqueReport

        cr = CritiqueReport(
            anatomy_score=8, face_score=9, eye_consistency_score=8,
            hands_score=7, clothing_score=8,
            composition_score=8, color_score=8, style_score=8,
            background_score=7, accessories_score=7, pose_score=8,
        )
        # Weighted: 8*1.0 + 9*1.5 + 8*1.2 + 7*1.0 + 8*0.8 + 8*1.0 + 8*0.8 + 8*1.0 + 7*0.7 + 7*0.5 + 8*0.9
        total_weight = 1.0 + 1.5 + 1.2 + 1.0 + 0.8 + 1.0 + 0.8 + 1.0 + 0.7 + 0.5 + 0.9
        weighted_sum = 8*1.0 + 9*1.5 + 8*1.2 + 7*1.0 + 8*0.8 + 8*1.0 + 8*0.8 + 8*1.0 + 7*0.7 + 7*0.5 + 8*0.9
        expected = weighted_sum / total_weight
        assert abs(cr.overall_score - expected) < 0.01

    def test_passed_true_when_score_high(self):
        from image_pipeline.anime_pipeline.schemas import CritiqueReport

        cr = CritiqueReport(
            anatomy_score=8, face_score=8, eye_consistency_score=8,
            hands_score=8, clothing_score=8,
            composition_score=8, color_score=8, style_score=8,
            background_score=8, accessories_score=8, pose_score=8,
        )
        assert cr.overall_score >= 7.0
        assert cr.passed is True

    def test_passed_false_when_retry_recommended(self):
        from image_pipeline.anime_pipeline.schemas import CritiqueReport

        cr = CritiqueReport(
            anatomy_score=9, face_score=9, eye_consistency_score=9,
            hands_score=9, clothing_score=9,
            composition_score=9, color_score=9, style_score=9,
            background_score=9, accessories_score=9, pose_score=9,
            retry_recommendation=True,
        )
        assert cr.passed is False  # despite high scores

    def test_passed_false_when_score_low(self):
        from image_pipeline.anime_pipeline.schemas import CritiqueReport

        cr = CritiqueReport(
            anatomy_score=3, face_score=3, eye_consistency_score=3,
            hands_score=3, clothing_score=3,
            composition_score=3, color_score=3, style_score=3,
            background_score=3, accessories_score=3, pose_score=3,
        )
        assert cr.overall_score < 7.0
        assert cr.passed is False

    def test_all_issues_flattened(self):
        from image_pipeline.anime_pipeline.schemas import CritiqueReport

        cr = CritiqueReport(
            anatomy_issues=["bad arm"],
            face_issues=["asymmetric eyes"],
            hand_issues=["extra finger"],
        )
        assert len(cr.all_issues) == 3
        assert "bad arm" in cr.all_issues

    def test_backward_compat_alias(self):
        from image_pipeline.anime_pipeline.schemas import CritiqueResult, CritiqueReport

        assert CritiqueResult is CritiqueReport

    def test_to_dict(self):
        from image_pipeline.anime_pipeline.schemas import CritiqueReport

        cr = CritiqueReport(anatomy_score=7, face_score=8)
        d = cr.to_dict()
        assert d["anatomy_score"] == 7
        assert "overall_score" in d
        assert "passed" in d


# ═══════════════════════════════════════════════════════════════════════
# Config tests
# ═══════════════════════════════════════════════════════════════════════

class TestAnimePipelineConfig:
    """Test config loading and env overrides."""

    def test_load_config_returns_config(self):
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        assert config.composition_model
        assert config.beauty_model
        assert config.quality_threshold > 0
        assert config.max_refine_rounds >= 0

    def test_env_override_composition_model(self):
        from image_pipeline.anime_pipeline.config import load_config

        with patch.dict(os.environ, {"ANIME_PIPELINE_COMPOSITION_MODEL": "test-model-v1"}):
            config = load_config()
            assert config.composition_model.checkpoint == "test-model-v1"

    def test_env_override_quality_threshold(self):
        from image_pipeline.anime_pipeline.config import load_config

        with patch.dict(os.environ, {"ANIME_PIPELINE_QUALITY_THRESHOLD": "0.95"}):
            config = load_config()
            assert config.quality_threshold == 0.95

    def test_config_has_structure_layers(self):
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        assert len(config.structure_layers) > 0
        for layer in config.structure_layers:
            assert layer.layer_type
            assert layer.preprocessor
            assert layer.controlnet_model


# ═══════════════════════════════════════════════════════════════════════
# Orchestrator tests
# ═══════════════════════════════════════════════════════════════════════

class TestAnimePipelineOrchestrator:
    """Test orchestrator flow control."""

    def test_enabled_flag_false_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IMAGE_PIPELINE_V2", None)
            from image_pipeline.anime_pipeline.orchestrator import _pipeline_enabled
            assert not _pipeline_enabled()

    def test_enabled_flag_true(self):
        with patch.dict(os.environ, {"IMAGE_PIPELINE_V2": "true"}):
            from image_pipeline.anime_pipeline.orchestrator import _pipeline_enabled
            assert _pipeline_enabled()

    def test_orchestrator_creates_all_agents(self):
        from image_pipeline.anime_pipeline.orchestrator import AnimePipelineOrchestrator

        orch = AnimePipelineOrchestrator()
        assert orch._vision is not None
        assert orch._planner is not None
        assert orch._composition is not None
        assert orch._structure is not None
        assert orch._beauty is not None
        assert orch._critique is not None
        assert orch._upscale is not None
        assert orch._result_store is not None

    def test_run_stream_yields_pipeline_start(self):
        from image_pipeline.anime_pipeline.orchestrator import AnimePipelineOrchestrator
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob

        orch = AnimePipelineOrchestrator()
        job = AnimePipelineJob(user_prompt="test prompt")

        for agent_attr in ("_vision", "_planner", "_composition", "_structure", "_beauty", "_critique", "_upscale"):
            mock_agent = MagicMock()
            mock_agent.execute = MagicMock(return_value=job)
            setattr(orch, agent_attr, mock_agent)

        events = list(orch.run_stream(job))
        assert len(events) > 0
        assert events[0]["event"] == "anime_pipeline_pipeline_start"
        assert events[0]["data"]["job_id"] == job.job_id

    def test_run_stream_ends_with_complete(self):
        from image_pipeline.anime_pipeline.orchestrator import AnimePipelineOrchestrator
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob

        orch = AnimePipelineOrchestrator()
        job = AnimePipelineJob(user_prompt="test prompt")

        for agent_attr in ("_vision", "_planner", "_composition", "_structure", "_beauty", "_critique", "_upscale"):
            mock_agent = MagicMock()
            mock_agent.execute = MagicMock(return_value=job)
            setattr(orch, agent_attr, mock_agent)

        events = list(orch.run_stream(job))
        last_event = events[-1]
        assert last_event["event"] == "anime_pipeline_pipeline_complete"
        assert last_event["data"]["status"] == "completed"

    def test_run_stream_error_handling(self):
        from image_pipeline.anime_pipeline.orchestrator import AnimePipelineOrchestrator
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob

        orch = AnimePipelineOrchestrator()
        job = AnimePipelineJob(user_prompt="test prompt")

        mock_vision = MagicMock()
        mock_vision.execute = MagicMock(side_effect=RuntimeError("API down"))
        orch._vision = mock_vision

        events = list(orch.run_stream(job))
        event_types = [e["event"] for e in events]
        assert "anime_pipeline_pipeline_error" in event_types


# ═══════════════════════════════════════════════════════════════════════
# Agent contract tests
# ═══════════════════════════════════════════════════════════════════════

class TestLayerPlannerAgent:
    """Test the deterministic layer planner."""

    def test_execute_creates_layer_plan_with_passes(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import LayerPlannerAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        planner = LayerPlannerAgent(config)
        job = AnimePipelineJob(user_prompt="anime girl in cherry blossoms")
        result = planner.execute(job)

        plan = result.layer_plan
        assert plan is not None
        assert plan.scene_summary
        assert plan.subject_list
        assert len(plan.passes) >= 4  # composition, structure_lock, cleanup, beauty
        assert plan.positive_prompt_base  # backward compat
        assert plan.resolution_width > 0

    def test_pass_sequencing(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import LayerPlannerAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        planner = LayerPlannerAgent(config)
        job = AnimePipelineJob(user_prompt="anime girl standing")
        planner.execute(job)

        names = [p.pass_name for p in job.layer_plan.passes]
        assert names[0] == "composition"
        assert names[1] == "structure_lock"
        assert "beauty" in names

    def test_fast_quality_skips_upscale(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import LayerPlannerAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        planner = LayerPlannerAgent(config)
        job = AnimePipelineJob(user_prompt="quick anime sketch", quality_hint="fast")
        planner.execute(job)

        names = [p.pass_name for p in job.layer_plan.passes]
        assert "upscale" not in names

    def test_orientation_detection_portrait(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import LayerPlannerAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        from image_pipeline.anime_pipeline.config import load_config

        planner = LayerPlannerAgent(load_config())
        job = AnimePipelineJob(user_prompt="portrait of anime girl")
        assert planner._detect_orientation(job) == "portrait"

    def test_orientation_detection_landscape(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import LayerPlannerAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        from image_pipeline.anime_pipeline.config import load_config

        planner = LayerPlannerAgent(load_config())
        job = AnimePipelineJob(user_prompt="landscape scenery mountains")
        assert planner._detect_orientation(job) == "landscape"

    def test_plan_validation_passes(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import LayerPlannerAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        from image_pipeline.anime_pipeline.config import load_config

        planner = LayerPlannerAgent(load_config())
        job = AnimePipelineJob(user_prompt="anime girl with sword")
        planner.execute(job)
        errors = job.layer_plan.validate()
        assert errors == [], f"Validation errors: {errors}"


# ═══════════════════════════════════════════════════════════════════════
# Workflow builder tests
# ═══════════════════════════════════════════════════════════════════════

class TestWorkflowBuilder:
    """Test ComfyUI workflow JSON generation."""

    def test_txt2img_has_required_nodes(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        from image_pipeline.anime_pipeline.schemas import PassConfig

        wb = WorkflowBuilder()
        pc = PassConfig(
            pass_name="composition", checkpoint="test.safetensors",
            width=832, height=1216, steps=28, cfg=5.0, denoise=1.0,
            positive_prompt="masterpiece", negative_prompt="low quality",
        )
        wf = wb.build_txt2img(pc, seed=42)

        node_types = {n["class_type"] for n in wf.values()}
        assert "CheckpointLoaderSimple" in node_types
        assert "CLIPTextEncode" in node_types
        assert "KSampler" in node_types
        assert "VAEDecode" in node_types
        assert "SaveImage" in node_types

    def test_img2img_has_vae_encode(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        from image_pipeline.anime_pipeline.schemas import PassConfig

        wb = WorkflowBuilder()
        pc = PassConfig(pass_name="beauty", checkpoint="test.safetensors", steps=30)
        wf = wb.build_img2img(pc, source_b64="fake_b64", seed=42)

        node_types = {n["class_type"] for n in wf.values()}
        assert "LoadImageFromBase64" in node_types
        assert "VAEEncode" in node_types

    def test_controlnet_chain(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        from image_pipeline.anime_pipeline.schemas import PassConfig, ControlInput

        wb = WorkflowBuilder()
        pc = PassConfig(
            pass_name="beauty", checkpoint="test.safetensors", steps=30,
            positive_prompt="test", negative_prompt="bad",
            control_inputs=[
                ControlInput(layer_type="lineart", controlnet_model="cn_lineart.safetensors",
                             strength=0.8, image_b64="fake1"),
                ControlInput(layer_type="depth", controlnet_model="cn_depth.safetensors",
                             strength=0.5, image_b64="fake2"),
            ],
        )
        wf = wb.build_txt2img(pc, seed=42)

        node_types = [n["class_type"] for n in wf.values()]
        assert node_types.count("ControlNetApplyAdvanced") == 2
        assert node_types.count("ControlNetLoader") == 2

    def test_upscale_workflow(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        wf = wb.build_upscale("fake_b64", "RealESRGAN_x4plus_anime_6B.pth")

        node_types = {n["class_type"] for n in wf.values()}
        assert "UpscaleModelLoader" in node_types
        assert "ImageUpscaleWithModel" in node_types


# ═══════════════════════════════════════════════════════════════════════
# Feature flag integration
# ═══════════════════════════════════════════════════════════════════════

class TestFeatureFlag:
    """Test IMAGE_PIPELINE_V2 feature flag."""

    def test_flag_defaults_to_false(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("IMAGE_PIPELINE_V2", None)
            from core.feature_flags import FeatureFlags
            ff = FeatureFlags()
            assert not ff.image_pipeline_v2

    def test_flag_enabled_via_env(self):
        with patch.dict(os.environ, {"IMAGE_PIPELINE_V2": "true"}):
            from core.feature_flags import FeatureFlags
            ff = FeatureFlags()
            assert ff.image_pipeline_v2

    def test_flag_disabled_via_env(self):
        with patch.dict(os.environ, {"IMAGE_PIPELINE_V2": "false"}):
            from core.feature_flags import FeatureFlags
            ff = FeatureFlags()
            assert not ff.image_pipeline_v2


# ═══════════════════════════════════════════════════════════════════════
# Workflow Serializer tests
# ═══════════════════════════════════════════════════════════════════════

class TestWorkflowSerializer:
    """Test the workflow metadata wrapper and version helper."""

    def test_serialize_wraps_with_meta(self):
        from image_pipeline.anime_pipeline.workflow_serializer import serialize_workflow

        wf = {"1": {"class_type": "KSampler"}, "2": {"class_type": "VAEDecode"}}
        result = serialize_workflow(wf, pass_name="composition", job_id="job123")

        assert "workflow" in result
        assert result["workflow"] is wf
        meta = result["_meta"]
        assert meta["pass_name"] == "composition"
        assert meta["job_id"] == "job123"
        assert meta["node_count"] == 2
        assert "KSampler" in meta["node_classes"]
        assert "VAEDecode" in meta["node_classes"]
        assert "timestamp" in meta
        assert "version" in meta

    def test_serialize_extra_meta(self):
        from image_pipeline.anime_pipeline.workflow_serializer import serialize_workflow

        result = serialize_workflow(
            {"1": {"class_type": "Test"}},
            extra_meta={"seed": 42, "model": "animagine"},
        )
        assert result["_meta"]["seed"] == 42
        assert result["_meta"]["model"] == "animagine"

    def test_get_workflow_version(self):
        from image_pipeline.anime_pipeline.workflow_serializer import get_workflow_version

        v = get_workflow_version()
        assert isinstance(v, str)
        assert "." in v  # semver-like

    def test_version_matches_builder(self):
        from image_pipeline.anime_pipeline.workflow_serializer import get_workflow_version
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        assert wb.version == get_workflow_version()


# ═══════════════════════════════════════════════════════════════════════
# ComfyClient integration tests (mocked HTTP)
# ═══════════════════════════════════════════════════════════════════════

class TestComfyClientIntegration:
    """Integration tests for ComfyClient with mocked ComfyUI responses."""

    def _mock_comfy_success(self, prompt_id="abc123"):
        """Build mock responses for a successful ComfyUI generation.

        Returns a dict mapping (method, url_suffix) → httpx.Response.
        """
        import base64

        # Fake 1x1 red PNG
        fake_png = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
            "nGP4z8BQDwAEgAF/pooBPQAAAABJRU5ErkJggg=="
        )
        fake_b64 = base64.b64encode(fake_png).decode()

        prompt_resp = httpx.Response(
            200,
            json={"prompt_id": prompt_id},
            request=httpx.Request("POST", "http://test/prompt"),
        )

        history_resp = httpx.Response(
            200,
            json={
                prompt_id: {
                    "status": {"completed": True, "status_str": "success"},
                    "outputs": {
                        "9": {
                            "images": [
                                {"filename": "test_00001_.png", "subfolder": "", "type": "output"}
                            ]
                        }
                    },
                }
            },
            request=httpx.Request("GET", f"http://test/history/{prompt_id}"),
        )

        view_resp = httpx.Response(
            200,
            content=fake_png,
            request=httpx.Request("GET", "http://test/view"),
        )

        return prompt_resp, history_resp, view_resp, fake_b64

    def test_submit_workflow_success(self):
        """Full integration test: submit → poll → download, with mocked HTTP."""
        import httpx as _httpx
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        prompt_resp, history_resp, view_resp, fake_b64 = self._mock_comfy_success()

        call_count = {"history": 0}

        def mock_transport(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if request.method == "POST" and "/prompt" in url:
                return prompt_resp
            if "/history/" in url:
                call_count["history"] += 1
                return history_resp
            if "/view" in url:
                return view_resp
            return httpx.Response(404, request=request)

        client = ComfyClient(
            base_url="http://test:8188",
            timeout_s=10,
            max_retries=0,
        )

        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)

            def side_effect_post(url, **kwargs):
                return mock_transport(httpx.Request("POST", url))

            def side_effect_get(url, **kwargs):
                return mock_transport(httpx.Request("GET", url))

            mock_instance.post = MagicMock(side_effect=side_effect_post)
            mock_instance.get = MagicMock(side_effect=side_effect_get)
            MockClient.return_value = mock_instance

            with patch("image_pipeline.anime_pipeline.comfy_client.time.sleep"):
                result = client.submit_workflow(
                    {"1": {"class_type": "KSampler"}},
                    job_id="test-job",
                    pass_name="composition",
                )

        assert result.success is True
        assert result.prompt_id == "abc123"
        assert len(result.images_b64) == 1
        assert result.duration_ms >= 0  # may be ~0 with mocked sleep
        assert result.error == ""

    def test_submit_workflow_validation_error(self):
        """ComfyUI rejects invalid workflow with node errors."""
        import httpx as _httpx
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        error_resp = httpx.Response(
            400,
            json={
                "error": {"message": "Invalid node configuration"},
                "node_errors": {
                    "3": {"class_type": "BadNode", "errors": ["Unknown node type"]}
                },
            },
            request=httpx.Request("POST", "http://test/prompt"),
        )

        client = ComfyClient(base_url="http://test:8188", max_retries=0)

        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.post = MagicMock(return_value=error_resp)
            MockClient.return_value = mock_instance

            result = client.submit_workflow(
                {"1": {"class_type": "BadNode"}},
                job_id="err-job",
                pass_name="test",
            )

        assert result.success is False
        assert "rejected" in result.error.lower()
        assert "node_errors" in result.error
        assert result.validation_error  # non-empty

    def test_submit_workflow_retry_on_connect_error(self):
        """Retry with backoff when ComfyUI is temporarily unreachable."""
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        prompt_resp, history_resp, view_resp, _ = self._mock_comfy_success()
        attempts = {"n": 0}

        client = ComfyClient(
            base_url="http://test:8188", timeout_s=10, max_retries=2,
        )

        def mock_post(url, **kwargs):
            attempts["n"] += 1
            if attempts["n"] <= 2:
                raise httpx.ConnectError("Connection refused")
            return prompt_resp

        def mock_get(url, **kwargs):
            if "/history/" in str(url):
                return history_resp
            if "/view" in str(url):
                return view_resp
            return httpx.Response(404, request=httpx.Request("GET", url))

        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.post = MagicMock(side_effect=mock_post)
            mock_instance.get = MagicMock(side_effect=mock_get)
            MockClient.return_value = mock_instance

            with patch("image_pipeline.anime_pipeline.comfy_client.time.sleep"):
                result = client.submit_workflow(
                    {"1": {"class_type": "KSampler"}},
                    job_id="retry-job",
                    pass_name="beauty",
                )

        assert result.success is True
        assert attempts["n"] == 3  # 2 failures + 1 success

    def test_cancel_sets_cancelled_flag(self):
        """cancel() sets internal flag and posts /interrupt."""
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        client = ComfyClient(base_url="http://test:8188")

        interrupt_resp = httpx.Response(
            200, request=httpx.Request("POST", "http://test/interrupt"),
        )

        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.post = MagicMock(return_value=interrupt_resp)
            MockClient.return_value = mock_instance

            cancelled = client.cancel("prompt-xyz")

        assert cancelled is True
        assert client._is_cancelled("prompt-xyz")

    def test_health_check_success(self):
        """check_health returns True when ComfyUI is alive."""
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        client = ComfyClient(base_url="http://test:8188")
        stats_resp = httpx.Response(
            200,
            json={"system": {"gpu": "RTX 3060"}},
            request=httpx.Request("GET", "http://test/system_stats"),
        )

        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get = MagicMock(return_value=stats_resp)
            MockClient.return_value = mock_instance

            assert client.check_health() is True

    def test_health_check_failure(self):
        """check_health returns False on connection error."""
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        client = ComfyClient(base_url="http://test:8188")

        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.get = MagicMock(side_effect=httpx.ConnectError("refused"))
            MockClient.return_value = mock_instance

            assert client.check_health() is False

    def test_debug_mode_saves_workflow_json(self, tmp_path):
        """Debug mode saves workflow JSON with metadata wrapper."""
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        prompt_resp, history_resp, view_resp, _ = self._mock_comfy_success()
        client = ComfyClient(
            base_url="http://test:8188",
            debug_mode=True,
            debug_dir=str(tmp_path / "debug"),
            max_retries=0,
        )

        def mock_post(url, **kwargs):
            return prompt_resp

        def mock_get(url, **kwargs):
            if "/history/" in str(url):
                return history_resp
            if "/view" in str(url):
                return view_resp
            return httpx.Response(404, request=httpx.Request("GET", url))

        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.post = MagicMock(side_effect=mock_post)
            mock_instance.get = MagicMock(side_effect=mock_get)
            MockClient.return_value = mock_instance

            with patch("image_pipeline.anime_pipeline.comfy_client.time.sleep"):
                result = client.submit_workflow(
                    {"1": {"class_type": "KSampler"}},
                    job_id="debug-job",
                    pass_name="composition",
                )

        assert result.success is True
        assert result.workflow_file
        wf_path = Path(result.workflow_file)
        assert wf_path.exists()

        saved = json.loads(wf_path.read_text(encoding="utf-8"))
        assert "_meta" in saved
        assert saved["_meta"]["pass_name"] == "composition"
        assert saved["_meta"]["job_id"] == "debug-job"
        assert "workflow" in saved

    def test_debug_mode_saves_images(self, tmp_path):
        """Debug mode saves output images with correct debug filenames."""
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        prompt_resp, history_resp, view_resp, _ = self._mock_comfy_success()
        debug_dir = tmp_path / "debug"
        client = ComfyClient(
            base_url="http://test:8188",
            debug_mode=True,
            debug_dir=str(debug_dir),
            max_retries=0,
        )

        def mock_post(url, **kwargs):
            return prompt_resp

        def mock_get(url, **kwargs):
            if "/history/" in str(url):
                return history_resp
            if "/view" in str(url):
                return view_resp
            return httpx.Response(404, request=httpx.Request("GET", url))

        with patch("image_pipeline.anime_pipeline.comfy_client.httpx.Client") as MockClient:
            mock_instance = MagicMock()
            mock_instance.__enter__ = MagicMock(return_value=mock_instance)
            mock_instance.__exit__ = MagicMock(return_value=False)
            mock_instance.post = MagicMock(side_effect=mock_post)
            mock_instance.get = MagicMock(side_effect=mock_get)
            MockClient.return_value = mock_instance

            with patch("image_pipeline.anime_pipeline.comfy_client.time.sleep"):
                result = client.submit_workflow(
                    {"1": {"class_type": "KSampler"}},
                    job_id="img-job",
                    pass_name="composition",
                )

        assert result.success is True
        assert len(result.output_paths) == 1
        img_path = Path(result.output_paths[0])
        assert img_path.exists()
        assert img_path.name == "base.png"  # composition → base.png

    def test_workflow_version_on_result(self):
        """ComfyJobResult carries workflow_version."""
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult

        r = ComfyJobResult()
        assert r.workflow_version
        assert "." in r.workflow_version

    def test_url_from_env(self):
        """ComfyClient reads URL from ANIME_PIPELINE_COMFYUI_URL env."""
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        with patch.dict(os.environ, {"ANIME_PIPELINE_COMFYUI_URL": "http://gpu-box:9999"}):
            client = ComfyClient()
            assert client.base_url == "http://gpu-box:9999"

    def test_url_fallback_chain(self):
        """URL resolution: explicit arg > ANIME_PIPELINE_COMFYUI_URL > COMFYUI_URL > default."""
        from image_pipeline.anime_pipeline.comfy_client import ComfyClient

        # Explicit beats env
        with patch.dict(os.environ, {"ANIME_PIPELINE_COMFYUI_URL": "http://env:1234"}):
            client = ComfyClient(base_url="http://explicit:5678")
            assert client.base_url == "http://explicit:5678"

        # Default when no env set
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("ANIME_PIPELINE_COMFYUI_URL", None)
            os.environ.pop("COMFYUI_URL", None)
            client = ComfyClient()
            assert client.base_url == "http://localhost:8188"


# ═══════════════════════════════════════════════════════════════════════
# WorkflowBuilder version test
# ═══════════════════════════════════════════════════════════════════════

class TestWorkflowBuilderVersion:
    """Test workflow builder version field."""

    def test_builder_has_version(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        assert wb.version
        assert isinstance(wb.version, str)

    def test_builder_version_matches_serializer(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        from image_pipeline.anime_pipeline.workflow_serializer import get_workflow_version

        assert WorkflowBuilder().version == get_workflow_version()


# ═══════════════════════════════════════════════════════════════════════
# Vision Service (Phase 3) — full rewrite tests
# ═══════════════════════════════════════════════════════════════════════

class TestVisionPrompts:
    """Test prompt templates module."""

    def test_templates_registry_has_all_keys(self):
        from image_pipeline.anime_pipeline.vision_prompts import TEMPLATES

        expected = {"caption_short", "caption_rich", "tag_extraction",
                    "discrepancy", "full_analysis"}
        assert set(TEMPLATES.keys()) == expected

    def test_each_template_has_system_and_builder(self):
        from image_pipeline.anime_pipeline.vision_prompts import TEMPLATES

        for name, tmpl in TEMPLATES.items():
            assert "system" in tmpl, f"{name} missing 'system'"
            assert "user_builder" in tmpl, f"{name} missing 'user_builder'"
            assert callable(tmpl["user_builder"]), f"{name} user_builder not callable"
            assert isinstance(tmpl["system"], str), f"{name} system not str"

    def test_caption_short_user_builder(self):
        from image_pipeline.anime_pipeline.vision_prompts import caption_short_user

        msg = caption_short_user("anime girl", 2)
        assert "anime girl" in msg
        assert "2 image(s)" in msg

    def test_caption_rich_user_builder(self):
        from image_pipeline.anime_pipeline.vision_prompts import caption_rich_user

        msg = caption_rich_user("sakura scene", 0)
        assert "prompt only" in msg

    def test_tag_extraction_user_builder(self):
        from image_pipeline.anime_pipeline.vision_prompts import tag_extraction_user

        msg = tag_extraction_user("test", 3)
        assert "3 image(s)" in msg

    def test_discrepancy_user_builder(self):
        from image_pipeline.anime_pipeline.vision_prompts import discrepancy_user

        msg = discrepancy_user("gen girl", "A girl in park", ["girl"], ["pink"], "standing")
        assert "TARGET PLAN" in msg
        assert "girl" in msg
        assert "pink" in msg

    def test_full_analysis_user_builder_with_stage(self):
        from image_pipeline.anime_pipeline.vision_prompts import full_analysis_user

        msg = full_analysis_user("anime girl", 1, stage="composition")
        assert "[composition output]" in msg

    def test_full_analysis_user_builder_no_stage(self):
        from image_pipeline.anime_pipeline.vision_prompts import full_analysis_user

        msg = full_analysis_user("anime girl", 0)
        assert "[" not in msg.split("User")[0]  # no stage prefix


class TestDiscrepancyReport:
    """Test DiscrepancyReport dataclass."""

    def test_defaults(self):
        from image_pipeline.anime_pipeline.vision_service import DiscrepancyReport

        report = DiscrepancyReport()
        assert report.match_score == 0.0
        assert report.subject_match is True
        assert report.severity == "none"
        assert report.missing_elements == []

    def test_to_dict(self):
        from image_pipeline.anime_pipeline.vision_service import DiscrepancyReport

        report = DiscrepancyReport(
            match_score=0.75,
            subject_match=False,
            missing_elements=["cat"],
            severity="minor",
        )
        d = report.to_dict()
        assert d["match_score"] == 0.75
        assert d["missing_elements"] == ["cat"]
        assert d["severity"] == "minor"

    def test_all_fields_in_to_dict(self):
        from image_pipeline.anime_pipeline.vision_service import DiscrepancyReport

        report = DiscrepancyReport()
        d = report.to_dict()
        expected_keys = {
            "match_score", "subject_match", "pose_match", "color_match",
            "background_match", "missing_elements", "extra_elements",
            "identity_drift", "style_drift", "prompt_corrections",
            "control_corrections", "severity", "model_used", "latency_ms",
        }
        assert set(d.keys()) == expected_keys


class TestVisionServiceCore:
    """Test VisionService with mocked LLM backends."""

    def _make_service(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig
        from image_pipeline.anime_pipeline.vision_service import VisionService

        cfg = AnimePipelineConfig()
        return VisionService(cfg)

    def _mock_gemini_response(self, data: dict) -> httpx.Response:
        """Build a mock Gemini API response."""
        body = {
            "candidates": [{
                "content": {
                    "parts": [{"text": json.dumps(data)}],
                },
            }],
        }
        return httpx.Response(
            200, json=body,
            request=httpx.Request("POST", "https://test.example.com"),
        )

    def _mock_openai_response(self, data: dict) -> httpx.Response:
        """Build a mock OpenAI API response."""
        body = {
            "choices": [{
                "message": {"content": json.dumps(data)},
            }],
        }
        return httpx.Response(
            200, json=body,
            request=httpx.Request("POST", "https://test.example.com"),
        )

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_analyze_reference_images_gemini(self):
        svc = self._make_service()
        mock_data = {
            "caption_short": "An anime girl in a garden",
            "caption_detailed": "A young anime girl standing in a cherry blossom garden",
            "subjects": ["anime girl"],
            "pose": "standing",
            "camera_angle": "front",
            "framing": "medium_shot",
            "background_elements": ["cherry blossoms"],
            "dominant_colors": ["pink", "white"],
            "anime_tags": ["1girl", "cherry_blossoms"],
            "quality_risks": [],
            "missing_details": [],
            "identity_anchors": ["blue eyes", "long hair"],
            "suggested_negative": "bad anatomy",
        }
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = self._mock_gemini_response(mock_data)

            result = svc.analyze_reference_images(
                images_b64=["base64imgdata"],
                user_prompt="anime girl in cherry blossoms",
            )

        assert result.caption_short == "An anime girl in a garden"
        assert result.model_used == "gemini-2.0-flash"
        assert result.subjects == ["anime girl"]
        assert result.confidence == 0.85
        assert result.latency_ms >= 0

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_analyze_reference_images_cache_hit(self):
        svc = self._make_service()
        mock_data = {
            "caption_short": "cached result",
            "subjects": ["test"],
        }
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = self._mock_gemini_response(mock_data)

            # First call populates cache
            r1 = svc.analyze_reference_images(["img1"], "prompt A")
            # Second call with same args should hit cache
            r2 = svc.analyze_reference_images(["img1"], "prompt A")

        assert r1.caption_short == r2.caption_short
        # httpx.Client.post called only once (cache hit on second)
        assert mock_client.return_value.post.call_count == 1

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_analyze_intermediate_output(self):
        svc = self._make_service()
        mock_data = {"caption_short": "composition output", "subjects": ["girl"]}
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = self._mock_gemini_response(mock_data)

            result = svc.analyze_intermediate_output(
                image_b64="base64data",
                user_prompt="test prompt",
                stage="composition",
            )

        assert result.caption_short == "composition output"
        assert result.model_used == "gemini-2.0-flash"

    def test_prompt_only_fallback(self):
        svc = self._make_service()
        # No env keys set → all models fail → prompt-only fallback
        result = svc.analyze_reference_images([], "anime girl standing")

        assert result.model_used == "prompt_only"
        assert result.confidence == 0.3
        assert "anime girl" in result.caption_short

    def test_backward_compat_analyze(self):
        svc = self._make_service()
        result = svc.analyze("test prompt")
        assert isinstance(result.caption_short, str)
        assert result.model_used == "prompt_only"

    def test_backward_compat_analyze_intermediate(self):
        svc = self._make_service()
        result = svc.analyze_intermediate("test prompt", "base64data", "beauty")
        assert isinstance(result, object)
        assert hasattr(result, "caption_short")

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_parse_handles_markdown_fences(self):
        svc = self._make_service()
        fenced = '```json\n{"caption_short": "fenced", "subjects": []}\n```'
        body = {
            "candidates": [{"content": {"parts": [{"text": fenced}]}}],
        }
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = httpx.Response(
                200, json=body,
                request=httpx.Request("POST", "https://test.example.com"),
            )

            result = svc.analyze_reference_images(["img"], "test")

        assert result.caption_short == "fenced"

    @patch.dict(os.environ, {
        "GEMINI_API_KEY": "",
        "OPENAI_API_KEY": "test-openai",
    })
    def test_openai_fallback(self):
        svc = self._make_service()
        mock_data = {"caption_short": "openai result", "subjects": ["girl"]}
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = self._mock_openai_response(mock_data)

            result = svc.analyze_reference_images(["img"], "prompt")

        assert result.caption_short == "openai result"
        assert result.model_used == "gpt-4o-mini"

    def test_cache_clear(self):
        svc = self._make_service()
        svc._cache["test_key"] = MagicMock()
        assert len(svc._cache) == 1
        svc.cache_clear()
        assert len(svc._cache) == 0

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_parse_old_field_names(self):
        """LLMs sometimes return old schema field names."""
        svc = self._make_service()
        mock_data = {
            "caption_short": "test",
            "subject_description": "a girl",
            "pose_description": "sitting",
            "background_description": "a park",
            "color_palette": ["green"],
        }
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = self._mock_gemini_response(mock_data)

            result = svc.analyze_reference_images(["img"], "test")

        assert result.subjects == ["a girl"]
        assert result.pose == "sitting"
        assert result.background_elements == ["a park"]
        assert result.dominant_colors == ["green"]


class TestVisionServiceFlorence2:
    """Test Florence-2 local model integration."""

    def _make_service(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig
        from image_pipeline.anime_pipeline.vision_service import VisionService

        return VisionService(AnimePipelineConfig())

    @patch.dict(os.environ, {"FLORENCE2_ENDPOINT": "http://localhost:5050/caption"})
    def test_florence2_used_when_available(self):
        svc = self._make_service()
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = httpx.Response(
                200, json={"result": "an anime girl with blue hair standing"},
                request=httpx.Request("POST", "https://test.example.com"),
            )

            result = svc.analyze_reference_images(["img_b64"], "test")

        assert result.model_used == "florence-2"
        assert "blue hair" in result.caption_short

    def test_florence2_skipped_without_env(self):
        svc = self._make_service()
        # No FLORENCE2_ENDPOINT → skip → fall through to prompt_only
        result = svc.analyze_reference_images([], "test prompt")
        assert result.model_used == "prompt_only"


class TestVisionServiceJoyCaption:
    """Test JoyCaption local model integration."""

    def _make_service(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig
        from image_pipeline.anime_pipeline.vision_service import VisionService

        return VisionService(AnimePipelineConfig())

    @patch.dict(os.environ, {"JOYCAPTION_ENDPOINT": "http://localhost:5051/caption"})
    def test_joycaption_used_when_available(self):
        svc = self._make_service()
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = httpx.Response(
                200, json={
                    "caption": "soft pastel anime illustration of a girl",
                    "tags": ["1girl", "pastel"],
                },
                request=httpx.Request("POST", "https://test.example.com"),
            )

            result = svc.analyze_reference_images(["img_b64"], "test")

        assert result.model_used == "joycaption"
        assert result.anime_tags == ["1girl", "pastel"]


class TestVisionServiceCompare:
    """Test compare_target_vs_output and heuristic comparison."""

    def _make_service(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig
        from image_pipeline.anime_pipeline.vision_service import VisionService

        return VisionService(AnimePipelineConfig())

    def test_heuristic_compare_perfect_match(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis, LayerPlan

        svc = self._make_service()
        plan = LayerPlan(
            scene_summary="girl in garden",
            subject_list=["anime girl"],
            palette=["pink"],
            pose="standing",
            background_plan="garden",
        )
        analysis = VisionAnalysis(
            subjects=["anime girl"],
            dominant_colors=["pink"],
            pose="standing",
            background_elements=["garden with flowers"],
        )
        report = svc.compare_target_vs_output(plan, analysis)

        assert report.match_score >= 0.75
        assert report.subject_match is True
        assert report.severity in ("none", "minor")

    def test_heuristic_compare_mismatch(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis, LayerPlan

        svc = self._make_service()
        plan = LayerPlan(
            scene_summary="girl with cat",
            subject_list=["anime girl", "cat"],
            palette=["blue", "orange"],
            pose="sitting",
            background_plan="living room",
        )
        analysis = VisionAnalysis(
            subjects=["robot"],
            dominant_colors=["gray"],
            pose="running",
            background_elements=["street"],
        )
        report = svc.compare_target_vs_output(plan, analysis)

        assert report.match_score < 0.75
        assert report.subject_match is False
        assert len(report.missing_elements) > 0
        assert report.severity in ("major", "critical")

    def test_heuristic_compare_empty_plan(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis, LayerPlan

        svc = self._make_service()
        plan = LayerPlan()
        analysis = VisionAnalysis(subjects=["girl"])
        report = svc.compare_target_vs_output(plan, analysis)

        # Empty plan = everything matches by default
        assert report.subject_match is True
        assert report.match_score >= 0.75

    @patch.dict(os.environ, {"GEMINI_API_KEY": "test-key"})
    def test_llm_compare_with_image(self):
        from image_pipeline.anime_pipeline.schemas import LayerPlan, VisionAnalysis

        svc = self._make_service()
        plan = LayerPlan(
            scene_summary="test scene",
            subject_list=["girl"],
            palette=["red"],
            pose="standing",
        )
        mock_data = {
            "match_score": 0.8,
            "subject_match": True,
            "pose_match": True,
            "color_match": False,
            "background_match": True,
            "missing_elements": [],
            "extra_elements": [],
            "identity_drift": [],
            "style_drift": [],
            "prompt_corrections": ["add more red"],
            "control_corrections": {},
            "severity": "minor",
        }
        body = {
            "candidates": [{"content": {"parts": [{"text": json.dumps(mock_data)}]}}],
        }
        with patch("httpx.Client") as mock_client:
            mock_client.return_value.__enter__ = lambda s: s
            mock_client.return_value.__exit__ = MagicMock(return_value=False)
            mock_client.return_value.post.return_value = httpx.Response(
                200, json=body,
                request=httpx.Request("POST", "https://test.example.com"),
            )

            report = svc.compare_target_vs_output(
                plan, VisionAnalysis(), output_image_b64="img_b64",
            )

        assert report.match_score == 0.8
        assert report.severity == "minor"
        assert "add more red" in report.prompt_corrections


class TestBuildPromptPatch:
    """Test build_prompt_patch_from_analysis."""

    def _make_service(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig
        from image_pipeline.anime_pipeline.vision_service import VisionService

        return VisionService(AnimePipelineConfig())

    def test_missing_details_become_emphasis(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis, LayerPlan

        svc = self._make_service()
        analysis = VisionAnalysis(
            missing_details=["blue eyes", "ribbon"],
            subjects=["girl"],
            dominant_colors=["red"],
        )
        plan = LayerPlan(subject_list=["girl"], palette=["red"])
        patches = svc.build_prompt_patch_from_analysis(analysis, plan)

        assert any("blue eyes" in p for p in patches)
        assert any("ribbon" in p for p in patches)
        assert any(":1.3" in p for p in patches)

    def test_missing_subjects_get_emphasis(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis, LayerPlan

        svc = self._make_service()
        analysis = VisionAnalysis(subjects=["girl"])
        plan = LayerPlan(subject_list=["girl", "cat"])
        patches = svc.build_prompt_patch_from_analysis(analysis, plan)

        assert any("cat" in p.lower() for p in patches)

    def test_missing_colors_get_scheme(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis, LayerPlan

        svc = self._make_service()
        analysis = VisionAnalysis(dominant_colors=["red"])
        plan = LayerPlan(palette=["red", "blue"])
        patches = svc.build_prompt_patch_from_analysis(analysis, plan)

        assert any("blue" in p.lower() for p in patches)

    def test_quality_risks_added_to_negative(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis, LayerPlan

        svc = self._make_service()
        analysis = VisionAnalysis(quality_risks=["bad hands", "blurry"])
        plan = LayerPlan()
        patches = svc.build_prompt_patch_from_analysis(analysis, plan)

        assert any("NEGATIVE_ADD" in p for p in patches)
        assert any("bad hands" in p for p in patches)

    def test_no_patches_when_everything_matches(self):
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis, LayerPlan

        svc = self._make_service()
        analysis = VisionAnalysis(
            subjects=["girl"],
            dominant_colors=["pink"],
        )
        plan = LayerPlan(subject_list=["girl"], palette=["pink"])
        patches = svc.build_prompt_patch_from_analysis(analysis, plan)

        assert patches == []


class TestVisionServiceExports:
    """Test that __init__.py exports are correct."""

    def test_discrepancy_report_importable(self):
        from image_pipeline.anime_pipeline import DiscrepancyReport

        report = DiscrepancyReport()
        assert report.severity == "none"

    def test_vision_prompts_importable(self):
        from image_pipeline.anime_pipeline import vision_prompts

        assert hasattr(vision_prompts, "TEMPLATES")
        assert hasattr(vision_prompts, "FULL_ANALYSIS_SYSTEM")

    def test_vision_service_importable(self):
        from image_pipeline.anime_pipeline import VisionService

        assert callable(VisionService)


# ═══════════════════════════════════════════════════════════════════════
# Phase 3B — Planner presets + rewritten layer planner
# ═══════════════════════════════════════════════════════════════════════


class TestPlannerPresets:
    """Test planner_presets module: dataclasses, registry, lookup."""

    def test_preset_registry_has_four(self):
        from image_pipeline.anime_pipeline.planner_presets import PRESETS
        assert len(PRESETS) == 4

    def test_list_presets(self):
        from image_pipeline.anime_pipeline.planner_presets import list_presets
        names = list_presets()
        assert "anime_quality" in names
        assert "anime_speed" in names
        assert "anime_reference_strict" in names
        assert "anime_background_heavy" in names

    def test_get_preset_known(self):
        from image_pipeline.anime_pipeline.planner_presets import get_preset
        p = get_preset("anime_speed")
        assert p.name == "anime_speed"
        assert p.skip_cleanup is True
        assert p.skip_upscale is True

    def test_get_preset_unknown_falls_back(self):
        from image_pipeline.anime_pipeline.planner_presets import get_preset
        p = get_preset("nonexistent_preset")
        assert p.name == "anime_quality"

    def test_pass_override_defaults(self):
        from image_pipeline.anime_pipeline.planner_presets import PassOverride
        o = PassOverride()
        assert o.steps is None
        assert o.cfg is None
        assert o.denoise is None
        assert o.controlnet_strength_scale == 1.0

    def test_anime_quality_preset_values(self):
        from image_pipeline.anime_pipeline.planner_presets import ANIME_QUALITY
        assert ANIME_QUALITY.pass_overrides["composition"].steps == 30
        assert ANIME_QUALITY.pass_overrides["beauty"].steps == 28
        assert ANIME_QUALITY.skip_upscale is False

    def test_anime_reference_strict_identity(self):
        from image_pipeline.anime_pipeline.planner_presets import ANIME_REFERENCE_STRICT
        assert ANIME_REFERENCE_STRICT.identity_emphasis == 1.5
        assert ANIME_REFERENCE_STRICT.reference_weight == 1.5
        beauty = ANIME_REFERENCE_STRICT.pass_overrides["beauty"]
        assert beauty.controlnet_strength_scale > 1.0

    def test_anime_background_heavy_negatives(self):
        from image_pipeline.anime_pipeline.planner_presets import ANIME_BACKGROUND_HEAVY
        assert "simple background" in ANIME_BACKGROUND_HEAVY.negative_extra


class TestMakeLayerPlan:
    """Test the standalone make_layer_plan function."""

    def test_basic_call_returns_layer_plan(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan
        from image_pipeline.anime_pipeline.schemas import LayerPlan

        plan = make_layer_plan("anime girl in cherry blossoms")
        assert isinstance(plan, LayerPlan)
        assert len(plan.passes) >= 4

    def test_default_preset_is_anime_quality(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl walking")
        comp = plan.get_pass("composition")
        assert comp is not None
        # anime_quality preset: 30 steps for composition
        assert comp.steps == 30

    def test_speed_preset_skips_cleanup_and_upscale(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl", preset="anime_speed")
        names = [p.pass_name for p in plan.passes]
        assert "cleanup" not in names
        assert "upscale" not in names

    def test_speed_preset_uses_euler_a(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl", preset="anime_speed")
        comp = plan.get_pass("composition")
        assert comp.sampler == "euler_a"

    def test_background_heavy_adds_env_prompts(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan(
            "forest scenery", preset="anime_background_heavy",
        )
        comp = plan.get_pass("composition")
        assert "detailed environment" in comp.positive_prompt.lower() or \
               "scenic composition" in comp.positive_prompt.lower()

    def test_background_heavy_negative_extra(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan(
            "forest scenery", preset="anime_background_heavy",
        )
        beauty = plan.get_pass("beauty")
        assert "simple background" in beauty.negative_prompt

    def test_reference_strict_identity_emphasis(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan
        from image_pipeline.anime_pipeline.schemas import VisionAnalysis

        va = VisionAnalysis(
            caption_short="blonde anime girl",
            identity_anchors=["blonde hair", "blue eyes", "school uniform"],
            confidence=0.9,
        )
        plan = make_layer_plan(
            "anime girl standing",
            references=va,
            preset="anime_reference_strict",
        )
        comp = plan.get_pass("composition")
        # identity anchors should appear with emphasis in prompt
        assert "blonde hair" in comp.positive_prompt

    def test_reference_strict_lower_denoise(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan(
            "anime girl", preset="anime_reference_strict",
        )
        beauty = plan.get_pass("beauty")
        # reference_strict beauty denoise is 0.35 (lower than quality's 0.45)
        assert beauty.denoise <= 0.40

    def test_quality_hint_fast_skips_upscale(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan(
            "anime girl", quality_hint="fast",
        )
        names = [p.pass_name for p in plan.passes]
        assert "upscale" not in names

    def test_pass_ordering_always_correct(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl in park")
        names = [p.pass_name for p in plan.passes]
        assert names[0] == "composition"
        assert names[1] == "structure_lock"
        # beauty is always last render pass (before upscale if present)
        beauty_idx = names.index("beauty")
        for n in names[beauty_idx + 1:]:
            assert n == "upscale"

    def test_all_passes_have_expected_output(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl")
        for p in plan.passes:
            assert p.expected_output, f"Pass {p.pass_name} missing expected_output"

    def test_importable_from_package(self):
        from image_pipeline.anime_pipeline import make_layer_plan
        assert callable(make_layer_plan)


class TestLayerPlannerVRAM:
    """Test VRAM profile handling — resolution and step capping."""

    def test_8gb_resolution_capped(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl standing", vram_profile="8gb")
        comp = plan.get_pass("composition")
        assert comp.width <= 1024
        assert comp.height <= 1024

    def test_12gb_default_profile(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl standing", vram_profile="12gb")
        comp = plan.get_pass("composition")
        assert comp.width <= 1216
        assert comp.height <= 1216

    def test_resolution_rounded_to_8(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl standing", vram_profile="8gb")
        comp = plan.get_pass("composition")
        assert comp.width % 8 == 0
        assert comp.height % 8 == 0

    def test_step_cap_respected(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan(
            "anime girl",
            preset="anime_background_heavy",
            vram_profile="8gb",
        )
        for p in plan.passes:
            if p.steps > 0:
                assert p.steps <= 25, (
                    f"Pass {p.pass_name} has {p.steps} steps, "
                    f"exceeds 8gb step_cap of 25"
                )

    def test_speed_preset_step_cap_combined(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan(
            "anime girl", preset="anime_speed", vram_profile="8gb",
        )
        comp = plan.get_pass("composition")
        # speed preset vram_step_cap=20 and 8gb step_cap=25
        # min(18, min(20, 25)) = 18
        assert comp.steps <= 20


class TestLayerPlannerCritique:
    """Test critique-aware replanning."""

    def test_critique_patches_positive_prompt(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan
        from image_pipeline.anime_pipeline.schemas import CritiqueReport

        critique = CritiqueReport(
            prompt_patch=["fix broken hands", "sharper eyes"],
            anatomy_issues=["extra finger"],
            anatomy_score=3,
        )
        plan = make_layer_plan("anime girl", critique=critique)
        comp = plan.get_pass("composition")
        assert "fix broken hands" in comp.positive_prompt
        assert "sharper eyes" in comp.positive_prompt

    def test_critique_adds_issues_to_negative(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan
        from image_pipeline.anime_pipeline.schemas import CritiqueReport

        critique = CritiqueReport(
            anatomy_issues=["extra finger"],
            face_issues=["asymmetric eyes"],
        )
        plan = make_layer_plan("anime girl", critique=critique)
        comp = plan.get_pass("composition")
        assert "extra finger" in comp.negative_prompt

    def test_critique_via_execute(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import LayerPlannerAgent
        from image_pipeline.anime_pipeline.schemas import (
            AnimePipelineJob, CritiqueReport,
        )
        from image_pipeline.anime_pipeline.config import load_config

        critique = CritiqueReport(
            prompt_patch=["more detail on clothing"],
            retry_recommendation=True,
        )
        job = AnimePipelineJob(
            user_prompt="anime girl",
            critique_results=[critique],
        )
        planner = LayerPlannerAgent(load_config())
        planner.execute(job)

        comp = job.layer_plan.get_pass("composition")
        assert "more detail on clothing" in comp.positive_prompt


class TestLayerPlannerOrientation:
    """Test orientation detection from prompts and hints."""

    def test_square_detection(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime avatar icon")
        comp = plan.get_pass("composition")
        # square resolution should have w == h
        assert comp.width == comp.height

    def test_landscape_detection(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime panorama wide scenery mountains")
        comp = plan.get_pass("composition")
        assert comp.width > comp.height

    def test_orientation_hint_overrides(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        # prompt says landscape but hint overrides to portrait
        plan = make_layer_plan(
            "landscape scenery", orientation_hint="portrait",
        )
        comp = plan.get_pass("composition")
        assert comp.height >= comp.width


class TestLayerPlannerSourceImage:
    """Test img2img mode when source image is provided."""

    def test_source_image_lowers_composition_denoise(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan(
            "anime girl",
            source_image_b64="base64_data_here",
        )
        comp = plan.get_pass("composition")
        assert comp.denoise < 1.0  # should be img2img denoise

    def test_no_source_composition_full_denoise(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl")
        comp = plan.get_pass("composition")
        assert comp.denoise == 1.0  # txt2img


class TestPlannerExports:
    """Test __init__.py exports for planner modules."""

    def test_planner_presets_importable(self):
        from image_pipeline.anime_pipeline import planner_presets
        assert hasattr(planner_presets, "PRESETS")

    def test_preset_classes_importable(self):
        from image_pipeline.anime_pipeline import (
            PlannerPreset, PassOverride, get_preset, list_presets,
        )
        assert callable(get_preset)
        assert callable(list_presets)
        assert PlannerPreset is not None
        assert PassOverride is not None

    def test_make_layer_plan_importable(self):
        from image_pipeline.anime_pipeline import make_layer_plan
        assert callable(make_layer_plan)


class TestLayerPlannerValidation:
    """Ensure generated plans pass schema validation."""

    def test_quality_plan_validates(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl with sword", preset="anime_quality")
        errors = plan.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_speed_plan_validates(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan("anime girl", preset="anime_speed")
        errors = plan.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_reference_strict_plan_validates(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan(
            "anime girl", preset="anime_reference_strict",
        )
        errors = plan.validate()
        assert errors == [], f"Validation errors: {errors}"

    def test_background_heavy_plan_validates(self):
        from image_pipeline.anime_pipeline.agents.layer_planner import make_layer_plan

        plan = make_layer_plan(
            "forest scenery", preset="anime_background_heavy",
        )
        errors = plan.validate()
        assert errors == [], f"Validation errors: {errors}"


# ═══════════════════════════════════════════════════════════════════════
# Composition pass workflow builder tests
# ═══════════════════════════════════════════════════════════════════════


def _make_composition_pc(**overrides) -> "PassConfig":
    """Helper to create a PassConfig for composition tests."""
    from image_pipeline.anime_pipeline.schemas import PassConfig

    defaults = dict(
        pass_name="composition",
        model_slot="base",
        checkpoint="animagine-xl-4.0-opt.safetensors",
        width=832,
        height=1216,
        sampler="dpmpp_2m_sde",
        scheduler="karras",
        steps=30,
        cfg=5.0,
        denoise=1.0,
        positive_prompt="masterpiece, best quality, 1girl standing in park, full body, anime",
        negative_prompt="low quality, bad anatomy, blurry",
        prompt_strategy="broad",
        expected_output="Structurally sound draft with correct pose and composition",
    )
    defaults.update(overrides)
    return PassConfig(**defaults)


class TestCompositionWorkflowTxt2Img:
    """Test WorkflowBuilder.build_composition() txt2img path."""

    def test_has_required_node_types(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc()
        wf = wb.build_composition(pc, seed=42)

        types = {n["class_type"] for n in wf.values()}
        assert "CheckpointLoaderSimple" in types
        assert "CLIPTextEncode" in types
        assert "EmptyLatentImage" in types
        assert "KSampler" in types
        assert "VAEDecode" in types
        assert "SaveImage" in types

    def test_ksampler_settings_match_passconfig(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(steps=28, cfg=5.5, sampler="euler_a", scheduler="normal")
        wf = wb.build_composition(pc, seed=123)

        ks = [n for n in wf.values() if n["class_type"] == "KSampler"][0]
        assert ks["inputs"]["seed"] == 123
        assert ks["inputs"]["steps"] == 28
        assert ks["inputs"]["cfg"] == 5.5
        assert ks["inputs"]["sampler_name"] == "euler_a"
        assert ks["inputs"]["scheduler"] == "normal"
        assert ks["inputs"]["denoise"] == 1.0

    def test_latent_image_resolution(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(width=1216, height=832)
        wf = wb.build_composition(pc, seed=42)

        latent = [n for n in wf.values() if n["class_type"] == "EmptyLatentImage"][0]
        assert latent["inputs"]["width"] == 1216
        assert latent["inputs"]["height"] == 832

    def test_prompts_encoded_correctly(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(
            positive_prompt="masterpiece, anime girl",
            negative_prompt="bad quality",
        )
        wf = wb.build_composition(pc, seed=42)

        clip_nodes = [n for n in wf.values() if n["class_type"] == "CLIPTextEncode"]
        texts = [n["inputs"]["text"] for n in clip_nodes]
        assert "masterpiece, anime girl" in texts
        assert "bad quality" in texts

    def test_checkpoint_loaded(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(checkpoint="my_model.safetensors")
        wf = wb.build_composition(pc, seed=42)

        ckpt = [n for n in wf.values() if n["class_type"] == "CheckpointLoaderSimple"][0]
        assert ckpt["inputs"]["ckpt_name"] == "my_model.safetensors"

    def test_save_image_filename_prefix(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc()
        wf = wb.build_composition(pc, seed=999)

        save = [n for n in wf.values() if n["class_type"] == "SaveImage"][0]
        prefix = save["inputs"]["filename_prefix"]
        assert "anime_pipeline/" in prefix
        assert "01_composition" in prefix
        assert "999" in prefix

    def test_no_clip_skip_default(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc()
        wf = wb.build_composition(pc, seed=42, clip_skip=1)

        types = [n["class_type"] for n in wf.values()]
        assert "CLIPSetLastLayer" not in types

    def test_clip_skip_2_inserts_node(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc()
        wf = wb.build_composition(pc, seed=42, clip_skip=2)

        types = [n["class_type"] for n in wf.values()]
        assert "CLIPSetLastLayer" in types

        clip_set = [n for n in wf.values() if n["class_type"] == "CLIPSetLastLayer"][0]
        assert clip_set["inputs"]["stop_at_clip_layer"] == -2

    def test_workflow_json_all_nodes_have_class_type(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc()
        wf = wb.build_composition(pc, seed=42)

        for nid, node in wf.items():
            assert "class_type" in node, f"Node {nid} missing class_type"
            assert "inputs" in node, f"Node {nid} missing inputs"

    def test_node_ids_are_string_integers(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc()
        wf = wb.build_composition(pc, seed=42)

        for nid in wf.keys():
            assert nid.isdigit(), f"Node ID '{nid}' is not a digit string"


class TestCompositionWorkflowImg2Img:
    """Test WorkflowBuilder.build_composition() img2img path."""

    def test_img2img_has_vae_encode(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(denoise=0.75)
        wf = wb.build_composition(pc, seed=42, source_image_b64="fake_b64")

        types = {n["class_type"] for n in wf.values()}
        assert "LoadImageFromBase64" in types
        assert "VAEEncode" in types

    def test_img2img_no_empty_latent(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(denoise=0.75)
        wf = wb.build_composition(pc, seed=42, source_image_b64="fake_b64")

        types = {n["class_type"] for n in wf.values()}
        assert "EmptyLatentImage" not in types

    def test_img2img_ksampler_denoise_below_1(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(denoise=0.75)
        wf = wb.build_composition(pc, seed=42, source_image_b64="fake_b64")

        ks = [n for n in wf.values() if n["class_type"] == "KSampler"][0]
        assert ks["inputs"]["denoise"] == 0.75

    def test_img2img_source_image_loaded(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(denoise=0.75)
        wf = wb.build_composition(pc, seed=42, source_image_b64="my_image_data")

        loader = [n for n in wf.values() if n["class_type"] == "LoadImageFromBase64"][0]
        assert loader["inputs"]["base64_image"] == "my_image_data"

    def test_img2img_filename_indicates_i2i(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(denoise=0.75)
        wf = wb.build_composition(pc, seed=42, source_image_b64="fake_b64")

        save = [n for n in wf.values() if n["class_type"] == "SaveImage"][0]
        assert "i2i" in save["inputs"]["filename_prefix"]

    def test_img2img_with_clip_skip(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        pc = _make_composition_pc(denoise=0.75)
        wf = wb.build_composition(pc, seed=42, source_image_b64="fake_b64", clip_skip=2)

        types = [n["class_type"] for n in wf.values()]
        assert "CLIPSetLastLayer" in types


class TestCompositionPromptRules:
    """Test composition prompt refinement rules."""

    def test_pose_tags_promoted(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import refine_composition_prompt

        prompt = "masterpiece, best quality, detailed eyes, 1girl standing, anime"
        result = refine_composition_prompt(prompt)
        parts = [p.strip() for p in result.split(",")]
        # "standing" is a priority tag — should appear before "anime"
        standing_idx = next(i for i, p in enumerate(parts) if "standing" in p.lower())
        anime_idx = next(i for i, p in enumerate(parts) if p.strip() == "anime")
        assert standing_idx < anime_idx

    def test_detail_tags_removed(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import refine_composition_prompt

        prompt = "masterpiece, 1girl, intricate details, detailed fingers, anime"
        result = refine_composition_prompt(prompt)
        assert "intricate details" not in result
        assert "detailed fingers" not in result

    def test_base_content_preserved(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import refine_composition_prompt

        prompt = "masterpiece, best quality, 1girl, anime, cherry blossoms"
        result = refine_composition_prompt(prompt)
        assert "masterpiece" in result
        assert "1girl" in result
        assert "cherry blossoms" in result

    def test_face_quality_preserved(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import refine_composition_prompt

        prompt = "masterpiece, beautiful face, 1girl, best quality"
        result = refine_composition_prompt(prompt)
        assert "beautiful face" in result

    def test_empty_prompt_returns_empty(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import refine_composition_prompt

        result = refine_composition_prompt("")
        assert result == ""

    def test_full_body_promoted(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import refine_composition_prompt

        prompt = "masterpiece, anime, 1girl, full body, detailed hair"
        result = refine_composition_prompt(prompt)
        parts = [p.strip() for p in result.split(",")]
        fb_idx = next(i for i, p in enumerate(parts) if "full body" in p.lower())
        assert fb_idx < len(parts) - 1  # should be near front, not at end


class TestCompositionPassAgent:
    """Test CompositionPassAgent workflow building (no actual ComfyUI)."""

    def test_build_workflow_returns_valid_json(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import CompositionPassAgent
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        agent = CompositionPassAgent(config)
        pc = _make_composition_pc()

        wf = agent.build_workflow(pc, seed=42)
        types = {n["class_type"] for n in wf.values()}
        assert "CheckpointLoaderSimple" in types
        assert "KSampler" in types

    def test_build_workflow_applies_prompt_rules(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import CompositionPassAgent
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        agent = CompositionPassAgent(config)
        pc = _make_composition_pc(
            positive_prompt="masterpiece, intricate details, 1girl standing, anime",
        )
        wf = agent.build_workflow(pc, seed=42)

        clip_nodes = [n for n in wf.values() if n["class_type"] == "CLIPTextEncode"]
        pos_texts = [n["inputs"]["text"] for n in clip_nodes]
        # intricate details should be removed
        for text in pos_texts:
            if "masterpiece" in text:
                assert "intricate details" not in text

    def test_build_workflow_with_clip_skip(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import CompositionPassAgent
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        agent = CompositionPassAgent(config)
        pc = _make_composition_pc()

        wf = agent.build_workflow(pc, seed=42, clip_skip=2)
        types = [n["class_type"] for n in wf.values()]
        assert "CLIPSetLastLayer" in types

    def test_build_workflow_img2img(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import CompositionPassAgent
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        agent = CompositionPassAgent(config)
        pc = _make_composition_pc(denoise=0.75)

        wf = agent.build_workflow(pc, seed=42, source_image_b64="fake_b64")
        types = {n["class_type"] for n in wf.values()}
        assert "LoadImageFromBase64" in types
        assert "VAEEncode" in types

    def test_execute_fails_without_plan(self):
        from image_pipeline.anime_pipeline.agents.composition_pass import CompositionPassAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob, AnimePipelineStatus
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        agent = CompositionPassAgent(config)
        job = AnimePipelineJob(user_prompt="test")

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "No layer plan" in result.error


# ═══════════════════════════════════════════════════════════════════════
# Structure Lock tests
# ═══════════════════════════════════════════════════════════════════════


def _make_lineart_layer_config(**overrides):
    """Helper to create a StructureLayerConfig for lineart tests."""
    from image_pipeline.anime_pipeline.config import StructureLayerConfig

    defaults = dict(
        layer_type="lineart_anime",
        preprocessor="AnimeLineArtPreprocessor",
        controlnet_model="control_v11p_sd15_lineart_anime",
        strength=0.85,
        start_percent=0.0,
        end_percent=0.8,
        priority=1,
        optional=False,
        enabled=True,
    )
    defaults.update(overrides)
    return StructureLayerConfig(**defaults)


def _make_depth_layer_config(**overrides):
    """Helper to create a StructureLayerConfig for depth tests."""
    from image_pipeline.anime_pipeline.config import StructureLayerConfig

    defaults = dict(
        layer_type="depth",
        preprocessor="DepthAnythingV2Preprocessor",
        controlnet_model="control_v11f1p_sd15_depth",
        strength=0.55,
        start_percent=0.0,
        end_percent=0.6,
        priority=2,
        optional=False,
        enabled=True,
    )
    defaults.update(overrides)
    return StructureLayerConfig(**defaults)


def _make_canny_layer_config(**overrides):
    """Helper to create a StructureLayerConfig for canny tests."""
    from image_pipeline.anime_pipeline.config import StructureLayerConfig

    defaults = dict(
        layer_type="canny",
        preprocessor="CannyEdgePreprocessor",
        controlnet_model="control_v11p_sd15_canny",
        strength=0.35,
        start_percent=0.0,
        end_percent=0.4,
        priority=3,
        optional=True,
        enabled=False,
    )
    defaults.update(overrides)
    return StructureLayerConfig(**defaults)


class TestStructureLockWorkflowLineart:
    """Test WorkflowBuilder.build_structure_lock_layer() for lineart."""

    def test_has_required_nodes(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_lineart_layer_config()
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        types = {n["class_type"] for n in wf.values()}
        assert "LoadImageFromBase64" in types
        assert "AnimeLineArtPreprocessor" in types
        assert "SaveImage" in types

    def test_preprocessor_receives_image(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_lineart_layer_config()
        wf = wb.build_structure_lock_layer("my_image_data", lc)

        loader = [n for n in wf.values() if n["class_type"] == "LoadImageFromBase64"][0]
        assert loader["inputs"]["base64_image"] == "my_image_data"

    def test_resolution_param_set(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_lineart_layer_config()
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        proc = [n for n in wf.values() if n["class_type"] == "AnimeLineArtPreprocessor"][0]
        assert proc["inputs"]["resolution"] == 1024

    def test_save_filename_has_layer_type(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_lineart_layer_config()
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        save = [n for n in wf.values() if n["class_type"] == "SaveImage"][0]
        assert "02_lineart_anime" in save["inputs"]["filename_prefix"]

    def test_node_ids_are_digit_strings(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_lineart_layer_config()
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        for nid in wf.keys():
            assert nid.isdigit(), f"Node ID '{nid}' is not a digit string"

    def test_all_nodes_have_class_type_and_inputs(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_lineart_layer_config()
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        for nid, node in wf.items():
            assert "class_type" in node, f"Node {nid} missing class_type"
            assert "inputs" in node, f"Node {nid} missing inputs"

    def test_standard_lineart_preprocessor(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_lineart_layer_config(preprocessor="LineArtPreprocessor")
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        types = {n["class_type"] for n in wf.values()}
        assert "LineArtPreprocessor" in types

        proc = [n for n in wf.values() if n["class_type"] == "LineArtPreprocessor"][0]
        assert proc["inputs"]["resolution"] == 1024


class TestStructureLockWorkflowDepth:
    """Test WorkflowBuilder.build_structure_lock_layer() for depth."""

    def test_depth_preprocessor_node(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_depth_layer_config()
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        types = {n["class_type"] for n in wf.values()}
        assert "DepthAnythingV2Preprocessor" in types

    def test_depth_resolution_set(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_depth_layer_config()
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        proc = [n for n in wf.values() if n["class_type"] == "DepthAnythingV2Preprocessor"][0]
        assert proc["inputs"]["resolution"] == 1024

    def test_depth_filename_prefix(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_depth_layer_config()
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        save = [n for n in wf.values() if n["class_type"] == "SaveImage"][0]
        assert "02_depth" in save["inputs"]["filename_prefix"]


class TestStructureLockWorkflowCanny:
    """Test WorkflowBuilder.build_structure_lock_layer() for canny."""

    def test_canny_preprocessor_node(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_canny_layer_config(enabled=True)
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        types = {n["class_type"] for n in wf.values()}
        assert "CannyEdgePreprocessor" in types

    def test_canny_thresholds_set(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_canny_layer_config(enabled=True)
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        proc = [n for n in wf.values() if n["class_type"] == "CannyEdgePreprocessor"][0]
        assert proc["inputs"]["low_threshold"] == 100
        assert proc["inputs"]["high_threshold"] == 200
        assert proc["inputs"]["resolution"] == 1024

    def test_canny_filename_prefix(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder

        wb = WorkflowBuilder()
        lc = _make_canny_layer_config(enabled=True)
        wf = wb.build_structure_lock_layer("fake_b64", lc)

        save = [n for n in wf.values() if n["class_type"] == "SaveImage"][0]
        assert "02_canny" in save["inputs"]["filename_prefix"]


class TestStructureLockQualityCheck:
    """Test validate_hint_image quality gate."""

    def test_empty_string_fails(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import validate_hint_image

        assert validate_hint_image("", "lineart_anime") is False

    def test_none_coerced_fails(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import validate_hint_image

        # validate_hint_image expects str, but called with "" when None
        assert validate_hint_image("", "depth") is False

    def test_too_small_fails(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import validate_hint_image

        # 50 chars is well below the 200-char threshold
        assert validate_hint_image("x" * 50, "canny") is False

    def test_threshold_boundary(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import validate_hint_image

        assert validate_hint_image("x" * 199, "lineart") is False
        assert validate_hint_image("x" * 200, "lineart") is True

    def test_valid_image_passes(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import validate_hint_image

        # A real base64 image would be much longer
        assert validate_hint_image("x" * 5000, "depth") is True


class TestStructureLockConfigEnabled:
    """Test enabled/disabled control per layer."""

    def test_default_config_has_enabled_field(self):
        from image_pipeline.anime_pipeline.config import StructureLayerConfig

        lc = StructureLayerConfig()
        assert lc.enabled is True

    def test_disabled_layer_excluded_from_resolve(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = [
            _make_lineart_layer_config(enabled=True),
            _make_depth_layer_config(enabled=False),
            _make_canny_layer_config(enabled=False),
        ]
        agent = StructureLockAgent(config)
        layers = agent.get_enabled_layers()

        types = [lc.layer_type for lc in layers]
        assert "lineart_anime" in types
        assert "depth" not in types
        assert "canny" not in types

    def test_all_disabled_returns_empty(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = [
            _make_lineart_layer_config(enabled=False),
            _make_depth_layer_config(enabled=False),
        ]
        agent = StructureLockAgent(config)
        layers = agent.get_enabled_layers()

        assert layers == []

    def test_layers_sorted_by_priority(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = [
            _make_depth_layer_config(priority=2),     # second
            _make_lineart_layer_config(priority=1),   # first
            _make_canny_layer_config(enabled=True, priority=3),  # third
        ]
        config.max_simultaneous_layers = 5
        agent = StructureLockAgent(config)
        layers = agent.get_enabled_layers()

        types = [lc.layer_type for lc in layers]
        assert types == ["lineart_anime", "depth", "canny"]

    def test_max_simultaneous_layers_respected(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = [
            _make_lineart_layer_config(priority=1),
            _make_depth_layer_config(priority=2),
            _make_canny_layer_config(enabled=True, priority=3),
        ]
        config.max_simultaneous_layers = 2
        agent = StructureLockAgent(config)
        layers = agent.get_enabled_layers()

        assert len(layers) == 2
        types = [lc.layer_type for lc in layers]
        assert "lineart_anime" in types
        assert "depth" in types
        assert "canny" not in types


class TestStructureLockAgent:
    """Test StructureLockAgent workflow building (no actual ComfyUI)."""

    def test_build_workflow_returns_all_enabled_layers(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = [
            _make_lineart_layer_config(),
            _make_depth_layer_config(),
        ]
        config.max_simultaneous_layers = 5
        agent = StructureLockAgent(config)

        workflows = agent.build_structure_lock_workflow("fake_b64")
        assert "lineart_anime" in workflows
        assert "depth" in workflows
        assert len(workflows) == 2

    def test_build_workflow_skips_disabled(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = [
            _make_lineart_layer_config(),
            _make_depth_layer_config(enabled=False),
        ]
        config.max_simultaneous_layers = 5
        agent = StructureLockAgent(config)

        workflows = agent.build_structure_lock_workflow("fake_b64")
        assert "lineart_anime" in workflows
        assert "depth" not in workflows

    def test_build_workflow_with_override_configs(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = [_make_lineart_layer_config()]
        agent = StructureLockAgent(config)

        custom = [_make_canny_layer_config(enabled=True)]
        workflows = agent.build_structure_lock_workflow("fake_b64", control_configs=custom)
        assert "canny" in workflows
        assert "lineart_anime" not in workflows

    def test_each_workflow_is_valid(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = [
            _make_lineart_layer_config(),
            _make_depth_layer_config(),
        ]
        config.max_simultaneous_layers = 5
        agent = StructureLockAgent(config)

        workflows = agent.build_structure_lock_workflow("fake_b64")
        for layer_type, wf in workflows.items():
            for nid, node in wf.items():
                assert nid.isdigit(), f"{layer_type}: Node ID '{nid}' not digit"
                assert "class_type" in node
                assert "inputs" in node

    def test_execute_skips_without_composition_image(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        agent = StructureLockAgent(config)
        job = AnimePipelineJob(user_prompt="test")

        result = agent.execute(job)
        assert "structure_lock" in result.stages_executed
        assert len(result.structure_layers) == 0

    def test_execute_uses_source_image_fallback(self):
        """When no composition intermediate exists, fall back to source_image_b64."""
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = []  # no layers = no extraction
        agent = StructureLockAgent(config)

        job = AnimePipelineJob(user_prompt="test", source_image_b64="user_sketch")
        # With no layers configured, it just marks stage and returns
        result = agent.execute(job)
        assert "structure_lock" in result.stages_executed

    def test_strength_configurable(self):
        from image_pipeline.anime_pipeline.agents.structure_lock import StructureLockAgent
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig

        config = AnimePipelineConfig()
        config.structure_layers = [
            _make_lineart_layer_config(strength=0.42),
        ]
        config.max_simultaneous_layers = 5
        agent = StructureLockAgent(config)
        layers = agent.get_enabled_layers()

        assert layers[0].strength == 0.42


class TestStructureLockConfigYaml:
    """Test that YAML config parsing picks up structure lock settings."""

    def test_yaml_loads_enabled_field(self):
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        # lineart_anime and depth should be enabled, canny disabled (from YAML)
        layer_map = {lc.layer_type: lc for lc in config.structure_layers}
        if "lineart_anime" in layer_map:
            assert layer_map["lineart_anime"].enabled is True
        if "canny" in layer_map:
            assert layer_map["canny"].enabled is False

    def test_yaml_loads_strength_values(self):
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        layer_map = {lc.layer_type: lc for lc in config.structure_layers}
        if "lineart_anime" in layer_map:
            assert layer_map["lineart_anime"].strength == 0.85
        if "depth" in layer_map:
            assert layer_map["depth"].strength == 0.55
        if "canny" in layer_map:
            assert layer_map["canny"].strength == 0.35

    def test_yaml_loads_priority(self):
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        layer_map = {lc.layer_type: lc for lc in config.structure_layers}
        if "lineart_anime" in layer_map:
            assert layer_map["lineart_anime"].priority == 1
        if "depth" in layer_map:
            assert layer_map["depth"].priority == 2
        if "canny" in layer_map:
            assert layer_map["canny"].priority == 3

    def test_max_simultaneous_from_yaml(self):
        from image_pipeline.anime_pipeline.config import load_config

        config = load_config()
        assert config.max_simultaneous_layers == 2


# ═══════════════════════════════════════════════════════════════════════
# Cleanup pass — helpers
# ═══════════════════════════════════════════════════════════════════════

_FAKE_IMG_B64 = "iVBORw0KGgoAAAANSUhEUg" + "A" * 200

def _make_cleanup_pc(**overrides) -> "PassConfig":
    from image_pipeline.anime_pipeline.schemas import PassConfig, ControlInput
    defaults = dict(
        pass_name="cleanup",
        model_slot="base",
        checkpoint="animagine-xl-4.0-opt.safetensors",
        width=832,
        height=1216,
        sampler="euler_a",
        scheduler="normal",
        steps=20,
        cfg=5.0,
        denoise=0.45,
        seed=42,
        positive_prompt="1girl, school uniform, anime",
        negative_prompt="worst quality, lowres",
        control_inputs=[],
    )
    defaults.update(overrides)
    return PassConfig(**defaults)


def _make_structure_layer(layer_type="lineart_anime", strength=0.85, **kw):
    from image_pipeline.anime_pipeline.schemas import StructureLayer, StructureLayerType
    layer_map = {
        "lineart_anime": StructureLayerType.LINEART_ANIME,
        "depth": StructureLayerType.DEPTH,
        "canny": StructureLayerType.CANNY,
    }
    return StructureLayer(
        layer_type=layer_map.get(layer_type, StructureLayerType.LINEART_ANIME),
        image_b64=kw.get("image_b64", _FAKE_IMG_B64),
        controlnet_model=kw.get("controlnet_model", f"control_v11p_sd15_{layer_type}"),
        strength=strength,
        start_percent=kw.get("start_percent", 0.0),
        end_percent=kw.get("end_percent", 0.8),
    )


def _make_critique(**overrides) -> "CritiqueReport":
    from image_pipeline.anime_pipeline.schemas import CritiqueReport
    defaults = dict(
        anatomy_score=7,
        face_score=7,
        eye_consistency_score=7,
        hands_score=7,
        clothing_score=7,
        composition_score=7,
        color_score=7,
        style_score=7,
        background_score=7,
        accessories_score=7,
        pose_score=7,
        anatomy_issues=[],
        face_issues=[],
        eye_issues=[],
        hand_issues=[],
        clothing_issues=[],
        composition_issues=[],
        color_issues=[],
        style_drift=[],
        background_issues=[],
        accessories_issues=[],
        pose_issues=[],
        retry_recommendation=False,
    )
    defaults.update(overrides)
    return CritiqueReport(**defaults)


# ═══════════════════════════════════════════════════════════════════════
# Cleanup workflow builder tests
# ═══════════════════════════════════════════════════════════════════════

class TestCleanupWorkflow:
    """WorkflowBuilder.build_cleanup() node-level tests."""

    def test_required_nodes_present(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc()
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42)
        types = {n["class_type"] for n in w.values()}
        assert "CheckpointLoaderSimple" in types
        assert "LoadImageFromBase64" in types
        assert "VAEEncode" in types
        assert "KSampler" in types
        assert "VAEDecode" in types
        assert "SaveImage" in types

    def test_checkpoint_matches_config(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc(checkpoint="my_model.safetensors")
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=99)
        ckpt_nodes = [n for n in w.values() if n["class_type"] == "CheckpointLoaderSimple"]
        assert len(ckpt_nodes) == 1
        assert ckpt_nodes[0]["inputs"]["ckpt_name"] == "my_model.safetensors"

    def test_ksampler_denoise(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc(denoise=0.35)
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        assert len(ks) == 1
        assert ks[0]["inputs"]["denoise"] == 0.35

    def test_ksampler_seed(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc()
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=12345)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["seed"] == 12345

    def test_ksampler_steps_cfg(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc(steps=25, cfg=6.5)
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["steps"] == 25
        assert ks[0]["inputs"]["cfg"] == 6.5

    def test_clip_skip_1_no_extra_node(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc()
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42, clip_skip=1)
        clip_set = [n for n in w.values() if n["class_type"] == "CLIPSetLastLayer"]
        assert len(clip_set) == 0

    def test_clip_skip_2_inserts_node(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc()
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42, clip_skip=2)
        clip_set = [n for n in w.values() if n["class_type"] == "CLIPSetLastLayer"]
        assert len(clip_set) == 1
        assert clip_set[0]["inputs"]["stop_at_clip_layer"] == -2

    def test_filename_prefix(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc()
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=777)
        save = [n for n in w.values() if n["class_type"] == "SaveImage"]
        assert len(save) == 1
        assert save[0]["inputs"]["filename_prefix"] == "anime_pipeline/03_cleanup_777"

    def test_prompts_encoded(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc(
            positive_prompt="1girl, beautiful",
            negative_prompt="bad quality",
        )
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42)
        clip_texts = [n for n in w.values() if n["class_type"] == "CLIPTextEncode"]
        assert len(clip_texts) == 2
        prompts = {n["inputs"]["text"] for n in clip_texts}
        assert "1girl, beautiful" in prompts
        assert "bad quality" in prompts

    def test_source_image_loaded(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc()
        img = "AAAA" + "B" * 300
        w = wb.build_cleanup(pc, img, seed=42)
        load = [n for n in w.values() if n["class_type"] == "LoadImageFromBase64"]
        assert len(load) == 1
        assert load[0]["inputs"]["base64_image"] == img


class TestCleanupWorkflowControlNet:
    """ControlNet wiring in cleanup workflow."""

    def test_controlnet_nodes_added(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        from image_pipeline.anime_pipeline.schemas import ControlInput
        wb = WorkflowBuilder()
        ci = ControlInput(
            layer_type="lineart_anime",
            controlnet_model="control_lineart.safetensors",
            strength=0.85,
            start_percent=0.0,
            end_percent=0.8,
            image_b64=_FAKE_IMG_B64,
        )
        pc = _make_cleanup_pc(control_inputs=[ci])
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42)
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn_nodes) >= 1

    def test_controlnet_strength(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        from image_pipeline.anime_pipeline.schemas import ControlInput
        wb = WorkflowBuilder()
        ci = ControlInput(
            layer_type="lineart_anime",
            controlnet_model="control_lineart.safetensors",
            strength=0.70,
            start_percent=0.1,
            end_percent=0.9,
            image_b64=_FAKE_IMG_B64,
        )
        pc = _make_cleanup_pc(control_inputs=[ci])
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42)
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert cn_nodes[0]["inputs"]["strength"] == 0.70
        assert cn_nodes[0]["inputs"]["start_percent"] == 0.1
        assert cn_nodes[0]["inputs"]["end_percent"] == 0.9

    def test_multiple_controlnets(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        from image_pipeline.anime_pipeline.schemas import ControlInput
        wb = WorkflowBuilder()
        ci1 = ControlInput(
            layer_type="lineart_anime",
            controlnet_model="control_lineart.safetensors",
            strength=0.85,
            image_b64=_FAKE_IMG_B64,
        )
        ci2 = ControlInput(
            layer_type="depth",
            controlnet_model="control_depth.safetensors",
            strength=0.55,
            image_b64=_FAKE_IMG_B64,
        )
        pc = _make_cleanup_pc(control_inputs=[ci1, ci2])
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42)
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn_nodes) == 2

    def test_no_controlnet_without_inputs(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_cleanup_pc(control_inputs=[])
        w = wb.build_cleanup(pc, _FAKE_IMG_B64, seed=42)
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn_nodes) == 0


# ═══════════════════════════════════════════════════════════════════════
# Cleanup critique adjustment tests
# ═══════════════════════════════════════════════════════════════════════

class TestCleanupCritiqueAdjustment:
    """Tests for compute_cleanup_adjustments()."""

    def test_no_critique_returns_defaults(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments,
        )
        adj = compute_cleanup_adjustments(None, base_denoise=0.45)
        assert adj["denoise"] == 0.45
        assert adj["lineart_strength_delta"] == 0.0
        assert adj["negative_extra"] == ""

    def test_good_composition_lowers_denoise(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments,
        )
        critique = _make_critique(composition_score=9, anatomy_score=8)
        adj = compute_cleanup_adjustments(critique, base_denoise=0.45)
        assert adj["denoise"] < 0.45
        assert adj["denoise"] == pytest.approx(0.30)

    def test_anatomy_issues_raise_denoise(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments,
        )
        critique = _make_critique(
            anatomy_score=3,
            anatomy_issues=["broken arm", "extra finger", "wrong proportion"],
        )
        adj = compute_cleanup_adjustments(critique, base_denoise=0.45)
        assert adj["denoise"] > 0.45
        assert adj["denoise"] == pytest.approx(0.60)
        assert adj["lineart_strength_delta"] > 0

    def test_bad_hands_raises_denoise(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments,
        )
        critique = _make_critique(hands_score=2)
        adj = compute_cleanup_adjustments(critique, base_denoise=0.45)
        assert adj["denoise"] > 0.45
        assert adj["lineart_strength_delta"] > 0

    def test_busy_background_adds_negative(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments,
        )
        critique = _make_critique(
            background_score=3,
            background_issues=["busy background with too many objects"],
        )
        adj = compute_cleanup_adjustments(critique, base_denoise=0.45)
        assert "cluttered background" in adj["negative_extra"]

    def test_busy_background_keyword_trigger(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments,
        )
        critique = _make_critique(
            background_score=6,
            background_issues=["slightly cluttered"],
        )
        adj = compute_cleanup_adjustments(critique, base_denoise=0.45)
        assert "cluttered background" in adj["negative_extra"]

    def test_face_issues_maintain_moderate_denoise(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments,
        )
        # Good composition (would lower denoise) but bad face (should keep moderate)
        critique = _make_critique(
            composition_score=9, anatomy_score=8, face_score=3,
        )
        adj = compute_cleanup_adjustments(critique, base_denoise=0.45)
        assert adj["denoise"] >= 0.45

    def test_denoise_never_below_floor(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments, _DENOISE_FLOOR,
        )
        critique = _make_critique(composition_score=10, anatomy_score=10)
        adj = compute_cleanup_adjustments(critique, base_denoise=0.20)
        assert adj["denoise"] >= _DENOISE_FLOOR

    def test_denoise_never_above_ceiling(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments, _DENOISE_CEILING,
        )
        critique = _make_critique(
            anatomy_score=1, hands_score=1,
            anatomy_issues=["a", "b", "c", "d"],
        )
        adj = compute_cleanup_adjustments(critique, base_denoise=0.70)
        assert adj["denoise"] <= _DENOISE_CEILING

    def test_all_good_no_changes(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments,
        )
        critique = _make_critique(
            anatomy_score=7, face_score=7, hands_score=7,
            composition_score=7, background_score=7,
        )
        adj = compute_cleanup_adjustments(critique, base_denoise=0.45)
        # Not high enough for "good composition" (needs >=8), so stays default
        assert adj["denoise"] == 0.45
        assert adj["lineart_strength_delta"] == 0.0
        assert adj["negative_extra"] == ""

    def test_reason_populated(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import (
            compute_cleanup_adjustments,
        )
        critique = _make_critique(anatomy_score=2, background_score=3)
        adj = compute_cleanup_adjustments(critique, base_denoise=0.45)
        assert "anatomy" in adj["reason"]
        assert "background" in adj["reason"]


# ═══════════════════════════════════════════════════════════════════════
# CleanupPassAgent tests
# ═══════════════════════════════════════════════════════════════════════

class TestCleanupPassAgent:
    """Integration-level tests for CleanupPassAgent."""

    def _make_config(self):
        from image_pipeline.anime_pipeline.config import (
            AnimePipelineConfig, ModelConfig,
        )
        return AnimePipelineConfig(
            comfyui_url="http://localhost:8188",
            composition_model=ModelConfig(
                checkpoint="animagine-xl-4.0-opt.safetensors",
                clip_skip=2,
            ),
            beauty_model=ModelConfig(checkpoint="noobai-xl-1.1.safetensors"),
            upscale_model=ModelConfig(checkpoint="upscale.safetensors"),
        )

    def _make_job(self, with_composition=True, with_plan=True):
        from image_pipeline.anime_pipeline.schemas import (
            AnimePipelineJob, LayerPlan, IntermediateImage,
        )
        job = AnimePipelineJob(job_id="test-cleanup-001")
        if with_composition:
            job.intermediates.append(IntermediateImage(
                stage="composition_pass", image_b64=_FAKE_IMG_B64,
            ))
        if with_plan:
            job.layer_plan = LayerPlan(
                scene_summary="test scene",
                passes=[_make_cleanup_pc()],
            )
        return job

    def test_build_workflow_returns_dict(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc()
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42)
        assert isinstance(w, dict)
        types = {n["class_type"] for n in w.values()}
        assert "KSampler" in types

    def test_build_workflow_with_critique(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc(denoise=0.45)
        critique = _make_critique(composition_score=9, anatomy_score=8)
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42, critique=critique)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        # Critique says composition is good → denoise lowered
        assert ks[0]["inputs"]["denoise"] < 0.45

    def test_build_workflow_with_structure_layers(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc()
        layers = [_make_structure_layer("lineart_anime", 0.85)]
        w = agent.build_workflow(
            pc, _FAKE_IMG_B64, seed=42, structure_layers=layers,
        )
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn_nodes) == 1

    def test_build_workflow_anatomy_critique_boosts_lineart(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc()
        layers = [_make_structure_layer("lineart_anime", 0.85)]
        critique = _make_critique(anatomy_score=2)
        w = agent.build_workflow(
            pc, _FAKE_IMG_B64, seed=42,
            structure_layers=layers, critique=critique,
        )
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        # lineart strength should be boosted above 0.85
        assert cn_nodes[0]["inputs"]["strength"] > 0.85

    def test_build_workflow_clip_skip(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc()
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42, clip_skip=2)
        clip_set = [n for n in w.values() if n["class_type"] == "CLIPSetLastLayer"]
        assert len(clip_set) == 1
        assert clip_set[0]["inputs"]["stop_at_clip_layer"] == -2

    @patch("image_pipeline.anime_pipeline.agents.cleanup_pass.ComfyClient")
    def test_execute_success(self, MockClient):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult

        mock_result = ComfyJobResult(
            success=True,
            images_b64=[_FAKE_IMG_B64],
            duration_ms=1500.0,
        )
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = CleanupPassAgent(self._make_config())
        agent._client = mock_instance
        job = self._make_job()

        result = agent.execute(job)
        assert result.error is None
        intermediates = [i for i in result.intermediates if i.stage == "cleanup_pass"]
        assert len(intermediates) == 1
        assert "cleanup_pass" in result.stages_executed

    @patch("image_pipeline.anime_pipeline.agents.cleanup_pass.ComfyClient")
    def test_execute_no_plan_fails(self, MockClient):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        agent = CleanupPassAgent(self._make_config())
        job = self._make_job(with_plan=False)

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "No layer plan" in result.error

    @patch("image_pipeline.anime_pipeline.agents.cleanup_pass.ComfyClient")
    def test_execute_no_source_image_fails(self, MockClient):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        agent = CleanupPassAgent(self._make_config())
        job = self._make_job(with_composition=False)

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "No source image" in result.error

    @patch("image_pipeline.anime_pipeline.agents.cleanup_pass.ComfyClient")
    def test_execute_comfy_failure(self, MockClient):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        mock_result = ComfyJobResult(success=False, error="GPU OOM")
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = CleanupPassAgent(self._make_config())
        agent._client = mock_instance
        job = self._make_job()

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "GPU OOM" in result.error

    @patch("image_pipeline.anime_pipeline.agents.cleanup_pass.ComfyClient")
    def test_execute_with_critique(self, MockClient):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult

        mock_result = ComfyJobResult(
            success=True, images_b64=[_FAKE_IMG_B64], duration_ms=1200.0,
        )
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = CleanupPassAgent(self._make_config())
        agent._client = mock_instance
        job = self._make_job()
        job.structure_layers = [_make_structure_layer("lineart_anime", 0.85)]
        critique = _make_critique(anatomy_score=3)

        result = agent.execute(job, critique=critique)
        assert result.error is None
        # Verify workflow was submitted
        mock_instance.submit_workflow.assert_called_once()

    @patch("image_pipeline.anime_pipeline.agents.cleanup_pass.ComfyClient")
    def test_execute_empty_images_fails(self, MockClient):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        mock_result = ComfyJobResult(success=True, images_b64=[], duration_ms=500.0)
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = CleanupPassAgent(self._make_config())
        agent._client = mock_instance
        job = self._make_job()

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "no image" in result.error.lower()


class TestCleanupPassAgentApplyAdjustments:
    """Unit tests for _apply_adjustments internal method."""

    def _make_config(self):
        from image_pipeline.anime_pipeline.config import (
            AnimePipelineConfig, ModelConfig,
        )
        return AnimePipelineConfig(
            comfyui_url="http://localhost:8188",
            composition_model=ModelConfig(checkpoint="test.safetensors"),
            beauty_model=ModelConfig(checkpoint="test.safetensors"),
            upscale_model=ModelConfig(checkpoint="test.safetensors"),
        )

    def test_lineart_boost_applied(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc()
        layers = [_make_structure_layer("lineart_anime", 0.80)]
        adjustments = {
            "denoise": 0.60,
            "lineart_strength_delta": 0.15,
            "negative_extra": "",
        }
        result_pc = agent._apply_adjustments(pc, adjustments, layers)
        # Lineart should be boosted: 0.80 + 0.15 = 0.95
        assert len(result_pc.control_inputs) == 1
        assert result_pc.control_inputs[0].strength == pytest.approx(0.95)

    def test_lineart_boost_capped_at_1(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc()
        layers = [_make_structure_layer("lineart_anime", 0.95)]
        adjustments = {
            "denoise": 0.60,
            "lineart_strength_delta": 0.15,
            "negative_extra": "",
        }
        result_pc = agent._apply_adjustments(pc, adjustments, layers)
        assert result_pc.control_inputs[0].strength == 1.0

    def test_depth_layer_not_boosted(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc()
        layers = [_make_structure_layer("depth", 0.55)]
        adjustments = {
            "denoise": 0.60,
            "lineart_strength_delta": 0.15,
            "negative_extra": "",
        }
        result_pc = agent._apply_adjustments(pc, adjustments, layers)
        assert result_pc.control_inputs[0].strength == 0.55

    def test_negative_extra_appended(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc(negative_prompt="worst quality")
        layers = []
        adjustments = {
            "denoise": 0.45,
            "lineart_strength_delta": 0.0,
            "negative_extra": "cluttered background",
        }
        result_pc = agent._apply_adjustments(pc, adjustments, layers)
        assert "worst quality" in result_pc.negative_prompt
        assert "cluttered background" in result_pc.negative_prompt

    def test_denoise_from_adjustments(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        agent = CleanupPassAgent(self._make_config())
        pc = _make_cleanup_pc(denoise=0.45)
        adjustments = {
            "denoise": 0.30,
            "lineart_strength_delta": 0.0,
            "negative_extra": "",
        }
        result_pc = agent._apply_adjustments(pc, adjustments, [])
        assert result_pc.denoise == 0.30

    def test_max_simultaneous_layers_respected(self):
        from image_pipeline.anime_pipeline.agents.cleanup_pass import CleanupPassAgent
        config = self._make_config()
        config.max_simultaneous_layers = 1
        agent = CleanupPassAgent(config)
        pc = _make_cleanup_pc()
        layers = [
            _make_structure_layer("lineart_anime", 0.85),
            _make_structure_layer("depth", 0.55),
        ]
        adjustments = {
            "denoise": 0.45,
            "lineart_strength_delta": 0.0,
            "negative_extra": "",
        }
        result_pc = agent._apply_adjustments(pc, adjustments, layers)
        # Only 1 layer should be included (max_simultaneous_layers=1)
        assert len(result_pc.control_inputs) == 1


class TestCleanupPassExport:
    """Test that CleanupPassAgent is properly exported."""

    def test_import_from_agents(self):
        from image_pipeline.anime_pipeline.agents import CleanupPassAgent
        assert CleanupPassAgent is not None

    def test_import_from_agents_all(self):
        from image_pipeline.anime_pipeline import agents
        assert "CleanupPassAgent" in agents.__all__


# ═══════════════════════════════════════════════════════════════════════
# Beauty pass — helpers
# ═══════════════════════════════════════════════════════════════════════

def _make_beauty_pc(**overrides) -> "PassConfig":
    from image_pipeline.anime_pipeline.schemas import PassConfig
    defaults = dict(
        pass_name="beauty",
        model_slot="final",
        checkpoint="noobaiXLNAIXL_vPred10Version.safetensors",
        width=832,
        height=1216,
        sampler="euler_a",
        scheduler="normal",
        steps=28,
        cfg=5.5,
        denoise=0.30,
        seed=42,
        positive_prompt="1girl, school uniform, anime",
        negative_prompt="worst quality, lowres",
        control_inputs=[],
    )
    defaults.update(overrides)
    return PassConfig(**defaults)


def _make_beauty_config(**overrides):
    from image_pipeline.anime_pipeline.config import (
        AnimePipelineConfig, ModelConfig, BeautyStrength,
    )
    defaults = dict(
        comfyui_url="http://localhost:8188",
        composition_model=ModelConfig(
            checkpoint="animagine-xl-4.0-opt.safetensors",
            clip_skip=2,
        ),
        beauty_model=ModelConfig(
            checkpoint="flatpiececorexl_a1818.safetensors",
            denoise_strength=0.45,
        ),
        final_model=ModelConfig(
            checkpoint="noobaiXLNAIXL_vPred10Version.safetensors",
            sampler="euler_a",
            scheduler="normal",
            steps=28,
            cfg=5.5,
            clip_skip=2,
            denoise_strength=0.30,
        ),
        upscale_model="RealESRGAN_x4plus_anime_6B",
        beauty_strength=BeautyStrength.BALANCED,
    )
    defaults.update(overrides)
    return AnimePipelineConfig(**defaults)


def _make_beauty_job(with_cleanup=True, with_plan=True):
    from image_pipeline.anime_pipeline.schemas import (
        AnimePipelineJob, LayerPlan, IntermediateImage,
    )
    job = AnimePipelineJob(job_id="test-beauty-001")
    if with_cleanup:
        job.intermediates.append(IntermediateImage(
            stage="cleanup_pass", image_b64=_FAKE_IMG_B64,
        ))
    if with_plan:
        job.layer_plan = LayerPlan(
            scene_summary="test scene",
            passes=[_make_beauty_pc()],
        )
    return job


# ═══════════════════════════════════════════════════════════════════════
# Beauty config tests
# ═══════════════════════════════════════════════════════════════════════

class TestBeautyConfig:
    """BeautyStrength, presets, final_model, and YAML loading."""

    def test_beauty_strength_enum_values(self):
        from image_pipeline.anime_pipeline.config import BeautyStrength
        assert BeautyStrength.SUBTLE.value == "subtle"
        assert BeautyStrength.BALANCED.value == "balanced"
        assert BeautyStrength.AGGRESSIVE.value == "aggressive"

    def test_get_beauty_preset_subtle(self):
        from image_pipeline.anime_pipeline.config import get_beauty_preset
        p = get_beauty_preset("subtle")
        assert p["denoise"] < 0.25
        assert "steps" in p and "cfg" in p

    def test_get_beauty_preset_balanced(self):
        from image_pipeline.anime_pipeline.config import get_beauty_preset
        p = get_beauty_preset("balanced")
        assert 0.25 <= p["denoise"] <= 0.40

    def test_get_beauty_preset_aggressive(self):
        from image_pipeline.anime_pipeline.config import get_beauty_preset
        p = get_beauty_preset("aggressive")
        assert p["denoise"] >= 0.40

    def test_get_beauty_preset_from_enum(self):
        from image_pipeline.anime_pipeline.config import (
            get_beauty_preset, BeautyStrength,
        )
        p = get_beauty_preset(BeautyStrength.BALANCED)
        assert p["denoise"] == pytest.approx(0.30)

    def test_final_model_in_config(self):
        config = _make_beauty_config()
        assert config.final_model.checkpoint == "noobaiXLNAIXL_vPred10Version.safetensors"
        assert config.final_model.clip_skip == 2

    def test_final_model_defaults_to_beauty_model(self):
        from image_pipeline.anime_pipeline.config import load_config
        config = load_config()
        # final_model should be populated (either from YAML or fallback to beauty)
        assert config.final_model.checkpoint != ""

    def test_beauty_strength_from_yaml(self):
        from image_pipeline.anime_pipeline.config import load_config
        config = load_config()
        # Should be "balanced" from our YAML
        assert config.beauty_strength.value == "balanced"

    def test_final_model_env_override(self):
        from image_pipeline.anime_pipeline.config import load_config
        with patch.dict(os.environ, {"ANIME_PIPELINE_FINAL_MODEL": "custom_final.safetensors"}):
            config = load_config()
            assert config.final_model.checkpoint == "custom_final.safetensors"

    def test_beauty_strength_env_override(self):
        from image_pipeline.anime_pipeline.config import load_config, BeautyStrength
        with patch.dict(os.environ, {"ANIME_PIPELINE_BEAUTY_STRENGTH": "aggressive"}):
            config = load_config()
            assert config.beauty_strength == BeautyStrength.AGGRESSIVE


# ═══════════════════════════════════════════════════════════════════════
# Beauty workflow builder tests
# ═══════════════════════════════════════════════════════════════════════

class TestBeautyWorkflow:
    """WorkflowBuilder.build_beauty() node-level tests."""

    def test_required_nodes_present(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc()
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=42)
        types = {n["class_type"] for n in w.values()}
        assert "CheckpointLoaderSimple" in types
        assert "LoadImageFromBase64" in types
        assert "VAEEncode" in types
        assert "KSampler" in types
        assert "VAEDecode" in types
        assert "SaveImage" in types

    def test_checkpoint_matches_config(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc(checkpoint="custom_model.safetensors")
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=99)
        ckpt_nodes = [n for n in w.values() if n["class_type"] == "CheckpointLoaderSimple"]
        assert len(ckpt_nodes) == 1
        assert ckpt_nodes[0]["inputs"]["ckpt_name"] == "custom_model.safetensors"

    def test_ksampler_denoise(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc(denoise=0.25)
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=42)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["denoise"] == 0.25

    def test_ksampler_seed(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc()
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=54321)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["seed"] == 54321

    def test_ksampler_steps_cfg(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc(steps=30, cfg=6.0)
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=42)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["steps"] == 30
        assert ks[0]["inputs"]["cfg"] == 6.0

    def test_clip_skip_1_no_extra_node(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc()
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=42, clip_skip=1)
        clip_set = [n for n in w.values() if n["class_type"] == "CLIPSetLastLayer"]
        assert len(clip_set) == 0

    def test_clip_skip_2_inserts_node(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc()
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=42, clip_skip=2)
        clip_set = [n for n in w.values() if n["class_type"] == "CLIPSetLastLayer"]
        assert len(clip_set) == 1
        assert clip_set[0]["inputs"]["stop_at_clip_layer"] == -2

    def test_filename_prefix(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc()
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=888)
        save = [n for n in w.values() if n["class_type"] == "SaveImage"]
        assert save[0]["inputs"]["filename_prefix"] == "anime_pipeline/04_beauty_888"

    def test_prompts_encoded(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc(
            positive_prompt="1girl, masterpiece",
            negative_prompt="ugly, deformed",
        )
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=42)
        clip_texts = [n for n in w.values() if n["class_type"] == "CLIPTextEncode"]
        assert len(clip_texts) == 2
        prompts = {n["inputs"]["text"] for n in clip_texts}
        assert "1girl, masterpiece" in prompts
        assert "ugly, deformed" in prompts

    def test_source_image_loaded(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc()
        img = "ZZZZ" + "Q" * 300
        w = wb.build_beauty(pc, img, seed=42)
        load = [n for n in w.values() if n["class_type"] == "LoadImageFromBase64"]
        assert len(load) == 1
        assert load[0]["inputs"]["base64_image"] == img


class TestBeautyWorkflowControlNet:
    """ControlNet wiring in beauty workflow."""

    def test_controlnet_nodes_added(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        from image_pipeline.anime_pipeline.schemas import ControlInput
        wb = WorkflowBuilder()
        ci = ControlInput(
            layer_type="lineart_anime",
            controlnet_model="control_lineart.safetensors",
            strength=0.60,
            image_b64=_FAKE_IMG_B64,
        )
        pc = _make_beauty_pc(control_inputs=[ci])
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=42)
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn_nodes) >= 1

    def test_no_controlnet_without_inputs(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        pc = _make_beauty_pc(control_inputs=[])
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=42)
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn_nodes) == 0

    def test_multiple_controlnets(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        from image_pipeline.anime_pipeline.schemas import ControlInput
        wb = WorkflowBuilder()
        ci1 = ControlInput(
            layer_type="lineart_anime",
            controlnet_model="control_lineart.safetensors",
            strength=0.60,
            image_b64=_FAKE_IMG_B64,
        )
        ci2 = ControlInput(
            layer_type="depth",
            controlnet_model="control_depth.safetensors",
            strength=0.35,
            image_b64=_FAKE_IMG_B64,
        )
        pc = _make_beauty_pc(control_inputs=[ci1, ci2])
        w = wb.build_beauty(pc, _FAKE_IMG_B64, seed=42)
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn_nodes) == 2


# ═══════════════════════════════════════════════════════════════════════
# Beauty prompt construction tests
# ═══════════════════════════════════════════════════════════════════════

class TestBeautyPromptConstruction:
    """refine_beauty_prompt() and build_beauty_negative() tests."""

    def test_refine_adds_quality_tags(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import (
            refine_beauty_prompt,
        )
        result = refine_beauty_prompt("1girl, school uniform")
        assert "masterpiece" in result
        assert "detailed eyes" in result
        assert "1girl, school uniform" in result

    def test_refine_no_duplicate(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import (
            refine_beauty_prompt,
        )
        result = refine_beauty_prompt("masterpiece, detailed eyes, 1girl")
        # Should not add "masterpiece" or "detailed eyes" again
        assert result.count("masterpiece") == 1
        assert result.count("detailed eyes") == 1

    def test_build_negative_adds_identity_protection(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import (
            build_beauty_negative,
        )
        result = build_beauty_negative("worst quality, lowres")
        assert "blurry face" in result
        assert "asymmetrical eyes" in result

    def test_build_negative_no_duplicate(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import (
            build_beauty_negative,
        )
        result = build_beauty_negative("blurry face, asymmetrical eyes, ugly")
        assert result.count("blurry face") == 1


# ═══════════════════════════════════════════════════════════════════════
# BeautyPassAgent tests
# ═══════════════════════════════════════════════════════════════════════

class TestBeautyPassAgent:
    """Integration-level tests for BeautyPassAgent."""

    def test_build_workflow_returns_dict(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        agent = BeautyPassAgent(_make_beauty_config())
        pc = _make_beauty_pc()
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42)
        assert isinstance(w, dict)
        types = {n["class_type"] for n in w.values()}
        assert "KSampler" in types

    def test_build_workflow_uses_final_model(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        config = _make_beauty_config()
        agent = BeautyPassAgent(config)
        pc = _make_beauty_pc(checkpoint="should_be_overridden.safetensors")
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42)
        ckpt = [n for n in w.values() if n["class_type"] == "CheckpointLoaderSimple"]
        # Should use final_model checkpoint, not the pc's checkpoint
        assert ckpt[0]["inputs"]["ckpt_name"] == "noobaiXLNAIXL_vPred10Version.safetensors"

    def test_build_workflow_subtle_low_denoise(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.config import BeautyStrength
        agent = BeautyPassAgent(_make_beauty_config())
        pc = _make_beauty_pc()
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42, strength=BeautyStrength.SUBTLE)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["denoise"] < 0.25

    def test_build_workflow_aggressive_high_denoise(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.config import BeautyStrength
        agent = BeautyPassAgent(_make_beauty_config())
        pc = _make_beauty_pc()
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42, strength=BeautyStrength.AGGRESSIVE)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["denoise"] >= 0.40

    def test_build_workflow_with_structure_layers(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        agent = BeautyPassAgent(_make_beauty_config())
        pc = _make_beauty_pc()
        layers = [_make_structure_layer("lineart_anime", 0.85)]
        w = agent.build_workflow(
            pc, _FAKE_IMG_B64, seed=42, structure_layers=layers,
        )
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn_nodes) == 1

    def test_control_strength_reduced(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        agent = BeautyPassAgent(_make_beauty_config())
        pc = _make_beauty_pc()
        layers = [_make_structure_layer("lineart_anime", 0.85)]
        w = agent.build_workflow(
            pc, _FAKE_IMG_B64, seed=42, structure_layers=layers,
        )
        cn_nodes = [n for n in w.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        # Strength should be reduced by _CONTROL_STRENGTH_FACTOR (0.70)
        assert cn_nodes[0]["inputs"]["strength"] == pytest.approx(0.85 * 0.70)

    def test_build_workflow_clip_skip(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        agent = BeautyPassAgent(_make_beauty_config())
        pc = _make_beauty_pc()
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42, clip_skip=2)
        clip_set = [n for n in w.values() if n["class_type"] == "CLIPSetLastLayer"]
        assert len(clip_set) == 1
        assert clip_set[0]["inputs"]["stop_at_clip_layer"] == -2

    def test_build_workflow_prompt_enhanced(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        agent = BeautyPassAgent(_make_beauty_config())
        pc = _make_beauty_pc(positive_prompt="1girl, school uniform")
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42)
        clip_texts = [n for n in w.values() if n["class_type"] == "CLIPTextEncode"]
        pos_texts = [n["inputs"]["text"] for n in clip_texts]
        # At least one positive should contain quality tags
        assert any("masterpiece" in t for t in pos_texts)
        assert any("detailed eyes" in t for t in pos_texts)

    def test_build_workflow_negative_enhanced(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        agent = BeautyPassAgent(_make_beauty_config())
        pc = _make_beauty_pc(negative_prompt="worst quality")
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42)
        clip_texts = [n for n in w.values() if n["class_type"] == "CLIPTextEncode"]
        neg_texts = [n["inputs"]["text"] for n in clip_texts]
        # At least one negative should contain identity protection
        assert any("blurry face" in t for t in neg_texts)

    @patch("image_pipeline.anime_pipeline.agents.beauty_pass.ComfyClient")
    def test_execute_success(self, MockClient):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult

        mock_result = ComfyJobResult(
            success=True,
            images_b64=[_FAKE_IMG_B64],
            duration_ms=2000.0,
        )
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = BeautyPassAgent(_make_beauty_config())
        agent._client = mock_instance
        job = _make_beauty_job()

        result = agent.execute(job)
        assert result.error is None
        intermediates = [i for i in result.intermediates if i.stage == "beauty_pass"]
        assert len(intermediates) == 1
        assert "beauty_pass" in result.stages_executed

    @patch("image_pipeline.anime_pipeline.agents.beauty_pass.ComfyClient")
    def test_execute_no_plan_fails(self, MockClient):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        agent = BeautyPassAgent(_make_beauty_config())
        job = _make_beauty_job(with_plan=False)

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "No layer plan" in result.error

    @patch("image_pipeline.anime_pipeline.agents.beauty_pass.ComfyClient")
    def test_execute_no_source_fails(self, MockClient):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        agent = BeautyPassAgent(_make_beauty_config())
        job = _make_beauty_job(with_cleanup=False)

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "No source image" in result.error

    @patch("image_pipeline.anime_pipeline.agents.beauty_pass.ComfyClient")
    def test_execute_comfy_failure(self, MockClient):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        mock_result = ComfyJobResult(success=False, error="GPU OOM")
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = BeautyPassAgent(_make_beauty_config())
        agent._client = mock_instance
        job = _make_beauty_job()

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "GPU OOM" in result.error

    @patch("image_pipeline.anime_pipeline.agents.beauty_pass.ComfyClient")
    def test_execute_empty_images_fails(self, MockClient):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        mock_result = ComfyJobResult(success=True, images_b64=[], duration_ms=500.0)
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = BeautyPassAgent(_make_beauty_config())
        agent._client = mock_instance
        job = _make_beauty_job()

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "no image" in result.error.lower()

    @patch("image_pipeline.anime_pipeline.agents.beauty_pass.ComfyClient")
    def test_execute_with_retry_seed(self, MockClient):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult

        mock_result = ComfyJobResult(
            success=True, images_b64=[_FAKE_IMG_B64], duration_ms=1000.0,
        )
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = BeautyPassAgent(_make_beauty_config())
        agent._client = mock_instance
        job = _make_beauty_job()

        result = agent.execute(job, retry_seed=99999)
        assert result.error is None
        # Check that the retry seed was used
        submitted_workflow = mock_instance.submit_workflow.call_args[0][0]
        ks = [n for n in submitted_workflow.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["seed"] == 99999

    @patch("image_pipeline.anime_pipeline.agents.beauty_pass.ComfyClient")
    def test_execute_with_strength_override(self, MockClient):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult

        mock_result = ComfyJobResult(
            success=True, images_b64=[_FAKE_IMG_B64], duration_ms=1000.0,
        )
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = BeautyPassAgent(_make_beauty_config())
        agent._client = mock_instance
        job = _make_beauty_job()

        result = agent.execute(job, strength="subtle")
        assert result.error is None
        submitted = mock_instance.submit_workflow.call_args[0][0]
        ks = [n for n in submitted.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["denoise"] < 0.25

    @patch("image_pipeline.anime_pipeline.agents.beauty_pass.ComfyClient")
    def test_execute_prefers_cleanup_over_composition(self, MockClient):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
        from image_pipeline.anime_pipeline.schemas import IntermediateImage

        mock_result = ComfyJobResult(
            success=True, images_b64=["output_img"], duration_ms=500.0,
        )
        mock_instance = MagicMock()
        mock_instance.submit_workflow.return_value = mock_result
        MockClient.return_value = mock_instance

        agent = BeautyPassAgent(_make_beauty_config())
        agent._client = mock_instance
        job = _make_beauty_job(with_cleanup=False)
        # Add both composition and cleanup
        job.intermediates.append(IntermediateImage(
            stage="composition_pass", image_b64="comp_image_data",
        ))
        job.intermediates.append(IntermediateImage(
            stage="cleanup_pass", image_b64="cleanup_image_data",
        ))

        result = agent.execute(job)
        assert result.error is None
        # Verify cleanup image was used as source (not composition)
        submitted = mock_instance.submit_workflow.call_args[0][0]
        load_nodes = [n for n in submitted.values() if n["class_type"] == "LoadImageFromBase64"]
        # The first LoadImageFromBase64 should have the cleanup image
        assert load_nodes[0]["inputs"]["base64_image"] == "cleanup_image_data"


class TestBeautyPassAgentBuildControls:
    """Unit tests for _build_controls internal method."""

    def test_strength_reduced_by_factor(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import (
            BeautyPassAgent, _CONTROL_STRENGTH_FACTOR,
        )
        agent = BeautyPassAgent(_make_beauty_config())
        layers = [_make_structure_layer("lineart_anime", 1.0)]
        controls = agent._build_controls(layers, [])
        assert len(controls) == 1
        assert controls[0].strength == pytest.approx(_CONTROL_STRENGTH_FACTOR)

    def test_max_simultaneous_respected(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.config import BeautyStrength
        config = _make_beauty_config()
        config.max_simultaneous_layers = 1
        agent = BeautyPassAgent(config)
        layers = [
            _make_structure_layer("lineart_anime", 0.85),
            _make_structure_layer("depth", 0.55),
        ]
        controls = agent._build_controls(layers, [])
        assert len(controls) == 1

    def test_skips_layers_without_model(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.schemas import StructureLayer, StructureLayerType
        agent = BeautyPassAgent(_make_beauty_config())
        layers = [StructureLayer(
            layer_type=StructureLayerType.LINEART_ANIME,
            image_b64=_FAKE_IMG_B64,
            controlnet_model="",  # no model
        )]
        controls = agent._build_controls(layers, [])
        assert len(controls) == 0

    def test_existing_controls_also_reduced(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import (
            BeautyPassAgent, _CONTROL_STRENGTH_FACTOR,
        )
        from image_pipeline.anime_pipeline.schemas import ControlInput
        agent = BeautyPassAgent(_make_beauty_config())
        existing = [ControlInput(
            layer_type="lineart_anime",
            controlnet_model="model.safetensors",
            strength=0.80,
            image_b64=_FAKE_IMG_B64,
        )]
        controls = agent._build_controls([], existing)
        assert len(controls) == 1
        assert controls[0].strength == pytest.approx(0.80 * _CONTROL_STRENGTH_FACTOR)


class TestBeautyPassModelSwap:
    """Verify final_model is swappable without orchestration changes."""

    def test_different_final_model_used(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.config import ModelConfig
        config = _make_beauty_config()
        config.final_model = ModelConfig(
            checkpoint="illustrious-xl-v1.safetensors",
            sampler="dpmpp_2m_sde",
            scheduler="karras",
            steps=30,
            cfg=5.0,
            clip_skip=1,
        )
        agent = BeautyPassAgent(config)
        pc = _make_beauty_pc()
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42)
        ckpt = [n for n in w.values() if n["class_type"] == "CheckpointLoaderSimple"]
        assert ckpt[0]["inputs"]["ckpt_name"] == "illustrious-xl-v1.safetensors"

    def test_sampler_from_final_model(self):
        from image_pipeline.anime_pipeline.agents.beauty_pass import BeautyPassAgent
        from image_pipeline.anime_pipeline.config import ModelConfig
        config = _make_beauty_config()
        config.final_model = ModelConfig(
            checkpoint="test.safetensors",
            sampler="dpmpp_sde",
            scheduler="exponential",
        )
        agent = BeautyPassAgent(config)
        pc = _make_beauty_pc()
        w = agent.build_workflow(pc, _FAKE_IMG_B64, seed=42)
        ks = [n for n in w.values() if n["class_type"] == "KSampler"]
        assert ks[0]["inputs"]["sampler_name"] == "dpmpp_sde"
        assert ks[0]["inputs"]["scheduler"] == "exponential"


class TestBeautyPassExport:
    """Test that BeautyPassAgent is properly exported."""

    def test_import_from_agents(self):
        from image_pipeline.anime_pipeline.agents import BeautyPassAgent
        assert BeautyPassAgent is not None

    def test_import_from_agents_all(self):
        from image_pipeline.anime_pipeline import agents
        assert "BeautyPassAgent" in agents.__all__


# ═══════════════════════════════════════════════════════════════════════
# Refine loop — helpers
# ═══════════════════════════════════════════════════════════════════════

def _make_refine_config(**overrides):
    """Config with refine-relevant defaults. Extends _make_beauty_config."""
    from image_pipeline.anime_pipeline.config import (
        AnimePipelineConfig, ModelConfig, BeautyStrength,
    )
    defaults = dict(
        comfyui_url="http://localhost:8188",
        composition_model=ModelConfig(
            checkpoint="animagine-xl-4.0-opt.safetensors",
            clip_skip=2,
        ),
        beauty_model=ModelConfig(
            checkpoint="flatpiececorexl_a1818.safetensors",
            denoise_strength=0.45,
        ),
        final_model=ModelConfig(
            checkpoint="noobaiXLNAIXL_vPred10Version.safetensors",
            sampler="euler_a",
            scheduler="normal",
            steps=28,
            cfg=5.5,
            clip_skip=2,
            denoise_strength=0.30,
        ),
        upscale_model="RealESRGAN_x4plus_anime_6B",
        beauty_strength=BeautyStrength.BALANCED,
        max_refine_rounds=2,
        return_best_on_fail=True,
        refine_score_threshold=7.0,
        refine_denoise_step_up=0.05,
        refine_denoise_step_down=0.03,
        refine_denoise_floor=0.12,
        refine_denoise_ceiling=0.55,
        refine_control_boost=0.10,
        refine_control_reduce=0.05,
        refine_dimension_thresholds={
            "anatomy": 5, "face_symmetry": 5, "eye_consistency": 5,
            "hand_quality": 4, "clothing_consistency": 5,
            "composition": 5, "color_drift": 5, "style_drift": 5,
            "background_clutter": 4, "missing_accessories": 4,
            "pose_drift": 5,
        },
        refine_artifact_accumulation_limit=8,
    )
    defaults.update(overrides)
    return AnimePipelineConfig(**defaults)


def _make_refine_job(with_beauty=True, with_plan=True):
    """Job with beauty_pass intermediate for refine loop testing."""
    from image_pipeline.anime_pipeline.schemas import (
        AnimePipelineJob, LayerPlan, IntermediateImage,
    )
    job = AnimePipelineJob(job_id="test-refine-001")
    if with_beauty:
        job.intermediates.append(IntermediateImage(
            stage="beauty_pass", image_b64=_FAKE_IMG_B64,
        ))
    if with_plan:
        job.layer_plan = LayerPlan(
            scene_summary="test scene",
            passes=[_make_beauty_pc()],
        )
    return job


# ═══════════════════════════════════════════════════════════════════════
# CritiqueReport expanded — new dimension tests
# ═══════════════════════════════════════════════════════════════════════

class TestCritiqueReportExpanded:
    """Verify CritiqueReport's new dimensions, weights, and properties."""

    def test_dimension_scores_returns_all_10(self):
        cr = _make_critique()
        ds = cr.dimension_scores
        assert len(ds) == 11  # 11 dimensions (10 named + removed eye_reference_match_pct)
        expected_keys = {
            "anatomy", "face_symmetry", "eye_consistency", "hand_quality",
            "clothing_consistency", "composition", "color_drift", "style_drift",
            "background_clutter", "missing_accessories", "pose_drift",
        }
        assert set(ds.keys()) == expected_keys

    def test_overall_score_all_sevens(self):
        cr = _make_critique()  # all scores = 7
        assert cr.overall_score == pytest.approx(7.0, abs=0.01)

    def test_overall_score_weighted(self):
        """Face at 1.5x weight should pull score up more than background at 0.7x."""
        high_face = _make_critique(face_score=10, background_score=0)
        low_face = _make_critique(face_score=0, background_score=10)
        assert high_face.overall_score > low_face.overall_score

    def test_overall_score_face_weight_is_highest(self):
        """Changing face_score by 1 should impact more than changing accessories_score by 1."""
        base = _make_critique()
        face_up = _make_critique(face_score=8)
        acc_up = _make_critique(accessories_score=8)
        face_delta = face_up.overall_score - base.overall_score
        acc_delta = acc_up.overall_score - base.overall_score
        assert face_delta > acc_delta

    def test_all_issues_includes_new_lists(self):
        cr = _make_critique(
            eye_issues=["mismatched pupils"],
            clothing_issues=["torn shirt"],
            accessories_issues=["missing earring"],
            pose_issues=["twisted torso"],
        )
        issues = cr.all_issues
        assert "mismatched pupils" in issues
        assert "torn shirt" in issues
        assert "missing earring" in issues
        assert "twisted torso" in issues

    def test_passed_true_when_all_high(self):
        cr = _make_critique(
            anatomy_score=8, face_score=8, eye_consistency_score=8,
            hands_score=8, clothing_score=8, composition_score=8,
            color_score=8, style_score=8, background_score=8,
            accessories_score=8, pose_score=8,
        )
        assert cr.passed is True

    def test_passed_false_when_retry_recommended(self):
        cr = _make_critique(retry_recommendation=True)
        assert cr.passed is False

    def test_passed_false_when_scores_low(self):
        cr = _make_critique(anatomy_score=1, face_score=1, hands_score=1)
        assert cr.passed is False

    def test_to_dict_has_new_fields(self):
        cr = _make_critique()
        d = cr.to_dict()
        assert "eye_consistency_score" in d
        assert "clothing_score" in d
        assert "accessories_score" in d
        assert "pose_score" in d
        assert "dimension_scores" in d
        assert "passed" in d
        assert "overall_score" in d

    def test_to_dict_dimension_scores_match(self):
        cr = _make_critique(anatomy_score=9, pose_score=3)
        d = cr.to_dict()
        assert d["dimension_scores"]["anatomy"] == 9
        assert d["dimension_scores"]["pose_drift"] == 3


# ═══════════════════════════════════════════════════════════════════════
# RefineAction / RefineDecision schema tests
# ═══════════════════════════════════════════════════════════════════════

class TestRefineSchemas:
    """Test RefineActionType, RefineAction, RefineDecision dataclasses."""

    def test_action_type_values(self):
        from image_pipeline.anime_pipeline.schemas import RefineActionType
        assert RefineActionType.ADJUST_DENOISE.value == "adjust_denoise"
        assert RefineActionType.PATCH_POSITIVE.value == "patch_positive"
        assert RefineActionType.SWITCH_PRESET.value == "switch_preset"

    def test_refine_action_to_dict(self):
        from image_pipeline.anime_pipeline.schemas import RefineAction, RefineActionType
        a = RefineAction(
            action_type=RefineActionType.PATCH_NEGATIVE,
            target="negative",
            value="bad anatomy",
            reason="anatomy score low",
        )
        d = a.to_dict()
        assert d["action_type"] == "patch_negative"
        assert d["target"] == "negative"
        assert d["value"] == "bad anatomy"
        assert d["reason"] == "anatomy score low"

    def test_refine_decision_to_dict(self):
        from image_pipeline.anime_pipeline.schemas import (
            RefineAction, RefineActionType, RefineDecision,
        )
        dec = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.ADJUST_DENOISE,
                target="denoise", value=0.05,
            )],
            reason="score below threshold",
            worst_dimensions=["anatomy", "hand_quality"],
        )
        d = dec.to_dict()
        assert d["should_refine"] is True
        assert len(d["actions"]) == 1
        assert d["worst_dimensions"] == ["anatomy", "hand_quality"]

    def test_refine_decision_defaults(self):
        from image_pipeline.anime_pipeline.schemas import RefineDecision
        dec = RefineDecision()
        assert dec.should_refine is False
        assert dec.actions == []
        assert dec.worst_dimensions == []

    def test_import_from_package(self):
        from image_pipeline.anime_pipeline import (
            RefineAction, RefineActionType, RefineDecision,
        )
        assert RefineAction is not None
        assert RefineActionType is not None
        assert RefineDecision is not None


# ═══════════════════════════════════════════════════════════════════════
# Refine config tests
# ═══════════════════════════════════════════════════════════════════════

class TestRefineConfig:
    """Test that refine fields load correctly from YAML and env."""

    def test_config_defaults(self):
        config = _make_refine_config()
        assert config.refine_score_threshold == 7.0
        assert config.refine_denoise_step_up == 0.05
        assert config.refine_denoise_floor == 0.12
        assert config.refine_denoise_ceiling == 0.55
        assert config.max_refine_rounds == 2
        assert config.refine_artifact_accumulation_limit == 8

    def test_dimension_thresholds_loaded(self):
        config = _make_refine_config()
        assert config.refine_dimension_thresholds["anatomy"] == 5
        assert config.refine_dimension_thresholds["hand_quality"] == 4
        assert config.refine_dimension_thresholds["background_clutter"] == 4

    def test_yaml_loads_refine_section(self):
        from image_pipeline.anime_pipeline.config import load_config
        config = load_config()
        assert config.refine_score_threshold > 0
        assert config.refine_denoise_floor > 0
        assert isinstance(config.refine_dimension_thresholds, dict)

    def test_max_refine_rounds_env_override(self):
        from image_pipeline.anime_pipeline.config import load_config
        with patch.dict(os.environ, {"ANIME_PIPELINE_MAX_REFINE_ROUNDS": "5"}):
            config = load_config()
            assert config.max_refine_rounds == 5


# ═══════════════════════════════════════════════════════════════════════
# decide_refine_action tests
# ═══════════════════════════════════════════════════════════════════════

class TestDecideRefineAction:
    """Pure-logic tests for decide_refine_action()."""

    def test_high_scores_no_refine(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        critique = _make_critique(
            anatomy_score=8, face_score=8, eye_consistency_score=8,
            hands_score=8, clothing_score=8, composition_score=8,
            color_score=8, style_score=8, background_score=8,
            accessories_score=8, pose_score=8,
        )
        config = _make_refine_config(refine_score_threshold=7.0)
        decision = decide_refine_action(critique, round_num=1, config=config)
        assert decision.should_refine is False

    def test_max_rounds_stops(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        critique = _make_critique(anatomy_score=2, face_score=2)
        config = _make_refine_config(max_refine_rounds=2)
        decision = decide_refine_action(critique, round_num=2, config=config)
        assert decision.should_refine is False
        assert "max" in decision.reason.lower()

    def test_low_anatomy_triggers_denoise_up(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        from image_pipeline.anime_pipeline.schemas import RefineActionType
        critique = _make_critique(anatomy_score=3)  # below threshold 5
        config = _make_refine_config()
        decision = decide_refine_action(critique, round_num=1, config=config)
        assert decision.should_refine is True
        assert "anatomy" in decision.worst_dimensions
        action_types = [a.action_type for a in decision.actions]
        assert RefineActionType.ADJUST_DENOISE in action_types
        denoise_action = [a for a in decision.actions if a.action_type == RefineActionType.ADJUST_DENOISE][0]
        assert denoise_action.value > 0  # denoise UP

    def test_low_hands_triggers_denoise_up(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        from image_pipeline.anime_pipeline.schemas import RefineActionType
        critique = _make_critique(hands_score=2)  # below threshold 4
        config = _make_refine_config()
        decision = decide_refine_action(critique, round_num=1, config=config)
        assert decision.should_refine is True
        action_types = [a.action_type for a in decision.actions]
        assert RefineActionType.ADJUST_DENOISE in action_types

    def test_low_pose_triggers_control_boost(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        from image_pipeline.anime_pipeline.schemas import RefineActionType
        critique = _make_critique(pose_score=3)  # below threshold 5
        config = _make_refine_config()
        decision = decide_refine_action(critique, round_num=1, config=config)
        assert decision.should_refine is True
        assert "pose_drift" in decision.worst_dimensions
        action_types = [a.action_type for a in decision.actions]
        assert RefineActionType.ADJUST_CONTROL in action_types
        ctrl_action = [a for a in decision.actions if a.action_type == RefineActionType.ADJUST_CONTROL][0]
        assert ctrl_action.value > 0  # control strength UP

    def test_style_drift_triggers_control_reduce(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        from image_pipeline.anime_pipeline.schemas import RefineActionType
        critique = _make_critique(style_score=3)  # below threshold 5
        config = _make_refine_config()
        decision = decide_refine_action(critique, round_num=1, config=config)
        assert decision.should_refine is True
        assert "style_drift" in decision.worst_dimensions
        action_types = [a.action_type for a in decision.actions]
        assert RefineActionType.ADJUST_CONTROL in action_types
        ctrl_action = [a for a in decision.actions if a.action_type == RefineActionType.ADJUST_CONTROL][0]
        assert ctrl_action.value < 0  # control strength DOWN

    def test_artifact_accumulation_switches_preset(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        from image_pipeline.anime_pipeline.schemas import RefineActionType
        # Create a critique with many issues to exceed artifact limit
        critique = _make_critique(
            anatomy_score=3, face_score=3,
            anatomy_issues=["bad arm", "bad leg", "missing finger"],
            face_issues=["asymmetric", "blurry"],
            hand_issues=["extra finger", "merged hand"],
            eye_issues=["different sizes"],
        )
        config = _make_refine_config(refine_artifact_accumulation_limit=8)
        decision = decide_refine_action(critique, round_num=1, config=config)
        assert decision.should_refine is True
        action_types = [a.action_type for a in decision.actions]
        assert RefineActionType.SWITCH_PRESET in action_types
        preset_action = [a for a in decision.actions if a.action_type == RefineActionType.SWITCH_PRESET][0]
        assert preset_action.value == "subtle"

    def test_below_threshold_no_single_dim_failing(self):
        """Overall below threshold but no single dimension critically bad → general boost."""
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        from image_pipeline.anime_pipeline.schemas import RefineActionType
        # All scores at 6 = overall ~6.0 < 7.0 threshold, but each dim > its threshold (5)
        critique = _make_critique(
            anatomy_score=6, face_score=6, eye_consistency_score=6,
            hands_score=6, clothing_score=6, composition_score=6,
            color_score=6, style_score=6, background_score=6,
            accessories_score=6, pose_score=6,
        )
        config = _make_refine_config()
        decision = decide_refine_action(critique, round_num=1, config=config)
        assert decision.should_refine is True
        assert len(decision.actions) == 1
        assert decision.actions[0].action_type == RefineActionType.ADJUST_DENOISE
        assert decision.actions[0].value > 0  # slight bump
        assert decision.worst_dimensions == []

    def test_negative_patch_added_for_failing_dim(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        from image_pipeline.anime_pipeline.schemas import RefineActionType
        critique = _make_critique(anatomy_score=3)
        config = _make_refine_config()
        decision = decide_refine_action(critique, round_num=1, config=config)
        neg_patches = [a for a in decision.actions if a.action_type == RefineActionType.PATCH_NEGATIVE]
        assert len(neg_patches) >= 1
        assert "bad anatomy" in neg_patches[0].value

    def test_positive_patch_from_issues(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        from image_pipeline.anime_pipeline.schemas import RefineActionType
        critique = _make_critique(
            face_score=3,
            face_issues=["eyes too far apart", "nose off center"],
        )
        config = _make_refine_config()
        decision = decide_refine_action(critique, round_num=1, config=config)
        pos_patches = [a for a in decision.actions if a.action_type == RefineActionType.PATCH_POSITIVE]
        assert len(pos_patches) >= 1
        values = [a.value for a in pos_patches]
        assert "eyes too far apart" in values

    def test_round_0_always_allowed(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        critique = _make_critique(anatomy_score=2)
        config = _make_refine_config(max_refine_rounds=2)
        decision = decide_refine_action(critique, round_num=0, config=config)
        assert decision.should_refine is True

    def test_multiple_failing_dims(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        critique = _make_critique(
            anatomy_score=2, hands_score=2, pose_score=2,
        )
        config = _make_refine_config()
        decision = decide_refine_action(critique, round_num=1, config=config)
        assert decision.should_refine is True
        assert len(decision.worst_dimensions) >= 3


# ═══════════════════════════════════════════════════════════════════════
# patch_plan_from_critique tests
# ═══════════════════════════════════════════════════════════════════════

class TestPatchPlanFromCritique:
    """Pure-function tests for patch_plan_from_critique()."""

    def test_denoise_increase_clamped_to_ceiling(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            RefineAction, RefineActionType, RefineDecision,
        )
        pc = _make_beauty_pc(denoise=0.53)
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.ADJUST_DENOISE,
                target="denoise", value=0.05,
            )],
        )
        config = _make_refine_config(refine_denoise_ceiling=0.55)
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert result.denoise <= 0.55

    def test_denoise_decrease_clamped_to_floor(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            RefineAction, RefineActionType, RefineDecision,
        )
        pc = _make_beauty_pc(denoise=0.13)
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.ADJUST_DENOISE,
                target="denoise", value=-0.05,
            )],
        )
        config = _make_refine_config(refine_denoise_floor=0.12)
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert result.denoise >= 0.12

    def test_control_strength_increase(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            ControlInput, RefineAction, RefineActionType, RefineDecision,
        )
        ci = ControlInput(
            layer_type="lineart_anime",
            controlnet_model="model.safetensors",
            strength=0.50,
            image_b64=_FAKE_IMG_B64,
        )
        pc = _make_beauty_pc(control_inputs=[ci])
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.ADJUST_CONTROL,
                target="control_strength", value=0.10,
            )],
        )
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert len(result.control_inputs) == 1
        assert result.control_inputs[0].strength == pytest.approx(0.60)

    def test_control_strength_clamped_max(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            ControlInput, RefineAction, RefineActionType, RefineDecision,
        )
        ci = ControlInput(
            layer_type="depth", controlnet_model="m.safetensors",
            strength=0.95, image_b64=_FAKE_IMG_B64,
        )
        pc = _make_beauty_pc(control_inputs=[ci])
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.ADJUST_CONTROL,
                target="control_strength", value=0.20,
            )],
        )
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert result.control_inputs[0].strength == 1.0

    def test_control_strength_clamped_min(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            ControlInput, RefineAction, RefineActionType, RefineDecision,
        )
        ci = ControlInput(
            layer_type="depth", controlnet_model="m.safetensors",
            strength=0.12, image_b64=_FAKE_IMG_B64,
        )
        pc = _make_beauty_pc(control_inputs=[ci])
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.ADJUST_CONTROL,
                target="control_strength", value=-0.10,
            )],
        )
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert result.control_inputs[0].strength == 0.1

    def test_positive_prompt_no_duplicate(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            RefineAction, RefineActionType, RefineDecision,
        )
        pc = _make_beauty_pc(positive_prompt="1girl, school uniform")
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[
                RefineAction(
                    action_type=RefineActionType.PATCH_POSITIVE,
                    target="positive", value="1girl",  # already present
                ),
                RefineAction(
                    action_type=RefineActionType.PATCH_POSITIVE,
                    target="positive", value="detailed hands",  # new
                ),
            ],
        )
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert result.positive_prompt.count("1girl") == 1
        assert "detailed hands" in result.positive_prompt

    def test_negative_prompt_no_duplicate(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            RefineAction, RefineActionType, RefineDecision,
        )
        pc = _make_beauty_pc(negative_prompt="worst quality, lowres")
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[
                RefineAction(
                    action_type=RefineActionType.PATCH_NEGATIVE,
                    target="negative", value="worst quality",  # already present
                ),
                RefineAction(
                    action_type=RefineActionType.PATCH_NEGATIVE,
                    target="negative", value="bad anatomy",  # new
                ),
            ],
        )
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert result.negative_prompt.count("worst quality") == 1
        assert "bad anatomy" in result.negative_prompt

    def test_switch_preset_applies_values(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            RefineAction, RefineActionType, RefineDecision,
        )
        pc = _make_beauty_pc(denoise=0.40, steps=28, cfg=5.5)
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.SWITCH_PRESET,
                target="beauty_strength", value="subtle",
            )],
        )
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        # Subtle preset: denoise=0.18, cfg=5.0, steps=25
        assert result.denoise == pytest.approx(0.18)
        assert result.steps == 25
        assert result.cfg == pytest.approx(5.0)

    def test_critique_prompt_patch_applied(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import RefineDecision
        pc = _make_beauty_pc(positive_prompt="1girl")
        critique = _make_critique(prompt_patch=["better lighting", "sharp focus"])
        decision = RefineDecision(should_refine=True)
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert "better lighting" in result.positive_prompt
        assert "sharp focus" in result.positive_prompt

    def test_critique_control_patch_applied(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            ControlInput, RefineDecision,
        )
        ci = ControlInput(
            layer_type="lineart_anime",
            controlnet_model="model.safetensors",
            strength=0.50,
            image_b64=_FAKE_IMG_B64,
        )
        pc = _make_beauty_pc(control_inputs=[ci])
        critique = _make_critique(control_patch={"lineart_anime": 0.15})
        decision = RefineDecision(should_refine=True)
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert result.control_inputs[0].strength == pytest.approx(0.65)

    def test_original_pc_not_mutated(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            RefineAction, RefineActionType, RefineDecision,
        )
        pc = _make_beauty_pc(denoise=0.30)
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.ADJUST_DENOISE,
                target="denoise", value=0.05,
            )],
        )
        config = _make_refine_config()
        patch_plan_from_critique(pc, critique, decision, config)
        assert pc.denoise == 0.30  # original unchanged

    def test_empty_actions_returns_copy(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import RefineDecision
        pc = _make_beauty_pc()
        critique = _make_critique()
        decision = RefineDecision(should_refine=True)
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        assert result.denoise == pc.denoise
        assert result.positive_prompt == pc.positive_prompt

    def test_invalid_preset_logged_but_not_crash(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        from image_pipeline.anime_pipeline.schemas import (
            RefineAction, RefineActionType, RefineDecision,
        )
        pc = _make_beauty_pc(denoise=0.30)
        critique = _make_critique()
        decision = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.SWITCH_PRESET,
                target="beauty_strength", value="nonexistent_preset",
            )],
        )
        config = _make_refine_config()
        result = patch_plan_from_critique(pc, critique, decision, config)
        # Should not crash, denoise stays the same
        assert result.denoise == 0.30


# ═══════════════════════════════════════════════════════════════════════
# critique_image function tests
# ═══════════════════════════════════════════════════════════════════════

class TestCritiqueImageFunction:
    """Test critique_image() wrapper function."""

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.CritiqueAgent")
    def test_delegates_to_critique_agent(self, MockCritiqueAgent):
        from image_pipeline.anime_pipeline.agents.refine_loop import critique_image

        expected_critique = _make_critique(anatomy_score=8)

        def mock_execute(job):
            job.critique_results.append(expected_critique)
            return job

        mock_instance = MagicMock()
        mock_instance.execute.side_effect = mock_execute
        MockCritiqueAgent.return_value = mock_instance

        job = _make_refine_job()
        config = _make_refine_config()
        result = critique_image(job, config)
        assert result.anatomy_score == 8
        mock_instance.execute.assert_called_once_with(job)

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.CritiqueAgent")
    def test_fallback_when_no_results(self, MockCritiqueAgent):
        from image_pipeline.anime_pipeline.agents.refine_loop import critique_image

        # Critique agent returns but doesn't append results
        mock_instance = MagicMock()
        mock_instance.execute.return_value = None
        MockCritiqueAgent.return_value = mock_instance

        job = _make_refine_job()
        config = _make_refine_config()
        result = critique_image(job, config)
        # Should return fallback with neutral scores
        assert result.model_used == "fallback"
        assert result.anatomy_score == 5
        assert result.face_score == 5


# ═══════════════════════════════════════════════════════════════════════
# run_refine_round tests
# ═══════════════════════════════════════════════════════════════════════

class TestRunRefineRound:
    """Integration-level tests for run_refine_round()."""

    def test_no_refine_returns_early(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import run_refine_round

        critique = _make_critique(
            anatomy_score=8, face_score=8, eye_consistency_score=8,
            hands_score=8, clothing_score=8, composition_score=8,
            color_score=8, style_score=8, background_score=8,
            accessories_score=8, pose_score=8,
        )  # passes threshold
        config = _make_refine_config()
        job = _make_refine_job()
        pc = _make_beauty_pc()

        beauty_agent = MagicMock()
        critique_agent = MagicMock()

        result_job, result_crit, result_pc = run_refine_round(
            job, config, round_num=1,
            beauty_agent=beauty_agent,
            critique_agent=critique_agent,
            last_critique=critique,
            beauty_pc=pc,
        )
        # Should not have called beauty agent
        beauty_agent._builder.build_beauty.assert_not_called()
        assert result_crit is critique  # same object returned

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.random")
    def test_success_round(self, mock_random):
        from image_pipeline.anime_pipeline.agents.refine_loop import run_refine_round
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult

        mock_random.randint.return_value = 12345

        # Low critique to trigger refine
        critique = _make_critique(anatomy_score=3, face_score=3)
        config = _make_refine_config()
        job = _make_refine_job()
        pc = _make_beauty_pc()

        # Mock beauty agent
        beauty_agent = MagicMock()
        beauty_result = ComfyJobResult(
            success=True, images_b64=[_FAKE_IMG_B64], duration_ms=1500.0,
        )
        beauty_agent._builder.build_beauty.return_value = {"test": "workflow"}
        beauty_agent._client.submit_workflow.return_value = beauty_result

        # Mock critique agent
        new_critique = _make_critique(anatomy_score=7, face_score=7)

        def mock_critique_execute(j):
            j.critique_results.append(new_critique)
            return j

        critique_agent = MagicMock()
        critique_agent.execute.side_effect = mock_critique_execute

        result_job, result_crit, result_pc = run_refine_round(
            job, config, round_num=1,
            beauty_agent=beauty_agent,
            critique_agent=critique_agent,
            last_critique=critique,
            beauty_pc=pc,
        )
        assert result_job.error is None
        assert result_crit.anatomy_score == 7
        assert result_job.refine_rounds == 1
        # Should have added intermediate
        refine_imgs = [i for i in result_job.intermediates if i.stage == "refine_round_1"]
        assert len(refine_imgs) == 1

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.random")
    def test_beauty_failure_sets_failed(self, mock_random):
        from image_pipeline.anime_pipeline.agents.refine_loop import run_refine_round
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        mock_random.randint.return_value = 99999
        critique = _make_critique(anatomy_score=2)
        config = _make_refine_config()
        job = _make_refine_job()
        pc = _make_beauty_pc()

        beauty_agent = MagicMock()
        beauty_agent._builder.build_beauty.return_value = {}
        beauty_agent._client.submit_workflow.return_value = ComfyJobResult(
            success=False, error="GPU OOM",
        )

        critique_agent = MagicMock()
        result_job, _, _ = run_refine_round(
            job, config, round_num=1,
            beauty_agent=beauty_agent,
            critique_agent=critique_agent,
            last_critique=critique,
            beauty_pc=pc,
        )
        assert result_job.status == AnimePipelineStatus.FAILED
        assert "GPU OOM" in result_job.error

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.random")
    def test_empty_images_sets_failed(self, mock_random):
        from image_pipeline.anime_pipeline.agents.refine_loop import run_refine_round
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        mock_random.randint.return_value = 11111
        critique = _make_critique(anatomy_score=2)
        config = _make_refine_config()
        job = _make_refine_job()
        pc = _make_beauty_pc()

        beauty_agent = MagicMock()
        beauty_agent._builder.build_beauty.return_value = {}
        beauty_agent._client.submit_workflow.return_value = ComfyJobResult(
            success=True, images_b64=[], duration_ms=500.0,
        )

        critique_agent = MagicMock()
        result_job, _, _ = run_refine_round(
            job, config, round_num=1,
            beauty_agent=beauty_agent,
            critique_agent=critique_agent,
            last_critique=critique,
            beauty_pc=pc,
        )
        assert result_job.status == AnimePipelineStatus.FAILED
        assert "no image" in result_job.error.lower()

    def test_no_source_image_fails(self):
        from image_pipeline.anime_pipeline.agents.refine_loop import run_refine_round
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        critique = _make_critique(anatomy_score=2)
        config = _make_refine_config()
        job = _make_refine_job(with_beauty=False)  # no beauty image
        pc = _make_beauty_pc()

        beauty_agent = MagicMock()
        critique_agent = MagicMock()

        result_job, _, _ = run_refine_round(
            job, config, round_num=1,
            beauty_agent=beauty_agent,
            critique_agent=critique_agent,
            last_critique=critique,
            beauty_pc=pc,
        )
        assert result_job.status == AnimePipelineStatus.FAILED
        assert "source image" in result_job.error.lower()


# ═══════════════════════════════════════════════════════════════════════
# RefineLoopAgent tests
# ═══════════════════════════════════════════════════════════════════════

class TestRefineLoopAgent:
    """Integration tests for RefineLoopAgent.execute()."""

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.CritiqueAgent")
    @patch("image_pipeline.anime_pipeline.agents.refine_loop.BeautyPassAgent")
    def test_passes_on_first_critique(self, MockBeauty, MockCritique):
        from image_pipeline.anime_pipeline.agents.refine_loop import RefineLoopAgent

        good_critique = _make_critique(
            anatomy_score=8, face_score=8, eye_consistency_score=8,
            hands_score=8, clothing_score=8, composition_score=8,
            color_score=8, style_score=8, background_score=8,
            accessories_score=8, pose_score=8,
        )  # all 8s → passes

        def mock_critique(job):
            job.critique_results.append(good_critique)
            return job

        MockCritique.return_value.execute.side_effect = mock_critique
        MockBeauty.return_value  # not called

        config = _make_refine_config()
        agent = RefineLoopAgent(config)
        job = _make_refine_job()

        result = agent.execute(job)
        assert result.error is None
        # Beauty agent should NOT have been called for refinement
        # (only CritiqueAgent.execute should be called once for initial critique)
        assert MockCritique.return_value.execute.call_count == 1

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.CritiqueAgent")
    @patch("image_pipeline.anime_pipeline.agents.refine_loop.BeautyPassAgent")
    def test_no_layer_plan_fails(self, MockBeauty, MockCritique):
        from image_pipeline.anime_pipeline.agents.refine_loop import RefineLoopAgent
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus

        config = _make_refine_config()
        agent = RefineLoopAgent(config)
        job = _make_refine_job(with_plan=False)

        result = agent.execute(job)
        assert result.status == AnimePipelineStatus.FAILED
        assert "No layer plan" in result.error

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.random")
    @patch("image_pipeline.anime_pipeline.agents.refine_loop.CritiqueAgent")
    @patch("image_pipeline.anime_pipeline.agents.refine_loop.BeautyPassAgent")
    def test_refines_then_passes(self, MockBeauty, MockCritique, mock_random):
        from image_pipeline.anime_pipeline.agents.refine_loop import RefineLoopAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult

        mock_random.randint.return_value = 42424

        critique_calls = [0]
        bad_critique = _make_critique(anatomy_score=3, face_score=3)
        good_critique = _make_critique(
            anatomy_score=8, face_score=8, eye_consistency_score=8,
            hands_score=8, clothing_score=8, composition_score=8,
            color_score=8, style_score=8, background_score=8,
            accessories_score=8, pose_score=8,
        )

        def mock_critique(job):
            critique_calls[0] += 1
            if critique_calls[0] == 1:
                job.critique_results.append(bad_critique)
            else:
                job.critique_results.append(good_critique)
            return job

        MockCritique.return_value.execute.side_effect = mock_critique

        # Beauty agent for refinement
        beauty_result = ComfyJobResult(
            success=True, images_b64=[_FAKE_IMG_B64], duration_ms=1000.0,
        )
        MockBeauty.return_value._builder.build_beauty.return_value = {"wf": True}
        MockBeauty.return_value._client.submit_workflow.return_value = beauty_result

        config = _make_refine_config()
        agent = RefineLoopAgent(config)
        job = _make_refine_job()

        result = agent.execute(job)
        assert result.error is None
        # Should have done initial critique + 1 refine round critique
        assert MockCritique.return_value.execute.call_count == 2
        assert result.refine_rounds == 1

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.random")
    @patch("image_pipeline.anime_pipeline.agents.refine_loop.CritiqueAgent")
    @patch("image_pipeline.anime_pipeline.agents.refine_loop.BeautyPassAgent")
    def test_max_rounds_exhausted(self, MockBeauty, MockCritique, mock_random):
        from image_pipeline.anime_pipeline.agents.refine_loop import RefineLoopAgent
        from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult

        mock_random.randint.return_value = 55555

        # Always return bad critique
        bad_critique = _make_critique(anatomy_score=2, face_score=2)

        def mock_critique(job):
            job.critique_results.append(bad_critique)
            return job

        MockCritique.return_value.execute.side_effect = mock_critique

        beauty_result = ComfyJobResult(
            success=True, images_b64=[_FAKE_IMG_B64], duration_ms=800.0,
        )
        MockBeauty.return_value._builder.build_beauty.return_value = {}
        MockBeauty.return_value._client.submit_workflow.return_value = beauty_result

        config = _make_refine_config(max_refine_rounds=2)
        agent = RefineLoopAgent(config)
        job = _make_refine_job()

        result = agent.execute(job)
        # Should have attempted max_refine_rounds (2) then stopped at round 3 check
        # Initial critique + up to 2 refine round critiques
        assert MockCritique.return_value.execute.call_count >= 2

    @patch("image_pipeline.anime_pipeline.agents.refine_loop.CritiqueAgent")
    @patch("image_pipeline.anime_pipeline.agents.refine_loop.BeautyPassAgent")
    def test_return_best_on_fail(self, MockBeauty, MockCritique):
        from image_pipeline.anime_pipeline.agents.refine_loop import RefineLoopAgent

        good_critique = _make_critique(
            anatomy_score=8, face_score=8, eye_consistency_score=8,
            hands_score=8, clothing_score=8, composition_score=8,
            color_score=8, style_score=8, background_score=8,
            accessories_score=8, pose_score=8,
        )

        def mock_critique(job):
            job.critique_results.append(good_critique)
            return job

        MockCritique.return_value.execute.side_effect = mock_critique

        config = _make_refine_config(return_best_on_fail=True)
        agent = RefineLoopAgent(config)
        job = _make_refine_job()

        result = agent.execute(job)
        # With return_best_on_fail and a beauty_pass image, final should be set
        assert result.final_image_b64 == _FAKE_IMG_B64


# ═══════════════════════════════════════════════════════════════════════
# RefineLoopAgent export tests
# ═══════════════════════════════════════════════════════════════════════

class TestRefineLoopExport:
    """Test that RefineLoopAgent and functions are properly exported."""

    def test_import_refine_loop_agent(self):
        from image_pipeline.anime_pipeline.agents import RefineLoopAgent
        assert RefineLoopAgent is not None

    def test_import_critique_image(self):
        from image_pipeline.anime_pipeline.agents import critique_image
        assert callable(critique_image)

    def test_import_decide_refine_action(self):
        from image_pipeline.anime_pipeline.agents import decide_refine_action
        assert callable(decide_refine_action)

    def test_import_patch_plan_from_critique(self):
        from image_pipeline.anime_pipeline.agents import patch_plan_from_critique
        assert callable(patch_plan_from_critique)

    def test_import_run_refine_round(self):
        from image_pipeline.anime_pipeline.agents import run_refine_round
        assert callable(run_refine_round)

    def test_all_in_agents_all(self):
        from image_pipeline.anime_pipeline import agents
        expected = [
            "RefineLoopAgent", "critique_image",
            "decide_refine_action", "patch_plan_from_critique",
            "run_refine_round",
        ]
        for name in expected:
            assert name in agents.__all__, f"{name} not in agents.__all__"


# ═══════════════════════════════════════════════════════════════════════
# Phase 3B-7: Upscale Service, Final Ranker, Output Manifest
# ═══════════════════════════════════════════════════════════════════════

# ── Helpers ───────────────────────────────────────────────────────────

def _make_upscale_config(**overrides):
    """Config for upscale / ranker / manifest tests."""
    from image_pipeline.anime_pipeline.config import (
        AnimePipelineConfig, ModelConfig, BeautyStrength,
    )
    defaults = dict(
        comfyui_url="http://localhost:8188",
        composition_model=ModelConfig(
            checkpoint="animagine-xl-4.0-opt.safetensors", clip_skip=2,
        ),
        beauty_model=ModelConfig(
            checkpoint="flatpiececorexl_a1818.safetensors", denoise_strength=0.45,
        ),
        final_model=ModelConfig(
            checkpoint="noobaiXLNAIXL_vPred10Version.safetensors",
            sampler="euler_a", scheduler="normal", steps=28, cfg=5.5,
            clip_skip=2, denoise_strength=0.30,
        ),
        upscale_model="RealESRGAN_x4plus_anime_6B",
        upscale_factor=2,
        upscale_tile_size=512,
        upscale_denoise=0.2,
        beauty_strength=BeautyStrength.BALANCED,
        quality_prefix="masterpiece, best quality",
        negative_base="lowres, worst quality",
    )
    defaults.update(overrides)
    return AnimePipelineConfig(**defaults)


def _make_upscale_job(with_beauty=True, with_upscale_pass=True):
    """Job with beauty_pass intermediate and optional upscale pass in plan."""
    from image_pipeline.anime_pipeline.schemas import (
        AnimePipelineJob, LayerPlan, IntermediateImage, PassConfig,
    )
    job = AnimePipelineJob(job_id="test-upscale-001")
    if with_beauty:
        job.intermediates.append(IntermediateImage(
            stage="beauty_pass", image_b64=_FAKE_IMG_B64,
        ))
    passes = [_make_beauty_pc()]
    if with_upscale_pass:
        passes.append(PassConfig(pass_name="upscale"))
    job.layer_plan = LayerPlan(
        scene_summary="test scene",
        passes=passes,
    )
    return job


def _make_comfy_result(success=True, images=None):
    """Build a mock ComfyJobResult."""
    from image_pipeline.anime_pipeline.comfy_client import ComfyJobResult
    return ComfyJobResult(
        prompt_id="test-prompt-id",
        success=success,
        images_b64=images or ([_FAKE_IMG_B64] if success else []),
    )


# ═══════════════════════════════════════════════════════════════════════
# RankCandidate / RankResult schema tests
# ═══════════════════════════════════════════════════════════════════════

class TestRankCandidate:
    """RankCandidate dataclass contract."""

    def test_defaults(self):
        from image_pipeline.anime_pipeline.schemas import RankCandidate
        c = RankCandidate()
        assert c.image_b64 == ""
        assert c.stage == ""
        assert c.critique is None
        assert c.face_quality == 0.0
        assert c.clarity == 0.0
        assert c.style_consistency == 0.0
        assert c.artifact_count == 0
        assert c.composite_score == 0.0

    def test_to_dict_keys(self):
        from image_pipeline.anime_pipeline.schemas import RankCandidate
        c = RankCandidate(
            image_b64="abc", stage="beauty_pass",
            face_quality=8.0, clarity=7.5, style_consistency=9.0,
            artifact_count=2, composite_score=7.8,
        )
        d = c.to_dict()
        assert d["stage"] == "beauty_pass"
        assert d["face_quality"] == 8.0
        assert d["clarity"] == 7.5
        assert d["style_consistency"] == 9.0
        assert d["artifact_count"] == 2
        assert d["composite_score"] == 7.8
        assert d["has_image"] is True

    def test_to_dict_no_image(self):
        from image_pipeline.anime_pipeline.schemas import RankCandidate
        c = RankCandidate(image_b64="", stage="test")
        assert c.to_dict()["has_image"] is False

    def test_to_dict_rounds_floats(self):
        from image_pipeline.anime_pipeline.schemas import RankCandidate
        c = RankCandidate(face_quality=7.123456, clarity=8.999999)
        d = c.to_dict()
        assert d["face_quality"] == 7.12
        assert d["clarity"] == 9.0


class TestRankResult:
    """RankResult dataclass contract."""

    def test_defaults(self):
        from image_pipeline.anime_pipeline.schemas import RankResult
        r = RankResult()
        assert r.winner is None
        assert r.runner_ups == []
        assert r.total_candidates == 0

    def test_to_dict_with_winner(self):
        from image_pipeline.anime_pipeline.schemas import RankCandidate, RankResult
        winner = RankCandidate(stage="upscale", composite_score=9.0, image_b64="x")
        runner = RankCandidate(stage="beauty_pass", composite_score=7.0, image_b64="y")
        r = RankResult(winner=winner, runner_ups=[runner], total_candidates=2)
        d = r.to_dict()
        assert d["winner"]["stage"] == "upscale"
        assert len(d["runner_ups"]) == 1
        assert d["total_candidates"] == 2

    def test_to_dict_no_winner(self):
        from image_pipeline.anime_pipeline.schemas import RankResult
        r = RankResult(total_candidates=0)
        d = r.to_dict()
        assert d["winner"] is None
        assert d["runner_ups"] == []


# ═══════════════════════════════════════════════════════════════════════
# WorkflowBuilder — new upscale methods
# ═══════════════════════════════════════════════════════════════════════

class TestWorkflowBuilderSimpleUpscale:
    """Tests for build_simple_upscale — model upscale + rescale."""

    def test_node_count(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_simple_upscale("IMG", "RealESRGAN_x4plus_anime_6B", 1248, 1824)
        assert len(w) == 5  # load, loader, upscale, rescale, save

    def test_has_image_scale_node(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_simple_upscale("IMG", "model.pth", 1664, 2432)
        scale_nodes = [n for n in w.values() if n["class_type"] == "ImageScale"]
        assert len(scale_nodes) == 1

    def test_target_dimensions(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_simple_upscale("IMG", "model.pth", 1664, 2432)
        scale_node = [n for n in w.values() if n["class_type"] == "ImageScale"][0]
        assert scale_node["inputs"]["width"] == 1664
        assert scale_node["inputs"]["height"] == 2432
        assert scale_node["inputs"]["upscale_method"] == "lanczos"

    def test_has_upscale_model_loader(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_simple_upscale("IMG", "MyModel.pth", 100, 100)
        loader_nodes = [n for n in w.values() if n["class_type"] == "UpscaleModelLoader"]
        assert len(loader_nodes) == 1
        assert loader_nodes[0]["inputs"]["model_name"] == "MyModel.pth"

    def test_save_node_filename_prefix(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_simple_upscale("IMG", "m.pth", 100, 100, pass_name="my_upscale")
        save_nodes = [n for n in w.values() if n["class_type"] == "SaveImage"]
        assert len(save_nodes) == 1
        assert "my_upscale" in save_nodes[0]["inputs"]["filename_prefix"]

    def test_node_ids_are_sequential_strings(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_simple_upscale("IMG", "m.pth", 100, 100)
        ids = sorted(w.keys(), key=int)
        assert ids == ["1", "2", "3", "4", "5"]


class TestWorkflowBuilderUltimateSDUpscale:
    """Tests for build_ultimate_sd_upscale."""

    def test_node_count(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_ultimate_sd_upscale(
            "IMG", "model.pth", 2.0, "ckpt.safetensors",
            "positive", "negative", 42,
        )
        # load, ckpt, clip_pos, clip_neg, up_loader, ultimate, save = 7
        assert len(w) == 7

    def test_has_ultimate_node(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_ultimate_sd_upscale(
            "IMG", "model.pth", 1.5, "ckpt.safetensors",
            "pos", "neg", 42,
        )
        ultimate_nodes = [n for n in w.values() if n["class_type"] == "UltimateSDUpscale"]
        assert len(ultimate_nodes) == 1

    def test_upscale_by_factor(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_ultimate_sd_upscale(
            "IMG", "model.pth", 1.5, "ckpt.safetensors",
            "pos", "neg", 42,
        )
        ultimate = [n for n in w.values() if n["class_type"] == "UltimateSDUpscale"][0]
        assert ultimate["inputs"]["upscale_by"] == 1.5

    def test_tile_dimensions(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_ultimate_sd_upscale(
            "IMG", "model.pth", 2.0, "ckpt.safetensors",
            "pos", "neg", 42, tile_width=768, tile_height=768,
        )
        ultimate = [n for n in w.values() if n["class_type"] == "UltimateSDUpscale"][0]
        assert ultimate["inputs"]["tile_width"] == 768
        assert ultimate["inputs"]["tile_height"] == 768

    def test_denoise_and_cfg(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_ultimate_sd_upscale(
            "IMG", "model.pth", 2.0, "ckpt.safetensors",
            "pos", "neg", 42, denoise=0.15, cfg=6.0,
        )
        ultimate = [n for n in w.values() if n["class_type"] == "UltimateSDUpscale"][0]
        assert ultimate["inputs"]["denoise"] == 0.15
        assert ultimate["inputs"]["cfg"] == 6.0

    def test_checkpoint_and_prompts_wired(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_ultimate_sd_upscale(
            "IMG", "upmodel.pth", 2.0, "my_checkpoint.safetensors",
            "masterpiece", "worst quality", 99,
        )
        ckpt_nodes = [n for n in w.values() if n["class_type"] == "CheckpointLoaderSimple"]
        assert len(ckpt_nodes) == 1
        assert ckpt_nodes[0]["inputs"]["ckpt_name"] == "my_checkpoint.safetensors"
        clip_nodes = [n for n in w.values() if n["class_type"] == "CLIPTextEncode"]
        texts = [n["inputs"]["text"] for n in clip_nodes]
        assert "masterpiece" in texts
        assert "worst quality" in texts

    def test_seed_passed_through(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_ultimate_sd_upscale(
            "IMG", "model.pth", 2.0, "ckpt.safetensors",
            "pos", "neg", 12345,
        )
        ultimate = [n for n in w.values() if n["class_type"] == "UltimateSDUpscale"][0]
        assert ultimate["inputs"]["seed"] == 12345

    def test_save_node_present(self):
        from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
        wb = WorkflowBuilder()
        w = wb.build_ultimate_sd_upscale(
            "IMG", "model.pth", 2.0, "ckpt.safetensors",
            "pos", "neg", 42, pass_name="upscale_final",
        )
        save_nodes = [n for n in w.values() if n["class_type"] == "SaveImage"]
        assert len(save_nodes) == 1
        assert "upscale_final" in save_nodes[0]["inputs"]["filename_prefix"]


# ═══════════════════════════════════════════════════════════════════════
# score_candidate / rank_candidates function tests
# ═══════════════════════════════════════════════════════════════════════

class TestScoreCandidate:
    """Tests for score_candidate() function."""

    def test_with_critique_all_8s(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        crit = _make_critique(
            anatomy_score=8, face_score=8, eye_consistency_score=8,
            hands_score=8, composition_score=8, style_score=8,
        )
        c = score_candidate(_FAKE_IMG_B64, "beauty_pass", crit)
        assert c.face_quality == pytest.approx(8.0, abs=0.01)
        assert c.clarity == pytest.approx(8.0, abs=0.01)
        assert c.style_consistency == 8.0
        assert c.artifact_count == 0
        assert c.composite_score == pytest.approx(8.0, abs=0.01)

    def test_with_critique_all_7s(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        crit = _make_critique()  # all 7s
        c = score_candidate(_FAKE_IMG_B64, "beauty_pass", crit)
        assert c.face_quality == pytest.approx(7.0, abs=0.01)
        assert c.clarity == pytest.approx(7.0, abs=0.01)
        assert c.style_consistency == 7.0
        assert c.composite_score == pytest.approx(7.0, abs=0.01)

    def test_with_artifacts_penalises_score(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        crit = _make_critique(
            anatomy_issues=["bad arm", "bad leg", "extra finger"],
            face_issues=["asymmetric eyes", "blurry face"],
        )
        c = score_candidate(_FAKE_IMG_B64, "beauty_pass", crit)
        assert c.artifact_count == 5
        # 5 * 0.3 = 1.5 penalty
        expected = 7.0 - 1.5
        assert c.composite_score == pytest.approx(expected, abs=0.01)

    def test_artifact_penalty_capped(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        # 20 issues → penalty capped at 3.0
        crit = _make_critique(
            anatomy_issues=["issue"] * 10,
            face_issues=["issue"] * 10,
        )
        c = score_candidate(_FAKE_IMG_B64, "beauty_pass", crit)
        assert c.artifact_count == 20
        expected = 7.0 - 3.0
        assert c.composite_score == pytest.approx(expected, abs=0.01)

    def test_without_critique_uses_defaults(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        c = score_candidate(_FAKE_IMG_B64, "beauty_pass", None)
        assert c.face_quality == 5.0
        assert c.clarity == 5.0
        assert c.style_consistency == 5.0
        assert c.artifact_count == 0
        assert c.composite_score == pytest.approx(5.0, abs=0.01)

    def test_stage_stored(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        c = score_candidate("img", "upscale", None)
        assert c.stage == "upscale"

    def test_image_stored(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        c = score_candidate("myimg", "beauty_pass", None)
        assert c.image_b64 == "myimg"

    def test_critique_reference_stored(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        crit = _make_critique()
        c = score_candidate("img", "beauty_pass", crit)
        assert c.critique is crit

    def test_mixed_scores(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        crit = _make_critique(
            face_score=10, eye_consistency_score=10,   # face_quality = (10*1.5+10*1.2)/2.7 = 10.0
            anatomy_score=4, composition_score=6, hands_score=5,  # clarity = 5.0
            style_score=3,  # style = 3.0
        )
        c = score_candidate("img", "beauty_pass", crit)
        assert c.face_quality == pytest.approx(10.0, abs=0.01)
        assert c.clarity == pytest.approx(5.0, abs=0.01)
        assert c.style_consistency == 3.0
        # composite = (10*1.5 + 5*1.2 + 3*1.0) / 3.7 = (15+6+3)/3.7 = 24/3.7 ≈ 6.486
        assert c.composite_score == pytest.approx(24.0 / 3.7, abs=0.01)

    def test_zero_scores_zero_composite(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        crit = _make_critique(
            anatomy_score=0, face_score=0, eye_consistency_score=0,
            hands_score=0, composition_score=0, style_score=0,
            color_score=0, background_score=0, accessories_score=0,
            pose_score=0, clothing_score=0,
        )
        c = score_candidate("img", "beauty_pass", crit)
        assert c.composite_score == pytest.approx(0.0, abs=0.01)


class TestRankCandidatesFunction:
    """Tests for rank_candidates()."""

    def test_empty_list(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import rank_candidates
        r = rank_candidates([])
        assert r.winner is None
        assert r.runner_ups == []
        assert r.total_candidates == 0

    def test_single_candidate(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import (
            score_candidate, rank_candidates,
        )
        c = score_candidate(_FAKE_IMG_B64, "beauty_pass", None)
        r = rank_candidates([c])
        assert r.winner is c
        assert r.runner_ups == []
        assert r.total_candidates == 1

    def test_two_candidates_winner_first(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import (
            score_candidate, rank_candidates,
        )
        from image_pipeline.anime_pipeline.schemas import RankCandidate
        high = RankCandidate(image_b64="a", stage="upscale", composite_score=9.0)
        low = RankCandidate(image_b64="b", stage="beauty_pass", composite_score=6.0)
        r = rank_candidates([low, high])
        assert r.winner.composite_score == 9.0
        assert r.winner.stage == "upscale"
        assert len(r.runner_ups) == 1
        assert r.runner_ups[0].composite_score == 6.0

    def test_three_candidates_sorted(self):
        from image_pipeline.anime_pipeline.schemas import RankCandidate
        from image_pipeline.anime_pipeline.agents.final_ranker import rank_candidates
        a = RankCandidate(stage="a", composite_score=5.0)
        b = RankCandidate(stage="b", composite_score=9.0)
        c = RankCandidate(stage="c", composite_score=7.0)
        r = rank_candidates([a, b, c])
        assert r.winner.stage == "b"
        assert [ru.stage for ru in r.runner_ups] == ["c", "a"]
        assert r.total_candidates == 3

    def test_result_to_dict(self):
        from image_pipeline.anime_pipeline.schemas import RankCandidate, RankResult
        from image_pipeline.anime_pipeline.agents.final_ranker import rank_candidates
        cands = [
            RankCandidate(stage="x", composite_score=8.0, image_b64="i"),
            RankCandidate(stage="y", composite_score=6.0, image_b64="j"),
        ]
        r = rank_candidates(cands)
        d = r.to_dict()
        assert d["winner"]["stage"] == "x"
        assert d["total_candidates"] == 2


# ═══════════════════════════════════════════════════════════════════════
# FinalRanker.execute() — integration with job
# ═══════════════════════════════════════════════════════════════════════

class TestFinalRanker:
    """FinalRanker.execute() over AnimePipelineJob."""

    def test_no_intermediates_returns_empty(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import FinalRanker
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        ranker = FinalRanker()
        job = AnimePipelineJob(job_id="test")
        result = ranker.execute(job)
        assert result.winner is None
        assert result.total_candidates == 0

    def test_single_beauty_pass(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import FinalRanker
        job = _make_upscale_job(with_beauty=True, with_upscale_pass=False)
        ranker = FinalRanker()
        result = ranker.execute(job)
        assert result.winner is not None
        assert result.winner.stage == "beauty_pass"
        assert result.total_candidates == 1

    def test_beauty_plus_upscale(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import FinalRanker
        from image_pipeline.anime_pipeline.schemas import IntermediateImage
        job = _make_upscale_job(with_beauty=True)
        job.intermediates.append(IntermediateImage(
            stage="upscale", image_b64=_FAKE_IMG_B64,
        ))
        ranker = FinalRanker()
        result = ranker.execute(job)
        assert result.total_candidates == 2
        # Both have same default scores, so either could win
        assert result.winner is not None

    def test_critique_boosts_beauty_score(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import FinalRanker
        from image_pipeline.anime_pipeline.schemas import IntermediateImage
        job = _make_upscale_job(with_beauty=True)
        # Add good critique
        crit = _make_critique(
            face_score=9, eye_consistency_score=9,
            anatomy_score=9, composition_score=9, hands_score=9,
            style_score=9,
        )
        job.critique_results.append(crit)
        ranker = FinalRanker()
        result = ranker.execute(job)
        assert result.winner.composite_score > 5.0

    def test_non_rankable_stages_excluded(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import FinalRanker
        from image_pipeline.anime_pipeline.schemas import (
            AnimePipelineJob, IntermediateImage,
        )
        job = AnimePipelineJob(job_id="test")
        # pre_upscale and structure_lock are not rankable
        job.intermediates.append(IntermediateImage(
            stage="pre_upscale", image_b64=_FAKE_IMG_B64,
        ))
        job.intermediates.append(IntermediateImage(
            stage="structure_lock", image_b64=_FAKE_IMG_B64,
        ))
        ranker = FinalRanker()
        result = ranker.execute(job)
        assert result.total_candidates == 0

    def test_empty_image_excluded(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import FinalRanker
        from image_pipeline.anime_pipeline.schemas import (
            AnimePipelineJob, IntermediateImage,
        )
        job = AnimePipelineJob(job_id="test")
        job.intermediates.append(IntermediateImage(
            stage="beauty_pass", image_b64="",
        ))
        ranker = FinalRanker()
        result = ranker.execute(job)
        assert result.total_candidates == 0

    def test_runner_ups_populated(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import FinalRanker
        from image_pipeline.anime_pipeline.schemas import IntermediateImage
        job = _make_upscale_job(with_beauty=True)
        job.intermediates.append(IntermediateImage(
            stage="upscale", image_b64=_FAKE_IMG_B64,
        ))
        job.intermediates.append(IntermediateImage(
            stage="composition_pass", image_b64=_FAKE_IMG_B64,
        ))
        ranker = FinalRanker()
        result = ranker.execute(job)
        assert result.total_candidates == 3
        assert len(result.runner_ups) == 2


# ═══════════════════════════════════════════════════════════════════════
# UpscaleService tests (ComfyClient mocked)
# ═══════════════════════════════════════════════════════════════════════

class TestUpscaleService:
    """UpscaleService.execute() with mocked ComfyClient."""

    def test_skip_when_no_upscale_in_plan(self):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        job = _make_upscale_job(with_beauty=True, with_upscale_pass=False)
        result = svc.execute(job)
        assert "upscale" in result.stages_executed
        assert result.stage_timings_ms["upscale"] == 0.0
        # Final image should be set from beauty pass
        assert result.final_image_b64 == _FAKE_IMG_B64

    def test_skip_when_no_source_image(self):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        job = _make_upscale_job(with_beauty=False, with_upscale_pass=True)
        result = svc.execute(job)
        assert "upscale" in result.stages_executed

    @patch("image_pipeline.anime_pipeline.agents.upscale_service.ComfyClient")
    def test_ultimate_sd_success(self, MockClient):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        mock_instance = MockClient.return_value
        mock_instance.submit_workflow.return_value = _make_comfy_result(
            success=True, images=[_FAKE_IMG_B64],
        )
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        svc._client = mock_instance
        job = _make_upscale_job()
        result = svc.execute(job)
        assert result.final_image_b64 == _FAKE_IMG_B64
        assert any(i.stage == "pre_upscale" for i in result.intermediates)
        assert any(i.stage == "upscale" for i in result.intermediates)
        # Should have called submit_workflow at least once
        assert mock_instance.submit_workflow.call_count >= 1

    @patch("image_pipeline.anime_pipeline.agents.upscale_service.ComfyClient")
    def test_fallback_to_simple_on_ultimate_failure(self, MockClient):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        mock_instance = MockClient.return_value
        # First call (ultimate) fails, second (simple) succeeds
        mock_instance.submit_workflow.side_effect = [
            _make_comfy_result(success=False, images=[]),
            _make_comfy_result(success=True, images=[_FAKE_IMG_B64]),
        ]
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        svc._client = mock_instance
        job = _make_upscale_job()
        result = svc.execute(job)
        assert result.final_image_b64 == _FAKE_IMG_B64
        assert mock_instance.submit_workflow.call_count == 2

    @patch("image_pipeline.anime_pipeline.agents.upscale_service.ComfyClient")
    def test_both_fail_uses_pre_upscale(self, MockClient):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        mock_instance = MockClient.return_value
        mock_instance.submit_workflow.side_effect = [
            _make_comfy_result(success=False, images=[]),
            _make_comfy_result(success=False, images=[]),
        ]
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        svc._client = mock_instance
        job = _make_upscale_job()
        result = svc.execute(job)
        # Should still have a final image (from beauty pass)
        assert result.final_image_b64 == _FAKE_IMG_B64

    @patch("image_pipeline.anime_pipeline.agents.upscale_service.ComfyClient")
    def test_ultimate_exception_triggers_fallback(self, MockClient):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        mock_instance = MockClient.return_value
        mock_instance.submit_workflow.side_effect = [
            RuntimeError("UltimateSDUpscale not found"),
            _make_comfy_result(success=True, images=[_FAKE_IMG_B64]),
        ]
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        svc._client = mock_instance
        job = _make_upscale_job()
        result = svc.execute(job)
        assert result.final_image_b64 == _FAKE_IMG_B64

    def test_factor_clamped_to_supported(self):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        cfg = _make_upscale_config(upscale_factor=3)
        svc = UpscaleService(cfg)
        factor = svc._resolve_factor()
        assert factor == 2.0  # snapped to nearest supported

    def test_factor_1_5_supported(self):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        cfg = _make_upscale_config(upscale_factor=1.5)
        svc = UpscaleService(cfg)
        factor = svc._resolve_factor()
        assert factor == 1.5

    def test_factor_2_supported(self):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        cfg = _make_upscale_config(upscale_factor=2)
        svc = UpscaleService(cfg)
        factor = svc._resolve_factor()
        assert factor == 2.0

    def test_pre_upscale_intermediate_saved(self):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        # Mock client to avoid real HTTP calls
        svc._client = MagicMock()
        svc._client.submit_workflow.return_value = _make_comfy_result(success=False)
        job = _make_upscale_job()
        svc.execute(job)
        pre = [i for i in job.intermediates if i.stage == "pre_upscale"]
        assert len(pre) == 1
        assert pre[0].image_b64 == _FAKE_IMG_B64

    @patch("image_pipeline.anime_pipeline.agents.upscale_service.ComfyClient")
    def test_upscale_intermediate_has_model_metadata(self, MockClient):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        mock_instance = MockClient.return_value
        mock_instance.submit_workflow.return_value = _make_comfy_result(
            success=True, images=[_FAKE_IMG_B64],
        )
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        svc._client = mock_instance
        job = _make_upscale_job()
        svc.execute(job)
        up = [i for i in job.intermediates if i.stage == "upscale"]
        assert len(up) == 1
        assert up[0].metadata.get("model") == "RealESRGAN_x4plus_anime_6B"

    def test_status_set_to_upscaling(self):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        from image_pipeline.anime_pipeline.schemas import AnimePipelineStatus
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        svc._client = MagicMock()
        svc._client.submit_workflow.return_value = _make_comfy_result(success=False)
        job = _make_upscale_job()
        # Status should transition through UPSCALING
        original_status = job.status
        svc.execute(job)
        # The stage was recorded
        assert "upscale" in job.stages_executed

    def test_get_source_dimensions_from_plan(self):
        from image_pipeline.anime_pipeline.agents.upscale_service import UpscaleService
        cfg = _make_upscale_config()
        svc = UpscaleService(cfg)
        job = _make_upscale_job()
        w, h = svc._get_source_dimensions(job)
        assert w == 832
        assert h == 1216


# ═══════════════════════════════════════════════════════════════════════
# Output Manifest tests
# ═══════════════════════════════════════════════════════════════════════

class TestBuildOutputManifest:
    """Tests for build_output_manifest() function."""

    def test_basic_manifest_keys(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="mfst-001", preset="anime_quality")
        job.mark_stage("composition", 100.0)
        job.mark_stage("beauty_pass", 200.0)
        m = build_output_manifest(job)
        assert m["job_id"] == "mfst-001"
        assert m["preset"] == "anime_quality"
        assert m["vram_profile"] == "normalvram"
        assert len(m["passes"]) == 2
        assert m["critique_rounds"] == 0
        assert m["selected_final"] == "unknown"

    def test_pass_list_has_duration(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="mfst-002")
        job.mark_stage("composition_pass", 150.5)
        m = build_output_manifest(job)
        assert m["passes"][0]["name"] == "composition_pass"
        assert m["passes"][0]["duration_ms"] == 150.5

    def test_pass_output_filename(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="mfst-003")
        job.mark_stage("upscale", 300.0)
        m = build_output_manifest(job)
        assert m["passes"][0]["output"] == "05_upscaled.png"

    def test_with_rank_result(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import (
            AnimePipelineJob, RankCandidate, RankResult,
        )
        job = AnimePipelineJob(job_id="mfst-004")
        rank = RankResult(
            winner=RankCandidate(stage="upscale", composite_score=8.5, image_b64="x"),
            runner_ups=[RankCandidate(stage="beauty_pass", composite_score=7.0)],
            total_candidates=2,
        )
        m = build_output_manifest(job, rank)
        assert m["winner"]["stage"] == "upscale"
        assert m["total_candidates"] == 2
        assert m["selected_final"] == "upscale"
        # Runner-ups not included without debug_mode
        assert "runner_ups" not in m

    def test_debug_mode_includes_runner_ups(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import (
            AnimePipelineJob, RankCandidate, RankResult,
        )
        job = AnimePipelineJob(job_id="mfst-005")
        job.mark_stage("beauty_pass", 100.0)
        rank = RankResult(
            winner=RankCandidate(stage="upscale", composite_score=8.5),
            runner_ups=[RankCandidate(stage="beauty_pass", composite_score=7.0)],
            total_candidates=2,
        )
        m = build_output_manifest(job, rank, debug_mode=True)
        assert "runner_ups" in m
        assert len(m["runner_ups"]) == 1
        assert "stage_timings_ms" in m

    def test_error_included_when_present(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="mfst-006", error="ComfyUI timeout")
        m = build_output_manifest(job)
        assert m["error"] == "ComfyUI timeout"

    def test_no_error_key_when_none(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="mfst-007")
        m = build_output_manifest(job)
        assert "error" not in m

    def test_models_used_included(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="mfst-008")
        job.models_used.append("animagine")
        job.models_used.append("noobai")
        m = build_output_manifest(job)
        assert m["models_used"] == ["animagine", "noobai"]

    def test_critique_rounds_counted(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="mfst-009")
        job.critique_results.append(_make_critique())
        job.critique_results.append(_make_critique())
        m = build_output_manifest(job)
        assert m["critique_rounds"] == 2

    def test_refine_rounds_from_job(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="mfst-010", refine_rounds=2)
        m = build_output_manifest(job)
        assert m["refine_rounds"] == 2

    def test_model_for_stage_from_metadata(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="mfst-011")
        job.add_intermediate("composition_pass", _FAKE_IMG_B64, model="animagine")
        job.mark_stage("composition_pass", 100.0)
        m = build_output_manifest(job)
        assert m["passes"][0]["model"] == "animagine"


class TestManifestToJson:
    """Tests for manifest_to_json() convenience function."""

    def test_returns_valid_json_string(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            manifest_to_json,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="json-001")
        s = manifest_to_json(job)
        parsed = json.loads(s)
        assert parsed["job_id"] == "json-001"

    def test_indent_parameter(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            manifest_to_json,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="json-002")
        s = manifest_to_json(job, indent=4)
        # 4-space indent means lines start with "    "
        lines = s.split("\n")
        indented = [l for l in lines if l.startswith("    ")]
        assert len(indented) > 0

    def test_debug_mode_forwarded(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            manifest_to_json,
        )
        from image_pipeline.anime_pipeline.schemas import (
            AnimePipelineJob, RankCandidate, RankResult,
        )
        job = AnimePipelineJob(job_id="json-003")
        rank = RankResult(
            winner=RankCandidate(stage="up", composite_score=8.0),
            runner_ups=[RankCandidate(stage="b", composite_score=7.0)],
            total_candidates=2,
        )
        s = manifest_to_json(job, rank, debug_mode=True)
        parsed = json.loads(s)
        assert "runner_ups" in parsed


# ═══════════════════════════════════════════════════════════════════════
# Config — new upscale fields
# ═══════════════════════════════════════════════════════════════════════

class TestUpscaleConfigFields:
    """Config dataclass has new upscale-related fields."""

    def test_upscale_tile_size_default(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig
        cfg = AnimePipelineConfig()
        assert cfg.upscale_tile_size == 512

    def test_upscale_denoise_default(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig
        cfg = AnimePipelineConfig()
        assert cfg.upscale_denoise == 0.2

    def test_upscale_tile_size_override(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig
        cfg = AnimePipelineConfig(upscale_tile_size=768)
        assert cfg.upscale_tile_size == 768

    def test_upscale_denoise_override(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig
        cfg = AnimePipelineConfig(upscale_denoise=0.35)
        assert cfg.upscale_denoise == 0.35


# ═══════════════════════════════════════════════════════════════════════
# Import / export tests for Phase 3B-7
# ═══════════════════════════════════════════════════════════════════════

class TestPhase3B7Exports:
    """Verify all new symbols are importable and in __all__."""

    def test_import_upscale_service(self):
        from image_pipeline.anime_pipeline.agents import UpscaleService
        assert UpscaleService is not None

    def test_import_final_ranker(self):
        from image_pipeline.anime_pipeline.agents import FinalRanker
        assert FinalRanker is not None

    def test_import_score_candidate(self):
        from image_pipeline.anime_pipeline.agents import score_candidate
        assert callable(score_candidate)

    def test_import_rank_candidates(self):
        from image_pipeline.anime_pipeline.agents import rank_candidates
        assert callable(rank_candidates)

    def test_import_build_output_manifest(self):
        from image_pipeline.anime_pipeline.agents import build_output_manifest
        assert callable(build_output_manifest)

    def test_import_manifest_to_json(self):
        from image_pipeline.anime_pipeline.agents import manifest_to_json
        assert callable(manifest_to_json)

    def test_import_rank_candidate_schema(self):
        from image_pipeline.anime_pipeline.schemas import RankCandidate
        assert RankCandidate is not None

    def test_import_rank_result_schema(self):
        from image_pipeline.anime_pipeline.schemas import RankResult
        assert RankResult is not None

    def test_all_new_in_agents_all(self):
        from image_pipeline.anime_pipeline import agents
        expected = [
            "UpscaleService", "FinalRanker",
            "score_candidate", "rank_candidates",
            "build_output_manifest", "manifest_to_json",
        ]
        for name in expected:
            assert name in agents.__all__, f"{name} not in agents.__all__"

    def test_old_exports_still_present(self):
        from image_pipeline.anime_pipeline import agents
        old = [
            "VisionAnalystAgent", "LayerPlannerAgent",
            "CompositionPassAgent", "StructureLockAgent",
            "CleanupPassAgent", "BeautyPassAgent",
            "CritiqueAgent", "UpscaleAgent",
            "RefineLoopAgent", "critique_image",
            "decide_refine_action", "patch_plan_from_critique",
            "run_refine_round",
        ]
        for name in old:
            assert name in agents.__all__, f"{name} missing from agents.__all__"


# ═══════════════════════════════════════════════════════════════════════
# VRAM Profile — Config, Manager, Retry, OOM
# ═══════════════════════════════════════════════════════════════════════

class TestVRAMProfileEnum:
    """VRAMProfile enum values and string coercion."""

    def test_auto_value(self):
        from image_pipeline.anime_pipeline.config import VRAMProfile
        assert VRAMProfile.AUTO.value == "auto"

    def test_normalvram_value(self):
        from image_pipeline.anime_pipeline.config import VRAMProfile
        assert VRAMProfile.NORMALVRAM.value == "normalvram"

    def test_lowvram_value(self):
        from image_pipeline.anime_pipeline.config import VRAMProfile
        assert VRAMProfile.LOWVRAM.value == "lowvram"

    def test_from_string(self):
        from image_pipeline.anime_pipeline.config import VRAMProfile
        assert VRAMProfile("normalvram") == VRAMProfile.NORMALVRAM

    def test_is_str_enum(self):
        from image_pipeline.anime_pipeline.config import VRAMProfile
        assert isinstance(VRAMProfile.AUTO, str)


class TestVRAMProfileConfig:
    """VRAMProfileConfig defaults and to_dict."""

    def test_default_is_normalvram(self):
        from image_pipeline.anime_pipeline.config import VRAMProfileConfig, VRAMProfile
        cfg = VRAMProfileConfig()
        assert cfg.profile == VRAMProfile.NORMALVRAM

    def test_normalvram_limits(self):
        from image_pipeline.anime_pipeline.config import VRAMProfileConfig
        cfg = VRAMProfileConfig()
        assert cfg.max_resolution == 1216
        assert cfg.step_cap == 35
        assert cfg.max_controlnet_layers == 2
        assert cfg.cpu_vae_offload is False
        assert cfg.disable_previews is False

    def test_to_dict_keys(self):
        from image_pipeline.anime_pipeline.config import VRAMProfileConfig
        d = VRAMProfileConfig().to_dict()
        expected = {
            "profile", "max_resolution", "step_cap", "max_controlnet_layers",
            "cpu_vae_offload", "disable_previews", "unload_models_between_passes",
            "upscale_tile_size", "max_upscale_factor",
            "oom_retry_enabled", "oom_resolution_step_down", "oom_max_retries",
        }
        assert set(d.keys()) == expected

    def test_to_dict_profile_is_string(self):
        from image_pipeline.anime_pipeline.config import VRAMProfileConfig
        d = VRAMProfileConfig().to_dict()
        assert d["profile"] == "normalvram"


class TestResolveVRAMProfile:
    """resolve_vram_profile() with various inputs."""

    def test_normalvram_string(self):
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        cfg = resolve_vram_profile("normalvram")
        assert cfg.max_resolution == 1216
        assert cfg.cpu_vae_offload is False

    def test_lowvram_string(self):
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        cfg = resolve_vram_profile("lowvram")
        assert cfg.max_resolution == 1024
        assert cfg.cpu_vae_offload is True
        assert cfg.disable_previews is True
        assert cfg.max_controlnet_layers == 1

    def test_lowvram_upscale_limits(self):
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        cfg = resolve_vram_profile("lowvram")
        assert cfg.max_upscale_factor == 1.5
        assert cfg.upscale_tile_size == 384

    def test_auto_defaults_to_normalvram(self):
        import os
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        # Clear env to avoid interference
        old = os.environ.pop("ANIME_PIPELINE_VRAM_PROFILE", None)
        try:
            cfg = resolve_vram_profile("auto")
            assert cfg.max_resolution == 1216
        finally:
            if old is not None:
                os.environ["ANIME_PIPELINE_VRAM_PROFILE"] = old

    def test_auto_reads_env(self):
        import os
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        old = os.environ.get("ANIME_PIPELINE_VRAM_PROFILE")
        os.environ["ANIME_PIPELINE_VRAM_PROFILE"] = "lowvram"
        try:
            cfg = resolve_vram_profile("auto")
            assert cfg.max_resolution == 1024
        finally:
            if old is not None:
                os.environ["ANIME_PIPELINE_VRAM_PROFILE"] = old
            else:
                os.environ.pop("ANIME_PIPELINE_VRAM_PROFILE", None)

    def test_unknown_string_falls_back(self):
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        cfg = resolve_vram_profile("ultravram")
        assert cfg.max_resolution == 1216  # normalvram default

    def test_enum_input(self):
        from image_pipeline.anime_pipeline.config import resolve_vram_profile, VRAMProfile
        cfg = resolve_vram_profile(VRAMProfile.LOWVRAM)
        assert cfg.max_resolution == 1024

    def test_normalvram_oom_settings(self):
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        cfg = resolve_vram_profile("normalvram")
        assert cfg.oom_retry_enabled is True
        assert cfg.oom_max_retries == 2
        assert cfg.oom_resolution_step_down == 128

    def test_lowvram_oom_more_retries(self):
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        cfg = resolve_vram_profile("lowvram")
        assert cfg.oom_max_retries == 3


class TestAnimePipelineConfigVRAM:
    """AnimePipelineConfig VRAM field integration."""

    def test_default_config_has_vram(self):
        from image_pipeline.anime_pipeline.config import AnimePipelineConfig, VRAMProfile
        cfg = AnimePipelineConfig()
        assert cfg.vram_profile == VRAMProfile.AUTO
        assert cfg.vram is not None

    def test_load_config_resolves_vram(self):
        from image_pipeline.anime_pipeline.config import load_config
        cfg = load_config()
        # Should be resolved (not AUTO)
        from image_pipeline.anime_pipeline.config import VRAMProfile
        assert cfg.vram.profile in (VRAMProfile.NORMALVRAM, VRAMProfile.LOWVRAM)


class TestIsOOMError:
    """is_oom_error() detection."""

    def test_cuda_oom(self):
        from image_pipeline.anime_pipeline.vram_manager import is_oom_error
        assert is_oom_error("CUDA out of memory") is True

    def test_torch_oom(self):
        from image_pipeline.anime_pipeline.vram_manager import is_oom_error
        assert is_oom_error("torch.cuda.OutOfMemoryError: allocator") is True

    def test_generic_oom(self):
        from image_pipeline.anime_pipeline.vram_manager import is_oom_error
        assert is_oom_error("RuntimeError: OOM during generation") is True

    def test_not_enough_memory(self):
        from image_pipeline.anime_pipeline.vram_manager import is_oom_error
        assert is_oom_error("Not enough memory on device") is True

    def test_not_oom(self):
        from image_pipeline.anime_pipeline.vram_manager import is_oom_error
        assert is_oom_error("Connection refused") is False

    def test_empty_string(self):
        from image_pipeline.anime_pipeline.vram_manager import is_oom_error
        assert is_oom_error("") is False

    def test_case_insensitive(self):
        from image_pipeline.anime_pipeline.vram_manager import is_oom_error
        assert is_oom_error("CUDA OUT OF MEMORY") is True


class TestRetryContext:
    """RetryContext dataclass behavior."""

    def test_initial_state(self):
        from image_pipeline.anime_pipeline.vram_manager import RetryContext
        ctx = RetryContext(
            original_width=832, original_height=1216,
            current_width=832, current_height=1216,
        )
        assert ctx.attempts == 0
        assert ctx.exhausted is False
        assert ctx.profile_escalated is False

    def test_exhausted_after_max(self):
        from image_pipeline.anime_pipeline.vram_manager import RetryContext
        ctx = RetryContext(max_retries=2, attempts=2)
        assert ctx.exhausted is True

    def test_not_exhausted_below_max(self):
        from image_pipeline.anime_pipeline.vram_manager import RetryContext
        ctx = RetryContext(max_retries=2, attempts=1)
        assert ctx.exhausted is False

    def test_to_dict(self):
        from image_pipeline.anime_pipeline.vram_manager import RetryContext
        ctx = RetryContext(
            original_width=832, original_height=1216,
            current_width=704, current_height=1088,
            attempts=1, profile_escalated=False,
        )
        d = ctx.to_dict()
        assert d["original_resolution"] == "832x1216"
        assert d["final_resolution"] == "704x1088"
        assert d["attempts"] == 1


class TestBuildRetryContext:
    """build_retry_context() factory."""

    def test_copies_dimensions(self):
        from image_pipeline.anime_pipeline.vram_manager import build_retry_context
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        vram = resolve_vram_profile("normalvram")
        ctx = build_retry_context(832, 1216, vram)
        assert ctx.original_width == 832
        assert ctx.current_width == 832
        assert ctx.max_retries == 2

    def test_lowvram_has_more_retries(self):
        from image_pipeline.anime_pipeline.vram_manager import build_retry_context
        from image_pipeline.anime_pipeline.config import resolve_vram_profile
        vram = resolve_vram_profile("lowvram")
        ctx = build_retry_context(832, 1024, vram)
        assert ctx.max_retries == 3


class TestStepDownResolution:
    """step_down_resolution() logic."""

    def test_reduces_by_step(self):
        from image_pipeline.anime_pipeline.vram_manager import (
            RetryContext, step_down_resolution,
        )
        ctx = RetryContext(
            current_width=832, current_height=1216,
            resolution_step_down=128, max_retries=3,
        )
        w, h = step_down_resolution(ctx)
        assert w == 704
        assert h == 1088
        assert ctx.attempts == 1

    def test_rounds_to_8(self):
        from image_pipeline.anime_pipeline.vram_manager import (
            RetryContext, step_down_resolution,
        )
        ctx = RetryContext(
            current_width=830, current_height=1210,
            resolution_step_down=128, max_retries=3,
        )
        w, h = step_down_resolution(ctx)
        assert w % 8 == 0
        assert h % 8 == 0

    def test_floor_at_512(self):
        from image_pipeline.anime_pipeline.vram_manager import (
            RetryContext, step_down_resolution,
        )
        ctx = RetryContext(
            current_width=520, current_height=520,
            resolution_step_down=128, max_retries=3,
        )
        w, h = step_down_resolution(ctx)
        assert w >= 512
        assert h >= 512

    def test_logs_retry(self):
        from image_pipeline.anime_pipeline.vram_manager import (
            RetryContext, step_down_resolution,
        )
        ctx = RetryContext(
            current_width=832, current_height=1216,
            resolution_step_down=128, max_retries=3,
        )
        step_down_resolution(ctx)
        assert len(ctx.retries_log) == 1
        assert ctx.retries_log[0]["action"] == "resolution_step_down"

    def test_successive_step_downs(self):
        from image_pipeline.anime_pipeline.vram_manager import (
            RetryContext, step_down_resolution,
        )
        ctx = RetryContext(
            current_width=832, current_height=1216,
            resolution_step_down=128, max_retries=5,
        )
        step_down_resolution(ctx)  # 704, 1088
        step_down_resolution(ctx)  # 576, 960
        assert ctx.current_width == 576
        assert ctx.current_height == 960
        assert ctx.attempts == 2


class TestEscalateToLowvram:
    """escalate_to_lowvram() profile switch."""

    def test_returns_lowvram_config(self):
        from image_pipeline.anime_pipeline.vram_manager import (
            RetryContext, escalate_to_lowvram,
        )
        ctx = RetryContext(attempts=2)
        cfg = escalate_to_lowvram(ctx)
        assert cfg.max_resolution == 1024
        assert cfg.cpu_vae_offload is True
        assert ctx.profile_escalated is True

    def test_logs_escalation(self):
        from image_pipeline.anime_pipeline.vram_manager import (
            RetryContext, escalate_to_lowvram,
        )
        ctx = RetryContext(attempts=2)
        escalate_to_lowvram(ctx)
        assert any(r["action"] == "profile_escalation" for r in ctx.retries_log)


class TestStripPreviewNodes:
    """strip_preview_nodes() workflow patching."""

    def test_removes_preview_nodes(self):
        from image_pipeline.anime_pipeline.vram_manager import strip_preview_nodes
        wf = {
            "1": {"class_type": "KSampler", "inputs": {}},
            "2": {"class_type": "PreviewImage", "inputs": {"images": ["1", 0]}},
            "3": {"class_type": "SaveImage", "inputs": {}},
        }
        cleaned = strip_preview_nodes(wf)
        assert "2" not in cleaned
        assert "1" in cleaned
        assert "3" in cleaned

    def test_no_previews_returns_same(self):
        from image_pipeline.anime_pipeline.vram_manager import strip_preview_nodes
        wf = {
            "1": {"class_type": "KSampler", "inputs": {}},
            "2": {"class_type": "SaveImage", "inputs": {}},
        }
        cleaned = strip_preview_nodes(wf)
        assert cleaned == wf

    def test_empty_workflow(self):
        from image_pipeline.anime_pipeline.vram_manager import strip_preview_nodes
        assert strip_preview_nodes({}) == {}

    def test_multiple_previews(self):
        from image_pipeline.anime_pipeline.vram_manager import strip_preview_nodes
        wf = {
            "1": {"class_type": "PreviewImage", "inputs": {}},
            "2": {"class_type": "PreviewImage", "inputs": {}},
            "3": {"class_type": "SaveImage", "inputs": {}},
        }
        cleaned = strip_preview_nodes(wf)
        assert len(cleaned) == 1
        assert "3" in cleaned


class TestFreeModelsBetweenPasses:
    """free_models_between_passes() with mocked httpx."""

    def test_unload_false_skips(self):
        from image_pipeline.anime_pipeline.vram_manager import free_models_between_passes
        assert free_models_between_passes("http://localhost:8188", unload=False) is False

    def test_success(self):
        from unittest.mock import patch, MagicMock
        from image_pipeline.anime_pipeline.vram_manager import free_models_between_passes

        mock_client = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client.post.return_value = mock_resp

        with patch("image_pipeline.anime_pipeline.vram_manager.httpx.Client", return_value=mock_client):
            result = free_models_between_passes("http://localhost:8188", unload=True)
        assert result is True

    def test_failure_returns_false(self):
        from unittest.mock import patch
        from image_pipeline.anime_pipeline.vram_manager import free_models_between_passes

        with patch("image_pipeline.anime_pipeline.vram_manager.httpx.Client", side_effect=Exception("conn")):
            result = free_models_between_passes("http://localhost:8188", unload=True)
        assert result is False


class TestSubmitWithOOMRetry:
    """submit_with_oom_retry() integration tests with mocks."""

    def _make_result(self, success=True, error=""):
        from unittest.mock import MagicMock
        r = MagicMock()
        r.success = success
        r.error = error
        return r

    def _make_client(self, results):
        from unittest.mock import MagicMock
        client = MagicMock()
        client.submit_workflow = MagicMock(side_effect=results)
        client.base_url = "http://localhost:8188"
        return client

    def test_success_on_first_try(self):
        from image_pipeline.anime_pipeline.vram_manager import submit_with_oom_retry
        from image_pipeline.anime_pipeline.config import resolve_vram_profile

        ok = self._make_result(success=True)
        client = self._make_client([ok])
        vram = resolve_vram_profile("normalvram")

        result, ctx = submit_with_oom_retry(
            client, lambda w, h: {"test": True},
            "beauty_pass", "job1", vram, 832, 1216,
        )
        assert result.success is True
        assert ctx.attempts == 0

    def test_oom_then_success(self):
        from unittest.mock import patch
        from image_pipeline.anime_pipeline.vram_manager import submit_with_oom_retry
        from image_pipeline.anime_pipeline.config import resolve_vram_profile

        oom = self._make_result(success=False, error="CUDA out of memory")
        ok = self._make_result(success=True)
        client = self._make_client([oom, ok])
        vram = resolve_vram_profile("normalvram")

        with patch("image_pipeline.anime_pipeline.vram_manager.free_models_between_passes"):
            result, ctx = submit_with_oom_retry(
                client, lambda w, h: {"test": True},
                "beauty_pass", "job1", vram, 832, 1216,
            )
        assert result.success is True
        assert ctx.attempts == 1
        assert ctx.current_width == 704

    def test_oom_exhausted_then_escalation(self):
        from unittest.mock import patch
        from image_pipeline.anime_pipeline.vram_manager import submit_with_oom_retry
        from image_pipeline.anime_pipeline.config import resolve_vram_profile

        oom = self._make_result(success=False, error="CUDA out of memory")
        ok = self._make_result(success=True)
        # 1st attempt (original), 2 retries (both OOM), 1 escalation
        client = self._make_client([oom, oom, oom, ok])
        vram = resolve_vram_profile("normalvram")

        with patch("image_pipeline.anime_pipeline.vram_manager.free_models_between_passes"):
            result, ctx = submit_with_oom_retry(
                client, lambda w, h: {"test": True},
                "beauty_pass", "job1", vram, 832, 1216,
            )
        assert result.success is True
        assert ctx.profile_escalated is True

    def test_non_oom_error_no_retry(self):
        from image_pipeline.anime_pipeline.vram_manager import submit_with_oom_retry
        from image_pipeline.anime_pipeline.config import resolve_vram_profile

        err = self._make_result(success=False, error="Connection refused")
        client = self._make_client([err])
        vram = resolve_vram_profile("normalvram")

        result, ctx = submit_with_oom_retry(
            client, lambda w, h: {"test": True},
            "beauty_pass", "job1", vram, 832, 1216,
        )
        assert result.success is False
        assert ctx.attempts == 0

    def test_retry_disabled(self):
        from image_pipeline.anime_pipeline.vram_manager import submit_with_oom_retry
        from image_pipeline.anime_pipeline.config import VRAMProfileConfig, VRAMProfile

        vram = VRAMProfileConfig(profile=VRAMProfile.NORMALVRAM, oom_retry_enabled=False)
        oom = self._make_result(success=False, error="CUDA out of memory")
        client = self._make_client([oom])

        result, ctx = submit_with_oom_retry(
            client, lambda w, h: {"test": True},
            "beauty_pass", "job1", vram, 832, 1216,
        )
        assert result.success is False
        assert ctx.attempts == 0

    def test_preview_stripped_when_disabled(self):
        from unittest.mock import patch, MagicMock
        from image_pipeline.anime_pipeline.vram_manager import submit_with_oom_retry
        from image_pipeline.anime_pipeline.config import VRAMProfileConfig, VRAMProfile

        vram = VRAMProfileConfig(
            profile=VRAMProfile.LOWVRAM,
            disable_previews=True,
            oom_retry_enabled=False,
        )
        ok = self._make_result(success=True)
        client = self._make_client([ok])

        workflows_submitted = []
        original_submit = client.submit_workflow

        def capture_wf(wf, **kw):
            workflows_submitted.append(wf)
            return original_submit(wf, **kw)

        client.submit_workflow = capture_wf

        def build(w, h):
            return {
                "1": {"class_type": "KSampler", "inputs": {}},
                "2": {"class_type": "PreviewImage", "inputs": {}},
            }

        result, ctx = submit_with_oom_retry(
            client, build, "beauty_pass", "job1", vram, 832, 1024,
        )
        # PreviewImage should have been stripped
        assert "2" not in workflows_submitted[0]


class TestManifestVRAMProfile:
    """build_output_manifest() respects vram_profile parameter."""

    def test_default_is_normalvram(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="vram-test-1")
        m = build_output_manifest(job)
        assert m["vram_profile"] == "normalvram"

    def test_explicit_lowvram(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        job = AnimePipelineJob(job_id="vram-test-2")
        m = build_output_manifest(job, vram_profile="lowvram")
        assert m["vram_profile"] == "lowvram"

    def test_manifest_to_json_passes_profile(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            manifest_to_json,
        )
        from image_pipeline.anime_pipeline.schemas import AnimePipelineJob
        import json
        job = AnimePipelineJob(job_id="vram-test-3")
        raw = manifest_to_json(job, vram_profile="lowvram")
        data = json.loads(raw)
        assert data["vram_profile"] == "lowvram"


class TestVRAMExports:
    """Verify all VRAM symbols are importable from the package."""

    def test_import_vram_profile_enum(self):
        from image_pipeline.anime_pipeline import VRAMProfile
        assert VRAMProfile.AUTO.value == "auto"

    def test_import_vram_profile_config(self):
        from image_pipeline.anime_pipeline import VRAMProfileConfig
        assert VRAMProfileConfig is not None

    def test_import_resolve_vram_profile(self):
        from image_pipeline.anime_pipeline import resolve_vram_profile
        assert callable(resolve_vram_profile)

    def test_import_is_oom_error(self):
        from image_pipeline.anime_pipeline import is_oom_error
        assert callable(is_oom_error)

    def test_import_retry_context(self):
        from image_pipeline.anime_pipeline import RetryContext
        assert RetryContext is not None

    def test_import_build_retry_context(self):
        from image_pipeline.anime_pipeline import build_retry_context
        assert callable(build_retry_context)

    def test_import_step_down_resolution(self):
        from image_pipeline.anime_pipeline import step_down_resolution
        assert callable(step_down_resolution)

    def test_import_escalate_to_lowvram(self):
        from image_pipeline.anime_pipeline import escalate_to_lowvram
        assert callable(escalate_to_lowvram)

    def test_import_strip_preview_nodes(self):
        from image_pipeline.anime_pipeline import strip_preview_nodes
        assert callable(strip_preview_nodes)

    def test_import_free_models(self):
        from image_pipeline.anime_pipeline import free_models_between_passes
        assert callable(free_models_between_passes)

    def test_import_submit_with_oom_retry(self):
        from image_pipeline.anime_pipeline import submit_with_oom_retry
        assert callable(submit_with_oom_retry)

    def test_import_log_helpers(self):
        from image_pipeline.anime_pipeline import (
            log_pass_memory_mode,
            log_retry_cause,
            log_final_fallback,
        )
        assert callable(log_pass_memory_mode)
        assert callable(log_retry_cause)
        assert callable(log_final_fallback)

    def test_all_vram_in_package_all(self):
        import image_pipeline.anime_pipeline as pkg
        expected = [
            "VRAMProfile", "VRAMProfileConfig", "resolve_vram_profile",
            "is_oom_error", "RetryContext", "build_retry_context",
            "step_down_resolution", "escalate_to_lowvram",
            "strip_preview_nodes", "free_models_between_passes",
            "submit_with_oom_retry",
            "log_pass_memory_mode", "log_retry_cause", "log_final_fallback",
        ]
        for name in expected:
            assert name in pkg.__all__, f"{name} not in __all__"
