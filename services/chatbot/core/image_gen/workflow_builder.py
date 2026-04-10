"""
ComfyUI Workflow Builder — dynamically constructs workflow JSON
with support for multiple LoRAs, VAE overrides, and various pipelines.

Replaces hardcoded workflow dicts with a composable builder approach.
"""

from __future__ import annotations

import logging
from typing import Optional

from .providers.base import ImageRequest, LoraSpec

logger = logging.getLogger(__name__)


class _NodeCounter:
    """Auto-incrementing node IDs for workflow construction."""

    def __init__(self, start: int = 100):
        self._n = start

    def next(self) -> str:
        self._n += 1
        return str(self._n)


def build_txt2img_workflow(
    req: ImageRequest,
    seed: int,
    checkpoint: str,
    vae_name: Optional[str] = None,
) -> dict:
    """
    Build a txt2img workflow with optional LoRA chain and VAE override.

    Node graph:
        CheckpointLoader → [LoRA₁ → LoRA₂ → … → LoRAₙ] → CLIPEncode(+/-) → KSampler → VAEDecode → Save
    """
    nc = _NodeCounter()
    workflow: dict = {}

    # ── 1. Checkpoint loader ────────────────────────────────────────────
    ckpt_id = nc.next()
    workflow[ckpt_id] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": checkpoint},
    }
    model_out = [ckpt_id, 0]
    clip_out = [ckpt_id, 1]
    vae_out = [ckpt_id, 2]

    # ── 2. LoRA chain ───────────────────────────────────────────────────
    model_out, clip_out = _inject_lora_chain(
        workflow, nc, model_out, clip_out, req.lora_models,
    )

    # ── 3. Optional VAE override ────────────────────────────────────────
    if vae_name:
        vae_id = nc.next()
        workflow[vae_id] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae_name},
        }
        vae_out = [vae_id, 0]

    # ── 4. Prompt encoding ──────────────────────────────────────────────
    prompt_text = _build_prompt_with_triggers(req.prompt, req.lora_models)

    pos_id = nc.next()
    workflow[pos_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt_text, "clip": clip_out},
    }
    neg_id = nc.next()
    workflow[neg_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": req.negative_prompt or "", "clip": clip_out},
    }

    # ── 5. Empty latent ─────────────────────────────────────────────────
    latent_id = nc.next()
    workflow[latent_id] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": req.width, "height": req.height, "batch_size": 1},
    }

    # ── 6. KSampler ─────────────────────────────────────────────────────
    sampler_id = nc.next()
    workflow[sampler_id] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": req.steps,
            "cfg": req.guidance,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": model_out,
            "positive": [pos_id, 0],
            "negative": [neg_id, 0],
            "latent_image": [latent_id, 0],
        },
    }

    # ── 7. VAE decode + save ────────────────────────────────────────────
    decode_id = nc.next()
    workflow[decode_id] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": [sampler_id, 0], "vae": vae_out},
    }
    save_id = nc.next()
    workflow[save_id] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "api_lora_gen", "images": [decode_id, 0]},
    }

    return workflow


def build_img2img_workflow(
    req: ImageRequest,
    seed: int,
    checkpoint: str,
    image_name: str,
    vae_name: Optional[str] = None,
) -> dict:
    """
    Build an img2img workflow with optional LoRA chain and VAE override.

    Expects the source image was already uploaded to ComfyUI via /upload/image.
    """
    nc = _NodeCounter()
    workflow: dict = {}

    # ── Load source image ───────────────────────────────────────────────
    load_id = nc.next()
    workflow[load_id] = {
        "class_type": "LoadImage",
        "inputs": {"image": image_name},
    }

    # ── Scale to target dims ────────────────────────────────────────────
    scale_id = nc.next()
    workflow[scale_id] = {
        "class_type": "ImageScale",
        "inputs": {
            "image": [load_id, 0],
            "upscale_method": "lanczos",
            "width": req.width,
            "height": req.height,
            "crop": "center",
        },
    }

    # ── Checkpoint ──────────────────────────────────────────────────────
    ckpt_id = nc.next()
    workflow[ckpt_id] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": checkpoint},
    }
    model_out = [ckpt_id, 0]
    clip_out = [ckpt_id, 1]
    vae_out = [ckpt_id, 2]

    # ── LoRA chain ──────────────────────────────────────────────────────
    model_out, clip_out = _inject_lora_chain(
        workflow, nc, model_out, clip_out, req.lora_models,
    )

    # ── VAE override ────────────────────────────────────────────────────
    if vae_name:
        vae_id = nc.next()
        workflow[vae_id] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae_name},
        }
        vae_out = [vae_id, 0]

    # ── Encode image to latent ──────────────────────────────────────────
    encode_id = nc.next()
    workflow[encode_id] = {
        "class_type": "VAEEncode",
        "inputs": {"pixels": [scale_id, 0], "vae": vae_out},
    }

    # ── Prompts ─────────────────────────────────────────────────────────
    prompt_text = _build_prompt_with_triggers(req.prompt, req.lora_models)
    pos_id = nc.next()
    workflow[pos_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt_text, "clip": clip_out},
    }
    neg_id = nc.next()
    workflow[neg_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": req.negative_prompt or "", "clip": clip_out},
    }

    # ── KSampler ────────────────────────────────────────────────────────
    sampler_id = nc.next()
    workflow[sampler_id] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": req.steps,
            "cfg": req.guidance,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": req.strength,
            "model": model_out,
            "positive": [pos_id, 0],
            "negative": [neg_id, 0],
            "latent_image": [encode_id, 0],
        },
    }

    # ── Decode + save ───────────────────────────────────────────────────
    decode_id = nc.next()
    workflow[decode_id] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": [sampler_id, 0], "vae": vae_out},
    }
    save_id = nc.next()
    workflow[save_id] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "api_lora_i2i", "images": [decode_id, 0]},
    }

    return workflow


def build_hires_fix_workflow(
    req: ImageRequest,
    seed: int,
    checkpoint: str,
    vae_name: Optional[str] = None,
    hires_scale: float = 1.5,
    hires_denoise: float = 0.45,
    hires_steps: int = 15,
) -> dict:
    """
    Two-pass hi-res fix workflow:
      Pass 1: Generate at base resolution
      Pass 2: Upscale + KSampler denoise for detail refinement

    Great for SDXL models — produces sharper details at higher resolutions.
    """
    nc = _NodeCounter()
    workflow: dict = {}

    # ── Checkpoint ──────────────────────────────────────────────────────
    ckpt_id = nc.next()
    workflow[ckpt_id] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": checkpoint},
    }
    model_out = [ckpt_id, 0]
    clip_out = [ckpt_id, 1]
    vae_out = [ckpt_id, 2]

    # ── LoRA chain ──────────────────────────────────────────────────────
    model_out, clip_out = _inject_lora_chain(
        workflow, nc, model_out, clip_out, req.lora_models,
    )

    # ── VAE override ────────────────────────────────────────────────────
    if vae_name:
        vae_id = nc.next()
        workflow[vae_id] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae_name},
        }
        vae_out = [vae_id, 0]

    # ── Prompts ─────────────────────────────────────────────────────────
    prompt_text = _build_prompt_with_triggers(req.prompt, req.lora_models)
    pos_id = nc.next()
    workflow[pos_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt_text, "clip": clip_out},
    }
    neg_id = nc.next()
    workflow[neg_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": req.negative_prompt or "", "clip": clip_out},
    }

    # ── Pass 1: Base generation ─────────────────────────────────────────
    latent_id = nc.next()
    workflow[latent_id] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": req.width, "height": req.height, "batch_size": 1},
    }
    sampler1_id = nc.next()
    workflow[sampler1_id] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": req.steps,
            "cfg": req.guidance,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": 1.0,
            "model": model_out,
            "positive": [pos_id, 0],
            "negative": [neg_id, 0],
            "latent_image": [latent_id, 0],
        },
    }

    # ── Decode pass 1 ───────────────────────────────────────────────────
    decode1_id = nc.next()
    workflow[decode1_id] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": [sampler1_id, 0], "vae": vae_out},
    }

    # ── Upscale ─────────────────────────────────────────────────────────
    upscale_id = nc.next()
    workflow[upscale_id] = {
        "class_type": "ImageScale",
        "inputs": {
            "image": [decode1_id, 0],
            "upscale_method": "lanczos",
            "width": int(req.width * hires_scale),
            "height": int(req.height * hires_scale),
            "crop": "disabled",
        },
    }

    # ── Re-encode for pass 2 ────────────────────────────────────────────
    encode2_id = nc.next()
    workflow[encode2_id] = {
        "class_type": "VAEEncode",
        "inputs": {"pixels": [upscale_id, 0], "vae": vae_out},
    }

    # ── Pass 2: Refine at higher resolution ─────────────────────────────
    sampler2_id = nc.next()
    workflow[sampler2_id] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": hires_steps,
            "cfg": req.guidance,
            "sampler_name": "euler_ancestral",
            "scheduler": "normal",
            "denoise": hires_denoise,
            "model": model_out,
            "positive": [pos_id, 0],
            "negative": [neg_id, 0],
            "latent_image": [encode2_id, 0],
        },
    }

    # ── Decode + save ───────────────────────────────────────────────────
    decode2_id = nc.next()
    workflow[decode2_id] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": [sampler2_id, 0], "vae": vae_out},
    }
    save_id = nc.next()
    workflow[save_id] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "api_hires_lora", "images": [decode2_id, 0]},
    }

    return workflow


# ── Private helpers ──────────────────────────────────────────────────────

def _inject_lora_chain(
    workflow: dict,
    nc: _NodeCounter,
    model_out: list,
    clip_out: list,
    lora_models: list[LoraSpec],
) -> tuple[list, list]:
    """
    Insert LoraLoader nodes sequentially, chaining model/clip outputs.
    Returns the final (model_out, clip_out) after all LoRAs.
    """
    if not lora_models:
        return model_out, clip_out

    for lora in lora_models:
        if not lora.name:
            continue
        node_id = nc.next()
        clip_w = lora.clip_weight if lora.clip_weight != lora.weight else lora.weight
        workflow[node_id] = {
            "class_type": "LoraLoader",
            "inputs": {
                "model": model_out,
                "clip": clip_out,
                "lora_name": lora.name,
                "strength_model": lora.weight,
                "strength_clip": clip_w,
            },
        }
        model_out = [node_id, 0]
        clip_out = [node_id, 1]
        logger.debug(f"[WorkflowBuilder] Added LoRA: {lora.name} w={lora.weight}")

    return model_out, clip_out


def _build_prompt_with_triggers(prompt: str, lora_models: list[LoraSpec]) -> str:
    """Prepend LoRA trigger words to the prompt if any are defined."""
    triggers = []
    for lora in lora_models:
        triggers.extend(lora.trigger_words)
    if not triggers:
        return prompt
    trigger_str = ", ".join(triggers)
    return f"{trigger_str}, {prompt}"
