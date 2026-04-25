"""
image_pipeline.reasoning — Planner-driven reasoning layer (additive, gated by
IMAGE_PIPELINE_V2). See SKILL.md and docs/image_pipeline_v2_overview.md.

This package contains the state and spec contracts that every downstream
reasoning module (prompt_parser, planners, evaluator, correction_router,
execution_planner, comic_assembler) consumes or produces.

Nothing in this package performs I/O, calls an LLM, or talks to ComfyUI.
Runtime modules live in sibling files added in later commits.
"""

from image_pipeline.reasoning.schemas import (
    BoundingBox,
    CharacterAppearance,
    CharacterState,
    ComicSequenceSpec,
    EyeState,
    OutputLayout,
    OverlayElement,
    OverlayKind,
    OverlayPlan,
    PanelRole,
    PropRequirement,
    PropState,
    SceneState,
    SchemaValidationError,
    ShotType,
    SinglePanelSpec,
    ZoneRef,
)

__all__ = [
    "BoundingBox",
    "CharacterAppearance",
    "CharacterState",
    "ComicSequenceSpec",
    "EyeState",
    "OutputLayout",
    "OverlayElement",
    "OverlayKind",
    "OverlayPlan",
    "PanelRole",
    "PropRequirement",
    "PropState",
    "SceneState",
    "SchemaValidationError",
    "ShotType",
    "SinglePanelSpec",
    "ZoneRef",
]
