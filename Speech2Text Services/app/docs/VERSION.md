# Version Information

**Project:** Speech-to-Text System  
**Branch:** VistralS2T  
**Version:** 3.6.0  
**Release Date:** October 27, 2025

## System Components

- **Whisper:** large-v3 (OpenAI)
- **PhoWhisper:** large (VinAI)
- **Fusion Model:** Qwen2.5-1.5B-Instruct (Alibaba)
- **Python:** 3.10.6 (via pyenv)
- **CUDA:** 11.8 (recommended)

## Changelog

### v3.6.0 (2025-10-27) - Code Restructuring & Modular Architecture
- 🎨 **NEW:** Modular architecture with separated concerns
  - `models/` - AI model wrappers (whisper, phowhisper, qwen, diarization)
  - `pipelines/` - Processing workflows (7 pipelines reorganized)
  - `services/` - Business logic layer (prepared for future use)
  - `prompts/` - Prompt engineering (renamed from prompt_engineering)
- 🎨 **NEW:** File reorganization for better maintainability
  - Moved: `llm/*_client.py` → `models/*_model.py`
  - Moved: `run_*.py` → `pipelines/*_pipeline.py`
  - Renamed: `prompt_engineering/` → `prompts/`
- 📝 **IMPROVED:** Import path updates
  - Changed: `app.core.llm` → `app.core.models`
  - Updated: 9+ files with corrected import paths
  - Fixed: All test files with new imports
- 📝 **IMPROVED:** Code organization
  - Clear dependency hierarchy
  - Isolated components for testing
  - Scalable structure for future growth
- 📚 **DOCS:** Comprehensive documentation
  - New: `RESTRUCTURING_COMPLETE.md` with detailed migration guide
  - Updated: `README.md` completely rewritten for v3.6
  - Added: Architecture diagrams and examples

### v3.5.0 (2025-10-24) - VAD Optimization
- ⚡ **NEW:** Voice Activity Detection with Silero VAD
- ⚡ **NEW:** 30-50% faster processing with silence filtering
- 🔧 **FIXED:** Diarization timing display (was showing 0.00s)
- 🔧 **FIXED:** WebUI progress broadcasting issues
- 🔧 **IMPROVED:** Docker multi-stage builds for smaller images
- 📚 **DOCS:** VERSION_3.5_UPGRADE_GUIDE.py with upgrade instructions

### v3.0.0 (2025-10-22) - VistralS2T
- ✨ **NEW:** Qwen2.5-1.5B-Instruct for smart fusion
- ✨ **NEW:** 3-role speaker separation (System/Employee/Customer)
- ✨ **NEW:** Dual transcription with merge
- ✨ **NEW:** Complete project rebuild system
- ✨ **NEW:** Docker deployment
- ✨ **NEW:** Pyenv integration
- 🔧 **IMPROVED:** Clean project structure
- 🔧 **IMPROVED:** Comprehensive health checks
- 🔧 **IMPROVED:** Better error handling
- 📚 **DOCS:** Complete documentation overhaul

### v2.0.0 (Previous)
- Gemini AI fusion
- T5 model support
- FastAPI web service

### v1.0.0 (Initial)
- Basic Whisper transcription
- PhoWhisper Vietnamese support
- Rule-based fusion

## Dependencies

See `requirements.txt` for full list.

Key packages:
- torch >= 2.0.0
- transformers >= 4.35.0
- faster-whisper >= 0.10.0
- librosa >= 0.10.0

## License

MIT License

## Authors

- **SkastVnT** - Main developer
- Branch: VistralS2T
- Repository: https://github.com/SkastVnT/Speech2Text

## Support

- **Issues:** https://github.com/SkastVnT/Speech2Text/issues
- **Documentation:** See README.md and QUICKREF.md
- **Health Check:** `python check.py`
