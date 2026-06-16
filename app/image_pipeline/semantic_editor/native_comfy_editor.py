"""Native ComfyUI semantic editing for standalone LOCAL deployments."""

from __future__ import annotations

import time
from typing import Any

from image_pipeline.anime_pipeline.comfy_client import ComfyClient
from image_pipeline.anime_pipeline.config import AnimePipelineConfig, load_config
from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy
from image_pipeline.anime_pipeline.workflow_builder import WorkflowBuilder
from image_pipeline.semantic_editor.qwen_client import EditResponse


class NativeComfySemanticEditor:
    """Run Qwen Image Edit through an operator-exported native ComfyUI graph."""

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
        self._policy.assert_url(self._client.base_url, purpose="comfyui_semantic_edit")

    def edit(
        self,
        *,
        instruction: str,
        source_image_b64: str,
        reference_images_b64: list[str] | None = None,
        seed: int = -1,
        job_id: str = "",
        extra_values: dict[str, Any] | None = None,
    ) -> EditResponse:
        """Edit an image locally without assuming a chat-completions protocol."""

        provider = self._config.native_providers.get("qwen_image_edit")
        if not provider:
            return EditResponse(
                success=False,
                provider="comfyui-native",
                model="Qwen-Image-Edit-2511",
                error="qwen_image_edit native provider is not configured",
            )

        values: dict[str, Any] = {
            "instruction": instruction,
            "prompt": instruction,
            "source_image_b64": source_image_b64,
            "reference_images_b64": reference_images_b64 or [],
            "seed": seed,
        }
        values.update(extra_values or {})

        started = time.time()
        try:
            workflow = self._builder.build_native("qwen_image_edit", provider, values)
            result = self._client.submit_workflow(
                workflow,
                job_id=job_id,
                pass_name="semantic_edit",
            )
        except Exception as exc:
            return EditResponse(
                success=False,
                provider="comfyui-native",
                model=str(provider.get("model", "Qwen-Image-Edit-2511")),
                latency_ms=(time.time() - started) * 1000,
                error=str(exc),
            )

        return EditResponse(
            success=result.success and bool(result.images_b64),
            image_b64=result.images_b64[0] if result.images_b64 else None,
            latency_ms=result.duration_ms or (time.time() - started) * 1000,
            provider="comfyui-native",
            model=str(provider.get("model", "Qwen-Image-Edit-2511")),
            error=result.error or result.validation_error or None,
        )

