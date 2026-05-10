# ChatBot Troubleshooting Guide

## Fixed Issues (October 29, 2025)

### ✅ NumPy 2.x Compatibility Issue

**Problem:**
```
A module that was compiled using NumPy 1.x cannot be run in NumPy 2.2.6 as it may crash.
```

**Solution:**
- Downgraded NumPy to version 1.26.4 (1.x series)
- Updated `requirements.txt` to pin NumPy: `numpy<2.0`
- This ensures PyTorch (compiled with NumPy 1.x) runs properly

**Command to fix:**
```powershell
cd I:\AI-Assistant\ChatBot
.\venv_chatbot\Scripts\Activate.ps1
pip uninstall numpy -y
pip install "numpy<2.0"
```

### ✅ BloomVN-8B GPU Memory Issue

**Problem:**
```
ERROR: Some modules are dispatched on the CPU or the disk. 
Make sure you have enough GPU RAM to fit the quantized model.
```

**Solution:**
- Updated `local_model_loader.py` to use proper `BitsAndBytesConfig`
- Enabled CPU offloading: `llm_int8_enable_fp32_cpu_offload=True`
- Set memory limits: GPU=6GB, CPU=30GB
- This allows the 8B model to run on GPUs with limited VRAM

**Technical Details:**
- BloomVN-8B requires ~16GB VRAM in FP16
- With 8-bit quantization: ~8GB VRAM
- With CPU offloading: Can run on 6GB VRAM (rest offloaded to RAM)

---

## Other Common Issues

### 🔴 Stable Diffusion Connection Error

**Problem:**
```
Error changing model: HTTPConnectionPool(host='127.0.0.1', port=7860): 
Max retries exceeded with url: /sdapi/v1/options
```

**Solution:**
Stable Diffusion WebUI is not running. Start it first:
```powershell
cd I:\AI-Assistant\stable-diffusion-webui
.\webui-user.bat
```

Or use the startup script:
```powershell
cd I:\AI-Assistant\scripts\startup
.\start_chatbot_with_sd.bat
```

### ⚠️ Python Version Warning

**Warning:**
```
FutureWarning: You are using a Python version (3.10.11) which Google 
will stop supporting in new releases of google.api_core once it reaches 
its end of life (2026-10-04).
```

**Recommendation:**
- Current version (3.10.11) works fine until October 2026
- Consider upgrading to Python 3.11 or 3.12 in the future
- Not urgent, but plan for upgrade before October 2026

---

## System Requirements

### For ChatBot Only
- **Python:** 3.10+ (3.11 recommended for longevity)
- **RAM:** 8GB minimum
- **GPU:** Optional (for local models)
  - NVIDIA GPU with 6GB+ VRAM (for Qwen1.5-1.8B)
  - 8GB+ VRAM recommended (for BloomVN-8B with quantization)

### For ChatBot + Stable Diffusion
- **RAM:** 16GB minimum, 32GB recommended
- **GPU:** NVIDIA GPU with 8GB+ VRAM (12GB+ recommended)
- **Storage:** 50GB+ free space (for models)

### Model VRAM Requirements
| Model | Original | 8-bit Quantized | With CPU Offload |
|-------|----------|-----------------|------------------|
| Qwen1.5-1.8B | 3.6GB | N/A (small) | N/A |
| BloomVN-8B | 16GB | 8GB | 6GB+ |
| Qwen2.5-14B | 28GB | 14GB | 10GB+ |

---

## Quick Fixes

### Re-create Virtual Environment
If issues persist, recreate the virtual environment:
```powershell
cd I:\AI-Assistant\ChatBot
Remove-Item -Recurse -Force venv_chatbot
python -m venv venv_chatbot
.\venv_chatbot\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Clear GPU Memory
If models fail to load, clear GPU cache:
```python
import torch
torch.cuda.empty_cache()
```

### Check GPU Status
```powershell
nvidia-smi
```

---

## Debugging Commands

### Check Python/Package Versions
```powershell
cd I:\AI-Assistant\ChatBot
.\venv_chatbot\Scripts\Activate.ps1
python --version
pip show numpy torch transformers
```

### Test Local Model Loading
```powershell
cd I:\AI-Assistant\ChatBot
.\venv_chatbot\Scripts\Activate.ps1
python test_tools.py
```

### Check Available Models
Navigate to: http://127.0.0.1:5000 after starting the ChatBot
- Click "Local Models Status" in the UI
- Shows which models are detected and loaded

---

## Contact & Support

- **Project:** AI-Assistant ChatBot
- **Repository:** SkastVnT/AI-Assistant
- **Branch:** ChatBotCoding

### Files Modified (Oct 29, 2025)
1. `ChatBot/src/utils/local_model_loader.py` - Fixed quantization config
2. `ChatBot/requirements.txt` - Pinned NumPy version

### Related Scripts
- `scripts/startup/start_chatbot_with_sd.bat` - Start both services
- `scripts/stable-diffusion/fix_dependencies.bat` - Fix SD dependencies
- `ChatBot/setup_venv_chatbot.bat` - Setup ChatBot environment
