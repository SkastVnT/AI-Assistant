"""Shared LOCAL task dispatcher for API and benchmark execution."""

from __future__ import annotations

import time
from collections.abc import Iterator
from typing import Any

from image_pipeline.multi_reference.native_comfy_composer import (
    NativeComfyMultiRefComposer,
)
from image_pipeline.semantic_editor.native_comfy_editor import (
    NativeComfySemanticEditor,
)

from .config import AnimePipelineConfig, load_config
from .orchestrator import AnimePipelineOrchestrator
from .runtime_policy import RuntimePolicy
from .schemas import AnimePipelineJob, AnimePipelineStatus

_WAI_TASKS = {"", "t2i", "identity", "pose", "anatomy", "complex_background"}


class LocalAnimeTaskDispatcher:
    """Select a local executor while keeping WAI as the generation orchestrator."""

    def __init__(
        self,
        config: AnimePipelineConfig | None = None,
        *,
        orchestrator: AnimePipelineOrchestrator | None = None,
        editor: NativeComfySemanticEditor | None = None,
        composer: NativeComfyMultiRefComposer | None = None,
    ) -> None:
        self._config = config or load_config()
        self._policy = RuntimePolicy.from_config(self._config)
        self._orchestrator = orchestrator
        self._editor = editor
        self._composer = composer

    def run(self, job: AnimePipelineJob) -> AnimePipelineJob:
        list(self.run_stream(job))
        return job

    def run_stream(self, job: AnimePipelineJob) -> Iterator[dict[str, Any]]:
        self._policy.validate_request(
            content_mode=job.content_mode,
            validator_mode=job.validator_mode,
            adult_verified=job.adult_verified,
        )
        task_type = job.task_type or "t2i"
        if task_type in _WAI_TASKS:
            job.metadata["route_provenance"] = {
                "task_type": task_type,
                "executor": "wai_orchestrator",
            }
            yield from self._wai().run_stream(job)
            return
        if task_type == "multi_ref":
            yield from self._run_multi_ref(job)
            return
        if task_type == "semantic_edit":
            yield from self._run_semantic_edit(job)
            return
        if task_type == "multi_turn_edit":
            yield from self._run_multi_turn_edit(job)
            return
        raise ValueError(f"Unsupported LOCAL anime task_type: {task_type}")

    def _wai(self) -> AnimePipelineOrchestrator:
        if self._orchestrator is None:
            self._orchestrator = AnimePipelineOrchestrator(self._config)
        return self._orchestrator

    def _native_start(self, job: AnimePipelineJob, stage: str) -> Iterator[dict[str, Any]]:
        yield {
            "event": "anime_pipeline_pipeline_start",
            "data": {"job_id": job.job_id, "stages": [stage]},
        }
        yield {
            "event": "anime_pipeline_stage_start",
            "data": {"stage": stage, "stage_num": 1, "total_stages": 1},
        }

    def _native_complete(
        self,
        job: AnimePipelineJob,
        *,
        stage: str,
        image_b64: str,
        model: str,
        latency_ms: float,
        executor: str,
    ) -> Iterator[dict[str, Any]]:
        job.final_image_b64 = image_b64
        job.status = AnimePipelineStatus.COMPLETED
        job.total_latency_ms = latency_ms
        job.add_intermediate(stage, image_b64, model=model)
        job.mark_stage(stage, latency_ms)
        job.metadata["route_provenance"] = {
            "task_type": job.task_type,
            "executor": executor,
            "model": model,
        }
        yield {
            "event": "anime_pipeline_stage_complete",
            "data": {"stage": stage, "stage_num": 1, "latency_ms": latency_ms},
        }
        yield {
            "event": "anime_pipeline_pipeline_complete",
            "data": {"job_id": job.job_id, "latency_ms": latency_ms},
        }

    def _native_error(
        self,
        job: AnimePipelineJob,
        *,
        stage: str,
        error: str,
    ) -> Iterator[dict[str, Any]]:
        job.status = AnimePipelineStatus.FAILED
        job.error = error
        yield {
            "event": "anime_pipeline_stage_error",
            "data": {"stage": stage, "error": error},
        }
        yield {
            "event": "anime_pipeline_pipeline_error",
            "data": {"error": error, "has_fallback_image": False},
        }

    def _run_multi_ref(self, job: AnimePipelineJob) -> Iterator[dict[str, Any]]:
        stage = "multi_ref"
        yield from self._native_start(job, stage)
        if not self._config.capabilities.get("flux2_klein", False):
            yield from self._native_error(
                job, stage=stage, error="flux2_klein capability is disabled"
            )
            return
        composer = self._composer or NativeComfyMultiRefComposer(self._config)
        response = composer.compose(
            prompt=job.user_prompt,
            reference_images_b64=job.reference_images_b64,
            job_id=job.job_id,
            extra_values=job.metadata.get("native_values"),
        )
        if not response.success or not response.image_b64:
            yield from self._native_error(
                job, stage=stage, error=response.error or "FLUX.2 composition failed"
            )
            return
        yield from self._native_complete(
            job,
            stage=stage,
            image_b64=response.image_b64,
            model=response.model,
            latency_ms=response.latency_ms,
            executor="native_flux2_klein",
        )

    def _run_semantic_edit(self, job: AnimePipelineJob) -> Iterator[dict[str, Any]]:
        stage = "semantic_edit"
        yield from self._native_start(job, stage)
        if not self._config.capabilities.get("qwen_image_edit", False):
            yield from self._native_error(
                job, stage=stage, error="qwen_image_edit capability is disabled"
            )
            return
        if not job.source_image_b64:
            yield from self._native_error(
                job, stage=stage, error="semantic_edit requires source_image"
            )
            return
        editor = self._editor or NativeComfySemanticEditor(self._config)
        response = editor.edit(
            instruction=job.user_prompt,
            source_image_b64=job.source_image_b64,
            reference_images_b64=job.reference_images_b64,
            job_id=job.job_id,
            extra_values=job.metadata.get("native_values"),
        )
        if not response.success or not response.image_b64:
            yield from self._native_error(
                job, stage=stage, error=response.error or "Qwen image edit failed"
            )
            return
        yield from self._native_complete(
            job,
            stage=stage,
            image_b64=response.image_b64,
            model=response.model,
            latency_ms=response.latency_ms,
            executor="native_qwen_image_edit",
        )

    def _run_multi_turn_edit(self, job: AnimePipelineJob) -> Iterator[dict[str, Any]]:
        stage = "multi_turn_edit"
        yield from self._native_start(job, stage)
        if not self._config.capabilities.get("qwen_image_edit", False):
            yield from self._native_error(
                job, stage=stage, error="qwen_image_edit capability is disabled"
            )
            return
        if not job.source_image_b64 or not job.edit_turns:
            yield from self._native_error(
                job,
                stage=stage,
                error="multi_turn_edit requires source_image and at least one turn",
            )
            return

        editor = self._editor or NativeComfySemanticEditor(self._config)
        started = time.time()
        source = job.source_image_b64
        model = ""
        for index, instruction in enumerate(job.edit_turns, start=1):
            response = editor.edit(
                instruction=instruction,
                source_image_b64=source,
                reference_images_b64=job.reference_images_b64,
                job_id=job.job_id,
                extra_values=job.metadata.get("native_values"),
            )
            if not response.success or not response.image_b64:
                yield from self._native_error(
                    job,
                    stage=stage,
                    error=response.error or f"Qwen image edit turn {index} failed",
                )
                return
            source = response.image_b64
            model = response.model
            job.add_intermediate(
                f"semantic_edit_turn_{index}",
                source,
                model=model,
                turn=index,
                instruction=instruction,
            )
        latency_ms = (time.time() - started) * 1000
        yield from self._native_complete(
            job,
            stage=stage,
            image_b64=source,
            model=model,
            latency_ms=latency_ms,
            executor="native_qwen_image_edit_sequential",
        )
