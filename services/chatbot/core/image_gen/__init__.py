"""
Image Generation Engine â€” Modern multi-provider system.

Architecture:
    providers/      â†’ Backends: fal.ai, Replicate, BFL, OpenAI, ComfyUI
    enhancer.py     â†’ LLM-powered prompt rewriting
    router.py       â†’ Smart provider selection + fallback
    session.py      â†’ Per-conversation state + edit chains
    storage.py      â†’ Local + cloud image persistence

Usage:
    from core.image_gen import ImageGenerationRouter, SessionManager, ImageStorage

    router = ImageGenerationRouter()
    result = router.generate("a cat on a rooftop at sunset")
"""

from .character_detector import CharacterDetector, CharacterMatch, DetectionResult
from .enhancer import STYLE_PRESETS, PromptEnhancer, create_enhancer
from .intent import ImageIntent, IntentResult, detect_intent
from .orchestrator import ImageOrchestrator, OrchestratorResult
from .providers.base import LoraSpec
from .router import ImageGenerationRouter, QualityMode
from .session import ImageSession, SessionManager
from .storage import ImageStorage

__all__ = [
    "ImageGenerationRouter",
    "QualityMode",
    "ImageSession",
    "SessionManager",
    "ImageStorage",
    "PromptEnhancer",
    "STYLE_PRESETS",
    "create_enhancer",
    "LoraSpec",
    "CharacterDetector",
    "CharacterMatch",
    "DetectionResult",
    # Orchestration layer
    "ImageIntent",
    "IntentResult",
    "detect_intent",
    "ImageOrchestrator",
    "OrchestratorResult",
]
