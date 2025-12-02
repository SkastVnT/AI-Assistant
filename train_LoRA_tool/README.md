# LoRA Training Tool v2.3.1

**Modern WebUI for LoRA Training with AI-powered config recommendations**

A comprehensive, production-ready tool for training LoRA (Low-Rank Adaptation) models for Stable Diffusion. Features WebUI interface, AI-powered dataset preparation, Redis caching, and NSFW-safe training.

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Gemini 2.0](https://img.shields.io/badge/AI-Gemini%202.0%20Flash-blue.svg)](https://ai.google.dev/)
[![Redis](https://img.shields.io/badge/cache-Redis-red.svg)](https://redis.io/)

---

## 🚀 Quick Start

```bash
# 1. Setup (one-time)
bin\setup.bat

# 2. Start WebUI with Redis
bin\start_webui_with_redis.bat

# 3. Open browser
http://127.0.0.1:7860
```

**See [QUICK_START.md](QUICK_START.md) for detailed guide.**

---

## 🌟 Key Features

### 🌐 WebUI Interface
- **Modern Dark Theme** - Professional Stable Diffusion-style UI
- **Real-Time Monitoring** - Live training progress via Socket.IO
- **Interactive Charts** - Loss and LR visualization
- **Dataset Tools** - Resize, convert, deduplicate, validate
- **One-Click Training** - Start from browser
- **Remote Access** - Monitor from any device

### 🤖 AI-Powered
- **Gemini 2.0 Flash** - AI config recommendations (FREE tier!)
- **Smart Hyperparameters** - Optimal LR, epochs, network dim
- **Privacy-Safe NSFW** - Metadata-only approach (no images sent!)
- **Auto Analysis** - Dataset quality scoring
- **Cost Effective** - ~70% API savings with Redis caching

### 🛠️ Dataset Tools
- **🖼️ Resize Images** - Batch resize to 512x512, 768x768, etc.
- **🔄 Convert Format** - PNG → WebP/JPG (50% size reduction)
- **🗑️ Remove Duplicates** - Auto-detect and remove
- **📁 Organize** - Auto-organize by resolution
- **✅ Validate** - Check corrupted images, missing captions

### 🔒 NSFW Training
- **WD14 Tagger** - Local tagging (100% offline)
- **Privacy-First** - Images never leave your PC
- **Gemini Compatible** - Use AI with NSFW safely (metadata only!)
- **See**: [docs/NSFW_TRAINING_GUIDE.md](docs/NSFW_TRAINING_GUIDE.md)

### ⚡ Performance
- **Redis Caching** - 70% faster with intelligent caching
- **Task Queue** - FIFO job scheduling
- **Persistent State** - Resume after crashes
- **Real-time Updates** - Pub/Sub live progress

### 🎯 Advanced Training
- **LoRA+** - 2-3x faster convergence
- **Min-SNR Gamma** - Better loss weighting
- **Prodigy Optimizer** - Adaptive learning rates
- **EMA** - Smoother training
- **Multi-Resolution** - Aspect ratio bucketing
---

## 📁 Project Structure

```
train_LoRA_tool/
├── bin/                    # 🚀 Executable scripts
│   ├── setup.bat/sh        # One-time environment setup
│   ├── start_webui_with_redis.bat/sh  # Start WebUI + Redis
│   ├── stop_redis.bat/sh   # Stop Redis container
│   └── README.md           # Script documentation
├── docs/                   # 📚 Documentation
│   ├── README.md           # Documentation index
│   ├── changelog/          # Version histories
│   ├── archive/            # Deprecated docs
│   ├── QUICK_START.md      # ⭐ Start here
│   ├── WEBUI_GUIDE.md      # WebUI usage
│   ├── GEMINI_INTEGRATION.md
│   ├── REDIS_INTEGRATION.md
│   └── NSFW_TRAINING_GUIDE.md
├── configs/                # ⚙️ Training configurations
├── utils/                  # 🛠️ Core utilities
│   ├── config_recommender.py  # AI recommendations
│   ├── dataset_tools.py       # Image processing
│   └── redis_manager.py       # Caching
├── webui/                  # 🌐 Web interface
│   ├── templates/
│   └── static/
├── webui.py                # 🖥️ WebUI server
├── train_network.py        # 🎯 Core training
└── requirements.txt        # 📦 Dependencies
```

---

## 📋 Requirements

**Minimum:**
- Python 3.8 or higher
- CUDA-capable GPU with 8GB+ VRAM
- 20GB free disk space
- Windows 10/11, Linux, or macOS

**Recommended:**
- Python 3.10+
- NVIDIA GPU with 12GB+ VRAM (RTX 3060/4060 or better)
- 50GB free SSD space
- Windows 11 or Ubuntu 22.04

---

## 📖 Documentation

| Document | Description |
|----------|-------------|
| **[QUICK_START.md](QUICK_START.md)** | ⭐ Start here - Complete setup guide |
| **[docs/WEBUI_GUIDE.md](docs/WEBUI_GUIDE.md)** | WebUI features and usage |
| **[docs/GEMINI_INTEGRATION.md](docs/GEMINI_INTEGRATION.md)** | AI-powered features |
| **[docs/REDIS_INTEGRATION.md](docs/REDIS_INTEGRATION.md)** | Caching and performance |
| **[docs/NSFW_TRAINING_GUIDE.md](docs/NSFW_TRAINING_GUIDE.md)** | Safe NSFW training |
| **[docs/FEATURES.md](docs/FEATURES.md)** | Complete feature list |
| **[docs/ADVANCED_FEATURES.md](docs/ADVANCED_FEATURES.md)** | Advanced training |
| **[docs/](docs/)** | All documentation index |

---

## 💻 Usage

### First-Time Setup
```bash
# 1. Setup environment (installs PyTorch, dependencies)
bin\setup.bat

# 2. Configure Gemini API (optional but recommended)
# Add to .env file:
GOOGLE_API_KEY=your_gemini_api_key_here

# 3. Setup WD14 Tagger (for NSFW/offline tagging)
bin\setup_wd14.bat
```

### Start WebUI
```bash
# Option A: With Redis (recommended, 70% faster)
bin\start_webui_with_redis.bat

# Option B: Without Redis
bin\start_webui.bat

# Access at: http://127.0.0.1:7860
```

### WebUI Workflow
1. **Dataset Tab**: Upload images, select folder
2. **Tools Tab**: Resize, convert, validate dataset
3. **Model Tab**: Select base model
4. **Training Tab**: Click "Get AI-Powered Config"
5. **Start Training**: Monitor in real-time

### Command Line Training
```bash
# Activate environment
lora\Scripts\activate

# Train with AI-recommended config
python train_network.py --config configs/lora_config_recommended.yaml

# Train small dataset (20-100 images)
python train_network.py --config configs/lora_config_small.yaml

# Train large dataset (500+ images)  
python train_network.py --config configs/lora_config_large.yaml
```

---
---

## 💡 Example Use Cases

### Character Training (Anime/Person)
Perfect for: Anime characters, specific people, mascots

**Settings:**
- Network Dim: 32-64
- Epochs: 10-15
- Learning Rate: 1e-4
- Dataset: 50-200 images

**Usage:**
```
<lora:character_name:0.8> 1girl, red hair, blue eyes
```

### Style Training (Artistic)
Perfect for: Art styles, rendering techniques

**Settings:**
- Network Dim: 64-128
- Epochs: 15-20
- Learning Rate: 5e-5
- Dataset: 100-500 images

**Usage:**
```
<lora:style_name:0.7> landscape, sunset, watercolor style
```

### Concept Training (Objects)
Perfect for: Specific objects, props, concepts

**Settings:**
- Network Dim: 16-32
- Epochs: 10-15
- Learning Rate: 1e-4
- Dataset: 30-100 images

**Usage:**
```
<lora:object_name:0.6> futuristic car, cyberpunk style
```

---
python -m utils.preprocessing --data_dir data/train --action caption --prefix "a photo of sks person"

# Split dataset into train/val (optional)
python -m utils.preprocessing --data_dir data/all_images --action split --val_ratio 0.1
```

### 5. Configure Training

Choose a configuration based on your dataset size:

**AI-Recommended Config (Best for most cases):**
```bash
# Use config generated by Gemini AI
python scripts/training/train_lora.py --config configs/ai_config.yaml
```

## 🛠️ Advanced Features

### Resume Training
```bash
# Resume from latest checkpoint
lora\Scripts\activate
python train_network.py --config configs/my_config.yaml --resume

# Resume from specific epoch
python train_network.py --config configs/my_config.yaml --resume output/checkpoint-epoch-5.safetensors
```

### LoRA Analysis & Tools
```bash
# Analyze trained LoRA
python utils/analyze_lora.py output/lora_models/my_lora.safetensors

# Merge multiple LoRAs
python utils/merge_lora.py --loras lora1.safetensors lora2.safetensors --output merged.safetensors

# Convert formats
python utils/convert_lora.py --input model.pt --output model.safetensors
```

### Batch Processing
```bash
# Train multiple configs
python utils/batch_train.py --configs config1.yaml config2.yaml

# Benchmark different settings
python utils/benchmark.py --dataset data/train --variations lr,network_dim
```

---
├── utils/                      # Utility modules
│   ├── dataset_loader.py       # Dataset loading
│   ├── preprocessing.py        # Dataset preprocessing
│   ├── logger.py               # Logging utilities
│   ├── model_utils.py          # Model loading/saving
│   ├── lora_layers.py          # LoRA implementation
│   └── training_utils.py       # Training functions
├── train_lora.py               # Main training script
├── requirements.txt            # Python dependencies
├── setup.bat                   # Setup script (Windows)
├── train.bat                   # Training script (Windows)
└── README.md                   # This file
```

## ⚙️ Configuration Guide

### Key Parameters

**LoRA Settings:**
- `rank`: LoRA rank (4-128). Higher = more capacity but slower training
  - Small dataset: 8-16
  - Large dataset: 16-32
  - SDXL: 32-64
- `alpha`: LoRA alpha (typically 2x rank)
- `dropout`: Dropout rate for regularization (0.0-0.2)

**Training Settings:**
- `num_train_epochs`: Number of epochs
  - Small dataset: 15-20
  - Large dataset: 8-12
- `train_batch_size`: Batch size per GPU (usually 1-2)
- `gradient_accumulation_steps`: Accumulate gradients for larger effective batch size
- `learning_rate`: Learning rate
  - Small dataset: 5e-5 to 1e-4
  - Large dataset: 1e-4 to 2e-4

**Advanced Settings:**
- `mixed_precision`: "fp16" or "bf16" for faster training
- `gradient_checkpointing`: Save memory at cost of speed
- `enable_xformers`: Enable memory efficient attention
- `noise_offset`: Improves contrast (0.0-0.1)
- `snr_gamma`: Min-SNR weighting for better quality (5.0 recommended)

## 🎯 Training Tips

### For Character/Person Training:
- Use 20-50 varied images
- Include different angles, expressions, lighting
- Caption format: `"a photo of [trigger] person, [description]"`
- Example: `"a photo of sks person, smiling, outdoors"`
- Recommended rank: 8-16

### For Style Training:
- Use 100-500 images in consistent style
- Caption format: `"[description] in [trigger] style"`
- Example: `"landscape in watercolor style"`
- Recommended rank: 16-32

### For Concept Training:
- Use 50-200 images of the concept
- Diverse backgrounds and contexts
- Caption format: `"a photo of [trigger] [object]"`
- Example: `"a photo of custom car"`
- Recommended rank: 16-24

## 📊 Monitoring Training

### WebUI Real-Time Monitoring
- **Live Loss Chart** - Track training progress visually
- **Learning Rate Graph** - Monitor LR schedule
- **Live Logs** - Real-time training output
- **Sample Generation** - View test images during training

### TensorBoard (optional):
```bash
# Enable in config
use_tensorboard: true

# View
tensorboard --logdir outputs/tensorboard
```

---

## 🔧 Troubleshooting

### Out of Memory (OOM):
- Reduce `train_batch_size` to 1
- Increase `gradient_accumulation_steps`
- Enable `gradient_checkpointing: true`
- Reduce `resolution` (512 → 384)

### Training Too Slow:
- Enable `mixed_precision: "fp16"`
- Enable `cache_latents: true`
- Install xformers: `pip install xformers`

### Poor Quality Results:
- Increase epochs or adjust learning rate
- Enable `snr_gamma: 5.0`
- Improve dataset quality
- Use AI recommendations (click "Get AI-Powered Config")

### Redis Issues:
- Ensure Docker is running
- Restart Redis: `bin\stop_redis.bat` then `bin\start_webui_with_redis.bat`
- Or use WebUI without Redis: `bin\start_webui.bat`

---

## 🎨 Using Trained LoRA

### In Stable Diffusion WebUI (AUTOMATIC1111):
1. Copy `output/lora_models/final_model.safetensors` to `stable-diffusion-webui/models/Lora/`
2. In prompt: `<lora:final_model:0.8> your prompt here`
3. Adjust weight (0.5-1.2) as needed

### In ComfyUI:
1. Copy LoRA to `ComfyUI/models/loras/`
2. Use "Load LoRA" node
3. Set strength (0.5-1.2)

### In Code:
```python
from diffusers import StableDiffusionPipeline

pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5")
pipe.load_lora_weights("output/lora_models/final_model.safetensors")

image = pipe("your prompt", num_inference_steps=30).images[0]
```

---
## 📊 Training Statistics

| Configuration | GPU | Dataset | Training Time | Model Size |
|--------------|-----|---------|---------------|------------|
| SD 1.5, Rank 16 | RTX 3090 | 100 images | 1-2 hours | ~20MB |
| SD 1.5, Rank 32 | RTX 3090 | 500 images | 3-5 hours | ~40MB |
| SDXL, Rank 32 | RTX 4090 | 100 images | 4-6 hours | ~80MB |
| SDXL, Rank 64 | RTX 4090 | 500 images | 8-10 hours | ~160MB |

---

## 🌟 What's New in v2.3.1

### WebUI Features
- ✨ Modern dark theme interface
- ⚡ Real-time Socket.IO monitoring
- 🛠️ Dataset processing tools
- 🤖 AI-powered config recommendations
- 📊 Interactive charts and metrics

### Redis Integration
- ⚡ 70% faster AI recommendations (caching)
- 🔄 Task queue for job scheduling
- 💾 Persistent session management
- 📈 Training metrics logging

### Dataset Tools
- 🖼️ Batch resize images
- 🔄 Format conversion (PNG → WebP/JPG)
- 🗑️ Duplicate detection and removal
- 📁 Auto-organization by resolution
- ✅ Dataset validation

### NSFW Training
- 🔒 100% privacy-safe workflow
- 🏷️ Local WD14 tagging
- 🤖 Metadata-only Gemini recommendations
- 📝 Complete NSFW guide

See [docs/changelog/CHANGELOG_v2.3.1.md](docs/changelog/CHANGELOG_v2.3.1.md) for full changelog.

---

MIT License - Part of AI-Assistant suite. See [LICENSE](LICENSE) for details.

---

## 🙏 Credits

- **Kohya-ss** - Original LoRA training scripts
- **Hugging Face** - Diffusers library
- **Google DeepMind** - Gemini 2.0 Flash AI
- **WD14 Tagger** - SmilingWolf's anime tagging model
- **Redis Labs** - High-performance caching
- **Community** - Feedback and contributions

---

## 📞 Support

- **Documentation**: [docs/README.md](docs/README.md)
- **Quick Start**: [QUICK_START.md](QUICK_START.md)
- **Scripts**: [bin/README.md](bin/README.md)
- **Issues**: GitHub Issues
- **Discussions**: GitHub Discussions

---

**Made with ❤️ for the Stable Diffusion community**

**Happy Training! 🎨✨**
