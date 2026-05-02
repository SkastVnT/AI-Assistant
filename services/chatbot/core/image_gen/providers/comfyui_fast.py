"""Fast ComfyUI provider — SAA-style single-pass workflow.

Inspired by Character-Select-Stand-Alone-App (mirabarukaso). Uses ONE
KSampler pass instead of the multi-stage anime_pipeline. Target latency
on RTX 5070 @ 1024x1360, 30 steps: 5–15 seconds.

Workflow graph (mirrors SAA `comfyui_workflow.js`):

    CheckpointLoaderSimple
       │            │
       ├─► CLIPTextEncode (positive, with `<lora:...>` tokens stripped)
       ├─► CLIPTextEncode (negative)
       ├─► [Optional LoraLoader chain — 1 node per parsed `<lora:name:w>`]
       │
       └─► KSampler ◄─ EmptyLatentImage
              │
              ▼
           VAEDecode ──► SaveImage

Auto-strips `<lora:NAME:WEIGHT>` tokens from the prompt and converts each
to a stacked `LoraLoader` node (matches SAA's `LoRAfromText` behavior
without requiring the custom node).

Health-checks ComfyUI via `/system_stats` before submitting (audit R-1).
"""
from __future__ import annotations

import logging
import os
import re
import time
import uuid
from typing import Any, Optional

import httpx

from .base import (
    BaseImageProvider,
    ImageMode,
    ImageRequest,
    ImageResult,
    LoraSpec,
    ProviderTier,
)

logger = logging.getLogger(__name__)

# ── SAA-default knobs (override via env) ──────────────────────────────
DEFAULT_CKPT = os.getenv(
    "COMFYUI_FAST_CHECKPOINT",
    "waiIllustriousSDXL_v170.safetensors",
)
DEFAULT_W = int(os.getenv("COMFYUI_FAST_WIDTH", "1024"))
DEFAULT_H = int(os.getenv("COMFYUI_FAST_HEIGHT", "1360"))
DEFAULT_STEPS = int(os.getenv("COMFYUI_FAST_STEPS", "30"))
DEFAULT_CFG = float(os.getenv("COMFYUI_FAST_CFG", "7.0"))
DEFAULT_SAMPLER = os.getenv("COMFYUI_FAST_SAMPLER", "euler_ancestral")
DEFAULT_SCHEDULER = os.getenv("COMFYUI_FAST_SCHEDULER", "normal")
DEFAULT_NEGATIVE = os.getenv(
    "COMFYUI_FAST_NEGATIVE",
    "lowres, bad anatomy, bad hands, text, error, missing fingers, "
    "extra digit, fewer digits, cropped, worst quality, low quality, "
    "jpeg artifacts, signature, watermark, username, blurry",
)

# ── `<lora:name:weight>` parser (SAA syntax) ──────────────────────────
_LORA_TOKEN_RE = re.compile(
    r"<lora:([^:>]+?)(?::([\d.]+))?(?::([\d.]+))?>",
    re.IGNORECASE,
)


def parse_lora_tokens(prompt: str) -> tuple[str, list[LoraSpec]]:
    """Strip `<lora:name:w>` tokens from prompt; return cleaned prompt + specs."""
    specs: list[LoraSpec] = []

    def _capture(m: re.Match) -> str:
        name = m.group(1).strip()
        if not name.lower().endswith(".safetensors"):
            name = f"{name}.safetensors"
        try:
            weight = float(m.group(2)) if m.group(2) else 0.8
        except ValueError:
            weight = 0.8
        try:
            clip_w = float(m.group(3)) if m.group(3) else weight
        except ValueError:
            clip_w = weight
        specs.append(LoraSpec(name=name, weight=weight, clip_weight=clip_w))
        return ""

    cleaned = _LORA_TOKEN_RE.sub(_capture, prompt)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" ,")
    return cleaned, specs


# ── Workflow builder ──────────────────────────────────────────────────

def build_fast_workflow(
    *,
    checkpoint: str,
    positive: str,
    negative: str,
    width: int,
    height: int,
    steps: int,
    cfg: float,
    sampler: str,
    scheduler: str,
    seed: int,
    loras: list[LoraSpec],
    batch_size: int = 1,
    filename_prefix: str = "fast_saa",
) -> dict[str, Any]:
    """Build a SAA-shaped ComfyUI workflow as a dict."""
    nodes: dict[str, dict] = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        },
    }

    model_src: list = ["1", 0]
    clip_src: list = ["1", 1]

    # Stack LoraLoader nodes (sequential) — same as LoRAfromText output.
    next_id = 2
    for spec in loras:
        nid = str(next_id)
        nodes[nid] = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": spec.name,
                "strength_model": float(spec.weight),
                "strength_clip": float(spec.clip_weight or spec.weight),
                "model": model_src,
                "clip": clip_src,
            },
        }
        model_src = [nid, 0]
        clip_src = [nid, 1]
        next_id += 1

    pos_id = str(next_id); next_id += 1
    nodes[pos_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": positive, "clip": clip_src},
    }

    neg_id = str(next_id); next_id += 1
    nodes[neg_id] = {
        "class_type": "CLIPTextEncode",
        "inputs": {"text": negative, "clip": clip_src},
    }

    latent_id = str(next_id); next_id += 1
    nodes[latent_id] = {
        "class_type": "EmptyLatentImage",
        "inputs": {"width": width, "height": height, "batch_size": batch_size},
    }

    sampler_id = str(next_id); next_id += 1
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

    decode_id = str(next_id); next_id += 1
    nodes[decode_id] = {
        "class_type": "VAEDecode",
        "inputs": {"samples": [sampler_id, 0], "vae": ["1", 2]},
    }

    save_id = str(next_id)
    nodes[save_id] = {
        "class_type": "SaveImage",
        "inputs": {
            "filename_prefix": filename_prefix,
            "images": [decode_id, 0],
        },
    }
    return nodes


# ── Provider class ────────────────────────────────────────────────────

class ComfyUIFastProvider(BaseImageProvider):
    """Single-pass SAA-style ComfyUI provider. ~10s per 1024x1360 image."""

    name = "comfyui_fast"
    tier = ProviderTier.LOCAL
    supports_i2i = False
    supports_inpaint = False
    cost_per_image = 0.0

    def __init__(self, api_key: str = "", base_url: str = "", **kwargs):
        base_url = base_url or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self._http = httpx.Client(base_url=self.base_url, timeout=180.0)
        self._configured = True
        self._client_id = str(uuid.uuid4())

    # -- Health ----------------------------------------------------------
    def health_check(self) -> bool:
        try:
            r = self._http.get("/system_stats", timeout=3.0)
            return r.status_code == 200
        except Exception as e:
            logger.warning("[ComfyUIFast] health check failed: %s", e)
            return False

    # -- Generate --------------------------------------------------------
    def generate(self, req: ImageRequest) -> ImageResult:
        t0 = time.time()

        if req.mode != ImageMode.TEXT_TO_IMAGE:
            return ImageResult(
                success=False,
                provider=self.name,
                error="comfyui_fast supports only text-to-image",
            )

        if not self.health_check():
            return ImageResult(
                success=False,
                provider=self.name,
                error=f"ComfyUI not reachable at {self.base_url}",
            )

        # Merge inline `<lora:...>` tokens with explicit lora_models list.
        cleaned_prompt, parsed_loras = parse_lora_tokens(req.prompt)
        all_loras = list(req.lora_models or []) + parsed_loras

        ckpt = req.checkpoint or DEFAULT_CKPT
        seed = req.seed if req.seed is not None else int(time.time() * 1000) & 0xFFFFFFFF

        # Inject any LoRA trigger words into prompt tail.
        trigger_tail = " ".join(
            w for spec in all_loras for w in (spec.trigger_words or [])
        ).strip()
        positive = (cleaned_prompt + (", " + trigger_tail if trigger_tail else "")).strip(", ")

        workflow = build_fast_workflow(
            checkpoint=ckpt,
            positive=positive,
            negative=req.negative_prompt or DEFAULT_NEGATIVE,
            width=req.width or DEFAULT_W,
            height=req.height or DEFAULT_H,
            steps=req.steps or DEFAULT_STEPS,
            cfg=req.guidance or DEFAULT_CFG,
            sampler=req.extra.get("sampler", DEFAULT_SAMPLER),
            scheduler=req.extra.get("scheduler", DEFAULT_SCHEDULER),
            seed=seed,
            loras=all_loras,
            batch_size=max(1, req.num_images or 1),
        )

        # Submit
        try:
            r = self._http.post(
                "/prompt",
                json={"prompt": workflow, "client_id": self._client_id},
                timeout=10.0,
            )
            r.raise_for_status()
            prompt_id = r.json().get("prompt_id")
        except Exception as e:
            logger.exception("[ComfyUIFast] submit failed")
            return ImageResult(
                success=False, provider=self.name, error=f"submit failed: {e}"
            )

        if not prompt_id:
            return ImageResult(
                success=False, provider=self.name, error="no prompt_id from /prompt"
            )

        # Poll history
        max_wait = float(os.getenv("COMFYUI_FAST_MAX_WAIT", "180"))
        deadline = time.time() + max_wait
        outputs: dict | None = None
        while time.time() < deadline:
            try:
                rh = self._http.get(f"/history/{prompt_id}", timeout=10.0)
                if rh.status_code == 200:
                    payload = rh.json()
                    entry = payload.get(prompt_id)
                    if entry and entry.get("outputs"):
                        outputs = entry["outputs"]
                        break
            except Exception as e:
                logger.debug("[ComfyUIFast] poll error: %s", e)
            time.sleep(0.5)

        if outputs is None:
            return ImageResult(
                success=False,
                provider=self.name,
                error=f"timeout waiting for prompt {prompt_id} ({max_wait}s)",
            )

        # Fetch images
        images_b64: list[str] = []
        for node_out in outputs.values():
            for img in node_out.get("images", []) or []:
                try:
                    rv = self._http.get(
                        "/view",
                        params={
                            "filename": img["filename"],
                            "subfolder": img.get("subfolder", ""),
                            "type": img.get("type", "output"),
                        },
                        timeout=30.0,
                    )
                    if rv.status_code == 200:
                        import base64
                        images_b64.append(base64.b64encode(rv.content).decode("ascii"))
                except Exception as e:
                    logger.warning("[ComfyUIFast] fetch image failed: %s", e)

        if not images_b64:
            return ImageResult(
                success=False,
                provider=self.name,
                error="no images returned from /view",
            )

        latency_ms = (time.time() - t0) * 1000.0
        return ImageResult(
            success=True,
            images_b64=images_b64,
            provider=self.name,
            model=ckpt,
            prompt_used=positive,
            latency_ms=latency_ms,
            cost_usd=0.0,
            metadata={
                "prompt_id": prompt_id,
                "seed": seed,
                "steps": req.steps or DEFAULT_STEPS,
                "cfg": req.guidance or DEFAULT_CFG,
                "sampler": req.extra.get("sampler", DEFAULT_SAMPLER),
                "scheduler": req.extra.get("scheduler", DEFAULT_SCHEDULER),
                "loras_applied": [
                    {"name": s.name, "weight": s.weight} for s in all_loras
                ],
                "workflow_nodes": len(workflow),
            },
        )
