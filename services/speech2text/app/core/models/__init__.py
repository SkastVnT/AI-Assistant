"""
AI Models for VistralS2T v3.5
Model wrappers for Whisper, PhoWhisper, Qwen, and Diarization

Uses lazy imports to avoid import errors when optional dependencies
like pyannote are not available.
"""

import logging
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

# ============================================================================
# Numpy 2.x Compatibility Shim
# ============================================================================
# Numpy 2.0 removed np.NaN - add backwards compatibility
try:
    import numpy as np
    if not hasattr(np, 'NaN'):
        np.NaN = np.nan
        logger.debug("Added numpy.NaN compatibility shim")
except ImportError:
    pass
# ============================================================================

# ============================================================================
# Torchaudio Compatibility Shim
# ============================================================================
# Newer versions of torchaudio (2.x) removed set_audio_backend and 
# get_audio_backend functions. Some libraries like speechbrain still 
# expect these functions to exist. We add stub implementations.
try:
    import torchaudio
    if not hasattr(torchaudio, 'set_audio_backend'):
        def _set_audio_backend_stub(backend: str) -> None:
            """Stub for torchaudio.set_audio_backend (deprecated in 2.x)"""
            logger.debug(f"set_audio_backend({backend}) - ignored (torchaudio 2.x)")
        torchaudio.set_audio_backend = _set_audio_backend_stub
        logger.info("Added torchaudio.set_audio_backend compatibility shim")
    
    if not hasattr(torchaudio, 'get_audio_backend'):
        def _get_audio_backend_stub() -> str:
            """Stub for torchaudio.get_audio_backend (deprecated in 2.x)"""
            return "soundfile"
        torchaudio.get_audio_backend = _get_audio_backend_stub
        logger.info("Added torchaudio.get_audio_backend compatibility shim")
except ImportError:
    pass
# ============================================================================

# Always available imports - with error handling
_WhisperClient = None
_check_cudnn_available = None
_PhoWhisperClient = None
_QwenClient = None

try:
    from .whisper_model import WhisperClient as _WhisperClient, check_cudnn_available as _check_cudnn_available
except Exception as e:
    logger.warning(f"WhisperClient unavailable: {e}")

try:
    from .phowhisper_model import PhoWhisperClient as _PhoWhisperClient
except Exception as e:
    logger.warning(f"PhoWhisperClient unavailable: {e}")

try:
    from .qwen_model import QwenClient as _QwenClient
except Exception as e:
    logger.warning(f"QwenClient unavailable: {e}")


# Placeholder classes for when imports fail
class WhisperClientPlaceholder:
    """Placeholder when WhisperClient is unavailable."""
    def __init__(self, *args, **kwargs):
        raise ImportError("WhisperClient dependencies are not available.")

class PhoWhisperClientPlaceholder:
    """Placeholder when PhoWhisperClient is unavailable."""
    def __init__(self, *args, **kwargs):
        raise ImportError("PhoWhisperClient dependencies are not available.")

class QwenClientPlaceholder:
    """Placeholder when QwenClient is unavailable."""
    def __init__(self, *args, **kwargs):
        raise ImportError("QwenClient dependencies are not available.")


# Set exports with fallbacks
WhisperClient = _WhisperClient or WhisperClientPlaceholder
PhoWhisperClient = _PhoWhisperClient or PhoWhisperClientPlaceholder
QwenClient = _QwenClient or QwenClientPlaceholder

def check_cudnn_available():
    """Check if cuDNN is available"""
    if _check_cudnn_available:
        return _check_cudnn_available()
    return False

# Lazy import for diarization (optional dependency)
_SpeakerDiarizationClient = None
_SpeakerSegment = None
_diarization_available = None


def _check_diarization():
    """Check if diarization is available and load it lazily"""
    global _SpeakerDiarizationClient, _SpeakerSegment, _diarization_available
    
    if _diarization_available is not None:
        return _diarization_available
    
    try:
        from .diarization_model import SpeakerDiarizationClient, SpeakerSegment
        _SpeakerDiarizationClient = SpeakerDiarizationClient
        _SpeakerSegment = SpeakerSegment
        _diarization_available = True
        logger.info("Speaker diarization module loaded successfully")
    except ImportError as e:
        _diarization_available = False
        logger.warning(f"Speaker diarization unavailable: {e}")
    except Exception as e:
        _diarization_available = False
        logger.warning(f"Error loading diarization: {e}")
    
    return _diarization_available


def get_diarization_client():
    """Get the SpeakerDiarizationClient class if available"""
    if _check_diarization():
        return _SpeakerDiarizationClient
    return None


def get_speaker_segment():
    """Get the SpeakerSegment class if available"""
    if _check_diarization():
        return _SpeakerSegment
    return None


# For backwards compatibility, try to expose these
try:
    from .diarization_model import SpeakerDiarizationClient, SpeakerSegment
except ImportError:
    # Create placeholder classes
    class SpeakerDiarizationClient:
        def __init__(self, *args, **kwargs):
            raise ImportError("pyannote.audio is not installed. Install with: pip install pyannote.audio")
    
    class SpeakerSegment:
        def __init__(self, *args, **kwargs):
            raise ImportError("pyannote.audio is not installed")


__all__ = [
    "WhisperClient",
    "PhoWhisperClient", 
    "QwenClient",
    "SpeakerDiarizationClient",
    "SpeakerSegment",
    "check_cudnn_available",
    "get_diarization_client",
    "get_speaker_segment"
]
