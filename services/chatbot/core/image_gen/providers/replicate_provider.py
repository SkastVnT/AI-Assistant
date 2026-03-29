"""
Replicate provider â€” run any model on the cloud.
Supports FLUX, Grok-Imagine, Recraft, Seedream, and community models.
"""

from __future__ import annotations

import time
import logging
import httpx
from typing import Optional

from .base import (
    BaseImageProvider, ImageRequest, ImageResult,
    ImageMode, ProviderTier,
)

logger = logging.getLogger(__name__)

REPLICATE_MODELS = {
    "grok-imagine":     "xai/grok-imagine-image",
    "flux2-pro":        "black-forest-labs/flux-2-pro",
    "flux2-dev":        "black-forest-labs/flux-2-dev",
    "flux2-klein-4b":   "black-forest-labs/flux-2-klein-4b",
    "flux-kontext-pro": "black-forest-labs/flux-kontext-pro",
    "recraft-v4":       "recraft-ai/recraft-v4",
    "seedream5":        "bytedance/seedream-5-lite",
    "nano-banana":      "google/nano-banana",
    "nano-banana-pro":  "google/nano-banana",
    "nano-banana-2":    "google/nano-banana-2",
    "sdxl-lightning":   "bytedance/sdxl-lightning-4step",
}

REPLICATE_COST = {
    "grok-imagine":     0.020,
    "flux2-pro":        0.055,
    "flux2-dev":        0.025,
    "flux2-klein-4b":   0.003,
    "flux-kontext-pro": 0.040,
    "recraft-v4":       0.020,
    "seedream5":        0.018,
    "nano-banana":      0.011,
    "nano-banana-pro":  0.011,
    "nano-banana-2":    0.005,
    "sdxl-lightning":   0.002,
}


class ReplicateProvider(BaseImageProvider):
    """Replicate â€” run any model via prediction API."""

    name = "replicate"
    tier = ProviderTier.ULTRA
    supports_i2i = True
    supports_inpaint = False

    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.default_model = kwargs.get("default_model", "flux2-dev")
        self._http = httpx.Client(
            base_url="https://api.replicate.com/v1",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Prefer": "wait",
            },
            timeout=180.0,
        )

    @property
    def cost_per_image(self) -> float:
        return REPLICATE_COST.get(self.default_model, 0.025)

    def generate(self, req: ImageRequest) -> ImageResult:
        model_key = req.extra.get("model", self.default_model)
        model_version = REPLICATE_MODELS.get(model_key)
        if not model_version:
            return ImageResult(success=False, error=f"Unknown Replicate model: {model_key}")

        t0 = time.time()

        try:
            payload = self._build_input(req, model_key)

            # Create prediction (with Prefer: wait header for sync)
            resp = self._http.post(
                f"/models/{model_version}/predictions",
                json={"input": payload},
            )
            resp.raise_for_status()
            pred = resp.json()

            # If not completed yet, poll
            if pred.get("status") not in ("succeeded", "failed"):
                pred = self._poll(pred["id"])

            if pred.get("status") == "failed":
                return ImageResult(
                    success=False,
                    error=pred.get("error", "Replicate prediction failed"),
                    provider=self.name,
                )

            images_url = self._extract_output(pred.get("output"))
            latency = (time.time() - t0) * 1000

            return ImageResult(
                success=True,
                images_url=images_url,
                provider=self.name,
                model=model_key,
                prompt_used=req.prompt,
                latency_ms=latency,
                cost_usd=REPLICATE_COST.get(model_key, 0.025) * max(1, len(images_url)),
                metadata={"prediction_id": pred.get("id")},
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"[Replicate] HTTP {e.response.status_code}: {e.response.text[:500]}")
            return ImageResult(success=False, error=f"Replicate error: {e.response.status_code}", provider=self.name)
        except Exception as e:
            logger.error(f"[Replicate] Error: {e}", exc_info=True)
            return ImageResult(success=False, error=str(e), provider=self.name)

    def _build_input(self, req: ImageRequest, model_key: str) -> dict:
        payload = {"prompt": req.prompt}

        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt

        if req.seed is not None:
            payload["seed"] = req.seed

        payload["width"] = req.width
        payload["height"] = req.height

        if req.num_images > 1:
            payload["num_outputs"] = req.num_images

        if "flux" in model_key:
            payload["num_inference_steps"] = req.steps
            payload["guidance"] = req.guidance

        # img2img
        if req.mode == ImageMode.IMAGE_TO_IMAGE and req.source_image_b64:
            if "kontext" in model_key:
                payload["image"] = f"data:image/png;base64,{req.source_image_b64}"
            else:
                payload["image"] = f"data:image/png;base64,{req.source_image_b64}"
                payload["prompt_strength"] = req.strength

        return payload

    def _poll(self, prediction_id: str, max_wait: int = 180) -> dict:
        deadline = time.time() + max_wait
        while time.time() < deadline:
            resp = self._http.get(f"/predictions/{prediction_id}")
            pred = resp.json()
            if pred["status"] in ("succeeded", "failed", "canceled"):
                return pred
            time.sleep(2.0)
        raise TimeoutError(f"Replicate prediction {prediction_id} timed out")

    def _extract_output(self, output) -> list[str]:
        if output is None:
            return []
        if isinstance(output, str):
            return [output]
        if isinstance(output, list):
            urls = []
            for item in output:
                if isinstance(item, str):
                    urls.append(item)
                elif isinstance(item, dict) and "url" in item:
                    urls.append(item["url"])
            return urls
        return []

    def health_check(self) -> bool:
        try:
            resp = self._http.get("/models/black-forest-labs/flux-2-dev")
            return resp.status_code == 200
        except Exception:
            return False
