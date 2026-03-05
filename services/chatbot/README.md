# ChatBot Service - AI Assistant v3.0

Advanced multi-model intelligent chatbot with **Multi-Provider Image Generation (7 providers)**, **Split View**, **Drag & Drop Chat Management**, **External API + Browser Extension**, **MCP Integration**, **Custom Prompt System**, **GROK-3 Integration**, **Deep Thinking**, and a completely redesigned modern UI.

<details>
<summary><strong>🌟 Latest Updates (v3.0)</strong></summary>

### 🎨 Complete UI Redesign (NEW! ⭐)

- **ChatGPT/Gemini-quality design**: Dark-first professional interface
- **Lucide Icons**: 30+ SVG icons replacing all emoji icons
- **3 Themes**: Dark (default), Light, Eye Care mode
- **Responsive layout**: Collapsible sidebar, clean topbar with "More" menu
- **Modern CSS design system**: CSS variables, smooth transitions, consistent spacing

### 🖼️ Multi-Provider Image Generation V2 (NEW! ⭐)

- **7 AI Providers** auto-configured from API keys:
  - **fal.ai** (priority 90) — FLUX models
  - **Black Forest Labs** (85) — FLUX Pro
  - **Replicate** (80) — Community models
  - **StepFun** (75) — Step-1X Flash
  - **OpenAI** (70) — DALL-E 3
  - **Together AI** (60) — FLUX Schnell
  - **ComfyUI** (10) — Local workflows
- **Smart auto-detection**: Detects image requests in Vietnamese & English
- **Auto-enabled on startup**: Image tools always active, all API keys used
- **Fallback chain**: Automatically tries next provider if one fails

### 🔀 Split View (NEW!)

- **Side-by-side conversations**: View two chats simultaneously
- **Resizable divider**: Drag to adjust pane widths
- **Chat picker**: Click split button → choose which chat to view alongside
- **One-click toggle**: Split view button in topbar

### 🔄 Drag & Drop Chat Reorder (NEW!)

- **Drag to reorder**: Grab any chat in sidebar, drag to new position
- **Pin chats**: Pin important conversations to always show at top
- **Visual indicators**: Drop zone highlights while dragging
- **Persistent order**: Custom order saved to localStorage

### 🔌 External API + Browser Extension (NEW!)

**REST API v1** — Stateless endpoints for external apps:
- `GET /api/v1/health` — Public health check
- `POST /api/v1/chat` — Chat with AI (API key auth via `X-API-Key` header)
- `POST /api/v1/context` — Inject page context
- `GET /api/v1/providers` — List available models & image providers

**Chrome Extension** — Mini chat from any webpage:
- Right-click → "Ask AI Assistant about this" (selected text)
- Right-click → "Send page to AI Assistant" (full page)
- Popup mini-chat with history
- Configurable server URL & API key
- Keyboard shortcut: `Ctrl+Shift+A` to capture selection

### 🔗 MCP Integration (NEW! ⭐)

- **Model Context Protocol**: Access local files and code directly from ChatBot
- **Folder Selection**: Choose folders from your local disk system
- **Automatic Context Injection**: AI reads relevant files before answering
- **Smart File Search**: Finds and reads code files based on your questions
- **Visual Controls**: Simple UI toggle to enable/disable MCP
- **Multi-Folder Support**: Add multiple project folders simultaneously
- **Code-Aware AI**: Better responses with actual code context

**Quick Start:**
1. Toggle "🔗 MCP: Truy cập file local" in UI
2. Click "📁 Chọn folder" and enter path
3. Ask questions about your code!

📖 **[Read Full MCP Documentation →](QUICKSTART_MCP.md)**

### 🛠️ Custom Prompt System

- **Visual Status Indicators**: 
  - 🟡 Yellow button = Base prompt (default)
  - 🟢 Green button = Custom prompt active
- **Persistent Storage**: Custom prompts saved in localStorage
- **Chat Display**: Full prompt content shown when saved/cleared
- **Live Indicator**: Message info shows "🛠️ Custom Prompt" or "📝 Base Prompt"
- **Easy Management**: Save, edit, or clear custom prompts anytime

### 🤖 GROK-3 Model Integration (NEW!)

- **xAI GROK-3**: Latest model from xAI with advanced reasoning
- **NSFW Support**: Unrestricted conversations when using GROK
- **Multi-Model Choice**: Switch between Gemini, GROK, GPT-4o-mini, DeepSeek, etc.
- **Unified Interface**: Same UI for all AI models

### 🧠 Deep Thinking for All Models (ENHANCED!)

- **Universal Support**: Deep Thinking now available for ALL models
- **Visible Thinking Process**: See AI's reasoning steps in real-time
- **6-Step Analysis**: Comprehensive reasoning for better responses
- **Collapsible Sections**: Click to expand/collapse thinking details

### 🧠 Deep Thinking Feature (OpenAI o1-style)

- **Visible Thinking Process**: See AI's reasoning steps in real-time
- **Collapsible Sections**: Click to expand/collapse thinking details
- **Auto-enabled for Files**: Automatically activates when analyzing uploaded documents
- **Smart Analysis**: 6-step reasoning process for comprehensive responses
  1. Reading and parsing files
  2. Extracting key information
  3. Identifying main topics
  4. Analyzing content depth
  5. Cross-referencing information
  6. Formulating comprehensive response

### 💬 ChatGPT-Style Message Actions

- **Action Buttons**: Copy, Like/Dislike, Regenerate, Edit, More options
- **Hover-to-Show**: Smooth animations for clean interface
- **Message Versioning**: Navigate between multiple response versions (◀ 1/2 ▶)
- **Edit & Regenerate**: Click edit → modify message → get new response
- **Copy to Clipboard**: One-click copy with visual confirmation

### 📎 Enhanced File Upload (50MB Support)

- **Upload Button**: Click "📎 Upload Files" to select documents
- **Drag & Drop**: Paste files directly (Ctrl+V)
- **Large File Support**: Up to 50MB per file
- **Smart Context**: Files automatically included in conversation
- **Chat-based Errors**: No more annoying popups - errors shown in chat
- **User-initiated Analysis**: Upload → Ask questions → Get insights

### 📝 Markdown Code Blocks

- **Proper Formatting**: AI uses ` ` `language` syntax for code
- **Syntax Highlighting**: Python, JavaScript, SQL, etc.
- **Inline Code**: Variables and functions with \`backticks\`
- **All Modes Supported**: Works in Casual, Programming, Lifestyle, Psychological modes

</details>

<details>
<summary><strong>🌟 Core Features</strong></summary>

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

</details>

<details>
<summary><strong>📋 Requirements & Quick Start</strong></summary>

## Requirements

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

Access at: <http://localhost:5000>

</details>

<details>
<summary><strong>🎨 Image Generation Setup</strong></summary>

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

</details>

<details>
<summary><strong>📁 Project Structure</strong></summary>

```
ChatBot/
├── chatbot_main.py                # Main Flask application
├── requirements.txt               # Python dependencies
├── .env.example                   # Environment variables template
├── README.md                      # This file
├── templates/
│   └── index.html                 # Main UI (1370 lines, Lucide icons)
├── static/
│   ├── css/
│   │   └── app.css                # Design system (~1900 lines, 3 themes)
│   └── js/
│       ├── main.js                # Main app controller (2150+ lines)
│       ├── language-switcher.js   # i18n support (vi/en)
│       └── modules/               # ES6 Modules
│           ├── chat-manager.js    # Session management + drag reorder
│           ├── api-service.js     # API communications
│           ├── ui-utils.js        # UI utilities + drag & drop
│           ├── message-renderer.js# Message rendering + actions
│           ├── file-handler.js    # File processing (50MB)
│           ├── memory-manager.js  # Memory features
│           ├── image-gen.js       # Image generation (ComfyUI)
│           ├── image-gen-v2.js    # Multi-provider image gen
│           ├── split-view.js      # Split view manager
│           └── export-handler.js  # PDF export
├── core/
│   ├── image_gen/                 # Multi-provider image generation
│   │   ├── router.py             # Smart provider routing & fallback
│   │   └── providers/            # 7 provider adapters
│   ├── ai_router.py              # AI model routing
│   └── extensions.py             # Blueprint registration
├── routes/                        # Flask blueprints
│   ├── main_routes.py
│   ├── image_gen.py
│   ├── memory.py
│   ├── mcp.py
│   └── ...
├── extension/                     # Chrome browser extension
│   ├── manifest.json              # Manifest V3
│   ├── popup.html                 # Mini chat UI
│   ├── popup.js                   # Extension chat logic
│   ├── background.js              # Context menu + relay
│   ├── content.js                 # Page capture + shortcuts
│   └── icons/                     # Extension icons
├── src/
│   └── utils/
│       ├── local_model_loader.py  # Local model management
│       └── sd_client.py           # Stable Diffusion API client
├── Storage/
│   └── Image_Gen/                 # Generated images
└── data/
    └── memory/                    # Conversation memories
```

</details>

<details>
<summary><strong>🔧 Configuration & Setup</strong></summary>

## Configuration

### Environment Variables (.env)

```env
# AI APIs (chọn 1 hoặc nhiều)
GROK_API_KEY=your_grok_key
OPENAI_API_KEY=your_openai_key
GOOGLE_API_KEY=your_google_key
DEEPSEEK_API_KEY=your_deepseek_key
DASHSCOPE_API_KEY=your_qwen_key

# Image Generation (all optional — uses whichever keys are set)
FAL_KEY=your_fal_key                  # fal.ai FLUX models (priority 90)
BFL_API_KEY=your_bfl_key              # Black Forest Labs (priority 85)
REPLICATE_API_TOKEN=your_replicate    # Replicate (priority 80)
STEPFUN_API_KEY=your_stepfun_key      # StepFun (priority 75)
# OPENAI_API_KEY also used for DALL-E 3 (priority 70)
TOGETHER_API_KEY=your_together_key    # Together AI (priority 60)

# ComfyUI (local, priority 10)
COMFYUI_URL=http://127.0.0.1:8188
SD_API_URL=http://127.0.0.1:7860

# External API
EXTERNAL_API_KEY=your_secret_key      # For browser extension / .exe clients

# Database (optional)
MONGODB_URI=mongodb://localhost:27017

# Server
CHATBOT_PORT=5000
DEBUG=0
```

### Model Selection

- **Grok-3** (Default): xAI — 131K context, advanced reasoning
- **DeepSeek R1**: Reasoning model — 64K
- **GPT-4o-mini**: OpenAI — 128K context
- **Gemini 2.0 Flash**: Google — 1M context (Free)
- **Qwen Turbo**: Alibaba Cloud
- **StepFun**: OpenRouter — 128K (Free)
- **BloomVN-8B**: Vietnamese optimized (Free)

</details>

<details>
<summary><strong>📖 Usage Guide</strong></summary>

## Usage Guide

### Basic Chat

1. Select a model from the dropdown
2. Choose context mode (Casual, Psychological, Lifestyle, Programming)
3. Type your message
4. Click Send or press Enter
5. **NEW:** Click "⏹️ Dừng lại" to stop AI mid-generation

### File Upload & Analysis

1. Click "📎 Upload Files" button
2. Select files (up to 50MB each)
3. Files appear in chat with confirmation message
4. **Type your question** about the file
5. **Deep Thinking auto-enables** for better analysis
6. See thinking process → Get comprehensive answer

**Supported files:**

- Code: `.py`, `.js`, `.html`, `.css`, `.json`
- Documents: `.pdf`, `.doc`, `.docx`, `.txt`, `.xlsx`, `.csv`
- Images: `.jpg`, `.png`, `.gif`, `.webp`

**Example workflow:**
```
1. Upload: contract.pdf (127KB)
   ✅ Đã tải lên 1 file. Bạn có thể hỏi tôi về nội dung file bây giờ!

2. You ask: "Tóm tắt file này"
   
3. AI shows thinking:
   💡 Thought process ▼
   1. Đọc và phân tích file đính kèm...
   2. Trích xuất thông tin và cấu trúc chính...
   3. Xác định các chủ đề và nội dung chính...
   
4. AI provides detailed summary
```

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

</details>

<details>
<summary><strong>🔄 Changelog</strong></summary>

### Version 2.6.0 (December 1, 2025) 🎨

**Production Refinements & Documentation**

- 📚 **Complete Documentation**: Comprehensive README with all v2.5 features documented
- 🎨 **UI Polish**: Refined Deep Thinking animations and transitions
- 🐛 **Bug Fixes**: Event listener stability improvements
- 📊 **Performance**: Optimized file upload handling
- 🔧 **Code Quality**: Better error handling and logging
- 📖 **User Guides**: Enhanced troubleshooting and setup instructions

### Version 2.5.0 (November 25, 2025) 🧠

**Deep Thinking & UX Enhancements**

- ✨ **Deep Thinking (o1-style)**: Visible reasoning process with collapsible sections
- ✨ **ChatGPT-Style Actions**: Copy, Like/Dislike, Regenerate, Edit buttons with hover effects
- ✨ **Message Versioning**: Navigate response versions with ◀ 1/2 ▶ controls
- ✨ **Enhanced File Upload**: 50MB support, chat-based error messages
- ✨ **Smart File Analysis**: Auto-enable Deep Thinking for uploaded documents
- ✨ **Markdown Code Blocks**: Proper ` ` `language` syntax in all modes
- 🎨 **Improved UI**: Smooth animations, better visual feedback
- 🐛 **Fixed**: File upload button, event listeners after refresh, version navigation

### Version 2.0.0 (November 2025) 🎉

**Major UI/UX Overhaul**

- ✨ **Full-screen ChatGPT-like layout** - Utilizes entire viewport
- ✨ **Stop generation** - Interrupt AI and keep partial responses
- ✨ **Message editing** - Edit and regenerate AI responses
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

</details>

<details>
<summary><strong>🆕 What's New Highlights</strong></summary>

## What's New in v2.6?

### Production Ready & Polished

**📚 Documentation Excellence**
```
✅ Complete feature documentation
✅ Troubleshooting guides
✅ Setup wizards
✅ Best practices
```

**🎨 UI Refinements**
```
✅ Smoother animations
✅ Better loading states
✅ Improved error messages
✅ Visual polish
```

**🐛 Stability Improvements**
```
✅ Event listener fixes
✅ Better error handling
✅ Performance optimizations
✅ Edge case handling
```

## What's New in v2.5?

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

</details>

## 📝 License & Contributing

Part of AI-Assistant project. See root LICENSE file.

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

- xAI for GROK-3
- OpenAI for GPT & DALL-E models
- Google for Gemini API
- DeepSeek for reasoning models
- Black Forest Labs for FLUX
- fal.ai, Replicate, Together AI, StepFun
- Stability AI for Stable Diffusion
- Alibaba Cloud for Qwen models
- [Lucide Icons](https://lucide.dev) for the icon library
- Community contributors

---

**Built with ❤️ by [@SkastVnT](https://github.com/SkastVnT) & [@sug1omyo](https://github.com/sug1omyo)**  
**Star ⭐ this repo if you find it helpful!**
