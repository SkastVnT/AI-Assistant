# -*- coding: utf-8 -*-
# CI fix: corrected syntax error (extra quote) on GEMINI_API_KEY line
# Ref: d0861426e9d20a560020005122410a5ee240802a
"""
DUAL MODEL WITH GEMINI SEMANTIC FUSION
Whisper large-v3 + PhoWhisper-large + Gemini AI Smart Fusion
"""
import os
import time
import datetime
import librosa
import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from scipy import signal
from google import genai

# ============= CONFIGURATION =============
# Load .env from config folder
env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config', '.env')
load_dotenv(env_path)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUDIO_PATH = os.getenv("AUDIO_PATH", r"C:\Users\Asus\Downloads\d08deb45-d23d-449e-9fdf-7b40b1c1050d.mp3")

print(f"[KEY] Gemini API Key: {GEMINI_API_KEY[:20]}...{GEMINI_API_KEY[-4:]}")

# Configure Gemini
client = genai.Client(api_key=GEMINI_API_KEY)

# Create directories
def create_directories():
    directories = ["./audio", "./result/raw", "./result/gemini", "./result/dual"]
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"[FOLDER] Created/Checked directory: {dir_path}")

create_directories()

# Audio preprocessing
def preprocess_audio(input_path, output_path):
    print(f"[FOLDER] Loading audio: {input_path}")
    y_original, sr_original = librosa.load(input_path, sr=None)
    print(f"   Original - Sample rate: {sr_original}Hz, Duration: {len(y_original)/sr_original:.2f}s")
    
    y = librosa.resample(y_original, orig_sr=sr_original, target_sr=16000)
    sr = 16000
    
    y = librosa.util.normalize(y, norm=np.inf, axis=None)
    print("   [OK] Normalized volume")
    
    y_trimmed, _ = librosa.effects.trim(y, top_db=30)
    print(f"   [OK] Trimmed silence: {len(y_trimmed)/sr:.2f}s")
    
    sos = signal.butter(2, 50, "hp", fs=sr, output="sos")
    y_filtered = signal.sosfilt(sos, y_trimmed)
    print("   [OK] Applied high-pass filter")
    
    y_final = librosa.util.normalize(y_filtered, norm=np.inf, axis=None)
    sf.write(output_path, y_final, sr)
    print(f"   [OK] Saved processed audio: {len(y_final)/sr:.2f}s")
    return output_path

print("=" * 80)
print("[LAUNCH] DUAL MODEL: Whisper large-v3 + PhoWhisper-large + Gemini AI Fusion")
print("=" * 80)

total_start_time = time.time()

# ============= STEP 1: AUDIO PREPROCESSING =============
print("\n[TOOL] STEP 1: Audio Preprocessing...")
preprocessing_start = time.time()

try:
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]
    processed_audio_path = f"./audio/dual_processed_{file_name}_{timestamp}.wav"
    
    cleaned_path = preprocess_audio(AUDIO_PATH, processed_audio_path)
    preprocessing_time = time.time() - preprocessing_start
    print(f"[OK] Audio preprocessing completed in {preprocessing_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] Audio preprocessing failed: {e}")
    cleaned_path = AUDIO_PATH
    preprocessing_time = 0

# ============= STEP 2A: WHISPER LARGE-V3 TRANSCRIPTION =============
print(f"\n[MIC] STEP 2A: Whisper large-v3 Transcription...")
whisper_transcript = ""
whisper_time = 0

try:
    from faster_whisper import WhisperModel
    
    print("Loading Whisper large-v3...")
    whisper_load_start = time.time()
    
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        compute_type = "float16" if device == "cuda" else "int8"
        print(f"[OK] Using device: {device}")
    except:
        device = "cpu"
        compute_type = "int8"
    
    model = WhisperModel("large-v3", device=device, compute_type=compute_type)
    print(f"[OK] Whisper loaded in {time.time() - whisper_load_start:.2f}s")
    
    print("Transcribing with Whisper...")
    whisper_start = time.time()
    segments, info = model.transcribe(
        cleaned_path,
        language="vi",
        beam_size=5,
        vad_filter=True,
    )
    
    whisper_transcript = " ".join([segment.text for segment in segments])
    whisper_time = time.time() - whisper_start
    
    print("\n" + "=" * 80)
    print("WHISPER LARGE-V3 RESULT:")
    print("=" * 80)
    print(whisper_transcript)
    print(f"[OK] Whisper completed in {whisper_time:.2f}s")
    
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
    from transformers import WhisperForConditionalGeneration, WhisperProcessor
    
    print("Loading PhoWhisper-large...")
    pho_load_start = time.time()
    
    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"[OK] Using device: {device}")
    except:
        device = "cpu"
    
    print("[AI] Loading PhoWhisper model (OPTIMIZED)...")
    try:
        pho_processor = WhisperProcessor.from_pretrained("vinai/PhoWhisper-large")
        pho_model = WhisperForConditionalGeneration.from_pretrained(
            "vinai/PhoWhisper-large",
            device_map=device,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        )
    except Exception as e:
        print(f"[WARN] Model loading error: {e}")
        print("[AI] Trying FAST CPU fallback...")
        pho_processor = WhisperProcessor.from_pretrained("vinai/PhoWhisper-large")
        pho_model = WhisperForConditionalGeneration.from_pretrained("vinai/PhoWhisper-large")
        pho_model = pho_model.to(device)
        print("[OK] Fast CPU fallback")
    
    print(f"[OK] PhoWhisper loaded in {time.time() - pho_load_start:.2f}s")
    
    print("Transcribing with PhoWhisper (OPTIMIZED)...")
    pho_start = time.time()
    
    audio, sr = librosa.load(cleaned_path, sr=16000)
    
    duration = len(audio) / sr
    print(f"   [CHART] Audio duration: {duration:.1f}s")
    
    # Process in chunks for long audio
    chunk_duration = 25  # seconds
    chunk_size = chunk_duration * sr
    num_chunks = int(np.ceil(duration / chunk_duration))
    
    print(f"   [AI] Processing {num_chunks} chunks ({chunk_duration}s each)...")
    
    transcripts = []
    for i in range(num_chunks):
        start_idx = i * chunk_size
        end_idx = min((i + 1) * chunk_size, len(audio))
        chunk = audio[start_idx:end_idx]
        
        chunk_start = time.time()
        
        inputs = pho_processor(
            chunk,
            sampling_rate=16000,
            return_tensors="pt"
        ).input_features.to(device)
        
        with torch.no_grad():
            predicted_ids = pho_model.generate(inputs)
        
        transcript = pho_processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
        transcripts.append(transcript)
        
        chunk_time = time.time() - chunk_start
        print(f"   [AI] Chunk {i+1}/{num_chunks}... [OK] {chunk_time:.1f}s")
    
    phowhisper_transcript = " ".join(transcripts)
    phowhisper_time = time.time() - pho_start
    
    print("\n" + "=" * 80)
    print("PHOWHISPER-LARGE RESULT:")
    print("=" * 80)
    print(phowhisper_transcript)
    print(f"[OK] PhoWhisper completed in {phowhisper_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] PhoWhisper Error: {e}")
    import traceback
    traceback.print_exc()
    phowhisper_transcript = "[PhoWhisper transcription failed]"

# ============= STEP 3: GEMINI AI SEMANTIC FUSION =============
print(f"\n[AI] STEP 3: Gemini AI Semantic Fusion...")
fusion_start = time.time()

try:
    prompt = f"""Ban la chuyen gia tieng Viet. Nhiem vu cua ban la SMART FUSION hai transcript tu hai model AI khac nhau de tao ra mot transcript chinh xac nhat.

**TRANSCRIPT 1 - Whisper large-v3:**
{whisper_transcript}

**TRANSCRIPT 2 - PhoWhisper-large:**
{phowhisper_transcript}

**NHIEM VU:**
1. PHAN TICH CA HAI TRANSCRIPT va xac dinh phan nao CHINH XAC hon
2. KET HOP thong minh de tao ra ban transcript HOAN HAO nhat
3. SUA LOI chinh ta, ngu phap neu co
4. GIU NGUYEN noi dung, y nghia goc cua nguoi noi
5. LOAI BO cac tu lap lai, tiec dam, tieng on khong can thiet
6. DAM BAO van phong tu nhien, de doc, de hieu

**CHI TRA VE BAN TRANSCRIPT CUOI CUNG, KHONG GIAI THICH.**"""

    print("[AI] Sending to Gemini AI...")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents=prompt
    )
    fused_text = response.text.strip()
    
    fusion_time = time.time() - fusion_start
    
    print("\n" + "=" * 80)
    print("[BEST] FUSED RESULT (Gemini AI Semantic Fusion):")
    print("=" * 80)
    print(fused_text)
    print(f"[OK] Gemini fusion completed in {fusion_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] Gemini Fusion Error: {e}")
    # Fallback: use longer transcript
    if len(whisper_transcript) > len(phowhisper_transcript):
        fused_text = whisper_transcript
    else:
        fused_text = phowhisper_transcript
    fusion_time = 0

# ============= SAVE RESULTS =============
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
file_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]

# Save comparison report
dual_output_file = f"./result/dual/dual_models_gemini_{file_name}_{timestamp}.txt"
with open(dual_output_file, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\n")
    f.write("DUAL MODEL COMPARISON REPORT (WITH GEMINI AI FUSION)\n")
    f.write("=" * 80 + "\n")
    f.write(f"Original file: {AUDIO_PATH}\n")
    f.write(f"Timestamp: {timestamp}\n")
    f.write("=" * 80 + "\n\n")
    
    f.write("WHISPER LARGE-V3 RESULT:\n")
    f.write("-" * 80 + "\n")
    f.write(whisper_transcript + "\n\n")
    
    f.write("PHOWHISPER-LARGE RESULT:\n")
    f.write("-" * 80 + "\n")
    f.write(phowhisper_transcript + "\n\n")
    
    f.write("GEMINI AI FUSED RESULT:\n")
    f.write("-" * 80 + "\n")
    f.write(fused_text + "\n")

# Save final fused transcript
fused_clean_file = f"./result/gemini/dual_fused_gemini_{file_name}_{timestamp}.txt"
with open(fused_clean_file, "w", encoding="utf-8") as f:
    f.write("=" * 80 + "\n")
    f.write("DUAL MODEL FUSION TRANSCRIPT (GEMINI AI SEMANTIC FUSION)\n")
    f.write("(Whisper large-v3 + PhoWhisper-large + Gemini AI)\n")
    f.write("=" * 80 + "\n")
    f.write(f"Original file: {AUDIO_PATH}\n")
    f.write(f"Timestamp: {timestamp}\n")
    f.write("=" * 80 + "\n\n")
    f.write(fused_text)

total_time = time.time() - total_start_time

print(f"\n\n[OK] DUAL MODEL GEMINI FILES SAVED:")
print(f"   [CHART] Comparison report:  {dual_output_file}")
print(f"   [BEST] Fused transcript:   {fused_clean_file}")
if cleaned_path != AUDIO_PATH:
    print(f"   [MUSIC] Processed audio:    {cleaned_path}")

print("\n" + "=" * 80)
print("[STATS] DUAL MODEL GEMINI - THOI GIAN THUC HIEN:")
print("=" * 80)
print(f"  [TIME] Audio preprocessing:     {preprocessing_time:>8.2f}s")
print(f"  [TIME] Whisper large-v3:        {whisper_time:>8.2f}s")
print(f"  [TIME] PhoWhisper-large:        {phowhisper_time:>8.2f}s")
print(f"  [TIME] Gemini AI Fusion:        {fusion_time:>8.2f}s")
print(f"  [LINE] " + "-" * 60)
print(f"  [TOTAL] TONG CONG:               {total_time:>8.2f}s")
print("=" * 80)

print(f"\n[IDEA] LOI ICH GEMINI AI FUSION:")
print(f"  [OK] AI SEMANTIC - Hieu ngu nghia sau trong tieng Viet")
print(f"  [OK] SMART FUSION - Ket hop thong minh 2 model")
print(f"  [OK] AUTO CORRECTION - Tu dong sua loi chinh ta, ngu phap")
print(f"  [OK] CONTEXT AWARE - Hieu context va noi dung hoi thoai")
print(f"  [OK] NATURAL OUTPUT - Van phong tu nhien, de doc")
print(f"  [OK] Chi mat {fusion_time:.1f}s cho AI fusion")

print("\n" + "=" * 80)
print("[SUCCESS] DUAL MODEL GEMINI PROCESSING COMPLETED!")
print("=" * 80)
