# -*- coding: utf-8 -*-
"""
DUAL MODEL WITH QWEN2.5-1.5B-INSTRUCT FUSION
Whisper large-v3 + PhoWhisper-large + Qwen2.5-1.5B Smart Fusion
Optimized for Vietnamese with 3-role speaker separation (Lightweight & Fast)
"""
import os
import time
import datetime
import librosa
import numpy as np
import soundfile as sf
try:
    from services.shared_env import load_shared_env
except ModuleNotFoundError:
    import sys
    from pathlib import Path

    for _parent in Path(__file__).resolve().parents:
        if (_parent / "services" / "shared_env.py").exists():
            if str(_parent) not in sys.path:
                sys.path.insert(0, str(_parent))
            break
    from services.shared_env import load_shared_env
from scipy import signal
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

# ============= CONFIGURATION =============
# Load .env from config folder
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
load_shared_env(__file__)
AUDIO_PATH = os.getenv("AUDIO_PATH", "./audio/sample.mp3")
HF_TOKEN = os.getenv("HF_API_TOKEN", "")

# Login to Hugging Face if token available
if HF_TOKEN:
    from huggingface_hub import login
    login(token=HF_TOKEN)
    print(f"[HF] Logged in with token: {HF_TOKEN[:10]}...{HF_TOKEN[-4:]}")

print(f"[AI] Using Qwen2.5-1.5B-Instruct for enhancement (Lightweight & Fast)")

# Create directories
def create_directories():
    directories = [
        "./app/data/audio/processed",
        "./app/data/results/sessions",
        "./app/logs"
    ]
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"[FOLDER] Created/Checked directory: {dir_path}")

create_directories()

# Create session folder
timestamp_session = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
SESSION_DIR = f"./app/data/results/sessions/session_{timestamp_session}"
os.makedirs(SESSION_DIR, exist_ok=True)
print(f"[FOLDER] Session folder: {SESSION_DIR}")

print("=" * 80)
print("[LAUNCH] DUAL MODEL: Whisper + PhoWhisper + Vistral-7B Fusion")
print("=" * 80)

# ============= STEP 1: AUDIO PREPROCESSING =============
print(f"\n[TOOL] STEP 1: Audio Preprocessing...")
preprocess_start = time.time()

audio_path = AUDIO_PATH
print(f"[FOLDER] Loading audio: {audio_path}")

# Load and preprocess audio
audio, sr = librosa.load(audio_path, sr=None)
duration = len(audio) / sr
print(f"   Original - Sample rate: {sr}Hz, Duration: {duration:.2f}s")

# Resample to 32kHz (higher quality for Vietnamese speech recognition)
if sr != 32000:
    audio = librosa.resample(audio, orig_sr=sr, target_sr=32000)
    sr = 32000

# Normalize volume
audio = librosa.util.normalize(audio)
print(f"   [OK] Normalized volume")

# Trim silence
audio, _ = librosa.effects.trim(audio, top_db=20)
duration_trimmed = len(audio) / sr
print(f"   [OK] Trimmed silence: {duration_trimmed:.2f}s")

# Apply high-pass filter to remove low-frequency noise
sos = signal.butter(10, 100, 'hp', fs=sr, output='sos')
audio = signal.sosfilt(sos, audio)
print(f"   [OK] Applied high-pass filter")

# Save processed audio
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
audio_filename = os.path.basename(audio_path).replace('.mp3', '').replace('.wav', '')
cleaned_path = f"./app/data/audio/processed/processed_{audio_filename}_{timestamp}.wav"
sf.write(cleaned_path, audio, sr)
print(f"   [OK] Saved processed audio: {duration_trimmed:.2f}s")

preprocess_time = time.time() - preprocess_start
print(f"[OK] Audio preprocessing completed in {preprocess_time:.2f}s")

# ============= STEP 2A: WHISPER LARGE-V3 TRANSCRIPTION =============
print(f"\n[MIC] STEP 2A: Whisper large-v3 Transcription...")
whisper_transcript = ""
whisper_time = 0

try:
    from faster_whisper import WhisperModel
    
    print("Loading Whisper large-v3...")
    whisper_load_start = time.time()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[OK] Using device: {device}")
    
    if device == "cuda":
        compute_type = "float16"
    else:
        compute_type = "int8"
    
    model = WhisperModel("large-v3", device=device, compute_type=compute_type)
    print(f"[OK] Whisper loaded in {time.time() - whisper_load_start:.2f}s")
    
    print("Transcribing with Whisper...")
    whisper_start = time.time()
    segments, info = model.transcribe(
        cleaned_path,
        language="vi",
        beam_size=5,
        vad_filter=False,  # Disabled to capture full audio without cutting
        word_timestamps=False,
        condition_on_previous_text=False,  # Prevent repetition from hold music
        no_speech_threshold=0.1,  # Lower threshold to catch quiet speech
        compression_ratio_threshold=2.4,  # Allow longer segments
        temperature=0.0,  # Deterministic output
    )
    
    whisper_transcript = " ".join([segment.text for segment in segments])
    whisper_time = time.time() - whisper_start
    
    print("\n" + "=" * 80)
    print("WHISPER LARGE-V3 RESULT:")
    print("=" * 80)
    print(whisper_transcript)
    print(f"[OK] Whisper completed in {whisper_time:.2f}s")
    
    # Save Whisper result to session folder
    whisper_file = f"{SESSION_DIR}/whisper_{audio_filename}_{timestamp}.txt"
    with open(whisper_file, "w", encoding="utf-8") as f:
        f.write(whisper_transcript)
    print(f"[SAVE] Whisper saved: {whisper_file}")
    
except Exception as e:
    print(f"[ERROR] Whisper Error: {e}")
    import traceback
    traceback.print_exc()
    whisper_transcript = "[Whisper transcription failed]"
    whisper_time = 0

# ============= STEP 2B: PHOWHISPER-LARGE TRANSCRIPTION =============
print(f"\n[MIC] STEP 2B: PhoWhisper-large Transcription...")
phowhisper_transcript = ""
phowhisper_time = 0

try:
    from transformers import pipeline
    
    print("Loading PhoWhisper-large...")
    pho_load_start = time.time()
    
    device = "cuda:0" if torch.cuda.is_available() else "cpu"
    print(f"[OK] Using device: {device}")
    
    print("[AI] Loading PhoWhisper model (OPTIMIZED)...")
    try:
        pipe = pipeline(
            "automatic-speech-recognition",
            model="vinai/PhoWhisper-large",
            device=device,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        )
        print("[OK] GPU acceleration enabled")
    except Exception as e:
        print(f"[WARN] Model loading error: {e}")
        print("[AI] Trying FAST CPU fallback...")
        pipe = pipeline(
            "automatic-speech-recognition",
            model="vinai/PhoWhisper-large",
            device=-1,
        )
        print("[OK] Fast CPU fallback")
    
    print(f"[OK] PhoWhisper loaded in {time.time() - pho_load_start:.2f}s")
    
    print("Transcribing with PhoWhisper (OPTIMIZED - Full Audio)...")
    pho_start = time.time()
    
    # Load full audio
    audio_data, sr = librosa.load(cleaned_path, sr=16000)
    
    duration = len(audio_data) / sr
    print(f"   [CHART] Audio duration: {duration:.1f}s")
    
    # Process in chunks for better accuracy
    chunk_duration = 30  # Increased to 30s for better context
    chunk_size = chunk_duration * sr
    num_chunks = int(np.ceil(duration / chunk_duration))
    
    print(f"   [AI] Processing {num_chunks} chunks ({chunk_duration}s each)...")
    
    transcripts = []
    for i in range(num_chunks):
        chunk_start_time = time.time()
        start_sample = i * chunk_size
        end_sample = min((i + 1) * chunk_size, len(audio_data))
        chunk = audio_data[start_sample:end_sample]
        
        # Transcribe with language specified
        result = pipe(chunk, generate_kwargs={"language": "vietnamese", "task": "transcribe"})
        chunk_text = result["text"].strip()
        
        if chunk_text:  # Only add non-empty chunks
            transcripts.append(chunk_text)
        
        chunk_time = time.time() - chunk_start_time
        print(f"   [AI] Chunk {i+1}/{num_chunks}... [OK] {chunk_time:.1f}s - {len(chunk_text)} chars")
    
    phowhisper_transcript = " ".join(transcripts)
    phowhisper_time = time.time() - pho_start
    
    print("\n" + "=" * 80)
    print("PHOWHISPER-LARGE RESULT:")
    print("=" * 80)
    print(phowhisper_transcript)
    print(f"[OK] PhoWhisper completed in {phowhisper_time:.2f}s")
    print(f"[INFO] Total characters: {len(phowhisper_transcript)}")
    
    # Save PhoWhisper result to session folder
    phowhisper_file = f"{SESSION_DIR}/phowhisper_{audio_filename}_{timestamp}.txt"
    with open(phowhisper_file, "w", encoding="utf-8") as f:
        f.write(phowhisper_transcript)
    print(f"[SAVE] PhoWhisper saved: {phowhisper_file}")
    
except Exception as e:
    print(f"[ERROR] PhoWhisper Error: {e}")
    import traceback
    traceback.print_exc()
    phowhisper_transcript = whisper_transcript  # Fallback to Whisper
    phowhisper_time = 0

# ============= STEP 3: QWEN2.5-1.5B FUSION =============
print(f"\n[AI] STEP 3: Qwen2.5-1.5B-Instruct Fusion...")
fusion_start = time.time()

try:
    print("[AI] Loading Qwen2.5-1.5B-Instruct (float16 for SPEED & FUSION)...")
    
    # Clear GPU memory before loading Qwen
    if torch.cuda.is_available():
        print("[GPU] Clearing VRAM...")
        torch.cuda.empty_cache()
        import gc
        gc.collect()
        print(f"[GPU] VRAM available: {torch.cuda.get_device_properties(0).total_memory / 1024**3:.1f}GB")
    
    vistral_load_start = time.time()
    
    # Use Qwen2.5-1.5B-Instruct - Lightweight, fast, good Vietnamese support
    model_name = "Qwen/Qwen2.5-1.5B-Instruct"
    
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    
    # Load with float16 and better memory management
    if torch.cuda.is_available():
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=torch.float16,
            device_map="auto",
            low_cpu_mem_usage=True,
            trust_remote_code=True,
        )
    else:
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            device_map="cpu",
            trust_remote_code=True,
        )
    
    print(f"[OK] Qwen2.5-1.5B loaded in {time.time() - vistral_load_start:.2f}s")
    
    # Combine both transcripts for SMART FUSION
    full_raw_text = f"TRANSCRIPT 1 (Whisper large-v3):\n{whisper_transcript}\n\nTRANSCRIPT 2 (PhoWhisper-large):\n{phowhisper_transcript}"
    
    # Original user prompt - Smart fusion with speaker role detection
    prompt_text = f"""<|im_start|>system
Báº¡n lÃ  trá»£ lÃ½ chuyÃªn xá»­ lÃ½ transcript tiáº¿ng Viá»‡t, Ä‘Æ°á»£c thiáº¿t káº¿ Ä‘á»ƒ lÃ m sáº¡ch dá»¯ liá»‡u Ä‘áº§u ra tá»« mÃ´ hÃ¬nh nháº­n dáº¡ng giá»ng nÃ³i (speech-to-text).
Nhiá»‡m vá»¥ cá»§a báº¡n lÃ  giá»¯ nguyÃªn ná»™i dung vÃ  Ã½ nghÄ©a gá»‘c, nhÆ°ng chá»‰nh sá»­a toÃ n bá»™ lá»—i chÃ­nh táº£, ngá»¯ phÃ¡p, dáº¥u cÃ¢u vÃ  Ä‘á»‹nh dáº¡ng láº¡i cho dá»… Ä‘á»c.<|im_end|>
<|im_start|>user

NHIá»†M Vá»¤:
1. Sá»­a lá»—i chÃ­nh táº£, lá»—i gÃµ, lá»—i ngá»¯ phÃ¡p.
2. ThÃªm Ä‘áº§y Ä‘á»§ dáº¥u cÃ¢u (cháº¥m, pháº©y, há»i, than...) Ä‘Ãºng vá»‹ trÃ­ vÃ  tá»± nhiÃªn.
3. PhÃ¢n vai ngÆ°á»i nÃ³i rÃµ rÃ ng, gá»“m cÃ¡c nhÃ³m:
   - Há»‡ thá»‘ng: Giá»ng mÃ¡y, thÃ´ng bÃ¡o tá»± Ä‘á»™ng (vÃ­ dá»¥: "Cáº£m Æ¡n quÃ½ khÃ¡ch Ä‘Ã£ gá»i Ä‘áº¿n...")
   - NhÃ¢n viÃªn: NgÆ°á»i Ä‘áº¡i diá»‡n cÃ´ng ty, tá»•ng Ä‘Ã i viÃªn, nhÃ¢n viÃªn há»— trá»£.
   - KhÃ¡ch hÃ ng: NgÆ°á»i gá»i Ä‘áº¿n hoáº·c ngÆ°á»i Ä‘Æ°á»£c gá»i.
4. TÃ¡ch Ä‘oáº¡n theo tá»«ng ngÆ°á»i nÃ³i, má»—i lÆ°á»£t nÃ³i má»™t Ä‘oáº¡n riÃªng.
5. Giá»¯ nguyÃªn ná»™i dung vÃ  Ã½ nghÄ©a gá»‘c.
6. KhÃ´ng bá» hoáº·c thÃªm Ã½.
7. Äáº£m báº£o Ä‘oáº¡n há»™i thoáº¡i dá»… Ä‘á»c, Ä‘Ãºng chuáº©n tiáº¿ng Viá»‡t.
8. KhÃ´ng giáº£i thÃ­ch, khÃ´ng thÃªm ghi chÃº.

TRANSCRIPT Gá»C (tá»« 2 model speech-to-text, cÃ³ thá»ƒ sai chÃ­nh táº£, thiáº¿u dáº¥u hoáº·c ná»‘i liá»n tá»«):
{full_raw_text}

YÃŠU Cáº¦U Äáº¦U RA:
- Gá»™p thÃ´ng tin tá»« cáº£ 2 transcript, láº¥y pháº§n chÃ­nh xÃ¡c nháº¥t.
- Chá»‰ tráº£ vá» transcript Ä‘Ã£ Ä‘Æ°á»£c sá»­a lá»—i, chia vai vÃ  format rÃµ rÃ ng.
- Má»—i ngÆ°á»i nÃ³i hiá»ƒn thá»‹ trÃªn má»™t dÃ²ng riÃªng, cÃ³ dáº¡ng nhÆ° sau:

MáºªU Äá»ŠNH Dáº NG:
Há»‡ thá»‘ng: Xin cáº£m Æ¡n quÃ½ khÃ¡ch Ä‘Ã£ gá»i Ä‘áº¿n tá»•ng Ä‘Ã i Giao HÃ ng Nhanh.
KhÃ¡ch hÃ ng: Alo, cho tÃ´i há»i vá» Ä‘Æ¡n hÃ ng mÃ£ GHN12345 áº¡.
NhÃ¢n viÃªn: Dáº¡, em xin chÃ o anh áº¡. Anh vui lÃ²ng chá» em kiá»ƒm tra thÃ´ng tin Ä‘Æ¡n hÃ ng nhÃ©.
KhÃ¡ch hÃ ng: VÃ¢ng, cáº£m Æ¡n em.

LÆ¯U Ã:
- Suy luáº­n chá»§ ngá»¯ vÃ  ngá»¯ cáº£nh Ä‘á»ƒ phÃ¢n vai chÃ­nh xÃ¡c.
- Náº¿u khÃ´ng cháº¯c ngÆ°á»i nÃ³i lÃ  ai, hÃ£y suy luáº­n dá»±a trÃªn ngá»¯ cáº£nh:
  - "Xin chÃ o quÃ½ khÃ¡ch..." thÆ°á»ng lÃ  Há»‡ thá»‘ng hoáº·c NhÃ¢n viÃªn.
  - "Alo, tÃ´i muá»‘n há»i..." thÆ°á»ng lÃ  KhÃ¡ch hÃ ng.
  - "Em kiá»ƒm tra Ä‘Æ¡n giÃºp anh nhÃ©" thÆ°á»ng lÃ  NhÃ¢n viÃªn.
- Náº¿u váº«n khÃ´ng rÃµ, gÃ¡n lÃ  "NgÆ°á»i nÃ³i khÃ´ng xÃ¡c Ä‘á»‹nh:".
- KhÃ´ng thÃªm tiÃªu Ä‘á», khÃ´ng in láº¡i transcript gá»‘c, khÃ´ng thÃªm giáº£i thÃ­ch.
- Äáº£m báº£o vÄƒn báº£n cuá»‘i cÃ¹ng sáº¡ch, rÃµ, tá»± nhiÃªn, dá»… Ä‘á»c, Ä‘Ãºng ngá»¯ phÃ¡p tiáº¿ng Viá»‡t.
- QUAN TRá»ŒNG: Xuáº¥t Äáº¦Y Äá»¦ TOÃ€N Bá»˜ há»™i thoáº¡i tá»« Ä‘áº§u Ä‘áº¿n cuá»‘i, khÃ´ng bá» sÃ³t.<|im_end|>
<|im_start|>assistant"""
    
    print("[AI] Processing with Qwen2.5-1.5B...")
    inputs = tokenizer(prompt_text, return_tensors="pt").to(model.device)
    
    # Generate with optimized parameters for Qwen - LONG OUTPUT
    with torch.inference_mode():
        outputs = model.generate(
            **inputs,
            max_new_tokens=3072,  # Increased for full conversation
            min_new_tokens=500,   # Force minimum output length
            temperature=0.3,
            top_p=0.9,
            do_sample=True,
            repetition_penalty=1.1,  # Prevent loops
            pad_token_id=tokenizer.eos_token_id,
        )
    
    response = tokenizer.decode(outputs[0][len(inputs["input_ids"][0]):], skip_special_tokens=True)
    fused_text = response.strip()
    
    fusion_time = time.time() - fusion_start
    
    print("\n" + "=" * 80)
    print("[FINAL] QWEN2.5-1.5B ENHANCED RESULT (3-ROLE SPEAKER SEPARATION):")
    print("=" * 80)
    print(fused_text)
    print(f"[OK] Qwen2.5-1.5B fusion completed in {fusion_time:.2f}s")
    print(f"[INFO] Output length: {len(fused_text)} chars")
    
except Exception as e:
    print(f"[ERROR] Qwen2.5-1.5B Fusion Error: {e}")
    import traceback
    traceback.print_exc()
    # Fallback: use longer transcript
    print("[FALLBACK] Using longer transcript as fallback...")
    if len(phowhisper_transcript) > len(whisper_transcript):
        fused_text = phowhisper_transcript
        print(f"[INFO] Using PhoWhisper ({len(phowhisper_transcript)} chars)")
    else:
        fused_text = whisper_transcript
        print(f"[INFO] Using Whisper ({len(whisper_transcript)} chars)")
    fusion_time = 0

# ============= SAVE FINAL RESULTS =============
print("\n[SAVE] Saving final results...")

# Save final fused result to session folder (MAIN OUTPUT)
final_fused_path = f"{SESSION_DIR}/final_transcript_{audio_filename}_{timestamp}.txt"
with open(final_fused_path, 'w', encoding='utf-8') as f:
    f.write(fused_text)
print(f"[OK] Final result saved: {final_fused_path}")

# Save processing log to session folder (DETAILED LOG)
log_path = f"{SESSION_DIR}/processing_log_{audio_filename}_{timestamp}.txt"
with open(log_path, 'w', encoding='utf-8') as f:
    f.write("=" * 80 + "\n")
    f.write("DUAL MODEL TRANSCRIPTION - QWEN2.5-1.5B FUSION\n")
    f.write("=" * 80 + "\n\n")
    f.write(f"Audio: {audio_path}\n")
    f.write(f"Duration: {duration_trimmed:.2f}s\n")
    f.write(f"Timestamp: {timestamp}\n\n")
    
    f.write("=" * 80 + "\n")
    f.write("STEP 1: WHISPER LARGE-V3 RESULT\n")
    f.write("=" * 80 + "\n")
    f.write(whisper_transcript + "\n\n")
    
    f.write("=" * 80 + "\n")
    f.write("STEP 2: PHOWHISPER-LARGE RESULT\n")
    f.write("=" * 80 + "\n")
    f.write(phowhisper_transcript + "\n\n")
    
    f.write("=" * 80 + "\n")
    f.write("STEP 3: VISTRAL-7B ENHANCED RESULT (3-ROLE SEPARATION)\n")
    f.write("=" * 80 + "\n")
    f.write(fused_text + "\n\n")
    
    f.write("=" * 80 + "\n")
    f.write("PROCESSING TIME SUMMARY:\n")
    f.write("=" * 80 + "\n")
    f.write(f"Audio preprocessing: {preprocess_time:.2f}s\n")
    f.write(f"Whisper large-v3: {whisper_time:.2f}s\n")
    f.write(f"PhoWhisper-large: {phowhisper_time:.2f}s\n")
    f.write(f"Qwen2.5-1.5B fusion: {fusion_time:.2f}s\n")
    f.write(f"Total: {preprocess_time + whisper_time + phowhisper_time + fusion_time:.2f}s\n")

print(f"[OK] Processing log saved: {log_path}")

print(f"\n[SUCCESS] ALL FILES SAVED TO SESSION:")
print(f"   ðŸ“ Session folder: {SESSION_DIR}")
print(f"   ðŸ“„ Whisper transcript:    whisper_{audio_filename}_{timestamp}.txt")
print(f"   ðŸ“„ PhoWhisper transcript: phowhisper_{audio_filename}_{timestamp}.txt")
print(f"   ðŸ“„ Final transcript:      final_transcript_{audio_filename}_{timestamp}.txt")
print(f"   ðŸ“„ Processing log:        processing_log_{audio_filename}_{timestamp}.txt")
print(f"   ðŸ”Š Processed audio:       {cleaned_path}")

# ============= STATISTICS =============
total_time = preprocess_time + whisper_time + phowhisper_time + fusion_time

print("\n" + "=" * 80)
print("[STATS] PROCESSING TIME SUMMARY:")
print("=" * 80)
print(f"  [STEP 1] Audio preprocessing:      {preprocess_time:7.2f}s")
print(f"  [STEP 2] Whisper large-v3:         {whisper_time:7.2f}s")
print(f"  [STEP 3] PhoWhisper-large:         {phowhisper_time:7.2f}s")
print(f"  [STEP 4] Vistral-7B Enhancement: {fusion_time:7.2f}s")
print(f"  [LINE] " + "-" * 60)
print(f"  [TOTAL] TOTAL TIME:                {total_time:7.2f}s")
print("=" * 80)

print("\n[INFO] BENEFITS OF QWEN2.5-1.5B FUSION:")
print("  âœ… QWEN2.5-1.5B - Lightweight & Fast model by Alibaba")
print("  âœ… MULTILINGUAL - Good Vietnamese support")
print("  âœ… DUAL FUSION - Combines Whisper + PhoWhisper transcripts")
print("  âœ… 3-ROLE SEPARATION - System, Employee, Customer speakers")
print("  âœ… FLOAT16 PRECISION - GPU acceleration")
print("  âœ… SMART CORRECTION - Grammar, punctuation, formatting")
print(f"  âœ… Processing time: {fusion_time:.1f}s for AI fusion")

print("\n" + "=" * 80)
print("[SUCCESS] DUAL MODEL PROCESSING COMPLETED!")
print("=" * 80)



