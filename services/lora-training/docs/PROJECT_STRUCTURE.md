# LoRA Training Tool - Project Structure

## 📁 Complete Directory Tree

```
train_LoRA_tool/
├── 📂 config/                      # Configuration files (separate from code)
│   ├── __init__.py
│   ├── model_config.py             # Model configuration
│   ├── logging_config.py           # Logging configuration
│   └── training_config.py          # Training hyperparameters
│
├── 📂 configs/                     # YAML configuration presets
│   ├── default_config.yaml         # Standard configuration
│   ├── small_dataset_config.yaml   # For 500-1000 images
│   ├── large_dataset_config.yaml   # For 1500-2000+ images
│   └── sdxl_config.yaml            # SDXL training config
│
├── 📂 scripts/                     # All executable scripts
│   ├── README.md                   # Scripts documentation
│   │
│   ├── 📂 setup/                   # Setup and launcher scripts
│   │   ├── README.md
│   │   ├── setup.bat               # Environment setup
│   │   ├── train.bat               # Training launcher
│   │   ├── quickstart.bat          # Interactive wizard
│   │   ├── preprocess.bat          # Preprocessing menu
│   │   ├── utilities.bat           # Utilities menu
│   │   └── batch_generate.bat      # Batch generation
│   │
│   ├── 📂 training/                # Core training scripts
│   │   ├── README.md
│   │   ├── train_lora.py           # Main training script ✅
│   │   └── resume_training.py      # Resume from checkpoint
│   │
│   └── 📂 utilities/               # Utility scripts
│       ├── README.md
│       ├── generate_samples.py     # Generate test images ✅
│       ├── analyze_lora.py         # Analyze models
│       ├── merge_lora.py           # Merge LoRAs
│       ├── convert_lora.py         # Format conversion
│       └── benchmark.py            # Training benchmark
│
├── 📂 src/                         # Source code (modular organization)
│   ├── __init__.py
│   ├── 📂 llm/                     # LLM components (if needed)
│   │   ├── __init__.py
│   │   └── base.py
│   │
│   ├── 📂 prompt_engineering/      # Prompt templates
│   │   ├── __init__.py
│   │   ├── templates.py
│   │   └── chainer.py
│   │
│   └── 📂 utils/                   # Core utilities (same as utils/)
│       ├── __init__.py
│       ├── dataset_loader.py
│       ├── preprocessing.py
│       ├── logger.py
│       ├── model_utils.py
│       ├── lora_layers.py
│       └── training_utils.py
│
├── 📂 utils/                       # Core utility modules
│   ├── __init__.py
│   ├── dataset_loader.py           # Dataset loading
│   ├── preprocessing.py            # Dataset preprocessing
│   ├── logger.py                   # Logging utilities
│   ├── model_utils.py              # Model loading/saving
│   ├── lora_layers.py              # LoRA implementation
│   └── training_utils.py           # Training functions
│
├── 📂 data/                        # Data storage (organized by type)
│   ├── 📂 train/                   # Training images
│   │   └── README.txt
│   ├── 📂 val/                     # Validation images (optional)
│   │   └── README.txt
│   ├── 📂 examples/                # Example images
│   │   └── README.txt
│   ├── 📂 cache/                   # Cached latents (auto-generated)
│   ├── 📂 prompts/                 # Organized prompt storage
│   └── 📂 outputs/                 # Training outputs (alternative location)
│
├── 📂 prompts/                     # Prompt templates and examples
│   ├── character_prompts.txt       # Character testing prompts
│   └── style_prompts.txt           # Style testing prompts
│
├── 📂 docs/                        # Documentation
│   ├── GUIDE.md                    # Complete usage guide ✅
│   ├── API.md                      # API documentation
│   ├── TROUBLESHOOTING.md          # Common issues
│   └── CHANGELOG.md                # Version history
│
├── 📂 examples/                    # Implementation examples
│   ├── basic_training.py           # Basic training example
│   ├── advanced_training.py        # Advanced features demo
│   └── custom_dataset.py           # Custom dataset example
│
├── 📂 notebooks/                   # Jupyter notebooks
│   ├── dataset_analysis.ipynb      # Analyze your dataset
│   ├── prompt_testing.ipynb        # Test prompts
│   └── model_comparison.ipynb      # Compare models
│
├── 📂 outputs/                     # Training outputs (auto-created)
│   ├── 📂 lora_models/             # Trained LoRA models (.safetensors)
│   ├── 📂 checkpoints/             # Training checkpoints (.pt)
│   ├── 📂 logs/                    # Training logs
│   ├── 📂 samples/                 # Generated samples during training
│   └── 📂 tensorboard/             # TensorBoard logs
│
├── requirements.txt                # Python dependencies ✅
├── setup.py                        # Package setup (optional)
├── pyproject.toml                  # Modern Python project config
├── .gitignore                      # Git ignore rules ✅
├── .python-version                 # Python version specification
│
├── README.md                       # Main project README ✅
├── ADVANCED_GUIDE.md               # Advanced techniques ✅
├── FEATURES.md                     # Feature list ✅
├── LICENSE                         # License file
└── Dockerfile                      # Docker containerization (optional)
```

## 🎯 Project Structure Principles

### 1. Separation of Concerns
- **`config/`**: Configuration logic separate from code
- **`configs/`**: User-facing YAML configuration presets
- **`scripts/`**: All executable entry points
- **`src/` & `utils/`**: Core library code
- **`data/`**: All data storage

### 2. Modular Organization
- **Setup scripts**: Environment and launcher utilities
- **Training scripts**: Core training functionality
- **Utility scripts**: Model management and testing
- **Documentation**: Comprehensive guides at multiple levels

### 3. Best Practices
- ✅ Clear naming conventions
- ✅ README in each major directory
- ✅ Separate data from code
- ✅ Organized outputs by type
- ✅ Version control ready (.gitignore)

## 📊 File Categories

### Essential Files (Must Have)
- ✅ `scripts/training/train_lora.py` - Main training script
- ✅ `scripts/utilities/generate_samples.py` - Sample generation
- ✅ `utils/*.py` - All utility modules
- ✅ `configs/*.yaml` - Configuration presets
- ✅ `requirements.txt` - Dependencies
- ✅ `README.md` - Project documentation

### Configuration Files
- ✅ `configs/default_config.yaml` - Standard settings
- ✅ `configs/small_dataset_config.yaml` - Small dataset optimization
- ✅ `configs/large_dataset_config.yaml` - Large dataset optimization
- ✅ `configs/sdxl_config.yaml` - SDXL specific settings

### Setup & Launcher Scripts
- ✅ `scripts/setup/setup.bat` - Environment setup
- ✅ `scripts/setup/train.bat` - Training launcher
- ✅ `scripts/setup/quickstart.bat` - Interactive wizard
- ✅ `scripts/setup/preprocess.bat` - Dataset preprocessing
- ✅ `scripts/setup/utilities.bat` - Utilities menu

### Utility Scripts
- ✅ `scripts/utilities/generate_samples.py` - Image generation
- ✅ `scripts/utilities/analyze_lora.py` - Model analysis
- ✅ `scripts/utilities/merge_lora.py` - LoRA merging
- ✅ `scripts/utilities/convert_lora.py` - Format conversion
- ✅ `scripts/utilities/benchmark.py` - Configuration benchmark

### Documentation
- ✅ `README.md` - Main README
- ✅ `docs/GUIDE.md` - Complete guide
- ✅ `ADVANCED_GUIDE.md` - Advanced techniques
- ✅ `FEATURES.md` - Feature list
- ✅ `scripts/README.md` - Scripts documentation
- ✅ `scripts/setup/README.md` - Setup scripts guide
- ✅ `scripts/training/README.md` - Training scripts guide
- ✅ `scripts/utilities/README.md` - Utilities guide

## 🚀 Quick Navigation

### For Users
- **Getting Started**: `README.md` → `docs/GUIDE.md`
- **Setup**: Run `scripts/setup/setup.bat`
- **Training**: Run `scripts/setup/train.bat` or `scripts/setup/quickstart.bat`
- **Testing**: Use `scripts/utilities/generate_samples.py`

### For Developers
- **Core Logic**: `utils/` and `src/`
- **Training Flow**: `scripts/training/train_lora.py`
- **Configuration**: `config/` and `configs/`
- **Examples**: `examples/` and `notebooks/`

### For Troubleshooting
- **Logs**: `outputs/logs/`
- **Guides**: `docs/GUIDE.md` → Section 10 (Troubleshooting)
- **Advanced**: `ADVANCED_GUIDE.md`

## 📝 Notes

- All paths are relative to `train_LoRA_tool/` root
- `outputs/` directory is auto-created during training
- Virtual environment is created as `lora/` (excluded from git)
- Dataset images go in `data/train/` and optionally `data/val/`
- Generated models saved to `outputs/lora_models/`
