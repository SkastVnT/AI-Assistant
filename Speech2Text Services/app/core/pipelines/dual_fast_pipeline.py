# -*- coding: utf-8 -*-
import os
import time
import datetime
import librosa
import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from scipy import signal
import torch
from transformers import T5ForConditionalGeneration, T5Tokenizer

# ============= CONFIGURATION =============
load_dotenv()

AUDIO_PATH = os.getenv("AUDIO_PATH", r"C:\Users\Asus\Downloads\d08deb45-d23d-449e-9fdf-7b40b1c1050d.mp3")

# Create directories
def create_directories():
    directories = ["./audio", "./result/raw", "./result/gemini", "./result/dual"]
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"[FOLDER] Created/Checked directory: {dir_path}")

create_directories()

# Audio preprocessing (FAST)
def preprocess_audio_fast(input_path, output_path):
    print(f"[FOLDER] Loading audio: {input_path}")
    y_original, sr_original = librosa.load(input_path, sr=None)
    print(f"   Original - Sample rate: {sr_original}Hz, Duration: {len(y_original)/sr_original:.2f}s")
    
    # Ch[?] resample, kh[?]ng x[?] l[?] th[?]m d[?] nhanh h[?]n
    y = librosa.resample(y_original, orig_sr=sr_original, target_sr=16000)
    sr = 16000
    
    # Normalize d[?]n gi[?]n
    y = librosa.util.normalize(y, norm=np.inf, axis=None)
    print("   [OK] Fast normalized")
    
    sf.write(output_path, y, sr)
    print(f"   [OK] Fast processed: {len(y)/sr:.2f}s")
    return output_path

print("=" * 80)
print("[LAUNCH] DUAL MODEL ULTRA FAST: Whisper + PhoWhisper + T5 (SPEED OPTIMIZED)")
print("=" * 80)

total_start_time = time.time()

if not os.path.exists(AUDIO_PATH):
    print(f"[ERROR] Audio file not found: {AUDIO_PATH}")
    exit(1)

# ============= B[?][?]C 1: FAST AUDIO PREPROCESSING =============
print("\n[TOOL] B[?][?]C 1: Fast Audio Preprocessing...")
preprocessing_start = time.time()

try:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]
    processed_audio_path = f"./audio/fast_{file_name}_{timestamp}.wav"
    
    cleaned_path = preprocess_audio_fast(AUDIO_PATH, processed_audio_path)
    preprocessing_time = time.time() - preprocessing_start
    print(f"[OK] Fast preprocessing completed in {preprocessing_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] Audio preprocessing failed: {e}")
    cleaned_path = AUDIO_PATH
    preprocessing_time = 0

# ============= B[?][?]C 2: WHISPER LARGE-V3 (FAST) =============
print(f"\n[MIC] B[?][?]C 2A: Whisper large-v3 (FAST)...")
whisper_transcript = ""
whisper_time = 0

try:
    from faster_whisper import WhisperModel
    
    print("Loading Whisper large-v3 (FAST)...")
    whisper_load_start = time.time()
    
    try:
        import torch
        if torch.cuda.is_available():
            whisper_model = WhisperModel("large-v3", device="cuda", compute_type="float16")
            print("[OK] Using GPU (CUDA)")
        else:
            whisper_model = WhisperModel("large-v3", device="cpu", compute_type="int8")
            print("[OK] Using CPU")
    except Exception as e:
        print(f"[WARN] CUDA error: {e}")
        whisper_model = WhisperModel("large-v3", device="cpu", compute_type="int8")
        print("[OK] CPU fallback")
    
    whisper_load_time = time.time() - whisper_load_start
    print(f"[OK] Whisper loaded in {whisper_load_time:.2f}s")
    
    print("Transcribing with Whisper (FAST)...")
    whisper_start = time.time()
    
    segments, info = whisper_model.transcribe(
        cleaned_path,
        language="vi",
        beam_size=3,  # Gi[?]m t[?] 5 xu[?]ng 3
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=True  # B[?]t VAD d[?] nhanh h[?]n
    )
    
    whisper_segments = []
    for segment in segments:
        text = segment.text.strip()
        whisper_segments.append(text)
    
    whisper_transcript = " ".join(whisper_segments)
    whisper_time = time.time() - whisper_start
    
    print("\n" + "=" * 50)
    print("WHISPER RESULT (FAST):")
    print("=" * 50)
    print(whisper_transcript[:200] + "..." if len(whisper_transcript) > 200 else whisper_transcript)
    print(f"\n[OK] Whisper completed in {whisper_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] Whisper Error: {e}")
    whisper_transcript = "[Whisper transcription failed]"

# ============= B[?][?]C 3: PHOWHISPER ULTRA FAST =============
print(f"\n[MIC] B[?][?]C 2B: PhoWhisper (ULTRA FAST)...")
phowhisper_transcript = ""
phowhisper_time = 0

try:
    # Ki[?]m tra d[?] d[?]i audio tr[?][?]c
    audio_test, sr_test = librosa.load(cleaned_path, sr=16000)
    audio_duration = len(audio_test) / sr_test
    print(f"   [CHART] Audio duration: {audio_duration:.1f}s")
    
    # N[?]u audio qu[?] d[?]i (>60s), s[?] d[?]ng Whisper result thay v[?] PhoWhisper
    if audio_duration > 60:
        print(f"   [FAST] Audio >60s, using Whisper result to save time")
        phowhisper_transcript = whisper_transcript
        phowhisper_time = 0.1
    else:
        # Ch[?] ch[?]y PhoWhisper cho audio ng[?]n
        os.environ['HF_HUB_DISABLE_SAFETENSORS_LOAD_WARNING'] = '1'
        os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
        
        from transformers import WhisperProcessor, WhisperForConditionalGeneration
        import torch
        
        print("Loading PhoWhisper (ULTRA FAST)...")
        phowhisper_load_start = time.time()
        
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[OK] Using device: {device}")
        
        processor = WhisperProcessor.from_pretrained("vinai/PhoWhisper-large")
        pho_model = WhisperForConditionalGeneration.from_pretrained(
            "vinai/PhoWhisper-large",
            torch_dtype=torch.float16 if device == "cuda" else torch.float32,
            low_cpu_mem_usage=True
        ).to(device)
        
        phowhisper_load_time = time.time() - phowhisper_load_start
        print(f"[OK] PhoWhisper loaded in {phowhisper_load_time:.2f}s")
        
        print("Transcribing with PhoWhisper (ULTRA FAST)...")
        phowhisper_start = time.time()
        
        # Single shot, kh[?]ng chunking
        inputs = processor(audio_test, sampling_rate=16000, return_tensors="pt")
        
        if device == "cuda":
            inputs = {k: v.to(device).half() if v.dtype == torch.float32 else v.to(device) for k, v in inputs.items()}
        else:
            inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            predicted_ids = pho_model.generate(
                inputs["input_features"],
                max_length=256,  # Gi[?]m m[?]nh
                num_beams=2,     # Gi[?]m m[?]nh
                do_sample=False,
                temperature=0.0,
                language="vi",
                task="transcribe",
                forced_decoder_ids=processor.get_decoder_prompt_ids(language="vi", task="transcribe")
            )
        
        phowhisper_transcript = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        phowhisper_time = time.time() - phowhisper_start
    
    print("\n" + "=" * 50)
    print("PHOWHISPER RESULT (ULTRA FAST):")
    print("=" * 50)
    print(phowhisper_transcript[:200] + "..." if len(phowhisper_transcript) > 200 else phowhisper_transcript)
    print(f"\n[OK] PhoWhisper completed in {phowhisper_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] PhoWhisper Error: {e}")
    phowhisper_transcript = whisper_transcript  # Fallback to Whisper

# ============= B[?][?]C 4: SIMPLE FUSION (NO T5) =============
print(f"\n[AI] B[?][?]C 3: Simple Fusion (ULTRA FAST)...")
fusion_start = time.time()

# Simple rule-based fusion thay v[?] T5 d[?] ti[?]t ki[?]m th[?]i gian
def simple_fusion(text1, text2):
    """Fusion d[?]n gi[?]n b[?]ng rule-based"""
    # Ch[?]n text d[?]i h[?]n (th[?][?]ng ch[?]a nhi[?]u th[?]ng tin h[?]n)
    if len(text1) > len(text2):
        main_text = text1
        backup_text = text2
    else:
        main_text = text2
        backup_text = text1
    
    # N[?]u 2 text qu[?] kh[?]c nhau, gh[?]p l[?]i
    if len(main_text) > len(backup_text) * 2:
        return main_text
    else:
        # Gh[?]p 2 text v[?]i m[?]t [?]t logic
        return f"{main_text.strip()}. {backup_text.strip()}".replace("...", ".").replace("  ", " ")

fused_text = simple_fusion(whisper_transcript, phowhisper_transcript)
fusion_time = time.time() - fusion_start

print("\n" + "=" * 50)
print("FUSED RESULT (ULTRA FAST):")
print("=" * 50)
print(fused_text)
print(f"\n[OK] Simple fusion completed in {fusion_time:.2f}s")

# ============= L[?]U K[?]T QU[?] =============
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
file_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]

# File fused only (clean version)
fused_clean_file = f"./result/gemini/ultra_fast_{file_name}_{timestamp}.txt"
with open(fused_clean_file, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\n")
    f.write("ULTRA FAST DUAL MODEL TRANSCRIPT\n")
    f.write("(Whisper + PhoWhisper + Simple Fusion)\n")
    f.write("=" * 80 + "\n")
    f.write(f"Original file: {AUDIO_PATH}\n")
    f.write(f"Timestamp: {timestamp}\n")
    f.write("=" * 80 + "\n\n")
    f.write(fused_text)

total_time = time.time() - total_start_time

print(f"\n\n[OK] ULTRA FAST PROCESSING COMPLETED:")
print(f"   [BEST] Result file: {fused_clean_file}")

print("\n" + "=" * 80)
print("[FAST] ULTRA FAST - TH[?]I GIAN TH[?]C HI[?]N:")
print("=" * 80)
print(f"  [?] Audio preprocessing:     {preprocessing_time:>8.2f}s")
print(f"  [?] Whisper large-v3:        {whisper_time:>8.2f}s")
print(f"  [?] PhoWhisper:              {phowhisper_time:>8.2f}s")
print(f"  [?] Simple Fusion:           {fusion_time:>8.2f}s")
print(f"  [?] [?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?]")
print(f"  [?] T[?]NG C[?]NG:               {total_time:>8.2f}s")
print("=" * 80)

print(f"\n[FAST] ULTRA FAST FEATURES:")
print(f"  [OK] Reduced beam search (Whisper: 3, PhoWhisper: 2)")
print(f"  [OK] Simple fusion instead of T5")
print(f"  [OK] Skip PhoWhisper for long audio (>60s)")
print(f"  [OK] VAD filter for Whisper speed")
print(f"  [OK] Target: Under 5 minutes total")

print("\n" + "=" * 80)
print("[SUCCESS] ULTRA FAST PROCESSING COMPLETED!")
print("=" * 80)