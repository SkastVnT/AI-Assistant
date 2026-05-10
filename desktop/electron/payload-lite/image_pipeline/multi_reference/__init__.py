"""
image_pipeline.multi_reference — Stage 4: Multi-reference composition.

Components:
    ReferenceManager   — Download, cache, crop, and tag reference images
    Flux2Composer      — FLUX.2 multi-reference composition via BFL API
    MultiRefComposer   — Facade that owns Stage 4 of the pipeline
"""

from .reference_manager import ReferenceManager
from .flux2_composer import Flux2Composer, ComposeResponse
from .composer import MultiRefComposer

__all__ = [
    "MultiRefComposer",
    "ReferenceManager",
    "Flux2Composer",
    "ComposeResponse",
]
