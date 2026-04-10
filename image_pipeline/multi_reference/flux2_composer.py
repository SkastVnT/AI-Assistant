"""
image_pipeline.multi_reference.flux2_composer — FLUX.2 multi-reference via BFL API.

Implements the FLUX.2 image editing / multi-reference composition protocol
documented at https://docs.bfl.ai/flux_2/flux2_image_editing:

    POST /v1/{model_id}  →  {"id": task_id}
    GET  /v1/get_result?id={task_id}  →  {"status": "Ready", "result": {"sample": url}}

Payload for multi-reference:
    {
        "prompt": "...",
        "input_image":   "<b64 or url>",   # image 1 (required)
        "input_image_2": "<b64 or url>",   # image 2 (optional)
        ...
        "input_image_8": "<b64 or url>",   # image 8 (max for pro/max)
        "width": int,
        "height": int,
        "seed": int,
        "output_format": "jpeg" | "png",
        "safety_tolerance": 2
    }

Models:
    flux-2-pro          — production, up to 8 refs, $0.03/MP
    flux-2-pro-preview  — latest improvements
    flux-2-max          — highest quality + grounding search, up to 8 refs, $0.07/MP
    flux-2-klein-4b     — sub-second, up to 4 refs, $0.001/MP
    flux-2-klein-9b     — balanced, up to 4 refs, $0.002/MP
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

import httpx

from image_pipeline.multi_reference.reference_manager import RefPlan

logger = logging.getLogger(__name__)

# ── Model catalog ────────────────────────────────────────────────────

FLUX2_MODELS = {
    "flux2-pro":          "flux-2-pro",
    "flux2-pro-preview":  "flux-2-pro-preview",
    "flux2-max":          "flux-2-max",
    "flux2-klein-4b":     "flux-2-klein-4b",
    "flux2-klein-9b":     "flux-2-klein-9b",
    "flux2-klein-9b-preview": "flux-2-klein-9b-preview",
}

FLUX2_COST_PER_MP = {
    "flux2-pro":          0.030,
    "flux2-pro-preview":  0.030,
    "flux2-max":          0.070,
    "flux2-klein-4b":     0.001,
    "flux2-klein-9b":     0.002,
    "flux2-klein-9b-preview": 0.002,
}

FLUX2_MAX_REFS = {
    "flux2-pro":          8,
    "flux2-pro-preview":  8,
    "flux2-max":          8,
    "flux2-klein-4b":     4,
    "flux2-klein-9b":     4,
    "flux2-klein-9b-preview": 4,
}


# ── Response type ────────────────────────────────────────────────────

@dataclass
class ComposeResponse:
    """Result from a FLUX.2 composition call."""
    success:     bool
    image_url:   Optional[str] = None     # Signed URL (valid 10 min per BFL docs)
    image_b64:   Optional[str] = None     # Only if we download the result
    latency_ms:  float         = 0.0
    model:       str           = ""
    provider:    str           = "bfl"
    cost_usd:    float         = 0.0
    task_id:     str           = ""
    error:       Optional[str] = None
    metadata:    dict          = field(default_factory=dict)


# ── Composer ─────────────────────────────────────────────────────────

class Flux2Composer:
    """
    FLUX.2 multi-reference composition via BFL direct API.

    Usage:
        composer = Flux2Composer(api_key="...")
        resp = composer.compose(
            prompt="The person from image 1 wearing outfit from image 2",
            ref_plan=plan,          # from ReferenceManager.resolve()
            model="flux2-pro",
        )
    """

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.bfl.ai/v1",
        timeout: float = 180.0,
        poll_interval: float = 1.5,
        max_poll_wait: float = 120.0,
    ):
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._poll_interval = poll_interval
        self._max_poll_wait = max_poll_wait
        self._http: Optional[httpx.Client] = None

    def _get_http(self) -> httpx.Client:
        if self._http is None or self._http.is_closed:
            self._http = httpx.Client(
                base_url=self._base_url,
                headers={
                    "X-Key": self._api_key,
                    "Content-Type": "application/json",
                },
                timeout=httpx.Timeout(
                    connect=8.0, read=self._timeout, write=30.0, pool=5.0,
                ),
            )
        return self._http

    # ── Main compose call ─────────────────────────────────────────

    def compose(
        self,
        prompt: str,
        ref_plan: RefPlan,
        model: str = "flux2-pro",
        width: Optional[int] = None,
        height: Optional[int] = None,
        seed: Optional[int] = None,
        output_format: str = "png",
        safety_tolerance: int = 2,
    ) -> ComposeResponse:
        """
        Submit a multi-reference composition to FLUX.2 and poll for result.

        Args:
            prompt:           Edit/composition instruction
            ref_plan:         Resolved references from ReferenceManager
            model:            Model key (flux2-pro, flux2-max, etc.)
            width/height:     Output dimensions (multiples of 16; None = match input)
            seed:             Reproducibility seed
            output_format:    "png" or "jpeg"
            safety_tolerance: 0 (strict) to 6 (permissive)

        Returns:
            ComposeResponse with signed image URL.
        """
        model_id = FLUX2_MODELS.get(model)
        if not model_id:
            return ComposeResponse(
                success=False,
                error=f"Unknown FLUX.2 model: {model}",
                model=model,
            )

        max_refs = FLUX2_MAX_REFS.get(model, 8)
        if ref_plan.count > max_refs:
            logger.warning(
                "[Flux2Composer] %d refs exceeds %s limit (%d), truncating",
                ref_plan.count, model, max_refs,
            )

        t0 = time.time()

        try:
            payload = self._build_payload(
                prompt=prompt,
                ref_plan=ref_plan,
                max_refs=max_refs,
                width=width,
                height=height,
                seed=seed,
                output_format=output_format,
                safety_tolerance=safety_tolerance,
            )

            client = self._get_http()

            # Submit task
            submit_resp = client.post(f"/{model_id}", json=payload)
            submit_resp.raise_for_status()
            submit_data = submit_resp.json()
            task_id = submit_data.get("id", "")

            if not task_id:
                return ComposeResponse(
                    success=False,
                    error="BFL did not return task ID",
                    model=model,
                )

            # Poll for result
            polling_url = submit_data.get("polling_url")
            result_data = self._poll(task_id, polling_url)

            image_url = result_data.get("result", {}).get("sample", "")
            latency = (time.time() - t0) * 1000

            # Estimate cost based on megapixels
            mp = (
                ((width or 1024) * (height or 1024)) / 1_000_000
            )
            cost_per_mp = FLUX2_COST_PER_MP.get(model, 0.030)
            # BFL reports actual cost in response; use that if available
            actual_cost = submit_data.get("cost")
            cost = float(actual_cost) / 100 if actual_cost else cost_per_mp * mp

            return ComposeResponse(
                success=bool(image_url),
                image_url=image_url or None,
                latency_ms=latency,
                model=model,
                cost_usd=cost,
                task_id=task_id,
                metadata={
                    "refs_used": ref_plan.count,
                    "input_mp": submit_data.get("input_mp"),
                    "output_mp": submit_data.get("output_mp"),
                },
            )

        except httpx.HTTPStatusError as e:
            body = e.response.text[:300]
            logger.error("[Flux2Composer] HTTP %d: %s", e.response.status_code, body)
            return ComposeResponse(
                success=False,
                error=f"BFL HTTP {e.response.status_code}: {body}",
                model=model,
                latency_ms=(time.time() - t0) * 1000,
            )
        except TimeoutError as e:
            return ComposeResponse(
                success=False,
                error=str(e),
                model=model,
                latency_ms=(time.time() - t0) * 1000,
            )
        except Exception as e:
            logger.error("[Flux2Composer] %s", e, exc_info=True)
            return ComposeResponse(
                success=False,
                error=str(e),
                model=model,
                latency_ms=(time.time() - t0) * 1000,
            )

    # ── Text-to-image (no reference images) ───────────────────────

    def generate(
        self,
        prompt: str,
        model: str = "flux2-pro",
        width: int = 1024,
        height: int = 1024,
        seed: Optional[int] = None,
    ) -> ComposeResponse:
        """Pure text-to-image via FLUX.2 (no input images)."""
        empty_plan = RefPlan()
        return self.compose(
            prompt=prompt,
            ref_plan=empty_plan,
            model=model,
            width=width,
            height=height,
            seed=seed,
        )

    # ── Health check ──────────────────────────────────────────────

    def health_check(self) -> bool:
        """Check if BFL API is reachable."""
        try:
            client = self._get_http()
            resp = client.get("/get_result", params={"id": "test"})
            return resp.status_code in (200, 404, 422)
        except Exception:
            return False

    # ── Internal: payload builder ─────────────────────────────────

    @staticmethod
    def _build_payload(
        prompt: str,
        ref_plan: RefPlan,
        max_refs: int,
        width: Optional[int],
        height: Optional[int],
        seed: Optional[int],
        output_format: str,
        safety_tolerance: int,
    ) -> dict:
        """
        Build the FLUX.2 API payload with multi-reference image fields.

        FLUX.2 API convention:
            input_image   = image 1 (primary)
            input_image_2 = image 2
            ...
            input_image_8 = image 8
        """
        payload: dict = {"prompt": prompt}

        # Add reference images as indexed fields
        image_map = ref_plan.input_image_map()
        # Respect model's max ref limit
        allowed_keys = {"input_image"} | {
            f"input_image_{i}" for i in range(2, max_refs + 1)
        }
        for key, value in image_map.items():
            if key in allowed_keys:
                payload[key] = value

        # Optional dimensions (multiples of 16)
        if width:
            payload["width"] = (width // 16) * 16
        if height:
            payload["height"] = (height // 16) * 16

        if seed is not None:
            payload["seed"] = seed

        payload["output_format"] = output_format
        payload["safety_tolerance"] = safety_tolerance

        return payload

    # ── Internal: polling ─────────────────────────────────────────

    def _poll(
        self,
        task_id: str,
        polling_url: Optional[str] = None,
    ) -> dict:
        """
        Poll BFL for task completion.

        Uses polling_url from submit response if available,
        otherwise constructs from task_id.
        """
        client = self._get_http()
        url = polling_url or f"{self._base_url}/get_result"

        deadline = time.time() + self._max_poll_wait
        while time.time() < deadline:
            if polling_url:
                resp = client.get(polling_url)
            else:
                resp = client.get(url, params={"id": task_id})

            data = resp.json()
            status = data.get("status", "")

            if status == "Ready":
                return data
            if status in ("Error", "Failed", "Request Moderated"):
                raise RuntimeError(
                    f"FLUX.2 task {task_id} {status}: {data}"
                )

            time.sleep(self._poll_interval)

        raise TimeoutError(
            f"FLUX.2 task {task_id} timed out after {self._max_poll_wait}s"
        )

    # ── Cleanup ───────────────────────────────────────────────────

    def close(self) -> None:
        """Release HTTP client."""
        if self._http and not self._http.is_closed:
            self._http.close()
