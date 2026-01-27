# 🚀 AI-Assistant - Setup Guide

Complete setup guide for end-users who clone the project for the first time.

## 📋 System Requirements

### Minimum Requirements
- **OS**: Windows 10/11, Linux (Ubuntu 20.04+), macOS 12+
- **Python**: 3.10.6 or higher (**3.11.x recommended**)
- **RAM**: 16GB minimum
- **Storage**: 50GB+ free space
- **Internet**: Stable connection (for downloading models)

### For Image Generation (Optional)
- **GPU**: NVIDIA GPU with 6GB+ VRAM (8GB+ recommended)
- **CUDA**: CUDA 11.8 compatible GPU
- **Driver**: Latest NVIDIA drivers

### Verify Python Version
```bash
python --version
# Should show: Python 3.10.x or Python 3.11.x
```

If you don't have Python installed:
- Download from: https://www.python.org/downloads/
- **Important**: Check "Add Python to PATH" during installation

---

## ⚡ Quick Start (Recommended)

### Method 1: Interactive Menu (Easiest!)

1. **Clone the repository**
```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant
```

2. **Run the menu**
```bash
menu.bat
```

3. **Select option `0`** - Quick Setup (Auto-install everything)

4. **Wait for installation** (20-30 minutes)

5. **Configure API Keys** (see below)

6. **Back to menu → Select `2`** - Start ChatBot

### Method 2: Direct Setup Script

1. **Clone the repository**
```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant
```

2. **Run the setup script**
```bash
scripts\SETUP.bat
```

This single script will:
- ✅ Check Python version
- ✅ Create virtual environment (`.venv`)
- ✅ Upgrade pip to latest version
- ✅ Install PyTorch with CUDA support
- ✅ Install all dependencies
- ✅ Create `.env` files from examples
- ✅ Create quick start shortcuts

3. **Configure API Keys**

Edit these files and add your API keys:
- **Root `.env`** (optional - for Hub Gateway)
- **`services/chatbot/.env`** (required - for ChatBot)

Required API keys:
```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Get your Gemini API key: https://makersuite.google.com/app/apikey

Optional API keys:
```env
OPENAI_API_KEY=your_openai_api_key_here  # For OpenAI models
IMGBB_API_KEY=your_imgbb_api_key_here    # For image upload
```

4. **Start the services**

Start ChatBot only:
```bash
scripts\start-chatbot.bat
```

OR start all services:
```bash
scripts\start-all.bat
```

5. **Access the application**
- **ChatBot**: http://localhost:5000
- **Hub Gateway**: http://localhost:3000
- **Stable Diffusion**: http://localhost:7861

---

## 📖 Manual Setup (Advanced)

If you prefer manual control or the automated script fails:

### Step 1: Create Virtual Environment
```bash
python -m venv .venv
```

### Step 2: Activate Virtual Environment

**Windows:**
```bash
.venv\Scripts\activate.bat
```

**Linux/Mac:**
```bash
source .venv/bin/activate
```

### Step 3: Upgrade pip
```bash
python -m pip install --upgrade pip
```

### Step 4: Install PyTorch

> **Note:** PyTorch 2.4.1 is the last version supporting CUDA 11.8. If you have CUDA 12.1+, you can use PyTorch 2.9.1 by changing `cu118` to `cu121` in the URL below.

**For GPU (CUDA 11.8):**
```bash
pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu118
```

**For CPU only:**
```bash
pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1
```

### Step 5: Install Dependencies
```bash
pip install -r requirements.txt
```

This will install all required packages including:
- Flask (Web framework)
- Google Generative AI SDK (Gemini 2.0 Flash)
- Transformers (Hugging Face models)
- Gradio (UI for services)
- And 200+ other packages

**Note**: Installation may take 20-30 minutes depending on your internet speed.

### Step 6: Configure Environment

**Create `.env` file:**
```bash
# Windows
copy .env.example .env

# Linux/Mac
cp .env.example .env
```

**Create ChatBot `.env`:**
```bash
# Windows
copy services\chatbot\.env.example services\chatbot\.env

# Linux/Mac
cp services/chatbot/.env.example services/chatbot/.env
```

**Edit `.env` files** and add your API keys (see Quick Start step 3).

### Step 7: Start Services

**ChatBot only:**
```bash
cd services\chatbot
python app.py
```

**All services (separate terminals):**
```bash
# Terminal 1 - ChatBot
cd services\chatbot
python app.py

# Terminal 2 - Stable Diffusion
cd services\stable-diffusion
python launch.py --api --listen --port 7861

# Terminal 3 - Hub Gateway (optional)
cd services\hub-gateway
python app.py
```

---

## 🔧 Troubleshooting

### Problem: "Python not found"
**Solution**: 
1. Download Python from https://www.python.org/downloads/
2. During installation, check "Add Python to PATH"
3. Restart terminal after installation

### Problem: "Failed to create virtual environment"
**Solution**:
```bash
# Try this instead
python -m pip install --upgrade virtualenv
python -m virtualenv .venv
```

### Problem: PyTorch installation fails (CUDA version)
**Solution**:
```bash
# Install CPU-only version instead
pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1
```

### Problem: "Some packages failed to install"
**Solution**:
1. This is usually okay - most packages are optional
2. Try installing problematic packages individually:
```bash
pip install package-name
```
3. Check if critical packages are installed:
```bash
python -c "import flask"
python -c "import torch"
python -c "import google.genai"
```

### Problem: "ImportError: No module named 'google.genai'"
**Solution**:
```bash
# Upgrade to latest version
pip install --upgrade google-genai
```

### Problem: ChatBot won't start - "GEMINI_API_KEY not found"
**Solution**:
1. Edit `services/chatbot/.env`
2. Add: `GEMINI_API_KEY=your_actual_key_here`
3. Get key from: https://makersuite.google.com/app/apikey

### Problem: Image generation not working
**Solution**:
1. Start Stable Diffusion first:
```bash
scripts\start-stable-diffusion.bat
```
2. Wait for it to load (may take 2-3 minutes first time)
3. Then start ChatBot
4. Check if SD is running: http://localhost:7861

### Problem: "Port already in use"
**Solution**:
1. Close other services using the same port
2. Or change the port in service's `app.py`:
```python
app.run(port=5001)  # Change 5000 to 5001
```

### Problem: Out of memory (GPU)
**Solution**:
1. Lower image resolution in Stable Diffusion
2. Use `--medvram` or `--lowvram` flags
3. Close other GPU-intensive programs

### Problem: Slow image generation
**Solution**:
1. Check if using GPU (not CPU):
```bash
python -c "import torch; print(torch.cuda.is_available())"
# Should print: True
```
2. If False, reinstall PyTorch with CUDA (see Step 4)

---

## 📦 Services Overview

| Service | Port | Required | Description |
|---------|------|----------|-------------|
| **ChatBot** | 5000 | ✅ Yes | Main AI chatbot with image generation |
| **Stable Diffusion** | 7861 | ⚠️ Optional | Image generation backend |
| **Hub Gateway** | 3000 | ❌ No | API gateway/coordinator |
| **Text2SQL** | 5002 | ❌ No | Natural language to SQL |
| **Document Intelligence** | 5003 | ❌ No | OCR + AI analysis |
| **Speech2Text** | 5001 | ❌ No | Vietnamese speech recognition |
| **LoRA Training** | 7862 | ❌ No | Model fine-tuning |
| **Image Upscale** | 7863 | ❌ No | AI image upscaling |

### Start Individual Services

```bash
# ChatBot (main service)
scripts\start-chatbot.bat

# Stable Diffusion (for image generation)
scripts\start-stable-diffusion.bat

# All services at once
scripts\start-all.bat
```

---

## 🎯 Post-Setup Verification

### Test ChatBot
1. Open http://localhost:5000
2. Type: "Hello, how are you?"
3. You should get a response from Gemini AI

### Test Image Generation
1. Enable "Tạo ảnh" tool in ChatBot
2. Type: "Create an image of a mountain landscape"
3. AI will generate prompt and create image
4. Image should appear in chat

### Test Hidden NSFW Toggle
1. In ChatBot, press: `Ctrl + Shift + N`
2. Page title should flash: 🔓 Filter OFF
3. Press again: 🛡️ Filter ON
4. This toggles SFW/NSFW filtering

### Check Installed Packages
```bash
# Activate venv first
.venv\Scripts\activate.bat

# Check critical packages
python -c "import flask; print('Flask:', flask.__version__)"
python -c "import torch; print('PyTorch:', torch.__version__)"
python -c "import google.genai; print('Google GenAI: OK')"
python -c "import transformers; print('Transformers: OK')"
```

---

## 🔄 Daily Usage

### Every time you start working:

1. **Activate virtual environment**
```bash
.venv\Scripts\activate.bat  # Windows
source .venv/bin/activate   # Linux/Mac
```

2. **Start services**
```bash
scripts\start-chatbot.bat  # Or start-all.bat
```

3. **Access application**
- Open browser: http://localhost:5000

### Quick Start Shortcuts (Created by SETUP.bat)

- **`START_CHATBOT.bat`** - In project root, double-click to start

---

## 🆘 Getting Help

- **Documentation**: Check `docs/` folder
- **Issues**: https://github.com/SkastVnT/AI-Assistant/issues
- **Quick Reference**: `docs/QUICK_REFERENCE.md`
- **API Docs**: `docs/API_DOCUMENTATION.md`

---

## ⚙️ Advanced Configuration

### Change ChatBot Port
Edit `services/chatbot/app.py`:
```python
app.run(host='0.0.0.0', port=5000)  # Change 5000 to your port
```

### Use Different GROK Model
Edit `services/chatbot/.env`:
```env
GROK_MODEL=grok-3
```

### Enable Debug Mode
Edit `services/chatbot/app.py`:
```python
DEBUG = True  # Change False to True
```

### Custom Stable Diffusion Settings
Edit `services/stable-diffusion/webui-user.bat`:
```bat
set COMMANDLINE_ARGS=--api --listen --port 7861 --xformers --medvram
```

---

## 📝 Version History

- **v2.4** (2025-12-17): Simplified setup, fixed google-genai migration, added SETUP.bat
- **v2.3** (2025-12-16): Added NSFW filters, smart people detection, fixed dropdowns
- **v2.2** (2025-11): Gemini 2.0 Flash integration
- **v2.0** (2025-09): Multi-service architecture

---

## ✅ Checklist Before Running

- [ ] Python 3.10.6+ installed and in PATH
- [ ] Virtual environment created (`.venv` folder exists)
- [ ] Virtual environment activated (prompt shows `(.venv)`)
- [ ] All dependencies installed (`pip list` shows flask, torch, etc.)
- [ ] `.env` files created and configured
- [ ] `GEMINI_API_KEY` added to `services/chatbot/.env`
- [ ] Stable Diffusion started (if using image generation)
- [ ] Port 5000 is free (not used by other programs)

---

**Happy coding! 🎉**

If you encounter any issues, please open an issue on GitHub or check the troubleshooting section above.
