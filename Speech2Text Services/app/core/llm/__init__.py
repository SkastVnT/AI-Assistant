"""
LLM clients for speech-to-text models
- WhisperClient: OpenAI Whisper large-v3
- PhoWhisperClient: VinAI PhoWhisper-large  
- GeminiClient: Google Gemini 2.0 Flash (Free)
- SpeakerDiarizationClient: pyannote.audio speaker diarization
"""

from .whisper_client import WhisperClient
from .phowhisper_client import PhoWhisperClient
from .gemini_client import GeminiClient
from .diarization_client import SpeakerDiarizationClient, SpeakerSegment

__all__ = [
    "WhisperClient", 
    "PhoWhisperClient", 
    "GeminiClient",
    "SpeakerDiarizationClient",
    "SpeakerSegment"
]
