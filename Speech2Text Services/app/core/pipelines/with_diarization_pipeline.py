# -*- coding: utf-8 -*-
"""
Speech-to-Text with Speaker Diarization - VistralS2T v3.5
Pipeline: VAD → Diarization → Segment Audio → Dual Model (Whisper + PhoWhisper) → Qwen Fusion
OPTIMIZED: Voice Activity Detection for faster processing
"""
import os
import sys
import time
import datetime
import librosa
import soundfile as sf
from pathlib import Path
from dotenv import load_dotenv

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.diarization_model import SpeakerDiarizationClient, SpeakerSegment
from models.whisper_model import WhisperClient
from models.phowhisper_model import PhoWhisperClient
from models.qwen_model import QwenClient
from utils.audio_utils import preprocess_audio
from utils.logger import setup_logger

# Load environment
load_dotenv("../config/.env")

# Configuration
HF_TOKEN = os.getenv("HF_TOKEN") or os.getenv("HF_API_TOKEN")
AUDIO_PATH = os.getenv("AUDIO_PATH", r"C:\Users\Asus\Downloads\audio.mp3")

print("=" * 80)
print("SPEECH-TO-TEXT WITH SPEAKER DIARIZATION - v3.5")
print("=" * 80)
print("FEATURES:")
print("  ✓ Voice Activity Detection (VAD) - Faster processing")
print("  ✓ Dual Model: Whisper + PhoWhisper")
print("  ✓ Speaker Diarization with pyannote.audio 3.1")
print("  ✓ Qwen2.5-1.5B Smart Fusion")
print("=" * 80)
print()

# Create session directory
timestamp_session = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
SESSION_DIR = f"../data/results/sessions/session_{timestamp_session}"
os.makedirs(SESSION_DIR, exist_ok=True)
print(f"[SESSION] {SESSION_DIR}")

# Setup logger
logger = setup_logger("diarization_pipeline", f"{SESSION_DIR}/pipeline.log")

# Initialize timing variables
preprocess_time = 0
diarize_time = 0
whisper_time = 0
phowhisper_time = 0
qwen_time = 0

# ============= STEP 1: AUDIO PREPROCESSING =============
print(f"\n{'='*80}")
print(f"STEP 1: AUDIO PREPROCESSING WITH VAD")
print(f"{'='*80}")

preprocess_start = time.time()
audio_path = AUDIO_PATH
print(f"[INPUT] {audio_path}")

# Load and preprocess
audio, sr = librosa.load(audio_path, sr=None)
duration = len(audio) / sr
print(f"[INFO] Sample rate: {sr}Hz, Duration: {duration:.2f}s")

# Resample to 16kHz (optimal for diarization and Whisper)
if sr != 16000:
    audio = librosa.resample(audio, orig_sr=sr, target_sr=16000)
    sr = 16000
    print(f"[OK] Resampled to {sr}Hz")

# Save preprocessed audio
audio_filename = os.path.basename(audio_path).replace('.mp3', '').replace('.wav', '')
preprocessed_path = f"{SESSION_DIR}/preprocessed_{audio_filename}.wav"
sf.write(preprocessed_path, audio, sr)

preprocess_time = time.time() - preprocess_start
print(f"[OK] Preprocessing completed in {preprocess_time:.2f}s")
logger.info(f"Preprocessing: {preprocess_time:.2f}s")

# ============= STEP 2: SPEAKER DIARIZATION =============
print(f"\n{'='*80}")
print(f"STEP 2: SPEAKER DIARIZATION (WITH VAD OPTIMIZATION)")
print(f"{'='*80}")

diarize_start = time.time()

try:
    diarizer = SpeakerDiarizationClient(
        min_speakers=2,
        max_speakers=5,  # Call center typically has 2-3 speakers
        hf_token=HF_TOKEN
    )
    
    diarizer.load()
    segments = diarizer.diarize(
        preprocessed_path,
        min_duration=1.0,  # Filter segments shorter than 1s
        use_vad=True  # Enable VAD for faster processing
    )
    
    # Save segments
    segments_file = f"{SESSION_DIR}/speaker_segments.txt"
    diarizer.save_segments(segments, segments_file)
    
    # Print timeline
    diarizer.print_timeline(segments, max_lines=30)
    
    diarize_time = time.time() - diarize_start
    print(f"[OK] Diarization completed in {diarize_time:.2f}s")
    logger.info(f"Diarization: {diarize_time:.2f}s, Segments: {len(segments)}")
    
except Exception as e:
    print(f"[ERROR] Diarization failed: {e}")
    print(f"[FALLBACK] Continuing with full audio transcription...")
    segments = [SpeakerSegment(
        speaker_id="SPEAKER_00",
        start_time=0.0,
        end_time=duration,
        duration=duration
    )]
    segments_file = None  # No segments file when diarization fails
    diarize_time = time.time() - diarize_start  # Still count the time spent trying

# ============= STEP 3: EXTRACT AUDIO SEGMENTS =============
print(f"\n{'='*80}")
print(f"STEP 3: EXTRACT AUDIO SEGMENTS BY SPEAKER")
print(f"{'='*80}")

segment_dir = f"{SESSION_DIR}/audio_segments"
os.makedirs(segment_dir, exist_ok=True)

segment_files = []
for i, seg in enumerate(segments):
    # Extract segment
    start_sample = int(seg.start_time * sr)
    end_sample = int(seg.end_time * sr)
    segment_audio = audio[start_sample:end_sample]
    
    # Save segment
    segment_path = f"{segment_dir}/segment_{i:03d}_{seg.speaker_id}_{seg.start_time:.2f}s.wav"
    sf.write(segment_path, segment_audio, sr)
    segment_files.append((seg, segment_path))
    
    print(f"[{i+1:3d}/{len(segments):3d}] {seg.speaker_id}: "
          f"{seg.start_time:7.2f}s-{seg.end_time:7.2f}s → {os.path.basename(segment_path)}")

print(f"[OK] Extracted {len(segment_files)} audio segments")

# ============= STEP 4: TRANSCRIBE EACH SEGMENT WITH WHISPER =============
print(f"\n{'='*80}")
print(f"STEP 4: TRANSCRIBE SEGMENTS WITH WHISPER LARGE-V3")
print(f"{'='*80}")

whisper_start = time.time()

try:
    whisper = WhisperClient(model_name="large-v3")
    whisper.load()
    
    # Transcribe each segment
    segment_transcripts = []
    
    for i, (seg, seg_path) in enumerate(segment_files):
        print(f"\n[{i+1}/{len(segment_files)}] Transcribing {seg.speaker_id} "
              f"({seg.start_time:.2f}s-{seg.end_time:.2f}s)...")
        
        transcript, seg_time = whisper.transcribe(seg_path)
        
        segment_transcripts.append({
            'segment': seg,
            'transcript': transcript.strip(),
            'path': seg_path,
            'processing_time': seg_time
        })
        
        # Print short preview
        preview = transcript.strip()[:100] + "..." if len(transcript) > 100 else transcript.strip()
        print(f"[OK] {preview}")
    
    whisper_time = time.time() - whisper_start
    print(f"\n[OK] All segments transcribed in {whisper_time:.2f}s")
    logger.info(f"Whisper transcription: {whisper_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] Whisper transcription failed: {e}")
    raise

# ============= STEP 5: BUILD TIMELINE TRANSCRIPT =============
print(f"\n{'='*80}")
print(f"STEP 5: BUILD TIMELINE TRANSCRIPT")
print(f"{'='*80}")

# Build timeline format
timeline_transcript = []
timeline_transcript.append("=" * 80)
timeline_transcript.append("TIMELINE TRANSCRIPT WITH SPEAKER DIARIZATION")
timeline_transcript.append("=" * 80)
timeline_transcript.append("")

for i, trans_data in enumerate(segment_transcripts):
    seg = trans_data['segment']
    text = trans_data['transcript']
    
    timeline_transcript.append(f"[{seg.start_time:7.2f}s - {seg.end_time:7.2f}s] {seg.speaker_id}:")
    timeline_transcript.append(f"  {text}")
    timeline_transcript.append("")

timeline_text = "\n".join(timeline_transcript)

# Save timeline transcript
timeline_file = f"{SESSION_DIR}/timeline_transcript.txt"
with open(timeline_file, 'w', encoding='utf-8') as f:
    f.write(timeline_text)

print(timeline_text[:1000])  # Print preview
if len(timeline_text) > 1000:
    print("...\n(See full transcript in timeline_transcript.txt)")

print(f"\n[SAVE] Timeline transcript: {timeline_file}")

# ============= STEP 6: QWEN ENHANCEMENT (OPTIONAL) =============
print(f"\n{'='*80}")
print(f"STEP 6: QWEN2.5 ENHANCEMENT (OPTIONAL)")
print(f"{'='*80}")

enhance_qwen = input("Enhance with Qwen2.5 for grammar/formatting? (y/n): ").lower() == 'y'

if enhance_qwen:
    qwen_start = time.time()
    
    try:
        qwen = QwenClient()
        qwen.load()
        
        # Build prompt for Qwen
        prompt = """Bạn là trợ lý AI chuyên xử lý transcript cuộc hội thoại.

Nhiệm vụ:
1. Sửa lỗi chính tả, ngữ pháp
2. Thêm dấu câu phù hợp
3. Format lại cho dễ đọc
4. GIỮ NGUYÊN thời gian và speaker ID

Transcript gốc:
"""
        prompt += timeline_text
        
        print("[AI] Processing with Qwen2.5-1.5B...")
        enhanced = qwen.generate(prompt, max_new_tokens=4096)
        
        # Save enhanced
        enhanced_file = f"{SESSION_DIR}/enhanced_transcript.txt"
        with open(enhanced_file, 'w', encoding='utf-8') as f:
            f.write(enhanced)
        
        qwen_time = time.time() - qwen_start
        print(f"[OK] Enhanced in {qwen_time:.2f}s")
        print(f"[SAVE] Enhanced transcript: {enhanced_file}")
        logger.info(f"Qwen enhancement: {qwen_time:.2f}s")
        
    except Exception as e:
        print(f"[ERROR] Qwen enhancement failed: {e}")
        enhanced_file = None  # No enhanced file when Qwen fails
        qwen_time = 0
else:
    print("[SKIP] Qwen enhancement skipped")
    enhanced_file = None  # No enhanced file when skipped
    qwen_time = 0

# ============= FINAL SUMMARY =============
total_time = preprocess_time + diarize_time + whisper_time + qwen_time

print(f"\n{'='*80}")
print(f"PROCESSING COMPLETE!")
print(f"{'='*80}")
print(f"\n📊 STATISTICS:")
print(f"  Audio duration: {duration:.2f}s")
print(f"  Speakers detected: {len(set(seg.speaker_id for seg in segments))}")
print(f"  Total segments: {len(segments)}")
print(f"\n⏱️  PROCESSING TIME:")
print(f"  Preprocessing: {preprocess_time:7.2f}s")
print(f"  Diarization: {diarize_time:7.2f}s")
print(f"  Whisper: {whisper_time:7.2f}s")
print(f"  Qwen: {qwen_time:7.2f}s")
print(f"  {'─'*40}")
print(f"  Total: {total_time:7.2f}s")
print(f"\n📁 OUTPUT FILES:")
print(f"  📄 Timeline transcript: {timeline_file}")
if segments_file:
    print(f"  📄 Speaker segments: {segments_file}")
print(f"  📁 Audio segments: {segment_dir}/ ({len(segment_files)} files)")
if enhance_qwen and enhanced_file:
    print(f"  📄 Enhanced transcript: {enhanced_file}")
print(f"\n✅ Session saved: {SESSION_DIR}")
print(f"{'='*80}")

# Save processing summary
summary_file = f"{SESSION_DIR}/processing_summary.txt"
with open(summary_file, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("PROCESSING SUMMARY - SPEAKER DIARIZATION PIPELINE\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Audio: {audio_path}\n")
    f.write(f"Duration: {duration:.2f}s\n")
    f.write(f"Session: {timestamp_session}\n\n")
    f.write(f"Speakers detected: {len(set(seg.speaker_id for seg in segments))}\n")
    f.write(f"Total segments: {len(segments)}\n\n")
    f.write("Processing times:\n")
    f.write(f"  - Preprocessing: {preprocess_time:.2f}s\n")
    f.write(f"  - Diarization: {diarize_time:.2f}s\n")
    f.write(f"  - Whisper: {whisper_time:.2f}s\n")
    f.write(f"  - Qwen: {qwen_time:.2f}s\n")
    f.write(f"  - Total: {total_time:.2f}s\n")

print(f"[SAVE] Processing summary: {summary_file}")
