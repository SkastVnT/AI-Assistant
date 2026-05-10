"""
OpenAI image provider â€” GPT-Image-1 / DALL-E API.
Supports conversational image generation & editing via OpenAI's /images endpoint.
"""

from __future__ import annotations

import time
import base64
import logging
import httpx

from .base import (
    BaseImageProvider, ImageRequest, ImageResult,
    ImageMode, ProviderTier,
)

logger = logging.getLogger(__name__)

OPENAI_COST = {
    "gpt-image-1": {
        "1024x1024": 0.040,
        "1536x1024": 0.080,
        "1024x1536": 0.080,
        "auto": 0.040,
    },
    "dall-e-3": {
        "1024x1024": 0.040,
        "1792x1024": 0.080,
        "1024x1792": 0.080,
    },
}


class OpenAIImageProvider(BaseImageProvider):
    """OpenAI gpt-image-1 / DALL-E 3 â€” native image generation with conversation understanding."""

    name = "openai"
    tier = ProviderTier.ULTRA
    supports_i2i = True
    supports_inpaint = True

    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.default_model = kwargs.get("default_model", "dall-e-3")
        self._http = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    @property
    def cost_per_image(self) -> float:
        return 0.040

    def generate(self, req: ImageRequest) -> ImageResult:
        t0 = time.time()

        try:
            if req.mode == ImageMode.INPAINT and req.source_image_b64:
                return self._edit(req, t0)
            else:
                return self._generate(req, t0)

        except httpx.HTTPStatusError as e:
            logger.error(f"[OpenAI Image] HTTP {e.response.status_code}: {e.response.text[:500]}")
            return ImageResult(success=False, error=f"OpenAI error: {e.response.status_code}", provider=self.name)
        except Exception as e:
            logger.error(f"[OpenAI Image] Error: {e}", exc_info=True)
            return ImageResult(success=False, error=str(e), provider=self.name)

    def _generate(self, req: ImageRequest, t0: float) -> ImageResult:
        model = req.extra.get("model", self.default_model)

        # dall-e-3 supported sizes
        DALLE3_SIZES = {"1024x1024", "1792x1024", "1024x1792"}
        # gpt-image-1 supported sizes
        GPT_IMAGE_SIZES = {"1024x1024", "1536x1024", "1024x1536", "auto"}

        size = f"{req.width}x{req.height}"

        if model == "gpt-image-1":
            if size not in GPT_IMAGE_SIZES:
                size = "1024x1024"
            payload = {
                "model": model,
                "prompt": req.prompt,
                "n": min(req.num_images, 1),  # gpt-image-1 supports max n=1
                "size": size,
            }
        else:
            # dall-e-3
            if size not in DALLE3_SIZES:
                size = "1024x1024"
            payload = {
                "model": model,
                "prompt": req.prompt,
                "n": min(req.num_images, 1),  # dall-e-3 supports max n=1
                "size": size,
                "response_format": "url",
            }
            if req.style_preset:
                payload["style"] = req.style_preset  # "vivid" or "natural"

        resp = self._http.post("/images/generations", json=payload)
        resp.raise_for_status()
        data = resp.json()

        images_url = []
        images_b64 = []
        for item in data.get("data", []):
            if "url" in item:
                images_url.append(item["url"])
            elif "b64_json" in item:
                images_b64.append(item["b64_json"])

        latency = (time.time() - t0) * 1000

        cost_table = OPENAI_COST.get(model, {})
        cost = cost_table.get(size, cost_table.get("auto", 0.040))

        return ImageResult(
            success=True,
            images_url=images_url,
            images_b64=images_b64,
            provider=self.name,
            model=model,
            prompt_used=req.prompt,
            latency_ms=latency,
            cost_usd=cost * req.num_images,
            metadata={"size": size},
        )

    def _edit(self, req: ImageRequest, t0: float) -> ImageResult:
        """Use /images/edits for inpainting."""
        # Build multipart form
        import io
        files = {
            "image": ("image.png", base64.b64decode(req.source_image_b64), "image/png"),
            "prompt": (None, req.prompt),
            "n": (None, str(req.num_images)),
            "size": (None, f"{req.width}x{req.height}"),
            "response_format": (None, "url"),
        }
        if req.mask_b64:
            files["mask"] = ("mask.png", base64.b64decode(req.mask_b64), "image/png")

        edit_http = httpx.Client(
            base_url="https://api.openai.com/v1",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=120.0,
        )
        resp = edit_http.post("/images/edits", files=files)
        resp.raise_for_status()
        data = resp.json()

        images_url = [img["url"] for img in data.get("data", [])]
        latency = (time.time() - t0) * 1000

        return ImageResult(
            success=True,
            images_url=images_url,
            provider=self.name,
            model="gpt-image-1-edit",
            prompt_used=req.prompt,
            latency_ms=latency,
            cost_usd=0.040 * req.num_images,
            metadata={"mode": "edit"},
        )

    def health_check(self) -> bool:
        try:
            resp = self._http.get("/models")
            return resp.status_code == 200
        except Exception:
            return False
