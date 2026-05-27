"""
image_pipeline.semantic_editor — The editing brain of the Nano Banana-like system.

Stage 3 (§12): Semantic edit / generation pass.

Components:
    QwenClient       — Primary: Qwen-Image-Edit-2511 via vLLM (VPS)
    FallbackChain    — Fallback: Kontext (fal) → Step1X-Edit (StepFun) → Nano-Banana (fal)
    SemanticEditor   — Facade that routes to primary or falls through the chain
"""

from .qwen_client import QwenClient
from .fallback_editors import FallbackChain, KontextEditor, StepEditEditor
from .editor import SemanticEditor

__all__ = [
    "SemanticEditor",
    "QwenClient",
    "FallbackChain",
    "KontextEditor",
    "StepEditEditor",
]
