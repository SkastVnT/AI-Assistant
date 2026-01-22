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

AUDIO_PATH = os.getenv("AUDIO_PATH", "./audio/sample.mp3")

# Create directories
def create_directories():
    directories = ["./audio", "./result/raw", "./result/gemini", "./result/dual"]
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"[FOLDER] Created/Checked directory: {dir_path}")

create_directories()

# ============= LOAD T5 MODEL =============
print("[AI] Loading T5 Model for Text Fusion...")
t5_load_start = time.time()

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[OK] Using device: {device}")

try:
    # S[?] d[?]ng T5-base cho t[?]c d[?], c[?] th[?] n[?]ng c[?]p l[?]n large n[?]u c[?]n
    model_name = "google/t5-v1_1-base"
    print(f"[?] Loading {model_name}...")
    
    t5_tokenizer = T5Tokenizer.from_pretrained(model_name)
    t5_model = T5ForConditionalGeneration.from_pretrained(
        model_name,
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        device_map="auto" if device == "cuda" else None,
        low_cpu_mem_usage=True
    )
    
    if device == "cuda":
        t5_model = t5_model.to(device)
    
    t5_load_time = time.time() - t5_load_start
    print(f"[OK] T5 model loaded in {t5_load_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] T5 loading error: {e}")
    print("Falling back to simple fusion...")
    t5_model = None
    t5_tokenizer = None
    t5_load_time = 0

# Audio preprocessing (optimized)
def preprocess_audio(input_path, output_path):
    print(f"[FOLDER] Loading audio: {input_path}")
    y_original, sr_original = librosa.load(input_path, sr=None)
    print(f"   Original - Sample rate: {sr_original}Hz, Duration: {len(y_original)/sr_original:.2f}s")
    
    # Resample to 16kHz (optimal for both models)
    y = librosa.resample(y_original, orig_sr=sr_original, target_sr=16000)
    sr = 16000
    
    # Light processing only
    y = librosa.util.normalize(y, norm=np.inf, axis=None)
    y_trimmed, _ = librosa.effects.trim(y, top_db=30)
    
    # Minimal filtering
    sos = signal.butter(2, 50, "hp", fs=sr, output="sos")
    y_filtered = signal.sosfilt(sos, y_trimmed)
    
    y_final = librosa.util.normalize(y_filtered, norm=np.inf, axis=None)
    sf.write(output_path, y_final, sr)
    print(f"   [OK] Processed audio: {len(y_final)/sr:.2f}s")
    return output_path

print("=" * 80)
print("[LAUNCH] DUAL MODEL APP: Whisper + PhoWhisper + T5 Fusion")
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
    processed_audio_path = f"./audio/app_processed_{file_name}_{timestamp}.wav"
    
    cleaned_path = preprocess_audio(AUDIO_PATH, processed_audio_path)
    preprocessing_time = time.time() - preprocessing_start
    print(f"[OK] Audio preprocessing completed in {preprocessing_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] Audio preprocessing failed: {e}")
    cleaned_path = AUDIO_PATH
    preprocessing_time = 0

# ============= B[?][?]C 2: WHISPER TRANSCRIPTION =============
print(f"\n[MIC] B[?][?]C 2A: Whisper large-v3...")
whisper_transcript = ""
whisper_time = 0

try:
    from faster_whisper import WhisperModel
    
    print("Loading Whisper large-v3...")
    whisper_load_start = time.time()
    
    try:
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
        beam_size=3,  # Reduced for speed
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=True  # Enable VAD for speed
    )
    
    whisper_segments = []
    for segment in segments:
        text = segment.text.strip()
        whisper_segments.append(text)
    
    whisper_transcript = " ".join(whisper_segments)
    whisper_time = time.time() - whisper_start
    
    print("\n" + "=" * 50)
    print("WHISPER RESULT:")
    print("=" * 50)
    print(whisper_transcript[:300] + "..." if len(whisper_transcript) > 300 else whisper_transcript)
    print(f"\n[OK] Whisper completed in {whisper_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] Whisper Error: {e}")
    whisper_transcript = "[Whisper transcription failed]"

# ============= B[?][?]C 3: PHOWHISPER TRANSCRIPTION (OPTIMIZED) =============
print(f"\n[MIC] B[?][?]C 2B: PhoWhisper (SPEED OPTIMIZED)...")
phowhisper_transcript = ""
phowhisper_time = 0

try:
    # Disable warnings for cleaner output
    os.environ['HF_HUB_DISABLE_SAFETENSORS_LOAD_WARNING'] = '1'
    os.environ['TRANSFORMERS_VERBOSITY'] = 'error'
    
    from transformers import WhisperProcessor, WhisperForConditionalGeneration
    import torch
    
    print("Loading PhoWhisper (OPTIMIZED)...")
    phowhisper_load_start = time.time()
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[OK] Using device: {device}")
    
    # Load audio first to check duration
    audio, sr = librosa.load(cleaned_path, sr=16000)
    audio_duration = len(audio) / sr
    print(f"   [CHART] Audio duration: {audio_duration:.1f}s")
    
    processor = WhisperProcessor.from_pretrained("vinai/PhoWhisper-large")
    
    # Optimized model loading
    pho_model = WhisperForConditionalGeneration.from_pretrained(
        "vinai/PhoWhisper-large",
        torch_dtype=torch.float16 if device == "cuda" else torch.float32,
        use_safetensors=False,
        low_cpu_mem_usage=True,
        device_map="auto" if device == "cuda" else None
    )
    
    if device == "cuda":
        pho_model = pho_model.half().to(device)
        torch.cuda.empty_cache()
        print("[OK] GPU optimized")
    else:
        pho_model = pho_model.to(device)
        print("[OK] CPU mode")
    
    phowhisper_load_time = time.time() - phowhisper_load_start
    print(f"[OK] PhoWhisper loaded in {phowhisper_load_time:.2f}s")
    
    print("Transcribing with PhoWhisper (OPTIMIZED)...")
    phowhisper_start = time.time()
    
    # Optimized processing strategy
    if audio_duration > 45:  # Long audio - use chunking
        print(f"   [?] Long audio detected, using optimized chunking...")
        
        chunk_duration = 20  # Smaller chunks for speed
        chunk_samples = chunk_duration * sr
        transcriptions = []
        
        num_chunks = int(len(audio)/chunk_samples) + 1
        print(f"   [?] Processing {num_chunks} chunks...")
        
        for i in range(0, len(audio), chunk_samples):
            chunk_idx = i // chunk_samples + 1
            chunk = audio[i:i + chunk_samples]
            
            if len(chunk) < 3 * sr:  # Skip very short chunks
                continue
            
            inputs = processor(chunk, sampling_rate=16000, return_tensors="pt")
            
            if device == "cuda":
                inputs = {k: v.to(device).half() if v.dtype == torch.float32 else v.to(device) for k, v in inputs.items()}
            else:
                inputs = {k: v.to(device) for k, v in inputs.items()}
            
            with torch.no_grad():
                predicted_ids = pho_model.generate(
                    inputs["input_features"],
                    max_length=256,  # Reduced for speed
                    num_beams=2,     # Minimal beam search
                    do_sample=False,
                    temperature=0.0,
                    language="vi",
                    task="transcribe",
                    forced_decoder_ids=processor.get_decoder_prompt_ids(language="vi", task="transcribe")
                )
            
            chunk_text = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
            if chunk_text.strip():
                transcriptions.append(chunk_text.strip())
                print(f"   [OK] Chunk {chunk_idx}/{num_chunks}")
        
        phowhisper_transcript = " ".join(transcriptions)
        
    else:  # Short audio - single pass
        print(f"   [?] Short audio, single pass processing...")
        
        inputs = processor(audio, sampling_rate=16000, return_tensors="pt")
        
        if device == "cuda":
            inputs = {k: v.to(device).half() if v.dtype == torch.float32 else v.to(device) for k, v in inputs.items()}
        else:
            inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad():
            predicted_ids = pho_model.generate(
                inputs["input_features"],
                max_length=384,
                num_beams=3,  # Balanced speed vs quality
                do_sample=False,
                temperature=0.0,
                language="vi",
                task="transcribe",
                forced_decoder_ids=processor.get_decoder_prompt_ids(language="vi", task="transcribe")
            )
        
        phowhisper_transcript = processor.batch_decode(predicted_ids, skip_special_tokens=True)[0]
    
    phowhisper_time = time.time() - phowhisper_start
    
    print("\n" + "=" * 50)
    print("PHOWHISPER RESULT:")
    print("=" * 50)
    print(phowhisper_transcript[:300] + "..." if len(phowhisper_transcript) > 300 else phowhisper_transcript)
    print(f"\n[OK] PhoWhisper completed in {phowhisper_time:.2f}s")
    
except Exception as e:
    print(f"[ERROR] PhoWhisper Error: {e}")
    import traceback
    traceback.print_exc()
    phowhisper_transcript = "[PhoWhisper transcription failed]"

# ============= B[?][?]C 4: T5 FUSION =============
print(f"\n[AI] B[?][?]C 3: T5 Text Fusion...")
fusion_start = time.time()

def t5_fusion_optimized(whisper_text, phowhisper_text):
    """Optimized T5 fusion for Vietnamese"""
    if not t5_model or not t5_tokenizer:
        # Fallback to simple rule-based fusion
        print("   [FAST] Using rule-based fusion (T5 not available)")
        if len(phowhisper_text) > len(whisper_text):
            return phowhisper_text
        else:
            return whisper_text
    
    try:
        print("   [AI] T5 processing...")
        
        # Simple prompt that works better with T5
        prompt = f"summarize: {whisper_text[:400]} AND {phowhisper_text[:400]}"
        
        # Encode with proper length handling
        inputs = t5_tokenizer.encode(
            prompt, 
            return_tensors="pt", 
            max_length=512, 
            truncation=True
        ).to(device)
        
        # Generate with conservative settings
        with torch.no_grad():
            outputs = t5_model.generate(
                inputs,
                max_length=256,
                num_beams=2,
                temperature=0.8,
                do_sample=False,
                early_stopping=True
            )
        
        # Decode result
        fused_text = t5_tokenizer.decode(outputs[0], skip_special_tokens=True)
        
        # If T5 output is nonsensical, fallback to rule-based
        if len(fused_text) < 20 or "unk" in fused_text.lower():
            print("   [WARN] T5 output poor quality, using rule-based fallback")
            if len(phowhisper_text) > len(whisper_text):
                return phowhisper_text
            else:
                return whisper_text
        
        return fused_text
        
    except Exception as e:
        print(f"   [ERROR] T5 fusion error: {e}")
        # Intelligent fallback
        if len(phowhisper_text) > len(whisper_text) * 1.2:
            return phowhisper_text
        else:
            return whisper_text

# Execute fusion
try:
    fused_text = t5_fusion_optimized(whisper_transcript, phowhisper_transcript)
    fusion_time = time.time() - fusion_start
    
    print("\n" + "=" * 80)
    print("[BEST] FUSED RESULT (T5 + Fallback Logic):")
    print("=" * 80)
    print(fused_text)
    print(f"\n[OK] Fusion completed in {fusion_time:.2f}s")
    
    # ============= L[?]U K[?]T QU[?] =============
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]
    
    # Save comprehensive result
    dual_output_file = f"./result/dual/app_t5_{file_name}_{timestamp}.txt"
    with open(dual_output_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("DUAL MODEL APP REPORT (T5 FUSION)\n")
        f.write("=" * 80 + "\n")
        f.write(f"Original file: {AUDIO_PATH}\n")
        f.write(f"Processed file: {cleaned_path}\n")
        f.write(f"Timestamp: {timestamp}\n\n")
        
        f.write("=" * 80 + "\n")
        f.write("MODEL 1: WHISPER LARGE-V3\n")
        f.write("=" * 80 + "\n\n")
        f.write(whisper_transcript)
        
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("MODEL 2: PHOWHISPER-LARGE (OPTIMIZED)\n")
        f.write("=" * 80 + "\n\n")
        f.write(phowhisper_transcript)
        
        f.write("\n\n" + "=" * 80 + "\n")
        f.write("[BEST] T5 FUSED RESULT\n")
        f.write("=" * 80 + "\n\n")
        f.write(fused_text)
    
    # Save clean version
    fused_clean_file = f"./result/gemini/app_t5_clean_{file_name}_{timestamp}.txt"
    with open(fused_clean_file, "w", encoding="utf-8") as f:
        f.write("=" * 80 + "\n")
        f.write("DUAL MODEL APP - T5 FUSION TRANSCRIPT\n")
        f.write("(Whisper + PhoWhisper + T5 AI)\n")
        f.write("=" * 80 + "\n")
        f.write(f"File: {AUDIO_PATH}\n")
        f.write(f"Timestamp: {timestamp}\n")
        f.write("=" * 80 + "\n\n")
        f.write(fused_text)
    
    total_time = time.time() - total_start_time
    
    print(f"\n\n[OK] DUAL MODEL APP FILES SAVED:")
    print(f"   [CHART] Full report:     {dual_output_file}")
    print(f"   [BEST] Clean result:    {fused_clean_file}")
    
    print("\n" + "=" * 80)
    print("[?][?]  APP PERFORMANCE SUMMARY:")
    print("=" * 80)
    print(f"  [?] T5 model loading:        {t5_load_time:>8.2f}s")
    print(f"  [?] Audio preprocessing:     {preprocessing_time:>8.2f}s")
    print(f"  [?] Whisper transcription:   {whisper_time:>8.2f}s")
    print(f"  [?] PhoWhisper (optimized):  {phowhisper_time:>8.2f}s")
    print(f"  [?] T5 fusion:               {fusion_time:>8.2f}s")
    print(f"  [?] [?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?][?]")
    print(f"  [?] TOTAL TIME:              {total_time:>8.2f}s")
    print("=" * 80)
    
    print(f"\n[IDEA] APP FEATURES:")
    print(f"  [OK] T5 AI fusion with intelligent fallback")
    print(f"  [OK] Optimized PhoWhisper processing")
    print(f"  [OK] Adaptive chunking for long audio")
    print(f"  [OK] GPU acceleration when available")
    print(f"  [OK] Comprehensive error handling")
    
except Exception as e:
    print(f"[ERROR] Fusion Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 80)
print("[SUCCESS] DUAL MODEL APP COMPLETED!")
print("=" * 80)