"""
image_pipeline.anime_pipeline.agents — Pipeline agent implementations.

Each agent has a single execute(job, config) → job interface.
"""

from .vision_analyst import VisionAnalystAgent
from .layer_planner import LayerPlannerAgent
from .composition_pass import CompositionPassAgent
from .structure_lock import StructureLockAgent
from .cleanup_pass import CleanupPassAgent
from .beauty_pass import BeautyPassAgent
from .critique import CritiqueAgent
from .upscale import UpscaleAgent
from .upscale_service import UpscaleService
from .final_ranker import FinalRanker, score_candidate, rank_candidates
from .output_manifest import build_output_manifest, manifest_to_json
from .refine_loop import (
    RefineLoopAgent,
    critique_image,
    decide_refine_action,
    patch_plan_from_critique,
    run_refine_round,
)
from .detection_detail import DetectionDetailAgent, DetectedRegion, DetectionResult
from .detection_inpaint import DetectionInpaintAgent

__all__ = [
    "VisionAnalystAgent",
    "LayerPlannerAgent",
    "CompositionPassAgent",
    "StructureLockAgent",
    "CleanupPassAgent",
    "BeautyPassAgent",
    "CritiqueAgent",
    "UpscaleAgent",
    "UpscaleService",
    "FinalRanker",
    "score_candidate",
    "rank_candidates",
    "build_output_manifest",
    "manifest_to_json",
    "RefineLoopAgent",
    "critique_image",
    "decide_refine_action",
    "patch_plan_from_critique",
    "run_refine_round",
    "DetectionDetailAgent",
    "DetectedRegion",
    "DetectionResult",
    "DetectionInpaintAgent",
]
