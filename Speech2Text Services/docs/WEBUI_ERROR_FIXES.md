# WEBUI ERROR FIXES - VistralS2T
> Comprehensive guide to fix all Web UI runtime errors

**Date:** October 27, 2025  
**Version:** 3.6.0+  
**Branch:** VistralS2T

---

## 🔍 ERRORS IDENTIFIED

From the log output, three critical errors were detected:

### 1️⃣ **TorchCodec FFmpeg Loading Error**
```
Could not load libtorchcodec. Likely causes:
1. FFmpeg is not properly installed in your environment. We support versions 4, 5, 6 and 7.
2. The PyTorch version (2.9.0+cpu) is not compatible with this version of TorchCodec.
```

**Impact:** PhoWhisper transcription skipped entirely  
**Status:** ❌ Critical - Vietnamese ASR not working

---

### 2️⃣ **HuggingFace Token Missing**
```
[PROGRESS] diarization: 40% - Diarization failed, using full audio: 
HuggingFace token required for pyannote models. Set HF_TOKEN in .env or pass hf_token parameter
```

**Impact:** Speaker diarization disabled, all audio treated as single speaker  
**Status:** ⚠️ Important - Reduces accuracy for multi-speaker audio

---

### 3️⃣ **Accelerate Package Missing**
```
[PROGRESS] qwen: 98% - Qwen skipped: Using a `device_map`, `tp_plan`, `torch.device` 
context manager or setting `torch.set_default_device(device)` requires `accelerate`. 
You can install it with `pip install accelerate`
```

**Impact:** Qwen enhancement skipped, only Whisper output returned  
**Status:** ⚠️ Important - Missing smart fusion and role detection

---

## ✅ COMPLETE FIX GUIDE

### **Step 1: Configure HuggingFace Token**

#### 1.1 Get Your Token
1. Go to: https://huggingface.co/settings/tokens
2. Create a new token (or use existing)
3. Copy the token (starts with `hf_...`)

#### 1.2 Accept Model License
Visit and accept the license:
- https://huggingface.co/pyannote/speaker-diarization-3.1
- Click "Agree and access repository"

#### 1.3 Configure .env File
Edit `d:\WORK\s2t\.env`:

```env
# Replace with your actual token
HF_TOKEN=hf_your_actual_token_here

# Keep existing Gemini key
GEMINI_API_KEY=AIzaSyCbaNe3w8VW7aKXGKBzN9JgpjKrYRsed-c
```

**Verification:**
```powershell
# Check .env file
type .env | findstr HF_TOKEN
```

---

### **Step 2: Install FFmpeg for TorchCodec**

#### Option A: Automated Installation (Recommended)
```powershell
cd d:\WORK\s2t
.\app\s2t\Scripts\activate
.\scripts\install_ffmpeg.bat
```

The script will:
- Install Chocolatey (if needed)
- Install FFmpeg automatically
- Verify installation
- Install torchcodec package

#### Option B: Manual Installation

1. **Download FFmpeg:**
   - Visit: https://www.gyan.dev/ffmpeg/builds/
   - Download: `ffmpeg-release-full.7z`

2. **Extract and Install:**
   ```powershell
   # Extract to C:\ffmpeg
   # Should have: C:\ffmpeg\bin\ffmpeg.exe
   ```

3. **Add to PATH:**
   - Open: System Properties → Environment Variables
   - Edit `PATH` variable
   - Add: `C:\ffmpeg\bin`
   - Click OK

4. **Verify Installation:**
   ```powershell
   # Restart PowerShell, then:
   ffmpeg -version
   ```

5. **Install TorchCodec:**
   ```powershell
   cd d:\WORK\s2t
   .\app\s2t\Scripts\activate
   pip install torchcodec>=0.1.0
   ```

---

### **Step 3: Fix Accelerate Package**

The `accelerate` package is already in `requirements.txt` but may not be installed:

```powershell
cd d:\WORK\s2t
.\app\s2t\Scripts\activate
pip install accelerate>=0.27.0
```

**Verify Installation:**
```powershell
python -c "import accelerate; print('Accelerate version:', accelerate.__version__)"
```

---

### **Step 4: Complete Dependency Reinstall**

To ensure all packages are properly installed:

```powershell
cd d:\WORK\s2t
.\app\s2t\Scripts\activate

# Upgrade pip first
python -m pip install --upgrade pip

# Reinstall all dependencies
pip install -r requirements.txt --upgrade
```

---

## 🧪 VERIFICATION TESTS

### Test 1: Check All Imports
```powershell
cd d:\WORK\s2t
.\app\s2t\Scripts\activate

python -c "import torchcodec; print('✓ TorchCodec OK')"
python -c "import accelerate; print('✓ Accelerate OK')"
python -c "import pyannote.audio; print('✓ Pyannote OK')"
python -c "from transformers import AutoModelForSpeechSeq2Seq; print('✓ PhoWhisper OK')"
```

### Test 2: Check FFmpeg
```powershell
ffmpeg -version
# Should show: ffmpeg version 4.x, 5.x, 6.x, or 7.x
```

### Test 3: Check Environment Variables
```powershell
type .env | findstr HF_TOKEN
# Should show: HF_TOKEN=hf_xxxxxx (not empty)
```

### Test 4: Run Web UI
```powershell
cd d:\WORK\s2t
.\start_webui.bat
```

Upload a test audio file and check for:
- ✅ No TorchCodec errors
- ✅ Diarization working (if multi-speaker audio)
- ✅ PhoWhisper transcription completed
- ✅ Qwen enhancement completed
- ✅ Three-role speaker labels (if applicable)

---

## 📊 EXPECTED LOG OUTPUT (After Fixes)

```
[PROGRESS] diarization: 20% - Loading diarization model...
[DIARIZATION] Initialized with model: pyannote/speaker-diarization-3.1
[DIARIZATION] Device: cpu
[DIARIZATION] Speaker range: 2-5
[DIARIZATION] Processing audio... ✅ (No error!)

[PROGRESS] phowhisper: 78% - Loading PhoWhisper model...
[PhoWhisper] Loading vinai/PhoWhisper-large on cpu...
[PhoWhisper] GPU acceleration enabled
[PhoWhisper] Loaded in 8.83s
[PhoWhisper] Transcribing: segment_000_SPEAKER_00.wav
[PhoWhisper] Audio duration: 250.3s
[PhoWhisper] Processing 9 chunks (30s each)
[PhoWhisper] Completed in 156.42s ✅ (No torchcodec error!)

[PROGRESS] qwen: 92% - Loading Qwen model for enhancement...
[Qwen] Loading Qwen/Qwen2.5-1.5B-Instruct...
[Qwen] Loaded in 12.34s
[Qwen] Enhancing transcript...
[Qwen] Enhancement complete ✅ (No accelerate error!)
```

---

## 🔧 TROUBLESHOOTING

### Issue: FFmpeg still not found after installation
**Solution:**
1. Restart PowerShell/Terminal
2. Check PATH: `echo $env:PATH`
3. Verify FFmpeg location: `where.exe ffmpeg`
4. If not in PATH, add manually via System Properties

---

### Issue: TorchCodec still fails after FFmpeg install
**Solution:**
```powershell
# Reinstall torchcodec with --force
pip uninstall torchcodec -y
pip install torchcodec>=0.1.0 --no-cache-dir
```

---

### Issue: Diarization still fails with "HuggingFace token required"
**Solution:**
1. Check `.env` file exists in `d:\WORK\s2t\`
2. Verify token format: `HF_TOKEN=hf_xxxxxx` (no quotes, no spaces)
3. Restart Web UI completely (Ctrl+C, then `.\start_webui.bat`)
4. Check license acceptance at: https://huggingface.co/pyannote/speaker-diarization-3.1

---

### Issue: Accelerate import still fails
**Solution:**
```powershell
# Check Python version (must be 3.10.x)
python --version

# Reinstall accelerate
pip uninstall accelerate -y
pip install accelerate>=0.27.0

# Verify
python -c "import accelerate; print(accelerate.__version__)"
```

---

## 📝 QUICK FIX CHECKLIST

Before starting Web UI, verify:

- [ ] `.env` file exists with valid `HF_TOKEN`
- [ ] FFmpeg installed and in PATH (`ffmpeg -version` works)
- [ ] TorchCodec installed (`python -c "import torchcodec"` works)
- [ ] Accelerate installed (`python -c "import accelerate"` works)
- [ ] Virtual environment activated (`.\app\s2t\Scripts\activate`)
- [ ] All requirements installed (`pip install -r requirements.txt`)

---

## 🚀 POST-FIX VALIDATION

After completing all fixes, run a full transcription test:

1. Start Web UI: `.\start_webui.bat`
2. Upload multi-speaker audio file
3. Verify in logs:
   - ✅ Diarization completes without token error
   - ✅ PhoWhisper completes without torchcodec error
   - ✅ Qwen enhancement completes without accelerate error
4. Check output has proper speaker roles:
   - **Hệ thống:** (System messages)
   - **Nhân viên:** (Staff messages)
   - **Khách hàng:** (Customer messages)

---

## 📚 RELATED DOCUMENTATION

- **FFmpeg Installation:** `scripts\install_ffmpeg.bat`
- **Environment Setup:** `.env.example`
- **Dependencies:** `requirements.txt`
- **Web UI Guide:** `docs\WEB_UI_ENHANCEMENTS.md`
- **Deployment:** `docker\README.md`

---

## 🆘 SUPPORT

If issues persist after following this guide:

1. Check logs in `logs\` directory
2. Run diagnostic: `python tools\check.py`
3. Report issue at: https://github.com/SkastVnT/Speech2Text/issues
4. Include:
   - Full error log
   - Python version (`python --version`)
   - Pip list output (`pip list > packages.txt`)
   - Environment details (Windows version, CUDA version if GPU)

---

**Last Updated:** October 27, 2025  
**Tested On:** Windows 10/11, Python 3.10.6
