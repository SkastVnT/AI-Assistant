"""
PhoWhisper Client - VinAI PhoWhisper-large for Vietnamese ASR
Optimized for Vietnamese speech recognition with chunking strategy
"""

import time
import torch
import librosa
import numpy as np
from typing import Tuple, Optional, List
from pathlib import Path


class PhoWhisperClient:
    """
    Client for PhoWhisper-large model
    Vietnamese-specialized speech recognition with chunking
    """
    
    def __init__(
        self,
        model_name: str = "vinai/PhoWhisper-large",
        device: Optional[str] = None,
        chunk_duration: int = 30,
    ):
        """
        Initialize PhoWhisper client
        
        Args:
            model_name: HuggingFace model name
            device: Device to use (cuda:0, cpu, or None for auto)
            chunk_duration: Audio chunk duration in seconds
        """
        self.model_name = model_name
        self.device = device or ("cuda:0" if torch.cuda.is_available() else "cpu")
        self.chunk_duration = chunk_duration
        self.pipe = None
        self._is_loaded = False
        
    def load(self) -> float:
        """
        Load PhoWhisper model
        
        Returns:
            Load time in seconds
        """
        from transformers import pipeline
        
        print(f"[PhoWhisper] Loading {self.model_name} on {self.device}...")
        start_time = time.time()
        
        try:
            # Try GPU with float16
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device=self.device if self.device != "cpu" else -1,
                torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            )
            print("[PhoWhisper] GPU acceleration enabled")
        except Exception as e:
            print(f"[PhoWhisper] GPU error: {e}")
            print("[PhoWhisper] Falling back to CPU...")
            self.pipe = pipeline(
                "automatic-speech-recognition",
                model=self.model_name,
                device=-1,
            )
            self.device = "cpu"
            print("[PhoWhisper] CPU fallback")
            
        load_time = time.time() - start_time
        self._is_loaded = True
        
        print(f"[PhoWhisper] Loaded in {load_time:.2f}s")
        return load_time
        
    def transcribe(
        self,
        audio_path: str,
        language: str = "vietnamese",
        sample_rate: int = 16000,
        **kwargs
    ) -> Tuple[str, float]:
        """
        Transcribe audio file with chunking
        
        Args:
            audio_path: Path to audio file
            language: Language for transcription
            sample_rate: Target sample rate (16kHz for PhoWhisper)
            **kwargs: Additional generation parameters
            
        Returns:
            Tuple of (transcript, processing_time)
        """
        if not self._is_loaded:
            self.load()
            
        print(f"[PhoWhisper] Transcribing: {Path(audio_path).name}")
        start_time = time.time()
        
        # Load audio
        audio_data, sr = librosa.load(audio_path, sr=sample_rate)
        duration = len(audio_data) / sr
        print(f"[PhoWhisper] Audio duration: {duration:.1f}s")
        
        # Process in chunks
        chunk_size = self.chunk_duration * sr
        num_chunks = int(np.ceil(duration / self.chunk_duration))
        
        print(f"[PhoWhisper] Processing {num_chunks} chunks ({self.chunk_duration}s each)")
        
        transcripts = []
        for i in range(num_chunks):
            chunk_start = time.time()
            start_sample = i * chunk_size
            end_sample = min((i + 1) * chunk_size, len(audio_data))
            chunk = audio_data[start_sample:end_sample]
            
            # Transcribe chunk
            generate_kwargs = {
                "language": language,
                "task": "transcribe",
                **kwargs
            }
            
            result = self.pipe(chunk, generate_kwargs=generate_kwargs)
            chunk_text = result["text"].strip()
            
            if chunk_text:  # Only add non-empty chunks
                transcripts.append(chunk_text)
                
            chunk_time = time.time() - chunk_start
            print(f"[PhoWhisper] Chunk {i+1}/{num_chunks} -> {chunk_time:.1f}s ({len(chunk_text)} chars)")
            
        # Combine all chunks
        full_transcript = " ".join(transcripts)
        processing_time = time.time() - start_time
        
        print(f"[PhoWhisper] Completed in {processing_time:.2f}s ({len(full_transcript)} chars)")
        return full_transcript, processing_time
        
    def save_result(self, transcript: str, output_path: str):
        """Save transcript to file"""
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(transcript)
        print(f"[PhoWhisper] Saved: {output_path}")
        
    def __repr__(self):
        status = "loaded" if self._is_loaded else "not loaded"
        return f"PhoWhisperClient(model={self.model_name}, device={self.device}, chunks={self.chunk_duration}s, status={status})"
