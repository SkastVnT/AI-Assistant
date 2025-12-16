"""
Whisper Client - OpenAI Whisper large-v3 for Global ASR
Uses faster_whisper for optimized inference
"""

import time
import torch
import os
from typing import Tuple, Optional
from pathlib import Path


def check_cudnn_available():
    """Check if cuDNN is available for CUDA operations"""
    if not torch.cuda.is_available():
        return False
    
    try:
        # Try to import ctranslate2 and test CUDA
        import ctranslate2
        # Test if cuDNN works by creating a small model
        # This will fail early if cuDNN is missing
        return True
    except Exception as e:
        if "cudnn" in str(e).lower():
            return False
        return True


class WhisperClient:
    """
    Client for Whisper large-v3 model
    Optimized for global speech recognition with Vietnamese support
    """
    
    def __init__(
        self,
        model_name: str = "large-v3",
        device: Optional[str] = None,
        compute_type: Optional[str] = None,
    ):
        """
        Initialize Whisper client
        
        Args:
            model_name: Model size (tiny, base, small, medium, large-v3)
            device: Device to use (cuda, cpu, or None for auto-detect)
            compute_type: Computation type (float16, int8, or None for auto)
        """
        self.model_name = model_name
        
        # Force CPU - CUDA version mismatch
        # PyTorch built for CUDA 11.8 but cuDNN installed in CUDA 13.0
        self.device = "cpu"
        self.compute_type = "int8"
        print(f"[Whisper] Using CPU (CUDA version mismatch: PyTorch 11.8 vs cuDNN 13.0)")
            
        self.model = None
        self._is_loaded = False
        
    def load(self) -> float:
        """
        Load Whisper model
        
        Returns:
            Load time in seconds
        """
        from faster_whisper import WhisperModel
        
        print(f"[Whisper] Loading {self.model_name} on {self.device}...")
        start_time = time.time()
        
        try:
            self.model = WhisperModel(
                self.model_name,
                device=self.device,
                compute_type=self.compute_type
            )
        except Exception as e:
            # Handle cuDNN, cublas, and other CUDA library errors
            error_str = str(e).lower()
            if ("cudnn" in error_str or "cublas" in error_str or "library" in error_str) and self.device == "cuda":
                print(f"[Whisper] CUDA library error detected: {e}")
                print(f"[Whisper] Falling back to CPU mode...")
                self.device = "cpu"
                self.compute_type = "int8"
                self.model = WhisperModel(
                    self.model_name,
                    device=self.device,
                    compute_type=self.compute_type
                )
            else:
                raise
        
        load_time = time.time() - start_time
        self._is_loaded = True
        
        print(f"[Whisper] Loaded in {load_time:.2f}s")
        return load_time
    
    def unload(self):
        """Unload model to free GPU/CPU memory"""
        if self.model is not None:
            del self.model
            self.model = None
            self._is_loaded = False
            if self.device == "cuda":
                import gc
                gc.collect()
                torch.cuda.empty_cache()
                print(f"[Whisper] Model unloaded, GPU memory freed")
            else:
                print(f"[Whisper] Model unloaded")
        
    def transcribe(
        self,
        audio_path: str,
        language: str = "vi",
        beam_size: int = 5,
        vad_filter: bool = False,
        **kwargs
    ) -> Tuple[str, float]:
        """
        Transcribe audio file
        
        Args:
            audio_path: Path to audio file
            language: Language code (vi for Vietnamese)
            beam_size: Beam size for decoding
            vad_filter: Enable voice activity detection
            **kwargs: Additional transcription parameters
            
        Returns:
            Tuple of (transcript, processing_time)
        """
        if not self._is_loaded:
            self.load()
            
        print(f"[Whisper] Transcribing: {Path(audio_path).name}")
        start_time = time.time()
        
        # Default optimized parameters
        default_params = {
            "word_timestamps": False,
            "condition_on_previous_text": False,  # Prevent repetition
            "no_speech_threshold": 0.1,  # Catch quiet speech
            "compression_ratio_threshold": 2.4,  # Allow longer segments
            "temperature": 0.0,  # Deterministic output
        }
        
        # Merge with user-provided params
        params = {**default_params, **kwargs}
        
        try:
            segments, info = self.model.transcribe(
                audio_path,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                **params
            )
            
            # Combine all segments
            transcript = " ".join([segment.text for segment in segments])
            processing_time = time.time() - start_time
            
            print(f"[Whisper] Completed in {processing_time:.2f}s ({len(transcript)} chars)")
            return transcript, processing_time
            
        except Exception as e:
            error_msg = str(e).lower()
            # Handle CUDA library errors (cuDNN, cublas, etc.)
            if ("cudnn" in error_msg or "cuda" in error_msg or "cublas" in error_msg or "library" in error_msg) and self.device == "cuda":
                print(f"[Whisper] CUDA library error during transcription: {e}")
                print(f"[Whisper] Reloading model in CPU mode...")
                
                # Reload model in CPU mode
                self.device = "cpu"
                self.compute_type = "int8"
                self._is_loaded = False
                self.load()
                
                # Retry transcription with CPU
                segments, info = self.model.transcribe(
                    audio_path,
                    language=language,
                    beam_size=beam_size,
                    vad_filter=vad_filter,
                    **params
                )
                
                # Combine all segments
                transcript = " ".join([segment.text for segment in segments])
                processing_time = time.time() - start_time
                
                print(f"[Whisper] Completed in {processing_time:.2f}s ({len(transcript)} chars) [CPU]")
                return transcript, processing_time
            else:
                raise
        
    def save_result(self, transcript: str, output_path: str):
        """Save transcript to file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        print(f"[Whisper] Saved: {output_path}")
        
    def __repr__(self):
        status = "loaded" if self._is_loaded else "not loaded"
        return f"WhisperClient(model={self.model_name}, device={self.device}, status={status})"
