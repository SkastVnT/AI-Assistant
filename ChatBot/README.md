# ChatBot Service - AI Assistant v2.0

Advanced multi-model intelligent chatbot with local LLM support, image generation, auto-file analysis, and modern UX inspired by ChatGPT.

## 🌟 Features

### 🤖 AI Capabilities
- **Multi-Model Support**: OpenAI GPT-4, Google Gemini, DeepSeek, Local Qwen models
- **Image Generation**: Integration with Stable Diffusion WebUI API
  - Text-to-Image (txt2img)
  - Image-to-Image (img2img) with LoRA and VAE support
  - Advanced parameters control (Steps, CFG Scale, Samplers)
- **Smart File Analysis**: Automatic analysis of uploaded files
  - Support for code files (.py, .js, .html, .css, .json)
  - Document processing (.pdf, .doc, .docx)
  - Image recognition
  - Auto-generated insights without user prompting

### 💾 Data Management
- **Memory System**: Persistent conversation history with image storage
- **Message Versioning**: Track multiple versions of AI responses
- **Session-based Files**: Files attached per conversation
- **Smart Storage**: Progress bar with auto-cleanup (keeps 5 recent chats)

### ⚡ User Experience
- **Stop Generation**: Interrupt AI mid-response and keep partial output
- **Full-Screen Layout**: ChatGPT-like interface utilizing entire viewport
- **Message Editing**: Edit and regenerate responses
- **Export**: PDF export for conversations with images
- **Modern UI**: Responsive design with dark mode support

## 📋 Requirements

- Python 3.10.6
- NVIDIA GPU with CUDA 11.8 (for local models)
- 8GB+ RAM (16GB recommended for local models)
- Stable Diffusion WebUI running (for image generation)

## 🚀 Quick Start

### 1. Setup Virtual Environment

```bash
# Create virtual environment
python -m venv venv_chatbot

# Activate (Windows)
.\venv_chatbot\Scripts\activate

# Activate (Linux/Mac)
source venv_chatbot/bin/activate
```

### 2. Install Dependencies

```bash
# Install PyTorch with CUDA (for GPU)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Install other dependencies
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
# Copy example environment file
copy .env.example .env

# Edit .env and add your API keys:
# - OPENAI_API_KEY (for GPT-4)
# - GOOGLE_API_KEY (for Gemini)
# - SD_API_URL (Stable Diffusion API, default: http://127.0.0.1:7860)
```

### 4. Run Application

```bash
python app.py
```

Access at: http://localhost:5000

## 🎨 Image Generation Setup

1. Start Stable Diffusion WebUI with API enabled:
   ```bash
   cd ../stable-diffusion-webui
   python webui.py --api
   ```

2. Image generation features:
   - **Text-to-Image**: Generate images from text prompts
   - **Image-to-Image**: Transform existing images
   - **LoRA Models**: Apply style transformations
   - **VAE**: Use custom VAE models
   - **Advanced Settings**: Steps, CFG Scale, Sampling methods

## 📁 Project Structure

```
ChatBot/
├── app.py                      # Main Flask application
├── requirements.txt            # Python dependencies
├── .env.example               # Environment variables template
├── README.md                  # This file
├── templates/
│   └── index.html             # Main UI (modular, 509 lines)
├── static/
│   ├── css/
│   │   └── style.css          # Custom styles (~2200 lines)
│   └── js/
│       ├── main.js            # Main app controller
│       └── modules/           # ES6 Modules
│           ├── chat-manager.js      # Session management
│           ├── api-service.js       # API communications
│           ├── ui-utils.js          # UI utilities
│           ├── message-renderer.js  # Message rendering
│           ├── file-handler.js      # File processing
│           ├── memory-manager.js    # Memory features
│           ├── image-gen.js         # Image generation
│           └── export-handler.js    # PDF export
├── src/
│   └── utils/
│       ├── local_model_loader.py  # Local model management
│       └── sd_client.py           # Stable Diffusion API client
├── models/
│   └── Qwen1.5-1.8B-Chat/        # Local LLM model
├── Storage/
│   └── Image_Gen/                 # Generated images
└── data/
    └── memory/                    # Conversation memories
```

## 🔧 Configuration

### Environment Variables (.env)

```env
# API Keys
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key

# Stable Diffusion
SD_API_URL=http://127.0.0.1:7860

# Server
FLASK_PORT=5000
FLASK_DEBUG=False
```

### Model Selection

- **GPT-4**: Best quality, requires API key
- **Gemini**: Fast and capable, requires API key
- **Qwen (Local)**: Free, runs locally, requires GPU

## 📖 Usage Guide

### Basic Chat

1. Select a model from the dropdown
2. Choose context mode (Casual, Psychological, Lifestyle, Programming)
3. Type your message
4. Click Send or press Enter
5. **NEW:** Click "⏹️ Dừng lại" to stop AI mid-generation

### File Upload & Auto-Analysis

1. Click "📎 Upload Files" or paste (Ctrl+V)
2. **Files appear directly in chat** (not in input area)
3. **AI automatically analyzes** - no need to type anything!
4. Receive detailed analysis:
   - Content summary
   - Issue detection
   - Recommendations
   - Q&A responses

**Supported files:**
- Code: `.py`, `.js`, `.html`, `.css`, `.json`
- Documents: `.pdf`, `.doc`, `.docx`, `.txt`
- Images: `.jpg`, `.png`, `.gif`, `.webp`

### Image Generation

1. Click "🎨 Tạo ảnh" button
2. Choose tab:
   - **Text2Img**: Generate from text prompt
   - **Img2Img**: Transform existing image
3. Configure parameters (optional):
   - Steps: 20-50 (higher = better quality)
   - CFG Scale: 7-12 (higher = follow prompt more)
   - Select LoRA or VAE models
4. Click "Generate"
5. Copy to chat or download

### Memory Features

1. Click "🧠 AI học tập" to open memory panel
2. Select memories to activate for current chat
3. Save current conversation as memory
4. AI will use activated memories as context

### Storage Management

- **Progress bar** shows storage usage (0-200MB)
- Status indicators:
  - 💚 Green (0-50%): Good
  - 🟡 Yellow (50-80%): Warning
  - 🔴 Red (80-100%): Full
- Click "🗑️ Dọn dẹp" to auto-cleanup (keeps 5 recent chats)

### Export to PDF

1. Click "📥 Tải chat" button
2. PDF includes messages, images, and metadata
3. Saved automatically to downloads

## 🐛 Troubleshooting

### Local Model Issues

```bash
# If Qwen model fails to load:
1. Check GPU memory (requires ~4GB VRAM)
2. Verify CUDA installation: nvidia-smi
3. Try CPU mode (slower): Edit app.py, set device='cpu'
```

### Image Generation Issues

```bash
# If SD API connection fails:
1. Verify SD WebUI is running with --api flag
2. Check SD_API_URL in .env
3. Test connection: http://127.0.0.1:7860/docs
```

### Dependencies Issues

```bash
# If torch installation fails:
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# If bitsandbytes fails on Windows:
# It's optional, comment out in requirements.txt
```

## 📚 Documentation

### Core Features
- **[NEW! v2.0 Features](docs/NEW_FEATURES_v2.0.md)** - Complete guide to latest features
- [Image Generation Guide](docs/IMAGE_GENERATION_TOOL_GUIDE.md)
- [LoRA & VAE Guide](docs/LORA_VAE_GUIDE.md)
- [Memory Features](docs/MEMORY_WITH_IMAGES_FEATURE.md)
- [UI Improvements](docs/UI_IMPROVEMENTS.md)

### Technical Documentation
- [Module Architecture](docs/NEW_FEATURES_v2.0.md#71-module-architecture)
- [File Upload System](docs/NEW_FEATURES_v2.0.md#5-file-upload-revolution)
- [Storage Management](docs/NEW_FEATURES_v2.0.md#73-storage-management)
- [Performance Optimizations](docs/NEW_FEATURES_v2.0.md#8-performance-optimizations)

## 🔄 Updates

### Version 2.0.0 (November 2025) 🎉
- ✨ **Full-screen ChatGPT-like layout** - Utilizes entire viewport
- ✨ **Auto-file analysis** - Upload and get instant AI insights
- ✨ **Stop generation** - Interrupt AI and keep partial responses
- ✨ **Message versioning** - Track multiple response versions
- ✨ **Fancy storage display** - Progress bar with smart cleanup
- 🎨 **Enhanced UI/UX** - Better visibility, GitHub badge, centered header
- 🐛 **Fixed timestamp bug** - Chat items no longer "jump" when switching
- 🔧 **Modular architecture** - ES6 modules for better maintainability

### Version 1.8.0
- Added img2img support with LoRA and VAE
- Improved UI with Tailwind CSS
- Enhanced memory system with images
- Added PDF export functionality

### Version 1.5.0
- Added local Qwen model support
- Implemented conversation memory
- Added image generation tool

## 🆕 What's New in v2.0?

### Key Highlights

**1. Upload & Forget** 📎
```
Before: Upload → Type question → Wait for response
Now:    Upload → Instant AI analysis appears!
```

**2. Stop When You Want** ⏹️
```
AI generating long response...
[Click Stop button]
→ Keeps partial response
→ Continue conversation from there
```

**3. Beautiful Storage Management** 💚
```
Old: "📊 Lưu trữ: 5MB / 200MB (2%)"
New: Progress bar with colors + One-click cleanup
```

**4. ChatGPT-like Experience** 🚀
- Full-screen layout
- Messages span wider (85% width)
- Better chat item visibility
- Smooth animations
- Dark mode perfected

## 📝 License

Part of AI-Assistant project. See root LICENSE file.

## 🤝 Contributing

This is a sub-service of AI-Assistant project. For contributions, please refer to the main project repository.

Interested in specific features? Check out:
- [CHANGELOG.md](CHANGELOG.md) - Full version history
- [NEW_FEATURES_v2.0.md](docs/NEW_FEATURES_v2.0.md) - Deep dive into v2.0
- [QUICK_START.md](docs/QUICK_START.md) - 5-minute setup guide

## 📧 Support

For issues and questions:
- Create an issue in [main repository](https://github.com/SkastVnT/AI-Assistant)
- Check [Troubleshooting](docs/NEW_FEATURES_v2.0.md#111-common-issues)
- Review [Quick Start Guide](docs/QUICK_START.md)

## 🙏 Acknowledgments

- OpenAI for GPT models
- Google for Gemini API
- Stability AI for Stable Diffusion
- Alibaba Cloud for Qwen models
- Community contributors

---

**Built with ❤️ by [@SkastVnT](https://github.com/SkastVnT)**

**Star ⭐ this repo if you find it helpful!**
