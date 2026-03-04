"""
ComfyUI provider — local/remote ComfyUI instance for FLUX, SDXL, etc.
Talks to the ComfyUI API to queue prompts and retrieve generated images.
Best for: free local generation when GPU is available.
"""

from __future__ import annotations

import time
import json
import base64
import uuid
import logging
import httpx

from .base import (
    BaseImageProvider, ImageRequest, ImageResult,
    ImageMode, ProviderTier,
)

logger = logging.getLogger(__name__)


# ── Workflow templates ──────────────────────────────────────────────
def _flux_txt2img_workflow(prompt: str, width: int, height: int,
                            steps: int, guidance: float, seed: int,
                            checkpoint: str = "flux1-schnell-fp8.safetensors") -> dict:
    """Minimal FLUX txt2img workflow for ComfyUI API."""
    return {
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": guidance,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["5", 0],
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint}
        },
        "5": {
            "class_type": "EmptyLatentImage",
            "inputs": {"width": width, "height": height, "batch_size": 1}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]}
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["4", 1]}
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "api_gen", "images": ["8", 0]}
        },
    }


def _img2img_workflow(prompt: str, width: int, height: int,
                       steps: int, guidance: float, seed: int,
                       strength: float, image_b64: str,
                       checkpoint: str = "flux1-schnell-fp8.safetensors") -> dict:
    """img2img workflow with LoadImage + KSampler denoise."""
    return {
        "1": {
            "class_type": "LoadImageBase64",
            "inputs": {"image": image_b64}
        },
        "3": {
            "class_type": "KSampler",
            "inputs": {
                "seed": seed,
                "steps": steps,
                "cfg": guidance,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": strength,
                "model": ["4", 0],
                "positive": ["6", 0],
                "negative": ["7", 0],
                "latent_image": ["10", 0],
            }
        },
        "4": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint}
        },
        "6": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": prompt, "clip": ["4", 1]}
        },
        "7": {
            "class_type": "CLIPTextEncode",
            "inputs": {"text": "", "clip": ["4", 1]}
        },
        "8": {
            "class_type": "VAEDecode",
            "inputs": {"samples": ["3", 0], "vae": ["4", 2]}
        },
        "9": {
            "class_type": "SaveImage",
            "inputs": {"filename_prefix": "api_i2i", "images": ["8", 0]}
        },
        "10": {
            "class_type": "VAEEncode",
            "inputs": {"pixels": ["1", 0], "vae": ["4", 2]}
        },
    }


class ComfyUIProvider(BaseImageProvider):
    """ComfyUI local/remote — free GPU generation."""

    name = "comfyui"
    tier = ProviderTier.LOCAL
    supports_i2i = True
    supports_inpaint = False
    cost_per_image = 0.0

    def __init__(self, api_key: str = "", base_url: str = "", **kwargs):
        base_url = base_url or "http://127.0.0.1:8189"
        super().__init__(api_key=api_key, base_url=base_url, **kwargs)
        self.checkpoint = kwargs.get("checkpoint", "flux1-schnell-fp8.safetensors")
        self._http = httpx.Client(base_url=self.base_url, timeout=300.0)
        self._configured = True  # Always try local

    @property
    def is_available(self) -> bool:
        return self.health_check()

    def generate(self, req: ImageRequest) -> ImageResult:
        t0 = time.time()
        client_id = str(uuid.uuid4())[:8]
        seed = req.seed if req.seed is not None else int(time.time()) % (2**32)

        try:
            if req.mode == ImageMode.IMAGE_TO_IMAGE and req.source_image_b64:
                workflow = _img2img_workflow(
                    prompt=req.prompt, width=req.width, height=req.height,
                    steps=req.steps, guidance=req.guidance, seed=seed,
                    strength=req.strength, image_b64=req.source_image_b64,
                    checkpoint=self.checkpoint,
                )
            else:
                workflow = _flux_txt2img_workflow(
                    prompt=req.prompt, width=req.width, height=req.height,
                    steps=req.steps, guidance=req.guidance, seed=seed,
                    checkpoint=self.checkpoint,
                )

            # Queue prompt
            resp = self._http.post("/prompt", json={
                "prompt": workflow,
                "client_id": client_id,
            })
            resp.raise_for_status()
            prompt_id = resp.json()["prompt_id"]

            # Poll history
            images_b64 = self._wait_for_images(prompt_id)
            latency = (time.time() - t0) * 1000

            return ImageResult(
                success=True,
                images_b64=images_b64,
                provider=self.name,
                model=f"comfyui/{self.checkpoint}",
                prompt_used=req.prompt,
                latency_ms=latency,
                cost_usd=0.0,
                metadata={"prompt_id": prompt_id, "seed": seed},
            )

        except Exception as e:
            logger.error(f"[ComfyUI] Error: {e}", exc_info=True)
            return ImageResult(success=False, error=str(e), provider=self.name)

    def _wait_for_images(self, prompt_id: str, max_wait: int = 300) -> list[str]:
        deadline = time.time() + max_wait
        while time.time() < deadline:
            resp = self._http.get(f"/history/{prompt_id}")
            if resp.status_code == 200:
                history = resp.json()
                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    images = []
                    for node_id, node_out in outputs.items():
                        for img_info in node_out.get("images", []):
                            fname = img_info.get("filename")
                            subfolder = img_info.get("subfolder", "")
                            # Fetch actual image
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
        raise TimeoutError(f"ComfyUI prompt {prompt_id} timed out")

    def health_check(self) -> bool:
        try:
            resp = self._http.get("/system_stats", timeout=3.0)
            return resp.status_code == 200
        except Exception:
            return False

    def get_models(self) -> list[str]:
        """List available checkpoints."""
        try:
            resp = self._http.get("/object_info/CheckpointLoaderSimple")
            data = resp.json()
            return data.get("CheckpointLoaderSimple", {}).get("input", {}).get("required", {}).get("ckpt_name", [[]])[0]
        except Exception:
            return []
