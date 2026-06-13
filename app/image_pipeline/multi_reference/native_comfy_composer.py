"""Native ComfyUI FLUX.2 Klein multi-reference composition."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from image_pipeline.anime_pipeline.comfy_client import ComfyClient
from image_pipeline.anime_pipeline.config import AnimePipelineConfig, load_config
from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy
from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder


@dataclass
class NativeComposeResponse:
    success: bool = False
    image_b64: str | None = None
    latency_ms: float = 0.0
    provider: str = "comfyui-native"
    model: str = "FLUX.2-klein"
    error: str | None = None


class NativeComfyMultiRefComposer:
    """Run FLUX.2 Klein through an operator-exported local ComfyUI graph."""

    def __init__(
        self,
        config: AnimePipelineConfig | None = None,
        *,
        client: ComfyClient | None = None,
        builder: WorkflowBuilder | None = None,
    ) -> None:
        self._config = config or load_config()
        self._policy = RuntimePolicy.from_config(self._config)
        self._client = client or ComfyClient(base_url=self._config.comfyui_url)
        self._builder = builder or WorkflowBuilder()
        self._policy.assert_url(self._client.base_url, purpose="comfyui_multi_ref")

    def compose(
        self,
        *,
        prompt: str,
        reference_images_b64: list[str],
        seed: int = -1,
        job_id: str = "",
        extra_values: dict[str, Any] | None = None,
    ) -> NativeComposeResponse:
        provider = self._config.native_providers.get("flux2_klein")
        if not provider:
            return NativeComposeResponse(
                error="flux2_klein native provider is not configured"
            )
        if not reference_images_b64:
            return NativeComposeResponse(
                model=str(provider.get("model", "FLUX.2-klein")),
                error="multi_ref requires at least one reference image",
            )

        values: dict[str, Any] = {
            "prompt": prompt,
            "instruction": prompt,
            "reference_images_b64": reference_images_b64,
            "seed": seed,
        }
        for index, image_b64 in enumerate(reference_images_b64):
            values[f"reference_{index}_b64"] = image_b64
        values.update(extra_values or {})

        started = time.time()
        try:
            workflow = self._builder.build_native("flux2_klein", provider, values)
            result = self._client.submit_workflow(
                workflow,
                job_id=job_id,
                pass_name="multi_ref",
            )
        except Exception as exc:
            return NativeComposeResponse(
                latency_ms=(time.time() - started) * 1000,
                model=str(provider.get("model", "FLUX.2-klein")),
                error=str(exc),
            )

        return NativeComposeResponse(
            success=result.success and bool(result.images_b64),
            image_b64=result.images_b64[0] if result.images_b64 else None,
            latency_ms=result.duration_ms or (time.time() - started) * 1000,
            model=str(provider.get("model", "FLUX.2-klein")),
            error=result.error or result.validation_error or None,
        )
