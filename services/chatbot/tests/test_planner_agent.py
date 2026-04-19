"""
Unit tests — LayerPlannerAgent

Covers:
    - make_layer_plan standalone function
    - LayerPlannerAgent.build_plan (preset application, resolution, prompt building)
    - Orientation detection (portrait, landscape, square, auto)
    - Critique integration (prompt patching, negative tagging)
    - Pass ordering and skipping (speed preset skips cleanup/upscale)
    - Resolution clamping per VRAM profile
    - Negative constraint building from vision analysis
    - Style tag deduplication
    - Identity anchor emphasis
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "services" / "chatbot"))

import pytest
from unittest.mock import patch, MagicMock
from dataclasses import replace

from image_pipeline.anime_pipeline.config import (
    AnimePipelineConfig,
    ModelConfig,
    VRAMProfile,
    VRAMProfileConfig,
    load_config,
)
from image_pipeline.anime_pipeline.schemas import (
    AnimePipelineJob,
    CritiqueReport,
    LayerPlan,
    PassConfig,
    VisionAnalysis,
)
from image_pipeline.anime_pipeline.agents.layer_planner import (
    LayerPlannerAgent,
    make_layer_plan,
    _PORTRAIT_HINTS,
    _LANDSCAPE_HINTS,
    _SQUARE_HINTS,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def config():
    """Minimal config with known defaults."""
    return AnimePipelineConfig(
        composition_model=ModelConfig(
            checkpoint="animagine-xl-4.0-opt.safetensors",
            sampler="euler_a", scheduler="normal", steps=28, cfg=5.0,
        ),
        beauty_model=ModelConfig(
            checkpoint="noobai-xl-1.1.safetensors",
            sampler="dpmpp_2m_sde", scheduler="karras", steps=28, cfg=5.5,
            denoise_strength=0.30,
        ),
        final_model=ModelConfig(
            checkpoint="noobai-xl-1.1.safetensors",
        ),
        portrait_res=(832, 1216),
        landscape_res=(1216, 832),
        square_res=(1024, 1024),
        quality_prefix="masterpiece, best quality",
        negative_base="lowres, bad anatomy",
        upscale_model="RealESRGAN_x4plus_anime_6B",
        upscale_factor=2,
    )


@pytest.fixture
def planner(config):
    return LayerPlannerAgent(config)


@pytest.fixture
def basic_job():
    return AnimePipelineJob(
        user_prompt="1girl, silver hair, blue eyes, standing in cherry blossoms",
    )


@pytest.fixture
def vision_analysis():
    return VisionAnalysis(
        caption_short="A girl with silver hair in cherry blossoms",
        caption_detailed="Detailed scene description",
        subjects=["1girl", "silver hair", "blue eyes"],
        pose="standing",
        camera_angle="medium",
        framing="medium_shot",
        dominant_colors=["pink", "silver"],
        anime_tags=["clean_lineart", "detailed_eyes"],
        quality_risks=["possible hand issues"],
        identity_anchors=["silver hair", "blue eyes"],
        background_elements=["cherry blossoms", "soft light"],
        confidence=0.85,
    )


# ═══════════════════════════════════════════════════════════════════
# make_layer_plan (standalone)
# ═══════════════════════════════════════════════════════════════════

class TestMakeLayerPlan:
    def test_returns_layer_plan(self, config):
        plan = make_layer_plan("1girl, anime style", config=config)
        assert isinstance(plan, LayerPlan)
        assert len(plan.passes) >= 3  # at least composition, structure_lock, beauty

    def test_with_references(self, config, vision_analysis):
        plan = make_layer_plan(
            "anime girl",
            references=vision_analysis,
            config=config,
        )
        assert plan.scene_summary == vision_analysis.caption_short
        assert "1girl" in plan.subject_list

    def test_preset_anime_speed_skips_cleanup(self, config):
        plan = make_layer_plan(
            "anime girl",
            preset="anime_speed",
            config=config,
        )
        pass_names = [p.pass_name for p in plan.passes]
        assert "cleanup" not in pass_names

    def test_fast_quality_skips_upscale(self, config):
        plan = make_layer_plan(
            "anime girl",
            quality_hint="fast",
            config=config,
        )
        pass_names = [p.pass_name for p in plan.passes]
        assert "upscale" not in pass_names

    def test_vram_8gb_caps_resolution(self, config):
        plan = make_layer_plan(
            "landscape scenery",
            vram_profile="8gb",
            config=config,
        )
        comp = plan.get_pass("composition")
        assert comp.width <= 1024
        assert comp.height <= 1024


# ═══════════════════════════════════════════════════════════════════
# Orientation detection
# ═══════════════════════════════════════════════════════════════════

class TestOrientationDetection:
    def test_portrait_keyword(self, planner):
        job = AnimePipelineJob(user_prompt="full body standing pose")
        assert planner._detect_orientation(job) == "portrait"

    def test_landscape_keyword(self, planner):
        job = AnimePipelineJob(user_prompt="wide landscape scenery")
        assert planner._detect_orientation(job) == "landscape"

    def test_square_keyword(self, planner):
        job = AnimePipelineJob(user_prompt="avatar 1:1 icon")
        assert planner._detect_orientation(job) == "square"

    def test_default_portrait(self, planner):
        job = AnimePipelineJob(user_prompt="anime girl")
        assert planner._detect_orientation(job) == "portrait"

    def test_explicit_hint_overrides(self, planner):
        job = AnimePipelineJob(
            user_prompt="wide landscape scenery",
            orientation_hint="square",
        )
        assert planner._detect_orientation(job) == "square"


# ═══════════════════════════════════════════════════════════════════
# Resolution
# ═══════════════════════════════════════════════════════════════════

class TestResolution:
    def test_portrait_resolution(self, planner, config):
        assert planner._get_resolution("portrait") == config.portrait_res

    def test_landscape_resolution(self, planner, config):
        assert planner._get_resolution("landscape") == config.landscape_res

    def test_square_resolution(self, planner, config):
        assert planner._get_resolution("square") == config.square_res

    def test_clamp_rounds_to_8(self):
        from image_pipeline.anime_pipeline.planner_presets import get_preset
        preset = get_preset("anime_quality")
        w, h = LayerPlannerAgent._clamp_resolution(
            833, 1217, {"max_dim": 1216}, preset,
        )
        assert w % 8 == 0
        assert h % 8 == 0

    def test_clamp_caps_to_vram(self):
        from image_pipeline.anime_pipeline.planner_presets import get_preset
        preset = get_preset("anime_quality")
        w, h = LayerPlannerAgent._clamp_resolution(
            1344, 1344, {"max_dim": 1024}, preset,
        )
        assert w <= 1024
        assert h <= 1024


# ═══════════════════════════════════════════════════════════════════
# Pass ordering
# ═══════════════════════════════════════════════════════════════════

class TestPassOrdering:
    def test_quality_preset_full_passes(self, planner, basic_job):
        plan = planner.build_plan(basic_job, preset_name="anime_quality")
        names = [p.pass_name for p in plan.passes]
        assert names[0] == "composition"
        assert names[1] == "structure_lock"
        assert "beauty" in names
        assert "upscale" in names

    def test_speed_preset_shorter(self, planner, basic_job):
        plan = planner.build_plan(basic_job, preset_name="anime_speed")
        names = [p.pass_name for p in plan.passes]
        assert "cleanup" not in names

    def test_composition_is_always_first(self, planner, basic_job):
        for preset_name in ["anime_quality", "anime_speed", "anime_balanced"]:
            plan = planner.build_plan(basic_job, preset_name=preset_name)
            assert plan.passes[0].pass_name == "composition"

    def test_structure_lock_after_composition(self, planner, basic_job):
        plan = planner.build_plan(basic_job)
        names = [p.pass_name for p in plan.passes]
        assert names.index("structure_lock") > names.index("composition")

    def test_beauty_after_structure_lock(self, planner, basic_job):
        plan = planner.build_plan(basic_job)
        names = [p.pass_name for p in plan.passes]
        assert names.index("beauty") > names.index("structure_lock")


# ═══════════════════════════════════════════════════════════════════
# Prompt construction
# ═══════════════════════════════════════════════════════════════════

class TestPromptConstruction:
    def test_quality_prefix_in_positive(self, planner, basic_job):
        plan = planner.build_plan(basic_job)
        comp = plan.get_pass("composition")
        assert "masterpiece" in comp.positive_prompt

    def test_user_prompt_in_positive(self, planner, basic_job):
        plan = planner.build_plan(basic_job)
        comp = plan.get_pass("composition")
        assert "silver hair" in comp.positive_prompt

    def test_negative_base_in_negative(self, planner, basic_job):
        plan = planner.build_plan(basic_job)
        comp = plan.get_pass("composition")
        assert "bad anatomy" in comp.negative_prompt

    def test_vision_tags_added(self, planner, vision_analysis):
        job = AnimePipelineJob(
            user_prompt="anime girl",
            vision_analysis=vision_analysis,
        )
        plan = planner.build_plan(job)
        comp = plan.get_pass("composition")
        assert "detailed_eyes" in comp.positive_prompt


# ═══════════════════════════════════════════════════════════════════
# Critique integration
# ═══════════════════════════════════════════════════════════════════

class TestCritiqueIntegration:
    def test_critique_patches_positive(self, planner, basic_job):
        critique = CritiqueReport(
            anatomy_score=7, face_score=7, hands_score=7,
            composition_score=7, color_score=7, style_score=7,
            background_score=7,
            prompt_patch=["better eyes", "sharper lineart"],
        )
        plan = planner.build_plan(basic_job, critique=critique)
        comp = plan.get_pass("composition")
        assert "better eyes" in comp.positive_prompt
        assert "sharper lineart" in comp.positive_prompt

    def test_critique_patches_negative(self, planner, basic_job):
        critique = CritiqueReport(
            anatomy_score=7, face_score=7, hands_score=7,
            composition_score=7, color_score=7, style_score=7,
            background_score=7,
            anatomy_issues=["twisted arm"],
        )
        plan = planner.build_plan(basic_job, critique=critique)
        comp = plan.get_pass("composition")
        assert "twisted arm" in comp.negative_prompt


# ═══════════════════════════════════════════════════════════════════
# Metadata population
# ═══════════════════════════════════════════════════════════════════

class TestMetadata:
    def test_scene_summary_from_vision(self, planner, vision_analysis):
        job = AnimePipelineJob(
            user_prompt="test", vision_analysis=vision_analysis,
        )
        plan = planner.build_plan(job)
        assert plan.scene_summary == vision_analysis.caption_short

    def test_scene_summary_fallback_to_prompt(self, planner, basic_job):
        plan = planner.build_plan(basic_job)
        assert plan.scene_summary == basic_job.user_prompt[:200]

    def test_palette_from_vision(self, planner, vision_analysis):
        job = AnimePipelineJob(
            user_prompt="test", vision_analysis=vision_analysis,
        )
        plan = planner.build_plan(job)
        assert "pink" in plan.palette

    def test_style_tags_deduplication(self, planner, basic_job):
        plan = planner.build_plan(basic_job)
        assert len(plan.style_tags) == len(set(plan.style_tags))


# ═══════════════════════════════════════════════════════════════════
# Execute (orchestrator interface)
# ═══════════════════════════════════════════════════════════════════

class TestPlannerExecute:
    def test_sets_status_and_plan(self, planner, basic_job):
        result = planner.execute(basic_job)
        assert result.layer_plan is not None
        assert "layer_planning" in result.stages_executed

    def test_records_timing(self, planner, basic_job):
        planner.execute(basic_job)
        assert "layer_planning" in basic_job.stage_timings_ms
        assert basic_job.stage_timings_ms["layer_planning"] >= 0


# ═══════════════════════════════════════════════════════════════════
# Img2img composition
# ═══════════════════════════════════════════════════════════════════

class TestImg2ImgComposition:
    def test_source_image_caps_denoise(self, planner):
        job = AnimePipelineJob(
            user_prompt="anime girl",
            source_image_b64="base64data",
        )
        plan = planner.build_plan(job)
        comp = plan.get_pass("composition")
        assert comp.denoise < 1.0

    def test_no_source_uses_full_denoise(self, planner, basic_job):
        plan = planner.build_plan(basic_job)
        comp = plan.get_pass("composition")
        assert comp.denoise == 1.0
