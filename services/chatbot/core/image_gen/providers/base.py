"""
Base provider interface for all image generation backends.
Any provider must implement this contract.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
import enum


class ImageMode(str, enum.Enum):
    TEXT_TO_IMAGE = "t2i"
    IMAGE_TO_IMAGE = "i2i"     # edit/transform existing image
    INPAINT       = "inpaint"  # fill masked area


class ProviderTier(str, enum.Enum):
    ULTRA  = "ultra"   # SOTA quality, slower/expensive
    HIGH   = "high"    # Great quality, balanced
    FAST   = "fast"    # Speed optimized, slightly lower quality
    LOCAL  = "local"   # Free, runs on local GPU


@dataclass
class ImageRequest:
    prompt:          str
    negative_prompt: str                = ""
    mode:            ImageMode          = ImageMode.TEXT_TO_IMAGE
    source_image_b64: Optional[str]     = None   # for i2i / inpaint
    mask_b64:        Optional[str]      = None   # for inpaint
    strength:        float              = 0.8    # i2i denoising (0-1)
    width:           int                = 1024
    height:          int                = 1024
    steps:           int                = 28
    guidance:        float              = 3.5
    seed:            Optional[int]      = None
    style_preset:    Optional[str]      = None   # "photorealistic", "anime", etc.
    num_images:      int                = 1
    extra:           dict               = field(default_factory=dict)


@dataclass
class ImageResult:
    success:      bool
    images_b64:   list[str]            = field(default_factory=list)
    images_url:   list[str]            = field(default_factory=list)
    provider:     str                  = ""
    model:        str                  = ""
    prompt_used:  str                  = ""
    latency_ms:   float                = 0.0
    cost_usd:     float                = 0.0
    metadata:     dict                 = field(default_factory=dict)
    error:        Optional[str]        = None


class BaseImageProvider(ABC):
    """Abstract base for all image generation providers."""

    name: str = "base"
    tier: ProviderTier = ProviderTier.HIGH
    supports_i2i: bool = False
    supports_inpaint: bool = False
    cost_per_image: float = 0.0   # USD estimate

    def __init__(self, api_key: str = "", base_url: str = "", **kwargs):
        self.api_key  = api_key
        self.base_url = base_url
        self._configured = bool(api_key or base_url)

    @property
    def is_available(self) -> bool:
        return self._configured

    @abstractmethod
    def generate(self, req: ImageRequest) -> ImageResult:
        """Synchronous generation — providers implement this."""
        ...

    def health_check(self) -> bool:
        """Optional: check if provider is reachable."""
        return self.is_available
