# -*- coding: utf-8 -*-
"""
Voice Activity Detection (VAD) Utilities
Detect speech segments to optimize diarization
"""
import numpy as np
import torch
from typing import List, Tuple

try:
    # Try to import silero-vad
    import torchaudio
    SILERO_AVAILABLE = True
except ImportError:
    SILERO_AVAILABLE = False
    print("[WARNING] torchaudio not available. VAD will use simple energy-based detection.")


class VADProcessor:
    """
    Voice Activity Detection processor
    Detects speech segments to reduce processing time
    """
    
    def __init__(self, method: str = "silero", threshold: float = 0.5):
        """
        Initialize VAD processor
        
        Args:
            method: "silero" (AI-based, accurate) or "energy" (simple, fast)
            threshold: Speech probability threshold (0-1)
        """
        self.method = method
        self.threshold = threshold
        self.model = None
        
        if method == "silero" and SILERO_AVAILABLE:
            self._load_silero()
        elif method == "silero":
            print("[VAD] Silero not available, falling back to energy-based VAD")
            self.method = "energy"
    
    def _load_silero(self):
        """Load Silero VAD model"""
        try:
            print("[VAD] Loading Silero VAD model...")
            self.model, utils = torch.hub.load(
                repo_or_dir='snakers4/silero-vad',
                model='silero_vad',
                force_reload=False,
                onnx=False
            )
            self.get_speech_timestamps = utils[0]
            print("[VAD] Silero VAD loaded successfully")
        except Exception as e:
            print(f"[VAD] Failed to load Silero: {e}")
            print("[VAD] Falling back to energy-based VAD")
            self.method = "energy"
            self.model = None
    
    def detect_speech_segments(
        self,
        audio: np.ndarray,
        sample_rate: int,
        min_speech_duration: float = 0.5,
        min_silence_duration: float = 0.3
    ) -> List[Tuple[float, float]]:
        """
        Detect speech segments in audio
        
        Args:
            audio: Audio signal (numpy array)
            sample_rate: Sample rate in Hz
            min_speech_duration: Minimum speech duration in seconds
            min_silence_duration: Minimum silence duration in seconds
        
        Returns:
            List of (start_time, end_time) tuples in seconds
        """
        if self.method == "silero" and self.model is not None:
            return self._detect_silero(
                audio, sample_rate, 
                min_speech_duration, 
                min_silence_duration
            )
        else:
            return self._detect_energy(
                audio, sample_rate,
                min_speech_duration,
                min_silence_duration
            )
    
    def _detect_silero(
        self,
        audio: np.ndarray,
        sample_rate: int,
        min_speech_duration: float,
        min_silence_duration: float
    ) -> List[Tuple[float, float]]:
        """Detect speech using Silero VAD"""
        try:
            # Convert to torch tensor
            audio_tensor = torch.from_numpy(audio).float()
            
            # Resample to 16kHz if needed (Silero requirement)
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(
                    orig_freq=sample_rate,
                    new_freq=16000
                )
                audio_tensor = resampler(audio_tensor)
                sample_rate = 16000
            
            # Get speech timestamps
            speech_timestamps = self.get_speech_timestamps(
                audio_tensor,
                self.model,
                threshold=self.threshold,
                sampling_rate=sample_rate,
                min_speech_duration_ms=int(min_speech_duration * 1000),
                min_silence_duration_ms=int(min_silence_duration * 1000)
            )
            
            # Convert to seconds
            segments = [
                (ts['start'] / sample_rate, ts['end'] / sample_rate)
                for ts in speech_timestamps
            ]
            
            return segments
            
        except Exception as e:
            print(f"[VAD] Silero detection failed: {e}")
            print("[VAD] Falling back to energy-based detection")
            return self._detect_energy(
                audio, sample_rate,
                min_speech_duration,
                min_silence_duration
            )
    
    def _detect_energy(
        self,
        audio: np.ndarray,
        sample_rate: int,
        min_speech_duration: float,
        min_silence_duration: float
    ) -> List[Tuple[float, float]]:
        """Simple energy-based VAD"""
        # Calculate frame-wise energy
        frame_length = int(0.025 * sample_rate)  # 25ms frames
        hop_length = int(0.010 * sample_rate)    # 10ms hop
        
        # Compute RMS energy per frame
        frames = []
        for i in range(0, len(audio) - frame_length, hop_length):
            frame = audio[i:i + frame_length]
            energy = np.sqrt(np.mean(frame ** 2))
            frames.append(energy)
        
        frames = np.array(frames)
        
        # Adaptive threshold (mean + 0.5 * std)
        threshold = np.mean(frames) + 0.5 * np.std(frames)
        
        # Detect speech frames
        speech_frames = frames > threshold
        
        # Convert to segments
        segments = []
        in_speech = False
        start_frame = 0
        
        for i, is_speech in enumerate(speech_frames):
            if is_speech and not in_speech:
                # Speech starts
                start_frame = i
                in_speech = True
            elif not is_speech and in_speech:
                # Speech ends
                start_time = start_frame * hop_length / sample_rate
                end_time = i * hop_length / sample_rate
                duration = end_time - start_time
                
                if duration >= min_speech_duration:
                    segments.append((start_time, end_time))
                
                in_speech = False
        
        # Handle last segment
        if in_speech:
            start_time = start_frame * hop_length / sample_rate
            end_time = len(audio) / sample_rate
            duration = end_time - start_time
            
            if duration >= min_speech_duration:
                segments.append((start_time, end_time))
        
        # Merge close segments
        merged_segments = self._merge_segments(
            segments, 
            min_silence_duration
        )
        
        return merged_segments
    
    def _merge_segments(
        self,
        segments: List[Tuple[float, float]],
        min_gap: float
    ) -> List[Tuple[float, float]]:
        """Merge segments that are close together"""
        if not segments:
            return []
        
        merged = [segments[0]]
        
        for start, end in segments[1:]:
            last_start, last_end = merged[-1]
            
            if start - last_end < min_gap:
                # Merge segments
                merged[-1] = (last_start, end)
            else:
                merged.append((start, end))
        
        return merged
    
    def filter_audio_by_speech(
        self,
        audio: np.ndarray,
        sample_rate: int,
        padding: float = 0.2
    ) -> np.ndarray:
        """
        Extract only speech segments from audio
        
        Args:
            audio: Input audio
            sample_rate: Sample rate
            padding: Padding around speech segments in seconds
        
        Returns:
            Filtered audio with only speech
        """
        segments = self.detect_speech_segments(audio, sample_rate)
        
        if not segments:
            print("[VAD] No speech detected, returning original audio")
            return audio
        
        # Extract speech segments with padding
        speech_audio = []
        for start, end in segments:
            start_sample = max(0, int((start - padding) * sample_rate))
            end_sample = min(len(audio), int((end + padding) * sample_rate))
            speech_audio.append(audio[start_sample:end_sample])
        
        # Concatenate all speech segments
        filtered_audio = np.concatenate(speech_audio)
        
        speech_duration = len(filtered_audio) / sample_rate
        total_duration = len(audio) / sample_rate
        saved_percent = (1 - speech_duration / total_duration) * 100
        
        print(f"[VAD] Speech: {speech_duration:.1f}s / {total_duration:.1f}s")
        print(f"[VAD] Saved {saved_percent:.1f}% processing time")
        
        return filtered_audio


# Convenience function
def detect_speech_segments(
    audio: np.ndarray,
    sample_rate: int,
    method: str = "silero",
    threshold: float = 0.5
) -> List[Tuple[float, float]]:
    """
    Quick function to detect speech segments
    
    Args:
        audio: Audio signal
        sample_rate: Sample rate
        method: "silero" or "energy"
        threshold: Speech threshold
    
    Returns:
        List of (start, end) time tuples
    """
    vad = VADProcessor(method=method, threshold=threshold)
    return vad.detect_speech_segments(audio, sample_rate)
