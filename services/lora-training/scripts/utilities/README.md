# Utility Scripts

Helper scripts for model management, testing, and analysis.

## Available Scripts

### `generate_samples.py`
**Purpose:** Generate test images from trained LoRA models

**Usage:**
```bash
# Basic generation with prompt
python scripts/utilities/generate_samples.py --lora_path outputs/lora_models/model.safetensors --prompts "a photo of sks person"

# Multiple prompts
python scripts/utilities/generate_samples.py --lora_path model.safetensors --prompts "prompt 1" "prompt 2" "prompt 3"

# From prompt file
python scripts/utilities/generate_samples.py --lora_path model.safetensors --prompts_file prompts/character_prompts.txt

# Comparison grid
python scripts/utilities/generate_samples.py --lora_path model.safetensors --comparison_grid

# Custom settings
python scripts/utilities/generate_samples.py --lora_path model.safetensors --prompts "test" --num_images 4 --guidance_scale 7.5 --steps 30
```

**Arguments:**
- `--lora_path`: Path to LoRA model (required)
- `--prompts`: One or more text prompts
- `--prompts_file`: File containing prompts (one per line)
- `--comparison_grid`: Generate comparison with/without LoRA
- `--num_images`: Images per prompt (default: 4)
- `--guidance_scale`: CFG scale (default: 7.5)
- `--steps`: Inference steps (default: 50)
- `--output_dir`: Save directory (default: `outputs/generated/`)

---

### `analyze_lora.py`
**Purpose:** Analyze and inspect LoRA models

**Usage:**
```bash
# Basic analysis
python scripts/utilities/analyze_lora.py outputs/lora_models/model.safetensors

# Detailed layer information
python scripts/utilities/analyze_lora.py model.safetensors --detailed

# Weight distribution analysis
python scripts/utilities/analyze_lora.py model.safetensors --weights

# Compare two LoRAs
python scripts/utilities/analyze_lora.py model1.safetensors --compare model2.safetensors

# Full analysis
python scripts/utilities/analyze_lora.py model.safetensors --detailed --weights --compare reference.safetensors
```

**Arguments:**
- `lora_path`: Path to LoRA model (required)
- `--detailed`: Show detailed layer information
- `--weights`: Analyze weight distributions
- `--compare`: Compare with another LoRA

**Output Information:**
- Model format and file size
- LoRA rank and alpha
- Number of layers
- Target modules
- Weight statistics (min, max, mean, std)
- Layer-by-layer breakdown
- Comparison metrics

---

### `merge_lora.py`
**Purpose:** Merge multiple LoRAs or merge LoRA into base model

**Usage:**

**Merge Multiple LoRAs:**
```bash
# Equal weights
python scripts/utilities/merge_lora.py merge_loras --loras model1.safetensors model2.safetensors --output merged.safetensors

# Custom weights (must sum to 1.0)
python scripts/utilities/merge_lora.py merge_loras --loras model1.safetensors model2.safetensors model3.safetensors --weights 0.5 0.3 0.2 --output merged.safetensors
```

**Merge LoRA into Base Model:**
```bash
# Full merge (alpha=1.0)
python scripts/utilities/merge_lora.py merge_to_base --base_model base.safetensors --lora my_lora.safetensors --output merged_model.safetensors

# Partial merge (alpha=0.75)
python scripts/utilities/merge_lora.py merge_to_base --base_model base.safetensors --lora my_lora.safetensors --alpha 0.75 --output merged_model.safetensors
```

**Extract LoRA Difference:**
```bash
python scripts/utilities/merge_lora.py extract_diff --original base.safetensors --finetuned finetuned.safetensors --output extracted_lora.safetensors --rank 16
```

**Arguments:**
- `merge_loras`: Merge multiple LoRA models
  - `--loras`: List of LoRA paths
  - `--weights`: Weights for each LoRA (optional, default: equal)
  - `--output`: Output path
  
- `merge_to_base`: Merge LoRA into base model
  - `--base_model`: Base model path
  - `--lora`: LoRA model path
  - `--alpha`: Merge strength (0.0-1.0, default: 1.0)
  - `--output`: Output path
  
- `extract_diff`: Extract LoRA from fine-tuned model
  - `--original`: Original base model
  - `--finetuned`: Fine-tuned model
  - `--output`: Output LoRA path
  - `--rank`: LoRA rank for extraction

---

### `convert_lora.py`
**Purpose:** Convert between LoRA formats

**Usage:**

**Safetensors to PyTorch:**
```bash
python scripts/utilities/convert_lora.py st2pt --input model.safetensors --output model.pt
```

**PyTorch to Safetensors:**
```bash
python scripts/utilities/convert_lora.py pt2st --input model.pt --output model.safetensors
```

**Resize LoRA Rank:**
```bash
# Reduce rank (32 → 16)
python scripts/utilities/convert_lora.py resize --input lora_rank32.safetensors --output lora_rank16.safetensors --rank 16

# Increase rank (16 → 32)
python scripts/utilities/convert_lora.py resize --input lora_rank16.safetensors --output lora_rank32.safetensors --rank 32
```

**Arguments:**
- `st2pt`: Safetensors to PyTorch
  - `--input`: Input .safetensors file
  - `--output`: Output .pt file
  
- `pt2st`: PyTorch to Safetensors
  - `--input`: Input .pt file
  - `--output`: Output .safetensors file
  
- `resize`: Change LoRA rank
  - `--input`: Input LoRA file
  - `--output`: Output LoRA file
  - `--rank`: New rank value

---

### `benchmark.py`
**Purpose:** Compare different training configurations

**Usage:**

**Benchmark Learning Rates:**
```bash
python scripts/utilities/benchmark.py --config configs/base_config.yaml --benchmark lr --values 1e-5 5e-5 1e-4 5e-4 --output benchmarks/lr_comparison
```

**Benchmark LoRA Ranks:**
```bash
python scripts/utilities/benchmark.py --config configs/base_config.yaml --benchmark rank --values 8 16 32 64 --output benchmarks/rank_comparison
```

**Benchmark Batch Sizes:**
```bash
python scripts/utilities/benchmark.py --config configs/base_config.yaml --benchmark batch_size --values 1 2 4 --output benchmarks/batch_comparison
```

**Custom Benchmark:**
```bash
python scripts/utilities/benchmark.py --configs config1.yaml config2.yaml config3.yaml --output benchmarks/custom
```

**Arguments:**
- `--config`: Base configuration file
- `--benchmark`: Parameter to benchmark (lr, rank, batch_size)
- `--values`: Values to test
- `--configs`: Multiple config files (alternative to --benchmark)
- `--output`: Output directory for results
- `--max_epochs`: Max epochs per run (default: 5 for benchmark)

**Output:**
- Training logs for each configuration
- Loss curves comparison
- Sample quality comparison
- Performance metrics (time, memory)
- Summary report

## Common Workflows

### Test New LoRA
```bash
# 1. Generate samples
python scripts/utilities/generate_samples.py --lora_path outputs/lora_models/new_model.safetensors --prompts_file prompts/character_prompts.txt

# 2. Analyze model
python scripts/utilities/analyze_lora.py outputs/lora_models/new_model.safetensors --detailed --weights

# 3. Compare with previous version
python scripts/utilities/analyze_lora.py outputs/lora_models/new_model.safetensors --compare outputs/lora_models/old_model.safetensors
```

### Combine Multiple LoRAs
```bash
# 1. Analyze each LoRA
python scripts/utilities/analyze_lora.py style_lora.safetensors
python scripts/utilities/analyze_lora.py character_lora.safetensors

# 2. Merge with custom weights
python scripts/utilities/merge_lora.py merge_loras --loras style_lora.safetensors character_lora.safetensors --weights 0.6 0.4 --output combined.safetensors

# 3. Test result
python scripts/utilities/generate_samples.py --lora_path combined.safetensors --prompts "test prompt"
```

### Optimize Configuration
```bash
# 1. Benchmark different settings
python scripts/utilities/benchmark.py --config configs/base.yaml --benchmark lr --values 5e-5 1e-4 2e-4

# 2. Review results
explorer benchmarks\lr_comparison

# 3. Use best config for full training
python scripts/training/train_lora.py --config benchmarks/lr_comparison/best_config.yaml
```

### Prepare for Distribution
```bash
# 1. Convert to safetensors (if needed)
python scripts/utilities/convert_lora.py pt2st --input model.pt --output model.safetensors

# 2. Analyze final model
python scripts/utilities/analyze_lora.py model.safetensors --detailed

# 3. Generate preview images
python scripts/utilities/generate_samples.py --lora_path model.safetensors --prompts_file prompts/showcase.txt --num_images 4
```

## Tips

- **Use safetensors format** for better compatibility and security
- **Generate samples regularly** to monitor training progress
- **Compare LoRAs** to understand what each training run learned
- **Merge carefully** - weights should sum to 1.0
- **Benchmark on small scale** (5 epochs) before full training
- **Keep backups** before format conversion or merging

## Related Documentation

- [Complete Guide](../../docs/GUIDE.md) - Usage examples
- [Advanced Guide](../../ADVANCED_GUIDE.md) - Advanced techniques
- [Feature List](../../FEATURES.md) - All capabilities
