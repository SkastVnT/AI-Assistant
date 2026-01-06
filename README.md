<div align="center">

# 🤖 AI-Assistant 
### *Nền Tảng Tích Hợp Đa Dịch Vụ AI*

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&duration=3000&pause=1000&color=6366F1&center=true&vCenter=true&width=600&lines=ChatBot+%7C+Text2SQL+%7C+Speech2Text+%7C+Image+Gen;Document+Intelligence+%7C+Upscaling+%7C+LoRA+Training;Multi-Model+AI+Platform;Built+with+%E2%9D%A4%EF%B8%8F+by+SkastVnT" alt="Typing SVG" />

---

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=for-the-badge&logo=redis&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge)

[![Stars](https://img.shields.io/github/stars/SkastVnT/AI-Assistant?style=for-the-badge&logo=github&color=FFD700)](https://github.com/SkastVnT/AI-Assistant)
[![Forks](https://img.shields.io/github/forks/SkastVnT/AI-Assistant?style=for-the-badge&logo=github&color=3B82F6)](https://github.com/SkastVnT/AI-Assistant)

**🌟 Nền tảng tích hợp 8+ dịch vụ AI 🚀**

[📖 Features](#-services) • [⚡ Quick Start](#-quick-start) • [🎮 Scripts](#-scripts) • [📚 Docs](#-documentation)

</div>

---

## ⚡ Quick Start

```bash
# Clone repository
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant

# Option 1: Interactive Menu (Easiest!)
menu.bat

# Option 2: Start Individual Service
scripts\start-chatbot.bat          # Port 5001
scripts\start-text2sql.bat         # Port 5002
scripts\start-hub-gateway.bat      # Port 3000

# Option 3: Docker
docker-compose up -d
```

---

## 🎯 Services

| Service | Description | Port | Status |
|---------|-------------|------|--------|
| 🤖 **ChatBot** | Multi-model AI Chat (GROK, GPT-4, DeepSeek) + MongoDB | `5001` | ✅ Production |
| 📊 **Text2SQL** | Natural Language → SQL Query | `5002` | ✅ Production |
| 📄 **Document Intelligence** | OCR + AI Document Analysis | `5003` | ✅ Production |
| 🎙️ **Speech2Text** | Vietnamese Transcription + Speaker Diarization | `7860` | ✅ Production |
| 🎨 **Stable Diffusion** | AI Image Generation | `7861` | ✅ Ready |
| ✨ **LoRA Training** | Fine-tune SD Models | N/A | ✅ Ready |
| 🖼️ **Image Upscale** | RealESRGAN Enhancement | N/A | ✅ Ready |
| 🎯 **Hub Gateway** | API Gateway & Orchestration | `3000` | ✅ Production |
| 🔌 **MCP Server** | Model Context Protocol for Claude | N/A | ✅ Ready |

---

## 🤖 ChatBot Highlights

**Database Migration Complete (MongoDB + Redis)**

- ✅ **MongoDB**: Conversations, Messages, Memory với Repository Pattern
- ✅ **Redis**: Caching với TTL và compression
- ✅ **Health Checks**: `/health`, `/health/live`, `/health/ready`, `/health/detailed`
- ✅ **Metrics**: Prometheus-compatible metrics
- ✅ **Multi-Model**: GROK, GPT-4, DeepSeek, Qwen
- ✅ **Streaming**: Real-time token-by-token output
- ✅ **Code Execution**: Secure Python/JS sandbox

---

## 🎮 Scripts

```bash
# Start Services
scripts\start-all.bat              # All services
scripts\start-chatbot.bat          # ChatBot only
scripts\start-hub-gateway.bat      # Hub Gateway

# Management
scripts\stop-all.bat               # Stop all
scripts\health-check-all.bat       # Health checks
scripts\deploy-chatbot.bat         # Deploy with backup
scripts\rollback-chatbot.bat       # Rollback if needed

# Testing
scripts\test-all.bat               # Run all tests
scripts\test_mongodb.py            # Test MongoDB connection
```

---

## 📁 Project Structure

```
AI-Assistant/
├── services/                      # All Microservices
│   ├── chatbot/                  # ChatBot (MongoDB + Redis)
│   │   ├── database/             # Repository Pattern
│   │   ├── utils/                # Health, Logger, Metrics
│   │   └── config/               # Configuration
│   ├── text2sql/                 # Text2SQL Service
│   ├── document-intelligence/    # Document OCR & Analysis
│   ├── speech2text/              # Speech Recognition
│   ├── stable-diffusion/         # Image Generation
│   ├── lora-training/            # LoRA Training
│   ├── image-upscale/            # Image Enhancement
│   ├── hub-gateway/              # API Gateway
│   └── mcp-server/               # MCP Server
├── scripts/                       # Management Scripts
├── docs/                          # Documentation
├── tests/                         # Test Suite
├── infrastructure/                # Docker & Deployment
└── config/                        # Global Configuration
```

---

## 📚 Documentation

| Document | Description |
|----------|-------------|
| [docs/GETTING_STARTED.md](docs/GETTING_STARTED.md) | Quick start guide |
| [docs/SETUP_GUIDE.md](docs/SETUP_GUIDE.md) | Detailed setup instructions |
| [docs/API_DOCUMENTATION.md](docs/API_DOCUMENTATION.md) | API reference |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | System architecture |
| [docs/CHATBOT_MIGRATION_GUIDE.md](docs/CHATBOT_MIGRATION_GUIDE.md) | ChatBot MongoDB migration |
| [docs/SCRIPTS_GUIDE.md](docs/SCRIPTS_GUIDE.md) | Scripts documentation |

---

## 🐳 Docker

```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d chatbot mongodb redis

# View logs
docker-compose logs -f chatbot

# Health check
curl http://localhost:5001/health/detailed
```

---

## 🧪 Testing

```bash
# ChatBot tests (Repository Pattern)
cd services/chatbot
python -m pytest tests/ -v

# All services
scripts\test-all.bat
```

---

## 🔧 Environment Variables

```env
# MongoDB
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=chatbot

# Redis (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379

# AI APIs
GROK_API_KEY=your_key
OPENAI_API_KEY=your_key
```

---

## 📊 Metrics & Monitoring

```bash
# Health endpoints
GET /health              # Basic health
GET /health/live         # Liveness probe
GET /health/ready        # Readiness probe
GET /health/detailed     # Full status with dependencies

# Metrics
GET /metrics             # Prometheus format
```

---
## Author & Collaborators
</div>

<table>
<tr>
<td align="center" width="50%">

<img src="https://github.com/SkastVnT.png" width="120" height="120" style="border-radius: 50%; border: 3px solid #6366F1;" />

### **SkastVnT**

[![GitHub](https://img.shields.io/badge/GitHub-SkastVnT-181717?style=for-the-badge&logo=github)](https://github.com/SkastVnT)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:nguyvip007@gmail.com)

**Solo Developer • AI Enthusiast • Full-Stack Engineer**

*Developed with late nights, lots of coffee ☕, and a passion for AI* 

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


</td>
</tr>
</table>

<div align="center">

---

<div align="center">



## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

<div align="center">

**Made with ❤️ by [SkastVnT](https://github.com/SkastVnT)**

[![GitHub](https://img.shields.io/badge/GitHub-SkastVnT-181717?style=flat-square&logo=github)](https://github.com/SkastVnT)
[![Discord](https://img.shields.io/badge/Discord-Join-5865F2?style=flat-square&logo=discord)](https://discord.gg/d3K8Ck9NeR)

**⭐ Star us on GitHub if you find this useful!**

</div>
