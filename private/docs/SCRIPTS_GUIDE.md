# 🚀 AI Assistant - Quick Start Scripts

Complete collection of batch scripts to manage all services easily.

## 📋 Available Scripts

### 🎯 Individual Service Launchers

| Script | Service | Port | Description |
|--------|---------|------|-------------|
| `start-hub-gateway.bat` | Hub Gateway | 3000 | API Orchestrator |
| `start-chatbot.bat` | ChatBot | 5001 | Multi-Model AI Chat |
| `start-text2sql.bat` | Text2SQL | 5002 | SQL Query Generation |
| `start-document-intelligence.bat` | Document Intelligence | 5003 | OCR + AI Analysis |
| `start-speech2text.bat` | Speech2Text | 7860 | Audio Transcription |
| `start-stable-diffusion.bat` | Stable Diffusion | 7861 | Image Generation |
| `start-lora-training.bat` | LoRA Training | 7862 | Model Fine-tuning |
| `start-image-upscale.bat` | Image Upscale | 7863 | Image Enhancement |

**Usage:**
```bat
REM Start a specific service
start-chatbot.bat
```

---

### 🔥 Batch Operations

| Script | Description |
|--------|-------------|
| `start-all.bat` | Start all 8 services in separate windows |
| `stop-all.bat` | Stop all running services |
| `check-status.bat` | Check which services are running |

**Usage:**
```bat
REM Start everything
start-all.bat

REM Check what's running
check-status.bat

REM Stop everything
stop-all.bat
```

---

### 🛠️ Utilities

| Script | Description |
|--------|-------------|
| `menu.bat` | Interactive menu for all operations |
| `setup-all.bat` | Setup all services with dependencies |
| `test-all.bat` | Run complete test suite (330+ tests) |
| `clean-logs.bat` | Clean all logs and temp files |

**Usage:**
```bat
REM Interactive menu (recommended for beginners)
menu.bat

REM First-time setup
setup-all.bat

REM Run tests
test-all.bat

REM Clean up
clean-logs.bat
```

---

## 🎮 Quick Start Guide

### Option 1: Interactive Menu (Recommended)

```bat
menu.bat
```

The menu provides a user-friendly interface to:
- Start/stop individual services
- Batch operations (start/stop all)
- Check service status
- Run tests and utilities

### Option 2: Start All Services

```bat
start-all.bat
```

This will:
1. Open 8 separate command windows
2. Start all services automatically
3. Show access URLs for each service

### Option 3: Start Specific Services

```bat
REM Start only ChatBot and Stable Diffusion
start-chatbot.bat
start-stable-diffusion.bat
```

---

## 📊 Service Status

Check which services are running:

```bat
check-status.bat
```

Output example:
```
✅ Hub Gateway (Port 3000) - RUNNING
✅ ChatBot (Port 5001) - RUNNING
❌ Text2SQL (Port 5002) - NOT RUNNING
✅ Document Intelligence (Port 5003) - RUNNING
...
```

---

## 🧪 Testing

Run the complete test suite:

```bat
test-all.bat
```

Features:
- 330+ test cases
- 85%+ code coverage
- HTML coverage report (`htmlcov/index.html`)
- Supports offline testing

---

## 🔧 Setup

First-time setup for all services:

```bat
setup-all.bat
```

This will:
1. Install root dependencies
2. Create virtual environments for each service
3. Install service-specific dependencies
4. Download required models (where applicable)

**Note:** This may take 30-60 minutes.

---

## 🧹 Maintenance

### Clean Logs

```bat
clean-logs.bat
```

Removes:
- `resources/logs/`
- `services/*/logs/`
- `services/*/output/`
- `services/*/temp/`
- Python cache (`__pycache__`, `*.pyc`)
- Pytest cache (`.pytest_cache`)

### Stop All Services

```bat
stop-all.bat
```

Cleanly stops all running service windows.

---

## 📖 Service Details

### 🌐 Hub Gateway (Port 3000)
**Script:** `start-hub-gateway.bat`

API orchestrator for routing requests to appropriate services.

### 💬 ChatBot (Port 5001)
**Script:** `start-chatbot.bat`

Multi-model AI chatbot with:
- Gemini 2.0 Flash, GPT-4o Mini, DeepSeek
- Text-to-Image via Stable Diffusion
- MongoDB chat history
- File upload & analysis

### 📊 Text2SQL (Port 5002)
**Script:** `start-text2sql.bat`

Convert natural language to SQL queries using:
- SQLCoder-7B-2 model
- Gemini AI integration
- Schema upload support

### 📄 Document Intelligence (Port 5003)
**Script:** `start-document-intelligence.bat`

OCR and document analysis:
- PaddleOCR (Vietnamese support)
- Gemini AI analysis
- Table detection

### 🎤 Speech2Text (Port 7860)
**Script:** `start-speech2text.bat`

Audio transcription:
- Whisper Large-v3 (Vietnamese)
- Speaker diarization
- Multi-language support

### 🎨 Stable Diffusion (Port 7861)
**Script:** `start-stable-diffusion.bat`

AI image generation:
- Text-to-Image
- Image-to-Image
- Inpainting
- LoRA/VAE support
- ControlNet

### 🔧 LoRA Training (Port 7862)
**Script:** `start-lora-training.bat`

Fine-tune AI models:
- LoRA model training
- Gemini AI assistant
- WD14 tagger for datasets
- Redis caching

### 📸 Image Upscale (Port 7863)
**Script:** `start-image-upscale.bat`

Image enhancement:
- RealESRGAN (x2, x4)
- SwinIR Real-SR
- ScuNET GAN
- Batch processing

---

## ⚙️ Configuration

Each service may require configuration:

1. **Environment Variables**: Copy `.env.example` to `.env` in each service folder
2. **API Keys**: Add your API keys to `.env` files
3. **Models**: Some services download models on first run

---

## 🐛 Troubleshooting

### Service Won't Start

1. Check virtual environment exists:
   ```bat
   REM Re-run setup
   setup-all.bat
   ```

2. Check dependencies:
   ```bat
   cd services\<service-name>
   pip install -r requirements.txt
   ```

3. Check port conflicts:
   ```bat
   check-status.bat
   ```

### Service Crashes

1. Check logs in service folder:
   ```
   services\<service-name>\logs\
   ```

2. Check for missing API keys in `.env`

3. Run tests to diagnose:
   ```bat
   test-all.bat
   ```

---

## 📚 Related Documentation

- [STRUCTURE.md](STRUCTURE.md) - Project structure overview
- [README.md](README.md) - Main documentation
- [TESTING_QUICKSTART.md](TESTING_QUICKSTART.md) - Testing guide
- [COMPLETE_TEST_SUMMARY.md](COMPLETE_TEST_SUMMARY.md) - Test suite details

---

## 💡 Tips

1. **Use the menu**: Run `menu.bat` for interactive management
2. **Start selectively**: Only start services you need
3. **Check status regularly**: Use `check-status.bat`
4. **Clean logs periodically**: Run `clean-logs.bat` monthly
5. **Test after updates**: Run `test-all.bat` after making changes

---

**Created:** December 10, 2025  
**Version:** 2.3  
**Status:** ✅ Production Ready
