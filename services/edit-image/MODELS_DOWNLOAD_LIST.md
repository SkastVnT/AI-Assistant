# 📥 Danh Sách Models Cần Tải - Edit Image Tool v0.3.0

> **Mục tiêu**: Tải về local để chạy offline, tốc độ nhanh hơn nhiều so với qua HuggingFace API
> **Thư mục lưu**: `./models/` trong thư mục edit-image
> **Tổng dung lượng ước tính**: ~80-120GB (tùy chọn)

---

## 📁 Cấu trúc thư mục Models

```
models/
├── base/                    # Base models (SDXL, SD1.5, FLUX)
├── controlnet/              # ControlNet checkpoints
├── ip-adapter/              # IP-Adapter weights
├── instantid/               # InstantID components
├── inpaint/                 # SAM + LaMa
├── lora/                    # LoRA weights
├── upscaler/                # Real-ESRGAN, GFPGAN
├── tagger/                  # WD14, DeepDanbooru
├── anime/                   # Anime-specific models
├── edit/                    # Edit models (Qwen, Step1X)
└── face/                    # Face detection (InsightFace)
```

---

## 🔥 PRIORITY 1: Core Models (BẮT BUỘC)

### 1. SDXL Base Model (~6.5GB)
| Model | Link | Size | License |
|-------|------|------|---------|
| **SDXL 1.0 Base** | https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0 | 6.5GB | OpenRAIL++ |
| **SDXL 1.0 Refiner** | https://huggingface.co/stabilityai/stable-diffusion-xl-refiner-1.0 | 6.2GB | OpenRAIL++ |
| **SDXL VAE** | https://huggingface.co/stabilityai/sdxl-vae | 335MB | OpenRAIL++ |

**Download command:**
```bash
# Dùng huggingface-cli
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 --local-dir ./models/base/sdxl-base
huggingface-cli download stabilityai/stable-diffusion-xl-refiner-1.0 --local-dir ./models/base/sdxl-refiner
```

### 2. SD 1.5 Base Model (~4GB)
| Model | Link | Size |
|-------|------|------|
| **SD 1.5** | https://huggingface.co/runwayml/stable-diffusion-v1-5 | 4.3GB |
| **SD 1.5 Inpainting** | https://huggingface.co/runwayml/stable-diffusion-inpainting | 4.3GB |

### 3. InstructPix2Pix (~5GB)
| Model | Link | Size |
|-------|------|------|
| **InstructPix2Pix** | https://huggingface.co/timbrooks/instruct-pix2pix | 5.1GB |

---

## 🎨 PRIORITY 2: ControlNet Models

### ControlNet for SDXL (~2.5GB each)
| Model | Link | Use Case |
|-------|------|----------|
| **Canny** | https://huggingface.co/diffusers/controlnet-canny-sdxl-1.0 | Edge detection |
| **Depth** | https://huggingface.co/diffusers/controlnet-depth-sdxl-1.0 | Depth map |
| **OpenPose** | https://huggingface.co/thibaud/controlnet-openpose-sdxl-1.0 | Pose control |

### ControlNet for SD 1.5 (~1.4GB each)
| Model | Link | Use Case |
|-------|------|----------|
| **Canny** | https://huggingface.co/lllyasviel/sd-controlnet-canny | Edge |
| **Depth** | https://huggingface.co/lllyasviel/sd-controlnet-depth | Depth |
| **OpenPose** | https://huggingface.co/lllyasviel/sd-controlnet-openpose | Pose |
| **Scribble** | https://huggingface.co/lllyasviel/sd-controlnet-scribble | Sketch |
| **Seg** | https://huggingface.co/lllyasviel/sd-controlnet-seg | Segmentation |

### 🎌 ControlNet Anime (QUAN TRỌNG cho anime)
| Model | Link | Use Case |
|-------|------|----------|
| **Lineart Anime** | https://huggingface.co/lllyasviel/control_v11p_sd15_lineart_anime | Anime line art |
| **Anime Control** | https://huggingface.co/lint/anime_control | Anime style |

---

## 👤 PRIORITY 3: Identity Preservation

### IP-Adapter (~100-500MB each)
| Model | Link | Size | Use Case |
|-------|------|------|----------|
| **IP-Adapter SDXL** | https://huggingface.co/h94/IP-Adapter | ~100MB | Image prompt |
| **IP-Adapter Plus** | https://huggingface.co/h94/IP-Adapter | ~100MB | Better quality |
| **IP-Adapter FaceID** | https://huggingface.co/h94/IP-Adapter-FaceID | ~500MB | Face identity |
| **IP-Adapter FaceID Plus** | https://huggingface.co/h94/IP-Adapter-FaceID | ~500MB | Better face |
| **IP-Adapter Anime** | https://huggingface.co/r3gm/ip-adapter-anime | ~100MB | Anime character |

**Direct download links:**
```
https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter_sdxl.safetensors
https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors
https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid_sdxl.bin
https://huggingface.co/h94/IP-Adapter-FaceID/resolve/main/ip-adapter-faceid-plusv2_sdxl.bin
```

### InstantID Components (~2GB total)
| Component | Link | Size |
|-----------|------|------|
| **InstantID Model** | https://huggingface.co/InstantX/InstantID | ~1.5GB |
| **ControlNet InstantID** | https://huggingface.co/InstantX/InstantID | ~500MB |
| **Antelopev2 (InsightFace)** | https://huggingface.co/DIAMONIK7777/antelopev2 | ~360MB |

**Direct download:**
```
# InstantID
https://huggingface.co/InstantX/InstantID/resolve/main/ip-adapter.bin
https://huggingface.co/InstantX/InstantID/resolve/main/ControlNetModel/diffusion_pytorch_model.safetensors

# InsightFace (REQUIRED for InstantID)
https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/1k3d68.onnx
https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/2d106det.onnx
https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/genderage.onnx
https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/glintr100.onnx
https://huggingface.co/DIAMONIK7777/antelopev2/resolve/main/scrfd_10g_bnkps.onnx
```

---

## ✂️ PRIORITY 4: Inpaint Anything (SAM + LaMa)

### Segment Anything Model (SAM)
| Model | Link | Size | Note |
|-------|------|------|------|
| **SAM ViT-H** | https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth | 2.6GB | Best quality |
| **SAM ViT-L** | https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth | 1.2GB | Balanced |
| **SAM ViT-B** | https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth | 375MB | Fast |

**Khuyến nghị**: SAM ViT-L cho balance giữa chất lượng và tốc độ

### LaMa Inpainting
| Model | Link | Size |
|-------|------|------|
| **LaMa Big** | https://huggingface.co/smartywu/big-lama | ~200MB |

---

## ⬆️ PRIORITY 5: Upscaler & Face Restoration

### Real-ESRGAN
| Model | Link | Size | Use Case |
|-------|------|------|----------|
| **RealESRGAN x4plus** | https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth | 67MB | General |
| **RealESRGAN x4plus Anime** | https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth | 17MB | Anime |
| **RealESRGAN x2plus** | https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.1/RealESRGAN_x2plus.pth | 67MB | 2x upscale |

### GFPGAN (Face Restoration)
| Model | Link | Size |
|-------|------|------|
| **GFPGANv1.4** | https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth | 348MB |
| **Detection** | https://github.com/xinntao/facexlib/releases/download/v0.1.0/detection_Resnet50_Final.pth | 104MB |
| **Parsing** | https://github.com/xinntao/facexlib/releases/download/v0.2.2/parsing_parsenet.pth | 81MB |

---

## 🏷️ PRIORITY 6: Tagger Models

### WD14 Tagger
| Model | Link | Size |
|-------|------|------|
| **WD14 ViT Tagger v2** | https://huggingface.co/SmilingWolf/wd-v1-4-vit-tagger-v2 | ~400MB |
| **WD14 Moat Tagger v2** | https://huggingface.co/SmilingWolf/wd-v1-4-moat-tagger-v2 | ~500MB |
| **WD14 SwinV2 Tagger v2** | https://huggingface.co/SmilingWolf/wd-v1-4-swinv2-tagger-v2 | ~850MB |

### DeepDanbooru
| Model | Link | Size |
|-------|------|------|
| **DeepDanbooru** | https://github.com/KichangKim/DeepDanbooru/releases/download/v3-20211112-sgd-e28/deepdanbooru-v3-20211112-sgd-e28.zip | ~600MB |

---

## 🎌 PRIORITY 7: Anime Models

### Animagine XL 3.1 (RECOMMENDED)
| Model | Link | Size |
|-------|------|------|
| **Animagine XL 3.1** | https://huggingface.co/cagliostrolab/animagine-xl-3.1 | ~6.5GB |

**Direct download:**
```
https://huggingface.co/cagliostrolab/animagine-xl-3.1/resolve/main/animagine-xl-3.1.safetensors
```

### Waifu Diffusion
| Model | Link | Size |
|-------|------|------|
| **Waifu Diffusion 1.4** | https://huggingface.co/hakurei/waifu-diffusion-v1-4 | ~4GB |

### Other Anime Models (CivitAI)
| Model | CivitAI Link | Base |
|-------|--------------|------|
| **Anything V5** | https://civitai.com/models/9409 | SD1.5 |
| **MeinaMix** | https://civitai.com/models/7240 | SD1.5 |
| **CounterfeitXL** | https://civitai.com/models/118406 | SDXL |
| **Pony Diffusion XL** | https://civitai.com/models/257749 | SDXL |

---

## 🚀 PRIORITY 8: SOTA Edit Models

### Qwen-Image-Edit (~40GB)
| Model | Link | Size | Note |
|-------|------|------|------|
| **Qwen-Image-Edit** | https://huggingface.co/Qwen/Qwen-Image-Edit | ~40GB | SOTA 20B params |
| **Qwen2.5-VL-7B** | https://huggingface.co/Qwen/Qwen2.5-VL-7B-Instruct | ~14GB | Lighter version |

**⚠️ Cần GPU 24GB+ hoặc quantization**

### Step1X-Edit (~7GB)
| Model | Link | Size | Note |
|-------|------|------|------|
| **Step1X-Edit** | https://huggingface.co/stepfun-ai/Step1X-Edit | ~7GB FP16 | Reasoning mode |
| **Step1X-Edit FP8** | ModelScope | ~4GB | Quantized |

**Direct download:**
```
# HuggingFace
https://huggingface.co/stepfun-ai/Step1X-Edit/tree/main

# ModelScope (alternative)
https://modelscope.cn/models/stepfun-ai/Step1X-Edit
```

---

## 🔧 PRIORITY 9: Additional Tools

### CLIP Image Encoder (Required for IP-Adapter)
| Model | Link | Size |
|-------|------|------|
| **CLIP ViT-H-14** | https://huggingface.co/laion/CLIP-ViT-H-14-laion2B-s32B-b79K | ~3.9GB |
| **CLIP ViT-bigG-14** | https://huggingface.co/laion/CLIP-ViT-bigG-14-laion2B-39B-b160k | ~10GB |

### Reference-Only Pipeline
| Model | Link | Use Case |
|-------|------|----------|
| **SD Reference-Only** | https://huggingface.co/aihao2000/stable-diffusion-reference-only | Style transfer, coloring |

### Ghibli Style
| Model | Link | Size |
|-------|------|------|
| **Ghibli Diffusion** | https://huggingface.co/nitrosocke/Ghibli-Diffusion | ~4GB |

---

## 📦 Download Script

Tạo file `download_models.py` để tải tất cả:

```python
#!/usr/bin/env python3
"""Download all models for Edit Image Tool"""

import os
import subprocess
from pathlib import Path

MODELS_DIR = Path("./models")

# Priority models to download
MODELS = {
    # Base models
    "base/sdxl-base": "stabilityai/stable-diffusion-xl-base-1.0",
    "base/sdxl-refiner": "stabilityai/stable-diffusion-xl-refiner-1.0",
    "base/sd15": "runwayml/stable-diffusion-v1-5",
    "base/instruct-pix2pix": "timbrooks/instruct-pix2pix",
    
    # ControlNet
    "controlnet/sdxl-canny": "diffusers/controlnet-canny-sdxl-1.0",
    "controlnet/sdxl-depth": "diffusers/controlnet-depth-sdxl-1.0",
    "controlnet/sd15-canny": "lllyasviel/sd-controlnet-canny",
    "controlnet/sd15-openpose": "lllyasviel/sd-controlnet-openpose",
    "controlnet/lineart-anime": "lllyasviel/control_v11p_sd15_lineart_anime",
    
    # IP-Adapter
    "ip-adapter/sdxl": "h94/IP-Adapter",
    "ip-adapter/faceid": "h94/IP-Adapter-FaceID",
    "ip-adapter/anime": "r3gm/ip-adapter-anime",
    
    # InstantID
    "instantid/model": "InstantX/InstantID",
    "instantid/antelopev2": "DIAMONIK7777/antelopev2",
    
    # Anime
    "anime/animagine-xl-31": "cagliostrolab/animagine-xl-3.1",
    "anime/waifu-diffusion": "hakurei/waifu-diffusion-v1-4",
    
    # Tagger
    "tagger/wd14-vit": "SmilingWolf/wd-v1-4-vit-tagger-v2",
    
    # SOTA Edit
    "edit/step1x": "stepfun-ai/Step1X-Edit",
    # "edit/qwen": "Qwen/Qwen-Image-Edit",  # Very large, download separately
}

# Direct download URLs
DIRECT_DOWNLOADS = {
    # SAM
    "inpaint/sam_vit_l.pth": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth",
    "inpaint/sam_vit_b.pth": "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth",
    
    # Real-ESRGAN
    "upscaler/RealESRGAN_x4plus.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth",
    "upscaler/RealESRGAN_x4plus_anime.pth": "https://github.com/xinntao/Real-ESRGAN/releases/download/v0.2.2.4/RealESRGAN_x4plus_anime_6B.pth",
    
    # GFPGAN
    "upscaler/GFPGANv1.4.pth": "https://github.com/TencentARC/GFPGAN/releases/download/v1.3.4/GFPGANv1.4.pth",
    
    # LaMa
    "inpaint/big-lama.pt": "https://huggingface.co/smartywu/big-lama/resolve/main/big-lama.pt",
}

def download_hf_model(local_path: str, repo_id: str):
    """Download from HuggingFace"""
    full_path = MODELS_DIR / local_path
    full_path.mkdir(parents=True, exist_ok=True)
    
    cmd = f"huggingface-cli download {repo_id} --local-dir {full_path}"
    print(f"Downloading {repo_id} to {full_path}...")
    subprocess.run(cmd, shell=True)

def download_direct(local_path: str, url: str):
    """Direct download with wget/curl"""
    full_path = MODELS_DIR / local_path
    full_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Use curl on Windows, wget on Linux
    if os.name == 'nt':
        cmd = f'curl -L -o "{full_path}" "{url}"'
    else:
        cmd = f'wget -O "{full_path}" "{url}"'
    
    print(f"Downloading {url}...")
    subprocess.run(cmd, shell=True)

if __name__ == "__main__":
    print("=" * 60)
    print("Edit Image Tool - Model Downloader")
    print("=" * 60)
    
    # Create base directory
    MODELS_DIR.mkdir(exist_ok=True)
    
    # Download HuggingFace models
    print("\n[1/2] Downloading HuggingFace models...")
    for local_path, repo_id in MODELS.items():
        download_hf_model(local_path, repo_id)
    
    # Download direct URLs
    print("\n[2/2] Downloading direct files...")
    for local_path, url in DIRECT_DOWNLOADS.items():
        download_direct(local_path, url)
    
    print("\n" + "=" * 60)
    print("Download complete!")
    print("=" * 60)
```

---

## 📊 Tổng kết dung lượng

| Category | Models | Size |
|----------|--------|------|
| Base Models | SDXL, SD1.5, IP2P | ~20GB |
| ControlNet | SDXL + SD1.5 | ~15GB |
| IP-Adapter + InstantID | All variants | ~5GB |
| SAM + LaMa | Inpaint | ~3GB |
| Upscaler | ESRGAN, GFPGAN | ~0.5GB |
| Tagger | WD14 | ~1GB |
| Anime | Animagine, Waifu | ~12GB |
| SOTA Edit | Step1X | ~7GB |
| **TOTAL (Essential)** | | **~65GB** |
| + Qwen-Image-Edit | Optional | +40GB |
| **TOTAL (Full)** | | **~105GB** |

---

## ⚡ Quick Start (Tải nhanh - Chỉ cần thiết)

Nếu chỉ muốn tải những thứ cần thiết nhất:

```bash
# 1. SDXL Base (BẮT BUỘC) - 6.5GB
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 --local-dir ./models/base/sdxl-base

# 2. InstructPix2Pix (cho Edit) - 5GB
huggingface-cli download timbrooks/instruct-pix2pix --local-dir ./models/base/ip2p

# 3. IP-Adapter (cho Image Prompt) - 100MB
huggingface-cli download h94/IP-Adapter --local-dir ./models/ip-adapter

# 4. InstantID (cho Face Swap) - 2GB
huggingface-cli download InstantX/InstantID --local-dir ./models/instantid
huggingface-cli download DIAMONIK7777/antelopev2 --local-dir ./models/face/antelopev2

# 5. SAM (cho Inpaint Anything) - 1.2GB
curl -L -o ./models/inpaint/sam_vit_l.pth https://dl.fbaipublicfiles.com/segment_anything/sam_vit_l_0b3195.pth

# 6. Real-ESRGAN (cho Upscale) - 67MB
curl -L -o ./models/upscaler/RealESRGAN_x4plus.pth https://github.com/xinntao/Real-ESRGAN/releases/download/v0.1.0/RealESRGAN_x4plus.pth

# 7. Animagine XL (cho Anime) - 6.5GB
huggingface-cli download cagliostrolab/animagine-xl-3.1 --local-dir ./models/anime/animagine-xl
```

**Tổng Quick Start: ~22GB**

---

## 🔗 Useful Links

- **HuggingFace**: https://huggingface.co/
- **CivitAI**: https://civitai.com/ (LoRA, Checkpoints)
- **ModelScope**: https://modelscope.cn/ (Chinese models)
- **HF-Mirror** (China): https://hf-mirror.com/

---

> **Note**: Sau khi tải xong, cập nhật `config/settings.yaml` với đường dẫn đến các models.
