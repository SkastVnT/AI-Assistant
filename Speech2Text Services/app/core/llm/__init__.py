"""
LLM clients for speech-to-text models
- WhisperClient: OpenAI Whisper large-v3
- PhoWhisperClient: VinAI PhoWhisper-large  
- QwenClient: Alibaba Qwen2.5-1.5B-Instruct
- SpeakerDiarizationClient: pyannote.audio speaker diarization
"""

from .whisper_client import WhisperClient
from .phowhisper_client import PhoWhisperClient
from .qwen_client import QwenClient
from .diarization_client import SpeakerDiarizationClient, SpeakerSegment

__all__ = [
    "WhisperClient", 
    "PhoWhisperClient", 
    "QwenClient",
    "SpeakerDiarizationClient",
    "SpeakerSegment"
]
