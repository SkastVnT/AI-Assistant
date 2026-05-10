"""
StepFun (é˜¶è·ƒæ˜Ÿè¾°) provider â€” Chinese SOTA image generation & editing.
Step1X-Edit: Best-in-class instruction-based image editing.
Step1X-Fill: High quality inpainting.
Step1-Turbo: Fast text-to-image.

API: https://platform.stepfun.com
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

# StepFun model mappings
STEPFUN_MODELS = {
    # Text-to-image
    "step1x-turbo":   "step-1x-turbo",
    "step1x-medium":  "step-1x-medium",
    # Image editing (instruction-based, like "add a hat")
    "step1x-edit":    "step-1x-edit",
    # Inpainting
    "step1x-fill":    "step-1x-fill",
}

STEPFUN_COST = {
    "step1x-turbo":   0.005,
    "step1x-medium":  0.015,
    "step1x-edit":    0.020,
    "step1x-fill":    0.020,
}


class StepFunProvider(BaseImageProvider):
    """StepFun AI â€” Chinese SOTA with excellent editing capabilities."""

    name = "stepfun"
    tier = ProviderTier.HIGH
    supports_i2i = True       # Step1X-Edit excels here
    supports_inpaint = True   # Step1X-Fill
    cost_per_image = 0.010

    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.default_model = kwargs.get("default_model", "step1x-turbo")
        self._http = httpx.Client(
            base_url="https://api.stepfun.com/v1",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    def generate(self, req: ImageRequest) -> ImageResult:
        # Select model based on mode
        model_key = req.extra.get("model", self._pick_model(req))
        model_id = STEPFUN_MODELS.get(model_key)
        if not model_id:
            return ImageResult(
                success=False,
                error=f"Unknown StepFun model: {model_key}",
                provider=self.name,
            )

        t0 = time.time()

        try:
            if req.mode == ImageMode.TEXT_TO_IMAGE:
                return self._text_to_image(req, model_id, model_key, t0)
            elif req.mode == ImageMode.IMAGE_TO_IMAGE:
                return self._edit_image(req, model_id, model_key, t0)
            elif req.mode == ImageMode.INPAINT:
                return self._inpaint(req, model_key, t0)
            else:
                return self._text_to_image(req, model_id, model_key, t0)

        except httpx.HTTPStatusError as e:
            error_body = e.response.text[:300]
            logger.error(f"[StepFun] HTTP {e.response.status_code}: {error_body}")
            return ImageResult(
                success=False,
                error=f"StepFun HTTP {e.response.status_code}: {error_body}",
                provider=self.name,
            )
        except Exception as e:
            logger.error(f"[StepFun] Exception: {e}", exc_info=True)
            return ImageResult(success=False, error=str(e), provider=self.name)

    def _text_to_image(
        self, req: ImageRequest, model_id: str, model_key: str, t0: float
    ) -> ImageResult:
        """Standard text-to-image generation."""
        payload = {
            "model": model_id,
            "prompt": req.prompt,
            "size": f"{req.width}x{req.height}",
            "n": req.num_images,
            "response_format": "b64_json",
        }

        if req.negative_prompt:
            payload["negative_prompt"] = req.negative_prompt
        if req.seed is not None:
            payload["seed"] = req.seed

        resp = self._http.post("/images/generations", json=payload)
        resp.raise_for_status()
        data = resp.json()

        return self._parse_response(data, model_key, t0)

    def _edit_image(
        self, req: ImageRequest, model_id: str, model_key: str, t0: float
    ) -> ImageResult:
        """
        Instruction-based image editing using Step1X-Edit.
        This is StepFun's killer feature â€” like ChatGPT's image editing.
        """
        # Step1X-Edit uses chat-like API with image + instruction
        model_key = "step1x-edit"
        model_id = STEPFUN_MODELS["step1x-edit"]

        payload = {
            "model": model_id,
            "prompt": req.prompt,
            "image": f"data:image/png;base64,{req.source_image_b64}",
            "n": req.num_images,
            "response_format": "b64_json",
        }

        if req.strength:
            payload["strength"] = req.strength

        resp = self._http.post("/images/edits", json=payload)
        resp.raise_for_status()
        data = resp.json()

        return self._parse_response(data, model_key, t0)

    def _inpaint(
        self, req: ImageRequest, model_key: str, t0: float
    ) -> ImageResult:
        """Inpainting using Step1X-Fill."""
        model_key = "step1x-fill"
        model_id = STEPFUN_MODELS["step1x-fill"]

        payload = {
            "model": model_id,
            "prompt": req.prompt,
            "image": f"data:image/png;base64,{req.source_image_b64}",
            "mask": f"data:image/png;base64,{req.mask_b64}",
            "n": req.num_images,
            "response_format": "b64_json",
        }

        resp = self._http.post("/images/edits", json=payload)
        resp.raise_for_status()
        data = resp.json()

        return self._parse_response(data, model_key, t0)

    def _parse_response(
        self, data: dict, model_key: str, t0: float
    ) -> ImageResult:
        """Parse StepFun API response."""
        images_b64 = []
        images_url = []

        for item in data.get("data", []):
            if "b64_json" in item:
                images_b64.append(item["b64_json"])
            elif "url" in item:
                images_url.append(item["url"])

        if not images_b64 and not images_url:
            return ImageResult(
                success=False,
                error="StepFun returned no images",
                provider=self.name,
                model=model_key,
            )

        latency = (time.time() - t0) * 1000

        return ImageResult(
            success=True,
            images_b64=images_b64,
            images_url=images_url,
            provider=self.name,
            model=model_key,
            latency_ms=latency,
            cost_usd=STEPFUN_COST.get(model_key, 0.010),
            metadata={"raw_response_keys": list(data.keys())},
        )

    def _pick_model(self, req: ImageRequest) -> str:
        """Auto-select best model for the request."""
        if req.mode == ImageMode.INPAINT:
            return "step1x-fill"
        if req.mode == ImageMode.IMAGE_TO_IMAGE:
            return "step1x-edit"
        return self.default_model

    def health_check(self) -> bool:
        """Check StepFun API reachability."""
        if not self._configured:
            return False
        try:
            resp = self._http.get("/models")
            return resp.status_code == 200
        except Exception:
            return False
