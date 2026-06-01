"""Live adapter from blueprint benchmark jobs to the LOCAL anime orchestrator."""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from urllib.parse import urlsplit

from image_pipeline.anime_pipeline import AnimePipelineJob, AnimePipelineOrchestrator
from image_pipeline.anime_pipeline.agents.output_manifest import build_output_manifest
from image_pipeline.anime_pipeline.config import AnimePipelineConfig, load_config
from image_pipeline.anime_pipeline.preflight import run_preflight
from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy
from image_pipeline.evaluator.benchmark_runner import BenchmarkRunner
from image_pipeline.evaluator.scorer import Scorer
from image_pipeline.job_schema import ImageJob, RunMetadata
from image_pipeline.paths import CONFIGS_DIR, STORAGE_DIR

_SUITE = CONFIGS_DIR / "anime_benchmark_suite.yaml"


def _local_path(value: str) -> Path:
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        raise ValueError(f"Benchmark fixtures must be local paths: {value}")
    path = Path(value)
    if not path.is_absolute():
        path = CONFIGS_DIR / path
    if not path.is_file():
        raise FileNotFoundError(f"Missing local benchmark fixture: {path}")
    return path


def _read_b64(value: str | None) -> str | None:
    if not value:
        return None
    return base64.b64encode(_local_path(value).read_bytes()).decode("ascii")


class AnimeBenchmarkAdapter:
    """Executes a real LOCAL anime pipeline run for BenchmarkRunner."""

    def __init__(self, config: AnimePipelineConfig | None = None):
        self._config = config or load_config()
        self._policy = RuntimePolicy.from_config(self._config)

    async def __call__(self, job: ImageJob) -> tuple[Path, RunMetadata]:
        preflight = run_preflight(self._config, probe_remote=True)
        if preflight.readiness == "blocked" or not preflight.endpoint_health.get(
            "comfyui", False
        ):
            raise RuntimeError(
                f"Anime LOCAL live benchmark preflight failed: {preflight.to_dict()}"
            )

        references = [
            encoded
            for encoded in (_read_b64(ref.image_url) for ref in job.reference_images)
            if encoded
        ]
        anime_job = AnimePipelineJob(
            user_prompt=job.user_instruction,
            language=job.language,
            reference_images_b64=references,
            source_image_b64=_read_b64(job.source_image_url),
            deployment_profile=self._config.deployment_profile,
            content_mode="sfw",
            validator_mode="local",
            network_policy=self._policy.to_dict(),
            benchmark_version=self._config.benchmark_version,
        )
        orchestrator = AnimePipelineOrchestrator(self._config)
        await asyncio.to_thread(orchestrator.run, anime_job)
        if not anime_job.final_image_b64:
            raise RuntimeError(f"Anime pipeline produced no output: {anime_job.error}")

        output_dir = STORAGE_DIR / "benchmarks" / self._config.benchmark_version / "outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{anime_job.job_id}.png"
        output_path.write_bytes(base64.b64decode(anime_job.final_image_b64))
        manifest_path = output_path.with_suffix(".manifest.json")
        manifest_path.write_text(
            json.dumps(build_output_manifest(anime_job), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        metadata = RunMetadata(
            job_id=anime_job.job_id,
            session_id=anime_job.session_id,
            total_latency_ms=anime_job.total_latency_ms,
            stage_timings=dict(anime_job.stage_timings_ms),
            execution_map={
                stage: "local" for stage in anime_job.stage_timings_ms
            },
            correction_rounds=anime_job.refine_rounds,
            final_provider="comfyui",
            final_model=anime_job.models_used[-1] if anime_job.models_used else "",
            tags=[
                "anime_local",
                self._config.deployment_profile,
                self._config.benchmark_version,
            ],
        )
        metadata.finalize()
        return output_path, metadata


def build_local_anime_benchmark_runner(
    config: AnimePipelineConfig | None = None,
) -> BenchmarkRunner:
    """Create a live benchmark runner wired only to LOCAL pipeline and scorer."""
    cfg = config or load_config()
    policy = RuntimePolicy.from_config(cfg)
    scorer = Scorer(
        benchmark_cfg_path=_SUITE,
        local_only=True,
        local_vlm_url=cfg.local_vlm_url,
        local_vlm_model=cfg.local_vlm_model,
        runtime_policy=policy,
    )
    return BenchmarkRunner(
        benchmark_path=_SUITE,
        scorer=scorer,
        pipeline_fn=AnimeBenchmarkAdapter(cfg),
    )

