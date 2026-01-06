# Changelog

All notable changes to Edit Image Service.

## [0.4.0] - Phase 6 - 2025-01

### ✨ New Features

#### 🎭 PuLID Integration (ByteDance NeurIPS 2024)
- **Identity Preservation**: Generate images while keeping facial identity
- **Lightning Mode**: Fast 4-step generation
- **Face Swap**: Transfer identity between images
- **Edit with ID**: Modify images while preserving identity
- Files: `app/core/pulid.py`

#### 🛍️ EcomID Integration (Alibaba)
- **IdentityNet**: Trained on 2M portrait images
- **Keypoint Control**: Precise facial feature control
- **Multi-Pose Generation**: Generate multiple angles at once
- **E-Commerce Mode**: Optimized for product photography
- Files: `app/core/ecomid.py`

#### 📦 Batch Processing
- **Priority Queue**: Jobs with priority levels 0-10
- **Async Processing**: Non-blocking job submission
- **Progress Tracking**: Real-time job status updates
- **Multiple Handlers**: generate, edit, upscale, face_swap
- Files: `app/core/batch_processing.py`

#### 🖥️ Multi-GPU Support
- **Load Balancing**: 4 strategies (round_robin, least_loaded, vram_based, compute_based)
- **GPU Tiers**: Automatic classification (HIGH 12GB+, MEDIUM 8GB, LOW 6GB)
- **Model Placement**: Smart allocation based on VRAM requirements
- **GPU Context Manager**: Automatic device selection
- Files: `app/core/multi_gpu.py`

#### 💾 Model Offloading
- **Offload Strategies**: none, attention, vae, model_cpu, sequential_cpu
- **Auto-Detection**: Recommends strategy based on available VRAM
- **Quantization**: FP16, BF16, INT8, INT4 support
- **Memory Cleanup**: Aggressive cache clearing
- Files: `app/core/model_offload.py`

### 🔧 API Changes

#### New Endpoints
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/pulid/generate` | Generate with identity |
| POST | `/api/v1/pulid/edit` | Edit preserving identity |
| POST | `/api/v1/pulid/swap` | Face swap |
| POST | `/api/v1/ecomid/generate` | EcomID generation |
| POST | `/api/v1/ecomid/multi-pose` | Multi-pose generation |
| POST | `/api/v1/ecomid/ecommerce` | E-commerce mode |
| POST | `/api/v1/batch/submit` | Submit batch job |
| POST | `/api/v1/batch/submit-batch` | Submit multiple jobs |
| GET | `/api/v1/batch/status/{id}` | Get job status |
| DELETE | `/api/v1/batch/cancel/{id}` | Cancel job |
| GET | `/api/v1/gpu/status` | GPU status |
| POST | `/api/v1/gpu/configure` | Configure GPUs |
| GET | `/api/v1/memory/status` | Memory status |
| POST | `/api/v1/memory/configure` | Configure offloading |
| POST | `/api/v1/memory/cleanup` | Trigger cleanup |

### 📱 UI Changes

#### New Tabs
- **PuLID Tab**: Generate, Edit, Face Swap sub-tabs
- **EcomID Tab**: Generate, Multi-Pose, E-Commerce sub-tabs
- **Batch Tab**: Job submission and queue management
- **GPU & Memory Tab**: Resource monitoring and configuration

### 📦 New Files Created

```
app/
├── core/
│   ├── pulid.py           # PuLID pipeline (~550 lines)
│   ├── ecomid.py          # EcomID pipeline (~500 lines)
│   ├── batch_processing.py # Batch processor (~400 lines)
│   ├── multi_gpu.py       # GPU manager (~450 lines)
│   └── model_offload.py   # Memory optimizer (~400 lines)
├── api/
│   └── phase6_routes.py   # Phase 6 API routes (~450 lines)
└── ui/
    └── phase6_ui.py       # Phase 6 Gradio UI (~600 lines)
```

### 🔧 Technical Details

#### PuLID Architecture
- Based on SDXL with identity encoder
- Contrastive alignment loss for ID preservation
- 3 modes: STANDARD (30 steps), LIGHTNING (4 steps), FIDELITY (50 steps)
- Face detection via InsightFace

#### EcomID Architecture
- IdentityNet trained on 2M portrait images
- 68-point facial keypoint extraction
- 5 pose angles support: front, left, right, up, down
- Grid layout for multi-pose output

#### Batch Processing
- ThreadPoolExecutor with configurable workers
- Priority queue (heapq-based)
- Automatic retry with exponential backoff
- Callback URL support for completion notification

#### Multi-GPU
- Real-time VRAM monitoring
- Load history tracking (last 10 operations)
- Automatic strategy selection
- Model tier classification

#### Memory Optimization
- xformers integration when available
- TF32 enabled for Ampere+ GPUs
- Channels-last memory format
- Aggressive garbage collection

---

## [0.3.0] - Phase 5 - 2024-12

### ✨ New Features
- IP-Adapter integration
- InstantID face swap
- Inpaint Anything (SAM + LaMa)
- Enhanced InstructPix2Pix
- Qwen-Image-Edit 20B
- Step1X-Edit reasoning
- LoRA Training
- Anime ControlNet

---

## [0.2.0] - Phase 3-4 - 2024-11

### ✨ New Features
- SDXL support
- ControlNet multi-type
- Web search integration
- Auto-tagging (WD14)
- Real-ESRGAN upscaling
- GFPGAN face restoration

---

## [0.1.0] - Initial Release - 2024-10

### ✨ Initial Features
- Text-to-Image generation
- Image-to-Image transformation
- Basic inpainting
- Gradio web UI
- REST API
