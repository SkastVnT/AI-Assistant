"""
Audio Utilities for VistralS2T
Functions for audio preprocessing, chunking, and manipulation
"""

import librosa
import soundfile as sf
import numpy as np
from scipy import signal
from pathlib import Path
from typing import Tuple, List, Optional


def preprocess_audio(
    audio_path: str,
    output_path: Optional[str] = None,
    target_sr: int = 32000,
    normalize: bool = True,
    trim_silence: bool = True,
    high_pass_freq: int = 100,
) -> Tuple[np.ndarray, int, str]:
    """
    Preprocess audio file for speech recognition
    
    Args:
        audio_path: Path to input audio file
        output_path: Path to save preprocessed audio (None = auto-generate)
        target_sr: Target sample rate
        normalize: Whether to normalize audio
        trim_silence: Whether to trim leading/trailing silence
        high_pass_freq: High-pass filter cutoff frequency (0 = disable)
        
    Returns:
        Tuple of (audio_data, sample_rate, output_path)
    """
    print(f"[Audio] Loading: {Path(audio_path).name}")
    
    # Load audio
    audio, sr = librosa.load(audio_path, sr=None)
    print(f"[Audio] Original: {sr}Hz, {len(audio)/sr:.1f}s")
    
    # Resample if needed
    if sr != target_sr:
        print(f"[Audio] Resampling: {sr}Hz -> {target_sr}Hz")
        audio = librosa.resample(audio, orig_sr=sr, target_sr=target_sr)
        sr = target_sr
    
    # Normalize
    if normalize:
        print("[Audio] Normalizing...")
        audio = librosa.util.normalize(audio)
    
    # Trim silence
    if trim_silence:
        print("[Audio] Trimming silence...")
        audio, _ = librosa.effects.trim(audio, top_db=20)
    
    # High-pass filter (remove low-frequency noise)
    if high_pass_freq > 0:
        print(f"[Audio] High-pass filter: {high_pass_freq}Hz")
        nyquist = sr / 2
        normal_cutoff = high_pass_freq / nyquist
        b, a = signal.butter(5, normal_cutoff, btype='high', analog=False)
        audio = signal.filtfilt(b, a, audio)
    
    # Auto-generate output path if not provided
    if output_path is None:
        input_path = Path(audio_path)
        output_path = str(input_path.parent / f"{input_path.stem}_cleaned{input_path.suffix}")
    
    # Save preprocessed audio
    print(f"[Audio] Saving: {Path(output_path).name}")
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio, sr)
    
    print(f"[Audio] Preprocessed: {sr}Hz, {len(audio)/sr:.1f}s")
    return audio, sr, output_path


def split_audio_chunks(
    audio: np.ndarray,
    sample_rate: int,
    chunk_duration: int = 30,
    overlap: float = 0.0,
) -> List[np.ndarray]:
    """
    Split audio into chunks for processing
    
    Args:
        audio: Audio data array
        sample_rate: Sample rate of audio
        chunk_duration: Chunk duration in seconds
        overlap: Overlap fraction between chunks (0.0 to 1.0)
        
    Returns:
        List of audio chunks
    """
    chunk_size = int(chunk_duration * sample_rate)
    overlap_size = int(chunk_size * overlap)
    step_size = chunk_size - overlap_size
    
    duration = len(audio) / sample_rate
    num_chunks = int(np.ceil((len(audio) - overlap_size) / step_size))
    
    print(f"[Audio] Splitting into {num_chunks} chunks ({chunk_duration}s each, {overlap*100:.0f}% overlap)")
    
    chunks = []
    for i in range(num_chunks):
        start = i * step_size
        end = min(start + chunk_size, len(audio))
        chunk = audio[start:end]
        chunks.append(chunk)
    
    return chunks


def save_audio(
    audio: np.ndarray,
    sample_rate: int,
    output_path: str,
    format: Optional[str] = None,
) -> str:
    """
    Save audio to file
    
    Args:
        audio: Audio data array
        sample_rate: Sample rate
        output_path: Output file path
        format: Audio format (None = auto-detect from extension)
        
    Returns:
        Output path
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    sf.write(output_path, audio, sample_rate, format=format)
    
    duration = len(audio) / sample_rate
    print(f"[Audio] Saved: {output_path} ({sample_rate}Hz, {duration:.1f}s)")
    
    return output_path


def get_audio_info(audio_path: str) -> dict:
    """
    Get audio file information
    
    Args:
        audio_path: Path to audio file
        
    Returns:
        Dictionary with audio info (duration, sample_rate, channels, etc.)
    """
    audio, sr = librosa.load(audio_path, sr=None)
    
    info = {
        "path": audio_path,
        "sample_rate": sr,
        "duration": len(audio) / sr,
        "samples": len(audio),
        "channels": 1,  # librosa loads as mono
        "dtype": str(audio.dtype),
    }
    
    return info


__all__ = [
    "preprocess_audio",
    "split_audio_chunks",
    "save_audio",
    "get_audio_info",
]
