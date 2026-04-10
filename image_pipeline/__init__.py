"""
image_pipeline — Nano Banana-like multi-stage image generation & editing system.

Architecture (§11.2 / §12):
    job_schema.py       → Canonical data contracts for the entire pipeline
    planner/            → Stage 0-1: intent parsing, constraint extraction, prompt layers
    semantic_editor/    → Stage 3: Qwen-Image-Edit / fallback editors
    multi_reference/    → Stage 4: FLUX.2 multi-reference composition
    refinement/         → Stage 5: Fill inpainting, ADetailer, IP-Adapter
    evaluator/          → Stage 6-7: 8-dim scoring, correction loop, experiment log
    workflow/           → Capability-based routing (task type → model chain)
    orchestrator.py     → Master 9-stage pipeline controller

Usage:
    from image_pipeline import ImageJob, PipelineOrchestrator
    from image_pipeline.job_schema import PromptSpec, RefinementPlan, EvalResult, RunMetadata
"""

from .job_schema import (
    ImageJob,
    PromptSpec,
    RefinementPlan,
    EvalResult,
    RunMetadata,
    # Supporting types
    ReferenceImage,
    ReferenceRole,
    GenerationParams,
    StageResult,
    StageStatus,
    JobStatus,
    ExecutionLocation,
    ModelUsage,
    EvalDimension,
    RefinementTarget,
    RefinementStrategy,
    OutputTargets,
)

__all__ = [
    "ImageJob",
    "PromptSpec",
    "RefinementPlan",
    "EvalResult",
    "RunMetadata",
    "ReferenceImage",
    "ReferenceRole",
    "GenerationParams",
    "StageResult",
    "StageStatus",
    "JobStatus",
    "ExecutionLocation",
    "ModelUsage",
    "EvalDimension",
    "RefinementTarget",
    "RefinementStrategy",
    "OutputTargets",
]
