"""
Image generation providers — multi-backend support.
Each provider wraps a different API/service for generating images.
"""

from .base import (
    BaseImageProvider, ImageRequest, ImageResult,
    ImageMode, ProviderTier,
)
from .fal_provider import FalProvider
from .replicate_provider import ReplicateProvider
from .bfl_provider import BFLProvider
from .openai_provider import OpenAIImageProvider
from .comfyui_provider import ComfyUIProvider
from .together_provider import TogetherProvider
from .stepfun_provider import StepFunProvider

__all__ = [
    "BaseImageProvider", "ImageRequest", "ImageResult",
    "ImageMode", "ProviderTier",
    "FalProvider", "ReplicateProvider", "BFLProvider",
    "OpenAIImageProvider", "ComfyUIProvider", "TogetherProvider",
    "StepFunProvider",
]

# Registry: name → class
PROVIDER_REGISTRY: dict[str, type[BaseImageProvider]] = {
    "fal":       FalProvider,
    "replicate": ReplicateProvider,
    "bfl":       BFLProvider,
    "openai":    OpenAIImageProvider,
    "comfyui":   ComfyUIProvider,
    "together":  TogetherProvider,
    "stepfun":   StepFunProvider,
}
