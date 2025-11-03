# 📁 Project Structure After Reorganization

## Root Directory (Minimal & Clean)

```
Speech2Text/
├── README.md                    # Main documentation
├── requirements.txt             # Python dependencies
├── .env                         # Configuration
├── .gitignore                   # Git config
├── .python-version              # Python version
├── pytest.ini                   # Test config
├── start_webui.bat             # Quick start Web UI ⚡
├── start_diarization.bat       # Quick start Diarization ⚡
├── app/                         # All application code
└── BACKUP_REORGANIZE/           # Backup before reorganization
```

---

## App Directory Structure

```
app/
├── __init__.py
├── web_ui.py                    # Main Web UI application
│
├── api/                         # API services
│   ├── main.py
│   ├── whisper_service.py
│   ├── phowhisper_service.py
│   ├── gemini_service.py
│   └── ...
│
├── core/                        # Core functionality
│   ├── Phowhisper.py
│   ├── run_with_diarization.py
│   ├── handlers/
│   ├── llm/
│   ├── utils/
│   └── prompt_engineering/
│
├── config/                      # Configuration
│   ├── __init__.py
│   └── .env
│
├── data/                        # Data files
│   ├── audio/                   # Input audio
│   ├── results/                 # Processing results
│   ├── prompts/                 # LLM prompts
│   └── cache/                   # Cache files
│
├── output/                      # Output files
│   ├── raw/                     # Raw transcriptions
│   ├── dual/                    # Dual transcriptions
│   └── vistral/                 # Vistral enhanced
│
├── models/                      # Model files (downloaded)
│   └── .gitkeep
│
├── audio/                       # Temporary audio files
│   └── .gitkeep
│
├── logs/                        # Log files
│   └── .gitkeep
│
├── scripts/                     # Batch/Shell scripts
│   ├── setup.bat
│   ├── rebuild_project.bat
│   ├── fix_webui.bat
│   ├── install_webui_deps.bat
│   ├── run_diarization_cli.bat
│   ├── check.py
│   └── ...
│
├── docker/                      # Docker configuration
│   ├── docker-compose.windows.yml
│   ├── docker-manage.bat
│   ├── Dockerfile
│   ├── install_full_deps.bat
│   ├── test_container.bat
│   ├── QUICK_START.md
│   └── ...
│
├── docs/                        # Documentation
│   ├── QUICKSTART_v3.5.md
│   ├── INSTALLATION_SUCCESS.md
│   ├── CONTRIBUTING.md
│   ├── SUMMARY_VI.md
│   ├── REORGANIZE_GUIDE.md
│   ├── PROJECT_STRUCTURE.md
│   └── ...
│
├── tools/                       # Development tools
│   ├── download_phowhisper.py
│   ├── VERSION_3.5_UPGRADE_GUIDE.py
│   ├── reorganize.bat
│   ├── reorganize_app.bat
│   ├── _patch.py
│   └── ...
│
├── tests/                       # Test files
│   ├── test_whisper.py
│   ├── test_phowhisper.py
│   ├── test_qwen.py
│   └── conftest.py
│
├── templates/                   # HTML templates
│   └── index.html
│
├── notebooks/                   # Jupyter notebooks
│   ├── experiments/
│   └── README.md
│
├── deployment/                  # Deployment configs
│   ├── docker-compose.yml
│   ├── docker-compose.dev.yml
│   └── ...
│
├── deprecated/                  # Old/deprecated code
│   └── src_old/
│
└── s2t/                        # Virtual environment
    ├── Scripts/
    ├── Lib/
    └── ...
```

---

## What Changed?

### ✅ Removed from Root (Moved to app/)

**Batch files → `app/scripts/`:**
- `setup.bat`
- `rebuild_project.bat`
- `fix_webui.bat`
- `install_webui_deps.bat`
- `run_diarization_cli.bat`

**Documentation → `app/docs/`:**
- `CONTRIBUTING.md`
- `INSTALLATION_SUCCESS.md`
- `QUICKSTART_v3.5.md`
- `REORGANIZE_GUIDE.md`
- `REORGANIZE_PLAN.md`
- `SUMMARY_VI.md`
- `README_NEW.md`

**Utility scripts → `app/tools/`:**
- `check.py`
- `VERSION_3.5_UPGRADE_GUIDE.py`
- `reorganize.bat`
- `reorganize_app.bat`

**Duplicate directories (removed):**
- `audio/` (use `app/audio/`)
- `input_audio/` (use `app/data/audio/`)
- `output/` (use `app/output/`)
- `core/` (use `app/core/`)
- `data/` (use `app/data/`)

**Deprecated code → `app/deprecated/`:**
- `deprecated/src_old/`

---

## ✨ Kept in Root (Essential Files Only)

```
├── README.md                    # Project overview
├── requirements.txt             # Dependencies
├── .env                         # Config (optional, can use app/config/.env)
├── .gitignore                   # Git ignore rules
├── .python-version              # Python version
├── pytest.ini                   # Test configuration
├── start_webui.bat             # Quick start Web UI
├── start_diarization.bat       # Quick start Diarization
└── app/                         # All application code
```

**Why these files stay in root?**
- `README.md` - First file users see
- `requirements.txt` - Standard Python convention
- `start_*.bat` - Quick access for users
- `.env`, `.gitignore`, `.python-version`, `pytest.ini` - Standard config files

---

## Benefits

✅ **Clean root directory** - Only 8-10 files at root level  
✅ **No duplicates** - Single source of truth for each directory  
✅ **Easy navigation** - Everything in logical subdirectories  
✅ **Professional structure** - Follows Python project best practices  
✅ **Easy deployment** - Can deploy entire `app/` folder  
✅ **Better Git workflow** - Clear separation of code vs config  

---

## Quick Start After Reorganization

```powershell
# From root directory
.\start_webui.bat

# Or run scripts from new location
.\app\scripts\setup.bat
.\app\docker\docker-manage.bat
```

---

## Path Updates Needed

After reorganization, update these paths:

### In `start_webui.bat` (root):
```bat
call app\s2t\Scripts\activate
cd app
python web_ui.py
```

### In `start_diarization.bat` (root):
```bat
call app\s2t\Scripts\activate
cd app
python core\run_with_diarization.py
```

### In batch files moved to `app\scripts\`:
```bat
REM Change from:
call app\s2t\Scripts\activate

REM To:
call ..\s2t\Scripts\activate
```

---

## Backup

All files backed up before reorganization:
- `BACKUP_REORGANIZE/` - Latest backup
- `BACKUP_BEFORE_CLEANUP/` - Previous backup

To rollback:
```powershell
xcopy /E /I /Y "BACKUP_REORGANIZE\app" "app"
```
