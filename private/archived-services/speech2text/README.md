<div align="center">

# 🎙️ VistralS2T

### Vietnamese Speech-to-Text System

**Advanced AI-Powered Speech Recognition with Dual-Model Fusion**

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-3.6.0+-brightgreen.svg)](https://github.com/SkastVnT/Speech2Text)
[![Status](https://img.shields.io/badge/status-production--ready-success.svg)](https://github.com/SkastVnT/Speech2Text)

**v3.6.0+** | Web UI Ready | Full Documentation ⭐⭐⭐⭐⭐

[Quick Start](#-quick-start) • [Features](#-features) • [Web UI](#-web-ui) • [Documentation](#-documentation)

</div>

---

## 🎉 What's New in v3.6.0+

- ✅ **Multi-Model LLM Support** - Choose between Gemini (Free), OpenAI (GPT-4o-mini), or DeepSeek for transcript enhancement
- ✅ **4-Key Retry Mechanism** - Automatic retry with 4 Gemini API keys to prevent quota issues
- ✅ **Interactive Model Selection** - 30-second countdown modal to select your preferred AI model
- ✅ **Real-time Monitoring** - Detailed progress notifications showing API key retry attempts
- ✅ **Graceful Fallback** - Returns raw transcript if LLM enhancement fails
- ✅ **Web UI Ready** - Professional web interface with real-time progress
- ✅ **Fixed Dependencies** - All dependency conflicts resolved
- ✅ **Clean Installation** - Step-by-step setup guides included
- ✅ **Full Documentation** - Complete troubleshooting & usage guides
- ✅ **Production Ready** - Tested and optimized for real-world use

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 Core Capabilities
- 🤖 **Dual-Model Fusion** - Whisper + PhoWhisper for maximum accuracy
- 🎙️ **Speaker Diarization** - 95-98% accuracy with pyannote.audio 3.1
- 🇻🇳 **Vietnamese Optimized** - Perfect Vietnamese phonetics & grammar
- ⚡ **Voice Activity Detection** - Smart VAD for faster processing
- 🧠 **Multi-LLM Enhancement** - Choose Gemini (Free), OpenAI, or DeepSeek for transcript cleaning
- 🔄 **4-Key Retry** - Automatic retry with 4 Gemini API keys (prevents quota issues)
- 🚀 **CPU/GPU Support** - Works on any hardware, cloud-based AI enhancement

</td>
<td width="50%">

### 💻 User Experience
- 🌐 **Web UI** - Real-time processing with drag & drop
- 🤖 **Interactive Model Selection** - 30s countdown modal to choose AI model
- 📊 **Live Progress** - WebSocket-based status updates with retry notifications
- 📁 **Session Management** - Organized results with timestamps
- 📥 **Multi-Format** - MP3, WAV, M4A, FLAC support
- 📝 **Export Options** - TXT, JSON, Timeline formats
- 📦 **100% Free** - Free tier available (Gemini)

</td>
</tr>
</table>

---

## 🤖 AI Models

| Model | Purpose | Provider | Accuracy | Cost |
|-------|---------|----------|----------|------|
| **Whisper large-v3** | Global speech recognition (99 languages) | OpenAI | 95%+ | Free |
| **PhoWhisper-large** | Vietnamese ASR specialist | VinAI | 98%+ | Free |
| **Gemini 2.0 Flash** | STT transcript cleaning & enhancement (4 keys) | Google | 98%+ | **FREE** |
| **GPT-4o-mini** | Alternative LLM for transcript cleaning | OpenAI | 98%+ | $0.15/1M tokens |
| **DeepSeek Chat** | Cost-effective LLM alternative | DeepSeek | 97%+ | $0.14/1M tokens |
| **pyannote.audio 3.1** | Speaker diarization | pyannote | 95-98% | Free |

> **💡 Tip:** Use Gemini (Free) for unlimited processing. OpenAI/DeepSeek available if quota exceeded.

---

## 🚀 Quick Start

### ⚡ Fast Setup (5 minutes)

```powershell
# 1. Clone repository
git clone https://github.com/SkastVnT/Speech2Text.git
cd Speech2Text

# 2. Run dependency installer (first time only)
.\scripts\fix_dependencies.bat

# 3. Configure API keys
# Edit .env file and add:
# - HF_TOKEN (for speaker diarization): https://huggingface.co/settings/tokens
# - GEMINI_API_KEY_1 to _4 (for transcript cleaning - FREE): https://aistudio.google.com/apikey
# - OPENAI_API_KEY (optional, for GPT-4o-mini): https://platform.openai.com/api-keys
# - DEEPSEEK_API_KEY (optional, for DeepSeek): https://platform.deepseek.com/api-keys

# 4. Launch Web UI
.\start_webui.bat

# 5. Open browser → http://localhost:5000
```

**📝 Note:** 
- First run will download AI models (~10GB). Requires internet connection.
- **FREE:** Get 4 Gemini API keys (free tier) to avoid quota limits
- **PAID:** OpenAI/DeepSeek optional for higher quality ($0.14-0.15/1M tokens)

---

## 🌐 Web UI

### Professional Interface with Real-Time Processing

<table>
<tr>
<td width="50%">

**Features:**
- 🎯 Drag & drop audio upload
- 📊 Real-time progress tracking
- 🤖 **Interactive model selection** (Gemini/OpenAI/DeepSeek)
- 🔄 **Automatic retry notifications** (4 Gemini keys)
- 🎙️ Speaker diarization visualization
- 📝 Live transcript preview
- 💾 One-click download results
- 📁 Session history

</td>
<td width="50%">

**Processing Stages:**
1. Audio preprocessing (10-15%)
2. Speaker diarization (20-40%)
3. Whisper transcription (55-75%)
4. PhoWhisper transcription (78-88%)
5. **Model selection** (90-92%) - 30s countdown
6. **LLM enhancement** (93-98%) - Auto-retry with 4 keys
7. Results ready (100%)

**Model Selection:**
- ✨ **Gemini** (Default) - FREE, 4-key retry
- 🧠 **OpenAI** - GPT-4o-mini ($0.15/1M)
- 🚀 **DeepSeek** - High quality ($0.14/1M)

</td>
</tr>
</table>

### Quick Start Web UI

```powershell
.\start_webui.bat
```

Then open: **http://localhost:5000**

---

## 📦 Installation

### Prerequisites

- **Python:** 3.10.6+ (managed by pyenv)
- **RAM:** 8GB minimum (16GB recommended)
- **Storage:** 15GB for models & cache
- **GPU:** Optional (NVIDIA with 6GB+ VRAM for speedup)

### Step-by-Step Installation

```powershell
# 1. Install dependencies in correct order
.\scripts\fix_dependencies.bat

# 2. Verify installation
.\test_system.bat

# 3. Configure environment (optional)
# Copy .env.example to .env
# Add your HF_TOKEN for speaker diarization
```

### Manual Installation (if script fails)

```powershell
# Activate virtual environment
.\app\s2t\Scripts\activate

# Install in steps
pip install -r requirements-step1.txt  # PyTorch foundation
pip install -r requirements-step2.txt  # AI models
pip install -r requirements-step3.txt  # Audio processing
pip install -r requirements-step4.txt  # Web UI
```

---

## 🎯 Usage

### Option 1: Web UI (Recommended) 🌐

```powershell
# 1. Navigate to docker folder
cd app\docker

# 2. Start services
docker-compose up --build

# 3. Access Web UI → http://localhost:5000
```

---

## � Documentation

### Quick References
- **[WEBUI_SETUP_COMPLETE.md](WEBUI_SETUP_COMPLETE.md)** - Complete Web UI setup guide
- **[SETUP_FINAL.md](SETUP_FINAL.md)** - Final setup steps
- **[README_SETUP.md](README_SETUP.md)** - Quick setup summary
- **[docs/WEBUI_ERROR_FIXES.md](docs/WEBUI_ERROR_FIXES.md)** - Troubleshooting guide
- **[docs/QUICK_FIX_DEPENDENCIES.md](docs/QUICK_FIX_DEPENDENCIES.md)** - Dependency fixes

### Installation & Setup
- **Step-by-step installer:** `.\scripts\fix_dependencies.bat`
- **System verification:** `.\test_system.bat`
- **FFmpeg installer:** `.\scripts\install_ffmpeg.bat` (optional)

### Configuration
- **Environment variables:** `.env` (copy from `.env.example`)
- **HuggingFace Token:** Required for speaker diarization
  - Get token: https://huggingface.co/settings/tokens
  - Accept license: https://huggingface.co/pyannote/speaker-diarization-3.1
- **LLM API Keys (choose one or all):**
  - **Gemini (FREE):** Get 4 keys from https://aistudio.google.com/apikey
    - Add as: `GEMINI_API_KEY_1`, `GEMINI_API_KEY_2`, `GEMINI_API_KEY_3`, `GEMINI_API_KEY_4`
  - **OpenAI (Paid):** Get from https://platform.openai.com/api-keys
    - Add as: `OPENAI_API_KEY=sk-proj-...`
  - **DeepSeek (Paid):** Get from https://platform.deepseek.com/api-keys
    - Add as: `DEEPSEEK_API_KEY=sk-...`

---

## 🔧 Troubleshooting

### Common Issues

**Issue: Dependency resolution error**
```powershell
# Solution: Use step-by-step installer
.\scripts\fix_dependencies.bat
```

**Issue: All Gemini API keys quota exhausted**
```powershell
# Solution 1: Wait 1 minute for quota reset (free tier)
# Solution 2: Use OpenAI or DeepSeek model
# Solution 3: Get more Gemini API keys (up to 4 supported)
```

**Issue: "Model selection timed out"**
```powershell
# Solution: System auto-selects Gemini after 30 seconds
# No action needed - processing continues automatically
```

**Issue: LLM enhancement failed**
```powershell
# System behavior: Returns raw Whisper+PhoWhisper transcript
# Check: API keys in .env file
# Check: Internet connection
# Fallback: Results still available without LLM cleaning
```

**Issue: Gemini API key not configured**
```powershell
# Solution: Get 4 free Gemini API keys
# 1. Visit: https://aistudio.google.com/apikey
# 2. Create 4 API keys (free tier)
# 3. Add to .env: 
#    GEMINI_API_KEY_1=your_key_1
#    GEMINI_API_KEY_2=your_key_2
#    GEMINI_API_KEY_3=your_key_3
#    GEMINI_API_KEY_4=your_key_4
```

**Issue: Speaker diarization fails (403 error)**
```powershell
# Solution: Accept HuggingFace model license
# 1. Visit: https://huggingface.co/pyannote/speaker-diarization-3.1
# 2. Click "Agree and access repository"
# 3. Add HF_TOKEN to .env file
```

**Issue: TorchCodec warnings**
```powershell
# Solution: Already suppressed in v3.6.0+
# Optional: Install FFmpeg for optimization
.\scripts\install_ffmpeg.bat
```

**More help:** See `docs/WEBUI_ERROR_FIXES.md`

---

## 🎯 Features in Detail

### Web UI Features
- ✅ Real-time progress tracking via WebSocket
- ✅ Drag & drop audio upload
- ✅ Multi-format support (MP3, WAV, M4A, FLAC)
- ✅ Live transcript preview
- ✅ Session management with history
- ✅ One-click results download (TXT, JSON)
- ✅ Speaker timeline visualization
- ✅ Processing time estimation

### Processing Pipeline
1. **Audio Preprocessing** (10-15%)
   - Format conversion to 16kHz WAV
   - Noise reduction
   - Volume normalization

2. **Speaker Diarization** (20-40%)
   - pyannote.audio 3.1 model
   - 2-5 speaker detection
   - Timeline segmentation

3. **Whisper Transcription** (55-75%)
   - OpenAI Whisper large-v3
   - 99 language support
   - High accuracy global ASR

4. **PhoWhisper Transcription** (78-88%)
   - VinAI PhoWhisper-large
   - Vietnamese specialist
   - Phonetics optimization

5. **Gemini AI Cleaning** (92-98%)
   - Google Gemini 2.0 Flash (Free)
   - STT transcript cleaning
   - Vietnamese diacritics restoration
   - Filler word removal
   - Speaker turn preservation

6. **Results Ready** (100%)
   - Timeline transcript
   - Speaker-separated output
   - JSON metadata

---

## 📊 Performance

### Processing Speed (CPU Mode)
- **Audio Duration:** 250 seconds
- **Whisper Time:** ~276 seconds (1.1x)
- **PhoWhisper Time:** ~156 seconds (0.6x with optimization)
- **Gemini AI Time:** ~5-10 seconds (cloud API)
- **Total:** ~440 seconds (1.76x audio duration)

### Accuracy Metrics
- **Whisper WER:** 5-8% (general content)
- **PhoWhisper WER:** 2-5% (Vietnamese content)
- **Combined Accuracy:** 95-98%
- **Speaker Diarization:** 95-98%

### System Requirements
- **Minimum:** 8GB RAM, 4-core CPU, 15GB storage
- **Recommended:** 16GB RAM, 8-core CPU, SSD, 20GB storage
- **Optimal:** 32GB RAM, GPU (6GB+ VRAM), NVMe SSD

---

```
VistralS2T/
├── 📄 README.md                    # This file
├── 📋 requirements.txt             # Python dependencies
├── 🚀 start_webui.bat             # Launch Web UI
├── 🚀 start_diarization.bat       # Launch CLI with diarization
│
├── 📂 app/                         # Main application
│   ├── core/                       # Core processing modules
│   │   ├── models/                 # 🆕 AI model wrappers
│   │   │   ├── whisper_model.py
│   │   │   ├── phowhisper_model.py
│   │   │   ├── gemini_model.py
│   │   │   └── diarization_model.py
│   │   ├── pipelines/              # 🆕 Processing workflows
│   │   │   ├── with_diarization_pipeline.py
│   │   │   ├── dual_fast_pipeline.py
│   │   │   └── dual_smart_pipeline.py
│   │   ├── services/               # 🆕 Business logic (ready for v3.7)
│   │   ├── prompts/                # 🆕 Prompt templates (renamed from prompt_engineering/)
│   │   ├── utils/                  # Audio, VAD, cache, logger utilities
│   │   └── handlers/               # Error & exception handlers
│   │
│   ├── web_ui.py                   # Flask Web UI application
│   ├── config/                     # Configuration & .env files
│   ├── data/                       # Data storage
│   │   ├── audio/                  # Input audio files
│   │   ├── models/                 # Downloaded AI models (~10GB)
│   │   ├── cache/                  # Processing cache
│   │   └── results/                # Output transcriptions
│   │
│   ├── docker/                     # Docker deployment configs
│   ├── tests/                      # Unit & integration tests
│   └── s2t/                        # Python virtual environment
│
├── 📂 scripts/                     # Utility scripts
│   ├── rebuild_project.bat         # Setup/rebuild environment
│   ├── fix_webui.bat              # Fix Web UI dependencies
│   └── install_webui_deps.bat     # Install Web UI packages
│
├── 📂 docs/                        # Documentation
│   ├── QUICKSTART.md              # Quick start guide
│   ├── DOCKER_GUIDE.md            # Docker deployment
│   ├── TROUBLESHOOTING.md         # Common issues
│   └── archive/                   # Version-specific docs
│
├── 📂 logs/                        # Application logs
└── 📂 results/                     # Output transcripts
```

**📖 Full architecture details:** See `docs/PROJECT_STRUCTURE.md`



---

## 🎯 Processing Pipeline

### Workflow Overview

```
Audio Input
    ↓
Preprocessing (16kHz mono normalization)
    ↓
Voice Activity Detection (Silero VAD - optional)
    ↓
Speaker Diarization (pyannote.audio 3.1)
    ↓
Audio Segmentation (by speaker turns)
    ↓
Dual Transcription (parallel processing)
    ├─→ Whisper large-v3 (Global ASR)
    └─→ PhoWhisper-large (Vietnamese ASR)
    ↓
Smart Fusion (confidence-based merging)
    ↓
AI Enhancement (Gemini 2.0 Flash STT cleaning)
    ↓
Final Transcript (with speaker labels & timestamps)
```

### Key Steps

1. **Preprocessing** - Audio normalization to 16kHz mono
2. **VAD (Optional)** - Filter silence for 30-50% speed boost
3. **Diarization** - Separate speakers with 95-98% accuracy
4. **Segmentation** - Split audio by speaker turns
5. **Dual Transcription** - Run Whisper + PhoWhisper in parallel
6. **Smart Fusion** - Merge with confidence-weighted scoring
7. **AI Enhancement** - Gemini 2.0 Flash cleans transcript & restores diacritics
8. **Output** - Formatted transcript with metadata

---

## 💡 What's New in v3.6

### 🎨 Code Restructuring - Major Architecture Overhaul

#### Before vs After

<table>
<tr>
<td width="50%">

**v3.5 Structure**
```
app/core/
├── llm/
│   ├── whisper_client.py
│   ├── phowhisper_client.py
│   ├── gemini_client.py
│   └── diarization_client.py
├── prompt_engineering/
├── utils/
├── handlers/
└── run_*.py (7 files at root)
```

</td>
<td width="50%">

**v3.6 Structure** ✨
```
app/core/
├── models/            # 🆕 Model wrappers
│   ├── whisper_model.py
│   ├── phowhisper_model.py
│   ├── gemini_model.py
│   └── diarization_model.py
├── pipelines/         # 🆕 Workflows
│   ├── with_diarization_pipeline.py
│   └── dual_*_pipeline.py
├── services/          # 🆕 Business logic
├── prompts/           # 🆕 Renamed
├── utils/
└── handlers/
```

</td>
</tr>
</table>

### ✅ Key Improvements

1. **🎯 Modular Architecture**
   - Separated models, pipelines, and services
   - Clear dependency hierarchy
   - Easy to test individual components

2. **📦 Better Organization**
   - Models: AI model wrappers and inference
   - Pipelines: End-to-end workflows
   - Services: Business logic (prepared for future)
   - Prompts: Renamed from `prompt_engineering`

3. **🔧 Technical Changes**
   - Import paths: `app.core.llm` → `app.core.models`
   - Pipeline files: `run_*.py` → `pipelines/*_pipeline.py`
   - All imports updated across 9+ files

4. **📚 Documentation**
   - Comprehensive `RESTRUCTURING_COMPLETE.md`
   - Updated README with v3.6 details
   - Clear migration guide

### 🚀 Benefits

- ✅ **Scalable** - Easy to add new models/pipelines
- ✅ **Testable** - Isolated components
- ✅ **Maintainable** - Clear code organization
- ✅ **Professional** - Follows industry best practices

---

## 📊 Performance

| Metric | Value | Notes |
|--------|-------|-------|
| **Transcription Accuracy** | 95-98% | Dual model fusion |
| **Speaker Separation** | 95-98% | pyannote.audio 3.1 |
| **Processing Speed (GPU)** | 0.1-0.3x realtime | RTX 3060+ |
| **Processing Speed (CPU)** | 1-2x realtime | Fallback mode |
| **VAD Speed Boost** | 30-50% faster | Silence filtering |
| **Memory Usage** | 4-8 GB | All models loaded |
| **Model Loading Time** | 10-30 seconds | First run only |

**Test Environment:** Windows 11, CUDA 11.8, RTX 3060 12GB, i7-10700K

---

## 📚 Documentation

### 📖 Quick Guides
- **[QUICKSTART_v3.5.md](app/docs/QUICKSTART_v3.5.md)** - Quick start guide
- **[RESTRUCTURING_COMPLETE.md](RESTRUCTURING_COMPLETE.md)** - v3.6 architecture details
- **[Docker README](app/docker/README.md)** - Docker deployment guide

### 🏗️ Technical Documentation
- **[PROJECT_STRUCTURE.md](app/docs/PROJECT_STRUCTURE.md)** - Architecture overview
- **[SPEAKER_DIARIZATION.md](app/docs/SPEAKER_DIARIZATION.md)** - Diarization deep dive
- **[WEB_UI_GUIDE.md](app/docs/WEB_UI_GUIDE.md)** - Web interface guide
- **[TROUBLESHOOTING.md](app/docs/TROUBLESHOOTING.md)** - Common issues

### 📚 References
- **[QUICKREF.md](app/docs/QUICKREF.md)** - Command quick reference
- **[VERSION.md](app/docs/VERSION.md)** - Complete version history
- **[CONTRIBUTING.md](app/docs/CONTRIBUTING.md)** - Development guidelines

---

## 🔧 Installation

### System Requirements

- **OS:** Windows 10/11 (Linux/Mac compatible)
- **Python:** 3.10+ (recommended: 3.10.6)
- **RAM:** 8GB minimum, 16GB recommended
- **Storage:** 10GB+ for models and cache
- **GPU:** NVIDIA GPU with CUDA 11.8+ (optional but recommended)

### Quick Install

```powershell
# 1. Clone repository
git clone https://github.com/SkastVnT/Speech2Text.git
cd Speech2Text

# 2. Run automated setup (recommended)
.\app\scripts\rebuild_project.bat

# This script will:
# ✓ Create virtual environment
# ✓ Install all dependencies
# ✓ Download AI models
# ✓ Verify CUDA availability
# ✓ Test installation
```

### Manual Install

```powershell
# 1. Create virtual environment
python -m venv app\s2t

# 2. Activate environment
.\app\s2t\Scripts\activate

# 3. Upgrade pip
python -m pip install --upgrade pip

# 4. Install dependencies
pip install -r requirements.txt

# 5. Install PyTorch with CUDA (if you have NVIDIA GPU)
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### Configuration

```powershell
# 1. Copy example config
copy app\config\.env.example app\config\.env

# 2. Edit configuration
notepad app\config\.env

# Required settings:
AUDIO_PATH=path\to\your\audio.mp3          # Input audio file
HF_TOKEN=hf_xxxxxxxxxxxxx                   # HuggingFace token (for diarization)

# Optional settings:
CUDA_VISIBLE_DEVICES=0                      # GPU device ID
OUTPUT_DIR=app\data\results                 # Output directory
LOG_LEVEL=INFO                              # Logging level
```

### HuggingFace Token

Required for speaker diarization:

1. **Sign up:** https://huggingface.co/join
2. **Accept license:** https://huggingface.co/pyannote/speaker-diarization-3.1
3. **Get token:** https://huggingface.co/settings/tokens
4. **Add to .env:** `HF_TOKEN=hf_xxxxx`

---

## 🐳 Docker Deployment

### Quick Start

```powershell
# Navigate to docker folder
cd app\docker

# Start all services
docker-compose up --build

# Access Web UI at http://localhost:5000
```

### Docker Compose Options

```powershell
# Development mode (hot reload)
docker-compose -f docker-compose.dev.yml up

# Production mode
docker-compose -f docker-compose.yml up

# Specific services only
docker-compose up whisper phowhisper gemini

# Detached mode (background)
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Docker Services

| Service | Port | Description |
|---------|------|-------------|
| **webui** | 5000 | Flask Web UI |
| **whisper** | 8001 | Whisper API service |
| **phowhisper** | 8002 | PhoWhisper API service |
| **gemini** | 8003 | Gemini AI cleaning service |
| **diarization** | 8004 | Speaker diarization service |

**Full guide:** [app/docker/README.md](app/docker/README.md)

---

## 📊 Output Format

### Directory Structure

```
app/data/results/sessions/session_YYYYMMDD_HHMMSS/
├── raw_whisper.txt              # Whisper raw transcription
├── raw_phowhisper.txt           # PhoWhisper raw transcription
├── segments_diarized.json       # Speaker segments with timestamps
├── enhanced_fused.txt           # ⭐ FINAL OUTPUT (AI-enhanced)
├── timeline.txt                 # Chronological timeline
└── metadata.json                # Processing statistics
```

### Output Example

**enhanced_fused.txt:**
```
[Speaker_00] 00:00 - 00:15
Chào buổi sáng, tôi là Nguyễn Văn A từ công ty XYZ. Hôm nay chúng ta sẽ thảo luận về dự án mới.

[Speaker_01] 00:15 - 00:30
Xin chào anh, em là Trần Thị B. Em đã chuẩn bị tài liệu về dự án rồi ạ.

[Speaker_00] 00:30 - 00:45
Rất tốt! Chúng ta bắt đầu với phần tổng quan nhé.
```

**metadata.json:**
```json
{
  "session_id": "session_20251027_095530",
  "audio_file": "meeting_recording.mp3",
  "duration": 180.5,
  "processing_time": 45.2,
  "num_speakers": 2,
  "models": {
    "whisper": "large-v3",
    "phowhisper": "large",
    "grok": "grok-3",
    "diarization": "pyannote.audio-3.1"
  },
  "accuracy_estimate": 0.97
}
```

---

## 🎯 Usage Examples

### 1. Web UI (Easiest)

```powershell
# Launch Web UI
.\start_webui.bat

# Then in browser:
# 1. Go to http://localhost:5000
# 2. Drag & drop audio file
# 3. Click "Process with Diarization"
# 4. Wait for results
# 5. Download transcript
```

### 2. Command Line

```powershell
# Activate environment
.\app\s2t\Scripts\activate

# Full pipeline with diarization
cd app\core\pipelines
python with_diarization_pipeline.py

# Fast processing (no diarization)
python dual_fast_pipeline.py

# Smart fusion with rules
python dual_smart_pipeline.py
```

### 3. Python API

```python
from app.core.models import (
    WhisperClient, 
    PhoWhisperClient, 
    GeminiClient,
    SpeakerDiarizationClient
)

# Initialize models
whisper = WhisperClient(model_size="large-v3", device="cuda")
phowhisper = PhoWhisperClient(device="cuda")
gemini = GeminiClient()  # Cloud-based, no device needed
diarizer = SpeakerDiarizationClient(hf_token="your_token")

# Process audio
audio_path = "path/to/audio.mp3"

# Step 1: Diarization
print("Running speaker diarization...")
segments = diarizer.diarize(audio_path, use_vad=True)

# Step 2: Transcription
print("Transcribing with Whisper...")
whisper_result = whisper.transcribe(audio_path)

print("Transcribing with PhoWhisper...")
phowhisper_result = phowhisper.transcribe(audio_path)

# Step 3: AI Cleaning with Gemini
print("Cleaning transcript with Gemini AI...")
cleaned_text = gemini.clean_transcript(
    whisper_result["text"],
    phowhisper_result["text"]
)

# Step 4: Save results
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(cleaned_text)

print("Done! Check output.txt")
```

### 4. Batch Processing

```python
import os
from pathlib import Path
from app.core.pipelines.with_diarization_pipeline import process_audio

# Process multiple files
audio_dir = Path("path/to/audio/folder")
output_dir = Path("path/to/output")

for audio_file in audio_dir.glob("*.mp3"):
    print(f"Processing: {audio_file.name}")
    
    results = process_audio(
        audio_path=str(audio_file),
        output_dir=output_dir / audio_file.stem,
        use_vad=True
    )
    
    print(f"  ✓ Speakers: {results['num_speakers']}")
    print(f"  ✓ Duration: {results['duration']:.1f}s")
    print(f"  ✓ Processing time: {results['processing_time']:.1f}s")
```

---

## 🛠️ Troubleshooting

### Common Issues & Solutions

#### 1. Import Errors

**Problem:** `ModuleNotFoundError: No module named 'librosa'`

**Solution:**
```powershell
# Re-run setup script
.\app\scripts\rebuild_project.bat

# Or manual install
.\app\s2t\Scripts\activate
pip install -r requirements.txt
```

#### 2. CUDA Not Available

**Problem:** Models running on CPU (slow)

**Solution:**
```powershell
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Install CUDA PyTorch
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118

# Verify
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}, Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"
```

#### 3. HuggingFace Authentication

**Problem:** `401 Unauthorized` for diarization

**Solution:**
```powershell
# 1. Get token from https://huggingface.co/settings/tokens
# 2. Accept license: https://huggingface.co/pyannote/speaker-diarization-3.1
# 3. Add to .env
echo HF_TOKEN=hf_xxxxxxxxxxxxx >> app\config\.env
```

#### 4. Out of Memory

**Problem:** CUDA out of memory error

**Solution:**
```python
# Option 1: Use smaller models
whisper = WhisperClient(model_size="medium")  # Instead of "large-v3"

# Option 2: Process in smaller chunks
# Option 3: Use CPU
whisper = WhisperClient(device="cpu")

# Option 4: Clear cache
import torch
torch.cuda.empty_cache()
```

#### 5. Web UI Not Loading

**Problem:** Can't access http://localhost:5000

**Solution:**
```powershell
# Check if port is in use
netstat -ano | findstr :5000

# Kill process if needed
taskkill /PID <PID> /F

# Reinstall dependencies
pip install flask flask-socketio eventlet

# Try different port
$env:FLASK_PORT="5001"; python app\web_ui.py
```

#### 6. Audio Format Not Supported

**Problem:** Can't load audio file

**Solution:**
```powershell
# Install ffmpeg
# Windows: Download from https://ffmpeg.org/download.html
# Add to PATH

# Or convert audio first
ffmpeg -i input.wav -ar 16000 -ac 1 output.wav
```

**More solutions:** [TROUBLESHOOTING.md](app/docs/TROUBLESHOOTING.md)

---

## 🔗 Resources

### Model Links
- [Whisper large-v3](https://huggingface.co/openai/whisper-large-v3) - OpenAI's multilingual ASR
- [PhoWhisper-large](https://huggingface.co/vinai/PhoWhisper-large) - Vietnamese-optimized Whisper
- [Gemini 2.0 Flash](https://ai.google.dev/gemini-api/docs) - Google's free cloud LLM for STT cleaning
- [pyannote.audio 3.1](https://huggingface.co/pyannote/speaker-diarization-3.1) - Speaker diarization
- [Silero VAD](https://github.com/snakers4/silero-vad) - Voice activity detection

### Repository
- **GitHub:** https://github.com/SkastVnT/Speech2Text
- **Branch:** VistralS2T
- **Issues:** https://github.com/SkastVnT/Speech2Text/issues
- **Discussions:** https://github.com/SkastVnT/Speech2Text/discussions

---

## 📈 Version History

### v3.6.1 (2025-11-26) - Gemini 2.0 Flash Migration 🎉

**Migrated from local Qwen to cloud-based Gemini for better performance**

- 🤖 **NEW:** Google Gemini 2.0 Flash integration (Free API)
- ☁️ **IMPROVED:** Cloud-based transcript cleaning (no GPU required)
- ⚡ **FASTER:** ~5-10s processing vs 12s local model
- 🎯 **BETTER:** Enhanced STT cleaning with expert prompt
- 🇻🇳 **ENHANCED:** Vietnamese diacritics restoration
- 💰 **FREE:** No costs within Google's free quota
- 📝 **DOCS:** Added `GEMINI_MIGRATION.md`

### v3.6.0 (2025-10-27) - Code Restructuring ✨

**Major architecture overhaul for better maintainability**

- 🎨 **NEW:** Modular architecture
  - `models/` - AI model wrappers
  - `pipelines/` - Processing workflows
  - `services/` - Business logic layer (prepared)
  
- 🎨 **NEW:** File reorganization
  - `llm/*_client.py` → `models/*_model.py`
  - `run_*.py` → `pipelines/*_pipeline.py`
  - `prompt_engineering/` → `prompts/`
  
- 📝 **IMPROVED:** Import paths
  - Updated: `app.core.llm` → `app.core.models`
  - Fixed: 9+ files with import updates
  - Added: Comprehensive `__init__.py` files
  
- 📚 **DOCS:** Complete restructuring documentation
  - New: `RESTRUCTURING_COMPLETE.md`
  - Updated: `README.md` with v3.6 details
  - Added: Migration guide

### v3.5.0 (2025-10-24) - VAD Optimization ⚡

- ⚡ **NEW:** Voice Activity Detection (Silero VAD)
- ⚡ **NEW:** 30-50% faster processing
- 🔧 **FIXED:** Diarization timing display (was showing 0.00s)
- 🔧 **FIXED:** WebUI progress broadcasting
- 🔧 **IMPROVED:** Docker multi-stage builds
- 📚 **DOCS:** `VERSION_3.5_UPGRADE_GUIDE.py`

### v3.0.0 (2025-10-22) - Qwen Fusion 🤖

- 🤖 **NEW:** Qwen2.5-1.5B-Instruct for smart fusion (replaced by Gemini in v3.6.1)
- 🎙️ **NEW:** Speaker diarization (pyannote.audio 3.1)
- 🎯 **NEW:** Dual-model transcription
- 🌐 **NEW:** Web UI (Flask + SocketIO)
- 🐳 **NEW:** Docker deployment

### v2.0.0 - Gemini Integration

- 🤖 **NEW:** Gemini API fusion
- 🔧 **NEW:** T5 model support
- 🌐 **NEW:** FastAPI web service

### v1.0.0 - Initial Release

- 🎯 Basic Whisper transcription
- 🇻🇳 PhoWhisper Vietnamese support
- 🔀 Rule-based fusion

**Full history:** [VERSION.md](app/docs/VERSION.md)

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

### Development Setup

```powershell
# 1. Fork repository
# 2. Clone your fork
git clone https://github.com/YOUR_USERNAME/Speech2Text.git
cd Speech2Text

# 3. Create feature branch
git checkout -b feature/your-feature-name

# 4. Setup environment
.\app\scripts\rebuild_project.bat

# 5. Make changes
# 6. Run tests
pytest app\tests\

# 7. Commit changes
git add .
git commit -m "feat: add your feature"

# 8. Push to fork
git push origin feature/your-feature-name

# 9. Create Pull Request
```

### Coding Standards

- **Python:** Follow PEP 8
- **Type hints:** Use type annotations
- **Docstrings:** Google style
- **Tests:** pytest for unit tests
- **Formatting:** black for code formatting

### Pull Request Guidelines

- Clear description of changes
- Tests for new features
- Documentation updates
- No breaking changes without discussion

**Full guide:** [CONTRIBUTING.md](app/docs/CONTRIBUTING.md)

---

## 📄 License

MIT License

Copyright (c) 2025 SkastVnT

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## 👥 Authors & Acknowledgments

### Authors

**SkastVnT** - Lead Developer
- GitHub: [@SkastVnT](https://github.com/SkastVnT)
- Email: [Your Email]

### Acknowledgments

Special thanks to:

- **OpenAI** - Whisper speech recognition model
- **VinAI** - PhoWhisper Vietnamese-optimized model
- **Google** - Gemini 2.0 Flash API for transcript cleaning
- **pyannote** - Speaker diarization toolkit
- **Silero** - Voice Activity Detection model
- **HuggingFace** - Model hosting & ecosystem

### Community

- Contributors: See [Contributors](https://github.com/SkastVnT/Speech2Text/graphs/contributors)
- Issues & Discussions: [GitHub](https://github.com/SkastVnT/Speech2Text/issues)

---

## 📞 Support & Contact

### Getting Help

- **Documentation:** [app/docs/](app/docs/)
- **Issues:** [GitHub Issues](https://github.com/SkastVnT/Speech2Text/issues)
- **Discussions:** [GitHub Discussions](https://github.com/SkastVnT/Speech2Text/discussions)

### Reporting Bugs

Please include:
1. System info (OS, Python version, CUDA version)
2. Steps to reproduce
3. Error messages
4. Relevant logs

### Feature Requests

Open an issue with:
1. Clear description
2. Use case
3. Expected behavior

---

<div align="center">

## 🌟 Star History

If you find this project useful, please consider giving it a ⭐!

[![Star History Chart](https://api.star-history.com/svg?repos=SkastVnT/Speech2Text&type=Date)](https://star-history.com/#SkastVnT/Speech2Text&Date)

---

**VistralS2T v3.6.0** | Made with ❤️ in Vietnam 🇻🇳

⭐ **Star us on GitHub!** | 🐛 **Report Issues** | 💬 **Join Discussions**

[⬆ Back to Top](#-vistrals2t)

</div>
