"""
AI Models for VistralS2T v3.5
Model wrappers for Whisper, PhoWhisper, Qwen, and Diarization
"""

from .whisper_model import WhisperClient, check_cudnn_available
from .phowhisper_model import PhoWhisperClient
from .qwen_model import QwenClient
from .diarization_model import SpeakerDiarizationClient, SpeakerSegment

__all__ = [
    "WhisperClient",
    "PhoWhisperClient", 
    "QwenClient",
    "SpeakerDiarizationClient",
    "SpeakerSegment",
    "check_cudnn_available"
]
