# File Organization Guide

## 📂 New Directory Structure (v3.0)

```
s2t/
├── app/
│   ├── core/                      # Core application logic
│   ├── config/                    # Configuration files
│   ├── tools/                     # Utility tools
│   ├── docker/                    # Docker configuration
│   ├── tests/                     # Test suite
│   ├── notebooks/                 # Jupyter notebooks
│   │   └── experiments/           # Experimental notebooks
│   ├── logs/                      # Application logs
│   │   └── .gitkeep
│   └── data/                      # Data directory
│       ├── audio/
│       │   ├── raw/               # Original audio files
│       │   │   └── .gitkeep
│       │   └── processed/         # Preprocessed audio
│       │       └── .gitkeep
│       ├── cache/
│       │   └── transcripts/       # Cached transcriptions
│       ├── prompts/               # Prompt templates
│       └── results/
│           └── sessions/          # Session-based results
│               ├── .gitkeep
│               └── session_YYYYMMDD_HHMMSS/
│                   ├── whisper_*.txt
│                   ├── phowhisper_*.txt
│                   ├── final_transcript_*.txt
│                   └── processing_log_*.txt
├── models/                        # AI models (gitignored)
├── run.py                         # Main entry point
├── requirements.txt               # Python dependencies
├── pytest.ini                     # Test configuration
└── README.md                      # Project documentation
```

## 🎯 File Categories

### Session Results (`app/data/results/sessions/`)
Each transcription run creates a new session folder with timestamp:
- **Format:** `session_YYYYMMDD_HHMMSS/`
- **Contents:**
  - `whisper_*.txt` - Whisper large-v3 raw transcript
  - `phowhisper_*.txt` - PhoWhisper-large raw transcript
  - `final_transcript_*.txt` - **MAIN OUTPUT** - Qwen-fused result with 3-role separation
  - `processing_log_*.txt` - Detailed processing statistics

### Audio Files (`app/data/audio/`)
- **raw/** - Original audio files (uploaded by user)
- **processed/** - Preprocessed audio (32kHz, normalized, trimmed, filtered)

### Logs (`app/logs/`)
- Application-level logs
- Error tracking
- Performance monitoring

### Cache (`app/data/cache/`)
- Cached transcriptions to avoid re-processing
- Temporary processing files

## 🚀 Usage Examples

### Find Latest Session
```powershell
# PowerShell
Get-ChildItem app\data\results\sessions\ | Sort-Object Name -Descending | Select-Object -First 1
```

### Read Latest Transcript
```powershell
# Get latest session
$latest = Get-ChildItem app\data\results\sessions\ | Sort-Object Name -Descending | Select-Object -First 1

# Read final transcript
Get-Content "$($latest.FullName)\final_transcript_*.txt"
```

### Archive Old Sessions
```powershell
# Archive sessions older than 7 days
$archiveDate = (Get-Date).AddDays(-7)
Get-ChildItem app\data\results\sessions\ | Where-Object { $_.CreationTime -lt $archiveDate } | 
    Compress-Archive -DestinationPath "archive_$(Get-Date -Format 'yyyyMMdd').zip"
```

## 📊 Session Output Structure

Each session contains:

```
session_20251023_174157/
├── whisper_9463501e-8c9b-419d-941a-d5a9c17fb5e7_20251023_143804.txt
│   └── Raw Whisper large-v3 transcript (global ASR)
│
├── phowhisper_9463501e-8c9b-419d-941a-d5a9c17fb5e7_20251023_143804.txt
│   └── Raw PhoWhisper-large transcript (Vietnamese-optimized)
│
├── final_transcript_9463501e-8c9b-419d-941a-d5a9c17fb5e7_20251023_143804.txt
│   └── ⭐ MAIN OUTPUT - Qwen2.5-1.5B fused result
│       Format: 3-role speaker separation
│       - Hệ thống: (System messages)
│       - Nhân viên: (Employee speech)
│       - Khách hàng: (Customer speech)
│
└── processing_log_9463501e-8c9b-419d-941a-d5a9c17fb5e7_20251023_143804.txt
    └── Detailed processing statistics:
        - Model versions
        - Processing times
        - Audio metadata
        - Performance metrics
```

## 🧹 Cleanup Strategy

### Keep Only Recent Sessions
```powershell
# Keep last 10 sessions, delete older ones
Get-ChildItem app\data\results\sessions\ | 
    Sort-Object Name -Descending | 
    Select-Object -Skip 10 | 
    Remove-Item -Recurse -Force
```

### Clean Processed Audio
```powershell
# Remove processed audio older than 30 days
$threshold = (Get-Date).AddDays(-30)
Get-ChildItem app\data\audio\processed\ | 
    Where-Object { $_.CreationTime -lt $threshold } | 
    Remove-Item -Force
```

## 🔄 Migration from Old Structure

Old structure (`./audio/`, `./output/`) has been migrated to new structure:

```
OLD                              →  NEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
./audio/*.wav                   →  app/data/audio/processed/
./output/raw/whisper_*.txt      →  app/data/results/sessions/session_*/
./output/raw/phowhisper_*.txt   →  app/data/results/sessions/session_*/
./output/vistral/dual_fused_*.txt  →  app/data/results/sessions/session_*/final_transcript_*.txt
./output/dual/dual_models_*.txt →  app/data/results/sessions/session_*/processing_log_*.txt
```

## ✅ Benefits of New Structure

1. **Session-based:** Each run isolated in own folder
2. **Organized:** Clear categorization (audio/results/logs/cache)
3. **Searchable:** Easy to find results by timestamp
4. **Scalable:** Can handle hundreds of sessions
5. **Git-friendly:** Only structure tracked, not large files
6. **Professional:** Follows industry best practices

## 📝 Notes

- All large files (audio, transcripts, models) are gitignored
- `.gitkeep` files preserve empty directory structure in git
- Session folders created automatically on each run
- Old directories (`audio/`, `output/`, `logs/`, `results/`) removed
- Docker volumes may need remapping for new structure
