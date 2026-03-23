# Scripts Directory

This directory contains all executable scripts for the LoRA Training Tool, organized by category.

## 📁 Directory Structure

```
scripts/
├── setup/              # Setup and launcher scripts (Windows batch files)
├── training/           # Core training scripts
└── utilities/          # Utility and helper scripts
```

## 🔧 Setup Scripts (`setup/`)

These are Windows batch files for easy interaction with the tool:

| Script | Description | Usage |
|--------|-------------|-------|
| `setup.bat` | Initial environment setup | Run once to create venv and install dependencies |
| `train.bat` | Training launcher | Interactive training with config selection |
| `quickstart.bat` | Step-by-step wizard | Guided setup from start to finish |
| `preprocess.bat` | Preprocessing menu | Validate, caption, and split datasets |
| `utilities.bat` | Utilities menu | Access all utility tools |
| `batch_generate.bat` | Batch sample generation | Generate samples from trained models |

**To run:** Double-click the .bat file or run from command prompt:
```bash
cd train_LoRA_tool
.\scripts\setup\setup.bat
```

## 🎓 Training Scripts (`training/`)

Core Python scripts for model training:

| Script | Description | Usage |
|--------|-------------|-------|
| `train_lora.py` | Main training script | Primary LoRA training engine |
| `resume_training.py` | Resume from checkpoint | Continue interrupted training |

**Example usage:**
```bash
# Basic training
python scripts/training/train_lora.py --config configs/default_config.yaml

# Resume training
python scripts/training/resume_training.py
```

## 🛠️ Utility Scripts (`utilities/`)

Helper scripts for model management and testing:

| Script | Description | Usage |
|--------|-------------|-------|
| `generate_samples.py` | Generate test images | Test LoRA quality with prompts |
| `analyze_lora.py` | Analyze LoRA models | Inspect model structure and weights |
| `merge_lora.py` | Merge LoRAs | Combine multiple LoRAs or merge to base |
| `convert_lora.py` | Format conversion | Convert between safetensors/PyTorch |
| `benchmark.py` | Training benchmark | Compare different configurations |

**Example usage:**
```bash
# Generate samples
python scripts/utilities/generate_samples.py --lora_path outputs/lora_models/model.safetensors

# Analyze LoRA
python scripts/utilities/analyze_lora.py outputs/lora_models/model.safetensors

# Merge LoRAs
python scripts/utilities/merge_lora.py merge_loras --loras model1.safetensors model2.safetensors
```

## 🚀 Quick Start Workflow

1. **Setup Environment:**
   ```bash
   .\scripts\setup\setup.bat
   ```

2. **Prepare Dataset:**
   ```bash
   .\scripts\setup\preprocess.bat
   ```

3. **Start Training:**
   ```bash
   .\scripts\setup\train.bat
   ```
   Or use the wizard:
   ```bash
   .\scripts\setup\quickstart.bat
   ```

4. **Generate Samples:**
   ```bash
   python scripts/utilities/generate_samples.py --lora_path outputs/lora_models/final_model.safetensors
   ```

5. **Analyze Results:**
   ```bash
   python scripts/utilities/analyze_lora.py outputs/lora_models/final_model.safetensors
   ```

## 📝 Notes

- **Windows users**: Use `.bat` files for easiest experience
- **Linux/Mac users**: Run Python scripts directly, activate venv first
- **All scripts**: Assume they're run from the `train_LoRA_tool` root directory
- **Python scripts**: Require virtual environment activation before use

## 🔗 Related Documentation

- [Main README](../README.md) - Overview and installation
- [Complete Guide](../docs/GUIDE.md) - Detailed usage guide
- [Advanced Guide](../ADVANCED_GUIDE.md) - Advanced techniques
- [Feature List](../FEATURES.md) - All features and capabilities
