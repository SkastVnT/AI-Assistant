"""
Nano Banana provider — Google Gemini 2.5 Flash Image (a.k.a. "Nano Banana").

Direct call to the Google Generative Language API. Supports:
  - Text → image generation
  - Multi-image reference input (character preservation, style transfer, edits)
  - Aspect-ratio control via ``imageConfig.aspectRatio``
  - Optional 2K output via ``imageConfig.imageSize`` (Nano Banana Pro models only)

Single API call returns 1 image. For ``num_images > 1`` the route layer
issues parallel calls (handled in ``routes/nano_banana.py``).

Reference image input is passed through ``ImageRequest.extra``:
    extra = {
        "reference_images_b64": [b64_str, ...],   # 0..6 PNG/JPEG bytes (no data: prefix)
        "reference_mime_types": [mime_str, ...],  # parallel list, defaults to image/png
        "model": "gemini-2.5-flash-image",        # override default model
        "image_size": "2K",                       # "1K" | "2K" | "4K" (Pro only)
        "aspect_ratio": "9:16",                   # "1:1" | "9:16" | "16:9" | "3:4" | "4:3"
    }
"""

from __future__ import annotations

import json
import logging
import time

import httpx

from .base import (
    BaseImageProvider,
    ImageRequest,
    ImageResult,
    ProviderTier,
)

logger = logging.getLogger(__name__)

# Cost (USD) per generated image — Gemini 2.5 Flash Image pricing (2025).
# ~ $0.039 per 1024-equivalent image (1290 output tokens × $30 / 1M).
NANO_BANANA_COST_PER_IMAGE = 0.039

# Max reference images Google currently accepts in a single multimodal call.
MAX_REFERENCE_IMAGES = 6

VALID_ASPECT_RATIOS = {
    "1:1",
    "9:16",
    "16:9",
    "3:4",
    "4:3",
    "2:3",
    "3:2",
    "4:5",
    "5:4",
    "21:9",
}
VALID_IMAGE_SIZES = {"1K", "2K", "4K"}

# Maximum retries when Gemini returns a safety-filter rejection (IMAGE_SAFETY / PROHIBITED_CONTENT).
MAX_SAFETY_RETRIES = 5
SAFETY_FINISH_REASONS = frozenset({"IMAGE_SAFETY", "PROHIBITED_CONTENT", "SAFETY"})


class NanoBananaProvider(BaseImageProvider):
    """Google Gemini 2.5 Flash Image — "Nano Banana"."""

    name = "nano_banana"
    tier = ProviderTier.HIGH
    supports_i2i = True
    supports_inpaint = False  # not via masks; uses prompt-driven edits

    DEFAULT_MODEL = "gemini-2.5-flash-image"
    BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(
        self,
        api_key: str = "",
        api_keys: list[str] | None = None,
        default_model: str = "",
        **kwargs,
    ):
        super().__init__(api_key=api_key, **kwargs)
        # Support a rotation pool of keys to spread per-key quota.
        self._api_keys: list[str] = [k for k in (api_keys or [api_key]) if k]
        self._key_idx: int = 0
        self.default_model = default_model or self.DEFAULT_MODEL
        self._configured = bool(self._api_keys)
        self._http = httpx.Client(timeout=180.0)

    @property
    def cost_per_image(self) -> float:
        return NANO_BANANA_COST_PER_IMAGE

    def _next_key(self) -> str:
        if not self._api_keys:
            return ""
        key = self._api_keys[self._key_idx % len(self._api_keys)]
        self._key_idx += 1
        return key

    def generate(self, req: ImageRequest) -> ImageResult:
        """Generate ONE image. The route layer loops for num_images > 1."""
        t0 = time.time()
        if not self._api_keys:
            return ImageResult(
                success=False, error="GEMINI_API_KEY not configured", provider=self.name
            )

        extra = req.extra or {}
        model = extra.get("model") or self.default_model

        # Build the multimodal "parts" list: text prompt + 0..N reference images.
        parts: list[dict] = [{"text": req.prompt}]

        ref_b64s: list[str] = list(extra.get("reference_images_b64") or [])
        ref_mimes: list[str] = list(extra.get("reference_mime_types") or [])
        if req.source_image_b64 and not ref_b64s:
            ref_b64s = [req.source_image_b64]
            ref_mimes = ["image/png"]
        for i, b64 in enumerate(ref_b64s[:MAX_REFERENCE_IMAGES]):
            mime = ref_mimes[i] if i < len(ref_mimes) else "image/png"
            parts.append({"inlineData": {"mimeType": mime, "data": b64}})

        logger.info(
            "[NanoBanana] generate model=%s refs=%d ar=%s size=%s prompt_len=%d",
            model,
            len(ref_b64s[:MAX_REFERENCE_IMAGES]),
            extra.get("aspect_ratio") or "auto",
            extra.get("image_size") or "default",
            len(req.prompt or ""),
        )

        # imageConfig — aspect ratio + (optional) image_size
        image_config: dict = {}
        ar = extra.get("aspect_ratio") or self._aspect_from_dims(req.width, req.height)
        if ar in VALID_ASPECT_RATIOS:
            image_config["aspectRatio"] = ar
        size = extra.get("image_size")
        if size in VALID_IMAGE_SIZES:
            image_config["imageSize"] = size

        generation_config: dict = {
            "responseModalities": ["IMAGE", "TEXT"],
        }
        if image_config:
            generation_config["imageConfig"] = image_config

        payload = {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": generation_config,
        }

        # Outer loop: retry on safety-filter rejections up to MAX_SAFETY_RETRIES times.
        # Inner loop: rotate API keys on transient HTTP errors (429 / 5xx).
        last_err = ""
        key_attempts = max(1, len(self._api_keys))
        for safety_attempt in range(1, MAX_SAFETY_RETRIES + 1):
            got_safety_block = False
            for _ in range(key_attempts):
                key = self._next_key()
                url = f"{self.BASE_URL}/models/{model}:generateContent"
                try:
                    resp = self._http.post(
                        url,
                        headers={
                            "x-goog-api-key": key,
                            "Content-Type": "application/json",
                        },
                        json=payload,
                    )
                except httpx.HTTPError as e:
                    last_err = f"network: {e}"
                    logger.warning("[NanoBanana] network error: %s", e)
                    continue

                if (
                    resp.status_code in (429, 500, 502, 503, 504)
                    and len(self._api_keys) > 1
                ):
                    last_err = f"HTTP {resp.status_code}"
                    logger.warning("[NanoBanana] %s, rotating key", last_err)
                    continue
                if resp.status_code >= 400:
                    snippet = resp.text[:500]
                    logger.error("[NanoBanana] HTTP %s: %s", resp.status_code, snippet)
                    return ImageResult(
                        success=False,
                        error=f"Gemini API HTTP {resp.status_code}: {snippet}",
                        provider=self.name,
                        model=model,
                        prompt_used=req.prompt,
                        metadata={"attempt": safety_attempt},
                    )

                data = resp.json()
                images_b64: list[str] = []
                text_chunks: list[str] = []
                for cand in data.get("candidates", []):
                    for part in cand.get("content", {}).get("parts", []):
                        inline = part.get("inline_data") or part.get("inlineData")
                        if inline and inline.get("data"):
                            images_b64.append(inline["data"])
                        elif part.get("text"):
                            text_chunks.append(part["text"])

                if not images_b64:
                    pf = data.get("promptFeedback") or data.get("prompt_feedback") or {}
                    block_reason = pf.get("blockReason") or pf.get("block_reason") or ""
                    finish_reasons = [
                        c.get("finishReason") or c.get("finish_reason") or ""
                        for c in data.get("candidates", [])
                    ]
                    safety_ratings = [
                        c.get("safetyRatings") or c.get("safety_ratings") or []
                        for c in data.get("candidates", [])
                    ]
                    is_safety = any(
                        fr in SAFETY_FINISH_REASONS for fr in finish_reasons
                    )
                    logger.warning(
                        "[NanoBanana] no image | attempt=%d/%d | model=%s | finish=%s "
                        "| block=%s | safety=%s | text=%r | raw=%s",
                        safety_attempt,
                        MAX_SAFETY_RETRIES,
                        model,
                        finish_reasons,
                        block_reason,
                        safety_ratings,
                        "\n".join(text_chunks)[:300],
                        json.dumps(data)[:1500],
                    )
                    if is_safety and safety_attempt < MAX_SAFETY_RETRIES:
                        logger.info(
                            "[NanoBanana] safety filter — retrying %d/%d",
                            safety_attempt + 1,
                            MAX_SAFETY_RETRIES,
                        )
                        got_safety_block = True
                        break  # break key loop → next safety_attempt

                    msg = (
                        "; ".join(t.strip() for t in text_chunks if t.strip())
                        or block_reason
                        or (finish_reasons and f"finish={finish_reasons[0]}")
                        or "no image returned"
                    )
                    return ImageResult(
                        success=False,
                        error=f"nano-banana: {msg[:300]}",
                        provider=self.name,
                        model=model,
                        prompt_used=req.prompt,
                        metadata={
                            "attempt": safety_attempt,
                            "finish_reasons": finish_reasons,
                        },
                    )

                latency = (time.time() - t0) * 1000.0
                return ImageResult(
                    success=True,
                    images_b64=images_b64,
                    provider=self.name,
                    model=model,
                    prompt_used=req.prompt,
                    latency_ms=latency,
                    cost_usd=NANO_BANANA_COST_PER_IMAGE * len(images_b64),
                    metadata={
                        "aspect_ratio": image_config.get("aspectRatio"),
                        "image_size": image_config.get("imageSize"),
                        "ref_count": len(ref_b64s),
                        "model": model,
                        "text": "\n".join(text_chunks)[:500] if text_chunks else "",
                        "attempt": safety_attempt,
                    },
                )

            if not got_safety_block:
                # Key rotation exhausted (network/quota) — no point retrying safety loop.
                break

        return ImageResult(
            success=False,
            error=f"nano-banana exhausted {MAX_SAFETY_RETRIES} safety retries: {last_err or 'unknown'}",
            provider=self.name,
            model=model,
            prompt_used=req.prompt,
            metadata={"attempt": MAX_SAFETY_RETRIES},
        )

    @staticmethod
    def _aspect_from_dims(w: int, h: int) -> str:
        """Pick the closest supported aspect ratio from explicit dimensions."""
        if not w or not h:
            return "1:1"
        ratio = w / float(h)
        candidates = {
            "1:1": 1.0,
            "16:9": 16 / 9,
            "9:16": 9 / 16,
            "4:3": 4 / 3,
            "3:4": 3 / 4,
            "3:2": 3 / 2,
            "2:3": 2 / 3,
            "4:5": 4 / 5,
            "5:4": 5 / 4,
            "21:9": 21 / 9,
        }
        return min(candidates.items(), key=lambda kv: abs(kv[1] - ratio))[0]

    def health_check(self) -> bool:
        if not self._api_keys:
            return False
        try:
            r = self._http.get(
                f"{self.BASE_URL}/models",
                headers={"x-goog-api-key": self._api_keys[0]},
                timeout=10.0,
            )
            return r.status_code == 200
        except Exception:
            return False
