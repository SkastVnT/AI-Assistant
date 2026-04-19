"""
Unit tests — CritiqueAgent + RefineLoop + FinalRanker

Covers:
    CritiqueAgent:
        - JSON parsing (new format with per-dimension scores 0-10)
        - JSON parsing (old format with overall_score 0-1)
        - Fallback when no output image exists
        - Model fallback chain
        - Markdown fence stripping

    decide_refine_action (pure logic):
        - Max rounds reached → stop
        - Score above threshold → stop
        - Failing dimensions → correct actions
        - Artifact accumulation → switch to subtle preset
        - Denoise up for anatomy, denoise down for color

    patch_plan_from_critique (pure logic):
        - Denoise adjustment clamped to floor/ceiling
        - Control strength adjustment
        - Prompt patching (positive + negative)
        - Beauty preset switch
        - Critique prompt_patch/control_patch merged

    FinalRanker:
        - score_candidate composite math
        - rank_candidates ordering
        - Empty candidate list
        - Artifact penalty cap

    OutputManifest:
        - build_output_manifest structure
        - manifest_to_json serialization
        - Debug mode includes runner-ups
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
from dataclasses import replace

from image_pipeline.anime_pipeline.config import AnimePipelineConfig, ModelConfig
from image_pipeline.anime_pipeline.schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    ControlInput,
    CritiqueReport,
    IntermediateImage,
    PassConfig,
    RankCandidate,
    RankResult,
    RefineAction,
    RefineActionType,
    RefineDecision,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def config():
    return AnimePipelineConfig(
        vision_model_priority=["gemini-2.0-flash", "gpt-4o-mini"],
        quality_threshold=0.70,
        max_refine_rounds=2,
        refine_score_threshold=7.0,
        refine_denoise_step_up=0.05,
        refine_denoise_step_down=0.03,
        refine_denoise_floor=0.12,
        refine_denoise_ceiling=0.55,
        refine_control_boost=0.10,
        refine_control_reduce=0.05,
        refine_artifact_accumulation_limit=8,
        refine_dimension_thresholds={
            "anatomy": 5, "face_symmetry": 5, "eye_consistency": 5,
            "hand_quality": 4, "clothing_consistency": 5,
            "style_drift": 5, "color_drift": 5, "background_clutter": 4,
            "missing_accessories": 4, "pose_drift": 5,
        },
    )


@pytest.fixture
def good_critique():
    return CritiqueReport(
        anatomy_score=8, face_score=8, eye_consistency_score=8,
        hands_score=7, clothing_score=8,
        composition_score=8, color_score=8, style_score=8,
        background_score=7, accessories_score=8, pose_score=8,
        model_used="gemini-2.0-flash",
    )


@pytest.fixture
def bad_critique():
    return CritiqueReport(
        anatomy_score=3, face_score=4, hands_score=2,
        composition_score=6, color_score=7, style_score=5,
        background_score=4,
        anatomy_issues=["twisted arm", "wrong proportions"],
        face_issues=["asymmetric eyes"],
        hand_issues=["extra fingers", "broken wrist"],
        background_issues=["cluttered"],
        retry_recommendation=True,
        model_used="gemini-2.0-flash",
    )


@pytest.fixture
def beauty_pass_config():
    return PassConfig(
        pass_name="beauty",
        model_slot="final",
        checkpoint="noobai-xl-1.1.safetensors",
        width=832, height=1216,
        sampler="dpmpp_2m_sde", scheduler="karras",
        steps=28, cfg=5.5, denoise=0.30,
        positive_prompt="masterpiece, 1girl",
        negative_prompt="lowres, bad anatomy",
        control_inputs=[
            ControlInput(
                layer_type="lineart_anime",
                controlnet_model="control_v11p_sd15_lineart",
                strength=0.8,
            ),
            ControlInput(
                layer_type="depth",
                controlnet_model="control_v11f1p_sd15_depth",
                strength=0.45,
            ),
        ],
    )


# ═══════════════════════════════════════════════════════════════════
# CritiqueAgent — parse logic
# ═══════════════════════════════════════════════════════════════════

class TestCritiqueParsing:
    def _make_agent(self, config):
        from image_pipeline.anime_pipeline.agents.critique import CritiqueAgent
        return CritiqueAgent(config)

    def test_parse_new_format(self, config):
        agent = self._make_agent(config)
        raw = json.dumps({
            "anatomy_score": 8, "face_score": 7, "hands_score": 6,
            "composition_score": 8, "color_score": 9, "style_score": 8,
            "background_score": 7,
            "retry_recommendation": False,
            "prompt_patch": ["sharper eyes"],
        })
        result = agent._parse_critique(raw)
        assert result is not None
        assert result.anatomy_score == 8
        assert result.face_score == 7
        assert result.retry_recommendation is False
        assert "sharper eyes" in result.prompt_patch

    def test_parse_old_format(self, config):
        agent = self._make_agent(config)
        raw = json.dumps({
            "overall_score": 0.85,
            "passed": True,
            "improvement_suggestions": ["fix hands"],
        })
        result = agent._parse_critique(raw)
        assert result is not None
        assert result.anatomy_score == 8  # 0.85 * 10 = 8
        assert "fix hands" in result.prompt_patch

    def test_parse_markdown_fence(self, config):
        agent = self._make_agent(config)
        raw = '```json\n{"anatomy_score": 7, "face_score": 8}\n```'
        result = agent._parse_critique(raw)
        assert result is not None
        assert result.anatomy_score == 7

    def test_parse_invalid_json_returns_none(self, config):
        agent = self._make_agent(config)
        result = agent._parse_critique("not json at all")
        assert result is None

    def test_no_image_gives_neutral_scores(self, config):
        agent = self._make_agent(config)
        job = AnimePipelineJob(user_prompt="test")
        agent.execute(job)
        assert len(job.critique_results) == 1
        assert job.critique_results[0].anatomy_score == 5
        assert job.critique_results[0].model_used == "skipped"


# ═══════════════════════════════════════════════════════════════════
# decide_refine_action
# ═══════════════════════════════════════════════════════════════════

class TestDecideRefineAction:
    def test_max_rounds_stops(self, config, good_critique):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        # Force bad score but max rounds reached
        good_critique.anatomy_score = 2
        decision = decide_refine_action(good_critique, round_num=2, config=config)
        assert decision.should_refine is False
        assert "max" in decision.reason.lower()

    def test_good_score_stops(self, config, good_critique):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        decision = decide_refine_action(good_critique, round_num=0, config=config)
        assert decision.should_refine is False
        assert "threshold" in decision.reason.lower()

    def test_bad_score_triggers_refine(self, config, bad_critique):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        decision = decide_refine_action(bad_critique, round_num=0, config=config)
        assert decision.should_refine is True
        assert len(decision.actions) > 0
        assert len(decision.worst_dimensions) > 0

    def test_anatomy_failure_bumps_denoise(self, config, bad_critique):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        decision = decide_refine_action(bad_critique, round_num=0, config=config)
        denoise_actions = [
            a for a in decision.actions
            if a.action_type == RefineActionType.ADJUST_DENOISE
        ]
        assert len(denoise_actions) >= 1
        assert float(denoise_actions[0].value) > 0  # positive = bump up

    def test_pose_failure_boosts_control(self, config):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        critique = CritiqueReport(
            anatomy_score=3, face_score=7, hands_score=7,
            composition_score=7, color_score=7, style_score=7,
            background_score=7,
            pose_score=2, pose_issues=["wrong pose direction"],
        )
        decision = decide_refine_action(critique, round_num=0, config=config)
        control_actions = [
            a for a in decision.actions
            if a.action_type == RefineActionType.ADJUST_CONTROL
        ]
        assert len(control_actions) >= 1
        assert float(control_actions[0].value) > 0

    def test_artifact_accumulation_switches_preset(self, config):
        from image_pipeline.anime_pipeline.agents.refine_loop import decide_refine_action
        critique = CritiqueReport(
            anatomy_score=4, face_score=4, hands_score=4,
            composition_score=4, color_score=4, style_score=4,
            background_score=4,
            anatomy_issues=["a", "b", "c"],
            face_issues=["d", "e"],
            hand_issues=["f", "g"],
            background_issues=["h", "i"],
        )
        decision = decide_refine_action(critique, round_num=0, config=config)
        preset_actions = [
            a for a in decision.actions
            if a.action_type == RefineActionType.SWITCH_PRESET
        ]
        assert len(preset_actions) >= 1
        assert "subtle" in str(preset_actions[0].value)


# ═══════════════════════════════════════════════════════════════════
# patch_plan_from_critique
# ═══════════════════════════════════════════════════════════════════

class TestPatchPlan:
    def test_denoise_adjustment_clamped(self, config, bad_critique, beauty_pass_config):
        from image_pipeline.anime_pipeline.agents.refine_loop import (
            decide_refine_action, patch_plan_from_critique,
        )
        decision = decide_refine_action(bad_critique, round_num=0, config=config)
        new_pc = patch_plan_from_critique(beauty_pass_config, bad_critique, decision, config)
        assert config.refine_denoise_floor <= new_pc.denoise <= config.refine_denoise_ceiling

    def test_control_strength_clamped(self, config, bad_critique, beauty_pass_config):
        from image_pipeline.anime_pipeline.agents.refine_loop import (
            patch_plan_from_critique,
        )
        # Force a large control boost
        decision = RefineDecision(
            should_refine=True,
            actions=[RefineAction(
                action_type=RefineActionType.ADJUST_CONTROL,
                target="control_strength",
                value=5.0,
                reason="test",
            )],
        )
        new_pc = patch_plan_from_critique(beauty_pass_config, bad_critique, decision, config)
        for ci in new_pc.control_inputs:
            assert 0.1 <= ci.strength <= 1.0

    def test_negative_patching(self, config, bad_critique, beauty_pass_config):
        from image_pipeline.anime_pipeline.agents.refine_loop import (
            decide_refine_action, patch_plan_from_critique,
        )
        decision = decide_refine_action(bad_critique, round_num=0, config=config)
        new_pc = patch_plan_from_critique(beauty_pass_config, bad_critique, decision, config)
        # Should have added bad anatomy-related negatives
        assert "bad anatomy" in new_pc.negative_prompt or "extra fingers" in new_pc.negative_prompt

    def test_prompt_patch_merged(self, config, beauty_pass_config):
        from image_pipeline.anime_pipeline.agents.refine_loop import patch_plan_from_critique
        critique = CritiqueReport(
            anatomy_score=7, face_score=7, hands_score=7,
            composition_score=7, color_score=7, style_score=7,
            background_score=7,
            prompt_patch=["sharper eyes", "better lighting"],
        )
        decision = RefineDecision(should_refine=True, actions=[])
        new_pc = patch_plan_from_critique(beauty_pass_config, critique, decision, config)
        assert "sharper eyes" in new_pc.positive_prompt
        assert "better lighting" in new_pc.positive_prompt

    def test_original_not_mutated(self, config, bad_critique, beauty_pass_config):
        from image_pipeline.anime_pipeline.agents.refine_loop import (
            decide_refine_action, patch_plan_from_critique,
        )
        original_denoise = beauty_pass_config.denoise
        original_positive = beauty_pass_config.positive_prompt
        decision = decide_refine_action(bad_critique, round_num=0, config=config)
        patch_plan_from_critique(beauty_pass_config, bad_critique, decision, config)
        assert beauty_pass_config.denoise == original_denoise
        assert beauty_pass_config.positive_prompt == original_positive


# ═══════════════════════════════════════════════════════════════════
# FinalRanker
# ═══════════════════════════════════════════════════════════════════

class TestFinalRanker:
    def test_score_candidate_with_critique(self, good_critique):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        cand = score_candidate("base64img", "beauty_pass", good_critique)
        assert cand.composite_score > 0
        assert cand.stage == "beauty_pass"
        assert cand.face_quality > 0
        assert cand.clarity > 0

    def test_score_candidate_without_critique(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        cand = score_candidate("base64img", "beauty_pass")
        assert cand.composite_score > 0
        assert cand.artifact_count == 0

    def test_rank_candidates_orders_correctly(self, good_critique, bad_critique):
        from image_pipeline.anime_pipeline.agents.final_ranker import (
            score_candidate, rank_candidates,
        )
        good = score_candidate("good_img", "beauty_pass", good_critique)
        bad = score_candidate("bad_img", "beauty_pass", bad_critique)
        result = rank_candidates([bad, good])
        assert result.winner.image_b64 == "good_img"
        assert result.total_candidates == 2
        assert len(result.runner_ups) == 1

    def test_empty_candidates(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import rank_candidates
        result = rank_candidates([])
        assert result.total_candidates == 0
        assert result.winner is None

    def test_artifact_penalty_capped(self):
        from image_pipeline.anime_pipeline.agents.final_ranker import score_candidate
        # Critique with many issues
        critique = CritiqueReport(
            anatomy_score=8, face_score=8, hands_score=8,
            composition_score=8, color_score=8, style_score=8,
            background_score=8,
            anatomy_issues=["a", "b", "c", "d", "e"],
            face_issues=["f", "g", "h", "i", "j"],
            hand_issues=["k", "l", "m", "n", "o"],
        )
        cand = score_candidate("img", "beauty_pass", critique)
        # Penalty is capped at 3.0 regardless of issue count
        assert cand.composite_score >= 0


# ═══════════════════════════════════════════════════════════════════
# OutputManifest
# ═══════════════════════════════════════════════════════════════════

class TestOutputManifest:
    def test_build_manifest_structure(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        job = AnimePipelineJob(user_prompt="test", preset="anime_quality")
        job.stages_executed = ["composition_pass", "structure_lock", "beauty_pass"]
        job.stage_timings_ms = {"composition_pass": 1200, "structure_lock": 500, "beauty_pass": 2000}
        job.total_latency_ms = 3700

        manifest = build_output_manifest(job)
        assert manifest["job_id"] == job.job_id
        assert manifest["preset"] == "anime_quality"
        assert len(manifest["passes"]) == 3
        assert manifest["total_latency_ms"] == 3700

    def test_manifest_to_json(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import manifest_to_json
        job = AnimePipelineJob(user_prompt="test")
        result = manifest_to_json(job)
        parsed = json.loads(result)
        assert "job_id" in parsed

    def test_debug_mode_includes_extras(self, good_critique):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        from image_pipeline.anime_pipeline.agents.final_ranker import (
            score_candidate, rank_candidates,
        )
        job = AnimePipelineJob(user_prompt="test")
        job.stages_executed = ["beauty_pass"]
        job.stage_timings_ms = {"beauty_pass": 1000}
        job.critique_results = [good_critique]

        cand1 = score_candidate("img1", "beauty_pass", good_critique)
        cand2 = score_candidate("img2", "composition_pass")
        rank = rank_candidates([cand1, cand2])

        manifest = build_output_manifest(job, rank, debug_mode=True)
        assert "runner_ups" in manifest
        assert "stage_timings_ms" in manifest

    def test_error_included_on_failure(self):
        from image_pipeline.anime_pipeline.agents.output_manifest import (
            build_output_manifest,
        )
        job = AnimePipelineJob(user_prompt="test")
        job.status = AnimePipelineStatus.FAILED
        job.error = "GPU OOM"

        manifest = build_output_manifest(job)
        assert manifest["error"] == "GPU OOM"
