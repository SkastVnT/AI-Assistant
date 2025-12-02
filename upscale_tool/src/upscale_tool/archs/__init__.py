"""
Architecture modules for different upscaling models
"""

from .swinir_model_arch import SwinIR
from .swinir_model_arch_v2 import Swin2SR
from .scunet_model_arch import SCUNet

__all__ = ['SwinIR', 'Swin2SR', 'SCUNet']
