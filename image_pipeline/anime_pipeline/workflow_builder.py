"""
image_pipeline.anime_pipeline.workflow_builder — Build ComfyUI workflow JSON per pass.

Centralizes node ID assignment, wiring, and serialization.
Each public method returns a plain dict ready for ComfyClient.submit_workflow().
"""

from __future__ import annotations

import logging
import os
from typing import Any

from .schemas import ControlInput, PassConfig

logger = logging.getLogger(__name__)

# Import StructureLayerConfig lazily to avoid circular import at module level
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from .config import StructureLayerConfig

_WORKFLOW_VERSION = "2.0.0"


class WorkflowBuilder:
    """Builds ComfyUI workflow JSON from PassConfig objects.

    Responsibilities:
      - Assign node IDs safely (auto-incrementing counter)
      - Wire prompts, latents, samplers, VAE, save nodes
      - Attach ControlNet inputs when needed
      - Serialize workflow JSON per pass
      - Keep compatibility with common custom nodes
    """

    def __init__(self) -> None:
        self._next_id = 1

    @property
    def version(self) -> str:
        """Return current workflow builder version."""
        return _WORKFLOW_VERSION

    def _nid(self) -> str:
        """Allocate the next node ID as a string."""
        nid = str(self._next_id)
        self._next_id += 1
        return nid

    def _reset(self) -> None:
        self._next_id = 1

    # ── Composition pass ─────────────────────────────────────────────

    def build_composition(
        self,
        pc: PassConfig,
        seed: int,
        *,
        source_image_b64: str = "",
        clip_skip: int = 1,
    ) -> dict:
        """Build a composition-pass workflow: txt2img or img2img.

        Supports all pass settings: width, height, sampler, scheduler,
        steps, cfg, seed, denoise, and clip_skip.

        When ``source_image_b64`` is provided, builds an img2img pipeline
        with the pass's denoise (should be < 1.0 to preserve composition).
        Otherwise, builds a standard txt2img pipeline.

        ``clip_skip`` > 1 inserts a CLIPSetLastLayer node to skip
        the last N-1 CLIP layers — common for anime checkpoints.

        ControlNet inputs attached from ``pc.control_inputs`` are wired
        in the same way as all other builder methods.
        """
        if source_image_b64:
            return self._build_composition_img2img(
                pc, source_image_b64, seed, clip_skip,
            )
        return self._build_composition_txt2img(pc, seed, clip_skip)

    def _build_composition_txt2img(
        self, pc: PassConfig, seed: int, clip_skip: int,
    ) -> dict:
        """Composition txt2img: checkpoint → [CLIPSetLastLayer] → CLIP → latent → KSampler → VAE → Save."""
        self._reset()
        w: dict[str, Any] = {}

        ckpt = self._nid()
        w[ckpt] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": pc.checkpoint},
        }

        # Optional LoRA chain on top of base checkpoint
        model_out, clip_base = self._attach_loras(w, pc.lora_models, ckpt, ckpt)

        # CLIP skip (anime checkpoints commonly use clip_skip=2)
        clip_out = clip_base
        if clip_skip > 1:
            clip_set = self._nid()
            w[clip_set] = {
                "class_type": "CLIPSetLastLayer",
                "inputs": {
                    "clip": [clip_base, 1],
                    "stop_at_clip_layer": -clip_skip,
                },
            }
            clip_out = clip_set
            clip_slot = 0  # CLIPSetLastLayer output slot 0
        else:
            clip_slot = 1  # CheckpointLoader CLIP slot

        clip_pos = self._nid()
        w[clip_pos] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.positive_prompt, "clip": [clip_out, clip_slot]},
        }

        clip_neg = self._nid()
        w[clip_neg] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.negative_prompt, "clip": [clip_out, clip_slot]},
        }

        latent = self._nid()
        w[latent] = {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": pc.width, "height": pc.height, "batch_size": 1},
        }

        pos_out = clip_pos
        neg_out = clip_neg

        model_out, pos_out, neg_out = self._attach_controlnets(
            w, pc.control_inputs, model_out, pos_out, neg_out,
        )

        sampler = self._nid()
        w[sampler] = {
            "class_type": "KSampler",
            "inputs": {
                "model": [model_out, 0],
                "positive": [pos_out, 0],
                "negative": [neg_out, 0],
                "latent_image": [latent, 0],
                "seed": seed,
                "steps": pc.steps,
                "cfg": pc.cfg,
                "sampler_name": pc.sampler,
                "scheduler": pc.scheduler,
                "denoise": pc.denoise,
            },
        }

        vae_decode = self._nid()
        w[vae_decode] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [sampler, 0], "vae": [ckpt, 2]},
        }

        save = self._nid()
        w[save] = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"anime_pipeline/01_composition_{seed}",
                "images": [vae_decode, 0],
            },
        }

        return w

    def _build_composition_img2img(
        self, pc: PassConfig, source_b64: str, seed: int, clip_skip: int,
    ) -> dict:
        """Composition img2img: checkpoint → load source → VAE encode → KSampler → decode → save."""
        self._reset()
        w: dict[str, Any] = {}

        ckpt = self._nid()
        w[ckpt] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": pc.checkpoint},
        }

        # Optional LoRA chain on top of base checkpoint
        model_out, clip_base = self._attach_loras(w, pc.lora_models, ckpt, ckpt)

        load_img = self._nid()
        w[load_img] = {
            "class_type": "LoadImageFromBase64",
            "inputs": {"base64_image": source_b64},
        }

        vae_enc = self._nid()
        w[vae_enc] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": [load_img, 0], "vae": [ckpt, 2]},
        }

        # CLIP skip
        clip_out = clip_base
        if clip_skip > 1:
            clip_set = self._nid()
            w[clip_set] = {
                "class_type": "CLIPSetLastLayer",
                "inputs": {
                    "clip": [clip_base, 1],
                    "stop_at_clip_layer": -clip_skip,
                },
            }
            clip_out = clip_set
            clip_slot = 0
        else:
            clip_slot = 1

        clip_pos = self._nid()
        w[clip_pos] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.positive_prompt, "clip": [clip_out, clip_slot]},
        }

        clip_neg = self._nid()
        w[clip_neg] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.negative_prompt, "clip": [clip_out, clip_slot]},
        }

        pos_out = clip_pos
        neg_out = clip_neg

        model_out, pos_out, neg_out = self._attach_controlnets(
            w, pc.control_inputs, model_out, pos_out, neg_out,
        )

        sampler = self._nid()
        w[sampler] = {
            "class_type": "KSampler",
            "inputs": {
                "model": [model_out, 0],
                "positive": [pos_out, 0],
                "negative": [neg_out, 0],
                "latent_image": [vae_enc, 0],
                "seed": seed,
                "steps": pc.steps,
                "cfg": pc.cfg,
                "sampler_name": pc.sampler,
                "scheduler": pc.scheduler,
                "denoise": pc.denoise,
            },
        }

        vae_decode = self._nid()
        w[vae_decode] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [sampler, 0], "vae": [ckpt, 2]},
        }

        save = self._nid()
        w[save] = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"anime_pipeline/01_composition_i2i_{seed}",
                "images": [vae_decode, 0],
            },
        }

        return w

    # ── Structure lock preprocessor ──────────────────────────────────

    def build_structure_lock_layer(
        self,
        input_image_b64: str,
        layer_config: "StructureLayerConfig",
    ) -> dict:
        """Build preprocessor workflow for a single structure layer.

        Loads the input image, runs the ControlNet preprocessor,
        and saves the result as a debug artifact.

        Handles preprocessor-specific parameters:
        - ``resolution`` for lineart / depth / canny preprocessors
        - ``low_threshold`` / ``high_threshold`` for Canny

        The output SaveImage uses descriptive filenames:
        ``anime_pipeline/02_{layer_type}``
        """
        self._reset()
        w: dict[str, Any] = {}

        load = self._nid()
        w[load] = {
            "class_type": "LoadImageFromBase64",
            "inputs": {"base64_image": input_image_b64},
        }

        proc = self._nid()
        proc_inputs: dict[str, Any] = {"image": [load, 0]}

        # Preprocessor-specific parameters
        if layer_config.preprocessor in (
            "AnimeLineArtPreprocessor",
            "LineArtPreprocessor",
            "CannyEdgePreprocessor",
            "DepthAnythingV2Preprocessor",
        ):
            proc_inputs["resolution"] = 1024

        if layer_config.preprocessor == "CannyEdgePreprocessor":
            proc_inputs["low_threshold"] = 100
            proc_inputs["high_threshold"] = 200

        w[proc] = {
            "class_type": layer_config.preprocessor,
            "inputs": proc_inputs,
        }

        save = self._nid()
        w[save] = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"anime_pipeline/02_{layer_config.layer_type}",
                "images": [proc, 0],
            },
        }

        return w

    # ── Cleanup pass (img2img with ControlNet) ───────────────────────

    def build_cleanup(
        self,
        pc: PassConfig,
        source_image_b64: str,
        seed: int,
        *,
        clip_skip: int = 1,
    ) -> dict:
        """Build a cleanup-pass workflow: img2img with ControlNet.

        The cleanup pass runs the composition image through img2img at
        low-to-medium denoise to fix drift, stabilize shapes, and simplify
        noisy regions before the beauty pass applies final detail.

        Uses structure-lock control layers (lineart, depth) from
        ``pc.control_inputs`` to preserve pose and silhouette.

        Filename: ``anime_pipeline/03_cleanup_{seed}``
        """
        self._reset()
        w: dict[str, Any] = {}

        ckpt = self._nid()
        w[ckpt] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": pc.checkpoint},
        }

        # Optional LoRA chain on top of base checkpoint
        model_out, clip_base = self._attach_loras(w, pc.lora_models, ckpt, ckpt)

        load_img = self._nid()
        w[load_img] = {
            "class_type": "LoadImageFromBase64",
            "inputs": {"base64_image": source_image_b64},
        }

        vae_enc = self._nid()
        w[vae_enc] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": [load_img, 0], "vae": [ckpt, 2]},
        }

        # CLIP skip
        clip_out = clip_base
        if clip_skip > 1:
            clip_set = self._nid()
            w[clip_set] = {
                "class_type": "CLIPSetLastLayer",
                "inputs": {
                    "clip": [clip_base, 1],
                    "stop_at_clip_layer": -clip_skip,
                },
            }
            clip_out = clip_set
            clip_slot = 0
        else:
            clip_slot = 1

        clip_pos = self._nid()
        w[clip_pos] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.positive_prompt, "clip": [clip_out, clip_slot]},
        }

        clip_neg = self._nid()
        w[clip_neg] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.negative_prompt, "clip": [clip_out, clip_slot]},
        }

        pos_out = clip_pos
        neg_out = clip_neg

        model_out, pos_out, neg_out = self._attach_controlnets(
            w, pc.control_inputs, model_out, pos_out, neg_out,
        )

        sampler = self._nid()
        w[sampler] = {
            "class_type": "KSampler",
            "inputs": {
                "model": [model_out, 0],
                "positive": [pos_out, 0],
                "negative": [neg_out, 0],
                "latent_image": [vae_enc, 0],
                "seed": seed,
                "steps": pc.steps,
                "cfg": pc.cfg,
                "sampler_name": pc.sampler,
                "scheduler": pc.scheduler,
                "denoise": pc.denoise,
            },
        }

        vae_decode = self._nid()
        w[vae_decode] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [sampler, 0], "vae": [ckpt, 2]},
        }

        save = self._nid()
        w[save] = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"anime_pipeline/03_cleanup_{seed}",
                "images": [vae_decode, 0],
            },
        }

        return w

    # ── Beauty pass (img2img with ControlNet + clip_skip) ────────────

    def build_beauty(
        self,
        pc: PassConfig,
        source_image_b64: str,
        seed: int,
        *,
        clip_skip: int = 1,
        eye_refine_steps: int = 0,
    ) -> dict:
        """Build a beauty-pass workflow: img2img with ControlNet.

        The beauty pass runs the strongest anime checkpoint over the
        cleaned-up intermediate at low denoise to maximize detail,
        face quality, hair rendering, and material shading.

        Structure controls from ``pc.control_inputs`` are applied at
        reduced strength to preserve identity without restricting detail.

        Filename: ``anime_pipeline/04_beauty_{seed}``
        """
        self._reset()
        w: dict[str, Any] = {}

        ckpt = self._nid()
        w[ckpt] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": pc.checkpoint},
        }

        # Optional LoRA chain on top of base checkpoint
        model_out, clip_base = self._attach_loras(w, pc.lora_models, ckpt, ckpt)

        load_img = self._nid()
        w[load_img] = {
            "class_type": "LoadImageFromBase64",
            "inputs": {"base64_image": source_image_b64},
        }

        vae_enc = self._nid()
        w[vae_enc] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": [load_img, 0], "vae": [ckpt, 2]},
        }

        # CLIP skip
        clip_out = clip_base
        if clip_skip > 1:
            clip_set = self._nid()
            w[clip_set] = {
                "class_type": "CLIPSetLastLayer",
                "inputs": {
                    "clip": [clip_base, 1],
                    "stop_at_clip_layer": -clip_skip,
                },
            }
            clip_out = clip_set
            clip_slot = 0
        else:
            clip_slot = 1

        clip_pos = self._nid()
        w[clip_pos] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.positive_prompt, "clip": [clip_out, clip_slot]},
        }

        clip_neg = self._nid()
        w[clip_neg] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.negative_prompt, "clip": [clip_out, clip_slot]},
        }

        pos_out = clip_pos
        neg_out = clip_neg

        model_out, pos_out, neg_out = self._attach_controlnets(
            w, pc.control_inputs, model_out, pos_out, neg_out,
        )

        sampler = self._nid()
        w[sampler] = {
            "class_type": "KSampler",
            "inputs": {
                "model": [model_out, 0],
                "positive": [pos_out, 0],
                "negative": [neg_out, 0],
                "latent_image": [vae_enc, 0],
                "seed": seed,
                "steps": pc.steps,
                "cfg": pc.cfg,
                "sampler_name": pc.sampler,
                "scheduler": pc.scheduler,
                "denoise": pc.denoise,
            },
        }

        # Optional eye-refine micro-steps (1-3) after the main beauty pass.
        # This keeps global composition stable while adding extra micro-detail
        # around face/iris/lash regions in the latent domain.
        latent_out: list[Any] = [sampler, 0]
        micro_steps = max(0, min(int(eye_refine_steps), 3))
        for i in range(micro_steps):
            eye_sampler = self._nid()
            w[eye_sampler] = {
                "class_type": "KSampler",
                "inputs": {
                    "model": [model_out, 0],
                    "positive": [pos_out, 0],
                    "negative": [neg_out, 0],
                    "latent_image": latent_out,
                    "seed": seed + 101 + i,
                    "steps": max(8, int(pc.steps * 0.35) - (i * 2)),
                    "cfg": max(4.0, pc.cfg - 0.4),
                    "sampler_name": pc.sampler,
                    "scheduler": pc.scheduler,
                    "denoise": max(0.08, min(0.22, pc.denoise * (0.55 - i * 0.08))),
                },
            }
            latent_out = [eye_sampler, 0]

        vae_decode = self._nid()
        w[vae_decode] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": latent_out, "vae": [ckpt, 2]},
        }

        save = self._nid()
        w[save] = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"anime_pipeline/04_beauty_{seed}",
                "images": [vae_decode, 0],
            },
        }

        return w

    # ── txt2img ───────────────────────────────────────────────────────

    def build_txt2img(self, pc: PassConfig, seed: int) -> dict:
        """Standard txt2img workflow: checkpoint → CLIP → latent → KSampler → VAE → Save."""
        self._reset()
        w: dict[str, Any] = {}

        ckpt = self._nid()
        w[ckpt] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": pc.checkpoint}}

        # Optional LoRA chain on top of base checkpoint
        model_out, clip_base = self._attach_loras(w, pc.lora_models, ckpt, ckpt)

        clip_pos = self._nid()
        w[clip_pos] = {"class_type": "CLIPTextEncode", "inputs": {"text": pc.positive_prompt, "clip": [clip_base, 1]}}

        clip_neg = self._nid()
        w[clip_neg] = {"class_type": "CLIPTextEncode", "inputs": {"text": pc.negative_prompt, "clip": [clip_base, 1]}}

        latent = self._nid()
        w[latent] = {"class_type": "EmptyLatentImage", "inputs": {"width": pc.width, "height": pc.height, "batch_size": 1}}

        pos_out = clip_pos
        neg_out = clip_neg

        # ControlNet chain (if any)
        model_out, pos_out, neg_out = self._attach_controlnets(
            w, pc.control_inputs, model_out, pos_out, neg_out
        )

        sampler = self._nid()
        w[sampler] = {"class_type": "KSampler", "inputs": {
            "model": [model_out, 0], "positive": [pos_out, 0], "negative": [neg_out, 0],
            "latent_image": [latent, 0], "seed": seed, "steps": pc.steps,
            "cfg": pc.cfg, "sampler_name": pc.sampler, "scheduler": pc.scheduler,
            "denoise": pc.denoise,
        }}

        vae_decode = self._nid()
        w[vae_decode] = {"class_type": "VAEDecode", "inputs": {"samples": [sampler, 0], "vae": [ckpt, 2]}}

        save = self._nid()
        w[save] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"anime_pipeline/{pc.pass_name}_{seed}",
            "images": [vae_decode, 0],
        }}

        return w

    # ── img2img ───────────────────────────────────────────────────────

    def build_img2img(self, pc: PassConfig, source_b64: str, seed: int) -> dict:
        """img2img workflow: load source → VAE encode → KSampler → VAE decode → Save."""
        self._reset()
        w: dict[str, Any] = {}

        ckpt = self._nid()
        w[ckpt] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": pc.checkpoint}}

        # Optional LoRA chain on top of base checkpoint
        model_out, clip_base = self._attach_loras(w, pc.lora_models, ckpt, ckpt)

        load_img = self._nid()
        w[load_img] = {"class_type": "LoadImageFromBase64", "inputs": {"base64_image": source_b64}}

        vae_enc = self._nid()
        w[vae_enc] = {"class_type": "VAEEncode", "inputs": {"pixels": [load_img, 0], "vae": [ckpt, 2]}}

        clip_pos = self._nid()
        w[clip_pos] = {"class_type": "CLIPTextEncode", "inputs": {"text": pc.positive_prompt, "clip": [clip_base, 1]}}

        clip_neg = self._nid()
        w[clip_neg] = {"class_type": "CLIPTextEncode", "inputs": {"text": pc.negative_prompt, "clip": [clip_base, 1]}}

        pos_out = clip_pos
        neg_out = clip_neg

        model_out, pos_out, neg_out = self._attach_controlnets(
            w, pc.control_inputs, model_out, pos_out, neg_out
        )

        sampler = self._nid()
        w[sampler] = {"class_type": "KSampler", "inputs": {
            "model": [model_out, 0], "positive": [pos_out, 0], "negative": [neg_out, 0],
            "latent_image": [vae_enc, 0], "seed": seed, "steps": pc.steps,
            "cfg": pc.cfg, "sampler_name": pc.sampler, "scheduler": pc.scheduler,
            "denoise": pc.denoise,
        }}

        vae_decode = self._nid()
        w[vae_decode] = {"class_type": "VAEDecode", "inputs": {"samples": [sampler, 0], "vae": [ckpt, 2]}}

        save = self._nid()
        w[save] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"anime_pipeline/{pc.pass_name}_{seed}",
            "images": [vae_decode, 0],
        }}

        return w

    # ── Preprocessor (for structure lock) ─────────────────────────────

    def build_preprocessor(self, image_b64: str, preprocessor: str, pass_name: str = "structure") -> dict:
        """Preprocessor workflow: load image → preprocessor node → preview."""
        self._reset()
        w: dict[str, Any] = {}

        load = self._nid()
        w[load] = {"class_type": "LoadImageFromBase64", "inputs": {"base64_image": image_b64}}

        proc = self._nid()
        w[proc] = {"class_type": preprocessor, "inputs": {"image": [load, 0]}}

        preview = self._nid()
        w[preview] = {"class_type": "PreviewImage", "inputs": {"images": [proc, 0]}}

        return w

    # ── Upscale ───────────────────────────────────────────────────────

    def build_upscale(self, image_b64: str, upscale_model: str, pass_name: str = "upscale") -> dict:
        """Upscale workflow: load image → upscale model → save."""
        self._reset()
        w: dict[str, Any] = {}

        load = self._nid()
        w[load] = {"class_type": "LoadImageFromBase64", "inputs": {"base64_image": image_b64}}

        loader = self._nid()
        w[loader] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": upscale_model}}

        upscale = self._nid()
        w[upscale] = {"class_type": "ImageUpscaleWithModel", "inputs": {
            "upscale_model": [loader, 0], "image": [load, 0],
        }}

        save = self._nid()
        w[save] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"anime_pipeline/{pass_name}",
            "images": [upscale, 0],
        }}

        return w

    def build_simple_upscale(
        self,
        image_b64: str,
        upscale_model: str,
        target_width: int,
        target_height: int,
        pass_name: str = "upscale",
    ) -> dict:
        """Upscale with model then resize to exact target dimensions.

        Uses ImageUpscaleWithModel (always 4x for RealESRGAN) then
        ImageScale to shrink to the requested factor.
        """
        self._reset()
        w: dict[str, Any] = {}

        load = self._nid()
        w[load] = {"class_type": "LoadImageFromBase64", "inputs": {"base64_image": image_b64}}

        loader = self._nid()
        w[loader] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": upscale_model}}

        upscale = self._nid()
        w[upscale] = {"class_type": "ImageUpscaleWithModel", "inputs": {
            "upscale_model": [loader, 0], "image": [load, 0],
        }}

        rescale = self._nid()
        w[rescale] = {"class_type": "ImageScale", "inputs": {
            "image": [upscale, 0],
            "width": target_width,
            "height": target_height,
            "upscale_method": "lanczos",
            "crop": "disabled",
        }}

        save = self._nid()
        w[save] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"anime_pipeline/{pass_name}",
            "images": [rescale, 0],
        }}

        return w

    def build_ultimate_sd_upscale(
        self,
        image_b64: str,
        upscale_model: str,
        upscale_by: float,
        checkpoint: str,
        positive_prompt: str,
        negative_prompt: str,
        seed: int,
        *,
        steps: int = 20,
        cfg: float = 5.0,
        sampler: str = "euler_ancestral",
        scheduler: str = "normal",
        denoise: float = 0.2,
        tile_width: int = 512,
        tile_height: int = 512,
        pass_name: str = "upscale",
    ) -> dict:
        """Build Ultimate SD Upscale workflow.

        Tiles the image and runs img2img on each tile for detail
        enhancement during upscaling.  Requires the UltimateSDUpscale
        custom node to be installed in ComfyUI.
        """
        self._reset()
        w: dict[str, Any] = {}

        load = self._nid()
        w[load] = {"class_type": "LoadImageFromBase64", "inputs": {"base64_image": image_b64}}

        ckpt = self._nid()
        w[ckpt] = {"class_type": "CheckpointLoaderSimple", "inputs": {"ckpt_name": checkpoint}}

        clip_pos = self._nid()
        w[clip_pos] = {"class_type": "CLIPTextEncode", "inputs": {
            "text": positive_prompt, "clip": [ckpt, 1],
        }}

        clip_neg = self._nid()
        w[clip_neg] = {"class_type": "CLIPTextEncode", "inputs": {
            "text": negative_prompt, "clip": [ckpt, 1],
        }}

        up_loader = self._nid()
        w[up_loader] = {"class_type": "UpscaleModelLoader", "inputs": {"model_name": upscale_model}}

        ultimate = self._nid()
        w[ultimate] = {"class_type": "UltimateSDUpscale", "inputs": {
            "image": [load, 0],
            "model": [ckpt, 0],
            "positive": [clip_pos, 0],
            "negative": [clip_neg, 0],
            "vae": [ckpt, 2],
            "upscale_model": [up_loader, 0],
            "upscale_by": upscale_by,
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": denoise,
            "mode_type": "Linear",
            "tile_width": tile_width,
            "tile_height": tile_height,
            "mask_blur": 8,
            "tile_padding": 32,
            "seam_fix_mode": "None",
            "seam_fix_denoise": 0.0,
            "seam_fix_width": 64,
            "seam_fix_mask_blur": 8,
            "seam_fix_padding": 16,
            "force_uniform_tiles": True,
        }}

        save = self._nid()
        w[save] = {"class_type": "SaveImage", "inputs": {
            "filename_prefix": f"anime_pipeline/{pass_name}",
            "images": [ultimate, 0],
        }}

        return w

    # ── Detection inpaint pass (ADetailer-style) ────────────────────

    def build_detection_inpaint(
        self,
        pc: PassConfig,
        source_image_b64: str,
        mask_b64: str,
        seed: int,
        *,
        clip_skip: int = 1,
        region_label: str = "face",
    ) -> dict:
        """Build a masked inpaint workflow for a detected region.

        ADetailer-style: load source image → VAE encode → apply mask via
        SetLatentNoiseMask → KSampler (inpaint) → VAE decode → save.

        The mask should be a white-on-black image (white = inpaint area)
        generated by DetectionDetailAgent.

        Args:
            pc: PassConfig with region-specific prompt, denoise, steps, etc.
            source_image_b64: Base image from beauty pass (or previous inpaint).
            mask_b64: Feathered mask from YOLO detection (base64 PNG).
            seed: Random seed for the KSampler.
            clip_skip: CLIP layer skip (typically 2 for anime).
            region_label: Human-readable label (face, eyes, hand) for filename.
        """
        self._reset()
        w: dict[str, Any] = {}

        # 1. Load checkpoint
        ckpt = self._nid()
        w[ckpt] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": pc.checkpoint},
        }

        # 2. LoRA chain (region-specific LoRAs, e.g. eye LoRAs for eye detail)
        model_out, clip_base = self._attach_loras(w, pc.lora_models, ckpt, ckpt)

        # 3. Load source image
        load_img = self._nid()
        w[load_img] = {
            "class_type": "LoadImageFromBase64",
            "inputs": {"base64_image": source_image_b64},
        }

        # 4. Load mask image
        load_mask = self._nid()
        w[load_mask] = {
            "class_type": "LoadImageFromBase64",
            "inputs": {"base64_image": mask_b64},
        }

        # 5. Convert mask image to MASK type (channel 0 = red)
        img_to_mask = self._nid()
        w[img_to_mask] = {
            "class_type": "ImageToMask",
            "inputs": {
                "image": [load_mask, 0],
                "channel": "red",
            },
        }

        # 6. GrowMask — expand slightly for smoother blending
        grow_mask = self._nid()
        w[grow_mask] = {
            "class_type": "GrowMask",
            "inputs": {
                "mask": [img_to_mask, 0],
                "expand": 6,
                "tapered_corners": True,
            },
        }

        # 7. VAE encode the source image
        vae_enc = self._nid()
        w[vae_enc] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": [load_img, 0], "vae": [ckpt, 2]},
        }

        # 8. SetLatentNoiseMask — apply mask to latent for inpainting
        masked_latent = self._nid()
        w[masked_latent] = {
            "class_type": "SetLatentNoiseMask",
            "inputs": {
                "samples": [vae_enc, 0],
                "mask": [grow_mask, 0],
            },
        }

        # 9. CLIP skip
        clip_out = clip_base
        if clip_skip > 1:
            clip_set = self._nid()
            w[clip_set] = {
                "class_type": "CLIPSetLastLayer",
                "inputs": {
                    "clip": [clip_base, 1],
                    "stop_at_clip_layer": -clip_skip,
                },
            }
            clip_out = clip_set
            clip_slot = 0
        else:
            clip_slot = 1

        # 10. CLIP text encode (region-specific prompts)
        clip_pos = self._nid()
        w[clip_pos] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.positive_prompt, "clip": [clip_out, clip_slot]},
        }

        clip_neg = self._nid()
        w[clip_neg] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.negative_prompt, "clip": [clip_out, clip_slot]},
        }

        # 11. KSampler — inpaint the masked region
        sampler = self._nid()
        w[sampler] = {
            "class_type": "KSampler",
            "inputs": {
                "model": [model_out, 0],
                "positive": [clip_pos, 0],
                "negative": [clip_neg, 0],
                "latent_image": [masked_latent, 0],
                "seed": seed,
                "steps": pc.steps,
                "cfg": pc.cfg,
                "sampler_name": pc.sampler,
                "scheduler": pc.scheduler,
                "denoise": pc.denoise,
            },
        }

        # 12. VAE decode
        vae_decode = self._nid()
        w[vae_decode] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [sampler, 0], "vae": [ckpt, 2]},
        }

        # 13. Save
        save = self._nid()
        w[save] = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"anime_pipeline/05_detail_{region_label}_{seed}",
                "images": [vae_decode, 0],
            },
        }

        return w

    def build_multi_region_inpaint(
        self,
        pc: PassConfig,
        source_image_b64: str,
        masks_b64: list[str],
        seed: int,
        *,
        clip_skip: int = 1,
        region_label: str = "multi",
    ) -> dict:
        """Build inpaint for multiple regions merged into one mask.

        Useful when multiple faces or multiple hands are detected — merges
        all masks via MaskComposite then runs a single inpaint pass.

        Args:
            pc: PassConfig for the merged region.
            source_image_b64: Source image.
            masks_b64: List of feathered masks to merge.
            seed: Random seed.
            clip_skip: CLIP skip.
            region_label: Label for filename.
        """
        if len(masks_b64) == 1:
            return self.build_detection_inpaint(
                pc, source_image_b64, masks_b64[0], seed,
                clip_skip=clip_skip, region_label=region_label,
            )

        self._reset()
        w: dict[str, Any] = {}

        # 1. Checkpoint + LoRA
        ckpt = self._nid()
        w[ckpt] = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": pc.checkpoint},
        }
        model_out, clip_base = self._attach_loras(w, pc.lora_models, ckpt, ckpt)

        # 2. Load source image
        load_img = self._nid()
        w[load_img] = {
            "class_type": "LoadImageFromBase64",
            "inputs": {"base64_image": source_image_b64},
        }

        # 3. Load + merge all masks
        first_mask_loaded = None
        merged_mask_id = None

        for idx, m_b64 in enumerate(masks_b64):
            load_m = self._nid()
            w[load_m] = {
                "class_type": "LoadImageFromBase64",
                "inputs": {"base64_image": m_b64},
            }
            to_mask = self._nid()
            w[to_mask] = {
                "class_type": "ImageToMask",
                "inputs": {"image": [load_m, 0], "channel": "red"},
            }

            if idx == 0:
                merged_mask_id = to_mask
            else:
                composite = self._nid()
                w[composite] = {
                    "class_type": "MaskComposite",
                    "inputs": {
                        "destination": [merged_mask_id, 0],
                        "source": [to_mask, 0],
                        "x": 0,
                        "y": 0,
                        "operation": "add",
                    },
                }
                merged_mask_id = composite

        # 4. GrowMask
        grow_mask = self._nid()
        w[grow_mask] = {
            "class_type": "GrowMask",
            "inputs": {
                "mask": [merged_mask_id, 0],
                "expand": 6,
                "tapered_corners": True,
            },
        }

        # 5. VAE encode
        vae_enc = self._nid()
        w[vae_enc] = {
            "class_type": "VAEEncode",
            "inputs": {"pixels": [load_img, 0], "vae": [ckpt, 2]},
        }

        # 6. SetLatentNoiseMask
        masked_latent = self._nid()
        w[masked_latent] = {
            "class_type": "SetLatentNoiseMask",
            "inputs": {
                "samples": [vae_enc, 0],
                "mask": [grow_mask, 0],
            },
        }

        # 7. CLIP skip + encode
        clip_out = clip_base
        if clip_skip > 1:
            clip_set = self._nid()
            w[clip_set] = {
                "class_type": "CLIPSetLastLayer",
                "inputs": {
                    "clip": [clip_base, 1],
                    "stop_at_clip_layer": -clip_skip,
                },
            }
            clip_out = clip_set
            clip_slot = 0
        else:
            clip_slot = 1

        clip_pos = self._nid()
        w[clip_pos] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.positive_prompt, "clip": [clip_out, clip_slot]},
        }
        clip_neg = self._nid()
        w[clip_neg] = {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": pc.negative_prompt, "clip": [clip_out, clip_slot]},
        }

        # 8. KSampler
        sampler = self._nid()
        w[sampler] = {
            "class_type": "KSampler",
            "inputs": {
                "model": [model_out, 0],
                "positive": [clip_pos, 0],
                "negative": [clip_neg, 0],
                "latent_image": [masked_latent, 0],
                "seed": seed,
                "steps": pc.steps,
                "cfg": pc.cfg,
                "sampler_name": pc.sampler,
                "scheduler": pc.scheduler,
                "denoise": pc.denoise,
            },
        }

        # 9. VAE decode + save
        vae_decode = self._nid()
        w[vae_decode] = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [sampler, 0], "vae": [ckpt, 2]},
        }
        save = self._nid()
        w[save] = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": f"anime_pipeline/05_detail_{region_label}_{seed}",
                "images": [vae_decode, 0],
            },
        }

        return w

    # ── ControlNet wiring ─────────────────────────────────────────────

    def _attach_loras(
        self,
        w: dict,
        lora_models: list[dict[str, Any]],
        model_id: str,
        clip_id: str,
    ) -> tuple[str, str]:
        """Attach LoRA chain; return final (model_id, clip_id).

        Each LoRA item supports:
          - name/model/filename: safetensors filename in ComfyUI/models/loras
          - strength: both model+clip strength (fallback)
          - strength_model / strength_clip: explicit strengths
          - enabled: optional flag (default true)
        """
        current_model = model_id
        current_clip = clip_id

        for lora in lora_models or []:
            if not isinstance(lora, dict):
                continue
            if lora.get("enabled", True) is False:
                continue

            lora_name = (
                lora.get("name")
                or lora.get("model")
                or lora.get("filename")
                or ""
            )
            if not lora_name:
                continue

            strength = float(lora.get("strength", 1.0))
            strength_model = float(lora.get("strength_model", strength))
            strength_clip = float(lora.get("strength_clip", strength))

            lora_node = self._nid()
            w[lora_node] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "model": [current_model, 0],
                    "clip": [current_clip, 1],
                    "lora_name": lora_name,
                    "strength_model": strength_model,
                    "strength_clip": strength_clip,
                },
            }
            current_model = lora_node
            current_clip = lora_node

        return current_model, current_clip

    def _attach_controlnets(
        self,
        w: dict,
        controls: list[ControlInput],
        model_id: str,
        pos_id: str,
        neg_id: str,
    ) -> tuple[str, str, str]:
        """Chain ControlNet apply nodes; return final (model, pos, neg) IDs."""
        current_pos = pos_id
        current_neg = neg_id

        for ctrl in controls:
            if not ctrl.image_b64 or not ctrl.controlnet_model:
                continue

            # Load control image
            ctrl_img = self._nid()
            w[ctrl_img] = {"class_type": "LoadImageFromBase64", "inputs": {"base64_image": ctrl.image_b64}}

            # Load ControlNet model
            cn_loader = self._nid()
            w[cn_loader] = {"class_type": "ControlNetLoader", "inputs": {"control_net_name": ctrl.controlnet_model}}

            # Apply
            cn_apply = self._nid()
            w[cn_apply] = {"class_type": "ControlNetApplyAdvanced", "inputs": {
                "positive": [current_pos, 0],
                "negative": [current_neg, 0],
                "control_net": [cn_loader, 0],
                "image": [ctrl_img, 0],
                "strength": ctrl.strength,
                "start_percent": ctrl.start_percent,
                "end_percent": ctrl.end_percent,
            }}

            current_pos = cn_apply  # output 0 = positive
            current_neg = cn_apply  # output 1 = negative

        return model_id, current_pos, current_neg
