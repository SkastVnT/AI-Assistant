"""
Together.ai provider â€” cheap/free FLUX inference.
Free tier: ~60 images/day. Paid: $0.001-0.006/image.
Good fallback when fal/replicate are down.
"""

from __future__ import annotations

import time
import logging
import httpx

from .base import (
    BaseImageProvider, ImageRequest, ImageResult,
    ImageMode, ProviderTier,
)

logger = logging.getLogger(__name__)

TOGETHER_MODELS = {
    "flux1-schnell":     "black-forest-labs/FLUX.1-schnell",
    "flux1-dev":         "black-forest-labs/FLUX.1-dev",
    "flux1-kontext":     "black-forest-labs/FLUX.1-Kontext",
    "flux1-canny":       "black-forest-labs/FLUX.1-canny",
    "flux1-depth":       "black-forest-labs/FLUX.1-depth",
    "flux1-redux":       "black-forest-labs/FLUX.1-Redux",
}

TOGETHER_COST = {
    "flux1-schnell":     0.001,
    "flux1-dev":         0.006,
    "flux1-kontext":     0.006,
    "flux1-canny":       0.006,
    "flux1-depth":       0.006,
    "flux1-redux":       0.006,
}


class TogetherProvider(BaseImageProvider):
    """Together.ai â€” free/cheap FLUX inference, great fallback."""

    name = "together"
    tier = ProviderTier.FAST
    supports_i2i = True
    supports_inpaint = False

    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.default_model = kwargs.get("default_model", "flux1-schnell")
        self._http = httpx.Client(
            base_url="https://api.together.xyz/v1",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    @property
    def cost_per_image(self) -> float:
        return TOGETHER_COST.get(self.default_model, 0.001)

    def generate(self, req: ImageRequest) -> ImageResult:
        model_key = req.extra.get("model", self.default_model)
        model_id = TOGETHER_MODELS.get(model_key)
        if not model_id:
            return ImageResult(success=False, error=f"Unknown Together model: {model_key}")

        t0 = time.time()

        try:
            # Schnell models need 1-4 steps, dev models handle more
            steps = req.steps
            if "schnell" in model_key:
                steps = min(steps, 4)

            payload = {
                "model": model_id,
                "prompt": req.prompt,
                "width": req.width,
                "height": req.height,
                "steps": steps,
                "n": req.num_images,
                "response_format": "b64_json",
            }

            if req.negative_prompt:
                payload["negative_prompt"] = req.negative_prompt

            if req.seed is not None:
                payload["seed"] = req.seed

            # img2img via Kontext/Redux
            if req.mode == ImageMode.IMAGE_TO_IMAGE and req.source_image_b64:
                payload["image"] = f"data:image/png;base64,{req.source_image_b64}"
                payload["strength"] = req.strength

            resp = self._http.post("/images/generations", json=payload)
            resp.raise_for_status()
            data = resp.json()

            images_b64 = []
            images_url = []
            for item in data.get("data", []):
                if "b64_json" in item:
                    images_b64.append(item["b64_json"])
                elif "url" in item:
                    images_url.append(item["url"])

            latency = (time.time() - t0) * 1000

            return ImageResult(
                success=True,
                images_b64=images_b64,
                images_url=images_url,
                provider=self.name,
                model=model_key,
                prompt_used=req.prompt,
                latency_ms=latency,
                cost_usd=TOGETHER_COST.get(model_key, 0.001) * max(1, len(images_b64) + len(images_url)),
                metadata={"together_model": model_id},
            )

        except httpx.HTTPStatusError as e:
            body = e.response.text[:500] if e.response else "no body"
            logger.error(f"[Together] HTTP {e.response.status_code}: {body}")
            return ImageResult(success=False, error=f"Together error: {e.response.status_code}", provider=self.name)
        except Exception as e:
            logger.error(f"[Together] Error: {e}", exc_info=True)
            return ImageResult(success=False, error=str(e), provider=self.name)

    def health_check(self) -> bool:
        try:
            resp = self._http.get("/models")
            return resp.status_code == 200
        except Exception:
            return False
