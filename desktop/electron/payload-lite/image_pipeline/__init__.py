"""
image_pipeline — Local image generation subtree.

CANONICAL LIVE PATH
-------------------
Only ``image_pipeline.anime_pipeline`` is wired into the running chatbot.
Reach it through ``services/chatbot/routes/anime_pipeline.py`` →
``/api/anime-pipeline/*`` (bridged by ``core/anime_pipeline_service.py``).
The single orchestrator is ``image_pipeline.anime_pipeline.orchestrator``.

DEFERRED / NOT INTEGRATED
-------------------------
The following subpackages are early design scaffolding ("Nano Banana"
blueprint) and are NOT imported by any live route or orchestrator. They
are kept for potential future restart; do not treat them as authoritative:

    job_schema.py, workflow/, planner/, evaluator/,
    semantic_editor/, multi_reference/, BLUEPRINT.md

See ``image_pipeline/DEPRECATED.md`` for details and the rule for new work.

BACKWARD-COMPAT EXPORTS (unchanged, do not add new ones here)
-------------------------------------------------------------
Existing imports from ``image_pipeline.job_schema`` continue to work, but
new code should import from ``image_pipeline.anime_pipeline`` instead.
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
