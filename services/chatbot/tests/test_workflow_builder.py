"""
Unit tests — WorkflowBuilder

Covers:
    - build_composition (txt2img): all nodes, wiring, seed, clip_skip
    - build_composition (img2img): source image, denoise < 1.0
    - build_cleanup: img2img + controlnet chaining
    - build_beauty: img2img + controlnet
    - build_txt2img / build_img2img: generic passes
    - build_structure_lock_layer: preprocessor params
    - build_upscale / build_simple_upscale / build_ultimate_sd_upscale
    - _attach_controlnets: chaining, empty list, strength/start/end
    - Node ID uniqueness across all nodes
    - _WORKFLOW_VERSION matches expected
    - Idempotent reset (repeated calls produce clean IDs)
"""

from __future__ import annotations

import sys
from pathlib import Path

_root = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_root))
sys.path.insert(0, str(_root / "services" / "chatbot"))

import pytest

from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
from image_pipeline.anime_pipeline.schemas import PassConfig, ControlInput
from image_pipeline.anime_pipeline.config import StructureLayerConfig


@pytest.fixture
def builder():
    return WorkflowBuilder()


@pytest.fixture
def composition_pc():
    return PassConfig(
        pass_name="composition",
        model_slot="composition",
        checkpoint="animagine-xl-4.0-opt.safetensors",
        width=832, height=1216,
        sampler="euler_a", scheduler="normal",
        steps=28, cfg=5.0, denoise=1.0,
        positive_prompt="masterpiece, 1girl, silver hair",
        negative_prompt="lowres, bad anatomy",
    )


@pytest.fixture
def beauty_pc():
    return PassConfig(
        pass_name="beauty",
        model_slot="final",
        checkpoint="noobai-xl-1.1.safetensors",
        width=832, height=1216,
        sampler="dpmpp_2m_sde", scheduler="karras",
        steps=28, cfg=5.5, denoise=0.30,
        positive_prompt="masterpiece, 1girl, silver hair, detailed eyes",
        negative_prompt="lowres, bad anatomy",
        control_inputs=[
            ControlInput(
                layer_type="lineart_anime",
                controlnet_model="control_v11p_sd15_lineart_anime",
                strength=0.80,
                start_percent=0.0,
                end_percent=0.80,
                image_b64="lineart_base64",
            ),
        ],
    )


SEED = 42


# ═══════════════════════════════════════════════════════════════════
# Version
# ═══════════════════════════════════════════════════════════════════

class TestVersion:
    def test_version_string(self, builder):
        assert builder.version == "2.0.0"


# ═══════════════════════════════════════════════════════════════════
# build_composition — txt2img
# ═══════════════════════════════════════════════════════════════════

class TestCompositionTxt2Img:
    def test_returns_dict(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED)
        assert isinstance(wf, dict)
        assert len(wf) > 0

    def test_has_checkpoint_loader(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED)
        loaders = [n for n in wf.values() if n["class_type"] == "CheckpointLoaderSimple"]
        assert len(loaders) == 1
        assert loaders[0]["inputs"]["ckpt_name"] == composition_pc.checkpoint

    def test_has_ksampler_with_seed(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED)
        samplers = [n for n in wf.values() if n["class_type"] == "KSampler"]
        assert len(samplers) == 1
        assert samplers[0]["inputs"]["seed"] == SEED
        assert samplers[0]["inputs"]["steps"] == composition_pc.steps
        assert samplers[0]["inputs"]["cfg"] == composition_pc.cfg

    def test_has_empty_latent(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED)
        latents = [n for n in wf.values() if n["class_type"] == "EmptyLatentImage"]
        assert len(latents) == 1
        assert latents[0]["inputs"]["width"] == composition_pc.width
        assert latents[0]["inputs"]["height"] == composition_pc.height

    def test_has_save_image(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED)
        saves = [n for n in wf.values() if n["class_type"] == "SaveImage"]
        assert len(saves) == 1
        assert "composition" in saves[0]["inputs"]["filename_prefix"]

    def test_denoise_is_full(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED)
        sampler = [n for n in wf.values() if n["class_type"] == "KSampler"][0]
        assert sampler["inputs"]["denoise"] == 1.0

    def test_clip_skip_2_adds_node(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED, clip_skip=2)
        clip_layers = [n for n in wf.values() if n["class_type"] == "CLIPSetLastLayer"]
        assert len(clip_layers) == 1
        assert clip_layers[0]["inputs"]["stop_at_clip_layer"] == -2

    def test_clip_skip_1_no_extra_node(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED, clip_skip=1)
        clip_layers = [n for n in wf.values() if n["class_type"] == "CLIPSetLastLayer"]
        assert len(clip_layers) == 0

    def test_unique_node_ids(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED)
        assert len(wf) == len(set(wf.keys()))

    def test_prompts_in_clip_encode(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED)
        encodes = [n for n in wf.values() if n["class_type"] == "CLIPTextEncode"]
        texts = {e["inputs"]["text"] for e in encodes}
        assert composition_pc.positive_prompt in texts
        assert composition_pc.negative_prompt in texts


# ═══════════════════════════════════════════════════════════════════
# build_composition — img2img
# ═══════════════════════════════════════════════════════════════════

class TestCompositionImg2Img:
    def test_returns_dict_with_source(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED, source_image_b64="base64data")
        assert isinstance(wf, dict)

    def test_has_load_image(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED, source_image_b64="base64data")
        loaders = [n for n in wf.values() if n["class_type"] == "LoadImageFromBase64"]
        assert len(loaders) == 1

    def test_has_vae_encode(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED, source_image_b64="base64data")
        encoders = [n for n in wf.values() if n["class_type"] == "VAEEncode"]
        assert len(encoders) == 1

    def test_no_empty_latent(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED, source_image_b64="base64data")
        latents = [n for n in wf.values() if n["class_type"] == "EmptyLatentImage"]
        assert len(latents) == 0

    def test_i2i_filename_prefix(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED, source_image_b64="b64")
        saves = [n for n in wf.values() if n["class_type"] == "SaveImage"]
        assert "i2i" in saves[0]["inputs"]["filename_prefix"]


# ═══════════════════════════════════════════════════════════════════
# build_cleanup
# ═══════════════════════════════════════════════════════════════════

class TestBuildCleanup:
    def test_returns_dict(self, builder, beauty_pc):
        wf = builder.build_cleanup(beauty_pc, "source_b64", SEED)
        assert isinstance(wf, dict)

    def test_has_load_image(self, builder, beauty_pc):
        wf = builder.build_cleanup(beauty_pc, "source_b64", SEED)
        loaders = [n for n in wf.values() if n["class_type"] == "LoadImageFromBase64"]
        assert len(loaders) >= 1  # source + possibly controlnet images

    def test_has_vae_encode(self, builder, beauty_pc):
        wf = builder.build_cleanup(beauty_pc, "source_b64", SEED)
        encoders = [n for n in wf.values() if n["class_type"] == "VAEEncode"]
        assert len(encoders) == 1

    def test_controlnets_attached(self, builder, beauty_pc):
        wf = builder.build_cleanup(beauty_pc, "source_b64", SEED)
        cn = [n for n in wf.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn) == 1
        assert cn[0]["inputs"]["strength"] == 0.80

    def test_cleanup_filename(self, builder, beauty_pc):
        wf = builder.build_cleanup(beauty_pc, "source_b64", SEED)
        saves = [n for n in wf.values() if n["class_type"] == "SaveImage"]
        assert "cleanup" in saves[0]["inputs"]["filename_prefix"]


# ═══════════════════════════════════════════════════════════════════
# build_beauty
# ═══════════════════════════════════════════════════════════════════

class TestBuildBeauty:
    def test_returns_dict(self, builder, beauty_pc):
        wf = builder.build_beauty(beauty_pc, "source_b64", SEED)
        assert isinstance(wf, dict)

    def test_controlnets_chained(self, builder, beauty_pc):
        wf = builder.build_beauty(beauty_pc, "source_b64", SEED)
        cn = [n for n in wf.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn) == 1

    def test_beauty_filename(self, builder, beauty_pc):
        wf = builder.build_beauty(beauty_pc, "source_b64", SEED)
        saves = [n for n in wf.values() if n["class_type"] == "SaveImage"]
        assert "beauty" in saves[0]["inputs"]["filename_prefix"]


# ═══════════════════════════════════════════════════════════════════
# build_txt2img / build_img2img (generic)
# ═══════════════════════════════════════════════════════════════════

class TestGenericBuilders:
    def test_txt2img_basic(self, builder, composition_pc):
        wf = builder.build_txt2img(composition_pc, SEED)
        assert "CheckpointLoaderSimple" in [n["class_type"] for n in wf.values()]
        assert "KSampler" in [n["class_type"] for n in wf.values()]
        assert "SaveImage" in [n["class_type"] for n in wf.values()]

    def test_img2img_basic(self, builder, composition_pc):
        wf = builder.build_img2img(composition_pc, "source_b64", SEED)
        assert "LoadImageFromBase64" in [n["class_type"] for n in wf.values()]
        assert "VAEEncode" in [n["class_type"] for n in wf.values()]


# ═══════════════════════════════════════════════════════════════════
# build_structure_lock_layer
# ═══════════════════════════════════════════════════════════════════

class TestStructureLockLayer:
    def test_lineart_preprocessor(self, builder):
        lc = StructureLayerConfig(
            layer_type="lineart_anime",
            preprocessor="AnimeLineArtPreprocessor",
        )
        wf = builder.build_structure_lock_layer("b64img", lc)
        procs = [n for n in wf.values() if n["class_type"] == "AnimeLineArtPreprocessor"]
        assert len(procs) == 1
        assert procs[0]["inputs"]["resolution"] == 1024

    def test_canny_has_thresholds(self, builder):
        lc = StructureLayerConfig(
            layer_type="canny",
            preprocessor="CannyEdgePreprocessor",
        )
        wf = builder.build_structure_lock_layer("b64img", lc)
        procs = [n for n in wf.values() if n["class_type"] == "CannyEdgePreprocessor"]
        assert procs[0]["inputs"]["low_threshold"] == 100
        assert procs[0]["inputs"]["high_threshold"] == 200

    def test_save_filename(self, builder):
        lc = StructureLayerConfig(
            layer_type="depth",
            preprocessor="DepthAnythingV2Preprocessor",
        )
        wf = builder.build_structure_lock_layer("b64img", lc)
        saves = [n for n in wf.values() if n["class_type"] == "SaveImage"]
        assert "depth" in saves[0]["inputs"]["filename_prefix"]


# ═══════════════════════════════════════════════════════════════════
# Upscale variants
# ═══════════════════════════════════════════════════════════════════

class TestUpscaleBuilders:
    def test_basic_upscale(self, builder):
        wf = builder.build_upscale("b64img", "RealESRGAN_x4plus_anime_6B")
        assert "UpscaleModelLoader" in [n["class_type"] for n in wf.values()]
        assert "ImageUpscaleWithModel" in [n["class_type"] for n in wf.values()]
        assert "SaveImage" in [n["class_type"] for n in wf.values()]

    def test_simple_upscale_has_rescale(self, builder):
        wf = builder.build_simple_upscale("b64", "RealESRGAN_x4plus_anime_6B", 1664, 2432)
        scales = [n for n in wf.values() if n["class_type"] == "ImageScale"]
        assert len(scales) == 1
        assert scales[0]["inputs"]["width"] == 1664
        assert scales[0]["inputs"]["height"] == 2432

    def test_ultimate_sd_upscale(self, builder):
        wf = builder.build_ultimate_sd_upscale(
            image_b64="b64img",
            upscale_model="RealESRGAN_x4plus_anime_6B",
            upscale_by=2.0,
            checkpoint="animagine-xl-4.0-opt.safetensors",
            positive_prompt="masterpiece",
            negative_prompt="lowres",
            seed=SEED,
        )
        nodes = [n["class_type"] for n in wf.values()]
        assert "UltimateSDUpscale" in nodes
        assert "UpscaleModelLoader" in nodes
        assert "CheckpointLoaderSimple" in nodes


# ═══════════════════════════════════════════════════════════════════
# ControlNet attachment
# ═══════════════════════════════════════════════════════════════════

class TestControlNetAttachment:
    def test_no_controls_passthrough(self, builder, composition_pc):
        wf = builder.build_composition(composition_pc, SEED)
        cn = [n for n in wf.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn) == 0

    def test_single_control(self, builder, beauty_pc):
        wf = builder.build_beauty(beauty_pc, "source", SEED)
        cn = [n for n in wf.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn) == 1
        assert cn[0]["inputs"]["strength"] == 0.80
        assert cn[0]["inputs"]["start_percent"] == 0.0
        assert cn[0]["inputs"]["end_percent"] == 0.80

    def test_multiple_controls(self, builder):
        pc = PassConfig(
            pass_name="beauty",
            model_slot="final",
            checkpoint="test.safetensors",
            width=832, height=1216,
            sampler="euler_a", scheduler="normal",
            steps=20, cfg=5.0, denoise=0.30,
            positive_prompt="test",
            negative_prompt="bad",
            control_inputs=[
                ControlInput(
                    layer_type="lineart", controlnet_model="cn_lineart",
                    strength=0.8, image_b64="la_b64",
                ),
                ControlInput(
                    layer_type="depth", controlnet_model="cn_depth",
                    strength=0.5, image_b64="depth_b64",
                ),
            ],
        )
        wf = builder.build_beauty(pc, "source", SEED)
        cn = [n for n in wf.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn) == 2

    def test_control_without_image_skipped(self, builder):
        pc = PassConfig(
            pass_name="beauty",
            model_slot="final",
            checkpoint="test.safetensors",
            width=832, height=1216,
            sampler="euler_a", scheduler="normal",
            steps=20, cfg=5.0, denoise=0.30,
            positive_prompt="test",
            negative_prompt="bad",
            control_inputs=[
                ControlInput(
                    layer_type="lineart", controlnet_model="cn_lineart",
                    strength=0.8,
                    # no image_b64
                ),
            ],
        )
        wf = builder.build_beauty(pc, "source", SEED)
        cn = [n for n in wf.values() if n["class_type"] == "ControlNetApplyAdvanced"]
        assert len(cn) == 0


# ═══════════════════════════════════════════════════════════════════
# Idempotency
# ═══════════════════════════════════════════════════════════════════

class TestIdempotency:
    def test_repeated_calls_reset_ids(self, builder, composition_pc):
        wf1 = builder.build_composition(composition_pc, SEED)
        wf2 = builder.build_composition(composition_pc, SEED)
        assert set(wf1.keys()) == set(wf2.keys())
        assert wf1 == wf2

    def test_different_passes_start_fresh(self, builder, composition_pc):
        wf1 = builder.build_txt2img(composition_pc, SEED)
        wf2 = builder.build_img2img(composition_pc, "src", SEED)
        # Both should start from ID "1"
        assert "1" in wf1
        assert "1" in wf2
