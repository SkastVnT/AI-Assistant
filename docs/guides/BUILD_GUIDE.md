# 🔨 BUILD GUIDE - AI-ASSISTANT PROJECT

> **Comprehensive build guide for all services**  
> **Updated:** 06/11/2025  
> **Version:** 1.0.0

---

## 📋 Table of Contents

1. [Quick Start](#-quick-start)
2. [System Requirements](#-system-requirements)
3. [Service-by-Service Guide](#-service-by-service-guide)
4. [Common Issues & Solutions](#-common-issues--solutions)
5. [Testing & Validation](#-testing--validation)
6. [Production Deployment](#-production-deployment)

---

## 🚀 Quick Start

### Prerequisites: Install pyenv First!

Before building any service, install **pyenv** for Python version management:

```powershell
# Using pip (recommended)
pip install pyenv-win --target %USERPROFILE%\.pyenv

# Add to PATH (PowerShell as Administrator)
[System.Environment]::SetEnvironmentVariable('PYENV',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")
[System.Environment]::SetEnvironmentVariable('PYENV_ROOT',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")
[System.Environment]::SetEnvironmentVariable('PYENV_HOME',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")

$Path = [System.Environment]::GetEnvironmentVariable('PATH', "User")
[System.Environment]::SetEnvironmentVariable('PATH', $Path + ";" + $env:USERPROFILE + "\.pyenv\pyenv-win\bin;" + $env:USERPROFILE + "\.pyenv\pyenv-win\shims", "User")

# Restart terminal and verify
pyenv --version
```

See [pyenv Installation Guide](#-installing-pyenv-for-windows) for detailed instructions.

---

### Quick Build - All Services

#### Step 1: Install Python Versions

```bash
# Install Python 3.10.11 (for Text2SQL, Document Intelligence, Speech2Text)
pyenv install 3.10.11

# Install Python 3.11.9 (for ChatBot, Stable Diffusion)
pyenv install 3.11.9

# Verify
pyenv versions
```

#### Step 2: Build Each Service

```bash
# ChatBot (Python 3.11.9)
cd ChatBot
pyenv local 3.11.9
pyenv exec python -m venv venv_chatbot
.\venv_chatbot\Scripts\activate
pip install -r requirements.txt

# Text2SQL (Python 3.10.11)
cd "Text2SQL Services"
pyenv local 3.10.11
pyenv exec python -m venv Text2SQL
.\Text2SQL\Scripts\activate
pip install -r requirements.txt

# Document Intelligence (Python 3.10.11)
cd "Document Intelligence Service"
pyenv local 3.10.11
pyenv exec python -m venv venv
.\venv\Scripts\activate
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
pip install -r requirements.txt

# Speech2Text (Python 3.10.11)
cd "Speech2Text Services"
pyenv local 3.10.11
pyenv exec python -m venv venv
.\venv\Scripts\activate
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
pip install -r requirements.txt

# Stable Diffusion (Python 3.11.9)
cd stable-diffusion-webui
pyenv local 3.11.9
.\webui-user.bat  # Auto-creates venv
```

---

### Or Use Automated Build Scripts

```bash
# Navigate to each service and run:

# ChatBot
cd ChatBot
pyenv local 3.11.9
build-service-chatbot.bat

# Text2SQL
cd "Text2SQL Services"
pyenv local 3.10.11
build-service-text2sql.bat

# Document Intelligence
cd "Document Intelligence Service"
pyenv local 3.10.11
build-service-document-intelligence.bat

# Speech2Text
cd "Speech2Text Services"
pyenv local 3.10.11
build-service-speech2text.bat

# Stable Diffusion
cd stable-diffusion-webui
pyenv local 3.11.9
build-service-stable-diffusion.bat
```

Each script will:
✅ Check Python version (via pyenv)  
✅ Create/activate virtual environment  
✅ Install/verify dependencies  
✅ Run tests (if available)  
✅ Configure directories  
✅ Validate critical packages  

---

## 💻 System Requirements

### Minimum Requirements

| Component | Minimum | Recommended |
|:----------|:--------|:------------|
| **OS** | Windows 10 64-bit | Windows 11 64-bit |
| **Python** | 3.10.x / 3.11.x (see below) | Latest stable |
| **pyenv** | Latest | Latest |
| **RAM** | 8GB | 16GB+ |
| **Storage** | 50GB free | 100GB+ SSD |
| **GPU** | None (CPU mode) | NVIDIA GPU 6GB+ VRAM |

### Python Version Requirements (pyenv)

| Service | Python Version | Reason |
|:--------|:--------------|:-------|
| **ChatBot** | **3.11.x** | Better performance with transformers |
| **Text2SQL** | **3.10.x** | Stable with Gemini SDK |
| **Document Intelligence** | **3.10.x** | PaddleOCR compatibility |
| **Speech2Text** | **3.10.x** | PyTorch 2.0 compatibility |
| **Stable Diffusion** | **3.11.x** | AUTOMATIC1111 WebUI optimization |

**⚠️ IMPORTANT:** We use **pyenv** to manage Python versions per service. This prevents version conflicts between services.

### Service-Specific Requirements

#### ChatBot
- **RAM:** 4GB minimum, 8GB recommended
- **GPU:** Optional (for local models like Llama)
- **Storage:** 10GB (20GB with local models)

#### Text2SQL
- **RAM:** 4GB minimum
- **GPU:** Not required
- **Storage:** 5GB

#### Document Intelligence
- **RAM:** 4GB minimum
- **GPU:** Not required (PaddleOCR is CPU-optimized)
- **Storage:** 5GB (includes OCR models ~200MB)

#### Speech2Text
- **RAM:** 8GB minimum, 16GB recommended
- **GPU:** NVIDIA GPU with 4GB+ VRAM (highly recommended)
- **Storage:** 15GB (models ~5GB)
- **CUDA:** 11.8 or 12.1

#### Stable Diffusion
- **RAM:** 8GB minimum
- **GPU:** **REQUIRED** - NVIDIA GPU with 4GB+ VRAM (6GB+ recommended)
- **Storage:** 30GB+ (models 2-7GB each)
- **CUDA:** 11.8 or 12.1

---

## � Python Version Management with pyenv

### Why pyenv?

Different services require different Python versions:
- **ChatBot & Stable Diffusion** work best with **Python 3.11.x**
- **Other services** require **Python 3.10.x** for compatibility

Using **pyenv** allows us to:
✅ Install multiple Python versions side-by-side  
✅ Switch between versions per project/service  
✅ Avoid version conflicts  
✅ Maintain clean, isolated environments  

---

### 📦 Installing pyenv for Windows

#### Option 1: pyenv-win (Recommended)

```powershell
# Using pip
pip install pyenv-win --target %USERPROFILE%\.pyenv

# Using chocolatey (if installed)
choco install pyenv-win

# Using scoop (if installed)
scoop install pyenv
```

#### Option 2: Manual Installation

```powershell
# Clone repository
git clone https://github.com/pyenv-win/pyenv-win.git %USERPROFILE%\.pyenv

# Add to PATH (PowerShell as Administrator)
[System.Environment]::SetEnvironmentVariable('PYENV',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")
[System.Environment]::SetEnvironmentVariable('PYENV_ROOT',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")
[System.Environment]::SetEnvironmentVariable('PYENV_HOME',$env:USERPROFILE + "\.pyenv\pyenv-win\","User")

$Path = [System.Environment]::GetEnvironmentVariable('PATH', "User")
[System.Environment]::SetEnvironmentVariable('PATH', $Path + ";" + $env:USERPROFILE + "\.pyenv\pyenv-win\bin;" + $env:USERPROFILE + "\.pyenv\pyenv-win\shims", "User")

# Restart terminal
```

#### Verify Installation

```bash
pyenv --version
# Should show: pyenv 3.x.x
```

---

### 🎯 pyenv Quick Reference

#### Essential Commands

```bash
# List available Python versions
pyenv install --list

# Install specific Python version
pyenv install 3.10.11
pyenv install 3.11.9

# List installed versions
pyenv versions

# Set global Python version (system-wide)
pyenv global 3.10.11

# Set local Python version (current directory only)
pyenv local 3.11.9

# Set shell Python version (current terminal session)
pyenv shell 3.10.11

# Check active Python version
pyenv version
python --version

# Uninstall Python version
pyenv uninstall 3.10.11
```

---

### 🔧 Service-Specific Setup with pyenv

#### Recommended Workflow

For each service, we follow this pattern:

```bash
# 1. Navigate to service directory
cd "ServiceName"

# 2. Install required Python version (if not already)
pyenv install 3.x.x

# 3. Set local Python version (creates .python-version file)
pyenv local 3.x.x

# 4. Verify version
python --version

# 5. Create virtual environment using pyenv's Python
pyenv exec python -m venv venv_name

# 6. Activate virtual environment
.\venv_name\Scripts\activate

# 7. Install dependencies
pip install -r requirements.txt
```

---

### 📋 Service Configuration Matrix

| Service | Python | Local Command | Virtual Env Name |
|:--------|:-------|:--------------|:-----------------|
| ChatBot | 3.11.9 | `pyenv local 3.11.9` | `venv_chatbot` |
| Text2SQL | 3.10.11 | `pyenv local 3.10.11` | `Text2SQL` |
| Document Intelligence | 3.10.11 | `pyenv local 3.10.11` | `venv` |
| Speech2Text | 3.10.11 | `pyenv local 3.10.11` | `venv` |
| Stable Diffusion | 3.11.9 | `pyenv local 3.11.9` | (auto-managed) |

---

### 🚀 Step-by-Step: Setting Up All Services

#### 1. Install Python Versions

```bash
# Install Python 3.10.11 (for most services)
pyenv install 3.10.11

# Install Python 3.11.9 (for ChatBot & Stable Diffusion)
pyenv install 3.11.9

# Verify installations
pyenv versions
```

Expected output:
```
* system (set by PYENV_VERSION environment variable)
  3.10.11
  3.11.9
```

#### 2. Configure Each Service

##### ChatBot (Python 3.11.9)

```bash
cd ChatBot

# Set Python 3.11.9 for this directory
pyenv local 3.11.9

# Verify
python --version  # Should show: Python 3.11.9

# Create virtual environment
pyenv exec python -m venv venv_chatbot

# Activate
.\venv_chatbot\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

##### Text2SQL (Python 3.10.11)

```bash
cd "Text2SQL Services"

# Set Python 3.10.11 for this directory
pyenv local 3.10.11

# Verify
python --version  # Should show: Python 3.10.11

# Create virtual environment
pyenv exec python -m venv Text2SQL

# Activate
.\Text2SQL\Scripts\activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

##### Document Intelligence (Python 3.10.11)

```bash
cd "Document Intelligence Service"

# Set Python 3.10.11
pyenv local 3.10.11

# Verify
python --version  # Should show: Python 3.10.11

# Create virtual environment
pyenv exec python -m venv venv

# Activate
.\venv\Scripts\activate

# CRITICAL: Set environment variable
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Install dependencies
pip install --upgrade pip
pip install protobuf==3.20.2
pip install -r requirements.txt
```

##### Speech2Text (Python 3.10.11)

```bash
cd "Speech2Text Services"

# Set Python 3.10.11
pyenv local 3.10.11

# Verify
python --version  # Should show: Python 3.10.11

# Create virtual environment
pyenv exec python -m venv venv

# Activate
.\venv\Scripts\activate

# Install PyTorch first (CRITICAL)
# For CUDA 11.8:
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

# Install remaining dependencies
pip install -r requirements.txt
```

##### Stable Diffusion (Python 3.11.9)

```bash
cd stable-diffusion-webui

# Set Python 3.11.9
pyenv local 3.11.9

# Verify
python --version  # Should show: Python 3.11.9

# Note: Virtual environment is auto-managed by webui.bat
# Just run:
.\webui-user.bat
```

---

### 📝 Understanding .python-version File

When you run `pyenv local 3.x.x`, pyenv creates a `.python-version` file in the current directory.

**Example:**
```bash
cd ChatBot
pyenv local 3.11.9
cat .python-version
# Output: 3.11.9
```

This file tells pyenv which Python version to use when you're in this directory.

**Benefits:**
- Automatic version switching when entering directory
- Project-specific Python versions
- Committed to git for team consistency

---

### 🔄 Switching Between Services

```bash
# Example workflow

# Work on ChatBot (Python 3.11.9)
cd ChatBot
python --version  # Auto-switches to 3.11.9
.\venv_chatbot\Scripts\activate

# Work on Text2SQL (Python 3.10.11)
cd ..\Text2SQL Services
python --version  # Auto-switches to 3.10.11
.\Text2SQL\Scripts\activate

# Work on Document Intelligence (Python 3.10.11)
cd "..\Document Intelligence Service"
python --version  # Auto-switches to 3.10.11
.\venv\Scripts\activate
```

---

### �🛠️ Troubleshooting pyenv

#### Issue 1: "pyenv: command not found"

```bash
# Check if pyenv is in PATH
echo $env:PATH | Select-String "pyenv"

# Re-add to PATH (PowerShell as Administrator)
$Path = [System.Environment]::GetEnvironmentVariable('PATH', "User")
[System.Environment]::SetEnvironmentVariable('PATH', $Path + ";" + $env:USERPROFILE + "\.pyenv\pyenv-win\bin;" + $env:USERPROFILE + "\.pyenv\pyenv-win\shims", "User")

# Restart terminal
```

#### Issue 2: "Version X.X.X is not installed"

```bash
# Install the required version
pyenv install 3.10.11
pyenv install 3.11.9

# Refresh shims
pyenv rehash
```

#### Issue 3: Wrong Python version activated

```bash
# Check which version is active
pyenv version

# Check what set it
pyenv version-origin

# Override with shell
pyenv shell 3.11.9

# Or go to directory and check .python-version file
cat .python-version
```

#### Issue 4: pyenv not switching versions automatically

```bash
# Ensure .python-version file exists
ls -la | Select-String ".python-version"

# If missing, create it
pyenv local 3.11.9

# Refresh shims
pyenv rehash

# Restart terminal
```

#### Issue 5: "python" command not found after pyenv install

```bash
# Rehash shims
pyenv rehash

# Check global version
pyenv global

# Set global if needed
pyenv global 3.10.11

# Verify
python --version
```

---

### 💡 Best Practices

#### 1. Always Use `pyenv local` in Service Directories

```bash
# Good ✅
cd ChatBot
pyenv local 3.11.9

# Avoid ❌
pyenv global 3.11.9  # Affects all projects!
```

#### 2. Use `pyenv exec` for Virtual Environment Creation

```bash
# Good ✅
pyenv exec python -m venv venv_chatbot

# Avoid ❌
python -m venv venv_chatbot  # May use wrong Python version
```

#### 3. Check Python Version Before Installing Dependencies

```bash
# Always verify first
python --version
pyenv version

# Then install
pip install -r requirements.txt
```

#### 4. Commit .python-version to Git

```bash
# Add to each service directory
git add .python-version
git commit -m "Add Python version specification"
```

#### 5. Document Version Requirements

Each service should have its Python version documented:
- In `README.md`
- In `.python-version` file
- In build scripts

---

### 📊 Quick Comparison: Before vs After pyenv

#### Before (Manual Python Management)

```
Problems:
❌ One global Python version for all services
❌ Version conflicts between services
❌ Need to manually track which service needs which version
❌ Difficult to switch between projects
❌ Requires multiple Python installations in different folders
```

#### After (With pyenv)

```
Benefits:
✅ Automatic version switching per directory
✅ Clean, centralized Python version management
✅ Easy to install/uninstall versions
✅ .python-version file ensures consistency
✅ Team members use same Python version
✅ Simple workflow: cd → pyenv auto-switches
```

---



### 1️⃣ ChatBot Service

**Required Python Version:** 3.11.9 (managed by pyenv)

#### Build Steps with pyenv

```bash
cd ChatBot

# Step 1: Install Python 3.11.9 (if not already installed)
pyenv install 3.11.9

# Step 2: Set local Python version (creates .python-version)
pyenv local 3.11.9

# Step 3: Verify Python version
python --version  # Should show: Python 3.11.9
pyenv version     # Confirm pyenv is managing it

# Step 4: Create virtual environment using pyenv's Python
pyenv exec python -m venv venv_chatbot

# Step 5: Activate virtual environment
.\venv_chatbot\Scripts\activate

# Step 6: Upgrade pip
python -m pip install --upgrade pip

# Step 7: Install dependencies
pip install -r requirements.txt
```

#### Or Use Build Script

```bash
cd ChatBot

# Make sure Python 3.11.9 is set first
pyenv local 3.11.9

# Run build script
build-service-chatbot.bat
```

**⚠️ Note:** The build script will check for Python 3.10+. With pyenv, ensure you run `pyenv local 3.11.9` before running the script.

#### Configuration

Create `.env` file:

```env
# Required: At least one AI API key
GEMINI_API_KEY=your_gemini_api_key_here
# OR
OPENAI_API_KEY=your_openai_api_key_here

# Optional: Image generation
STABILITY_API_KEY=your_stability_api_key_here

# Optional: Local model path
LOCAL_MODEL_PATH=models/llama-2-7b-chat

# Optional: Stable Diffusion API
SD_API_URL=http://localhost:7860
```

#### Running

```bash
# Start service
start_chatbot.bat

# Or manually
python app.py
```

Access at: **http://localhost:5001**

#### Common Issues

**Issue 1: PyTorch installation fails**

```bash
# Install PyTorch separately
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

**Issue 2: bitsandbytes fails on Windows**

```
# Windows requires Visual C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/

# Or skip bitsandbytes (not required for basic functionality)
pip install -r requirements.txt --no-deps
pip install flask flask-cors python-dotenv openai google-generativeai Pillow requests
```

**Issue 3: Gemini API errors**

```python
# Test API key
python -c "import google.generativeai as genai; genai.configure(api_key='YOUR_KEY'); print(genai.list_models())"
```

---

### 2️⃣ Text2SQL Service

**Required Python Version:** 3.10.11 (managed by pyenv)

#### Build Steps with pyenv

```bash
cd "Text2SQL Services"

# Step 1: Install Python 3.10.11 (if not already installed)
pyenv install 3.10.11

# Step 2: Set local Python version
pyenv local 3.10.11

# Step 3: Verify Python version
python --version  # Should show: Python 3.10.11

# Step 4: Create virtual environment
pyenv exec python -m venv Text2SQL

# Step 5: Activate virtual environment
.\Text2SQL\Scripts\activate

# Step 6: Upgrade pip
python -m pip install --upgrade pip

# Step 7: Install dependencies
pip install -r requirements.txt
```

#### Or Use Build Script

```bash
cd "Text2SQL Services"

# Set Python version first
pyenv local 3.10.11

# Run build script
build-service-text2sql.bat
```

#### Configuration

Create `.env` file:

```env
# Required
GEMINI_API_KEY_1=your_primary_gemini_key
GEMINI_API_KEY_2=your_fallback_gemini_key  # Optional

# Database connections (optional)
CLICKHOUSE_HOST=localhost
CLICKHOUSE_PORT=8123
MONGODB_URI=mongodb://localhost:27017
```

#### Running

```bash
# Recommended (simplified version)
python app_simple.py

# Or full version
python app.py
```

Access at: **http://localhost:5002**

#### Common Issues

**Issue 1: ClickHouse connection fails**

```python
# Test connection
import clickhouse_connect

client = clickhouse_connect.get_client(
    host='localhost',
    port=8123,
    username='default',
    password=''
)

print(client.command('SELECT version()'))
```

**Issue 2: MongoDB connection fails**

```python
# Test connection
from pymongo import MongoClient

client = MongoClient('mongodb://localhost:27017/')
print(client.server_info())
```

**Issue 3: Knowledge Base not saving**

```bash
# Check directory exists
mkdir data\knowledge_base

# Check file permissions
icacls data\knowledge_base
```

---

### 3️⃣ Document Intelligence Service

**Required Python Version:** 3.10.11 (managed by pyenv)

#### Build Steps with pyenv

```bash
cd "Document Intelligence Service"

# Step 1: Install Python 3.10.11 (if not already installed)
pyenv install 3.10.11

# Step 2: Set local Python version
pyenv local 3.10.11

# Step 3: Verify Python version
python --version  # Should show: Python 3.10.11

# Step 4: Create virtual environment
pyenv exec python -m venv venv

# Step 5: Activate virtual environment
.\venv\Scripts\activate

# Step 6: CRITICAL - Set environment variable
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

# Step 7: Upgrade pip
python -m pip install --upgrade pip

# Step 8: Install protobuf first (critical for PaddlePaddle)
pip install protobuf==3.20.2

# Step 9: Install remaining dependencies
pip install -r requirements.txt
```

#### Or Use Build Script

```bash
cd "Document Intelligence Service"

# Set Python version first
pyenv local 3.10.11

# Run build script (handles env variable automatically)
build-service-document-intelligence.bat
```

#### **CRITICAL:** Environment Variable

```bash
# MUST set this before running the service!
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

**Permanent Fix:** Add to System Environment Variables (Windows Settings → Environment Variables)

#### Configuration

Create `.env` file:

```env
GEMINI_API_KEY=your_gemini_api_key_here

# Optional: OCR settings
OCR_LANGUAGE=vi  # Vietnamese
OCR_USE_ANGLE_CLS=true
OCR_USE_GPU=false
```

#### Running

```bash
# Windows (sets env var automatically)
start_service.bat

# Or manually
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
python app.py
```

Access at: **http://localhost:5003**

#### Common Issues

**Issue 1: protobuf version error**

```
RuntimeError: Protobuf C++ implementation is not supported on Windows
```

**Solution:**

```bash
# Reinstall protobuf
pip uninstall protobuf -y
pip install protobuf==3.20.2

# Set environment variable
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python
```

**Issue 2: PaddleOCR model download fails**

```bash
# Models auto-download to:
# C:\Users\{username}\.paddleocr\whl\

# Manual download from:
# https://paddleocr.bj.bcebos.com/PP-OCRv4/chinese/

# Place in: .paddleocr/whl/ directory
```

**Issue 3: opencv-python import error**

```bash
# Reinstall opencv-python
pip uninstall opencv-python -y
pip install opencv-python==4.6.0.66
```

---

### 4️⃣ Speech2Text Service

**Required Python Version:** 3.10.11 (managed by pyenv)

#### Build Steps with pyenv

```bash
cd "Speech2Text Services"

# Step 1: Install Python 3.10.11 (if not already installed)
pyenv install 3.10.11

# Step 2: Set local Python version
pyenv local 3.10.11

# Step 3: Verify Python version
python --version  # Should show: Python 3.10.11

# Step 4: Create virtual environment
pyenv exec python -m venv venv

# Step 5: Activate virtual environment
.\venv\Scripts\activate

# Step 6: Upgrade pip
python -m pip install --upgrade pip

# Step 7: Install PyTorch FIRST (CRITICAL - choose based on GPU)
# For CUDA 11.8:
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118

# For CPU only:
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cpu

# Step 8: Install remaining dependencies
pip install -r requirements.txt
```

#### Or Use Build Script

```bash
cd "Speech2Text Services"

# Set Python version first
pyenv local 3.10.11

# Run build script (auto-detects CUDA)
build-service-speech2text.bat
```

#### Prerequisites

1. **CUDA Toolkit** (if using GPU - highly recommended):
   - Download: https://developer.nvidia.com/cuda-downloads
   - Version: 11.8 or 12.1
   - Verify: `nvidia-smi`

2. **HuggingFace Account** (required for speaker diarization):
   - Sign up: https://huggingface.co/join
   - Create token: https://huggingface.co/settings/tokens
   - Accept licenses:
     - https://huggingface.co/pyannote/speaker-diarization-3.1
     - https://huggingface.co/pyannote/segmentation-3.0

#### Configuration

Create `.env` file:

```env
# Required for speaker diarization
HF_TOKEN=your_huggingface_token_here

# Optional
USE_CUDA=true
WHISPER_MODEL=large-v3
PHOWHISPER_MODEL=base
```

#### Running

```bash
# Start WebUI
start_webui.bat

# Or manually
python app/webui.py
```

Access at: **http://localhost:7860**

#### Common Issues

**Issue 1: pyannote.audio import fails**

```bash
# Reinstall with specific version
pip uninstall pyannote.audio -y
pip install pyannote.audio==3.1.1

# Make sure you accepted licenses on HuggingFace
```

**Issue 2: CUDA out of memory**

```python
# In app/config.py, reduce batch size:
BATCH_SIZE = 8  # Reduce from 16
CHUNK_LENGTH = 20  # Reduce from 30
```

**Issue 3: Models download slow/fail**

```bash
# Set HuggingFace cache directory
set HF_HOME=D:\huggingface_cache  # Use drive with more space

# Use mirror (for China users)
set HF_ENDPOINT=https://hf-mirror.com
```

**Issue 4: Whisper model loading error**

```bash
# Clear cache and redownload
rmdir /s /q %USERPROFILE%\.cache\huggingface
python -c "from faster_whisper import WhisperModel; model = WhisperModel('large-v3')"
```

---

### 5️⃣ Stable Diffusion Service

**Required Python Version:** 3.11.9 (managed by pyenv)

#### Build Steps with pyenv

```bash
cd stable-diffusion-webui

# Step 1: Install Python 3.11.9 (if not already installed)
pyenv install 3.11.9

# Step 2: Set local Python version
pyenv local 3.11.9

# Step 3: Verify Python version
python --version  # Should show: Python 3.11.9

# Step 4: Run build script
build-service-stable-diffusion.bat

# Note: Virtual environment is auto-managed by webui.bat
# The webui.bat script will detect pyenv's Python and create venv automatically
```

#### Or Direct Launch

```bash
cd stable-diffusion-webui

# Set Python version
pyenv local 3.11.9

# Run WebUI (auto-creates venv on first run)
.\webui-user.bat
```

**⚠️ Important:** The AUTOMATIC1111 WebUI manages its own virtual environment. Just ensure Python 3.11.9 is active via pyenv before running `webui-user.bat`.

#### Prerequisites

1. **Git**: https://git-scm.com/download/win
2. **NVIDIA GPU** with 4GB+ VRAM (**REQUIRED** - CPU mode is extremely slow)
3. **CUDA** 11.8 or 12.1
4. **At least one SD model** (~2-7GB)

#### Initial Setup (if repository not cloned yet)

```bash
# Clone AUTOMATIC1111 WebUI
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
cd stable-diffusion-webui

# Set Python version
pyenv install 3.11.9
pyenv local 3.11.9

# Run build script
build-service-stable-diffusion.bat
```

#### Download Models

**Option 1: CivitAI (Recommended)**
- Visit: https://civitai.com/
- Download models (e.g., Anything V5, CounterfeitXL)
- Place `.safetensors` files in: `models/Stable-diffusion/`

**Option 2: HuggingFace**
- Stable Diffusion 1.5: https://huggingface.co/runwayml/stable-diffusion-v1-5
- SDXL 1.0: https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0

**Option 3: Direct Links**
```bash
# Stable Diffusion 1.5 (4GB)
# Download manually from HuggingFace to models/Stable-diffusion/
```

#### Configuration

Edit `webui-user.bat`:

```batch
@echo off

set PYTHON=
set GIT=
set VENV_DIR=
set COMMANDLINE_ARGS=--xformers --opt-sdp-attention --api --listen

call webui.bat
```

**Flags explained:**
- `--xformers`: 20-30% speed boost (NVIDIA only)
- `--opt-sdp-attention`: Memory optimization
- `--api`: Enable REST API
- `--listen`: Allow external connections
- `--port 7861`: Custom port (if 7860 is taken)
- `--medvram`: For 4-6GB VRAM
- `--lowvram`: For <4GB VRAM

#### Running

```bash
# First run (10-20 minutes - downloads PyTorch, xformers, etc.)
webui-user.bat

# Subsequent runs (~30 seconds)
webui-user.bat
```

Access at: **http://localhost:7860**

#### Common Issues

**Issue 1: CUDA out of memory**

```batch
# Add to COMMANDLINE_ARGS in webui-user.bat:
set COMMANDLINE_ARGS=--medvram --opt-split-attention

# Or for very low VRAM:
set COMMANDLINE_ARGS=--lowvram --opt-split-attention
```

**Issue 2: xformers installation fails**

```bash
# Use without xformers
set COMMANDLINE_ARGS=--opt-sdp-attention --api

# Or install manually
pip install xformers==0.0.20
```

**Issue 3: Black images generated**

```
# Common causes:
1. NSFW filter triggered
2. VAE issue
3. Corrupt model

# Solutions:
# 1. Add negative prompts
# 2. Download VAE separately: https://huggingface.co/stabilityai/sd-vae-ft-mse-original
# 3. Re-download model
```

**Issue 4: Slow generation speed**

```batch
# Enable optimizations:
set COMMANDLINE_ARGS=--xformers --opt-sdp-attention --no-half-vae

# Reduce image size (512x512 instead of 1024x1024)
# Use fewer steps (20-30 instead of 50)
```

---

## 🔧 Common Issues & Solutions

### Python Issues

#### Issue: "Python was not found"

```bash
# Add Python to PATH
setx PATH "%PATH%;C:\Python310;C:\Python310\Scripts"

# Or reinstall Python with "Add to PATH" option
```

#### Issue: "python.exe - System Error"

```bash
# Install Visual C++ Redistributable
# Download: https://aka.ms/vs/17/release/vc_redist.x64.exe
```

### Virtual Environment Issues

#### Issue: "cannot be loaded because running scripts is disabled"

```powershell
# Run PowerShell as Administrator
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser

# Then activate venv again
.\venv\Scripts\activate
```

#### Issue: Virtual environment activation fails

```bash
# Use Command Prompt instead of PowerShell
cmd

# Or use Python directly
venv\Scripts\python.exe app.py
```

### Dependency Issues

#### Issue: pip install fails with "permission denied"

```bash
# Run as administrator
# Or use --user flag
pip install --user -r requirements.txt
```

#### Issue: "Could not find a version that satisfies the requirement"

```bash
# Update pip
python -m pip install --upgrade pip setuptools wheel

# Try with --no-cache-dir
pip install --no-cache-dir -r requirements.txt
```

#### Issue: Conflicting dependencies

```bash
# Create fresh virtual environment
deactivate
rmdir /s /q venv
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Network Issues

#### Issue: pip install timeouts

```bash
# Increase timeout
pip install --timeout=1000 -r requirements.txt

# Use mirror (for slow connections)
pip install -i https://pypi.org/simple -r requirements.txt
```

#### Issue: HuggingFace model download fails

```bash
# Set mirror (for China)
set HF_ENDPOINT=https://hf-mirror.com

# Use download tools (aria2, wget)
# Then place in cache: %USERPROFILE%\.cache\huggingface\hub\
```

### GPU Issues

#### Issue: CUDA not detected

```bash
# Check CUDA installation
nvidia-smi

# Check PyTorch CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch with CUDA
pip uninstall torch torchaudio -y
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
```

#### Issue: "CUDA out of memory"

```python
# Reduce batch size, model size, or use CPU
# Add to Python script:
import torch
torch.cuda.empty_cache()

# Or restart service
```

---

## ✅ Testing & Validation

### Automated Testing

Each service includes pytest-based tests:

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_api.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

### Manual Testing

#### ChatBot

```python
# Test API
import requests

response = requests.post('http://localhost:5001/chat', json={
    'message': 'Hello, AI!',
    'model': 'gemini-2.0-flash-exp'
})

print(response.json())
```

#### Text2SQL

```python
# Test SQL generation
import requests

response = requests.post('http://localhost:5002/chat', json={
    'message': 'Show me total sales by month',
    'schema': {...}  # Upload schema first
})

print(response.json()['sql'])
```

#### Document Intelligence

```python
# Test OCR
import requests

files = {'file': open('document.jpg', 'rb')}
response = requests.post('http://localhost:5003/upload', files=files)

print(response.json()['text'])
```

#### Speech2Text

```python
# Test transcription
import requests

files = {'audio': open('audio.mp3', 'rb')}
response = requests.post('http://localhost:7860/transcribe', files=files)

print(response.json()['transcript'])
```

#### Stable Diffusion

```python
# Test image generation
import requests
import base64

payload = {
    'prompt': 'a beautiful sunset over mountains',
    'steps': 20,
    'width': 512,
    'height': 512
}

response = requests.post('http://localhost:7860/sdapi/v1/txt2img', json=payload)
image_data = base64.b64decode(response.json()['images'][0])

with open('output.png', 'wb') as f:
    f.write(image_data)
```

---

## 🚀 Production Deployment

### Checklist

- [ ] All services built and tested
- [ ] .env files configured with production keys
- [ ] Database connections tested
- [ ] API keys have proper quotas
- [ ] Firewall rules configured
- [ ] HTTPS/SSL certificates installed
- [ ] Monitoring and logging enabled
- [ ] Backup strategy in place

### Docker Deployment (Recommended)

```bash
# Build all services
docker-compose build

# Start services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f chatbot
```

### Windows Service Installation

```bash
# Use NSSM (Non-Sucking Service Manager)
# Download: https://nssm.cc/download

# Install service
nssm install ChatBot "C:\path\to\venv\Scripts\python.exe" "C:\path\to\app.py"

# Start service
nssm start ChatBot
```

### Performance Optimization

#### ChatBot
- Use Redis for session caching
- Enable response streaming
- Implement rate limiting

#### Text2SQL
- Cache schema parsing results
- Use connection pooling for databases
- Implement query result caching

#### Document Intelligence
- Batch process multiple documents
- Use worker processes for OCR
- Cache OCR results

#### Speech2Text
- Use GPU for acceleration
- Implement chunked processing
- Pre-load models on startup

#### Stable Diffusion
- Enable xformers
- Use model caching
- Implement queue system for requests

---

## 📞 Support & Resources

### Documentation
- Main README: [../README.md](../README.md)
- Diagrams: [../diagram/](../diagram/)
- API Docs: [../docs/API_DOCUMENTATION.md](../docs/API_DOCUMENTATION.md)

### External Resources
- Python: https://www.python.org/
- PyTorch: https://pytorch.org/
- CUDA Toolkit: https://developer.nvidia.com/cuda-downloads
- HuggingFace: https://huggingface.co/
- CivitAI: https://civitai.com/

### Community
- GitHub Issues: https://github.com/SkastVnT/AI-Assistant/issues
- Discussions: https://github.com/SkastVnT/AI-Assistant/discussions

---

## 📝 Changelog

### Version 1.0.0 (2025-11-06)
- ✨ Initial release
- ✨ Added build scripts for all 5 services
- ✨ Comprehensive troubleshooting guide
- ✨ Automated dependency validation
- ✨ Testing integration

---

<div align="center">

**Made with ❤️ by SkastVnT**

[⬅️ Back to Main README](../README.md)

</div>
