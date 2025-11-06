# 🚀 FINAL SETUP INSTRUCTIONS

**Date:** October 27, 2025  
**Status:** ✅ Web UI Running | ⚠️ 2 Issues Remain

---

## ✅ WHAT'S WORKING

- ✅ **Web UI:** Running successfully on http://localhost:5000
- ✅ **Whisper:** Transcription working (275.98s for 250.3s audio)
- ✅ **PhoWhisper:** Model loaded (with fallback for torchcodec)
- ✅ **Dependencies:** All core packages installed

---

## ⚠️ REMAINING ISSUES

### **Issue 1: HuggingFace Token Not Accepted**

**Error:**
```
403 Client Error - Access to model pyannote/speaker-diarization-3.1 is restricted
```

**Your Token:** `hf_api_token` ✅ (Found in .env)

**Solution:**
1. Visit: https://huggingface.co/pyannote/speaker-diarization-3.1
2. Click **"Agree and access repository"** button
3. Accept the terms of use
4. Restart Web UI: `.\start_webui.bat`

**Status:** Token is valid but license not accepted yet

---

### **Issue 2: Qwen Enhancement Skipped**

**Error:**
```
Qwen skipped: Using a `device_map` requires `accelerate`. 
You can install it with `pip install accelerate`
```

**Reality:** Accelerate IS installed (`0.27.2`) ✅

**Root Cause:** Qwen code uses `device_map="auto"` which requires accelerate import, but there's a detection bug.

**Quick Fix:**

Edit `d:\WORK\s2t\app\core\llm\qwen_client.py`:

```python
# Line 73-76, change:
if torch.cuda.is_available():
    self.model = AutoModelForCausalLM.from_pretrained(
        self.model_name,
        torch_dtype=self.torch_dtype,
        device_map="auto",  # ← Remove this line
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )

# To:
if torch.cuda.is_available():
    self.model = AutoModelForCausalLM.from_pretrained(
        self.model_name,
        torch_dtype=self.torch_dtype,
        # device_map="auto",  # ← Commented out
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    ).to("cuda")  # ← Add .to("cuda") instead
```

Or simpler fix - just remove `device_map` since you're on CPU:

```python
# Line 81-86, change:
else:
    self.model = AutoModelForCausalLM.from_pretrained(
        self.model_name,
        device_map="cpu",  # ← This causes the issue
        trust_remote_code=True,
    )

# To:
else:
    self.model = AutoModelForCausalLM.from_pretrained(
        self.model_name,
        # device_map removed
        trust_remote_code=True,
    )
```

---

### **Issue 3: TorchCodec Warning (Non-Critical)**

**Error:**
```
Could not load libtorchcodec - FFmpeg not properly installed
```

**Impact:** PhoWhisper uses fallback audio loading (still works)

**Optional Fix:**
```powershell
.\scripts\install_ffmpeg.bat
```

**Status:** Can ignore - system works fine without it

---

## 🎯 IMMEDIATE ACTIONS

### **Priority 1: Accept HF License** (Required for diarization)
1. Go to: https://huggingface.co/pyannote/speaker-diarization-3.1
2. Click "Agree and access repository"
3. Done!

### **Priority 2: Fix Qwen Code** (For smart fusion)

Option A - Quick CLI fix:
```powershell
# Edit qwen_client.py line 85
code d:\WORK\s2t\app\core\llm\qwen_client.py
# Remove 'device_map="cpu",' from line 85
```

Option B - Let me fix it for you (reply "fix qwen")

### **Priority 3: Optional FFmpeg** (For PhoWhisper optimization)
```powershell
.\scripts\install_ffmpeg.bat
```

---

## ✅ VERIFICATION AFTER FIXES

1. **Test HF Token:**
   ```powershell
   python -c "from pyannote.audio import Pipeline; p = Pipeline.from_pretrained('pyannote/speaker-diarization-3.1', token=''); print('✅ Token works!')"
   ```

2. **Test Qwen:**
   ```powershell
   python -c "from transformers import AutoModelForCausalLM; m = AutoModelForCausalLM.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct', trust_remote_code=True); print('✅ Qwen loads!')"
   ```

3. **Restart Web UI:**
   ```powershell
   .\start_webui.bat
   ```

4. **Upload test audio** and check logs for:
   - ✅ Diarization completed (no 403 error)
   - ✅ Qwen enhancement completed (no accelerate error)
   - ✅ All 3 stages finish successfully

---

## 📊 EXPECTED FINAL LOG OUTPUT

```
[PROGRESS] diarization: 20% - Loading diarization model...
[DIARIZATION] Initialized with model: pyannote/speaker-diarization-3.1
[DIARIZATION] Loading pyannote/speaker-diarization-3.1...
[OK] Diarization pipeline loaded in 8.5s  ✅ (No 403 error!)
[PROGRESS] diarization: 40% - Detected 2 speakers, 15 segments

[PROGRESS] whisper: 55% - Loading Whisper model...
[Whisper] Transcribing: segment_000_SPEAKER_00.wav
[Whisper] Completed in 145.23s (1204 chars)  ✅

[PROGRESS] phowhisper: 78% - Loading PhoWhisper model...
[PhoWhisper] Transcribing: segment_000_SPEAKER_00.wav
[PhoWhisper] Completed in 89.45s (1187 chars)  ✅

[PROGRESS] qwen: 92% - Loading Qwen model for enhancement...
[Qwen] Loading Qwen/Qwen2.5-1.5B-Instruct...
[Qwen] Loaded in 12.34s  ✅ (No accelerate error!)
[Qwen] Enhancing transcript...
[Qwen] Enhancement complete  ✅

[PROGRESS] complete: 100% - Processing complete!
```

---

## 🆘 NEED HELP?

**Option 1:** Reply "fix qwen" and I'll update the code

**Option 2:** Manual edit:
```powershell
code d:\WORK\s2t\app\core\llm\qwen_client.py
# Line 85: Remove device_map="cpu",
# Save and restart web UI
```

**Option 3:** Check docs:
- `docs\WEBUI_ERROR_FIXES.md` - Full troubleshooting
- `docs\QUICK_FIX_DEPENDENCIES.md` - Dependency issues

---

**Next Step:** Accept the HuggingFace license → https://huggingface.co/pyannote/speaker-diarization-3.1
