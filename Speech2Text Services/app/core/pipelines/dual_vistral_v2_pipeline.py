"""
VistralS2T - Dual Model Fusion Pipeline (Refactored Version)
Uses modular clients for Whisper, PhoWhisper, and Qwen

Version: 3.0.0
Architecture: Whisper large-v3 + PhoWhisper-large → Qwen2.5-1.5B Fusion
"""

import os
import time
import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv("app/config/.env")

# Import clients
from app.core.models import WhisperClient, PhoWhisperClient, QwenClient
from app.core.utils import preprocess_audio, setup_logger, log_transcription, log_fusion
from app.core.handlers import handle_error, validate_audio_path, AudioError

# Setup logging
logger = setup_logger()


def main():
    """Main pipeline execution"""
    start_time = time.time()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    
    print("\n" + "=" * 80)
    print("VistralS2T - Vietnamese Speech-to-Text System v3.0.0")
    print("Dual Model Fusion: Whisper + PhoWhisper → Qwen2.5-1.5B")
    print("=" * 80)
    
    # ============= STEP 1: LOAD AUDIO & PREPROCESS =============
    print("\n[AUDIO] STEP 1: Load and Preprocess Audio")
    
    audio_path = os.getenv("AUDIO_PATH", "")
    if not audio_path:
        raise AudioError("AUDIO_PATH not set in .env file")
    
    try:
        # Validate audio path
        audio_path = validate_audio_path(audio_path)
        audio_filename = audio_path.stem
        
        # Preprocess audio
        audio_data, sample_rate, cleaned_path = preprocess_audio(
            str(audio_path),
            target_sr=32000,
            normalize=True,
            trim_silence=True,
            high_pass_freq=100,
        )
        
        print(f"[OK] Audio ready: {cleaned_path}")
        
    except Exception as e:
        return handle_error(e, context="Audio preprocessing", raise_error=True)
    
    # ============= STEP 2A: WHISPER TRANSCRIPTION =============
    print("\n[MIC] STEP 2A: Whisper large-v3 Transcription")
    
    try:
        whisper = WhisperClient(model_name="large-v3")
        whisper.load()
        
        whisper_transcript, whisper_time = whisper.transcribe(
            cleaned_path,
            language="vi",
            beam_size=5,
            vad_filter=False,
        )
        
        print("\n" + "=" * 80)
        print("WHISPER LARGE-V3 RESULT:")
        print("=" * 80)
        print(whisper_transcript)
        
        # Save result
        whisper_output = f"app/output/raw/whisper_{audio_filename}_{timestamp}.txt"
        whisper.save_result(whisper_transcript, whisper_output)
        
        log_transcription("Whisper", str(audio_path), whisper_time, len(whisper_transcript))
        
    except Exception as e:
        whisper_transcript = handle_error(
            e,
            context="Whisper transcription",
            fallback_value="[Whisper transcription failed]"
        )
        whisper_time = 0
    
    # ============= STEP 2B: PHOWHISPER TRANSCRIPTION =============
    print("\n[MIC] STEP 2B: PhoWhisper-large Transcription")
    
    try:
        phowhisper = PhoWhisperClient(chunk_duration=30)
        phowhisper.load()
        
        phowhisper_transcript, phowhisper_time = phowhisper.transcribe(
            cleaned_path,
            language="vietnamese",
        )
        
        print("\n" + "=" * 80)
        print("PHOWHISPER-LARGE RESULT:")
        print("=" * 80)
        print(phowhisper_transcript)
        
        # Save result
        phowhisper_output = f"app/output/raw/phowhisper_{audio_filename}_{timestamp}.txt"
        phowhisper.save_result(phowhisper_transcript, phowhisper_output)
        
        log_transcription("PhoWhisper", str(audio_path), phowhisper_time, len(phowhisper_transcript))
        
    except Exception as e:
        phowhisper_transcript = handle_error(
            e,
            context="PhoWhisper transcription",
            fallback_value=whisper_transcript  # Fallback to Whisper
        )
        phowhisper_time = 0
    
    # ============= STEP 3: QWEN FUSION =============
    print("\n[AI] STEP 3: Qwen2.5-1.5B-Instruct Smart Fusion")
    
    try:
        qwen = QwenClient(model_name="Qwen/Qwen2.5-1.5B-Instruct")
        qwen.load()
        
        fused_text, fusion_time = qwen.fuse_transcripts(
            whisper_transcript,
            phowhisper_transcript,
            max_new_tokens=3072,
            min_new_tokens=500,
            temperature=0.3,
            top_p=0.9,
            repetition_penalty=1.1,
        )
        
        print("\n" + "=" * 80)
        print("[FINAL] QWEN2.5-1.5B ENHANCED RESULT:")
        print("=" * 80)
        print(fused_text)
        
        log_fusion("Qwen2.5-1.5B", fusion_time, len(fused_text))
        
    except Exception as e:
        fused_text = handle_error(
            e,
            context="Qwen fusion",
            fallback_value=phowhisper_transcript  # Fallback to PhoWhisper
        )
        fusion_time = 0
    
    # ============= STEP 4: SAVE RESULTS =============
    print("\n[SAVE] STEP 4: Save Final Results")
    
    try:
        # Create output directories
        Path("app/output/vistral").mkdir(parents=True, exist_ok=True)
        Path("app/output/dual").mkdir(parents=True, exist_ok=True)
        
        # Save final fused transcript
        final_output = f"app/output/vistral/fused_{audio_filename}_{timestamp}.txt"
        with open(final_output, "w", encoding="utf-8") as f:
            f.write(fused_text)
        print(f"[OK] Final transcript: {final_output}")
        
        # Save processing log
        log_output = f"app/output/dual/log_{audio_filename}_{timestamp}.txt"
        with open(log_output, "w", encoding="utf-8") as f:
            f.write(f"VistralS2T Processing Log\n")
            f.write(f"=" * 80 + "\n\n")
            f.write(f"Audio File: {audio_path}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write(f"Sample Rate: {sample_rate} Hz\n\n")
            f.write(f"Processing Times:\n")
            f.write(f"- Whisper: {whisper_time:.2f}s\n")
            f.write(f"- PhoWhisper: {phowhisper_time:.2f}s\n")
            f.write(f"- Qwen Fusion: {fusion_time:.2f}s\n")
            f.write(f"- Total: {time.time() - start_time:.2f}s\n\n")
            f.write(f"Output Lengths:\n")
            f.write(f"- Whisper: {len(whisper_transcript)} chars\n")
            f.write(f"- PhoWhisper: {len(phowhisper_transcript)} chars\n")
            f.write(f"- Final: {len(fused_text)} chars\n")
        print(f"[OK] Processing log: {log_output}")
        
    except Exception as e:
        handle_error(e, context="Saving results")
    
    # ============= SUMMARY =============
    total_time = time.time() - start_time
    
    print("\n" + "=" * 80)
    print("PROCESSING COMPLETE!")
    print("=" * 80)
    print(f"Total Time: {total_time:.2f}s")
    print(f"Whisper: {whisper_time:.2f}s ({len(whisper_transcript)} chars)")
    print(f"PhoWhisper: {phowhisper_time:.2f}s ({len(phowhisper_transcript)} chars)")
    print(f"Qwen Fusion: {fusion_time:.2f}s ({len(fused_text)} chars)")
    print("\n" + "=" * 80)
    print(f"✅ Final output: {final_output}")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[STOP] Process interrupted by user")
    except Exception as e:
        handle_error(e, context="Main pipeline", raise_error=False)
        print("\n[ERROR] Pipeline failed. Check logs for details.")
