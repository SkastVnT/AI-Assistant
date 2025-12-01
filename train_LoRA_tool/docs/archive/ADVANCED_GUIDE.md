# LoRA Training Tool - Advanced Guide

## 📚 Table of Contents
1. [Advanced Training Techniques](#advanced-training-techniques)
2. [Hyperparameter Tuning](#hyperparameter-tuning)
3. [Custom Dataset Preparation](#custom-dataset-preparation)
4. [Quality Optimization](#quality-optimization)
5. [Troubleshooting Common Issues](#troubleshooting-common-issues)

## 🎯 Advanced Training Techniques

### 1. Prior Preservation (DreamBooth-style)

For character/person training, use prior preservation to maintain model's general knowledge:

```yaml
training:
  with_prior_preservation: true
  prior_loss_weight: 1.0
  num_class_images: 100
  class_data_dir: "data/class_images"
  class_prompt: "a photo of person"
```

### 2. Min-SNR Weighting

Improves training stability and quality:

```yaml
advanced:
  snr_gamma: 5.0  # Recommended value
```

### 3. Noise Offset

Helps with contrast and darker images:

```yaml
advanced:
  noise_offset: 0.05  # For better contrast
  noise_offset: 0.1   # For darker/high-contrast styles
```

### 4. Text Encoder Training

Fine-tune text encoder for better concept understanding:

```yaml
advanced:
  train_text_encoder: true
  text_encoder_lr: 5.0e-6  # Lower than main LR
```

### 5. Exponential Moving Average (EMA)

Stabilizes training and improves quality:

```yaml
advanced:
  use_ema: true
  ema_decay: 0.9999
```

## ⚙️ Hyperparameter Tuning

### Learning Rate Schedules

**Cosine with Warmup (Recommended):**
```yaml
training:
  lr_scheduler: "cosine"
  lr_warmup_steps: 100
  learning_rate: 1.0e-4
```

**Cosine with Restarts (For long training):**
```yaml
training:
  lr_scheduler: "cosine_with_restarts"
  lr_warmup_steps: 100
  learning_rate: 1.0e-4
```

**Constant (For stable datasets):**
```yaml
training:
  lr_scheduler: "constant"
  learning_rate: 5.0e-5
```

### Batch Size and Gradient Accumulation

**Limited VRAM (8GB):**
```yaml
training:
  train_batch_size: 1
  gradient_accumulation_steps: 8  # Effective batch = 8
```

**Medium VRAM (12GB):**
```yaml
training:
  train_batch_size: 2
  gradient_accumulation_steps: 4  # Effective batch = 8
```

**High VRAM (24GB+):**
```yaml
training:
  train_batch_size: 4
  gradient_accumulation_steps: 4  # Effective batch = 16
```

### LoRA Rank Selection

| Use Case | Dataset Size | Recommended Rank |
|----------|-------------|------------------|
| Character/Person | 20-50 images | 8-16 |
| Art Style | 100-500 images | 16-32 |
| Concept | 50-200 images | 16-24 |
| SDXL | Any | 32-64 |

**Rule of thumb:** `alpha = 2 × rank`

## 📊 Custom Dataset Preparation

### Caption Format Best Practices

**Character Training:**
```
Format: "a photo of [trigger] person, [description], [style/quality]"

Examples:
- "a photo of sks person, smiling, professional photography"
- "a photo of sks person, portrait, natural lighting, high quality"
- "a photo of sks person, full body, outdoors, candid"
```

**Style Training:**
```
Format: "[subject] in [trigger] style, [details]"

Examples:
- "landscape in watercolor style, detailed brushstrokes"
- "portrait in anime style, vibrant colors"
- "architecture in cyberpunk style, neon lights, futuristic"
```

**Object/Concept Training:**
```
Format: "a photo of [trigger] [object], [context], [quality]"

Examples:
- "a photo of xyz car, parked on street, high detail"
- "a photo of xyz furniture, in modern room, professional photo"
```

### Image Quality Requirements

**Resolution:**
- Minimum: 512x512 for SD1.5
- Recommended: 768x768 for SD1.5
- SDXL: 1024x1024

**Format:**
- JPEG (quality 95+)
- PNG (preferred for quality)
- Avoid heavily compressed images

**Content:**
- Clear, well-lit subjects
- Variety of angles and poses
- Avoid watermarks/text overlays
- Consistent quality across dataset

### Dataset Size Guidelines

| Training Goal | Images | Epochs | Notes |
|--------------|--------|--------|-------|
| Quick concept | 10-20 | 20-30 | May overfit |
| Character | 20-50 | 15-20 | Good balance |
| Style | 100-500 | 10-15 | Best quality |
| Large dataset | 500-2000+ | 8-12 | Prevent overfit |

## 🎨 Quality Optimization

### Preventing Overfitting

**Symptoms:**
- Perfect replication but no variation
- Model ignores prompts
- Generic quality degrades

**Solutions:**
1. Reduce LoRA rank
2. Add dropout: `dropout: 0.1`
3. Reduce epochs
4. Use validation split
5. Increase dataset diversity

```yaml
lora:
  rank: 16  # Reduce from 32
  dropout: 0.1  # Add regularization

training:
  num_train_epochs: 10  # Reduce from 15
```

### Preventing Underfitting

**Symptoms:**
- Model doesn't learn trigger
- Poor quality outputs
- Inconsistent results

**Solutions:**
1. Increase LoRA rank
2. Increase epochs
3. Increase learning rate
4. Remove dropout

```yaml
lora:
  rank: 32  # Increase from 16
  dropout: 0.0  # Remove

training:
  num_train_epochs: 20  # Increase from 10
  learning_rate: 1.5e-4  # Increase from 1e-4
```

### Improving Image Quality

**Enable advanced features:**
```yaml
advanced:
  snr_gamma: 5.0  # Min-SNR weighting
  noise_offset: 0.05  # Better contrast
  use_ema: true  # Smoother results
  enable_xformers: true  # Memory efficient
```

**Use quality augmentations:**
```yaml
dataset:
  random_flip: true
  color_jitter: false  # Disable if style consistency needed
```

## 🔧 Troubleshooting Common Issues

### Issue: Training Loss Not Decreasing

**Possible causes:**
- Learning rate too low
- Model frozen incorrectly
- Data loading issues

**Solutions:**
```yaml
training:
  learning_rate: 2.0e-4  # Increase
  gradient_accumulation_steps: 4  # Reduce if too high
```

### Issue: Loss Exploding/NaN

**Possible causes:**
- Learning rate too high
- Gradient accumulation issues

**Solutions:**
```yaml
training:
  learning_rate: 5.0e-5  # Decrease
  max_grad_norm: 0.5  # Stronger clipping
  gradient_checkpointing: true
```

### Issue: Slow Training

**Optimizations:**
```yaml
training:
  mixed_precision: "fp16"  # Enable
  dataloader_num_workers: 8  # Increase
  
advanced:
  enable_xformers: true
  cache_latents: true  # Cache if enough disk space
```

**System optimizations:**
```bash
# Install xformers
pip install xformers

# Enable CUDA optimizations
set PYTORCH_CUDA_ALLOC_CONF=max_split_size_mb:512
```

### Issue: Poor Quality with Small Dataset

**Use these settings:**
```yaml
lora:
  rank: 8  # Lower rank
  alpha: 16
  dropout: 0.1  # Regularization

training:
  num_train_epochs: 20  # More epochs
  learning_rate: 5.0e-5  # Lower LR
  
advanced:
  snr_gamma: 5.0
  noise_offset: 0.05
```

### Issue: VRAM Out of Memory

**Progressive solutions:**
1. Enable gradient checkpointing: `gradient_checkpointing: true`
2. Reduce batch size: `train_batch_size: 1`
3. Increase gradient accumulation: `gradient_accumulation_steps: 8`
4. Reduce resolution: `resolution: 448` or `384`
5. Enable xformers: `enable_xformers: true`
6. Use fp16: `mixed_precision: "fp16"`

### Issue: Model Not Learning Trigger

**Ensure captions are correct:**
- Trigger word in every caption
- Consistent trigger format
- Varied descriptions after trigger

**Example fix:**
```
❌ Bad: "portrait of person"
✅ Good: "a photo of sks person, portrait"

❌ Bad: "sks, outdoor scene"
✅ Good: "a photo of sks person, outdoor scene"
```

## 📈 Advanced Monitoring

### Enable TensorBoard

```yaml
logging:
  use_tensorboard: true
  tensorboard_dir: "outputs/tensorboard"
```

Run TensorBoard:
```bash
tensorboard --logdir outputs/tensorboard
```

### Enable Wandb

```yaml
logging:
  use_wandb: true
  wandb_project: "lora-training"
  wandb_run_name: "character-training-v1"
```

Login and run:
```bash
wandb login
python train_lora.py --config configs/my_config.yaml
```

## 🎯 Training Recipes

### Recipe 1: High-Quality Character LoRA
```yaml
lora:
  rank: 16
  alpha: 32
  dropout: 0.05

training:
  num_train_epochs: 15
  learning_rate: 8.0e-5
  lr_scheduler: "cosine"
  
advanced:
  snr_gamma: 5.0
  noise_offset: 0.03
  use_ema: true
```

### Recipe 2: Art Style LoRA
```yaml
lora:
  rank: 32
  alpha: 64
  dropout: 0.0

training:
  num_train_epochs: 12
  learning_rate: 1.2e-4
  lr_scheduler: "cosine_with_restarts"
  
advanced:
  snr_gamma: 5.0
  noise_offset: 0.1
  color_jitter: false
```

### Recipe 3: Quick Test/Prototype
```yaml
lora:
  rank: 8
  alpha: 16

training:
  num_train_epochs: 5
  learning_rate: 1.0e-4
  save_steps: 1
  
logging:
  generate_samples: true
  sample_steps: 50
```

---

**For more help, check the main README.md or open an issue!**
