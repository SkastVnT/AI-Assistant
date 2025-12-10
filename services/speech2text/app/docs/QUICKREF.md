# 🚀 Quick Reference

## Commands

```bash
# Setup & Check
setup.bat              # First-time setup
rebuild_project.bat    # Complete rebuild from scratch
python check.py        # Health check

# Run
run.bat               # Main launcher

# Development
python app/core/run_dual_vistral.py    # Direct run
python app/tools/web_ui.py             # Web interface

# Docker
cd app/docker
docker-compose up      # Run in container
docker-compose build   # Rebuild image
```

## Files

| File | Purpose |
|------|---------|
| `run.bat` | Main launcher |
| `setup.bat` | First-time setup |
| `rebuild_project.bat` | Complete rebuild |
| `check.py` | System health check |
| `app/config/.env` | Configuration |
| `app/core/run_dual_vistral.py` | Main AI script |

## Folders

| Folder | Content |
|--------|---------|
| `app/output/vistral/` | ⭐ **Main results** |
| `app/output/raw/` | Individual model outputs |
| `app/audio/` | Processed audio |
| `app/logs/` | Application logs |
| `app/s2t/` | Virtual environment |

## Common Tasks

**Change audio input:**
```bash
# Edit app/config/.env
AUDIO_PATH=C:\new\path\to\audio.mp3
```

**Clean everything:**
```bash
rebuild_project.bat
```

**Fix dependencies:**
```bash
app\s2t\Scripts\activate.bat
pip install -r requirements.txt --force-reinstall
```

**Update models:**
```bash
# Delete cache
rmdir /s "%USERPROFILE%\.cache\huggingface\hub"
# Rerun - will redownload
run.bat
```

## Environment Variables

```env
# Required
HF_API_TOKEN=hf_xxxxx         # HuggingFace token

# Optional
AUDIO_PATH=C:\path\to\audio.mp3
CUDA_VISIBLE_DEVICES=0        # GPU device
```

## Pyenv Commands

```bash
# Install Python
pyenv install 3.10.6

# Set version
pyenv local 3.10.6      # For project
pyenv global 3.10.6     # System-wide
pyenv shell 3.10.6      # Current session

# Create venv
pyenv exec python -m venv app/s2t
```

## Docker Commands

```bash
cd app/docker

# Build
docker-compose build --no-cache

# Run
docker-compose up

# Stop
docker-compose down

# Check GPU
docker run --rm --gpus all nvidia/cuda:11.8.0-base nvidia-smi
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| System broken | `rebuild_project.bat` |
| CUDA error | Check GPU driver, run `python check.py` |
| Models not found | Set `HF_API_TOKEN` in `.env` |
| Out of memory | Need 6GB+ VRAM, close other apps |
| Import errors | `pip install -r requirements.txt` |

## Output Structure

```
app/output/
├── raw/
│   ├── whisper_xxx.txt      # Whisper transcript
│   └── phowhisper_xxx.txt   # PhoWhisper transcript
├── vistral/
│   └── dual_fused_xxx.txt   # ⭐ FINAL RESULT
└── dual/
    └── dual_models_xxx.txt  # Detailed log
```

## Performance

- **Audio preprocessing:** ~3-5s
- **Whisper large-v3:** ~15-20s
- **PhoWhisper-large:** ~6-8min
- **Qwen fusion:** ~5-8min
- **Total:** ~12-15min for 2.5min audio

## Links

- **HuggingFace Token:** https://huggingface.co/settings/tokens
- **Pyenv Windows:** https://github.com/pyenv-win/pyenv-win
- **Docker Desktop:** https://www.docker.com/products/docker-desktop
- **CUDA Toolkit:** https://developer.nvidia.com/cuda-downloads
