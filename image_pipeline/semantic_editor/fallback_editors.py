"""
image_pipeline.semantic_editor.fallback_editors — API-based editing fallbacks.

Fallback chain when Qwen VPS is unavailable (§5.1, routing.yaml):
    1. FLUX.1 Kontext  (fal.ai)   — instruction-based editing, $0.025/img
    2. Step1X-Edit     (StepFun)  — instruction-based editing, $0.020/img
    3. Nano-Banana     (fal.ai)   — generation fallback (no edit), $0.011/img

Each editor adapts the existing provider wrapper from
``services/chatbot/core/image_gen/providers/`` to the
``EditResponse`` contract used by the pipeline.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Optional

from image_pipeline.semantic_editor.qwen_client import EditResponse

logger = logging.getLogger(__name__)


# ═════════════════════════════════════════════════════════════════════
# Kontext Editor — fal.ai FLUX.1-Kontext
# ═════════════════════════════════════════════════════════════════════

class KontextEditor:
    """
    FLUX.1-Kontext via fal.ai queue API.

    Instruction-based img2img editing.  Day-1 fallback for Qwen.
    Uses the same queue-based flow as the existing FalProvider
    but returns an EditResponse instead of ImageResult.

    Protocol:
        POST /fal-ai/flux-kontext/dev  →  queue  →  poll  →  image URL
    """

    ENDPOINT = "fal-ai/flux-kontext/dev"
    COST = 0.025

    def __init__(self, api_key: str, base_url: str = "https://queue.fal.run"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def edit(
        self,
        instruction: str,
        source_image_b64: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
    ) -> EditResponse:
        """
        Synchronous edit via Kontext.

        Kontext uses ``image_url`` (data URI) for the source image
        and ``prompt`` for the edit instruction.
        """
        import httpx

        t0 = time.time()
        try:
            payload = self._build_payload(
                instruction, source_image_b64, width, height, seed,
            )
            with httpx.Client(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Key {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            ) as client:
                # Submit to queue
                submit = client.post(f"/{self.ENDPOINT}", json=payload)
                submit.raise_for_status()
                submit_data = submit.json()

                # Poll for result
                if "request_id" in submit_data:
                    result_data = self._poll(
                        client,
                        submit_data["request_id"],
                        submit_data.get("status_url"),
                        submit_data.get("response_url"),
                    )
                else:
                    result_data = submit_data

            image_url = self._extract_image(result_data)
            latency = (time.time() - t0) * 1000

            if image_url:
                return EditResponse(
                    success=True,
                    image_b64=None,       # URL-based result
                    latency_ms=latency,
                    model="flux1-kontext",
                    provider="fal",
                    raw_text=image_url,    # Store URL in raw_text
                )
            else:
                return EditResponse(
                    success=False,
                    error="Kontext returned no image",
                    latency_ms=(time.time() - t0) * 1000,
                    model="flux1-kontext",
                    provider="fal",
                )

        except Exception as e:
            logger.error("[KontextEditor] %s", e, exc_info=True)
            return EditResponse(
                success=False,
                error=str(e),
                latency_ms=(time.time() - t0) * 1000,
                model="flux1-kontext",
                provider="fal",
            )

    def _build_payload(
        self,
        instruction: str,
        source_b64: Optional[str],
        width: int,
        height: int,
        seed: Optional[int],
    ) -> dict:
        payload: dict = {
            "prompt": instruction,
            "image_size": {"width": width, "height": height},
        }
        if source_b64:
            payload["image_url"] = f"data:image/png;base64,{source_b64}"
        if seed is not None:
            payload["seed"] = seed
        return payload

    def _poll(
        self,
        client: "httpx.Client",
        request_id: str,
        status_url: Optional[str],
        response_url: Optional[str],
        max_wait: int = 120,
    ) -> dict:
        import time as _time

        _status = status_url or f"{self._base_url}/{self.ENDPOINT}/requests/{request_id}/status"
        _result = response_url or f"{self._base_url}/{self.ENDPOINT}/requests/{request_id}"
        deadline = _time.time() + max_wait

        while _time.time() < deadline:
            resp = client.get(_status)
            if resp.status_code == 200:
                data = resp.json()
                status = data.get("status", "")
                if status == "COMPLETED":
                    final = client.get(_result)
                    final.raise_for_status()
                    return final.json()
                if status in ("FAILED", "CANCELLED"):
                    raise RuntimeError(f"Kontext job {request_id} {status}")
            _time.sleep(1.0)

        raise TimeoutError(f"Kontext job {request_id} timed out after {max_wait}s")

    @staticmethod
    def _extract_image(data: dict) -> Optional[str]:
        """Extract first image URL from fal response."""
        for img in data.get("images", []):
            if isinstance(img, dict) and "url" in img:
                return img["url"]
            if isinstance(img, str):
                return img
        img = data.get("image")
        if isinstance(img, dict) and "url" in img:
            return img["url"]
        if isinstance(img, str):
            return img
        return None


# ═════════════════════════════════════════════════════════════════════
# Step1X-Edit Editor — StepFun API
# ═════════════════════════════════════════════════════════════════════

class StepEditEditor:
    """
    Step1X-Edit via StepFun API.

    Instruction-based editing using Step1X-Edit model.
    Second fallback in the chain.

    Protocol:
        POST /v1/images/edits  →  {"data": [{"b64_json": "..."}]}
    """

    MODEL_ID = "step-1x-edit"
    COST = 0.020

    def __init__(self, api_key: str, base_url: str = "https://api.stepfun.com/v1"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def edit(
        self,
        instruction: str,
        source_image_b64: Optional[str] = None,
        strength: float = 0.8,
    ) -> EditResponse:
        """
        Synchronous edit via Step1X-Edit.

        Step1X-Edit uses ``/images/edits`` with ``prompt`` + ``image`` (data URI).
        Returns base64 image directly.
        """
        import httpx

        if not source_image_b64:
            return EditResponse(
                success=False,
                error="Step1X-Edit requires a source image",
                model="step1x-edit",
                provider="stepfun",
            )

        t0 = time.time()
        try:
            payload = {
                "model": self.MODEL_ID,
                "prompt": instruction,
                "image": f"data:image/png;base64,{source_image_b64}",
                "n": 1,
                "response_format": "b64_json",
                "strength": strength,
            }

            with httpx.Client(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            ) as client:
                resp = client.post("/images/edits", json=payload)
                resp.raise_for_status()
                data = resp.json()

            image_b64 = self._extract_image(data)
            latency = (time.time() - t0) * 1000

            if image_b64:
                return EditResponse(
                    success=True,
                    image_b64=image_b64,
                    latency_ms=latency,
                    model="step1x-edit",
                    provider="stepfun",
                )
            else:
                return EditResponse(
                    success=False,
                    error="Step1X-Edit returned no images",
                    latency_ms=latency,
                    model="step1x-edit",
                    provider="stepfun",
                )

        except Exception as e:
            logger.error("[StepEditEditor] %s", e, exc_info=True)
            return EditResponse(
                success=False,
                error=str(e),
                latency_ms=(time.time() - t0) * 1000,
                model="step1x-edit",
                provider="stepfun",
            )

    @staticmethod
    def _extract_image(data: dict) -> Optional[str]:
        """Extract first b64 image from StepFun response."""
        for item in data.get("data", []):
            if "b64_json" in item:
                return item["b64_json"]
            if "url" in item:
                return item["url"]
        return None


# ═════════════════════════════════════════════════════════════════════
# Nano-Banana Fallback — fal.ai (generation-only, no edit)
# ═════════════════════════════════════════════════════════════════════

class NanoBananaEditor:
    """
    Nano-Banana via fal.ai — last-resort fallback for generation.

    Nano-Banana doesn't do instruction-based editing, only text-to-image.
    Used as final fallback when all edit models are down:
    regenerate from scratch using the execution prompt.
    """

    ENDPOINT = "fal-ai/nano-banana"
    COST = 0.011

    def __init__(self, api_key: str, base_url: str = "https://queue.fal.run"):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")

    def edit(
        self,
        instruction: str,
        source_image_b64: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
    ) -> EditResponse:
        """
        Generate from scratch (no source image support).
        Falls back to pure text-to-image.
        """
        import httpx

        t0 = time.time()
        try:
            payload = {
                "prompt": instruction,
                "image_size": {"width": width, "height": height},
            }

            with httpx.Client(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Key {self._api_key}",
                    "Content-Type": "application/json",
                },
                timeout=120.0,
            ) as client:
                submit = client.post(f"/{self.ENDPOINT}", json=payload)
                submit.raise_for_status()
                sub_data = submit.json()

                if "request_id" in sub_data:
                    result_data = self._poll(
                        client,
                        sub_data["request_id"],
                        sub_data.get("status_url"),
                        sub_data.get("response_url"),
                    )
                else:
                    result_data = sub_data

            image_url = KontextEditor._extract_image(result_data)
            latency = (time.time() - t0) * 1000

            if image_url:
                return EditResponse(
                    success=True,
                    image_b64=None,
                    latency_ms=latency,
                    model="nano-banana",
                    provider="fal",
                    raw_text=image_url,
                )
            else:
                return EditResponse(
                    success=False,
                    error="Nano-Banana returned no image",
                    latency_ms=latency,
                    model="nano-banana",
                    provider="fal",
                )

        except Exception as e:
            logger.error("[NanoBananaEditor] %s", e, exc_info=True)
            return EditResponse(
                success=False,
                error=str(e),
                latency_ms=(time.time() - t0) * 1000,
                model="nano-banana",
                provider="fal",
            )

    def _poll(
        self,
        client: "httpx.Client",
        request_id: str,
        status_url: Optional[str],
        response_url: Optional[str],
        max_wait: int = 120,
    ) -> dict:
        import time as _time

        _status = status_url or f"{self._base_url}/{self.ENDPOINT}/requests/{request_id}/status"
        _result = response_url or f"{self._base_url}/{self.ENDPOINT}/requests/{request_id}"
        deadline = _time.time() + max_wait

        while _time.time() < deadline:
            resp = client.get(_status)
            if resp.status_code == 200:
                data = resp.json()
                s = data.get("status", "")
                if s == "COMPLETED":
                    final = client.get(_result)
                    final.raise_for_status()
                    return final.json()
                if s in ("FAILED", "CANCELLED"):
                    raise RuntimeError(f"Nano-Banana job {request_id} {s}")
            _time.sleep(1.0)

        raise TimeoutError(f"Nano-Banana job {request_id} timed out after {max_wait}s")


# ═════════════════════════════════════════════════════════════════════
# FallbackChain — Ordered fallback execution
# ═════════════════════════════════════════════════════════════════════

@dataclass
class FallbackAttempt:
    """Record of one fallback attempt."""
    editor:    str
    success:   bool
    error:     str = ""
    latency_ms: float = 0.0


class FallbackChain:
    """
    Ordered fallback chain for semantic editing.

    Tries each editor in order until one succeeds.
    Records all attempts for debugging.

    Default chain (from routing.yaml):
        Kontext → Step1X-Edit → Nano-Banana

    Usage:
        chain = FallbackChain(fal_api_key="...", stepfun_api_key="...")
        resp, attempts = chain.edit(
            instruction="Add a hat",
            source_image_b64="...",
        )
    """

    def __init__(
        self,
        fal_api_key: str = "",
        stepfun_api_key: str = "",
        editors: Optional[list] = None,
    ):
        if editors:
            self._editors = editors
        else:
            self._editors = []
            if fal_api_key:
                self._editors.append(KontextEditor(api_key=fal_api_key))
            if stepfun_api_key:
                self._editors.append(StepEditEditor(api_key=stepfun_api_key))
            if fal_api_key:
                self._editors.append(NanoBananaEditor(api_key=fal_api_key))

    @property
    def chain_names(self) -> list[str]:
        return [type(e).__name__ for e in self._editors]

    def edit(
        self,
        instruction: str,
        source_image_b64: Optional[str] = None,
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
    ) -> tuple[EditResponse, list[FallbackAttempt]]:
        """
        Try each editor in the chain until one succeeds.

        Returns:
            (EditResponse, list[FallbackAttempt]) — result + attempt log
        """
        attempts: list[FallbackAttempt] = []

        for editor in self._editors:
            editor_name = type(editor).__name__
            logger.info("[FallbackChain] Trying %s ...", editor_name)

            if isinstance(editor, KontextEditor):
                resp = editor.edit(
                    instruction=instruction,
                    source_image_b64=source_image_b64,
                    width=width,
                    height=height,
                    seed=seed,
                )
            elif isinstance(editor, StepEditEditor):
                resp = editor.edit(
                    instruction=instruction,
                    source_image_b64=source_image_b64,
                )
            elif isinstance(editor, NanoBananaEditor):
                resp = editor.edit(
                    instruction=instruction,
                    source_image_b64=source_image_b64,
                    width=width,
                    height=height,
                )
            else:
                # Generic fallback — call .edit() with common signature
                resp = editor.edit(
                    instruction=instruction,
                    source_image_b64=source_image_b64,
                )

            attempts.append(FallbackAttempt(
                editor=editor_name,
                success=resp.success,
                error=resp.error or "",
                latency_ms=resp.latency_ms,
            ))

            if resp.success:
                logger.info(
                    "[FallbackChain] %s succeeded (%.0f ms)",
                    editor_name, resp.latency_ms,
                )
                return resp, attempts

            logger.warning(
                "[FallbackChain] %s failed: %s", editor_name, resp.error,
            )

        # All failed
        return EditResponse(
            success=False,
            error=f"All {len(self._editors)} fallback editors failed",
            model="",
            provider="",
        ), attempts
