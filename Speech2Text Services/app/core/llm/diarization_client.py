# -*- coding: utf-8 -*-
"""
Speaker Diarization Client - VistralS2T v3.1
Uses pyannote.audio for speaker segmentation
"""
import os
import time
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import torch
import numpy as np

try:
    from pyannote.audio import Pipeline
    from pyannote.core import Segment, Annotation
    PYANNOTE_AVAILABLE = True
except ImportError:
    PYANNOTE_AVAILABLE = False
    print("[WARNING] pyannote.audio not installed. Speaker diarization unavailable.")


@dataclass
class SpeakerSegment:
    """Represents a segment spoken by one speaker"""
    speaker_id: str          # e.g., "SPEAKER_00", "SPEAKER_01"
    start_time: float        # Start time in seconds
    end_time: float          # End time in seconds
    duration: float          # Duration in seconds
    
    def __repr__(self):
        return f"<Speaker {self.speaker_id}: {self.start_time:.2f}s - {self.end_time:.2f}s ({self.duration:.2f}s)>"


class SpeakerDiarizationClient:
    """
    Client for speaker diarization using pyannote.audio
    
    Features:
    - Automatic speaker detection (2-10 speakers)
    - Timeline segmentation by speaker
    - Optimized for Vietnamese call center conversations
    - GPU acceleration support
    
    Usage:
        diarizer = SpeakerDiarizationClient()
        diarizer.load()
        segments = diarizer.diarize("audio.wav")
        
        for seg in segments:
            print(f"{seg.speaker_id}: {seg.start_time}s - {seg.end_time}s")
    """
    
    def __init__(
        self,
        model_name: str = "pyannote/speaker-diarization-3.1",
        hf_token: Optional[str] = None,
        min_speakers: int = 2,
        max_speakers: int = 10
    ):
        """
        Initialize Speaker Diarization Client
        
        Args:
            model_name: HuggingFace model name (default: pyannote/speaker-diarization-3.1)
            hf_token: HuggingFace access token (required for gated models)
            min_speakers: Minimum number of speakers to detect
            max_speakers: Maximum number of speakers to detect
        """
        if not PYANNOTE_AVAILABLE:
            raise ImportError(
                "pyannote.audio not installed. Install with: pip install pyannote.audio"
            )
        
        self.model_name = model_name
        self.hf_token = hf_token or os.getenv("HF_TOKEN") or os.getenv("HF_API_TOKEN")
        self.min_speakers = min_speakers
        self.max_speakers = max_speakers
        
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        
        print(f"[DIARIZATION] Initialized with model: {model_name}")
        print(f"[DIARIZATION] Device: {self.device}")
        print(f"[DIARIZATION] Speaker range: {min_speakers}-{max_speakers}")
        print(f"[DIARIZATION] HF_TOKEN provided: {'YES' if self.hf_token else 'NO'}")
        if self.hf_token:
            print(f"[DIARIZATION] Token preview: {self.hf_token[:20]}...")
    
    def load(self):
        """Load the diarization pipeline"""
        if not self.hf_token:
            raise ValueError(
                "HuggingFace token required for pyannote models. "
                "Set HF_TOKEN in .env or pass hf_token parameter"
            )
        
        print(f"[DIARIZATION] Loading {self.model_name}...")
        load_start = time.time()
        
        try:
            # Load pipeline with authentication (use 'token' instead of deprecated 'use_auth_token')
            self.pipeline = Pipeline.from_pretrained(
                self.model_name,
                token=self.hf_token
            )
            
            # Move to GPU if available
            if self.device == "cuda":
                self.pipeline.to(torch.device("cuda"))
            
            load_time = time.time() - load_start
            print(f"[OK] Diarization pipeline loaded in {load_time:.2f}s")
            
        except Exception as e:
            print(f"[ERROR] Failed to load diarization model: {e}")
            print(f"[TIP] Make sure you have accepted the model license at:")
            print(f"      https://huggingface.co/{self.model_name}")
            raise
    
    def diarize(
        self,
        audio_path: str,
        min_duration: float = 1.0,
        collar: float = 0.0,
        use_vad: bool = True
    ) -> List[SpeakerSegment]:
        """
        Perform speaker diarization on audio file
        
        Args:
            audio_path: Path to audio file
            min_duration: Minimum segment duration in seconds (filter short segments)
            collar: Tolerance for segment boundaries in seconds
            use_vad: Use Voice Activity Detection to speed up processing
            
        Returns:
            List of SpeakerSegment objects sorted by start time
        """
        if self.pipeline is None:
            raise RuntimeError("Pipeline not loaded. Call load() first.")
        
        print(f"[DIARIZATION] Processing: {audio_path}")
        diarize_start = time.time()
        
        # Optional: Pre-filter with VAD for faster processing
        if use_vad:
            print(f"[DIARIZATION] Running VAD pre-filtering...")
            try:
                from utils.vad_utils import VADProcessor
                import librosa
                import soundfile as sf
                import os
                
                # Load audio
                audio, sr = librosa.load(audio_path, sr=16000)
                
                # Detect speech segments
                vad = VADProcessor(method="silero", threshold=0.5)
                speech_segments = vad.detect_speech_segments(
                    audio, sr,
                    min_speech_duration=0.3,
                    min_silence_duration=0.2
                )
                
                if speech_segments:
                    # Save filtered audio temporarily
                    filtered_audio = vad.filter_audio_by_speech(audio, sr, padding=0.3)
                    temp_path = audio_path.replace('.wav', '_vad.wav')
                    sf.write(temp_path, filtered_audio, sr)
                    audio_path = temp_path
                    print(f"[DIARIZATION] VAD filtered audio saved to: {temp_path}")
            except Exception as e:
                print(f"[DIARIZATION] VAD pre-filtering failed: {e}")
                print(f"[DIARIZATION] Continuing without VAD...")
        
        try:
            # Run diarization
            diarization = self.pipeline(
                audio_path,
                min_speakers=self.min_speakers,
                max_speakers=self.max_speakers
            )
            
            # Convert to segment list
            segments = []
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                duration = turn.end - turn.start
                
                # Filter short segments
                if duration >= min_duration:
                    segments.append(SpeakerSegment(
                        speaker_id=speaker,
                        start_time=turn.start,
                        end_time=turn.end,
                        duration=duration
                    ))
            
            # Sort by start time
            segments.sort(key=lambda x: x.start_time)
            
            diarize_time = time.time() - diarize_start
            
            # Statistics
            num_speakers = len(set(seg.speaker_id for seg in segments))
            total_speech = sum(seg.duration for seg in segments)
            
            print(f"[OK] Diarization completed in {diarize_time:.2f}s")
            print(f"[INFO] Detected {num_speakers} speakers")
            print(f"[INFO] Total segments: {len(segments)}")
            print(f"[INFO] Total speech time: {total_speech:.2f}s")
            
            # Clean up temp VAD file
            if use_vad and '_vad.wav' in audio_path:
                try:
                    os.remove(audio_path)
                except:
                    pass
            
            return segments
            
        except Exception as e:
            print(f"[ERROR] Diarization failed: {e}")
            raise
    
    def get_speaker_stats(self, segments: List[SpeakerSegment]) -> Dict[str, Dict]:
        """
        Get statistics for each speaker
        
        Args:
            segments: List of SpeakerSegment objects
            
        Returns:
            Dictionary with speaker statistics
        """
        stats = {}
        
        for seg in segments:
            if seg.speaker_id not in stats:
                stats[seg.speaker_id] = {
                    'total_duration': 0.0,
                    'num_segments': 0,
                    'first_speak': seg.start_time,
                    'last_speak': seg.end_time
                }
            
            stats[seg.speaker_id]['total_duration'] += seg.duration
            stats[seg.speaker_id]['num_segments'] += 1
            stats[seg.speaker_id]['last_speak'] = max(
                stats[seg.speaker_id]['last_speak'],
                seg.end_time
            )
        
        return stats
    
    def print_timeline(self, segments: List[SpeakerSegment], max_lines: int = 20):
        """Print a timeline of speaker segments"""
        print("\n" + "=" * 80)
        print("SPEAKER TIMELINE:")
        print("=" * 80)
        
        for i, seg in enumerate(segments[:max_lines]):
            print(f"[{i+1:3d}] {seg.speaker_id}: "
                  f"{seg.start_time:7.2f}s - {seg.end_time:7.2f}s "
                  f"({seg.duration:5.2f}s)")
        
        if len(segments) > max_lines:
            print(f"... and {len(segments) - max_lines} more segments")
        
        print("=" * 80)
    
    def save_segments(self, segments: List[SpeakerSegment], output_path: str):
        """
        Save segments to text file
        
        Format:
        SPEAKER_00 0.00-12.34 (12.34s)
        SPEAKER_01 12.34-25.67 (13.33s)
        ...
        """
        print(f"[SAVE] Saving segments to: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("SPEAKER DIARIZATION SEGMENTS\n")
            f.write("=" * 80 + "\n\n")
            
            for seg in segments:
                f.write(f"{seg.speaker_id}\t{seg.start_time:.2f}-{seg.end_time:.2f}\t"
                       f"({seg.duration:.2f}s)\n")
            
            # Add statistics
            f.write("\n" + "=" * 80 + "\n")
            f.write("SPEAKER STATISTICS:\n")
            f.write("=" * 80 + "\n")
            
            stats = self.get_speaker_stats(segments)
            for speaker_id, data in sorted(stats.items()):
                f.write(f"\n{speaker_id}:\n")
                f.write(f"  Total speaking time: {data['total_duration']:.2f}s\n")
                f.write(f"  Number of turns: {data['num_segments']}\n")
                f.write(f"  Average turn length: {data['total_duration']/data['num_segments']:.2f}s\n")
                f.write(f"  First spoke at: {data['first_speak']:.2f}s\n")
                f.write(f"  Last spoke at: {data['last_speak']:.2f}s\n")
        
        print(f"[OK] Segments saved")


# ============= USAGE EXAMPLE =============
if __name__ == "__main__":
    """
    Example usage of SpeakerDiarizationClient
    """
    import sys
    
    # Check if audio path provided
    if len(sys.argv) < 2:
        print("Usage: python diarization_client.py <audio_path>")
        sys.exit(1)
    
    audio_path = sys.argv[1]
    
    # Initialize and run
    diarizer = SpeakerDiarizationClient(
        min_speakers=2,
        max_speakers=5  # Typical call center: 2-3 speakers
    )
    
    diarizer.load()
    segments = diarizer.diarize(audio_path)
    
    # Print timeline
    diarizer.print_timeline(segments)
    
    # Print statistics
    stats = diarizer.get_speaker_stats(segments)
    print("\n" + "=" * 80)
    print("SPEAKER STATISTICS:")
    print("=" * 80)
    for speaker_id, data in sorted(stats.items()):
        print(f"\n{speaker_id}:")
        print(f"  Speaking time: {data['total_duration']:.2f}s")
        print(f"  Turns: {data['num_segments']}")
        print(f"  Avg turn: {data['total_duration']/data['num_segments']:.2f}s")
    
    # Save to file
    output_path = audio_path.replace('.mp3', '_segments.txt').replace('.wav', '_segments.txt')
    diarizer.save_segments(segments, output_path)
