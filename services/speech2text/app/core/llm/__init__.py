"""
LLM clients for speech-to-text models
- WhisperClient: OpenAI Whisper large-v3
- PhoWhisperClient: VinAI PhoWhisper-large  
- GeminiClient: Google Gemini 2.0 Flash (Free)
- OpenAIClient: OpenAI GPT-4o-mini
- DeepSeekClient: DeepSeek Chat (Most cost-effective)
- MultiLLMClient: Unified interface with retry mechanism
- SpeakerDiarizationClient: pyannote.audio speaker diarization
"""

from .whisper_client import WhisperClient
from .phowhisper_client import PhoWhisperClient
from .gemini_client import GeminiClient

# Optional imports - allow graceful failure if dependencies missing
try:
    from .openai_client import OpenAIClient
except ImportError:
    OpenAIClient = None
    print("[WARNING] OpenAIClient not available - openai library not installed or incompatible")

try:
    from .deepseek_client import DeepSeekClient
except ImportError:
    DeepSeekClient = None
    print("[WARNING] DeepSeekClient not available - openai library not installed or incompatible")

from .multi_llm_client import MultiLLMClient
from .diarization_client import SpeakerDiarizationClient, SpeakerSegment

__all__ = [
    "WhisperClient", 
    "PhoWhisperClient", 
    "GeminiClient",
    "OpenAIClient",
    "DeepSeekClient",
    "MultiLLMClient",
    "SpeakerDiarizationClient",
    "SpeakerSegment"
]
