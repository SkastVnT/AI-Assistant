"""
Black Forest Labs (BFL) direct API provider.
Access FLUX.2 models directly from https://api.bfl.ai
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

BFL_MODELS = {
    "flux2-pro":   "flux-2-pro",
    "flux2-dev":   "flux-2-dev",
    "flux2-max":   "flux-2-max",
    "flux1-pro":   "flux-pro-1.1",
    "flux1-dev":   "flux-dev",
}

BFL_COST = {
    "flux2-pro":   0.040,
    "flux2-dev":   0.025,
    "flux2-max":   0.080,
    "flux1-pro":   0.040,
    "flux1-dev":   0.025,
}


class BFLProvider(BaseImageProvider):
    """Black Forest Labs — official FLUX API."""

    name = "bfl"
    tier = ProviderTier.ULTRA
    supports_i2i = False
    supports_inpaint = False

    def __init__(self, api_key: str = "", **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self.default_model = kwargs.get("default_model", "flux1-dev")
        self._http = httpx.Client(
            base_url="https://api.bfl.ml/v1",
            headers={
                "X-Key": api_key,
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    @property
    def cost_per_image(self) -> float:
        return BFL_COST.get(self.default_model, 0.040)

    def generate(self, req: ImageRequest) -> ImageResult:
        model_key = req.extra.get("model", self.default_model)
        model_id = BFL_MODELS.get(model_key)
        if not model_id:
            return ImageResult(success=False, error=f"Unknown BFL model: {model_key}")

        t0 = time.time()

        try:
            payload = {
                "prompt": req.prompt,
                "width": req.width,
                "height": req.height,
            }
            if req.seed is not None:
                payload["seed"] = req.seed

            # Submit generation
            resp = self._http.post(f"/{model_id}", json=payload)
            resp.raise_for_status()
            task = resp.json()
            task_id = task.get("id")

            if not task_id:
                return ImageResult(success=False, error="BFL did not return task ID", provider=self.name)

            # Poll for result
            result = self._poll(task_id)
            images_url = []
            if result.get("result", {}).get("sample"):
                images_url.append(result["result"]["sample"])

            latency = (time.time() - t0) * 1000

            return ImageResult(
                success=True,
                images_url=images_url,
                provider=self.name,
                model=model_key,
                prompt_used=req.prompt,
                latency_ms=latency,
                cost_usd=BFL_COST.get(model_key, 0.040),
                metadata={"task_id": task_id},
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"[BFL] HTTP {e.response.status_code}: {e.response.text[:500]}")
            return ImageResult(success=False, error=f"BFL error: {e.response.status_code}", provider=self.name)
        except Exception as e:
            logger.error(f"[BFL] Error: {e}", exc_info=True)
            return ImageResult(success=False, error=str(e), provider=self.name)

    def _poll(self, task_id: str, max_wait: int = 120) -> dict:
        deadline = time.time() + max_wait
        while time.time() < deadline:
            resp = self._http.get("/get_result", params={"id": task_id})
            data = resp.json()
            status = data.get("status")
            if status == "Ready":
                return data
            elif status in ("Error", "Request Moderated"):
                raise RuntimeError(f"BFL task {task_id} failed: {data}")
            time.sleep(1.5)
        raise TimeoutError(f"BFL task {task_id} timed out after {max_wait}s")

    def health_check(self) -> bool:
        try:
            resp = self._http.get("/get_result", params={"id": "test"})
            return resp.status_code in (200, 404)
        except Exception:
            return False
