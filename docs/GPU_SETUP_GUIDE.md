# GPU Setup Guide - AI Assistant

## 🎯 Quick Start

### Option 1: Automatic Setup (Recommended)
```bash
# Run this - it will auto-detect GPU and install correct PyTorch
scripts\setup-venv.bat
```

### Option 2: Check Your GPU First
```bash
# Check if you have NVIDIA GPU and CUDA support
scripts\check-gpu.bat
```

---

## 🔍 What the Scripts Do

### GPU Detection Flow:
1. **Check nvidia-smi** → Detect NVIDIA GPU
2. **Check CUDA version** → Verify CUDA toolkit
3. **Install PyTorch**:
   - GPU found → Install PyTorch 2.6.0 with CUDA 11.8
   - No GPU → Install CPU-only PyTorch

---

## ✅ Expected Results

### With NVIDIA GPU:
```
[OK] NVIDIA GPU detected
[OK] CUDA 11.8 detected (or compatible)
[SUCCESS] PyTorch with CUDA 11.8 installed successfully!
[INFO] GPU acceleration enabled for:
  - Stable Diffusion (10-20x faster)
  - Image Upscale (5-10x faster)
  - LoRA Training (required)
  - Speech2Text (3-5x faster)
```

### Without GPU:
```
[INFO] No NVIDIA GPU detected
[INFO] Will install CPU-only PyTorch
[WARNING] Installed CPU-only PyTorch (no GPU acceleration)
```

---

## 🐛 Troubleshooting

### Problem: GPU detected but PyTorch has no CUDA
**Solution:**
```bash
# Uninstall old PyTorch
pip uninstall torch torchvision torchaudio -y

# Install CUDA version
pip install torch==2.6.0 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
```

### Problem: nvidia-smi not found
**Possible causes:**
1. No NVIDIA GPU in system
2. GPU drivers not installed
3. GPU disabled in BIOS

**Solution:**
- Update NVIDIA drivers from: https://www.nvidia.com/Download/index.aspx
- Or accept CPU-only installation

### Problem: CUDA version mismatch
**Check CUDA version:**
```bash
nvcc --version
```

**Install CUDA 11.8:**
https://developer.nvidia.com/cuda-11-8-0-download-archive

---

## 📊 Performance Comparison

| Service | GPU (CUDA) | CPU Only |
|---------|-----------|----------|
| **Stable Diffusion** | 5-10 sec | 3-5 min |
| **Image Upscale** | 2-5 sec | 30-60 sec |
| **LoRA Training** | ✓ Possible | ✗ Too slow |
| **Speech2Text** | Real-time | 3-5x slower |
| **ChatBot** | Same | Same |
| **Text2SQL** | Same | Same |

---

## 🎓 Manual Installation (Advanced)

### If you want to install manually:

1. **Create virtual environment:**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate
   ```

2. **Install PyTorch with GPU:**
   ```bash
   pip install torch==2.6.0 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
   ```

3. **Verify GPU support:**
   ```bash
   python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
   ```

4. **Install other dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## 📝 Notes

- **CUDA 11.8** is recommended (compatible with most GPUs)
- **Minimum 6GB VRAM** for Stable Diffusion
- **8GB+ VRAM** recommended for LoRA Training
- CPU-only mode works but is **much slower** for image/video tasks

---

## 🚀 Next Steps

After GPU setup:
1. Configure `.env` files with API keys
2. Run `scripts\start-all.bat` to start all services
3. Access Hub Gateway at http://localhost:3000

For more help, see [docs/GETTING_STARTED.md](../docs/GETTING_STARTED.md)
