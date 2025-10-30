# AI-Assistant - Getting Started

## 🚀 Quick Start

### Option 1: Start ChatBot with Stable Diffusion (Recommended)
```bash
.\scripts\startup\start_chatbot.bat
```
This will automatically start:
1. Stable Diffusion API (separate terminal) - Port 7860
2. ChatBot WebUI (current terminal) - Port 5000

Then open: http://127.0.0.1:5000

**Note:** Wait 30-60 seconds for Stable Diffusion to fully load before using image generation.

### Option 2: Start ChatBot Only (No Image Generation)
```bash
.\scripts\startup\start_chatbot_only.bat
```
Then open: http://127.0.0.1:5000

### Option 3: Start All Services
```bash
.\scripts\startup\start_all.bat
```

### Option 4: Manual Start (Both in Separate Terminals)
```bash
# Terminal 1: Start Stable Diffusion API
.\scripts\stable-diffusion\start_sd_no_install.bat

# Terminal 2: Start ChatBot
.\scripts\startup\start_chatbot_only.bat
```

## 📁 Project Structure

```
AI-Assistant/
├── docs/
│   ├── setup/              # Setup instructions
│   │   ├── SETUP_NEW_DEVICE.txt
│   │   ├── SETUP_COMPLETED.md
│   │   └── FINAL_STEP.md
│   │
│   ├── guides/             # Usage guides
│   │   ├── IMAGE_GENERATION_GUIDE.md      # Complete image generation guide
│   │   ├── QUICK_START_IMAGE_GEN.md       # Quick start for images
│   │   ├── SD_INTEGRATION_COMPLETE.md     # Integration details
│   │   ├── FIX_ACCESS_DENIED.md           # Fix installation errors
│   │   ├── FIX_NOW.md
│   │   └── FIX_SD_ERROR.md
│   │
│   ├── HUB_README.md
│   ├── MISSION_COMPLETE.md
│   └── PROJECT_STRUCTURE.md
│
├── scripts/
│   ├── startup/            # Service startup scripts
│   │   ├── start_chatbot.bat              # ChatBot + SD (Auto)
│   │   ├── start_chatbot_only.bat         # ChatBot only (No SD)
│   │   ├── start_chatbot_with_sd.bat      # Both in separate terminals
│   │   ├── start_hub.bat
│   │   ├── start_all.bat
│   │   └── start_all_with_sd.bat
│   │
│   └── stable-diffusion/   # SD specific scripts
│       ├── start_sd_no_install.bat        # Recommended
│       ├── start_stable_diffusion_api.bat
│       ├── start_sd_simple.bat
│       └── fix_sd_install.bat
│
├── ChatBot/                # Main chatbot application
├── src/                    # Hub core functionality
├── config/                 # Configuration files
├── examples/               # Usage examples
└── .env                    # API keys (create from .env.example)
```

## 🔑 Required API Keys

Create `.env` file in root directory:
```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...
```

Also create `ChatBot/.env`:
```env
OPENAI_API_KEY=sk-...
GEMINI_API_KEY=...
DEEPSEEK_API_KEY=...
SD_API_URL=http://127.0.0.1:7860
```

## 📚 Documentation

- **Setup Guide**: `docs/setup/SETUP_NEW_DEVICE.txt`
- **Image Generation**: `docs/guides/IMAGE_GENERATION_GUIDE.md`
- **Quick Start Images**: `docs/guides/QUICK_START_IMAGE_GEN.md`
- **Troubleshooting**: `docs/guides/FIX_*.md`

## 🎨 Features

- **Multi-Model Chat**: GPT-4o-mini, Gemini, DeepSeek
- **Image Generation**: Stable Diffusion with checkpoint selection
- **No NSFW Restrictions**: Complete creative freedom
- **Real-time Model Switching**: Change SD checkpoints on the fly
- **Advanced Controls**: Steps, CFG Scale, Samplers, Face Restoration, Hires Fix

## 🛠️ System Check

Run system verification:
```bash
python check_system.py
```

## ⚠️ Common Issues

### Stable Diffusion Won't Start?
Use the no-install version:
```bash
.\scripts\stable-diffusion\start_sd_no_install.bat
```

### Port Already in Use?
- ChatBot: Port 5000
- Hub: Port 8000  
- Stable Diffusion: Port 7860

Kill processes using these ports or change in config.

### API Keys Not Working?
Check both `.env` files (root and ChatBot directory).

## 📞 Support

- Check `docs/guides/` for detailed guides
- Review `docs/setup/` for installation help
- See troubleshooting guides in `docs/guides/FIX_*.md`
