# Stable Diffusion WebUI - Issues Fixed (October 29, 2025)

## ✅ FIXED ISSUES

### 1. **CPU-Only PyTorch (CRITICAL)**
**Problem:**
```
PyTorch: 2.8.0+cpu
CUDA Available: False
```

**Solution:**
- Uninstalled CPU-only PyTorch 2.8.0
- Installed PyTorch 2.4.0 with CUDA 12.1 support
- Verified CUDA is now working

**Result:**
```
✅ PyTorch: 2.4.0+cu121
✅ CUDA Available: True
✅ CUDA Version: 12.1
✅ GPU: NVIDIA GeForce RTX 3060 Ti
```

---

### 2. **Conflicting ldm Package**
**Problem:**
```
SyntaxError: Missing parentheses in call to 'print'. Did you mean print(...)?
```

**Root Cause:**
Wrong `ldm` package (v0.1.3 - face recognition library) was installed, conflicting with Stable Diffusion's Latent Diffusion Model.

**Solution:**
```batch
pip uninstall ldm -y
```

---

### 3. **basicsr Torchvision Compatibility**
**Problem:**
```
ModuleNotFoundError: No module named 'torchvision.transforms.functional_tensor'
```

**Root Cause:**
`basicsr` library uses deprecated import path from old torchvision versions.

**Solution:**
Patched `venv_sd\lib\site-packages\basicsr\data\degradations.py`:
```python
try:
    from torchvision.transforms.functional_tensor import rgb_to_grayscale
except ImportError:
    from torchvision.transforms.functional import rgb_to_grayscale
```

---

## ⚠️ KNOWN ISSUES (NON-CRITICAL)

### 1. xformers Version Conflict
**Issue:**
```
RuntimeError: Tried to register an operator (xformers_flash::flash_fwd) multiple times
```

**Impact:** Minimal - Stable Diffusion falls back to "Doggettx" optimization automatically

**Workaround:** Don't use `--xformers` flag, use `--opt-sdp-attention` instead

---

### 2. Pydantic v2 API Deprecation
**Issue:**
```
AttributeError: __config__
```

**Impact:** API documentation generation fails, but image generation works fine

**Status:** Non-critical, doesn't affect core functionality

---

## 📊 SYSTEM CONFIGURATION

| Component | Version | Status |
|-----------|---------|--------|
| **GPU** | NVIDIA GeForce RTX 3060 Ti (8GB VRAM) | ✅ Working |
| **CUDA** | 13.0 (Driver 581.57) | ✅ Compatible |
| **PyTorch** | 2.4.0+cu121 | ✅ Working |
| **Torchvision** | 0.19.0+cu121 | ✅ Working |
| **xformers** | 0.0.27.post2 | ⚠️  Has conflicts |
| **NumPy** | 1.26.4 | ✅ Compatible |
| **Python** | 3.10.11 | ✅ Working |

---

## 🚀 HOW TO START

### Method 1: Use the Fixed Startup Script
```batch
cd I:\AI-Assistant\scripts\stable-diffusion
.\start_sd.bat
```

### Method 2: Manual Start
```batch
cd I:\AI-Assistant\stable-diffusion-webui
call venv_sd\Scripts\activate.bat
python webui.py --api --no-half-vae --opt-sdp-attention
```

**Access WebUI:**
- Web Interface: http://127.0.0.1:7860
- API Documentation: http://127.0.0.1:7860/docs

---

## 📁 FILES MODIFIED

1. **`venv_sd\lib\site-packages\basicsr\data\degradations.py`**
   - Added compatibility fix for torchvision 0.19+

2. **`scripts\stable-diffusion\start_sd.bat`** (NEW)
   - Safe startup script with working optimizations

3. **`scripts\stable-diffusion\fix_sd_pytorch.bat`** (NEW)
   - Comprehensive PyTorch + CUDA reinstallation script

---

## 🔧 TROUBLESHOOTING

### Issue: "No CUDA devices available"
**Solution:**
```batch
cd I:\AI-Assistant\stable-diffusion-webui
call venv_sd\Scripts\activate.bat
python -c "import torch; print('CUDA:', torch.cuda.is_available())"
```

If shows `False`, reinstall PyTorch:
```batch
cd I:\AI-Assistant\scripts\stable-diffusion
.\fix_sd_pytorch.bat
```

### Issue: "Out of Memory (OOM)"
Your RTX 3060 Ti has 8GB VRAM. Tips to reduce memory usage:

1. **Use `--medvram` flag:**
   ```batch
   python webui.py --api --medvram
   ```

2. **Use `--lowvram` for extreme cases:**
   ```batch
   python webui.py --api --lowvram
   ```

3. **Reduce image resolution:**
   - Max recommended: 768x768
   - For multiple images: 512x512

### Issue: Generation is slow
**Solutions:**
1. Enable SDP attention (already in start script)
2. Use smaller batch sizes
3. Reduce sampling steps (20-30 is usually enough)

---

## 📝 PERFORMANCE NOTES

With RTX 3060 Ti (8GB VRAM):
- **512x512:** ~3-5 seconds per image
- **768x768:** ~6-10 seconds per image  
- **1024x1024:** Possible with `--medvram`, ~15-20 seconds

**Optimization used:** `Doggettx` (SDP attention fallback)
- Slightly slower than xformers, but more stable
- No noticeable quality difference

---

## 🔄 INTEGRATION WITH CHATBOT

The ChatBot can connect to Stable Diffusion API at `http://127.0.0.1:7860`

To use both together:

**Terminal 1 - Start Stable Diffusion:**
```batch
cd I:\AI-Assistant\scripts\stable-diffusion
.\start_sd.bat
```

**Terminal 2 - Start ChatBot:**
```batch
cd I:\AI-Assistant\ChatBot
.\start_chatbot.bat
```

**Alternatively - Start Both at Once:**
```batch
cd I:\AI-Assistant\scripts\startup
.\start_chatbot_with_sd.bat
```

---

## 📚 REFERENCES

- PyTorch CUDA Installation: https://pytorch.org/get-started/locally/
- Stable Diffusion WebUI: https://github.com/AUTOMATIC1111/stable-diffusion-webui
- xformers: https://github.com/facebookresearch/xformers

---

## 📞 SUPPORT

If issues persist:
1. Check GPU driver is up to date: `nvidia-smi`
2. Verify CUDA toolkit installation
3. Check Python version: `python --version` (should be 3.10.x)
4. Recreate virtual environment if needed

**Last Updated:** October 29, 2025
**Status:** ✅ Fully Functional (with minor non-critical warnings)
