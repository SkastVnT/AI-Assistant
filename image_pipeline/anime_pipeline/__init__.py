"""
image_pipeline.anime_pipeline — Multi-pass anime image generation pipeline.

Implements a 7-stage layered workflow:
    1. Vision Analyst   — analyze input/reference images with vision AI
    2. Layer Planner    — create structured layer plan from analysis
    3. Composition Pass — generate controllable draft via ComfyUI
    4. Structure Lock   — extract lineart/depth/canny control layers
    5. Beauty Pass      — final redraw with best anime checkpoint + ControlNet
    6. Critique         — vision-based quality scoring
    7. Upscale          — RealESRGAN final upscale

Gated by IMAGE_PIPELINE_V2=true feature flag.
Optimized for 12 GB VRAM systems using SDXL anime checkpoints.

Usage:
    from image_pipeline.anime_pipeline import AnimePipelineOrchestrator, AnimePipelineJob

    orchestrator = AnimePipelineOrchestrator()
    job = AnimePipelineJob(user_prompt="anime girl in cherry blossoms")
    result = orchestrator.run(job)
    # or streaming:
    for event in orchestrator.run_stream(job):
        send_sse(event)
"""

from .schemas import (
    AnimePipelineJob,
    AnimePipelineStatus,
    ControlInput,
    CritiqueDimension,
    CritiqueReport,
    CritiqueResult,          # backward compat alias
    IntermediateImage,
    LayerPassConfig,          # backward compat alias
    LayerPlan,
    PassConfig,
    RefineAction,
    RefineActionType,
    RefineDecision,
    StructureLayer,
    StructureLayerType,
    VisionAnalysis,
)
from .comfy_client import ComfyClient, ComfyJobResult
from .config import VRAMProfile, VRAMProfileConfig, resolve_vram_profile
from .vision_service import VisionService, DiscrepancyReport
from .workflow_builder import WorkflowBuilder
from .critique_service import CritiqueService
from .result_store import ResultStore
from .workflow_serializer import serialize_workflow, get_workflow_version
from . import vision_prompts
from . import planner_presets
from .planner_presets import PlannerPreset, PassOverride, get_preset, list_presets
from .agents.layer_planner import make_layer_plan
from .vram_manager import (
    is_oom_error,
    RetryContext,
    build_retry_context,
    step_down_resolution,
    escalate_to_lowvram,
    strip_preview_nodes,
    free_models_between_passes,
    log_pass_memory_mode,
    log_retry_cause,
    log_final_fallback,
    submit_with_oom_retry,
)
from .orchestrator import AnimePipelineOrchestrator

__all__ = [
    # Schemas
    "AnimePipelineJob",
    "AnimePipelineStatus",
    "ControlInput",
    "CritiqueDimension",
    "CritiqueReport",
    "CritiqueResult",
    "IntermediateImage",
    "LayerPassConfig",
    "LayerPlan",
    "PassConfig",
    "RefineAction",
    "RefineActionType",
    "RefineDecision",
    "StructureLayer",
    "StructureLayerType",
    "VisionAnalysis",
    # Services
    "ComfyClient",
    "ComfyJobResult",
    "VisionService",
    "DiscrepancyReport",
    "WorkflowBuilder",
    "CritiqueService",
    "ResultStore",
    # Helpers
    "serialize_workflow",
    "get_workflow_version",
    "vision_prompts",
    "planner_presets",
    # Presets & standalone planner
    "PlannerPreset",
    "PassOverride",
    "get_preset",
    "list_presets",
    "make_layer_plan",
    # VRAM management
    "VRAMProfile",
    "VRAMProfileConfig",
    "resolve_vram_profile",
    "is_oom_error",
    "RetryContext",
    "build_retry_context",
    "step_down_resolution",
    "escalate_to_lowvram",
    "strip_preview_nodes",
    "free_models_between_passes",
    "log_pass_memory_mode",
    "log_retry_cause",
    "log_final_fallback",
    "submit_with_oom_retry",
    # Orchestrator
    "AnimePipelineOrchestrator",
]
