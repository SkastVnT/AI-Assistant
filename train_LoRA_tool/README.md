# LoRA Training Tool for Stable Diffusion

A comprehensive, production-ready tool for training LoRA (Low-Rank Adaptation) models on image datasets. Optimized for Stable Diffusion fine-tuning with automatic dataset preparation, validation, and advanced training features.

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

## 🌟 Features

### Core Features
- **Flexible Dataset Support**: Works with image datasets ranging from 20 to 2000+ images
- **Automatic Captioning**: Built-in BLIP-based auto-captioning for images
- **Dataset Validation**: Automatic detection and fixing of corrupted/invalid images
- **Multiple Configurations**: Pre-configured settings for small/large datasets and SDXL
- **Memory Efficient**: Gradient checkpointing, mixed precision, and xformers support
- **Advanced Training**: SNR weighting, noise offset, EMA, prior preservation, and more
- **Easy to Use**: Simple configuration files and batch scripts for Windows

### Advanced Features
- 🔄 **Resume Training**: Continue from any checkpoint
- 🎨 **Sample Generation**: Generate test images during/after training
- 📊 **LoRA Analysis**: Detailed model inspection and comparison
- 🔗 **LoRA Merging**: Merge multiple LoRAs or merge into base model
- 🔧 **Format Conversion**: Convert between safetensors and PyTorch formats
- 📈 **Benchmarking**: Compare different configurations automatically
- 📝 **Comprehensive Logging**: TensorBoard and Wandb support

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

## 📚 Documentation

- **[Complete Guide](docs/GUIDE.md)** - Step-by-step tutorial for all features
- **[Advanced Guide](ADVANCED_GUIDE.md)** - Advanced techniques and optimization
- **[Feature List](FEATURES.md)** - Complete list of all 80+ features
- **[Quick Reference](#)** - Command reference and examples

## 🚀 Quick Start

### 1. Installation

```bash
# Clone or navigate to the tool directory
cd train_LoRA_tool

# Run setup script (Windows)
setup.bat

# Or manually install
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Prepare Your Dataset

```
data/
├── train/
│   ├── image1.jpg
│   ├── image1.txt          # Caption file (optional)
│   ├── image2.png
│   ├── image2.txt
│   └── ...
└── val/                    # Optional validation set
    ├── val_image1.jpg
    └── ...
```

**Caption Format:**
- Each image should have a corresponding `.txt` file with the same name
- Example: `portrait001.jpg` → `portrait001.txt`
- Caption content: `"a photo of sks person, professional lighting, high quality"`

### 3. Validate and Prepare Dataset

```bash
# Validate images
python -m utils.preprocessing --data_dir data/train --action validate --fix

# Auto-generate captions (optional)
python -m utils.preprocessing --data_dir data/train --action caption --prefix "a photo of sks person"

# Split dataset into train/val (optional)
python -m utils.preprocessing --data_dir data/all_images --action split --val_ratio 0.1
```

### 4. Configure Training

Choose a configuration based on your dataset size:

**Small Dataset (500-1000 images):**
```bash
copy configs\small_dataset_config.yaml configs\my_config.yaml
```

**Medium Dataset (1000-1500 images):**
```bash
copy configs\default_config.yaml configs\my_config.yaml
```

**Large Dataset (1500-2000+ images):**
```bash
copy configs\large_dataset_config.yaml configs\my_config.yaml
```

**SDXL Training:**
```bash
copy configs\sdxl_config.yaml configs\my_config.yaml
```

Edit `configs/my_config.yaml` to adjust:
- Dataset paths
## 📁 Directory Structure

```
train_LoRA_tool/
├── configs/                    # Configuration files
│   ├── default_config.yaml
│   ├── small_dataset_config.yaml
│   ├── large_dataset_config.yaml
│   └── sdxl_config.yaml
├── data/                       # Your datasets
│   ├── train/                  # Training images
│   └── val/                    # Validation images (optional)
├── docs/                       # Documentation
│   └── GUIDE.md                # Complete guide
├── scripts/                    # Helper scripts
├── prompts/                    # Sample prompts
│   ├── character_prompts.txt
│   └── style_prompts.txt
├── outputs/                    # Training outputs (auto-created)
│   ├── lora_models/            # Trained LoRA models
│   ├── checkpoints/            # Training checkpoints
│   ├── logs/                   # Training logs
│   └── samples/                # Generated samples
├── utils/                      # Core utilities
│   ├── dataset_loader.py
│   ├── preprocessing.py
│   ├── logger.py
│   ├── model_utils.py
│   ├── lora_layers.py
│   └── training_utils.py
├── train_lora.py               # Main training script
├── resume_training.py          # Resume from checkpoint
├── generate_samples.py         # Generate test images
├── analyze_lora.py             # Analyze LoRA models
├── merge_lora.py               # Merge LoRAs
├── convert_lora.py             # Format conversion
├── benchmark.py                # Training benchmark
├── requirements.txt            # Dependencies
├── setup.bat                   # Setup (Windows)
├── train.bat                   # Training launcher
├── quickstart.bat              # Interactive guide
├── preprocess.bat              # Preprocessing menu
├── utilities.bat               # Utilities menu
├── batch_generate.bat          # Batch generation
├── README.md                   # This file
├── ADVANCED_GUIDE.md           # Advanced guide
├── FEATURES.md                 # Feature list
└── .gitignore                  # Git ignore rules
``` ├── checkpoints/            # Training checkpoints
│   ├── logs/                   # Training logs
│   └── samples/                # Generated samples (optional)
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

### Check Logs:
```bash
# View latest log
type outputs\logs\training_*.log
```

### TensorBoard (optional):
```bash
# Enable in config
use_tensorboard: true

# View
tensorboard --logdir outputs/tensorboard
```

### Wandb (optional):
```bash
# Enable in config
use_wandb: true
wandb_project: "my-lora-training"

# Login
wandb login
```

## 🔧 Troubleshooting

### Out of Memory (OOM):
1. Reduce `train_batch_size` to 1
2. Increase `gradient_accumulation_steps`
3. Enable `gradient_checkpointing: true`
4. Reduce `resolution` (e.g., 512 → 384)
5. Enable `enable_xformers: true`

### Training Too Slow:
1. Enable `mixed_precision: "fp16"`
2. Enable `cache_latents: true`
3. Increase `dataloader_num_workers`
4. Install xformers: `pip install xformers`

### Poor Quality Results:
1. Increase number of epochs
2. Adjust learning rate (try 5e-5 to 2e-4)
3. Enable `snr_gamma: 5.0`
4. Add `noise_offset: 0.05`
5. Increase dataset size or quality

### Overfitting:
1. Reduce LoRA rank
2. Add dropout: `dropout: 0.1`
3. Increase weight decay
4. Use validation split
5. Reduce number of epochs

## 🎨 Using Trained LoRA

### In Stable Diffusion WebUI:
1. Copy `outputs/lora_models/final_model.safetensors` to `stable-diffusion-webui/models/Lora/`
2. In prompt, use: `<lora:final_model:0.8>`
3. Adjust weight (0.5-1.2) as needed

### In ComfyUI:
1. Copy LoRA to `ComfyUI/models/loras/`
2. Use "Load LoRA" node
3. Set strength (0.5-1.2)

### In Code:
```python
from diffusers import StableDiffusionPipeline
import torch

pipe = StableDiffusionPipeline.from_pretrained("runwayml/stable-diffusion-v1-5")
pipe.load_lora_weights("outputs/lora_models/final_model.safetensors")

image = pipe("a photo of sks person", num_inference_steps=30).images[0]
```

## 📖 Examples

### Example 1: Character LoRA
```yaml
dataset:
  train_data_dir: "data/character_photos"
  resolution: 512

lora:
  rank: 16
  alpha: 32

training:
  num_train_epochs: 15
  learning_rate: 1.0e-4

logging:
  sample_prompts:
    - "a photo of sks person"
    - "portrait of sks person"
    - "sks person smiling"
```

### Example 2: Art Style LoRA
```yaml
## 📊 Training Statistics

| Configuration | GPU | Dataset | Training Time | Model Size |
|--------------|-----|---------|---------------|------------|
| SD 1.5, Rank 16 | RTX 3090 | 500 images | 2-3 hours | ~20MB |
| SD 1.5, Rank 32 | RTX 3090 | 1000 images | 4-6 hours | ~40MB |
| SDXL, Rank 32 | RTX 4090 | 500 images | 6-8 hours | ~80MB |
| SDXL, Rank 64 | RTX 4090 | 1000 images | 10-12 hours | ~160MB |

## 🎯 Use Cases

### Character/Person Training
- **Images needed**: 20-50
- **Recommended rank**: 8-16
- **Training time**: 2-4 hours
- **Use for**: Consistent character generation, portrait styles

### Art Style Training  
- **Images needed**: 100-500
- **Recommended rank**: 16-32
- **Training time**: 4-8 hours
- **Use for**: Artistic style transfer, aesthetic consistency

### Concept/Object Training
- **Images needed**: 50-200
- **Recommended rank**: 16-24
- **Training time**: 3-6 hours
- **Use for**: Specific objects, products, clothing

## 🛠️ Included Tools

| Tool | Description | Usage |
|------|-------------|-------|
| `train_lora.py` | Main training script | Core training engine |
| `resume_training.py` | Resume from checkpoint | Continue interrupted training |
| `generate_samples.py` | Generate test images | Evaluate LoRA quality |
| `analyze_lora.py` | Analyze LoRA models | Inspect model details |
| `merge_lora.py` | Merge LoRAs | Combine multiple LoRAs |
| `convert_lora.py` | Format conversion | Convert between formats |
| `benchmark.py` | Training benchmark | Compare configurations |
| `preprocess.bat` | Preprocessing menu | Dataset preparation |
| `utilities.bat` | Utilities menu | All-in-one tool access |

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Ways to contribute:**
- 🐛 Report bugs and issues
- 💡 Suggest new features
- 📖 Improve documentation
- 🔧 Submit pull requests
- ⭐ Star the project!

## 📄 License

This project is part of the AI-Assistant suite. Licensed under MIT License - see [LICENSE](LICENSE) for details.

## 🙏 Acknowledgments

- [Diffusers](https://github.com/huggingface/diffusers) by HuggingFace - Diffusion models library
- [LoRA](https://arxiv.org/abs/2106.09685) paper by Microsoft - Original research
- [Stable Diffusion](https://github.com/Stability-AI/stablediffusion) by Stability AI - Base models
- [AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui) - WebUI integration
- [Kohya's Scripts](https://github.com/kohya-ss/sd-scripts) - Training inspiration

## 🌟 Star History

If you find this tool useful, please consider giving it a star! ⭐

## 📊 Project Stats

- **Total Features**: 80+
- **Python Scripts**: 17
- **Batch Scripts**: 6
- **Configurations**: 4
- **Lines of Code**: 5000+
- **Documentation Pages**: 4
    - "landscape in sks style"
    - "portrait in sks style"
    - "cityscape in sks style"
```

## 🤝 Contributing

Feel free to submit issues, feature requests, or pull requests!

## 📄 License

This project is part of the AI-Assistant suite. See LICENSE for details.

## 🙏 Acknowledgments

- [Diffusers](https://github.com/huggingface/diffusers) by HuggingFace
- [LoRA](https://arxiv.org/abs/2106.09685) paper by Microsoft
- [Stable Diffusion](https://github.com/Stability-AI/stablediffusion) by Stability AI
- [AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui) WebUI

## 🛠️ Advanced Features

### Resume Training
```bash
# Find latest checkpoint and resume
python resume_training.py

# Resume from specific checkpoint
python train_lora.py --config configs/my_config.yaml --resume outputs/checkpoints/checkpoint_epoch_5.pt
```

### Generate Samples
```bash
# Generate samples with trained LoRA
python generate_samples.py --lora_path outputs/lora_models/final_model.safetensors --prompts "a photo of sks person" "portrait of sks person"

# Generate comparison grid with different weights
python generate_samples.py --lora_path outputs/lora_models/final_model.safetensors --comparison_grid
```

### Analyze LoRA
```bash
# Basic analysis
python analyze_lora.py outputs/lora_models/final_model.safetensors

# Detailed analysis with weight distribution
python analyze_lora.py outputs/lora_models/final_model.safetensors --detailed --weights

# Compare two LoRAs
python analyze_lora.py lora1.safetensors --compare lora2.safetensors
```

### Merge LoRAs
```bash
# Merge multiple LoRAs with weighted average
python merge_lora.py merge_loras --loras lora1.safetensors lora2.safetensors --weights 0.7 0.3 --output merged.safetensors

# Merge LoRA into base model
python merge_lora.py merge_to_base --base_model base.safetensors --lora my_lora.safetensors --output merged_model.safetensors --alpha 1.0
```

### Convert Formats
```bash
# Convert safetensors to pytorch
python convert_lora.py st2pt --input model.safetensors --output model.pt

# Convert pytorch to safetensors
python convert_lora.py pt2st --input model.pt --output model.safetensors

# Resize LoRA rank
python convert_lora.py resize --input lora_rank32.safetensors --output lora_rank16.safetensors --rank 16
```

### Utilities Menu
```bash
# Interactive utilities menu (Windows)
utilities.bat
```

## 📞 Support

For issues or questions:
1. Check the troubleshooting section
2. Review configuration examples
3. Check logs in `outputs/logs/`
4. Open an issue on GitHub

---

**Happy Training! 🎨✨**
