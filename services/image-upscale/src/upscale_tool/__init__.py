"""
Image Upscaler Tool
Wrapper for Real-ESRGAN and other upscaling models
"""

__version__ = "1.0.0"
__author__ = "AI-Assistant Team"

from .upscaler import ImageUpscaler
from .config import load_config, UpscaleConfig

__all__ = ['ImageUpscaler', 'load_config', 'UpscaleConfig']
