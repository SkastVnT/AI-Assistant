"""
Image Generation Engine — Modern multi-provider system.

Architecture:
    providers/      → Backends: fal.ai, Replicate, BFL, OpenAI, ComfyUI
    enhancer.py     → LLM-powered prompt rewriting
    router.py       → Smart provider selection + fallback
    session.py      → Per-conversation state + edit chains
    storage.py      → Local + cloud image persistence

Usage:
    from core.image_gen import ImageGenerationRouter, SessionManager, ImageStorage
    
    router = ImageGenerationRouter()
    result = router.generate("a cat on a rooftop at sunset")
"""

from .router import ImageGenerationRouter, QualityMode
from .session import ImageSession, SessionManager
from .storage import ImageStorage
from .enhancer import PromptEnhancer, STYLE_PRESETS, create_enhancer

__all__ = [
    "ImageGenerationRouter",
    "QualityMode",
    "ImageSession",
    "SessionManager",
    "ImageStorage",
    "PromptEnhancer",
    "STYLE_PRESETS",
    "create_enhancer",
]
