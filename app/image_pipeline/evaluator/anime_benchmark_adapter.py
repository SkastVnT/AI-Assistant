"""Live adapter from blueprint benchmark jobs to the LOCAL anime orchestrator."""

from __future__ import annotations

import asyncio
import base64
import json
from pathlib import Path
from urllib.parse import urlsplit

import yaml

from image_pipeline.anime_pipeline import (
    AnimePipelineJob,
    LocalAnimeTaskDispatcher,
    PipelineReference,
)
from image_pipeline.anime_pipeline.agents.output_manifest import build_output_manifest
from image_pipeline.anime_pipeline.config import AnimePipelineConfig, load_config
from image_pipeline.anime_pipeline.preflight import run_preflight
from image_pipeline.anime_pipeline.runtime_policy import RuntimePolicy
from image_pipeline.evaluator.benchmark_config import resolve_suite_path
from image_pipeline.evaluator.benchmark_runner import BenchmarkExecution, BenchmarkRunner
from image_pipeline.evaluator.scorer import Scorer
from image_pipeline.job_schema import ImageJob, RunMetadata
from image_pipeline.paths import CONFIGS_DIR, STORAGE_DIR

_SUITE = CONFIGS_DIR / "anime_benchmark_suite.yaml"


def _local_path(value: str, artifact_root: Path | None = None) -> Path:
    parsed = urlsplit(value)
    if parsed.scheme or parsed.netloc:
        raise ValueError(f"Benchmark fixtures must be local paths: {value}")
    path = Path(value)
    if not path.is_absolute():
        if artifact_root:
            path = artifact_root / path
        else:
            path = (
                CONFIGS_DIR.parents[1] / path
                if path.parts and path.parts[0] == ".local"
                else CONFIGS_DIR / path
            )
    if not path.is_file():
        raise FileNotFoundError(f"Missing local benchmark fixture: {path}")
    return path


def _read_b64(value: str | None, artifact_root: Path | None = None) -> str | None:
    if not value:
        return None
    return base64.b64encode(_local_path(value, artifact_root).read_bytes()).decode(
        "ascii"
    )


class AnimeBenchmarkAdapter:
    """Executes a real LOCAL anime pipeline run for BenchmarkRunner."""

    def __init__(
        self,
        config: AnimePipelineConfig | None = None,
        *,
        content_mode: str = "sfw",
        adult_verified: bool = False,
        artifact_root: str | Path | None = None,
    ):
        self._config = config or load_config()
        self._policy = RuntimePolicy.from_config(self._config)
        self._content_mode = content_mode
        self._adult_verified = adult_verified
        self._artifact_root = Path(artifact_root) if artifact_root else None
        self._output_dir = (
            self._artifact_root / "outputs"
            if self._artifact_root
            else STORAGE_DIR / "benchmarks" / self._config.benchmark_version / "outputs"
        )

    def prepare_suite(
        self,
        cases: list[dict],
        *,
        parity: bool = False,
        run_id: str = "",
    ) -> None:
        """Run endpoint preflight and fail fast with the full missing fixture list."""
        preflight = run_preflight(
            self._config,
            probe_remote=True,
            parity=parity,
        )
        if preflight.readiness == "blocked" or not preflight.endpoint_health.get(
            "comfyui", False
        ):
            raise RuntimeError(
                f"Anime LOCAL live benchmark preflight failed: {preflight.to_dict()}"
            )
        if self._artifact_root and run_id:
            self._output_dir = self._artifact_root / run_id / "outputs"

        missing: list[str] = []
        for case in cases:
            setup = case.get("setup", {})
            fixture_values = [setup.get("source_image")]
            fixture_values.extend(
                ref.get("image")
                for ref in setup.get("references", [])
                if isinstance(ref, dict)
            )
            for value in fixture_values:
                if not value:
                    continue
                try:
                    _local_path(str(value), self._artifact_root)
                except (FileNotFoundError, ValueError) as exc:
                    missing.append(str(exc))
        if missing:
            raise RuntimeError(
                "Missing local benchmark fixtures:\n" + "\n".join(sorted(set(missing)))
            )

    async def __call__(self, job: ImageJob) -> BenchmarkExecution:
        source_path = (
            _local_path(job.source_image_url, self._artifact_root)
            if job.source_image_url
            else None
        )
        reference_paths = [
            _local_path(ref.image_url, self._artifact_root)
            for ref in job.reference_images
            if ref.image_url
        ]
        typed_references = [
            PipelineReference(role=ref.role.value, image_b64=encoded)
            for ref in job.reference_images
            if (encoded := _read_b64(ref.image_url, self._artifact_root))
        ]
        references = [reference.image_b64 for reference in typed_references]
        anime_job = AnimePipelineJob(
            user_prompt=job.user_instruction,
            language=job.language,
            reference_images_b64=references,
            references=typed_references,
            source_image_b64=_read_b64(job.source_image_url, self._artifact_root),
            task_type=job.intent or "t2i",
            edit_turns=list(job.edit_turns),
            deployment_profile=self._config.deployment_profile,
            content_mode=self._content_mode,
            validator_mode="local",
            adult_verified=self._adult_verified,
            adult_attestation_source=(
                "request" if self._content_mode == "adult_only" else ""
            ),
            network_policy=self._policy.to_dict(),
            benchmark_version=self._config.benchmark_version,
        )
        dispatcher = LocalAnimeTaskDispatcher(self._config)
        await asyncio.to_thread(dispatcher.run, anime_job)
        if not anime_job.final_image_b64:
            raise RuntimeError(f"Anime pipeline produced no output: {anime_job.error}")

        output_dir = self._output_dir
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{anime_job.job_id}.png"
        output_path.write_bytes(base64.b64decode(anime_job.final_image_b64))
        manifest_path = output_path.with_suffix(".manifest.json")
        manifest_path.write_text(
            json.dumps(build_output_manifest(anime_job), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        turn_artifacts: list[Path] = []
        for intermediate in anime_job.intermediates:
            if not intermediate.stage.startswith("semantic_edit_turn_"):
                continue
            turn_path = output_dir / f"{anime_job.job_id}.{intermediate.stage}.png"
            turn_path.write_bytes(base64.b64decode(intermediate.image_b64))
            turn_artifacts.append(turn_path)

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
        return BenchmarkExecution(
            output_path=output_path,
            run_metadata=metadata,
            source_image_path=source_path,
            reference_paths=reference_paths,
            turn_artifacts=turn_artifacts,
            route_provenance=dict(anime_job.metadata.get("route_provenance", {})),
        )


def build_local_anime_benchmark_runner(
    config: AnimePipelineConfig | None = None,
    *,
    suite: str = "auto",
    adult_verified: bool = False,
    artifact_root: str | Path | None = None,
) -> BenchmarkRunner:
    """Create a live benchmark runner wired only to LOCAL pipeline and scorer."""
    cfg = config or load_config()
    policy = RuntimePolicy.from_config(cfg)
    suite_path = resolve_suite_path(suite, cfg.deployment_profile)
    suite_config = yaml.safe_load(suite_path.read_text(encoding="utf-8")) or {}
    content_mode = str(suite_config.get("content_mode", "sfw"))
    scorer = Scorer(
        benchmark_cfg_path=suite_path,
        local_only=True,
        local_vlm_url=cfg.local_vlm_url,
        local_vlm_model=cfg.local_vlm_model,
        runtime_policy=policy,
    )
    return BenchmarkRunner(
        benchmark_path=suite_path,
        scorer=scorer,
        pipeline_fn=AnimeBenchmarkAdapter(
            cfg,
            content_mode=content_mode,
            adult_verified=adult_verified,
            artifact_root=artifact_root,
        ),
        artifact_root=artifact_root,
    )
