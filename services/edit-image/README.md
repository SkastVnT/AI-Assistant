# 🎨 Edit Image Service

> AI-powered image editing service with instruction-based editing, similar to Grok Edit Image.
> **Version: 0.4.0** | Self-hosted, no content filtering

## ✨ Features

### Core Generation
- **Text-to-Image**: Generate images from text descriptions
- **Image-to-Image**: Transform images while preserving structure
- **InstructPix2Pix**: Edit images with natural language instructions
- **Inpainting**: Fill in or modify parts of images
- **ControlNet**: Guided generation (Canny, OpenPose, Depth, Lineart, Scribble)

### 🆕 v0.4.0 Features (Phase 6)
- **PuLID**: ByteDance NeurIPS 2024 - Identity preservation with Lightning T2I
- **EcomID**: Alibaba IdentityNet - E-commerce identity generation
- **Batch Processing**: Priority queue, async jobs, bulk operations
- **Multi-GPU**: Load balancing across multiple GPUs
- **Model Offloading**: Smart memory optimization, sequential CPU offload

### v0.3.0 Features
- **IP-Adapter**: Image prompts, style transfer, FaceID Plus
- **InstantID**: Zero-shot face swap with InsightFace + ControlNet
- **Inpaint Anything**: SAM + LaMa for click-to-remove objects
- **Smart Edit**: LLM-enhanced editing with web search enrichment
- **Qwen-Image-Edit**: 20B SOTA model for semantic editing
- **Step1X-Edit**: Reasoning mode for complex instructions
- **LoRA Training**: In-app training with dataset preparation
- **Anime ControlNet**: lineart_anime, multi-controlnet support

### Anime & Character
- **Anime Models**: Animagine XL, Anything V5 support
- **Character Search**: AniList, MyAnimeList integration
- **Reference Search**: Danbooru, Gelbooru image search
- **Auto-Tagging**: WD14 Tagger, DeepDanbooru for prompt generation

### Post-Processing
- **Upscaling**: Real-ESRGAN (4x, anime-optimized)
- **Face Restoration**: GFPGAN for face enhancement
- **Full Enhancement Pipeline**: Upscale + face restore combo

## 🖥️ Web UI Tabs (18 tabs)

| Tab | Description |
|-----|-------------|
| 📝 Text to Image | Generate from text prompt |
| 🖼️ Image to Image | Transform existing images |
| ✏️ Edit Image | InstructPix2Pix editing |
| 🎨 Inpaint | Fill in regions with mask |
| 🎛️ ControlNet | Pose/edge guided generation |
| 🎌 Anime | Specialized anime generation |
| 🎨 IP-Adapter | Image prompt & style transfer |
| 👤 InstantID | Zero-shot face swap |
| ✂️ Inpaint Anything | Click-to-remove objects |
| 🧠 Smart Edit | LLM-enhanced editing |
| 🔍 Search | Character & reference search |
| 🏷️ Tagger | Auto-tag images for prompts |
| ⬆️ Upscale | Image enhancement |
| 🎭 PuLID | **NEW** Identity preservation |
| 🛍️ EcomID | **NEW** E-commerce identity |
| 📦 Batch | **NEW** Batch processing |
| 🖥️ GPU & Memory | **NEW** Resource management |
| ⚙️ Settings | System info & cache |

## 🛠️ Tech Stack

- **Backend**: FastAPI + Python 3.10+
- **AI Models**: 
  - SDXL / FLUX.1 / SD3
  - Step1X-Edit / Qwen-Image-Edit
  - ControlNet, IP-Adapter, InstantID
- **UI**: Gradio / Web Interface
- **Inference**: PyTorch + Diffusers

## 📦 Installation

### Prerequisites

- Python 3.10+
- CUDA 11.8+ (for GPU acceleration)
- 8GB+ VRAM (12GB+ recommended)

### Setup

```bash
# Clone repository (if not already)
cd services/edit-image

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Download Models

Models được tải về local sẽ **NHANH HƠN RẤT NHIỀU** so với qua HuggingFace API.

```bash
# Xem danh sách tất cả models
python download_models.py --list

# Tải models thiết yếu (~22GB) - KHUYẾN NGHỊ
python download_models.py --essential

# Tải thêm anime models
python download_models.py --category anime

# Tải tất cả (~65GB)
python download_models.py --all
```

**Xem chi tiết tại**: [MODELS_DOWNLOAD_LIST.md](MODELS_DOWNLOAD_LIST.md)

## 🚀 Usage

### Start Server

```bash
# Windows
.\start.bat

# Linux/Mac
./start.sh

# Or directly
python -m uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
```

### Web Interface

Open browser: `http://localhost:8100`

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| **Generation** |
| POST | `/api/v1/generate` | Text-to-Image generation |
| POST | `/api/v1/edit` | Edit image with text instruction |
| POST | `/api/v1/img2img` | Image-to-image transformation |
| POST | `/api/v1/inpaint` | Inpainting with mask |
| POST | `/api/v1/controlnet` | ControlNet generation |
| **Search** |
| POST | `/api/v1/search/images` | Search reference images |
| POST | `/api/v1/search/character` | Search character info |
| **Tagging** |
| POST | `/api/v1/tag` | Auto-tag image |
| POST | `/api/v1/image-to-prompt` | Convert image to prompt |
| **Upscaling** |
| POST | `/api/v1/upscale` | Upscale image |
| POST | `/api/v1/restore-faces` | Restore faces in image |
| POST | `/api/v1/enhance` | Full enhancement pipeline |
| **System** |
| GET | `/api/v1/models` | List available models |
| GET | `/api/v1/health` | Service health status |
| GET | `/api/v1/vram` | VRAM usage stats |
| POST | `/api/v1/clear-cache` | Clear model cache |

### Example API Call

```python
import requests

response = requests.post(
    "http://localhost:8100/api/v1/edit",
    files={"image": open("input.png", "rb")},
    data={
        "prompt": "Change hair color to blue",
        "model": "sdxl",
        "strength": 0.7
    }
)

# Save result
with open("output.png", "wb") as f:
    f.write(response.content)
```

## 📁 Project Structure

```
edit-image/
├── app/
│   ├── __init__.py          # Package info (version 0.2.0)
│   ├── main.py              # FastAPI app entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # All REST API routes
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Pydantic configuration
│   │   ├── pipeline.py      # Diffusion pipeline manager
│   │   ├── search.py        # Web search (Danbooru, Gelbooru, AniList, MAL)
│   │   └── upscaler.py      # Real-ESRGAN, GFPGAN post-processing
│   ├── ui/
│   │   ├── __init__.py
│   │   └── gradio_app.py    # Gradio web interface (10 tabs)
│   └── utils/
│       ├── __init__.py
│       ├── image_utils.py   # Image processing utilities
│       ├── controlnet_utils.py # ControlNet preprocessing
│       └── tagger.py        # WD14/DeepDanbooru auto-tagging
├── config/
│   └── settings.yaml        # Configuration file
├── models/                  # Downloaded model weights
├── outputs/                 # Generated images
├── logs/                    # Application logs
├── requirements.txt         # Python dependencies
├── Dockerfile              # Docker build
├── docker-compose.yml      # Docker compose
├── start.bat               # Windows startup
├── start.sh                # Linux startup
├── setup.bat               # Windows setup
└── README.md
```

## ⚙️ Configuration

Edit `config/settings.yaml`:

```yaml
server:
  host: "0.0.0.0"
  port: 8100

models:
  default: "sdxl"
  cache_dir: "./models"
  
inference:
  device: "cuda"
  dtype: "float16"
  batch_size: 1
  
controlnet:
  enabled: true
  models:
    - canny
    - openpose
    - depth
```

## 🎯 Supported Models

### Base Models
- SDXL 1.0
- FLUX.1 [dev]
- SD3 Medium
- Animagine XL 3.1

### ControlNet
- Canny Edge
- OpenPose
- Depth
- Lineart
- Segmentation

### Identity Preservation
- InstantID
- PuLID
- IP-Adapter FaceID

## 📝 License

MIT License - Use at your own risk.

## ⚠️ Disclaimer

This tool is for personal use only. Users are responsible for ensuring compliance with local laws and regulations.
