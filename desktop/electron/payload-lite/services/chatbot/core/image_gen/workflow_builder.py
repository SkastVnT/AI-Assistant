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
    *,
    sampler: str = "euler_ancestral",
    scheduler: str = "normal",
    steps: Optional[int] = None,
    cfg: Optional[float] = None,
    clip_skip: int = 1,
    quality_prefix: str = "",
    negative_prompt: Optional[str] = None,
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

    # ── 3b. Optional CLIP skip (needed for SD1.5 anime models) ──────────
    if clip_skip > 1:
        clipskip_id = nc.next()
        workflow[clipskip_id] = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {"stop_at_clip_layer": -clip_skip, "clip": clip_out},
        }
        clip_out = [clipskip_id, 0]

    # ── 4. Prompt encoding ──────────────────────────────────────────────
    prompt_text = _build_prompt_with_triggers(req.prompt, req.lora_models)
    if quality_prefix and not prompt_text.lower().startswith(("masterpiece", "best quality")):
        prompt_text = quality_prefix + prompt_text

    pos_id = nc.next()
    workflow[pos_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt_text, "clip": clip_out},
    }
    neg_id = nc.next()
    eff_neg = negative_prompt if negative_prompt is not None else (req.negative_prompt or "")
    workflow[neg_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": eff_neg, "clip": clip_out},
    }

    # ── 5. Empty latent ─────────────────────────────────────────────────

    latent_id = nc.next()
    workflow[latent_id] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": req.width, "height": req.height, "batch_size": 1},
    }

    # ── 6. KSampler ─────────────────────────────────────────────────────
    eff_steps = steps if steps is not None else req.steps
    eff_cfg = cfg if cfg is not None else req.guidance
    sampler_id = nc.next()
    workflow[sampler_id] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": eff_steps,
            "cfg": eff_cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
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
    *,
    sampler: str = "euler_ancestral",
    scheduler: str = "normal",
    steps: Optional[int] = None,
    cfg: Optional[float] = None,
    clip_skip: int = 1,
    quality_prefix: str = "",
    negative_prompt: Optional[str] = None,
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

    # ── Optional CLIP skip ───────────────────────────────────────────────
    if clip_skip > 1:
        clipskip_id = nc.next()
        workflow[clipskip_id] = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {"stop_at_clip_layer": -clip_skip, "clip": clip_out},
        }
        clip_out = [clipskip_id, 0]

    # ── Prompts ─────────────────────────────────────────────────────────
    prompt_text = _build_prompt_with_triggers(req.prompt, req.lora_models)
    if quality_prefix and not prompt_text.lower().startswith(("masterpiece", "best quality")):
        prompt_text = quality_prefix + prompt_text

    pos_id = nc.next()
    workflow[pos_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt_text, "clip": clip_out},
    }
    neg_id = nc.next()
    eff_neg = negative_prompt if negative_prompt is not None else (req.negative_prompt or "")
    workflow[neg_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": eff_neg, "clip": clip_out},
    }

    # ── KSampler ────────────────────────────────────────────────────────
    eff_steps = steps if steps is not None else req.steps
    eff_cfg = cfg if cfg is not None else req.guidance
    sampler_id = nc.next()
    workflow[sampler_id] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": eff_steps,
            "cfg": eff_cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
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
    *,
    sampler: str = "euler_ancestral",
    scheduler: str = "normal",
    steps: Optional[int] = None,
    cfg: Optional[float] = None,
    clip_skip: int = 1,
    quality_prefix: str = "",
    negative_prompt: Optional[str] = None,
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

    # ── Optional CLIP skip ───────────────────────────────────────────────
    if clip_skip > 1:
        clipskip_id = nc.next()
        workflow[clipskip_id] = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {"stop_at_clip_layer": -clip_skip, "clip": clip_out},
        }
        clip_out = [clipskip_id, 0]

    # ── Prompts ─────────────────────────────────────────────────────────
    prompt_text = _build_prompt_with_triggers(req.prompt, req.lora_models)
    if quality_prefix and not prompt_text.lower().startswith(("masterpiece", "best quality")):
        prompt_text = quality_prefix + prompt_text

    pos_id = nc.next()
    workflow[pos_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt_text, "clip": clip_out},
    }
    neg_id = nc.next()
    eff_neg = negative_prompt if negative_prompt is not None else (req.negative_prompt or "")
    workflow[neg_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": eff_neg, "clip": clip_out},
    }

    # ── Pass 1: Base generation ─────────────────────────────────────────
    eff_steps = steps if steps is not None else req.steps
    eff_cfg = cfg if cfg is not None else req.guidance
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
            "steps": eff_steps,
            "cfg": eff_cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
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
            "cfg": eff_cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
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
