# Training Scripts

Core Python scripts for LoRA model training.

## Available Scripts

### `train_lora.py`
**Purpose:** Main LoRA training engine

**Features:**
- Complete LoRA training pipeline
- Support for SD 1.5, 2.1, and SDXL
- Configurable via YAML files
- Automatic checkpoint saving
- Sample generation during training
- TensorBoard/Wandb logging
- Resume from checkpoint support

**Usage:**
```bash
# Basic training
python scripts/training/train_lora.py --config configs/default_config.yaml

# With specific output directory
python scripts/training/train_lora.py --config configs/my_config.yaml --output_dir outputs/my_experiment

# Resume from checkpoint
python scripts/training/train_lora.py --config configs/my_config.yaml --resume outputs/checkpoints/checkpoint_epoch_5.pt

# Enable verbose logging
python scripts/training/train_lora.py --config configs/my_config.yaml --verbose
```

**Arguments:**
- `--config`: Path to YAML configuration file (required)
- `--output_dir`: Custom output directory (optional)
- `--resume`: Path to checkpoint to resume from (optional)
- `--verbose`: Enable verbose logging (optional)

**Configuration File:**
See `configs/` directory for examples. Key sections:
- `model`: Base model selection
- `lora`: LoRA rank, alpha, dropout
- `dataset`: Data paths and augmentation
- `training`: Learning rate, epochs, batch size
- `logging`: TensorBoard, Wandb, sample generation

**Outputs:**
- `outputs/lora_models/`: Final trained LoRA models (.safetensors)
- `outputs/checkpoints/`: Training checkpoints (.pt)
- `outputs/logs/`: Training logs (.log)
- `outputs/samples/`: Generated samples during training (.png)

---

### `resume_training.py`
**Purpose:** Resume interrupted training from checkpoints

**Features:**
- Automatically finds latest checkpoint
- Displays checkpoint information
- Generates resume command
- Validates checkpoint compatibility

**Usage:**
```bash
# Interactive mode (recommended)
python scripts/training/resume_training.py

# Specify checkpoint directory
python scripts/training/resume_training.py --checkpoint_dir outputs/checkpoints

# Show all checkpoints
python scripts/training/resume_training.py --list
```

**Arguments:**
- `--checkpoint_dir`: Directory containing checkpoints (default: `outputs/checkpoints`)
- `--list`: List all available checkpoints
- `--checkpoint`: Specific checkpoint file to resume from

**What it shows:**
- Checkpoint epoch and step
- Training progress (e.g., "Epoch 5/10")
- Configuration used
- Timestamp
- Resume command

**Example output:**
```
Found checkpoint: checkpoint_epoch_5.pt
Epoch: 5/10 (50% complete)
Step: 2500
Created: 2025-12-01 10:30:45

To resume training, run:
python scripts/training/train_lora.py --config configs/my_config.yaml --resume outputs/checkpoints/checkpoint_epoch_5.pt
```

## Training Workflow

### 1. Prepare Configuration
```bash
# Copy and edit a preset
copy configs\default_config.yaml configs\my_config.yaml
notepad configs\my_config.yaml
```

### 2. Start Training
```bash
# Windows (easier)
.\scripts\setup\train.bat

# Direct Python
python scripts/training/train_lora.py --config configs/my_config.yaml
```

### 3. Monitor Progress
```bash
# View logs
type outputs\logs\training_*.log

# Real-time monitoring (PowerShell)
Get-Content outputs\logs\training_*.log -Wait

# Check samples
explorer outputs\samples
```

### 4. Resume if Interrupted
```bash
# Find checkpoint
python scripts/training/resume_training.py

# Resume
python scripts/training/train_lora.py --config configs/my_config.yaml --resume outputs/checkpoints/checkpoint_epoch_5.pt
```

## Configuration Tips

**Small Dataset (20-100 images):**
```yaml
lora:
  rank: 8
  alpha: 16
training:
  num_train_epochs: 20
  learning_rate: 5.0e-5
```

**Medium Dataset (100-500 images):**
```yaml
lora:
  rank: 16
  alpha: 32
training:
  num_train_epochs: 12
  learning_rate: 1.0e-4
```

**Large Dataset (500-2000 images):**
```yaml
lora:
  rank: 32
  alpha: 64
training:
  num_train_epochs: 8
  learning_rate: 1.5e-4
```

**SDXL:**
```yaml
model:
  pretrained_model_name_or_path: "stabilityai/stable-diffusion-xl-base-1.0"
dataset:
  resolution: 1024
lora:
  rank: 32
training:
  mixed_precision: "bf16"
```

## Memory Optimization

**8GB VRAM:**
```yaml
training:
  train_batch_size: 1
  gradient_accumulation_steps: 8
  gradient_checkpointing: true
  mixed_precision: "fp16"
dataset:
  resolution: 512
```

**12GB+ VRAM:**
```yaml
training:
  train_batch_size: 2
  gradient_accumulation_steps: 4
  gradient_checkpointing: false
  mixed_precision: "fp16"
dataset:
  resolution: 768
advanced:
  enable_xformers: true
  cache_latents: true
```

## Troubleshooting

**Out of Memory:**
- Reduce `train_batch_size` to 1
- Enable `gradient_checkpointing`
- Lower `resolution` (512 → 384)
- Reduce `gradient_accumulation_steps`

**Training Too Slow:**
- Enable `cache_latents: true`
- Install xformers: `pip install xformers`
- Increase `dataloader_num_workers`
- Use SSD for dataset

**Poor Results:**
- Increase `num_train_epochs`
- Enable `snr_gamma: 5.0`
- Add `noise_offset: 0.05`
- Check dataset quality
- Verify captions are correct

**Can't Resume:**
- Check checkpoint exists
- Verify config file matches
- Ensure same model version
- Check Python environment

## Related Documentation

- [Complete Guide](../../docs/GUIDE.md) - Full training guide
- [Advanced Guide](../../ADVANCED_GUIDE.md) - Advanced techniques
- [Configuration Examples](../../configs/) - Sample configs
