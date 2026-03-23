# LoRA Training Tool - Complete Guide

## 📋 Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [Dataset Preparation](#dataset-preparation)
5. [Configuration](#configuration)
6. [Training](#training)
7. [Utilities](#utilities)
8. [Best Practices](#best-practices)
9. [FAQ](#faq)
10. [Troubleshooting](#troubleshooting)

---

## 1. Introduction

### What is LoRA?

LoRA (Low-Rank Adaptation) is a technique for fine-tuning large models efficiently by training only small adapter layers instead of the entire model. This tool provides a comprehensive solution for training LoRA models on Stable Diffusion.

### Key Benefits

- 🚀 **Fast Training**: Train in hours instead of days
- 💾 **Low Storage**: LoRA models are 2-200MB vs. 2-7GB for full models
- 🎯 **Precise Control**: Fine-tune specific concepts, styles, or characters
- 💰 **Cost Effective**: Works on consumer GPUs (8GB+ VRAM)

### System Requirements

**Minimum:**
- GPU: 8GB VRAM (NVIDIA recommended)
- RAM: 16GB
- Storage: 20GB free space
- OS: Windows 10/11, Linux, or macOS

**Recommended:**
- GPU: 12GB+ VRAM (RTX 3060/4060 or better)
- RAM: 32GB
- Storage: 50GB+ SSD
- OS: Windows 11 or Ubuntu 22.04

---

## 2. Installation

### Step 1: Prerequisites

Install Python 3.8 or higher:
```bash
# Check Python version
python --version
```

If not installed, download from [python.org](https://www.python.org/downloads/)

### Step 2: Clone/Download

```bash
# If using git
git clone https://github.com/YourRepo/AI-Assistant.git
cd AI-Assistant/train_LoRA_tool

# Or download and extract the ZIP file
```

### Step 3: Run Setup

**Windows:**
```bash
setup.bat
```

**Linux/Mac:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 4: Verify Installation

```bash
# Activate environment
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Test imports
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import diffusers; print('Diffusers:', diffusers.__version__)"
```

### Optional: Install CUDA-optimized packages

```bash
# For NVIDIA GPUs
pip install xformers
pip install bitsandbytes
```

---

## 3. Quick Start

### Option A: Interactive Quick Start (Recommended for beginners)

```bash
quickstart.bat
```

This will guide you through:
1. Environment setup
2. Dataset validation
3. Configuration selection
4. Training launch

### Option B: Manual Quick Start

**1. Prepare Dataset:**
```bash
# Create directory structure
mkdir -p data/train

# Add your images
# Each image should have a .txt caption file
# Example:
#   data/train/image1.jpg
#   data/train/image1.txt (contains: "a photo of sks person, smiling")
```

**2. Validate Dataset:**
```bash
python -m utils.preprocessing --data_dir data/train --action validate --fix
```

**3. Start Training:**
```bash
train.bat

# Or with specific config
python train_lora.py --config configs/default_config.yaml
```

**4. Monitor Progress:**
- Check logs: `outputs/logs/training_*.log`
- View samples: `outputs/samples/`
- Check models: `outputs/lora_models/`

---

## 4. Dataset Preparation

### 4.1 Image Requirements

**Quality Standards:**
- Resolution: 512x512 minimum (768x768+ recommended)
- Format: JPG, PNG, WEBP (PNG preferred for quality)
- No watermarks or heavy compression
- Clear, well-lit subjects
- Variety in poses/angles/lighting

**Quantity Guidelines:**

| Use Case | Images | Training Time | Expected Quality |
|----------|--------|---------------|------------------|
| Character/Person | 20-50 | 2-4 hours | Excellent |
| Art Style | 100-500 | 4-8 hours | Very Good |
| Concept/Object | 50-200 | 3-6 hours | Good |
| General Fine-tune | 500-2000 | 8-16 hours | Variable |

### 4.2 Caption Format

**Template:**
```
[trigger_word] [subject], [description], [quality_tags]
```

**Examples:**

**Character Training:**
```
a photo of sks person, smiling, professional photography, high quality
a photo of sks person, portrait, natural lighting, detailed
a photo of sks person, full body, casual clothes, outdoors
```

**Style Training:**
```
landscape in watercolor style, mountains, detailed brushstrokes
portrait in anime style, vibrant colors, expressive eyes
architecture in cyberpunk style, neon lights, futuristic
```

**Object Training:**
```
a photo of xyz car, red sports car, side view, high detail
a photo of xyz furniture, modern chair, professional photo
```

### 4.3 Caption Generation

**Manual Captioning:**
- Most control and accuracy
- Time-consuming for large datasets
- Best for specialized concepts

**Auto-Captioning with BLIP:**
```bash
python -m utils.preprocessing --data_dir data/train --action caption --prefix "a photo of sks person"
```

**Tips:**
- Add trigger word prefix
- Review and refine generated captions
- Ensure consistency across dataset

### 4.4 Dataset Validation

```bash
# Interactive validation
preprocess.bat

# Command line
python -m utils.preprocessing --data_dir data/train --action validate --fix
```

**What it checks:**
- ✅ Corrupted images
- ✅ Invalid formats
- ✅ Resolution issues
- ✅ Missing captions
- ✅ File consistency

### 4.5 Dataset Splitting

```bash
python -m utils.preprocessing --data_dir data/all_images --action split --val_ratio 0.1
```

This creates:
- `data/all_images_train/` (90% of images)
- `data/all_images_val/` (10% of images)

---

## 5. Configuration

### 5.1 Choosing a Preset

**Small Dataset (500-1000 images):**
```bash
copy configs\small_dataset_config.yaml configs\my_config.yaml
```
- Lower rank (8-16) to prevent overfitting
- More epochs (15-20)
- Higher regularization

**Medium Dataset (1000-1500 images):**
```bash
copy configs\default_config.yaml configs\my_config.yaml
```
- Balanced settings
- Standard rank (16)
- Moderate epochs (10-15)

**Large Dataset (1500-2000+ images):**
```bash
copy configs\large_dataset_config.yaml configs\my_config.yaml
```
- Higher rank (24-32)
- Fewer epochs (8-12)
- Faster learning rate

**SDXL Training:**
```bash
copy configs\sdxl_config.yaml configs\my_config.yaml
```
- 1024x1024 resolution
- Higher rank (32-64)
- BF16 precision

### 5.2 Key Parameters

**LoRA Settings:**
```yaml
lora:
  rank: 16              # 4-128, higher = more capacity
  alpha: 32             # Usually 2x rank
  dropout: 0.0          # 0-0.2, regularization
  target_modules:       # Which layers to adapt
    - "to_q"
    - "to_k"
    - "to_v"
    - "to_out.0"
```

**Training Settings:**
```yaml
training:
  num_train_epochs: 10
  train_batch_size: 1
  gradient_accumulation_steps: 4
  learning_rate: 1.0e-4
  lr_scheduler: "cosine"
  mixed_precision: "fp16"
```

**Dataset Settings:**
```yaml
dataset:
  train_data_dir: "data/train"
  resolution: 512
  center_crop: true
  random_flip: true
```

### 5.3 Advanced Settings

**Quality Improvements:**
```yaml
advanced:
  snr_gamma: 5.0          # Min-SNR weighting
  noise_offset: 0.05      # Better contrast
  use_ema: true           # Smoother results
  enable_xformers: true   # Memory efficiency
```

**Memory Optimization:**
```yaml
training:
  gradient_checkpointing: true
  mixed_precision: "fp16"
  train_batch_size: 1
  gradient_accumulation_steps: 8
```

---

## 6. Training

### 6.1 Start Training

**Interactive:**
```bash
train.bat
```

**Command Line:**
```bash
python train_lora.py --config configs/my_config.yaml
```

**With Specific GPU:**
```bash
set CUDA_VISIBLE_DEVICES=0
python train_lora.py --config configs/my_config.yaml
```

### 6.2 Monitor Training

**Check Logs:**
```bash
# View latest log
type outputs\logs\training_*.log

# Monitor in real-time
Get-Content outputs\logs\training_*.log -Wait  # PowerShell
tail -f outputs/logs/training_*.log             # Linux/Mac
```

**TensorBoard (Optional):**
```bash
# Enable in config
logging:
  use_tensorboard: true

# Launch TensorBoard
tensorboard --logdir outputs/tensorboard
```

**Wandb (Optional):**
```bash
# Enable in config
logging:
  use_wandb: true
  wandb_project: "my-lora-training"

# Login first
wandb login
```

### 6.3 Training Progress

**What to look for:**
- Loss should steadily decrease
- Validation loss (if enabled) should follow training loss
- Generated samples should improve over epochs
- No NaN or infinite values

**Expected Training Times:**

| Configuration | GPU | Dataset Size | Time |
|--------------|-----|--------------|------|
| SD 1.5, rank 16 | RTX 3090 | 500 images | 2-3 hours |
| SD 1.5, rank 16 | RTX 4090 | 1000 images | 4-5 hours |
| SDXL, rank 32 | RTX 3090 | 500 images | 6-8 hours |
| SDXL, rank 32 | RTX 4090 | 1000 images | 8-10 hours |

### 6.4 Resume Training

**Find Latest Checkpoint:**
```bash
python resume_training.py
```

**Resume from Checkpoint:**
```bash
python train_lora.py --config configs/my_config.yaml --resume outputs/checkpoints/checkpoint_epoch_5.pt
```

---

## 7. Utilities

### 7.1 Generate Samples

**Basic Generation:**
```bash
python generate_samples.py --lora_path outputs/lora_models/final_model.safetensors --prompts "a photo of sks person" "portrait of sks person"
```

**From Prompt File:**
```bash
python generate_samples.py --lora_path outputs/lora_models/final_model.safetensors --prompts_file prompts/character_prompts.txt
```

**Comparison Grid:**
```bash
python generate_samples.py --lora_path outputs/lora_models/final_model.safetensors --comparison_grid
```

**Batch Generation:**
```bash
batch_generate.bat
```

### 7.2 Analyze LoRA

**Basic Analysis:**
```bash
python analyze_lora.py outputs/lora_models/final_model.safetensors
```

**Detailed Analysis:**
```bash
python analyze_lora.py outputs/lora_models/final_model.safetensors --detailed --weights
```

**Compare Two LoRAs:**
```bash
python analyze_lora.py lora1.safetensors --compare lora2.safetensors
```

### 7.3 Merge LoRAs

**Merge Multiple LoRAs:**
```bash
python merge_lora.py merge_loras --loras lora1.safetensors lora2.safetensors --weights 0.7 0.3 --output merged.safetensors
```

**Merge into Base Model:**
```bash
python merge_lora.py merge_to_base --base_model base.safetensors --lora my_lora.safetensors --output merged_model.safetensors --alpha 1.0
```

### 7.4 Format Conversion

**Safetensors to PyTorch:**
```bash
python convert_lora.py st2pt --input model.safetensors --output model.pt
```

**PyTorch to Safetensors:**
```bash
python convert_lora.py pt2st --input model.pt --output model.safetensors
```

**Resize Rank:**
```bash
python convert_lora.py resize --input lora32.safetensors --output lora16.safetensors --rank 16
```

### 7.5 Utilities Menu

**Interactive Menu (Windows):**
```bash
utilities.bat
```

---

## 8. Best Practices

### 8.1 Dataset Quality

✅ **DO:**
- Use high-quality, clear images
- Ensure variety in dataset
- Write descriptive, consistent captions
- Include trigger word in every caption
- Validate dataset before training

❌ **DON'T:**
- Use low-resolution images
- Mix different concepts in one dataset
- Skip caption files
- Use heavily compressed images
- Include watermarked images

### 8.2 Training Configuration

**For Character/Person:**
```yaml
lora:
  rank: 16
  alpha: 32
dataset:
  train_data_dir: "data/character"
  resolution: 512
training:
  num_train_epochs: 15
  learning_rate: 8.0e-5
```

**For Art Style:**
```yaml
lora:
  rank: 32
  alpha: 64
dataset:
  train_data_dir: "data/style"
  resolution: 768
training:
  num_train_epochs: 12
  learning_rate: 1.2e-4
```

### 8.3 Preventing Overfitting

**Signs:**
- Perfect replication, no variation
- Model ignores prompts
- Poor quality on new concepts

**Solutions:**
- Reduce LoRA rank
- Add dropout: `dropout: 0.1`
- Reduce epochs
- Increase dataset size
- Use validation split

### 8.4 Preventing Underfitting

**Signs:**
- Model doesn't learn trigger
- Poor quality outputs
- Inconsistent results

**Solutions:**
- Increase LoRA rank
- Increase epochs
- Increase learning rate
- Check caption quality
- Ensure dataset consistency

---

## 9. FAQ

**Q: How many images do I need?**
A: Minimum 20-30 for simple concepts, 100-500 for styles, 500+ for comprehensive training.

**Q: How long does training take?**
A: 2-8 hours on average, depending on dataset size and GPU.

**Q: Can I use CPU?**
A: Yes, but it will be 10-50x slower. GPU is highly recommended.

**Q: What's a good trigger word?**
A: Use unique, uncommon words like "sks", "xyz", "abc123" to avoid conflicts.

**Q: Can I train multiple concepts?**
A: Yes, but train them separately and merge later for best results.

**Q: How do I use the trained LoRA?**
A: Copy to `stable-diffusion-webui/models/Lora/` and use `<lora:name:weight>` in prompts.

**Q: What's the difference between rank values?**
A: Higher rank = more capacity but slower and larger. Start with 16.

**Q: Should I use validation split?**
A: Yes for datasets >200 images to monitor overfitting.

**Q: Can I resume failed training?**
A: Yes, use `resume_training.py` to find checkpoints.

**Q: How do I reduce VRAM usage?**
A: Enable gradient checkpointing, reduce batch size, lower resolution.

---

## 10. Troubleshooting

### Out of Memory (OOM)

**Solutions:**
1. Reduce `train_batch_size` to 1
2. Enable `gradient_checkpointing: true`
3. Reduce `resolution` (512 → 384)
4. Enable `enable_xformers: true`
5. Close other GPU applications

### Training Very Slow

**Solutions:**
1. Enable `mixed_precision: "fp16"`
2. Enable `cache_latents: true`
3. Install xformers: `pip install xformers`
4. Increase `dataloader_num_workers`
5. Use SSD for dataset

### Loss Not Decreasing

**Solutions:**
1. Increase learning rate
2. Check dataset quality
3. Verify captions are correct
4. Reduce gradient accumulation
5. Try different optimizer

### NaN or Infinite Loss

**Solutions:**
1. Reduce learning rate
2. Enable gradient clipping: `max_grad_norm: 1.0`
3. Check for corrupted images
4. Use `mixed_precision: "fp16"`

### Poor Quality Results

**Solutions:**
1. Increase training epochs
2. Enable `snr_gamma: 5.0`
3. Add `noise_offset: 0.05`
4. Improve caption quality
5. Increase dataset size

### Model Doesn't Learn Trigger

**Solutions:**
1. Ensure trigger in ALL captions
2. Make trigger unique and consistent
3. Increase training epochs
4. Check caption format
5. Verify dataset loading

---

## Additional Resources

- **Main README**: `README.md`
- **Advanced Guide**: `ADVANCED_GUIDE.md`
- **Feature List**: `FEATURES.md`
- **Example Configs**: `configs/`
- **Example Prompts**: `prompts/`

## Support

For issues or questions:
1. Check this guide
2. Review troubleshooting section
3. Check logs in `outputs/logs/`
4. Open an issue on GitHub

---

**Happy Training! 🎨✨**
