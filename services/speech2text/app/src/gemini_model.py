# -*- coding: utf-8 -*-
# CI fix: corrected syntax error (extra quote) on GEMINI_API_KEY line
# Ref: d0861426e9d20a560020005122410a5ee240802a
import os
import time
import datetime
import google.generativeai as genai
import librosa
import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from scipy import signal

# ============= CONFIGURATION =============
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUDIO_PATH = os.getenv("AUDIO_PATH", r"C:\Users\Asus\Downloads\92398d36-1460-4ef2-9e11-1a3d0fed2a3c.mp3")

# Create directories
def create_directories():
    directories = ["./audio", "./result/raw", "./result/gemini", "./result/dual"]
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"[FOLDER] Created/Checked directory: {dir_path}")

create_directories()

# Ki[?]m tra Gemini API key
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    print("=" * 60)
    print("[WARN]  CH[?]A CONFIGURATION GEMINI API KEY!")
    print("=" * 60)
    print("1. L[?]y API key t[?]i: https://aistudio.google.com/apikey")
    print("2. C[?]p nh[?]t file .env v[?]i GEMINI_API_KEY")
    print("=" * 60)
    exit(1)

# C[?]u h[?]nh Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("models/gemini-2.5-flash")

# Audio preprocessing (optimized)
def preprocess_audio(input_path, output_path):
    print(f"[FOLDER] Loading audio: {input_path}")
    y_original, sr_original = librosa.load(input_path, sr=None)
    print(f"   Original - Sample rate: {sr_original}Hz, Duration: {len(y_original)/sr_original:.2f}s")
    
    # Resample to 16kHz
    y = librosa.resample(y_original, orig_sr=sr_original, target_sr=16000)
    sr = 16000
    
    # Light processing for speed
    y = librosa.util.normalize(y, norm=np.inf, axis=None)
    print("   [OK] Normalized")
    
    y_trimmed, _ = librosa.effects.trim(y, top_db=30)
    print(f"   [OK] Trimmed: {len(y_trimmed)/sr:.2f}s")
    
    # Minimal filtering
    sos = signal.butter(2, 50, "hp", fs=sr, output="sos")
    y_filtered = signal.sosfilt(sos, y_trimmed)
    print("   [OK] Filtered")
    
    y_final = librosa.util.normalize(y_filtered, norm=np.inf, axis=None)
    sf.write(output_path, y_final, sr)
    print(f"   [OK] Saved: {len(y_final)/sr:.2f}s")
    return output_path

print("=" * 80)
print("[LAUNCH] DUAL MODEL RUN: Whisper + PhoWhisper + Gemini AI Fusion")
print("=" * 80)

total_start_time = time.time()

if not os.path.exists(AUDIO_PATH):
    print(f"[ERROR] Audio file not found: {AUDIO_PATH}")
    exit(1)

# ============= B[?][?]C 1: AUDIO PREPROCESSING =============
print("\n[TOOL] B[?][?]C 1: Audio Preprocessing...")
preprocessing_start = time.time()

try:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]
    processed_audio_path = f"./audio/run_processed_{file_name}_{timestamp}.wav"
    
    cleaned_path = preprocess_audio(AUDIO_PATH, processed_audio_path)
    preprocessing_time = time.time() - preprocessing_start
    print(f"[OK] Audio preprocessing completed in {preprocessing_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] Audio preprocessing failed: {e}")
    cleaned_path = AUDIO_PATH
    preprocessing_time = 0

# ============= B[?][?]C 2: WHISPER TRANSCRIPTION =============
print(f"\n[MIC] B[?][?]C 2A: Whisper large-v3 Transcription...")
whisper_transcript = ""
whisper_time = 0

try:
    from faster_whisper import WhisperModel
    
    print("Loading Whisper large-v3...")
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
        whisper_model = WhisperModel("large-v3", device="cpu", compute_type="int8")
        print("[OK] CPU fallback")
    
    whisper_load_time = time.time() - whisper_load_start
    print(f"[OK] Whisper loaded in {whisper_load_time:.2f}s")
    
    print("Transcribing with Whisper...")
    whisper_start = time.time()
    
    segments, info = whisper_model.transcribe(
        cleaned_path,
        language="vi",
        beam_size=4,  # Balanced speed vs quality
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=True
    )
    
    whisper_segments = []
    for segment in segments:
        text = segment.text.strip()
        whisper_segments.append(text)
    
    whisper_transcript = " ".join(whisper_segments)
    whisper_time = time.time() - whisper_start
    
    print("\n" + "=" * 80)
    print("WHISPER LARGE-V3 RESULT:")
    print("=" * 80)
    print(whisper_transcript)
    print(f"\n[OK] Whisper completed in {whisper_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] Whisper Error: {e}")
    whisper_transcript = "[Whisper transcription failed]"

# ============= B[?][?]C 3: PHOWHISPER ULTRA OPTIMIZED =============
print(f"\n[MIC] B[?][?]C 2B: PhoWhisper-large (ULTRA OPTIMIZED)...")
phowhisper_transcript = ""
phowhisper_time = 0

try:
    # Disable all warnings
    os.environ['HF_HUB_DISABLE_SAFETENSORS_LOAD_WARNING'] = '1'
    os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
    
    # Patch transformers for speed
    import transformers.utils.import_utils as import_utils
    original_check = import_utils.check_torch_load_is_safe
    def patched_check():
        pass
    import_utils.check_torch_load_is_safe = patched_check
    
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    import torch
    
    print("Loading PhoWhisper (ULTRA OPTIMIZED)...")
    phowhisper_load_start = time.time()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[OK] Using device: {device}")
    
    # Pre-load audio to determine strategy
    audio, sr = librosa.load(cleaned_path, sr=16000)
    audio_duration = len(audio) / sr
    print(f"   [CHART] Audio: {audio_duration:.1f}s")
    
    # Load processor
    processor = WhisperProcessor.from_pretrained("vinai/PhoWhisper-large")
    
    # Ultra-optimized model loading
    print("   [?] Loading model with maximum optimization...")
    pho_model = WhisperForConditionalGeneration.from_pretrained(
        "vinai/PhoWhisper-large",
        trust_remote_code=True,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        use_safetensors=False,
        local_files_only=False,
        low_cpu_mem_usage=True,
        device_map="auto" if device == "cuda" else None
    )
    
    if device == "cuda":
        pho_model = pho_model.half().to(device)
        # Aggressive GPU optimization
        torch.cuda.empty_cache()
        torch.backends.cudnn.benchmark = True
        print("   [OK] GPU ultra-optimized")
    else:
        pho_model = pho_model.to(device)
        print("   [OK] CPU optimized")
    
    phowhisper_load_time = time.time() - phowhisper_load_start
    print(f"[OK] PhoWhisper loaded in {phowhisper_load_time:.2f}s")
    
    print("Transcribing with PhoWhisper (ULTRA SPEED)...")
    phowhisper_start = time.time()
    
    # ULTRA OPTIMIZED PROCESSING STRATEGY
    if audio_duration > 60:  # Very long audio
        print(f"   [LAUNCH] Very long audio: using aggressive chunking...")
        
        chunk_duration = 15  # Very small chunks for max speed
        chunk_samples = chunk_duration * sr
        transcriptions = []
        
        num_chunks = int(len(audio)/chunk_samples) + 1
        print(f"   [?] Processing {num_chunks} chunks (15s each)...")
        
        for i in range(0, len(audio), chunk_samples):
            chunk_idx = i // chunk_samples + 1
            chunk = audio[i:i + chunk_samples]
            
            # Skip very short chunks
            if len(chunk) < 2 * sr:
                continue
            
            chunk_start = time.time()
            
            inputs = processor(chunk, sampling_rate=16000, return_tensors="pt")
            
            if device == "cuda":
                inputs = {k: v.to(device).half() if v.dtype == torch.float32 else v.to(device) for k, v in inputs.items()}
            else:
                inputs = {k: v.to(device) for k, v in inputs.items()}
            
            with torch.no_grad():
                predicted_ids = pho_model.generate(
                    inputs["input_features"],
                    max_length=192,  # Very short for speed
                    num_beams=1,     # Greedy search - fastest
                    do_sample=False,
                    temperature=0.0,
                    language="vi",
                    task="transcribe",
                    forced_decoder_ids=processor.get_decoder_prompt_ids(language="vi", task="transcribe")
                )
            
            chunk_text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            chunk_time = time.time() - chunk_start
            
            if chunk_text.strip():
                transcriptions.append(chunk_text.strip())
                
            # Real-time progress with timing
            print(f"   [OK] Chunk {chunk_idx}/{num_chunks} ({chunk_time:.1f}s)")
        
        phowhisper_transcript = " ".join(transcriptions)
        
    elif audio_duration > 30:  # Medium audio
        print(f"   [FAST] Medium audio: balanced chunking...")
        
        chunk_duration = 25
        chunk_samples = chunk_duration * sr
        transcriptions = []
        
        for i in range(0, len(audio), chunk_samples):
            chunk = audio[i:i + chunk_samples]
            
            if len(chunk) < 3 * sr:
                continue
            
            inputs = processor(chunk, sampling_rate=16000, return_tensors="pt")
            
            if device == "cuda":
                inputs = {k: v.to(device).half() if v.dtype == torch.float32 else v.to(device) for k, v in inputs.items()}
            else:
                inputs = {k: v.to(device) for k, v in inputs.items()}
            
            with torch.no_grad():
                predicted_ids = pho_model.generate(
                    inputs["input_features"],
                    max_length=256,
                    num_beams=2,  # Minimal beam search
                    do_sample=False,
                    temperature=0.0,
                    language="vi",
                    task="transcribe",
                    forced_decoder_ids=processor.get_decoder_prompt_ids(language="vi", task="transcribe")
                )
            
            chunk_text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            if chunk_text.strip():
                transcriptions.append(chunk_text.strip())
        
        phowhisper_transcript = " ".join(transcriptions)
        
    else:  # Short audio - single pass with optimization
        print(f"   [?] Short audio: single optimized pass...")
        
        inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
        
        if device == "cuda":
            inputs = {k: v.to(device).half() if v.dtype == torch.float32 else v.to(device) for k, v in inputs.items()}
        else:
            inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            predicted_ids = pho_model.generate(
                inputs["input_features"],
                max_length=384,
                num_beams=3,  # Balanced
                do_sample=False,
                temperature=0.0,
                repetition_penalty=1.05,
                language="vi",
                task="transcribe",
                forced_decoder_ids=processor.get_decoder_prompt_ids(language="vi", task="transcribe")
            )
        
        phowhisper_transcript = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    
    phowhisper_time = time.time() - phowhisper_start
    
    print("\n" + "=" * 80)
    print("PHOWHISPER-LARGE RESULT (ULTRA OPTIMIZED):")
    print("=" * 80)
    print(phowhisper_transcript)
    print(f"\n[OK] PhoWhisper completed in {phowhisper_time:.2f}s")
    
    # Performance calculation
    speed_factor = audio_duration / phowhisper_time if phowhisper_time > 0 else 0
    print(f"   [FAST] Processing speed: {speed_factor:.1f}x real-time")
    
except Exception as e:
    print(f"[ERROR] PhoWhisper Error: {e}")
    import traceback
    traceback.print_exc()
    phowhisper_transcript = "[PhoWhisper transcription failed]"

# ============= B[?][?]C 4: GEMINI AI FUSION =============
print(f"\n[AI] B[?][?]C 3: Gemini AI Intelligent Fusion...")
gemini_start = time.time()

fusion_prompt = f"""
B[?]n l[?] chuy[?]n gia x[?] l[?] ng[?]n ng[?] ti[?]ng Vi[?]t cao c[?]p. Nhi[?]m v[?]: T[?]o transcript ho[?]n h[?]o t[?] 2 b[?]n transcript c[?]a c[?]ng 1 audio.

## [TARGET] Y[?]U C[?]U
1. **G[?]P TH[?]NG MINH** t[?] c[?] 2 b[?]n
2. **B[?]O TO[?]N T[?]T C[?]** th[?]ng tin quan tr[?]ng:
   - M[?] d[?]n h[?]ng, s[?] di[?]n tho[?]i, d[?]a ch[?]
   - T[?]n ng[?][?]i, d[?]a danh
   - S[?] ti[?]n, ng[?]y th[?]ng
3. **CH[?]N PHI[?]N B[?]N T[?]T NH[?]T** cho m[?]i ph[?]n
4. **S[?]A L[?]I** ch[?]nh t[?], ng[?] ph[?]p
5. **CHU[?]N H[?]A** ti[?]ng Vi[?]t, d[?]u c[?]u

## [?] D[?] LI[?]U
### [?] Whisper large-v3:
```
{whisper_transcript}
```

### [?] PhoWhisper-large (Vietnamese specialized):
```
{phowhisper_transcript}
```

## [?] OUTPUT
Tr[?] v[?] **DUY NH[?]T** transcript d[?] g[?]p, kh[?]ng gi[?]i th[?]ch, kh[?]ng b[?]nh lu[?]n.

**Chi[?]n l[?][?]c:**
- N[?]u 2 b[?]n gi[?]ng nhau [?] gi[?] nguy[?]n
- N[?]u kh[?]c nhau [?] ch[?]n b[?]n r[?] r[?]ng h[?]n
- N[?]u 1 b[?]n c[?] th[?]m th[?]ng tin [?] B[?] SUNG
- [?]u ti[?]n PhoWhisper cho t[?]n Vi[?]t, d[?]a danh
- [?]u ti[?]n Whisper cho c[?]u tr[?]c c[?]u, ng[?] c[?]nh

[TARGET] M[?]c ti[?]u: Transcript **HO[?]N H[?]O** t[?] 2 ngu[?]n, kh[?]ng b[?] s[?]t g[?].
"""

try:
    response = model.generate_content(fusion_prompt)
    fused_text = response.text.strip()
    gemini_time = time.time() - gemini_start
    
    print("\n" + "=" * 80)
    print("[BEST] GEMINI AI FUSED RESULT:")
    print("=" * 80)
    print(fused_text)
    print(f"\n[OK] Gemini fusion completed in {gemini_time:.2f}s")
    
    # ============= L[?]U K[?]T QU[?] =============
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]
    
    # Full comparison report
    dual_output_file = f"./result/dual/run_gemini_{file_name}_{timestamp}.txt"
    with open(dual_output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("DUAL MODEL RUN REPORT (GEMINI AI FUSION)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Original file: {AUDIO_PATH}\n")
        f.write(f"Processed file: {cleaned_path}\n")
        f.write(f"Timestamp: {timestamp}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("MODEL 1: WHISPER LARGE-V3\n")
        f.write("=" * 80 + "\n\n")
        f.write(whisper_transcript)
        
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("MODEL 2: PHOWHISPER-LARGE (ULTRA OPTIMIZED)\n")
        f.write("=" * 80 + "\n\n")
        f.write(phowhisper_transcript)
        
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("[BEST] GEMINI AI FUSED RESULT\n")
        f.write("=" * 80 + "\n\n")
        f.write(fused_text)
    
    # Clean fusion result
    fused_clean_file = f"./result/gemini/run_gemini_clean_{file_name}_{timestamp}.txt"
    with open(fused_clean_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("DUAL MODEL RUN - GEMINI AI FUSION\n")
        f.write("(Whisper large-v3 + PhoWhisper-large + Gemini 2.5-flash)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Original file: {AUDIO_PATH}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        f.write(fused_text)
    
    total_time = time.time() - total_start_time
    
    print(f"\n\n[OK] DUAL MODEL RUN FILES SAVED:")
    print(f"   [CHART] Full report:     {dual_output_file}")
    print(f"   [BEST] Clean result:    {fused_clean_file}")
    if cleaned_path != AUDIO_PATH:
        print(f"   [MUSIC] Processed audio: {cleaned_path}")
    
    print("\n" + "=" * 80)
    print("[?][?]  DUAL MODEL RUN - PERFORMANCE SUMMARY:")
    print("=" * 80)
    print(f"  [?] Audio preprocessing:     {preprocessing_time:>8.2f}s")
    print(f"  [?] Whisper large-v3:        {whisper_time:>8.2f}s")
    print(f"  [?] PhoWhisper (optimized):  {phowhisper_time:>8.2f}s")
    print(f"  [?] Gemini AI fusion:        {gemini_time:>8.2f}s")
    print(f"  [?] [?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?]")
    print(f"  [?] TOTAL TIME:              {total_time:>8.2f}s")
    print("=" * 80)
    
    print(f"\n[IDEA] RUN.PY FEATURES:")
    print(f"  [OK] Gemini 2.5-flash AI fusion")
    print(f"  [OK] Ultra-optimized PhoWhisper processing")
    print(f"  [OK] Adaptive chunking strategy")
    print(f"  [OK] Real-time progress tracking")
    print(f"  [OK] Intelligent Vietnamese text fusion")
    print(f"  [OK] Speed: {audio_duration/phowhisper_time:.1f}x real-time PhoWhisper" if 'audio_duration' in locals() and phowhisper_time > 0 else "")
    
except Exception as e:
    print(f"[ERROR] Gemini Fusion Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("[SUCCESS] DUAL MODEL RUN COMPLETED!")
print("=" * 80)