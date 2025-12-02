# CUDA Setup Guide for Image Upscaling

## 🎯 Quick Start

Run GPU detection script to check your setup:
```bash
python gpu_info.py
```

## 📋 Prerequisites

### 1. Check GPU Compatibility

**Supported GPUs:**
- NVIDIA GPUs with CUDA Compute Capability >= 3.5
- Recommended: RTX 20xx, RTX 30xx, RTX 40xx series
- Minimum: GTX 1050 or better

**Check your GPU:**
```bash
nvidia-smi
```

### 2. Install NVIDIA Drivers

- **Windows**: Download from [NVIDIA Driver Downloads](https://www.nvidia.com/Download/index.aspx)
- **Minimum version**: 472.12+ (for CUDA 11.8)
- **Recommended**: Latest Game Ready or Studio Driver

## 🚀 CUDA PyTorch Installation

### Option 1: CUDA 11.8 (Recommended - Best compatibility)

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
```

### Option 2: CUDA 12.1 (Latest - For RTX 40xx)

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
```

### Option 3: CPU Only (No GPU)

```bash
pip install torch torchvision
```

## ✅ Verify Installation

### 1. Check PyTorch CUDA

```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
print(f"CUDA version: {torch.version.cuda}")
print(f"GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'None'}")
```

### 2. Run GPU Info Script

```bash
cd upscale_tool
python gpu_info.py
```

Expected output:
```
✓ PyTorch installed: 2.x.x
✓ CUDA available: 11.8
✓ cuDNN version: 8xxx

GPU 0: NVIDIA GeForce RTX 3060
  Compute Capability: 8.6
  Total Memory: 12.00 GB
  Memory Free: 11.50 GB
  FP16 Support: Yes
  TF32 Support: Yes (Ampere)
```

## ⚙️ Optimal Settings by GPU

### RTX 4090 / RTX 4080 (24GB / 16GB)
```yaml
device: cuda
tile_size: 2048
half_precision: true
cudnn_benchmark: true
tf32_matmul: true
```

### RTX 3090 / RTX 3080 (24GB / 10GB)
```yaml
device: cuda
tile_size: 1024
half_precision: true
cudnn_benchmark: true
tf32_matmul: true
```

### RTX 3060 / RTX 2060 (12GB / 6GB)
```yaml
device: cuda
tile_size: 768  # or 512 for 6GB
half_precision: true
cudnn_benchmark: true
```

### GTX 1660 / GTX 1650 (6GB / 4GB)
```yaml
device: cuda
tile_size: 384
half_precision: false  # Older architecture
cudnn_benchmark: true
```

### Integrated/Low VRAM (<4GB)
```yaml
device: cuda
tile_size: 256
half_precision: false
auto_tile_size: true
clear_cache: true
```

## 🐛 Troubleshooting

### Issue: "CUDA not available"

**Solutions:**
1. Check NVIDIA driver installation:
   ```bash
   nvidia-smi
   ```

2. Reinstall PyTorch with CUDA:
   ```bash
   pip uninstall torch torchvision
   pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
   ```

3. Verify CUDA toolkit (optional, PyTorch includes it):
   ```bash
   nvcc --version
   ```

### Issue: "Out of Memory (OOM)"

**Solutions:**
1. Reduce tile_size in config:
   ```yaml
   tile_size: 256  # Try smaller values
   ```

2. Enable auto tile size:
   ```yaml
   auto_tile_size: true
   ```

3. Use CPU mode:
   ```yaml
   device: cpu
   ```

4. Close other GPU applications (games, browsers, etc.)

### Issue: "Slow performance on GPU"

**Solutions:**
1. Enable FP16 (if supported):
   ```yaml
   half_precision: true
   ```

2. Enable cuDNN benchmark:
   ```yaml
   cudnn_benchmark: true
   ```

3. Check GPU usage:
   ```bash
   nvidia-smi -l 1  # Monitor every second
   ```

4. Increase tile size (if memory allows):
   ```yaml
   tile_size: 768  # Larger = faster
   ```

### Issue: "RuntimeError: CUDA error: device-side assert triggered"

**Solutions:**
1. Update NVIDIA drivers
2. Reinstall PyTorch
3. Try different CUDA version

## 🎯 Performance Benchmarks

Expected performance on 1920x1080 image → 4K (4x upscale):

| GPU | FP32 | FP16 | Speedup |
|-----|------|------|---------|
| RTX 4090 | 2.5s | 1.2s | 2.1x |
| RTX 3090 | 4.0s | 2.0s | 2.0x |
| RTX 3060 | 8.0s | 4.5s | 1.8x |
| RTX 2060 | 12.0s | 7.0s | 1.7x |
| GTX 1660 | 18.0s | N/A | - |
| CPU (i7) | 180.0s | N/A | - |

*Benchmark with RealESRGAN_x4plus model*

## 📊 Run Your Own Benchmark

```bash
cd upscale_tool
python gpu_info.py
# Choose 'y' when asked to run benchmark
```

Or in Python:
```python
from upscale_tool.utils import benchmark_gpu

results = benchmark_gpu(test_size=(512, 512))
print(f"FP32: {results['fp32_time']:.2f}s")
print(f"FP16: {results['fp16_time']:.2f}s")
print(f"Speedup: {results['speedup']:.2f}x")
```

## 🔧 Advanced Configuration

### Multi-GPU Setup

```yaml
# Use specific GPU
device: cuda:0  # First GPU
# or
device: cuda:1  # Second GPU

gpu_id: 0  # Or 1, 2, etc.
```

### Memory Optimization

```yaml
# Auto-adjust settings based on available memory
auto_tile_size: true
clear_cache: true

# Manual fine-tuning
tile_size: 512
tile_pad: 10
pre_pad: 0
```

### Maximum Performance

```yaml
device: cuda
half_precision: true
cudnn_benchmark: true
tf32_matmul: true  # RTX 30xx+ only
tile_size: 1024    # Adjust for your GPU
auto_tile_size: false
clear_cache: false
```

## 📚 Additional Resources

- [PyTorch CUDA Installation](https://pytorch.org/get-started/locally/)
- [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-toolkit)
- [Real-ESRGAN GitHub](https://github.com/xinntao/Real-ESRGAN)
- [cuDNN Installation](https://developer.nvidia.com/cudnn)

## 💡 Tips

1. **Always run `gpu_info.py` first** to check your setup
2. **Start with auto settings** (`device: auto`, `auto_tile_size: true`)
3. **Enable FP16** for RTX 20xx and newer GPUs
4. **Monitor GPU memory** with `nvidia-smi -l 1` during processing
5. **Update drivers regularly** for best performance
6. **Close other GPU apps** before upscaling large batches

## ❓ Need Help?

1. Run diagnostics:
   ```bash
   python gpu_info.py
   ```

2. Check logs for errors
3. Try CPU mode first to verify model works
4. Report issues with GPU info and error logs
