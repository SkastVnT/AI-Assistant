<div align="center">

<!-- Logo & Title -->
<img src="https://img.icons8.com/fluency/96/artificial-intelligence.png" width="100" alt="AI Logo"/>

# 🤖 AI-Assistant

### *Nền Tảng Tích Hợp Đa Dịch Vụ AI*

<br/>

<!-- Tech Stack Badges -->
<p>
<img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white"/>
<img src="https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white"/>
<img src="https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white"/>
<img src="https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white"/>
<img src="https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white"/>
</p>

<!-- Stats Badges -->
<p>
<a href="https://github.com/SkastVnT/AI-Assistant/stargazers">
  <img src="https://img.shields.io/github/stars/SkastVnT/AI-Assistant?style=for-the-badge&logo=github&color=yellow"/>
</a>
<a href="https://github.com/SkastVnT/AI-Assistant/network/members">
  <img src="https://img.shields.io/github/forks/SkastVnT/AI-Assistant?style=for-the-badge&logo=github&color=blue"/>
</a>
<a href="https://github.com/SkastVnT/AI-Assistant/releases">
  <img src="https://img.shields.io/github/v/release/SkastVnT/AI-Assistant?style=for-the-badge&logo=github&color=green"/>
</a>
<a href="https://github.com/SkastVnT/AI-Assistant/blob/master/LICENSE">
  <img src="https://img.shields.io/badge/License-MIT-success?style=for-the-badge"/>
</a>
</p>

<br/>

**🌟 Nền tảng tích hợp 9+ dịch vụ AI Microservices 🚀**

**Multi-Model Chat • 7-Provider Image Gen • Split View • External API • Browser Extension • Speech Recognition • Document OCR • Text2SQL**

<br/>

[✨ Features](#-features) &nbsp;•&nbsp; [🆕 What's New](#-whats-new-in-v30) &nbsp;•&nbsp; [⚡ Quick Start](#-quick-start) &nbsp;•&nbsp; [🎯 Services](#-services) &nbsp;•&nbsp; [📚 Docs](#-documentation)

---

</div>

<br/>

## ✨ Features

<table>
<tr>
<td width="50%">

### 💬 Multi-Model AI Chat
Hỗ trợ nhiều mô hình AI hàng đầu:
- **Grok-3** - xAI's flagship model (default)
- **GPT-4o-mini** - OpenAI
- **Gemini 2.0 Flash** - Google (Free, 1M ctx)
- **DeepSeek R1** - Reasoning model
- **Qwen Turbo** - Alibaba multilingual
- **BloomVN-8B** - Vietnamese optimized

✅ Streaming response real-time  
✅ Split view — 2 chats side-by-side  
✅ Drag & drop chat reorder + pin  
✅ External REST API + Browser Extension

</td>
<td width="50%">

### 🎙️ Speech Recognition
Nhận dạng giọng nói tiếng Việt chính xác:
- **Whisper** - OpenAI's speech model
- **Pyannote** - Speaker diarization

✅ Phân biệt người nói  
✅ Real-time transcription  
✅ Batch processing  
✅ Multiple audio formats

</td>
</tr>
<tr>
<td width="50%">

### 📄 Document Intelligence
Trích xuất và phân tích tài liệu:
- **PaddleOCR** - Multi-language OCR
- **AI Analysis** - Smart content extraction

✅ Tiếng Việt OCR chính xác  
✅ Table extraction  
✅ PDF/Image support  
✅ Structured data output

</td>
<td width="50%">

### 🎨 Image Generation
Đa nhà cung cấp AI tạo ảnh:
- **7 Providers**: fal, BFL, Replicate, StepFun, OpenAI, Together, ComfyUI
- **Smart Routing**: Auto-select best provider
- **Fallback chain**: Tự động thử provider tiếp theo

✅ FLUX, DALL-E 3, SD models  
✅ Auto-detect image requests  
✅ Prompt enhancement via LLM  
✅ All API keys auto-configured

</td>
</tr>
<tr>
<td width="50%">

### 📊 Text to SQL
Chuyển ngôn ngữ tự nhiên thành SQL:
- **MySQL/PostgreSQL** support
- **Vietnamese** language support

✅ Natural language queries  
✅ Auto-complete suggestions  
✅ Query validation  
✅ Result formatting

</td>
<td width="50%">

### 🖼️ Image Upscale
Nâng cấp chất lượng ảnh với AI:
- **RealESRGAN** - 4x upscaling
- **GIF Animation** support

✅ Batch processing  
✅ Multiple formats  
✅ Quality preservation  
✅ Fast processing

</td>
</tr>
</table>

<br/>

---

## 🆕 What's New in v3.0

| Category | Changes |
|:---------|:--------|
| 🎨 **Complete UI Redesign** | ChatGPT/Gemini-quality interface, Lucide SVG icons, 3 themes (Dark/Light/Eye-care) |
| 🖼️ **Multi-Provider Image Gen V2** | 7 providers with smart routing & auto-fallback (fal, BFL, Replicate, StepFun, OpenAI, Together, ComfyUI) |
| 🧩 **Split View** | View 2 conversations side-by-side with resizable divider |
| 🔀 **Drag & Drop Chats** | Reorder conversations by dragging, pin important chats to top |
| 🌐 **External REST API** | `/api/v1/chat`, `/api/v1/context`, `/api/v1/providers` — headless integration |
| 🧩 **Chrome Extension** | Mini chat sidebar, page context injection, `Ctrl+Shift+A` shortcut |
| 🤖 **Auto Image Detection** | LLM auto-detects image requests and routes to Image Gen V2 |
| 🎯 **Grok-3 Default** | xAI Grok-3 as default model, Deep Thinking mode support |

<br/>

---

## ⚡ Quick Start

### 🖥️ Chạy trực tiếp

```bash
# Clone repository
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant

# Chạy menu tương tác (dễ nhất!)
menu.bat          # Windows
./menu.sh         # Linux/Mac
```

### 🐳 Docker (Khuyến nghị)

```bash
# Chạy tất cả services
docker-compose up -d

# Hoặc chạy lightweight mode (không GPU)
docker-compose -f docker-compose.light.yml up -d

# Kiểm tra health
curl http://localhost:5001/health/detailed
```

### 📦 Chạy từng service

```bash
scripts\start-chatbot.bat          # 🤖 ChatBot      → localhost:5001
scripts\start-hub-gateway.bat      # 🎯 API Gateway  → localhost:3000
scripts\start-speech2text.bat      # 🎙️ Speech2Text  → localhost:7860
scripts\start-document-intelligence.bat  # 📄 OCR    → localhost:5003
scripts\start-text2sql.bat         # 📊 Text2SQL    → localhost:5002
```

<br/>

---

## 🎯 Services

<div align="center">

| Service | Port | Mô tả | Status |
|:--------|:----:|:------|:------:|
| 🤖 **ChatBot** | `5000` | Multi-model Chat + 7-Provider Image Gen + Split View + External API | ✅ **v3.0** |
| 🎯 **Hub Gateway** | `3000` | API Gateway + Rate limiting + Authentication | ✅ Production |
| 📄 **Document Intelligence** | `5003` | Vietnamese OCR + Table extraction + AI analysis | ✅ Production |
| 🎙️ **Speech2Text** | `7860` | Whisper + Speaker diarization + Real-time | ✅ Production |
| 📊 **Text2SQL** | `5002` | Natural Language → SQL + MySQL/PostgreSQL | ✅ Production |
| 🎨 **ComfyUI** | `8188` | Node-based image workflows + LoRA support | ✅ Ready |
| 🖼️ **Image Upscale** | `CLI` | RealESRGAN 4x + Batch + GIF animation | ✅ Ready |
| ✨ **LoRA Training** | `CLI` | SD fine-tuning + Dataset preparation | ✅ Ready |
| 🔌 **MCP Server** | `CLI` | Claude Desktop integration + Custom tools | ✅ Ready |
| 🌐 **Browser Extension** | `-` | Chrome Extension — chat sidebar + page context | ✅ **New** |

</div>

<br/>

---

## 📁 Project Structure

```
AI-Assistant/
│
├── 📦 services/                    # Microservices
│   ├── chatbot/                    # Flask + Multi-model AI + Image Gen V2
│   │   ├── core/image_gen/         # 7-provider image generation engine
│   │   ├── extension/              # Chrome browser extension (Manifest V3)
│   │   ├── static/js/modules/      # Split view, chat manager, UI utils
│   │   └── templates/              # Redesigned UI (Lucide icons, 3 themes)
│   ├── hub-gateway/                # API Gateway + Authentication
│   ├── speech2text/                # Whisper + Pyannote
│   ├── document-intelligence/      # PaddleOCR + AI Analysis
│   ├── text2sql/                   # NL to SQL
│   ├── image-upscale/              # RealESRGAN
│   ├── lora-training/              # SD Fine-tuning
│   ├── mcp-server/                 # Claude Desktop Integration
│   └── templates/                  # Shared UI Components
│
├── 🎨 ComfyUI/                     # Image Generation Workflows
│
├── 🔧 src/                         # Core shared modules
│   ├── cache/                      # Caching utilities
│   ├── database/                   # Database connectors
│   ├── health/                     # Health check utilities
│   └── security/                   # Security modules
│
├── ⚙️ config/                      # Global configuration
│   ├── firebase_config.py          # Firebase setup
│   ├── model_config.py             # AI model configurations
│   └── rate_limiter.py             # Rate limiting config
│
├── 🧪 tests/                       # Test suites
│   ├── unit/                       # Unit tests
│   ├── integration/                # Integration tests
│   └── e2e/                        # End-to-end tests
│
├── 📜 scripts/                     # 50+ automation scripts
├── 📋 requirements/                # Chunked dependencies
├── 🐳 docker/                      # Docker configurations
└── 🔐 private/                     # Private submodule
```

<br/>

---

## ⚙️ Configuration

### Environment Variables

```env
# 🔑 Required - Chat AI APIs (chọn 1 hoặc nhiều)
GROK_API_KEY=your_grok_key           # xAI Grok-3 (default)
OPENAI_API_KEY=your_openai_key       # GPT-4o-mini
GOOGLE_API_KEY=your_google_key       # Gemini 2.0 Flash
DEEPSEEK_API_KEY=your_deepseek_key   # DeepSeek R1
QWEN_API_KEY=your_qwen_key           # Qwen Turbo

# 🎨 Image Generation APIs (tùy chọn — hệ thống tự fallback)
FAL_KEY=your_fal_key                 # fal.ai (FLUX Pro/Dev - priority 90)
BFL_API_KEY=your_bfl_key             # Black Forest Labs (FLUX 1.1 - priority 85)
REPLICATE_API_TOKEN=your_replicate   # Replicate (FLUX Schnell - priority 80)
STEPFUN_API_KEY=your_stepfun_key     # StepFun (priority 75)
TOGETHER_API_KEY=your_together_key   # Together AI (FLUX Schnell - priority 60)

# 🌐 External API
EXTERNAL_API_KEY=ai-assistant-ext-key-2024  # Browser extension auth

# 🗄️ Database
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=chatbot

# 📦 Optional - Caching
REDIS_HOST=localhost
REDIS_PORT=6379

# 🔥 Optional - Firebase
FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY=your_private_key

# 🔐 Security
SECRET_KEY=your_secret_key
JWT_SECRET=your_jwt_secret
```

> 💡 **Tip:** Copy `.env.example` → `.env` và điền các API keys của bạn

<br/>

---

## 📚 Documentation

<div align="center">

| 📖 Document | 📝 Mô tả |
|:-----------:|:---------|
| [SCRIPTS_GUIDE.md](SCRIPTS_GUIDE.md) | Hướng dẫn sử dụng 50+ automation scripts |
| [SECURITY.md](SECURITY.md) | Security policy và audit report (120 findings) |
| [requirements/](requirements/) | Chunked dependency management |
| [tests/](tests/) | Testing documentation và coverage |

</div>

<br/>

---

## 🤝 Contributing

1. **Fork** repository này
2. Tạo **feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit** changes: `git commit -m 'Add amazing feature'`
4. **Push** to branch: `git push origin feature/amazing-feature`
5. Mở **Pull Request**

> 🔒 Vui lòng đọc [SECURITY.md](SECURITY.md) trước khi contribute

<br/>

---

## 👥 Author & Collaborators

<div align="center">

<table>
<tr>
<td align="center" width="50%">

<img src="https://github.com/SkastVnT.png" width="120" height="120" style="border-radius: 50%; border: 3px solid #6366F1;" />

### **SkastVnT**

[![GitHub](https://img.shields.io/badge/GitHub-SkastVnT-181717?style=for-the-badge&logo=github)](https://github.com/SkastVnT)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:nguyvip007@gmail.com)

**Solo Developer • AI Enthusiast • Full-Stack Engineer**

*Developed with late nights, lots of coffee ☕, and a passion for AI*

**Role:** DevOps

</td>
<td align="center" width="50%">

<img src="https://github.com/sug1omyo.png" width="120" height="120" style="border-radius: 50%; border: 3px solid #10B981;" />

### **sug1omyo**

[![GitHub](https://img.shields.io/badge/GitHub-sug1omyo-181717?style=for-the-badge&logo=github)](https://github.com/sug1omyo)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:ngtuanhei2004@gmail.com)

**Fresher Software Engineer**

***Collaborator & Contributor***

*Atsui~*
*Atsukute hikarabisou*
*Ugoitenai no ni atsui yo~*

**Role:** Ý tưởng và fix, refactor, test, làm framework React, debug support code

</td>
</tr>
</table>

</div>

<br/>

---

## 📄 License

<div align="center">

**MIT License** - Xem chi tiết tại [LICENSE](LICENSE)

---

<br/>

### ⭐ Nếu project này hữu ích, hãy cho một Star!

<a href="https://github.com/SkastVnT/AI-Assistant/stargazers">
  <img src="https://img.shields.io/badge/⭐_Star_this_repo-FFD700?style=for-the-badge"/>
</a>
&nbsp;&nbsp;
<a href="https://discord.gg/d3K8Ck9NeR">
  <img src="https://img.shields.io/badge/💬_Join_Discord-5865F2?style=for-the-badge&logo=discord&logoColor=white"/>
</a>

<br/><br/>

**Made with ❤️ by [SkastVnT](https://github.com/SkastVnT) & [sug1omyo](https://github.com/sug1omyo)**

</div>
