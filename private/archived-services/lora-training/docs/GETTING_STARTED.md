# LoRA Training Tool - Getting Started

Welcome to the LoRA Training Tool! This guide will help you get started in 5 minutes.

## ⚡ Quick Setup (5 Minutes)

### Step 1: Install (2 minutes)

**Windows:**
```bash
# Double-click or run from terminal
scripts\setup\setup.bat
```

**Linux/Mac:**
```bash
python -m venv lora
source lora/bin/activate
pip install -r requirements.txt
```

### Step 2: Prepare Dataset (2 minutes)

1. **Create dataset folder:**
   ```bash
   mkdir -p data/train
   ```

2. **Add your images:**
   - Copy 20-2000 images to `data/train/`
   - Supported formats: JPG, PNG, WEBP

3. **Add captions (optional):**
   ```
   data/train/image1.jpg
   data/train/image1.txt  # Text file with description
   ```

   Or use auto-captioning:
   ```bash
   scripts\setup\preprocess.bat  # Windows
   # Select option: Auto-caption images
   ```

### Step 3: Start Training (1 minute)

**Easy way (Windows):**
```bash
scripts\setup\quickstart.bat
```
Follow the interactive wizard!

**Direct way:**
```bash
# Activate environment first
lora\Scripts\activate  # Windows
source lora/bin/activate  # Linux/Mac

# Start training
python scripts/training/train_lora.py --config configs/default_config.yaml
```

## 📊 What Happens During Training

```
Training Progress:
[=====>    ] 50% | Epoch 5/10 | Loss: 0.0342 | ETA: 1h 30m

Outputs Created:
✓ outputs/lora_models/      ← Your trained LoRA model
✓ outputs/checkpoints/      ← Resume points
✓ outputs/logs/             ← Training logs
✓ outputs/samples/          ← Test images (if enabled)
```

## 🎨 After Training - Generate Images

```bash
# Generate test images
python scripts/utilities/generate_samples.py \
  --lora_path outputs/lora_models/final_model.safetensors \
  --prompts "a photo of sks person, smiling"

# Or use batch script (Windows)
scripts\setup\batch_generate.bat
```

## 📁 Project Structure

```
train_LoRA_tool/
├── 📂 scripts/              ← All executable scripts
│   ├── setup/               ← Setup & launcher scripts
│   ├── training/            ← Training scripts
│   └── utilities/           ← Helper tools
├── 📂 configs/              ← Configuration presets
├── 📂 data/                 ← Your datasets
│   ├── train/               ← Training images HERE
│   └── val/                 ← Validation (optional)
├── 📂 outputs/              ← Training results (auto-created)
│   ├── lora_models/         ← Trained models
│   ├── checkpoints/         ← Resume points
│   ├── logs/                ← Training logs
│   └── samples/             ← Generated images
├── 📂 docs/                 ← Documentation
└── 📂 utils/                ← Core utilities
```

## 🔧 Configuration Presets

Choose based on your dataset size:

| Config File | Best For | Images | Rank | Epochs |
|------------|----------|--------|------|--------|
| `small_dataset_config.yaml` | Characters, Portraits | 20-1000 | 8-16 | 15-20 |
| `default_config.yaml` | General Use | 1000-1500 | 16 | 10-12 |
| `large_dataset_config.yaml` | Styles, Concepts | 1500-2000+ | 24-32 | 8-10 |
| `sdxl_config.yaml` | SDXL Models | Any | 32 | 10 |

**To use a preset:**
```bash
python scripts/training/train_lora.py --config configs/small_dataset_config.yaml
```

## ⚙️ Common Tasks

### Validate Dataset
```bash
# Windows
scripts\setup\preprocess.bat

# Linux/Mac
python -m utils.preprocessing --data_dir data/train --action validate --fix
```

### Auto-Caption Images
```bash
python -m utils.preprocessing --data_dir data/train --action caption --prefix "a photo of sks person"
```

### Resume Interrupted Training
```bash
python scripts/training/resume_training.py
# Follow the prompts
```

### Analyze Trained Model
```bash
python scripts/utilities/analyze_lora.py outputs/lora_models/final_model.safetensors
```

### Merge Multiple LoRAs
```bash
python scripts/utilities/merge_lora.py merge_loras \
  --loras model1.safetensors model2.safetensors \
  --weights 0.7 0.3 \
  --output merged.safetensors
```

## 🎯 Training Tips

### For Best Results:

1. **Image Quality Matters**
   - Use high-resolution images (512x512 minimum)
   - Ensure good lighting and clarity
   - Avoid heavy compression

2. **Dataset Size**
   - Characters/People: 20-50 images is enough
   - Art Styles: 100-500 images recommended
   - Concepts: 500-2000 images for best quality

3. **Captions**
   - Be consistent with trigger word (e.g., "sks person")
   - Describe important details
   - Use quality tags: "high quality, detailed"

4. **Configuration**
   - Start with default config
   - Lower rank (8-16) for small datasets
   - Higher rank (24-32) for large datasets or styles

### Expected Training Times:

| Hardware | Dataset | Time |
|----------|---------|------|
| RTX 3060 (12GB) | 500 images | 3-4 hours |
| RTX 3090 (24GB) | 1000 images | 4-6 hours |
| RTX 4090 (24GB) | 1000 images | 2-3 hours |

## 🚨 Troubleshooting

### Out of Memory?
```yaml
# Edit your config file:
training:
  train_batch_size: 1
  gradient_accumulation_steps: 8
  gradient_checkpointing: true
dataset:
  resolution: 512  # Lower if still OOM
```

### Training Too Slow?
```yaml
# Enable optimizations:
advanced:
  enable_xformers: true
  cache_latents: true
training:
  mixed_precision: "fp16"
```

### Poor Quality Results?
```yaml
# Increase training:
training:
  num_train_epochs: 15  # More epochs
  learning_rate: 5.0e-5  # Lower learning rate
advanced:
  snr_gamma: 5.0        # Better quality
  noise_offset: 0.05    # Better contrast
```

## 📚 Learn More

- **[Complete Guide](docs/GUIDE.md)** - Full tutorial with all features
- **[Advanced Guide](ADVANCED_GUIDE.md)** - Advanced techniques
- **[Features](FEATURES.md)** - Complete feature list (80+)
- **[Project Structure](PROJECT_STRUCTURE.md)** - Detailed structure

## 🎓 Example Workflows

### Train a Character LoRA
```bash
# 1. Prepare 20-50 images
mkdir data/train
# (Copy your images)

# 2. Validate
scripts\setup\preprocess.bat

# 3. Train with small dataset config
python scripts/training/train_lora.py --config configs/small_dataset_config.yaml

# 4. Generate samples
python scripts/utilities/generate_samples.py \
  --lora_path outputs/lora_models/final_model.safetensors \
  --prompts "portrait of sks person" "sks person smiling"
```

### Train an Art Style LoRA
```bash
# 1. Prepare 100-500 images of the style
# 2. Use default or large dataset config
python scripts/training/train_lora.py --config configs/large_dataset_config.yaml

# 3. Test with style prompts
python scripts/utilities/generate_samples.py \
  --lora_path outputs/lora_models/final_model.safetensors \
  --prompts_file prompts/style_prompts.txt
```

## 🆘 Getting Help

1. **Check logs:** `outputs/logs/training_*.log`
2. **Read documentation:** `docs/GUIDE.md`
3. **Common issues:** Look in Troubleshooting section
4. **Open an issue:** GitHub Issues

## ✨ You're Ready!

Start with the quickstart wizard:
```bash
scripts\setup\quickstart.bat  # Windows
```

Or dive right in:
```bash
python scripts/training/train_lora.py --config configs/default_config.yaml
```

Happy training! 🎨🚀
