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
from image_pipeline.reasoning.capability_router import (
    CapabilityDecision,
    CapabilityRequest,
    RequestKind,
    classify,
)
from image_pipeline.reasoning.prompt_revision import RevisedPrompt, revise
from image_pipeline.reasoning.prompt_parser import ParseResult, parse
from image_pipeline.reasoning.panel_spec_validator import (
    ValidationIssue,
    ValidationResult,
    validate_panel,
    validate_sequence,
)
from image_pipeline.reasoning.state import (
    CharacterStateManager,
    PropStateManager,
    StateResolver,
    default_resolver,
    extract_scene,
)

__all__ = [
    # schemas
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
    # capability router
    "CapabilityDecision",
    "CapabilityRequest",
    "RequestKind",
    "classify",
    # prompt revision
    "RevisedPrompt",
    "revise",
    # prompt parser
    "ParseResult",
    "parse",
    # validator
    "ValidationIssue",
    "ValidationResult",
    "validate_panel",
    "validate_sequence",
    # state managers (cycle 2)
    "CharacterStateManager",
    "PropStateManager",
    "StateResolver",
    "default_resolver",
    "extract_scene",
]
