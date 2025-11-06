# -*- coding: utf-8 -*-
import os
import time

import google.generativeai as genai
import librosa
import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from scipy import signal

# ============= CONFIGURATION =============
# Load environment variables t[?] file .env
load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
AUDIO_PATH = os.getenv(
    "AUDIO_PATH", r"C:\Users\Asus\Downloads\d08deb45-d23d-449e-9fdf-7b40b1c1050d.mp3"
)

# Option to skip audio preprocessing
SKIP_AUDIO_PREPROCESSING = (
    os.getenv("SKIP_AUDIO_PREPROCESSING", "false").lower() == "true"
)

# Whisper model selection
WHISPER_MODEL = os.getenv(
    "WHISPER_MODEL", "large-v3"
)  # Options: large-v3, large-v2, large, distil-large-v3, medium


# T[?]o c[?]c th[?] m[?]c c[?]n thi[?]t
def create_directories():
    """T[?]o c[?]c th[?] m[?]c d[?] l[?]u tr[?] file"""
    directories = ["./audio", "./result/raw", "./result/gemini"]
    for dir_path in directories:
        os.makedirs(dir_path, exist_ok=True)
        print(f"[FOLDER] Created/Checked directory: {dir_path}")


create_directories()

# Ki[?]m tra API key
if not GEMINI_API_KEY or GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    print("=" * 60)
    print("[WARN]  CH[?]A CONFIGURATION GEMINI API KEY!")
    print("=" * 60)
    print("\nH[?][?]ng d[?]n:")
    print("1. L[?]y API key t[?]i: https://aistudio.google.com/apikey")
    print("2. M[?] file .env")
    print("3. Thay YOUR_GEMINI_API_KEY_HERE b[?]ng API key c[?]a b[?]n")
    print("4. L[?]u file v[?] ch[?]y l[?]i script")
    print("\nV[?] d[?] trong file .env:")
    print("GEMINI_API_KEY=AIzaSyAbCdEf123456...")
    print("=" * 60)
    exit(1)

# C[?]u h[?]nh Gemini
genai.configure(api_key=GEMINI_API_KEY)
# S[?] d[?]ng gemini-2.5-flash (model m[?]i nh[?]t)
model = genai.GenerativeModel("models/gemini-2.5-flash")


# ============= AUDIO PREPROCESSING =============
def preprocess_audio(input_path, output_path):
    """
    X[?] l[?] audio nh[?] nh[?]ng d[?] c[?]i thi[?]n ch[?]t l[?][?]ng cho transcription
    """
    print(f"[FOLDER] Loading audio: {input_path}")

    # Load audio v[?]i sample rate g[?]c tr[?][?]c, r[?]i m[?]i resample
    y_original, sr_original = librosa.load(input_path, sr=None)
    print(
        f"   Original - Sample rate: {sr_original}Hz, Duration: {len(y_original)/sr_original:.2f}s"
    )

    # Resample to 16kHz (chu[?]n cho Whisper)
    y = librosa.resample(y_original, orig_sr=sr_original, target_sr=48000)
    sr = 48000

    # 1. Normalize volume nh[?] nh[?]ng
    y = librosa.util.normalize(y, norm=np.inf, axis=None)
    print("   [OK] Normalized volume")

    # 2. Trim silence r[?]t nh[?] (ch[?] b[?] ph[?]n im l[?]ng r[?]t r[?] r[?]ng)
    y_trimmed, _ = librosa.effects.trim(
        y, top_db=30
    )  # T[?]ng t[?] 20 l[?]n 30 d[?] b[?]o to[?]n nhi[?]u audio h[?]n
    print(f"   [OK] Gently trimmed silence: {len(y_trimmed)/sr:.2f}s")

    # 3. Ch[?] [?]p d[?]ng high-pass filter r[?]t nh[?]
    sos = signal.butter(2, 50, "hp", fs=sr, output="sos")  # Gi[?]m order v[?] frequency
    y_filtered = signal.sosfilt(sos, y_trimmed)
    print("   [OK] Applied gentle high-pass filter")

    # 4. KH[?]NG [?]p d[?]ng band-pass filter d[?] tr[?]nh m[?]t th[?]ng tin
    # Gi[?] nguy[?]n to[?]n b[?] t[?]n s[?]
    y_enhanced = y_filtered
    print("   [OK] Preserved all frequencies")

    # 5. Normalize l[?]i nh[?] nh[?]ng
    y_final = librosa.util.normalize(y_enhanced, norm=np.inf, axis=None)

    # Save processed audio
    sf.write(output_path, y_final, sr)
    print(f"   [OK] Saved processed audio: {len(y_final)/sr:.2f}s")

    return output_path


# ============= B[?][?]C 1: AUDIO PREPROCESSING =============
print("=" * 60)
print("Vietnamese Speech-to-Text (Audio Processing + Whisper + Gemini AI)")
print("=" * 60)

# B[?]t d[?]u d[?]m th[?]i gian t[?]ng
total_start_time = time.time()

# Ki[?]m tra file audio c[?] t[?]n t[?]i kh[?]ng
if not os.path.exists(AUDIO_PATH):
    print(f"[ERROR] Audio file not found: {AUDIO_PATH}")
    print("Vui l[?]ng ki[?]m tra d[?][?]ng d[?]n file.")
    exit(1)

print("\n[TOOL] B[?][?]C 1: Audio Preprocessing...")
preprocessing_start = time.time()

if SKIP_AUDIO_PREPROCESSING:
    print("[?][?]  Skipping audio preprocessing (using original file)")
    cleaned_path = AUDIO_PATH
    preprocessing_time = 0
else:
    try:
        # T[?]o t[?]n file processed v[?]i timestamp
        import datetime

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]
        processed_audio_path = f"./audio/processed_{file_name}_{timestamp}.wav"

        # X[?] l[?] audio
        cleaned_path = preprocess_audio(AUDIO_PATH, processed_audio_path)
        preprocessing_time = time.time() - preprocessing_start
        print(f"[OK] Audio preprocessing completed in {preprocessing_time:.2f}s")
        print(f"[OK] Processed audio saved to: {processed_audio_path}")

    except Exception as e:
        print(f"[ERROR] Audio preprocessing failed: {e}")
        print("[?] Install required packages:")
        print("   pip install scipy librosa soundfile")
        print("\n[?] Using original audio file instead...")
        cleaned_path = AUDIO_PATH
        preprocessing_time = 0

# ============= B[?][?]C 2: TRANSCRIBE =============
print(f"\n[MIC] B[?][?]C 2: Whisper Transcription...")

try:
    from faster_whisper import WhisperModel

    print(f"Loading Whisper model: {WHISPER_MODEL}")
    load_start = time.time()
    # T[?] d[?]ng ch[?]n device v[?] compute type t[?]i [?]u
    try:
        # Th[?] CUDA tr[?][?]c (n[?]u c[?] GPU)
        whisper_model = WhisperModel(
            WHISPER_MODEL, device="cuda", compute_type="float16"
        )
        print(f"[OK] Using GPU (CUDA) with {WHISPER_MODEL}")
    except:
        # Fallback v[?] CPU
        whisper_model = WhisperModel(WHISPER_MODEL, device="cpu", compute_type="int8")
        print(f"[OK] Using CPU with {WHISPER_MODEL}")

    load_time = time.time() - load_start
    print(f"[OK] Model {WHISPER_MODEL} loaded in {load_time:.2f}s")

    print(f"\nTranscribing: {cleaned_path}")
    print("(C[?] th[?] m[?]t v[?]i ph[?]t...)\n")

    transcribe_start = time.time()
    segments, info = whisper_model.transcribe(
        cleaned_path,  # S[?] d[?]ng file d[?] d[?][?]c x[?] l[?]
        language="vi",
        beam_size=5,
        temperature=0.0,
        condition_on_previous_text=False,
        vad_filter=False,
        word_timestamps=False,
        initial_prompt="C[?]m [?]n qu[?] kh[?]ch d[?] g[?]i d[?]n giao h[?]ng nhanh",
        # Lo[?]i b[?] t[?]t c[?] gi[?]i h[?]n d[?] l[?]y to[?]n b[?] n[?]i dung
    )

    print(
        f"[OK] Detected language: {info.language} (probability: {info.language_probability:.2f})"
    )

    # Thu th[?]p to[?]n b[?] transcript
    raw_transcript = []

    for segment in segments:
        text = segment.text.strip()
        raw_transcript.append(
            {"start": segment.start, "end": segment.end, "text": text}
        )

    full_raw_text = " ".join([seg["text"] for seg in raw_transcript])
    transcribe_time = time.time() - transcribe_start

    print("\n" + "=" * 60)
    print("Raw result:")
    print("=" * 60)
    print(full_raw_text)
    print(f"\n[OK] Transcription completed in {transcribe_time:.2f}s")

    # ============= B[?][?]C 3: X[?] L[?] V[?]I GEMINI =============
    print(f"\n[AI] B[?][?]C 3: Gemini AI Processing...")
    gemini_start = time.time()

    prompt = f"""
B[?]n l[?] **chuy[?]n gia x[?] l[?] ng[?]n ng[?] ti[?]ng Vi[?]t**, chuy[?]n l[?]m s[?]ch v[?] t[?]i c[?]u tr[?]c **b[?]n transcript t[?] d[?]ng** t[?] m[?] h[?]nh speech-to-text.
B[?]n c[?] hi[?]u bi[?]t s[?]u v[?] **ng[?] ph[?]p, ng[?] di[?]u, v[?]ng mi[?]n, v[?] ng[?] c[?]nh h[?]i tho[?]i t[?] nhi[?]n** c[?]a ng[?][?]i Vi[?]t [?] ba mi[?]n B[?]c [?] Trung [?] Nam.

---

## [TARGET] M[?]C TI[?]U
T[?]o ra b[?]n transcript **chu[?]n ti[?]ng Vi[?]t ph[?] th[?]ng, d[?] d[?]c, m[?]ch l[?]c, c[?] c[?]m x[?]c t[?] nhi[?]n**, 
nh[?]ng v[?]n **gi[?] nguy[?]n n[?]i dung, [?] d[?]nh v[?] ng[?] di[?]u g[?]c** c[?]a ng[?][?]i n[?]i.

---

## [AI] H[?][?]NG D[?]N X[?] L[?]
1. **S[?]a l[?]i ch[?]nh t[?], ng[?] ph[?]p, v[?] d[?]u c[?]u**.  
   - Th[?]m c[?]c d[?]u [?].[?], [?],[?], [?]?[?], [?]![?] d[?]ng v[?] tr[?].  
   - Lo[?]i b[?] c[?]c l[?]i d[?]nh t[?], n[?]i l[?]p, ho[?]c ti[?]ng d[?]m ([?][?][?], [?][?][?], [?][?][?], [?]nha[?], [?]ha[?]) n[?]u kh[?]ng quan tr[?]ng ng[?] ngh[?]a.
2. **Hi[?]u ng[?] c[?]nh d[?] t[?]i c[?]u tr[?]c c[?]u t[?] nhi[?]n.**  
   - N[?]u ng[?][?]i n[?]i dang h[?]i [?] th[?]m ng[?] di[?]u h[?]i.  
   - N[?]u dang than phi[?]n [?] gi[?] c[?]m x[?]c t[?] nhi[?]n ([?]tr[?]i [?]i[?], [?]thi[?]t l[?][?], [?]m[?]t gh[?][?]).  
   - N[?]u l[?] h[?]i tho[?]i [?] chia vai [?]Ng[?][?]i 1[?], [?]Ng[?][?]i 2[?] (ho[?]c [?]Nh[?]n vi[?]n[?], [?]Kh[?]ch h[?]ng[?]) h[?]p l[?].
3. **T[?] d[?]ng nh[?]n di[?]n v[?] chuy[?]n d[?]i ti[?]ng d[?]a ph[?][?]ng v[?] ti[?]ng Vi[?]t chu[?]n**:
   - [?]r[?]ng r[?]a[?] [?] [?]sao v[?]y[?], [?]m[?][?] [?] [?]d[?]u[?], [?]choa[?] [?] [?]ch[?]ng t[?]i[?], [?]tau[?] [?] [?]t[?]i[?], [?]mi[?] [?] [?]b[?]n[?], [?]n[?][?] [?] [?]kh[?]ng[?], [?]chi[?] [?] [?]g[?][?], [?]h[?]n[?] [?] [?]n[?][?].
   - [?]h[?] / h[?]y / h[?][?] [?] b[?] ho[?]c thay b[?]ng h[?]t c[?]m x[?]c t[?][?]ng d[?][?]ng ([?]nh[?][?], [?]ha[?], [?]d[?]y[?]).  
   - Gi[?] l[?]i m[?]u gi[?]ng t[?] nhi[?]n khi ph[?] h[?]p (v[?] d[?] [?]tr[?]i [?]i[?], [?]bi[?]t r[?]ng ch[?][?] [?] [?]tr[?]i [?]i, bi[?]t l[?]m sao b[?]y gi[?][?]).
4. **Gi[?] nguy[?]n [?] ngh[?]a, kh[?]ng th[?]m ho[?]c b[?]t th[?]ng tin.**  
   - Kh[?]ng t[?]m t[?]t.  
   - Kh[?]ng d[?]ch sang ng[?]n ng[?] kh[?]c.  
   - Kh[?]ng b[?]nh lu[?]n.
5. **Chia do[?]n h[?]p l[?] d[?] d[?] d[?]c.**
   - M[?]i do[?]n 1[?]4 c[?]u.  
   - M[?]i ng[?][?]i n[?]i l[?] 1 do[?]n ri[?]ng (n[?]u nh[?]n di[?]n d[?][?]c vai tr[?]).
6. **Hi[?]u ng[?] c[?]nh r[?]ng:**  
   - N[?]u th[?]y ph[?]n d[?]i tho[?]i li[?]n quan d[?]n giao ti[?]p kh[?]ch h[?]ng, g[?]i di[?]n, hay ph[?]ng v[?]n [?] d[?]ng gi[?]ng n[?]i t[?] nhi[?]n, l[?]ch s[?].
   - N[?]u l[?] h[?]i tho[?]i th[?]n m[?]t [?] d[?]ng gi[?]ng d[?]n d[?], g[?]n g[?]i.
   - N[?]u l[?] b[?]n t[?][?]ng thu[?]t [?] d[?]ng gi[?]ng trung l[?]p, m[?]ch l[?]c.

---

## [?][?] D[?] LI[?]U G[?]C
Transcript c[?] th[?] ch[?]a:
- ti[?]ng d[?]a ph[?][?]ng (Ngh[?] An, H[?] T[?]nh, Qu[?]ng Nam, Qu[?]ng Ng[?]i[?])
- c[?]u n[?]i c[?]t, l[?]p, sai ch[?]nh t[?]
- thi[?]u d[?]u, thi[?]u kho[?]ng tr[?]ng
- nh[?]m t[?] (v[?] d[?]: [?]choa[?] [?] [?]ch[?]ng t[?]i[?], [?]r[?]ng[?] [?] [?]sao[?], [?]m[?][?] [?] [?]d[?]u[?])

### [?] TRANSCRIPT G[?]C:
{full_raw_text}

---

## [?] Y[?]U C[?]U [?][?]U RA
- Tr[?] v[?] **ch[?] transcript d[?] d[?][?]c l[?]m s[?]ch v[?] t[?]i c[?]u tr[?]c d[?]p.**
- **Kh[?]ng th[?]m gi[?]i th[?]ch ho[?]c b[?]nh lu[?]n.**
- **Kh[?]ng ghi ti[?]u d[?].**
- **Gi[?] nguy[?]n ng[?]n ng[?] l[?] ti[?]ng Vi[?]t.**

---

## [IDEA] V[?] D[?] M[?]U
### [?][?]u v[?]o:
> "r[?]ng mi ch[?]a [?]n chi, tau n[?]i r[?]i m[?] bi[?]t m[?] h[?]n di m[?] r[?]i"

### [?][?]u ra mong mu[?]n:
> [?]Sao m[?]y ch[?]a [?]n g[?]? Tao n[?]i r[?]i m[?], c[?] bi[?]t n[?] di d[?]u r[?]i kh[?]ng?[?]

---

## [?] G[?]I [?] B[?] SUNG (n[?]u c[?]n):
- N[?]u th[?]y gi[?]ng Ngh[?] - T[?]nh, [?]u ti[?]n hi[?]u: [?]r[?]ng, m[?], chi, n[?], h[?]n, mi, tau, choa[?].
- N[?]u th[?]y gi[?]ng Qu[?]ng, hi[?]u: [?]r[?]a, h[?], m[?]n chi, di m[?][?].
- N[?]u th[?]y gi[?]ng Nam, hi[?]u: [?]v[?]y, dz[?]y, hong, h[?]ng, b[?], [?]ng[?].
- N[?]u th[?]y gi[?]ng B[?]c, gi[?] nguy[?]n t[?] x[?]ng h[?] ph[?] th[?]ng: [?]t[?], c[?]u, anh, ch[?][?].

---

[?] K[?]t qu[?] cu[?]i c[?]ng ph[?]i l[?] transcript **t[?] nhi[?]n, d[?] d[?]c, d[?]ng ti[?]ng Vi[?]t, ph[?]n [?]nh d[?]ng c[?]m x[?]c v[?] [?] ngh[?]a c[?]a ng[?][?]i n[?]i.**
"""

    try:
        response = model.generate_content(prompt)
        cleaned_text = response.text.strip()
        gemini_time = time.time() - gemini_start

        print("\n" + "=" * 60)
        print("Gemini result:")
        print("=" * 60)
        print(cleaned_text)
        print(f"\n[OK] Gemini processing completed in {gemini_time:.2f}s")

        # L[?]u k[?]t qu[?] v[?]o c[?]c th[?] m[?]c ri[?]ng bi[?]t
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = os.path.splitext(os.path.basename(AUDIO_PATH))[0]

        # File raw transcript
        raw_output_file = f"./result/raw/raw_transcript_{file_name}_{timestamp}.txt"
        with open(raw_output_file, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("RAW TRANSCRIPT (Whisper)\n")
            f.write("=" * 60 + "\n")
            f.write(f"Original file: {AUDIO_PATH}\n")
            f.write(f"Processed file: {cleaned_path}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("=" * 60 + "\n\n")

            for seg in raw_transcript:
                f.write(f"[{seg['start']:.2f}s -> {seg['end']:.2f}s]: {seg['text']}\n")

            f.write("\n" + "=" * 60 + "\n")
            f.write("RAW TEXT (FULL)\n")
            f.write("=" * 60 + "\n\n")
            f.write(full_raw_text)

        # File cleaned transcript
        gemini_output_file = (
            f"./result/gemini/cleaned_transcript_{file_name}_{timestamp}.txt"
        )
        with open(gemini_output_file, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("CLEANED TRANSCRIPT (Gemini AI)\n")
            f.write("=" * 60 + "\n")
            f.write(f"Original file: {AUDIO_PATH}\n")
            f.write(f"Processed file: {cleaned_path}\n")
            f.write(f"Timestamp: {timestamp}\n")
            f.write("=" * 60 + "\n\n")
            f.write(cleaned_text)

        # File t[?]ng h[?]p (legacy)
        combined_output_file = f"transcript_combined_{file_name}_{timestamp}.txt"
        with open(combined_output_file, "w", encoding="utf-8") as f:
            f.write("=" * 60 + "\n")
            f.write("ORIGINAL AUDIO FILE\n")
            f.write("=" * 60 + "\n")
            f.write(f"Input: {AUDIO_PATH}\n")
            f.write(f"Processed: {cleaned_path}\n\n")

            f.write("=" * 60 + "\n")
            f.write("RAW TRANSCRIPT (Whisper)\n")
            f.write("=" * 60 + "\n\n")

            for seg in raw_transcript:
                f.write(f"[{seg['start']:.2f}s -> {seg['end']:.2f}s]: {seg['text']}\n")

            f.write("\n" + "=" * 60 + "\n")
            f.write("CLEANED TRANSCRIPT (Gemini AI)\n")
            f.write("=" * 60 + "\n\n")
            f.write(cleaned_text)

        total_time = time.time() - total_start_time
        
        print(f"\n\n[OK] FILES SAVED:")
        print(f"   [FILE] Raw transcript:     {raw_output_file}")
        print(f"   [?] Cleaned transcript: {gemini_output_file}")
        print(f"   [?] Combined report:    {combined_output_file}")
        if cleaned_path != AUDIO_PATH:
            print(f"   [MUSIC] Processed audio:    {cleaned_path}")
        
        print("\n" + "=" * 60)
        print("TH[?]I GIAN TH[?]C HI[?]N:")
        print("=" * 60)
        print(f"  [?] Audio processing:    {preprocessing_time:>8.2f}s")
        print(f"  [?] Load model:          {load_time:>8.2f}s")
        print(f"  [?] Transcription:       {transcribe_time:>8.2f}s")
        print(f"  [?] Gemini AI:           {gemini_time:>8.2f}s")
        print(f"  [?] T[?]NG:                {total_time:>8.2f}s")
        print("=" * 60)

        # D[?]n d[?]p file processed (optional)
        if cleaned_path != AUDIO_PATH and os.path.exists(cleaned_path):
            print(f"\n[TRASH]  Cleaning up processed file: {cleaned_path}")
            try:
                os.remove(cleaned_path)
                print("[OK] Temporary file removed")
            except:
                print("[WARN]  Could not remove temporary file")

    except Exception as e:
        print(f"\n[?] Gemini API Error: {e}")
        print("\nKi[?]m tra:")
        print("1. API key c[?] d[?]ng kh[?]ng?")
        print("2. [?][?] b[?]t Gemini API ch[?]a?")
        print("3. C[?] k[?]t n[?]i internet kh[?]ng?")

except ImportError as e:
    print(f"\n[?] Import Error: {e}")
    print("\nInstall required packages:")
    print("  pip install faster-whisper google-generativeai python-dotenv")
    print("  pip install scipy librosa soundfile  # For audio preprocessing")

except Exception as e:
    print(f"\n[?] Error: {e}")
    import traceback

    traceback.print_exc()
