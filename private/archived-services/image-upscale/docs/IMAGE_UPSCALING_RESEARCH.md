# Tài Liệu Nghiên Cứu: Image Upscaling - Từ Mờ Đến HD

## 📋 Tổng Quan

Tài liệu này tổng hợp kết quả nghiên cứu về công nghệ upscaling hình ảnh, đặc biệt tập trung vào việc tích hợp khả năng nâng cấp chất lượng ảnh từ mờ lên HD cho dự án AI-Assistant.

**Nguồn tham khảo chính:**
- [manga-image-translator](https://github.com/zyddnys/manga-image-translator) - Project đã tích hợp sẵn upscaling
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) - State-of-the-art upscaling model
- [Waifu2x](https://github.com/nihui/waifu2x-ncnn-vulkan) - Model tối ưu cho anime/manga

---

## 🎯 Các Công Nghệ Upscaling Chính

### 1. **Real-ESRGAN** (Recommended cho ảnh tổng quát)

#### 📌 Đặc điểm:
- **Mô tả**: Enhanced Super-Resolution Generative Adversarial Networks
- **Ứng dụng**: Tổng quát cho mọi loại ảnh (ảnh thực, anime, manga, illustration)
- **Tỷ lệ upscale**: 2x, 3x, 4x (có thể scale tùy ý với post-processing)
- **Model size**: ~17MB (RealESRGAN_x4plus), ~16MB (RealESRGAN_x4plus_anime_6B)
- **Paper**: [Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data](https://arxiv.org/abs/2107.10833)

#### ⚡ Các Model Có Sẵn:

| Model | Mục đích | Scale | Đặc điểm |
|-------|----------|-------|----------|
| **RealESRGAN_x4plus** | Ảnh tổng quát | 4x | Model mặc định, tốt cho ảnh thực |
| **RealESRNet_x4plus** | Ảnh tổng quát | 4x | Không có GAN, ít artifacts hơn |
| **RealESRGAN_x4plus_anime_6B** | Anime/Manga | 4x | Tối ưu cho anime, size nhỏ (6 blocks) |
| **RealESRGAN_x2plus** | Ảnh nhỏ hơn | 2x | Cho trường hợp cần scale ít |
| **realesr-general-x4v3** | Tổng quát nhỏ gọn | 4x | Model nhỏ nhất, hỗ trợ -dn (denoise) |

#### 💻 Cài đặt & Sử dụng:

```bash
# Cài đặt
pip install basicsr
pip install facexlib
pip install realesrgan

# Clone repo
git clone https://github.com/xinntao/Real-ESRGAN.git
cd Real-ESRGAN

# Download model
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth -P weights

# Sử dụng
python inference_realesrgan.py -n RealESRGAN_x4plus -i inputs -o outputs --outscale 4
```

#### 🎨 Các Tham Số Quan Trọng:

```python
# Python API
from basicsr.archs.rrdbnet_arch import RRDBNet
from realesrgan import RealESRGANer

model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, num_block=23, num_grow_ch=32, scale=4)
upsampler = RealESRGANer(
    scale=4,
    model_path='weights/RealESRGAN_x4plus.pth',
    model=model,
    tile=0,        # Tile size (0 = auto), dùng cho ảnh lớn
    tile_pad=10,   # Padding cho tile
    pre_pad=0,     # Pre-padding
    half=True      # fp16 để tiết kiệm VRAM
)

output, _ = upsampler.enhance(img, outscale=4)
```

#### 🌐 Demo Online:
- [Official ARC Demo](https://arc.tencent.com/en/ai-demos/imgRestore)
- [Replicate Demo](https://replicate.com/xinntao/realesrgan)
- [Colab Demo](https://colab.research.google.com/drive/1k2Zod6kSHEvraybHl50Lys0LerhyTMCo)

---

### 2. **Waifu2x** (Tối ưu cho Anime/Manga)

#### 📌 Đặc điểm:
- **Mô tả**: Deep convolutional neural networks cho anime/manga
- **Ứng dụng**: Đặc biệt tốt cho anime, manga, artwork 2D
- **Tỷ lệ upscale**: 1x, 2x, 4x, 8x, 16x, 32x
- **Denoise levels**: -1 (no denoise), 0, 1, 2, 3
- **Platform**: Cross-platform với Vulkan (Intel/AMD/NVIDIA GPU)

#### 🚀 Waifu2x-ncnn-vulkan (Recommended):

**Ưu điểm:**
- Executable độc lập, không cần CUDA/PyTorch
- Hỗ trợ đa GPU (Intel, AMD, NVIDIA)
- Rất nhanh với Vulkan API
- Portable (Windows/Linux/macOS)

**Download:**
- [Windows](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-windows.zip)
- [Linux](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-ubuntu.zip)
- [MacOS](https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesrgan-ncnn-vulkan-20220424-macos.zip)

#### 💻 Sử dụng:

```bash
# Cơ bản
waifu2x-ncnn-vulkan.exe -i input.jpg -o output.png -n 2 -s 2

# Chi tiết
waifu2x-ncnn-vulkan.exe \
  -i input.jpg \           # Input file
  -o output.png \          # Output file
  -n 2 \                   # Denoise level (0-3, -1=off)
  -s 2 \                   # Scale (1/2/4/8/16/32)
  -t 0 \                   # Tile size (0=auto)
  -m models-cunet \        # Model path
  -g 0 \                   # GPU ID (-1=cpu, 0,1,2 for multi-gpu)
  -j 1:2:2 \               # Thread count (load:proc:save)
  -f png                   # Output format (png/jpg/webp)
```

#### 📊 Models:
- **models-cunet**: Chất lượng cao nhất, chậm hơn
- **models-upconv_7_anime_style_art_rgb**: Nhanh, tốt cho anime
- **models-upconv_7_photo**: Tối ưu cho ảnh thực

---

### 3. **ESRGAN** (Enhanced Super-Resolution GAN)

#### 📌 Đặc điểm:
- **Mô tả**: Enhanced SRGAN với RRDB (Residual-in-Residual Dense Block)
- **Tỷ lệ upscale**: 2x, 3x, 4x
- **Ứng dụng**: Baseline cho Real-ESRGAN

#### 🔬 Kiến trúc:
```python
class RRDBNet(nn.Module):
    """
    RRDB (Residual in Residual Dense Block) Network
    - Input channels: 3 (RGB)
    - Output channels: 3 (RGB)  
    - Number of features: 64
    - Number of blocks: 23 (hoặc 6 cho anime)
    - Upscale: 4x
    """
    def __init__(self, in_nc=3, out_nc=3, nf=64, nb=23, upscale=4):
        # RRDB blocks
        # Upsampling layers (PixelShuffle hoặc Upconv)
        # Final conv layers
```

---

## 🔧 Tích Hợp vào manga-image-translator

### Cấu trúc Code trong manga-image-translator:

```
manga_translator/
├── upscaling/
│   ├── __init__.py              # Registry và dispatch
│   ├── common.py                # Base classes
│   ├── esrgan.py               # ESRGAN executable wrapper
│   ├── esrgan_pytorch.py       # ESRGAN PyTorch implementation
│   └── waifu2x.py              # Waifu2x executable wrapper
```

### 🎯 API Upscaling:

```python
from manga_translator.upscaling import get_upscaler, dispatch
from manga_translator.config import Upscaler
from PIL import Image

# 1. Lấy upscaler
upscaler = get_upscaler(Upscaler.esrgan)  # hoặc .waifu2x, .upscler4xultrasharp

# 2. Download models (nếu cần)
await upscaler.download()

# 3. Load model lên GPU
await upscaler.load(device='cuda')  # hoặc 'cpu'

# 4. Upscale batch images
images = [Image.open('input.jpg')]
upscaled = await upscaler.upscale(images, upscale_ratio=2)

# 5. Unload để free memory
await upscaler.unload()
```

### 📝 Config File Example:

```json
{
  "upscale": {
    "upscaler": "esrgan",           // waifu2x | esrgan | 4xultrasharp
    "upscale_ratio": 2,             // 1, 2, 3, 4, etc.
    "revert_upscaling": false       // Downscale về size gốc sau khi translate
  }
}
```

### 🎨 CLI Usage trong manga-image-translator:

```bash
# Upscale trước khi detect text (cải thiện detection)
python -m manga_translator local \
  -i input_folder \
  -o output_folder \
  --upscaler esrgan \
  --upscale-ratio 2 \
  --target-lang ENG

# Upscale rồi revert về size gốc
python -m manga_translator local \
  -i input.jpg \
  --upscaler waifu2x \
  --upscale-ratio 4 \
  --revert-upscaling \
  --target-lang ENG
```

---

## 💡 Đề Xuất Tích Hợp vào AI-Assistant

### Option 1: Tích hợp Code từ manga-image-translator

**Ưu điểm:**
- Code đã được test kỹ
- Hỗ trợ đầy đủ 3 upscalers
- API clean và dễ sử dụng

**Cách thực hiện:**
```bash
# 1. Copy upscaling module
cp -r manga-image-translator/manga_translator/upscaling ./upscale_tool/src/

# 2. Install dependencies
pip install torch torchvision
pip install einops
pip install tqdm
pip install Pillow numpy
```

### Option 2: Sử dụng Real-ESRGAN Package

**Ưu điểm:**
- Đơn giản, pip install được
- Cộng đồng lớn, cập nhật thường xuyên
- Nhiều pretrained models

**Cách thực hiện:**
```bash
pip install realesrgan
pip install basicsr
```

```python
# upscale_tool/src/upscaler.py
from realesrgan import RealESRGANer
from basicsr.archs.rrdbnet_arch import RRDBNet

class ImageUpscaler:
    def __init__(self, model_name='RealESRGAN_x4plus', device='cuda'):
        self.device = device
        self.model = self._load_model(model_name)
    
    def _load_model(self, model_name):
        if model_name == 'RealESRGAN_x4plus':
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, 
                          num_block=23, num_grow_ch=32, scale=4)
            upsampler = RealESRGANer(
                scale=4,
                model_path='weights/RealESRGAN_x4plus.pth',
                model=model,
                tile=400,
                tile_pad=10,
                pre_pad=0,
                half=True if self.device == 'cuda' else False
            )
        elif model_name == 'RealESRGAN_x4plus_anime_6B':
            model = RRDBNet(num_in_ch=3, num_out_ch=3, num_feat=64, 
                          num_block=6, num_grow_ch=32, scale=4)
            upsampler = RealESRGANer(
                scale=4,
                model_path='weights/RealESRGAN_x4plus_anime_6B.pth',
                model=model,
                tile=400,
                tile_pad=10,
                pre_pad=0,
                half=True if self.device == 'cuda' else False
            )
        return upsampler
    
    def upscale(self, img, outscale=4):
        """
        Args:
            img: numpy array (H, W, C) BGR format
            outscale: final output scale
        Returns:
            output: upscaled image (numpy array)
        """
        output, _ = self.model.enhance(img, outscale=outscale)
        return output
```

### Option 3: Sử dụng NCNN Executable (Fastest)

**Ưu điểm:**
- Rất nhanh (Vulkan API)
- Không cần Python environment phức tạp
- Cross-platform
- Hỗ trợ mọi GPU (Intel/AMD/NVIDIA)

**Cách thực hiện:**
```python
# upscale_tool/src/ncnn_upscaler.py
import subprocess
import os
from pathlib import Path

class NCNNUpscaler:
    def __init__(self, executable_path='./bin/realesrgan-ncnn-vulkan.exe'):
        self.executable = executable_path
    
    def upscale(self, input_path, output_path, scale=4, model='realesrgan-x4plus'):
        """
        Args:
            input_path: đường dẫn ảnh input
            output_path: đường dẫn ảnh output
            scale: tỷ lệ scale (2, 3, 4)
            model: tên model (realesrgan-x4plus, realesrgan-x4plus-anime, etc.)
        """
        cmd = [
            self.executable,
            '-i', input_path,
            '-o', output_path,
            '-s', str(scale),
            '-n', model,
            '-f', 'png'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            raise RuntimeError(f"Upscaling failed: {result.stderr}")
        
        return output_path
    
    def upscale_folder(self, input_folder, output_folder, **kwargs):
        """Upscale toàn bộ folder"""
        cmd = [
            self.executable,
            '-i', input_folder,
            '-o', output_folder,
            '-s', str(kwargs.get('scale', 4)),
            '-n', kwargs.get('model', 'realesrgan-x4plus'),
            '-f', kwargs.get('format', 'png')
        ]
        
        subprocess.run(cmd, check=True)
```

---

## 📊 So Sánh Performance

### Tốc độ xử lý (400x400 → 800x800):

| Model | Block Size | Time (s) | VRAM (MB) |
|-------|-----------|----------|-----------|
| **Real-ESRGAN (cunet)** | 200 | 1.04 | 638 |
| **Waifu2x-ncnn (cunet)** | 200 | 0.86 | 638 |
| **Waifu2x-ncnn (upconv)** | 200 | 0.83 | 482 |
| **Real-ESRGAN (anime)** | 200 | 0.95 | 482 |

### Chất lượng:

| Use Case | Recommended Model | Lý do |
|----------|------------------|-------|
| Ảnh thật (photo) | Real-ESRGAN x4plus | Tốt nhất cho ảnh thực |
| Anime/Manga | Real-ESRGAN x4plus_anime_6B hoặc Waifu2x | Ít artifacts, giữ được art style |
| Video game assets | Real-ESRGAN x4plus | Balance tốt |
| Low-res screenshots | realesr-general-x4v3 | Nhỏ gọn, có denoise |

---

## 🎯 Roadmap Tích Hợp

### Phase 1: Setup Cơ Bản
- [ ] Tạo cấu trúc folder cho upscale_tool
- [ ] Download pretrained models
- [ ] Cài đặt dependencies
- [ ] Test basic upscaling

### Phase 2: API Development
- [ ] Tạo Python API wrapper
- [ ] Implement batch processing
- [ ] Add progress tracking
- [ ] Error handling

### Phase 3: Integration
- [ ] Tích hợp vào AI-Assistant workflow
- [ ] Tạo config system
- [ ] Build Web UI (optional)
- [ ] CLI interface

### Phase 4: Optimization
- [ ] GPU optimization
- [ ] Memory management
- [ ] Multi-threading cho batch
- [ ] Caching system

---

## 📚 Tài Liệu Tham Khảo

### Papers:
1. **ESRGAN**: [ESRGAN: Enhanced Super-Resolution Generative Adversarial Networks](https://arxiv.org/abs/1809.00219)
2. **Real-ESRGAN**: [Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data](https://arxiv.org/abs/2107.10833)
3. **Waifu2x**: [Image Super-Resolution for Anime-Style Art](https://github.com/nagadomi/waifu2x)

### GitHub Repos:
- [Real-ESRGAN](https://github.com/xinntao/Real-ESRGAN) - 33.4k stars ⭐
- [manga-image-translator](https://github.com/zyddnys/manga-image-translator) - 9k stars ⭐
- [waifu2x-ncnn-vulkan](https://github.com/nihui/waifu2x-ncnn-vulkan) - 3.3k stars ⭐
- [BasicSR](https://github.com/xinntao/BasicSR) - Image/Video restoration toolkit

### Chinese Resources (中文资源):
- [Real-ESRGAN 中文文档](https://github.com/xinntao/Real-ESRGAN/blob/master/README_CN.md)
- [manga-image-translator 中文说明](https://github.com/zyddnys/manga-image-translator/blob/main/README_CN.md)
- [知乎 - Real-ESRGAN 讲解](https://zhuanlan.zhihu.com/p/390167517)
- [B站 - Real-ESRGAN 视频教程](https://www.bilibili.com/video/BV1H34y1m7sS/)

---

## 🔥 Quick Start Guide

### Bước 1: Chọn Phương Án

**Cho người mới bắt đầu:**
```bash
# Sử dụng NCNN executable (đơn giản nhất)
# Download từ: https://github.com/xinntao/Real-ESRGAN/releases
./realesrgan-ncnn-vulkan.exe -i input.jpg -o output.png
```

**Cho Python developers:**
```bash
# Sử dụng Real-ESRGAN package
pip install realesrgan
python inference_realesrgan.py -i input.jpg -o output.png
```

**Cho advanced users:**
```bash
# Clone manga-image-translator và sử dụng upscaling module
git clone https://github.com/zyddnys/manga-image-translator
# Xem code trong manga_translator/upscaling/
```

### Bước 2: Download Models

```bash
# Real-ESRGAN x4plus (17MB)
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth

# Real-ESRGAN x4plus anime (16MB)  
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth

# Real-ESRGAN general x4v3 (small, 16MB)
wget https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.5.0/realesr-general-x4v3.pth
```

### Bước 3: Test

```python
from PIL import Image
from upscaler import ImageUpscaler

# Initialize
upscaler = ImageUpscaler(model_name='RealESRGAN_x4plus', device='cuda')

# Load image
img = Image.open('input.jpg')

# Upscale
output = upscaler.upscale(img, outscale=4)

# Save
output.save('output.png')
```

---

## ⚠️ Lưu Ý Quan Trọng

### GPU Memory:
- **4GB VRAM**: Dùng tile_size=200-400, half precision (fp16)
- **6GB VRAM**: Dùng tile_size=400-600
- **8GB+ VRAM**: Có thể upscale ảnh lớn không cần tile

### Chất lượng vs Tốc độ:
- **Chất lượng cao**: Real-ESRGAN x4plus (chậm, ~2s/400x400)
- **Balanced**: Real-ESRGAN anime (nhanh hơn, ~0.9s/400x400)
- **Nhanh nhất**: Waifu2x-ncnn hoặc realesr-general-x4v3

### Tips:
1. **Upscale trước khi xử lý**: Nếu dùng OCR/detection, upscale ảnh trước sẽ cải thiện accuracy
2. **Denoise**: Dùng `-dn` option (Real-ESRGAN v3) hoặc waifu2x `-n` để giảm noise
3. **Batch processing**: Xử lý nhiều ảnh cùng lúc để tận dụng GPU
4. **Face enhancement**: Kết hợp với GFPGAN nếu có khuôn mặt trong ảnh

---

**Tác giả**: AI Research Team  
**Ngày cập nhật**: 2024-12-02  
**Version**: 1.0
