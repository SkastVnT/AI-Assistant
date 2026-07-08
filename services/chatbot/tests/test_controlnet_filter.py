"""
Unit tests — ControlNet submit-time guards + prompt-gated effect LoRAs
+ legacy manifest dedup.

Covers the fixes for the "beauty pass crash" incident (job a0cc2caa):
    - guess_model_family: SD family detection from model filenames
    - ComfyClient._filter_incompatible_controlnets:
        * drops ControlNets missing from ComfyUI's live list
          (HTTP 400 ``value_not_in_list`` at submit)
        * drops family-mismatched ControlNets (SD1.5 model on SDXL checkpoint)
        * rewires conditioning through removed apply nodes
        * prunes orphaned control-image loaders
    - detection_inpaint effect-LoRA gating: effects/<sub>/ LoRAs only attach
      when the prompt actually asks for the effect (no more ~14 off-topic
      mouth LoRAs on a gentle closed-mouth smile)
    - ResultStore.save_manifest legacy branch: one pass row per stage with a
      ``runs`` count instead of duplicated rows
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "services" / "chatbot"))

import pytest

from image_pipeline.anime_pipeline.comfy_client import (
    ComfyClient,
    guess_model_family,
)
from image_pipeline.anime_pipeline.agents import detection_inpaint as di
from image_pipeline.anime_pipeline.result_store import ResultStore
from image_pipeline.anime_pipeline.schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
)


# ═══════════════════════════════════════════════════════════════════
# guess_model_family
# ═══════════════════════════════════════════════════════════════════


class TestGuessModelFamily:
    @pytest.mark.parametrize(
        "name",
        [
            "waiIllustriousSDXL_v170.safetensors",
            "xinsir-controlnet-union-sdxl-1.0.safetensors",
            "kohya_controllllite_xl_canny.safetensors",
            "ponyDiffusionV6XL.safetensors",
            "noobaiXLNAIXL_epsilonPred11.safetensors",
        ],
    )
    def test_sdxl_names(self, name):
        assert guess_model_family(name) == "sdxl"

    @pytest.mark.parametrize(
        "name",
        [
            "control_v11p_sd15_lineart_anime",
            "control_v11f1p_sd15_depth",
            "mouthpull_sd15.safetensors",
            "meinamix_sd1.5.safetensors",
        ],
    )
    def test_sd15_names(self, name):
        assert guess_model_family(name) == "sd15"

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "meinamix_v12.safetensors",  # no family marker
            "pixel_art_style.safetensors",  # "xl" must not match inside "pixel"
            "CN-anytest_v4.safetensors",
        ],
    )
    def test_unknown_names(self, name):
        assert guess_model_family(name) == ""


# ═══════════════════════════════════════════════════════════════════
# ComfyClient._filter_incompatible_controlnets
# ═══════════════════════════════════════════════════════════════════

SDXL_CKPT = "waiIllustriousSDXL_v170.safetensors"
SD15_CN = "control_v11p_sd15_lineart_anime"
SDXL_CN = "xinsir-controlnet-union-sdxl-1.0.safetensors"


def _cn_workflow(cn_name: str, ckpt: str = SDXL_CKPT, with_union: bool = False):
    """Minimal img2img workflow with one ControlNet chain (builder shape)."""
    wf = {
        "1": {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": ckpt}},
        "2": {"class_type": "LoadImageFromBase64", "inputs": {"base64_image": "src"}},
        "3": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["2", 0], "vae": ["1", 2]},
        },
        "4": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "1girl", "clip": ["1", 1]},
        },
        "5": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "lowres", "clip": ["1", 1]},
        },
        "6": {"class_type": "LoadImageFromBase64", "inputs": {"base64_image": "ctrl"}},
        "7": {"class_type": "ControlNetLoader", "inputs": {"control_net_name": cn_name}},
    }
    cn_out = "7"
    if with_union:
        wf["10"] = {
            "class_type": "SetUnionControlNetType",
            "inputs": {"control_net": ["7", 0], "type": "depth"},
        }
        cn_out = "10"
    wf["8"] = {
        "class_type": "ControlNetApplyAdvanced",
        "inputs": {
            "positive": ["4", 0],
            "negative": ["5", 0],
            "control_net": [cn_out, 0],
            "image": ["6", 0],
            "strength": 0.8,
            "start_percent": 0.0,
            "end_percent": 0.8,
        },
    }
    wf["9"] = {
        "class_type": "KSampler",
        "inputs": {
            "model": ["1", 0],
            "positive": ["8", 0],
            "negative": ["8", 1],
            "latent_image": ["3", 0],
            "seed": 42,
            "steps": 28,
            "cfg": 5.0,
            "sampler_name": "euler_a",
            "scheduler": "normal",
            "denoise": 0.3,
        },
    }
    return wf


@pytest.fixture
def client():
    return ComfyClient(base_url="http://localhost:9999")


class TestFilterIncompatibleControlnets:
    def test_family_mismatch_dropped_even_when_installed(self, client):
        wf = _cn_workflow(SD15_CN)
        filtered, dropped = client._filter_incompatible_controlnets(
            wf, available={SD15_CN, SDXL_CN}
        )
        assert len(dropped) == 1
        assert SD15_CN in dropped[0]
        assert "sd15" in dropped[0] and "sdxl" in dropped[0]
        # Loader, apply, and orphaned control image are gone
        assert "7" not in filtered and "8" not in filtered and "6" not in filtered
        # Sampler rewired straight to the CLIP encoders
        assert filtered["9"]["inputs"]["positive"] == ["4", 0]
        assert filtered["9"]["inputs"]["negative"] == ["5", 0]

    def test_not_installed_dropped(self, client):
        wf = _cn_workflow(SDXL_CN)  # family matches, but not installed
        filtered, dropped = client._filter_incompatible_controlnets(
            wf, available={"some_other_cn.safetensors"}
        )
        assert len(dropped) == 1
        assert "not installed" in dropped[0]
        assert "7" not in filtered
        assert filtered["9"]["inputs"]["negative"] == ["5", 0]

    def test_family_mismatch_dropped_when_list_unavailable(self, client):
        # ComfyUI list fetch failed (empty set) → availability check skipped,
        # but the family mismatch is still caught.
        wf = _cn_workflow(SD15_CN)
        filtered, dropped = client._filter_incompatible_controlnets(wf, available=set())
        assert len(dropped) == 1
        assert "8" not in filtered

    def test_compatible_installed_kept(self, client):
        wf = _cn_workflow(SDXL_CN)
        filtered, dropped = client._filter_incompatible_controlnets(
            wf, available={SDXL_CN}
        )
        assert dropped == []
        assert filtered is wf  # untouched, no copy

    def test_sd15_on_sd15_kept(self, client):
        wf = _cn_workflow(SD15_CN, ckpt="meinamix_sd15.safetensors")
        filtered, dropped = client._filter_incompatible_controlnets(
            wf, available={SD15_CN}
        )
        assert dropped == []

    def test_union_node_removed_with_loader(self, client):
        wf = _cn_workflow(SD15_CN, with_union=True)
        filtered, dropped = client._filter_incompatible_controlnets(
            wf, available={SD15_CN}
        )
        assert len(dropped) == 1
        assert "10" not in filtered  # SetUnionControlNetType gone too
        assert filtered["9"]["inputs"]["positive"] == ["4", 0]

    def test_chain_rewired_through_removed_apply(self, client):
        # Two chained applies: first good (SDXL), second bad (SD1.5).
        wf = _cn_workflow(SDXL_CN)
        wf["11"] = {
            "class_type": "LoadImageFromBase64", "inputs": {"base64_image": "c2"}
        }
        wf["12"] = {
            "class_type": "ControlNetLoader",
            "inputs": {"control_net_name": SD15_CN},
        }
        wf["13"] = {
            "class_type": "ControlNetApplyAdvanced",
            "inputs": {
                "positive": ["8", 0],
                "negative": ["8", 1],
                "control_net": ["12", 0],
                "image": ["11", 0],
                "strength": 0.5,
                "start_percent": 0.0,
                "end_percent": 0.6,
            },
        }
        wf["9"]["inputs"]["positive"] = ["13", 0]
        wf["9"]["inputs"]["negative"] = ["13", 1]

        filtered, dropped = client._filter_incompatible_controlnets(
            wf, available={SDXL_CN, SD15_CN}
        )
        assert len(dropped) == 1
        # Good chain survives; sampler rewired back to the surviving apply
        assert "8" in filtered
        assert "13" not in filtered and "12" not in filtered and "11" not in filtered
        assert filtered["9"]["inputs"]["positive"] == ["8", 0]
        assert filtered["9"]["inputs"]["negative"] == ["8", 1]

    def test_workflow_without_controlnets_untouched(self, client):
        wf = {
            "1": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {"ckpt_name": SDXL_CKPT},
            },
        }
        filtered, dropped = client._filter_incompatible_controlnets(wf, available=set())
        assert filtered is wf
        assert dropped == []


# ═══════════════════════════════════════════════════════════════════
# Prompt-gated effect LoRAs (detection_inpaint)
# ═══════════════════════════════════════════════════════════════════


class TestEffectLoraGating:
    @pytest.fixture
    def candidates(self, monkeypatch):
        cands = {
            "mouth": [
                {
                    "name": "effects/mouth/mouthpull_sd15.safetensors",
                    "strength_model": 0.45,
                    "strength_clip": 0.35,
                    "_match_terms": ("mouth pull", "mouthpull", "finger in own mouth"),
                },
                {
                    "name": "effects/drool/pearly_drool.safetensors",
                    "strength_model": 0.45,
                    "strength_clip": 0.35,
                    "_match_terms": ("drool", "saliva"),
                },
                {
                    "name": "effects/expression/ahegao_xl.safetensors",
                    "strength_model": 0.45,
                    "strength_clip": 0.35,
                    "_match_terms": ("ahegao",),
                },
            ],
        }
        monkeypatch.setattr(di, "_AUTO_EFFECT_LORAS", cands)
        return cands

    def test_gentle_smile_attaches_nothing(self, candidates):
        # The exact incident scenario: gentle closed-mouth smile must not
        # pull in mouthpull/drool/ahegao LoRAs.
        prompt = "1girl, nahida, gentle smile, closed mouth, green hair"
        assert di.effect_loras_for_prompt("mouth", prompt) == []

    def test_matching_prompt_attaches_with_terms_stripped(self, candidates):
        result = di.effect_loras_for_prompt("mouth", "1girl, drooling, tongue out")
        assert len(result) == 1
        assert result[0]["name"] == "effects/drool/pearly_drool.safetensors"
        assert "_match_terms" not in result[0]

    def test_underscore_prompt_tag_matches(self, candidates):
        # danbooru-style tags use underscores; matching is normalized
        result = di.effect_loras_for_prompt("mouth", "1girl, mouth_pull, pov")
        assert [Path(r["name"]).name for r in result] == [
            "mouthpull_sd15.safetensors"
        ]

    def test_cap_applies(self, candidates):
        prompt = "1girl, ahegao, drooling, mouth pull"
        result = di.effect_loras_for_prompt("mouth", prompt)
        assert len(result) == di._AUTO_EFFECT_MAX_PER_REGION

    def test_unknown_region_or_empty_prompt(self, candidates):
        assert di.effect_loras_for_prompt("hand", "drool") == []
        assert di.effect_loras_for_prompt("mouth", "") == []


class TestFilenameMatchTerms:
    def test_generic_and_family_tokens_excluded(self):
        terms = di._filename_match_terms("mouthpull_sd15.safetensors", "mouth")
        assert "mouthpull" in terms
        assert "sd15" not in terms
        assert "mouth" not in terms  # stoplisted — too generic to gate on

    def test_subfolder_used_when_specific(self):
        terms = di._filename_match_terms("v2_final.safetensors", "drool")
        assert terms == ("drool",)

    def test_nothing_specific_yields_empty(self):
        # Only generic/packaging tokens → no safe gate → candidate skipped
        assert di._filename_match_terms("sd15_final_v10.safetensors", "mouth") == ()


# ═══════════════════════════════════════════════════════════════════
# Legacy manifest dedup (ResultStore.save_manifest without rank_result)
# ═══════════════════════════════════════════════════════════════════


class TestLegacyManifestDedup:
    def test_repeated_stages_collapse_to_runs(self, tmp_path):
        store = ResultStore(
            base_dir=tmp_path / "inter",
            metadata_dir=tmp_path / "meta",
        )
        job = AnimePipelineJob(job_id="testdedup01", user_prompt="1girl")
        job.status = AnimePipelineStatus.COMPLETED
        # Replan look-alike: same stages appended twice
        for _ in range(2):
            job.add_intermediate("layer_planning", "aW1n")
            job.add_intermediate(
                "composition_pass", "aW1n", checkpoint="waiIllustriousSDXL.safetensors"
            )
        job.add_intermediate("beauty_pass", "aW1n")
        job.mark_stage("layer_planning", 9.1)
        job.mark_stage("composition_pass", 48644.5)
        job.mark_stage("beauty_pass", 45047.2)

        path = store.save_manifest(job)  # rank_result=None → legacy branch
        manifest = json.loads(Path(path).read_text(encoding="utf-8"))

        names = [p["name"] for p in manifest["passes"]]
        assert names == ["layer_planning", "composition_pass", "beauty_pass"]
        by_name = {p["name"]: p for p in manifest["passes"]}
        assert by_name["layer_planning"]["runs"] == 2
        assert by_name["composition_pass"]["runs"] == 2
        assert "runs" not in by_name["beauty_pass"]
        assert (
            by_name["composition_pass"]["model"]
            == "waiIllustriousSDXL.safetensors"
        )
