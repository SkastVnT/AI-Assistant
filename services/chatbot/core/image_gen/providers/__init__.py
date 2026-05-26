"""
Image generation providers â€” multi-backend support.
Each provider wraps a different API/service for generating images.
"""

from .base import (
    BaseImageProvider,
    ImageMode,
    ImageRequest,
    ImageResult,
    ProviderTier,
)
from .bfl_provider import BFLProvider
from .comfyui_fast import ComfyUIFastProvider
from .comfyui_provider import ComfyUIProvider
from .fal_provider import FalProvider
from .nano_banana_provider import NanoBananaProvider
from .openai_provider import OpenAIImageProvider
from .replicate_provider import ReplicateProvider
from .stepfun_provider import StepFunProvider
from .together_provider import TogetherProvider

__all__ = [
    "BaseImageProvider",
    "ImageRequest",
    "ImageResult",
    "ImageMode",
    "ProviderTier",
    "FalProvider",
    "ReplicateProvider",
    "BFLProvider",
    "OpenAIImageProvider",
    "ComfyUIProvider",
    "ComfyUIFastProvider",
    "TogetherProvider",
    "StepFunProvider",
    "NanoBananaProvider",
]

# Registry: name â†’ class
PROVIDER_REGISTRY: dict[str, type[BaseImageProvider]] = {
    "fal": FalProvider,
    "replicate": ReplicateProvider,
    "bfl": BFLProvider,
    "openai": OpenAIImageProvider,
    "comfyui": ComfyUIProvider,
    "comfyui_fast": ComfyUIFastProvider,
    "together": TogetherProvider,
    "stepfun": StepFunProvider,
    "nano_banana": NanoBananaProvider,
}
