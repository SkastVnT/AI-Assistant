# File Reorganization - v3.0.1

## 🎯 Summary

Reorganized project structure to follow professional AI project standards with session-based result management.

## 📂 Changes

### Directory Structure
**Removed (old structure):**
- `./audio/` → Moved to `app/data/audio/processed/`
- `./output/raw/` → Moved to `app/data/results/sessions/session_*/`
- `./output/vistral/` → Moved to `app/data/results/sessions/session_*/`
- `./output/dual/` → Moved to `app/data/results/sessions/session_*/`
- `./logs/` → Moved to `app/logs/`
- `./data/` → Removed (duplicate)
- `./results/` → Removed (duplicate)

**Added (new structure):**
```
app/
├── data/
│   ├── audio/
│   │   ├── raw/              # Original audio uploads
│   │   └── processed/        # Preprocessed audio
│   ├── cache/
│   │   └── transcripts/      # Cached results
│   ├── prompts/              # Prompt templates
│   └── results/
│       └── sessions/         # Session-based results
│           └── session_YYYYMMDD_HHMMSS/
│               ├── whisper_*.txt
│               ├── phowhisper_*.txt
│               ├── final_transcript_*.txt
│               └── processing_log_*.txt
├── logs/                      # Application logs
└── notebooks/
    └── experiments/           # Experimental notebooks
```

### Code Changes

**app/core/run_dual_vistral.py:**
- Updated directory creation to use new structure
- Added `SESSION_DIR` variable for session-based output
- Changed output paths:
  - `./output/raw/whisper_*.txt` → `{SESSION_DIR}/whisper_*.txt`
  - `./output/raw/phowhisper_*.txt` → `{SESSION_DIR}/phowhisper_*.txt`
  - `./output/vistral/dual_fused_*.txt` → `{SESSION_DIR}/final_transcript_*.txt`
  - `./output/dual/dual_models_*.txt` → `{SESSION_DIR}/processing_log_*.txt`
  - `./audio/processed_*.wav` → `app/data/audio/processed/processed_*.wav`
- Updated console output messages with better formatting

**.gitignore:**
- Removed old directory patterns (`app/output/`, `app/audio/`, etc.)
- Added new patterns for session-based structure:
  - `app/data/audio/raw/*`
  - `app/data/audio/processed/*`
  - `app/data/results/sessions/*`
  - `app/logs/*.log`
- Added `.gitkeep` exceptions to preserve empty directories
- Updated comment sections for clarity

### New Files

**Documentation:**
- `FILE_ORGANIZATION.md` - Complete guide to new structure
- `SESSION_MANAGER.md` - Quick guide for session manager tool
- `app/docker/DOCKER_QUICKSTART.md` - Docker deployment guide

**Tools:**
- `session_manager.bat` - Interactive session management tool with:
  - List all sessions
  - Show latest session details
  - Read latest transcript
  - Clean old sessions (keep last 10)
  - Archive sessions to ZIP
- `fix_pyenv_path.bat` - Pyenv PATH restoration utility

**Structure Markers:**
- `app/data/audio/raw/.gitkeep`
- `app/data/audio/processed/.gitkeep`
- `app/data/results/sessions/.gitkeep`
- `app/logs/.gitkeep`
- `app/notebooks/experiments/.gitkeep`

## ✅ Benefits

1. **Session Isolation:** Each transcription run gets its own timestamped folder
2. **Better Organization:** Clear separation of audio/results/logs/cache
3. **Easier Management:** Use `session_manager.bat` to handle sessions
4. **Cleaner Root:** No more scattered output folders in project root
5. **Git-Friendly:** Only structure tracked, not large data files
6. **Scalable:** Can handle hundreds of sessions without clutter
7. **Professional:** Follows industry best practices for AI projects

## 🔄 Migration

All existing results have been migrated to the new structure:
- Old files moved to `app/data/results/sessions/session_20251023_174157/`
- Processed audio moved to `app/data/audio/processed/`
- Old empty directories removed

## 🚀 Usage

Next run will automatically use the new structure:
```bash
python run.py
# Results will be in: app/data/results/sessions/session_[timestamp]/
```

Manage sessions easily:
```bash
session_manager.bat
```

## 📊 Impact

- ✅ **Zero breaking changes** - All existing functionality preserved
- ✅ **Backward compatible** - Old session format still readable
- ✅ **Better UX** - Clearer output messages and folder structure
- ✅ **Maintainable** - Easy to find and manage results

## 🔗 Related Documentation

- See `FILE_ORGANIZATION.md` for detailed structure explanation
- See `SESSION_MANAGER.md` for session management guide
- See `PROJECT_STRUCTURE.md` for overall architecture

---

**Version:** v3.0.1  
**Date:** 2025-10-23  
**Branch:** VistralS2T  
**Status:** ✅ Complete
