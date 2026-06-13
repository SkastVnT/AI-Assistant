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
from .native_comfy_editor import NativeComfySemanticEditor

__all__ = [
    "SemanticEditor",
    "NativeComfySemanticEditor",
    "QwenClient",
    "FallbackChain",
    "KontextEditor",
    "StepEditEditor",
]
