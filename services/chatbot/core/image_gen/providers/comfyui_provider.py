"""
ComfyUI provider -- local/remote ComfyUI instance.
Auto-discovers available checkpoints and builds optimized workflows
for SD 1.5 anime, SDXL, and SDXL Lightning models.

Best for: free local generation when GPU is available.
"""

from __future__ import annotations

import os
import re
import time
import json
import base64
import uuid
import logging
import httpx

from .base import (
    BaseImageProvider, ImageRequest, ImageResult,
    ImageMode, ProviderTier, LoraSpec,
)
from ..workflow_builder import (
    build_txt2img_workflow,
    build_img2img_workflow,
    build_hires_fix_workflow,
)

logger = logging.getLogger(__name__)


# -- Model profiles -------------------------------------------------------
# Each profile defines optimal generation parameters for a checkpoint.

MODEL_PROFILES: dict[str, dict] = {
    # -- SD 1.5 anime ------------------------------------------------------
    "AnythingV5Ink_ink.safetensors": {
        "type": "sd15", "style": "anime", "priority": 90,
        "res_portrait": (512, 768), "res_landscape": (768, 512), "res_square": (512, 512),
        "steps": 28, "cfg": 7.5,
        "sampler": "dpmpp_2m", "scheduler": "karras",
        "vae": "kl-f8-anime2.vae.safetensors",
        "clip_skip": 2,
    },
    "illustrij_v3.safetensors": {
        "type": "sd15", "style": "anime", "priority": 85,
        "res_portrait": (512, 768), "res_landscape": (768, 512), "res_square": (512, 512),
        "steps": 28, "cfg": 7.0,
        "sampler": "dpmpp_2m", "scheduler": "karras",
        "vae": "kl-f8-anime2.vae.safetensors",
        "clip_skip": 2,
    },
    "abyssorangemix3AOM3_aom3a1b.safetensors": {
        "type": "sd15", "style": "anime", "priority": 80,
        "res_portrait": (512, 768), "res_landscape": (768, 512), "res_square": (512, 512),
        "steps": 28, "cfg": 6.5,
        "sampler": "dpmpp_2m_sde", "scheduler": "karras",
        "vae": "orangemix.vae.pt",
        "clip_skip": 2,
    },
    "soushiki_v10.safetensors": {
        "type": "sd15", "style": "anime", "priority": 75,
        "res_portrait": (512, 768), "res_landscape": (768, 512), "res_square": (512, 512),
        "steps": 28, "cfg": 7.0,
        "sampler": "dpmpp_2m", "scheduler": "karras",
        "vae": "kl-f8-anime2.vae.safetensors",
        "clip_skip": 2,
    },
    "anythingelseV4_v45.safetensors": {
        "type": "sd15", "style": "anime", "priority": 70,
        "res_portrait": (512, 768), "res_landscape": (768, 512), "res_square": (512, 512),
        "steps": 28, "cfg": 7.0,
        "sampler": "dpmpp_2m", "scheduler": "karras",
        "vae": "kl-f8-anime2.vae.safetensors",
        "clip_skip": 2,
    },
    "abyssorangemix2SFW_abyssorangemix2Sfw.safetensors": {
        "type": "sd15", "style": "anime", "priority": 65,
        "res_portrait": (512, 768), "res_landscape": (768, 512), "res_square": (512, 512),
        "steps": 28, "cfg": 6.5,
        "sampler": "dpmpp_2m_sde", "scheduler": "karras",
        "vae": "orangemix.vae.pt",
        "clip_skip": 2,
    },
    # -- SDXL ---------------------------------------------------------------
    "flatpiececorexl_a1818.safetensors": {
        "type": "sdxl", "style": "anime", "priority": 88,
        "res_portrait": (832, 1216), "res_landscape": (1216, 832), "res_square": (1024, 1024),
        "steps": 30, "cfg": 5.0,
        "sampler": "dpmpp_2m_sde", "scheduler": "karras",
        "vae": None,
        "clip_skip": 1,
    },
    "realvisxlV50_v50LightningBakedvae.safetensors": {
        "type": "sdxl_lightning", "style": "realistic", "priority": 92,
        "res_portrait": (832, 1216), "res_landscape": (1216, 832), "res_square": (1024, 1024),
        "steps": 6, "cfg": 1.8,
        "sampler": "euler", "scheduler": "sgm_uniform",
        "vae": None,
        "clip_skip": 1,
    },
}

# Quality negative prompts per model type
NEGATIVE_SD15 = (
    "(worst quality:1.4), (low quality:1.4), (normal quality:1.2), lowres, "
    "bad anatomy, bad proportions, bad hands, missing fingers, extra fingers, "
    "fused fingers, too many fingers, poorly drawn hands, poorly drawn face, "
    "long neck, missing arms, missing legs, extra arms, extra legs, extra limbs, "
    "mutated hands, deformed, disfigured, mutation, ugly, blurry, "
    "jpeg artifacts, cropped, watermark, username, signature, text, error, "
    "3d, render, cgi"
)

NEGATIVE_SDXL = (
    "(worst quality:1.4), (low quality:1.4), lowres, blurry, jpeg artifacts, "
    "bad anatomy, bad proportions, bad hands, missing fingers, extra fingers, "
    "fused fingers, poorly drawn hands, poorly drawn face, deformed, "
    "long neck, ugly, watermark, text, error, 3d, render"
)

# LoRAs that boost detail quality — ordered by priority (first found is used)
DETAIL_LORAS_SD15 = [
    ("add_detail.safetensors", 0.35),
    ("detail_tweaker_lora.safetensors", 0.4),
    ("more_details.safetensors", 0.3),
]
ANATOMY_LORAS_SD15 = [
    ("handmix101.safetensors", 0.4),
    ("body_proportion.safetensors", 0.35),
]
EYE_LORAS_SD15 = [
    ("beautiful_detailed_eyes.safetensors", 0.3),
    ("eyecolle_cosmos_v100.safetensors", 0.25),
]

DETAIL_LORAS_SDXL = [
    ("add-detail-xl.safetensors", 0.35),
    ("anime_detailer_xl.safetensors", 0.3),
]
EYE_LORAS_SDXL = [
    ("PerfectEyesXL.safetensors", 0.3),
    ("detailed_eyes_xl.safetensors", 0.25),
    ("perfect_eyes_xl.safetensors", 0.25),
]
STYLE_LORAS_SDXL = [
    ("anime_nouveau_xl.safetensors", 0.25),
    ("pvc_style_animagine_xl_4.safetensors", 0.2),
]

# Keywords for style classification
_ANIME_KEYWORDS = re.compile(
    r"anime|manga|genshin|waifu|chibi|2d\b|illustration|ghibli|vtuber|"
    r"light novel|visual novel|manhwa|webtoon|cel[\s-]?shad|lineart|"
    r"bishoujo|shoujo|shounen|isekai",
    re.IGNORECASE,
)
_REALISTIC_KEYWORDS = re.compile(
    r"photo(?:realistic|graph)?|realistic|dslr|portrait\b|headshot|"
    r"studio\b|real\b|cinema|film|35mm|bokeh|raw photo",
    re.IGNORECASE,
)


def _classify_style(prompt: str, style_preset: str | None) -> str:
    if style_preset:
        sp = style_preset.lower()
        if sp in ("anime", "digital_art", "fantasy"):
            return "anime"
        if sp in ("photorealistic", "cinematic", "studio_photo", "noir"):
            return "realistic"
    if _ANIME_KEYWORDS.search(prompt):
        return "anime"
    if _REALISTIC_KEYWORDS.search(prompt):
        return "realistic"
    return "anime"


def _pick_resolution(profile: dict, req_w: int, req_h: int) -> tuple[int, int]:
    ratio = req_w / max(req_h, 1)
    if ratio > 1.15:
        return profile["res_landscape"]
    elif ratio < 0.87:
        return profile["res_portrait"]
    else:
        return profile["res_square"]


# -- Workflow builders -----------------------------------------------------

def _build_txt2img_workflow(
    prompt: str, negative: str,
    width: int, height: int,
    steps: int, cfg: float, seed: int,
    sampler: str, scheduler: str,
    checkpoint: str,
    vae: str | None = None,
    loras: list[tuple[str, float]] | None = None,
    upscale_to: tuple[int, int] | None = None,
    clip_skip: int = 1,
    model_type: str = "sd15",
) -> dict:
    nodes: dict = {}
    node_id = 0

    def nid():
        nonlocal node_id
        node_id += 1
        return str(node_id)

    # -- Quality tag prefix for SD1.5 anime models
    if model_type == "sd15":
        quality_prefix = "masterpiece, best quality, highly detailed, "
        if not prompt.lower().startswith(("masterpiece", "best quality")):
            prompt = quality_prefix + prompt

    # 1. Checkpoint loader
    ckpt_id = nid()
    nodes[ckpt_id] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": checkpoint},
    }
    model_src = [ckpt_id, 0]
    clip_src = [ckpt_id, 1]
    vae_src = [ckpt_id, 2]

    # 2. Optional external VAE
    if vae:
        vae_id = nid()
        nodes[vae_id] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae},
        }
        vae_src = [vae_id, 0]

    # 3. Optional LoRA stack
    if loras:
        for lora_name, strength in loras:
            lora_id = nid()
            nodes[lora_id] = {
                "class_type": "LoraLoader",
                "inputs": {
                    "lora_name": lora_name,
                    "strength_model": strength,
                    "strength_clip": strength,
                    "model": model_src,
                    "clip": clip_src,
                },
            }
            model_src = [lora_id, 0]
            clip_src = [lora_id, 1]

    # 4. CLIP skip (essential for anime SD1.5 models)
    if clip_skip > 1:
        clipskip_id = nid()
        nodes[clipskip_id] = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {"stop_at_clip_layer": -clip_skip, "clip": clip_src},
        }
        clip_src = [clipskip_id, 0]

    # 5. CLIP text encode (positive + negative)
    pos_id = nid()
    nodes[pos_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt, "clip": clip_src},
    }
    neg_id = nid()
    nodes[neg_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": clip_src},
    }

    # 6. Empty latent image
    latent_id = nid()
    nodes[latent_id] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": width, "height": height, "batch_size": 1},
    }

    # 7. KSampler (first pass)
    sampler_id = nid()
    nodes[sampler_id] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": 1.0,
            "model": model_src,
            "positive": [pos_id, 0],
            "negative": [neg_id, 0],
            "latent_image": [latent_id, 0],
        },
    }

    latent_out = [sampler_id, 0]

    # 8. Proper HiRes fix: latent upscale → second KSampler pass
    if upscale_to:
        # Upscale the latent (not the pixel image)
        latent_up_id = nid()
        nodes[latent_up_id] = {
            "class_type": "LatentUpscale",
            "inputs": {
                "samples": latent_out,
                "upscale_method": "bislerp",
                "width": upscale_to[0],
                "height": upscale_to[1],
                "crop": "disabled",
            },
        }

        # Second KSampler pass at low denoise to refine details
        hires_sampler_id = nid()
        hires_steps = max(steps // 2, 12)  # half steps for refinement
        nodes[hires_sampler_id] = {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed + 1,
                "steps": hires_steps,
                "cfg": cfg,
                "sampler_name": sampler,
                "scheduler": scheduler,
                "denoise": 0.55,
                "model": model_src,
                "positive": [pos_id, 0],
                "negative": [neg_id, 0],
                "latent_image": [latent_up_id, 0],
            },
        }
        latent_out = [hires_sampler_id, 0]

    # 9. VAE decode
    decode_id = nid()
    nodes[decode_id] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": latent_out, "vae": vae_src},
    }

    # 10. Save
    save_id = nid()
    nodes[save_id] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "api_gen", "images": [decode_id, 0]},
    }

    return nodes


def _build_img2img_workflow(
    prompt: str, negative: str,
    steps: int, cfg: float, seed: int,
    sampler: str, scheduler: str,
    strength: float,
    image_b64: str,
    checkpoint: str,
    vae: str | None = None,
) -> dict:
    nodes: dict = {}
    node_id = 0

    def nid():
        nonlocal node_id
        node_id += 1
        return str(node_id)

    # 1. Load source image
    img_id = nid()
    nodes[img_id] = {
        "class_type": "LoadImageBase64",
        "inputs": {"image": image_b64},
    }

    # 2. Checkpoint
    ckpt_id = nid()
    nodes[ckpt_id] = {
        "class_type": "CheckpointLoaderSimple",
        "inputs": {"ckpt_name": checkpoint},
    }
    model_src = [ckpt_id, 0]
    clip_src = [ckpt_id, 1]
    vae_src = [ckpt_id, 2]

    # 3. Optional external VAE
    if vae:
        vae_id = nid()
        nodes[vae_id] = {
            "class_type": "VAELoader",
            "inputs": {"vae_name": vae},
        }
        vae_src = [vae_id, 0]

    # 4. CLIP encode
    pos_id = nid()
    nodes[pos_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": prompt, "clip": clip_src},
    }
    neg_id = nid()
    nodes[neg_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": clip_src},
    }

    # 5. VAE encode source image
    enc_id = nid()
    nodes[enc_id] = {
        "class_type": "VAEEncode",
        "inputs": {"pixels": [img_id, 0], "vae": vae_src},
    }

    # 6. KSampler
    sampler_id = nid()
    nodes[sampler_id] = {
        "class_type": "KSampler",
        "inputs": {
            "seed": seed,
            "steps": steps,
            "cfg": cfg,
            "sampler_name": sampler,
            "scheduler": scheduler,
            "denoise": strength,
            "model": model_src,
            "positive": [pos_id, 0],
            "negative": [neg_id, 0],
            "latent_image": [enc_id, 0],
        },
    }

    # 7. VAE decode
    decode_id = nid()
    nodes[decode_id] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": [sampler_id, 0], "vae": vae_src},
    }

    # 8. Save
    save_id = nid()
    nodes[save_id] = {
        "class_type": "SaveImage",
        "inputs": {"filename_prefix": "api_i2i", "images": [decode_id, 0]},
    }

    return nodes


# -- Provider class --------------------------------------------------------

class ComfyUIProvider(BaseImageProvider):
    name = "comfyui"
    tier = ProviderTier.LOCAL
    supports_i2i = True
    supports_inpaint = False
    cost_per_image = 0.0

    def __init__(self, api_key: str = "", base_url: str = "", **kwargs):
        base_url = base_url or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._http = httpx.Client(base_url=self.base_url, timeout=300.0)
        self._configured = True

        self._available_ckpts: list[str] | None = None
        self._available_vaes: list[str] | None = None
        self._available_loras: list[str] | None = None

        self._force_checkpoint: str = kwargs.get("checkpoint", os.getenv("COMFYUI_CHECKPOINT", ""))
        self._upscale_factor: float = float(kwargs.get("upscale_factor", os.getenv("COMFYUI_UPSCALE_FACTOR", "1.5")))
        self._enable_loras: bool = str(kwargs.get("enable_loras", os.getenv("COMFYUI_ENABLE_LORAS", "true"))).lower() in ("true", "1", "yes")
        self._enable_hires: bool = str(kwargs.get("enable_hires", os.getenv("COMFYUI_ENABLE_HIRES", "true"))).lower() in ("true", "1", "yes")

    # -- Discovery ---------------------------------------------------------

    def _discover(self):
        if self._available_ckpts is not None:
            return

        self._available_ckpts = []
        self._available_vaes = []
        self._available_loras = []

        try:
            r = self._http.get("/object_info/CheckpointLoaderSimple", timeout=5.0)
            if r.status_code == 200:
                self._available_ckpts = (
                    r.json()
                    .get("CheckpointLoaderSimple", {})
                    .get("input", {})
                    .get("required", {})
                    .get("ckpt_name", [[]])[0]
                )
        except Exception as e:
            logger.warning(f"[ComfyUI] Failed to discover checkpoints: {e}")

        try:
            r = self._http.get("/object_info/VAELoader", timeout=5.0)
            if r.status_code == 200:
                self._available_vaes = (
                    r.json()
                    .get("VAELoader", {})
                    .get("input", {})
                    .get("required", {})
                    .get("vae_name", [[]])[0]
                )
        except Exception:
            pass

        try:
            r = self._http.get("/object_info/LoraLoader", timeout=5.0)
            if r.status_code == 200:
                self._available_loras = (
                    r.json()
                    .get("LoraLoader", {})
                    .get("input", {})
                    .get("required", {})
                    .get("lora_name", [[]])[0]
                )
        except Exception:
            pass

        logger.info(
            f"[ComfyUI] Discovered: {len(self._available_ckpts)} checkpoints, "
            f"{len(self._available_vaes)} VAEs, {len(self._available_loras)} LoRAs"
        )

    def _select_model(self, req: ImageRequest) -> tuple[str, dict]:
        self._discover()

        if self._force_checkpoint and self._force_checkpoint in self._available_ckpts:
            profile = MODEL_PROFILES.get(self._force_checkpoint)
            if profile:
                return self._force_checkpoint, profile
            return self._force_checkpoint, {
                "type": "sd15", "style": "anime", "priority": 50,
                "res_portrait": (512, 768), "res_landscape": (768, 512), "res_square": (512, 512),
                "steps": 25, "cfg": 7.0,
                "sampler": "dpmpp_2m", "scheduler": "karras",
                "vae": None,
            }

        style = _classify_style(req.prompt, req.style_preset)

        candidates = []
        for ckpt in self._available_ckpts:
            profile = MODEL_PROFILES.get(ckpt)
            if profile:
                candidates.append((ckpt, profile))

        if not candidates:
            if self._available_ckpts:
                ckpt = self._available_ckpts[0]
                logger.warning(f"[ComfyUI] No profiled model, using {ckpt}")
                return ckpt, {
                    "type": "sd15", "style": "anime", "priority": 50,
                    "res_portrait": (512, 768), "res_landscape": (768, 512), "res_square": (512, 512),
                    "steps": 25, "cfg": 7.0,
                    "sampler": "dpmpp_2m", "scheduler": "karras",
                    "vae": None,
                }
            raise RuntimeError("No checkpoints available in ComfyUI")

        style_match = [(c, p) for c, p in candidates if p["style"] == style]
        pool = style_match if style_match else candidates
        pool.sort(key=lambda x: x[1]["priority"], reverse=True)
        return pool[0]

    def _resolve_loras(self, model_type: str, style: str = "anime") -> list[tuple[str, float]]:
        """Select best available LoRAs per category (detail + anatomy + eyes + style)."""
        if not self._enable_loras or not self._available_loras:
            return []

        is_xl = model_type.startswith("sdxl")

        # Pick one LoRA from each category (first available wins)
        categories: list[list[tuple[str, float]]] = []
        if is_xl:
            categories = [DETAIL_LORAS_SDXL, EYE_LORAS_SDXL]
            if style == "anime":
                categories.append(STYLE_LORAS_SDXL)
        else:
            categories = [DETAIL_LORAS_SD15, ANATOMY_LORAS_SD15, EYE_LORAS_SD15]

        found: list[tuple[str, float]] = []
        for cat in categories:
            for lora_name, strength in cat:
                # Check both plain name and subfolder paths
                if lora_name in self._available_loras or any(
                    l.endswith(lora_name) or l.endswith("/" + lora_name) or l.endswith("\\" + lora_name)
                    for l in self._available_loras
                ):
                    # Use the matched name as ComfyUI sees it
                    matched = lora_name
                    for l in self._available_loras:
                        if l == lora_name or l.endswith("/" + lora_name) or l.endswith("\\" + lora_name):
                            matched = l
                            break
                    found.append((matched, strength))
                    break  # one per category

        # Limit to 3 LoRAs max to avoid VRAM issues
        return found[:3]

    @property
    def is_available(self) -> bool:
        return self.health_check()

    def generate(self, req: ImageRequest) -> ImageResult:
        t0 = time.time()
        client_id = str(uuid.uuid4())[:8]
        seed = req.seed if req.seed is not None else int(time.time()) % (2**32)
        has_loras = bool(req.lora_models)

        # Profile-based variables (only populated in the profile routing branch)
        model_type: str = "unknown"
        native_w: int = req.width
        native_h: int = req.height
        upscale_to = None
        vae = None
        loras: list = []

        try:
            checkpoint, profile = self._select_model(req)
            vae_name = profile.get("vae")
            if vae_name and self._available_vaes and vae_name not in self._available_vaes:
                vae_name = None

            # ── Route to appropriate workflow ────────────────────────────
            if has_loras or req.preset_id:
                # New workflow builder path — supports LoRA chains
                workflow = self._build_lora_workflow(req, seed, checkpoint, vae_name)
            else:
                model_type = profile["type"]
                native_w, native_h = _pick_resolution(profile, req.width, req.height)

                vae = profile.get("vae")
                if vae and self._available_vaes and vae not in self._available_vaes:
                    vae = None

                loras = self._resolve_loras(model_type, _classify_style(req.prompt, req.style_preset))
                negative = NEGATIVE_SDXL if model_type.startswith("sdxl") else NEGATIVE_SD15

                if self._enable_hires and model_type == "sd15":
                    target_w, target_h = req.width, req.height
                    if target_w > native_w or target_h > native_h:
                        upscale_to = (
                            min(target_w, int(native_w * self._upscale_factor)),
                            min(target_h, int(native_h * self._upscale_factor)),
                        )

                logger.info(
                    f"[ComfyUI] Generating: ckpt={checkpoint}, "
                    f"res={native_w}x{native_h}, steps={profile['steps']}, "
                    f"cfg={profile['cfg']}, sampler={profile['sampler']}, "
                    f"clip_skip={profile.get('clip_skip', 1)}, "
                    f"vae={'ext' if vae else 'built-in'}, "
                    f"loras={[l[0] for l in loras]}, "
                    f"hires={'latent→' + str(upscale_to) if upscale_to else 'none'}"
                )

                if req.mode == ImageMode.IMAGE_TO_IMAGE and req.source_image_b64:
                    workflow = _build_img2img_workflow(
                        prompt=req.prompt, negative=negative,
                        steps=profile["steps"], cfg=profile["cfg"],
                        seed=seed,
                        sampler=profile["sampler"], scheduler=profile["scheduler"],
                        strength=req.strength,
                        image_b64=req.source_image_b64,
                        checkpoint=checkpoint, vae=vae,
                    )
                else:
                    workflow = _build_txt2img_workflow(
                        prompt=req.prompt, negative=negative,
                        width=native_w, height=native_h,
                        steps=profile["steps"], cfg=profile["cfg"],
                        seed=seed,
                        sampler=profile["sampler"], scheduler=profile["scheduler"],
                        checkpoint=checkpoint, vae=vae,
                        loras=loras, upscale_to=upscale_to,
                        clip_skip=profile.get("clip_skip", 1),
                        model_type=model_type,
                    )

            resp = self._http.post("/prompt", json={
                "prompt": workflow,
                "client_id": client_id,
            })
            if resp.status_code != 200:
                logger.error("[ComfyUI] Queue failed (%d): %s", resp.status_code, resp.text[:500])
                return ImageResult(
                    success=False,
                    error=f"ComfyUI rejected workflow (status {resp.status_code})",
                    provider=self.name,
                )
            prompt_id = resp.json()["prompt_id"]

            images_b64 = self._wait_for_images(prompt_id)
            latency = (time.time() - t0) * 1000

            lora_names = [l.name for l in req.lora_models] if req.lora_models else []
            model_desc = f"comfyui/{checkpoint}"
            if lora_names:
                model_desc += "+" + "+".join(lora_names)

            return ImageResult(
                success=True,
                images_b64=images_b64,
                provider=self.name,
                model=model_desc,
                prompt_used=req.prompt,
                latency_ms=latency,
                cost_usd=0.0,
                metadata={
                    "prompt_id": prompt_id,
                    "seed": seed,
                    "checkpoint": checkpoint,
                    "preset_id": req.preset_id,
                    "model_type": model_type,
                    "resolution": f"{native_w}x{native_h}",
                    "upscaled_to": f"{upscale_to[0]}x{upscale_to[1]}" if upscale_to else None,
                    "loras": (
                        [{"name": l.name, "weight": l.weight} for l in req.lora_models]
                        if req.lora_models else [l[0] for l in loras]
                    ),
                },
            )

        except Exception as e:
            logger.error("[ComfyUI] Error during generation", exc_info=True)
            return ImageResult(success=False, error="Image generation failed", provider=self.name)

    def _build_lora_workflow(
        self, req: ImageRequest, seed: int, checkpoint: str, vae_name: str | None,
    ) -> dict:
        """Select and build the right workflow template via workflow_builder."""
        use_hires = req.extra.get("hires_fix", False)

        if req.mode == ImageMode.IMAGE_TO_IMAGE and req.source_image_b64:
            # Upload source image first
            import base64 as _b64
            img_data = req.source_image_b64
            if "," in img_data:
                img_data = img_data.split(",", 1)[1]
            img_bytes = _b64.b64decode(img_data)
            upload_resp = self._http.post(
                "/upload/image",
                files={"image": (f"input_{int(time.time()*1000)}.png", img_bytes, "image/png")},
            )
            upload_resp.raise_for_status()
            image_name = upload_resp.json().get("name", "input.png")
            return build_img2img_workflow(req, seed, checkpoint, image_name, vae_name)
        elif use_hires:
            return build_hires_fix_workflow(
                req, seed, checkpoint, vae_name,
                hires_scale=float(req.extra.get("hires_scale", 1.5)),
                hires_denoise=float(req.extra.get("hires_denoise", 0.45)),
                hires_steps=int(req.extra.get("hires_steps", 15)),
            )
        else:
            return build_txt2img_workflow(req, seed, checkpoint, vae_name)

    def get_loras(self) -> list[str]:
        """List available LoRA models from ComfyUI."""
        try:
            resp = self._http.get("/object_info/LoraLoader")
            data = resp.json()
            return data.get("LoraLoader", {}).get("input", {}).get("required", {}).get("lora_name", [[]])[0]
        except Exception:
            return []

    def _wait_for_images(self, prompt_id: str, max_wait: int = 300) -> list[str]:
        deadline = time.time() + max_wait
        while time.time() < deadline:
            resp = self._http.get(f"/history/{prompt_id}")
            if resp.status_code == 200:
                history = resp.json()
                if prompt_id in history:
                    status = history[prompt_id].get("status", {})
                    if status.get("status_str") == "error":
                        msgs = status.get("messages", [])
                        error_detail = json.dumps(msgs[:3]) if msgs else "unknown"
                        raise RuntimeError(f"ComfyUI execution error: {error_detail}")

                    outputs = history[prompt_id].get("outputs", {})
                    images = []
                    for _nid, node_out in outputs.items():
                        for img_info in node_out.get("images", []):
                            fname = img_info.get("filename")
                            subfolder = img_info.get("subfolder", "")
                            img_resp = self._http.get("/view", params={
                                "filename": fname,
                                "subfolder": subfolder,
                                "type": img_info.get("type", "output"),
                            })
                            if img_resp.status_code == 200:
                                images.append(base64.b64encode(img_resp.content).decode())
                    if images:
                        return images
            time.sleep(1.0)
        raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out after {max_wait}s")

    def health_check(self) -> bool:
        try:
            resp = self._http.get("/system_stats", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def get_models(self) -> list[str]:
        self._discover()
        return list(self._available_ckpts or [])
