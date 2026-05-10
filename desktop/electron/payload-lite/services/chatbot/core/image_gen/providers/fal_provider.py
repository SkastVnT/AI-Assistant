"""
fal.ai provider â€” fastest inference engine for diffusion models.
Supports FLUX.2, FLUX.1-Kontext, Seedream, Nano-Banana, and more.
"""

from __future__ import annotations

import time
import base64
import logging
import httpx
from typing import Optional

from .base import (
    BaseImageProvider, ImageRequest, ImageResult,
    ImageMode, ProviderTier,
)

logger = logging.getLogger(__name__)

# fal.ai model catalog â€” map friendly names to endpoints
FAL_MODELS = {
    # FLUX.2 family (latest, best)
    "flux2-dev":        "fal-ai/flux-2-dev",
    "flux2-pro":        "fal-ai/flux-2-pro",
    "flux2-klein-4b":   "fal-ai/flux-2-klein-4b",     # sub-second, $0.003/img
    "flux2-klein-9b":   "fal-ai/flux-2-klein-9b",
    # FLUX.1 family
    "flux1-dev":        "fal-ai/flux/dev",
    "flux1-schnell":    "fal-ai/flux/schnell",
    "flux1-kontext":    "fal-ai/flux-kontext/dev",      # img2img editing
    # Other top models
    "seedream5":        "fal-ai/seedream-5-lite",       # ByteDance, reasoning
    "nano-banana":      "fal-ai/nano-banana",           # Google Pro alias
    "nano-banana-pro":  "fal-ai/nano-banana",           # Google Pro
    "nano-banana-2":    "fal-ai/nano-banana-2",         # Google, fast
    "recraft-v4":       "fal-ai/recraft-v4",            # Design taste
}

FAL_COST = {
    "flux2-dev":        0.025,
    "flux2-pro":        0.055,
    "flux2-klein-4b":   0.003,
    "flux2-klein-9b":   0.012,
    "flux1-dev":        0.025,
    "flux1-schnell":    0.003,
    "flux1-kontext":    0.025,
    "seedream5":        0.020,
    "nano-banana":      0.011,
    "nano-banana-pro":  0.011,
    "nano-banana-2":    0.005,
    "recraft-v4":       0.020,
}


class FalProvider(BaseImageProvider):
    """fal.ai â€” fastest diffusion inference, huge model catalog."""

    name = "fal"
    tier = ProviderTier.HIGH
    supports_i2i = True
    supports_inpaint = True

    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.default_model = kwargs.get("default_model", "flux1-dev")
        self._http = httpx.Client(
            base_url="https://queue.fal.run",
            headers={
                "Authorization": f"Key {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    @property
    def cost_per_image(self) -> float:
        return FAL_COST.get(self.default_model, 0.025)

    def generate(self, req: ImageRequest) -> ImageResult:
        model_key = req.extra.get("model", self.default_model)
        endpoint = FAL_MODELS.get(model_key)
        if not endpoint:
            return ImageResult(success=False, error=f"Unknown fal model: {model_key}")

        t0 = time.time()

        try:
            payload = self._build_payload(req, model_key)
            
            # Submit to queue
            submit_resp = self._http.post(f"/{endpoint}", json=payload)
            submit_resp.raise_for_status()
            submit_data = submit_resp.json()
            
            # fal returns status_url / response_url directly — prefer those
            if "request_id" in submit_data:
                result_data = self._poll_result(
                    endpoint,
                    submit_data["request_id"],
                    status_url=submit_data.get("status_url"),
                    response_url=submit_data.get("response_url"),
                )
            else:
                result_data = submit_data

            images_url = self._extract_images(result_data)
            latency = (time.time() - t0) * 1000

            return ImageResult(
                success=True,
                images_url=images_url,
                provider=self.name,
                model=model_key,
                prompt_used=req.prompt,
                latency_ms=latency,
                cost_usd=FAL_COST.get(model_key, 0.025) * max(1, len(images_url)),
                metadata={"fal_endpoint": endpoint, "raw_response_keys": list(result_data.keys())},
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"[fal] HTTP {e.response.status_code}: {e.response.text[:500]}")
            return ImageResult(success=False, error=f"fal API error: {e.response.status_code}", provider=self.name)
        except Exception as e:
            logger.error(f"[fal] Error: {e}", exc_info=True)
            return ImageResult(success=False, error=str(e), provider=self.name)

    def _build_payload(self, req: ImageRequest, model_key: str) -> dict:
        """Build request payload depending on model and mode."""
        payload: dict = {
            "prompt": req.prompt,
            "image_size": {"width": req.width, "height": req.height},
        }

        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt

        if req.seed is not None:
            payload["seed"] = req.seed

        if req.num_images > 1:
            payload["num_images"] = req.num_images

        # img2img via Kontext or others
        if req.mode in (ImageMode.IMAGE_TO_IMAGE, ImageMode.INPAINT) and req.source_image_b64:
            if "kontext" in model_key:
                payload["image_url"] = f"data:image/png;base64,{req.source_image_b64}"
            else:
                payload["image"] = f"data:image/png;base64,{req.source_image_b64}"
                payload["strength"] = req.strength

        if req.mode == ImageMode.INPAINT and req.mask_b64:
            payload["mask"] = f"data:image/png;base64,{req.mask_b64}"

        # Model-specific params
        if "flux" in model_key:
            # Schnell models need 1-4 steps, dev models use up to 50
            if "schnell" in model_key:
                payload["num_inference_steps"] = min(req.steps, 4)
            else:
                payload["num_inference_steps"] = req.steps
            payload["guidance_scale"] = req.guidance

        return payload

    def _poll_result(
        self,
        endpoint: str,
        request_id: str,
        max_wait: int = 120,
        status_url: Optional[str] = None,
        response_url: Optional[str] = None,
    ) -> dict:
        """Poll fal queue until result is ready.
        
        Uses status_url/response_url from submit response when available
        (new fal API), falls back to constructed URLs (legacy).
        """
        # Prefer URLs given by fal directly; fall back to constructed paths
        _status_url = status_url or f"https://queue.fal.run/{endpoint}/requests/{request_id}/status"
        _result_url = response_url or f"https://queue.fal.run/{endpoint}/requests/{request_id}"

        deadline = time.time() + max_wait
        while time.time() < deadline:
            status_resp = self._http.get(_status_url)
            if status_resp.status_code == 200:
                try:
                    status_data = status_resp.json()
                except Exception:
                    status_data = {}
                status = status_data.get("status", "")

                if status == "COMPLETED":
                    resp = self._http.get(_result_url)
                    resp.raise_for_status()
                    return resp.json()
                elif status in ("FAILED", "CANCELLED"):
                    raise RuntimeError(f"fal job {request_id} {status}: {status_data}")
                # IN_QUEUE / IN_PROGRESS → keep polling

            elif status_resp.status_code in (405, 404):
                # Some endpoints return the result directly without status polling
                resp = self._http.get(_result_url)
                if resp.status_code == 200:
                    data = resp.json()
                    # If it already has images, it's done
                    if data.get("images") or data.get("image"):
                        return data
                # Not ready yet, keep waiting
            else:
                status_resp.raise_for_status()

            time.sleep(1.0)

        raise TimeoutError(f"fal job {request_id} timed out after {max_wait}s")

    def _extract_images(self, data: dict) -> list[str]:
        """Extract image URLs from fal response (various formats)."""
        images = []
        # Most fal models return {"images": [{"url": ...}]}
        for img in data.get("images", []):
            if isinstance(img, dict) and "url" in img:
                images.append(img["url"])
            elif isinstance(img, str):
                images.append(img)
        # Some models return single {"image": {"url": ...}}
        if not images and "image" in data:
            img = data["image"]
            if isinstance(img, dict) and "url" in img:
                images.append(img["url"])
            elif isinstance(img, str):
                images.append(img)
        return images

    def health_check(self) -> bool:
        try:
            resp = self._http.get("/fal-ai/flux/dev")
            return resp.status_code in (200, 422)  # 422 = valid endpoint, bad params
        except Exception:
            return False
