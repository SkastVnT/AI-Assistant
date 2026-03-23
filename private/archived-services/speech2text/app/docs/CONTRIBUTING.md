# Contributing

## Setup Development Environment

1. **Clone & Setup:**
```bash
git clone https://github.com/SkastVnT/Speech2Text.git
cd Speech2Text
setup.bat  # or manual setup
```

2. **Install dev dependencies:**
```bash
pip install pytest black flake8 mypy
```

3. **Check installation:**
```bash
python check.py
```

## Project Structure

- `run.bat`, `run.py` - Entry points
- `app/core/` - AI models
- `app/config/` - Configuration
- `app/tools/` - Utilities
- `app/docs/` - Documentation

## Before Committing

1. Test your changes
2. Check code style: `black app/`
3. Run checks: `python check.py`
4. Update docs if needed

## Docker

Build & test:
```bash
cd app/docker
docker-compose build
docker-compose up
```

---

**Branch:** VistralS2T  
**Questions?** Open an issue
