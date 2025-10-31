# 🤖 AI Assistant - Integrated Multi-Service Platform# 🤖 AI Assistant - Integrated Multi-Service Platform



<div align="center"><div align="center">



![AI Assistant](https://img.shields.io/badge/AI-Assistant-purple?style=for-the-badge)![AI Assistant](https://img.shields.io/badge/AI-Assistant-purple?style=for-the-badge)

![Python](https://img.shields.io/badge/Python-3.10.6-blue?style=for-the-badge&logo=python)![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)

![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)

![CUDA](https://img.shields.io/badge/CUDA-11.8-green?style=for-the-badge&logo=nvidia)![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)



**Unified AI Platform with Multiple Services****Nền tảng tích hợp đa dịch vụ AI mạnh mẽ**



[Quick Start](#-quick-start) • [Services](#-services) • [Installation](#%EF%B8%8F-installation) • [Documentation](#-documentation)[Khởi động nhanh](#-khởi-động-nhanh) • [Tính năng](#-tính-năng) • [Cài đặt](#️-cài-đặt) • [Hướng dẫn](#-hướng-dẫn-sử-dụng) • [Đóng góp](#-đóng-góp)



</div></div>



------



## 📋 Overview## 🚀 Quick Start



**AI-Assistant** is a comprehensive AI platform integrating four powerful services:**New to this project?** Read [`GETTING_STARTED.md`](GETTING_STARTED.md) first!



1. 🤖 **ChatBot** - Multi-model conversational AI with local LLM and image generation```bash

2. 📊 **Text2SQL** - Natural language to SQL query conversion# Launch ChatBot with Stable Diffusion (Auto)

3. 🎤 **Speech2Text** - Vietnamese speech-to-text transcription.\scripts\startup\start_chatbot.bat

4. 🎨 **Stable Diffusion WebUI** - Advanced AI image generation

# ChatBot only (No image generation)

Each service operates independently with its own virtual environment, making deployment and maintenance simple and modular..\scripts\startup\start_chatbot_only.bat

```

---

**Documentation:**

## ✨ Features- Setup: `docs/setup/SETUP_NEW_DEVICE.txt`

- Image Gen: `docs/guides/IMAGE_GENERATION_GUIDE.md`

### 🤖 ChatBot Service- Troubleshooting: `docs/guides/FIX_*.md`

- **Multi-Model AI**: OpenAI GPT-4, Google Gemini, Local Qwen 1.5-1.8B

- **Image Generation**: Integrated Stable Diffusion with txt2img, img2img, LoRA, VAE---

- **Memory System**: Conversation history with image storage

- **Message Editing**: Edit and regenerate responses## �📋 Giới thiệu

- **PDF Export**: Export conversations with images

- **Modern UI**: Responsive Tailwind CSS design**AI Assistant Hub** là một nền tảng tổng hợp các dịch vụ AI tiên tiến, bao gồm:



### 📊 Text2SQL Service- 🤖 **AI ChatBot** - Trợ lý AI đa năng với Gemini, GPT-3.5, DeepSeek

- **Natural Language Processing**: Convert English to SQL queries- 🎤 **Speech to Text** - Chuyển đổi giọng nói thành văn bản (tiếng Việt)

- **Database Integration**: ClickHouse database support- 💾 **Text to SQL** - Tạo câu truy vấn SQL từ ngôn ngữ tự nhiên

- **Schema Intelligence**: Automatic table and column analysis

- **Query Validation**: Syntax checking and validationTất cả được kết nối qua một **Gateway Hub** với giao diện web đẹp mắt, hiện đại.

- **Multi-table Support**: Complex joins and relationships

---

### 🎤 Speech2Text Service

- **Vietnamese Optimized**: PhoWhisper + Whisper dual transcription## ✨ Tính năng

- **Speaker Diarization**: Identify and separate speakers

- **Smart Fusion**: Qwen2.5-1.5B LLM for accuracy enhancement### 🚀 AI Assistant Hub Gateway

- **Format Support**: WAV, MP3, M4A, FLAC- ✅ Giao diện web đẹp với **Tailwind CSS**

- **Web Interface**: Real-time transcription monitoring- ✅ Điều hướng tập trung đến các services

- ✅ Monitoring và health checks

### 🎨 Stable Diffusion WebUI- ✅ Responsive design, dark theme

- **Advanced Generation**: txt2img, img2img, inpainting- ✅ Quick start scripts

- **Model Support**: Stable Diffusion 1.5, 2.1, SDXL

- **Extensions**: LoRA, Hypernetworks, Textual Inversion### 🤖 AI ChatBot

- **Upscaling**: RealESRGAN, LDSR, SwinIR- ✅ 3 mô hình AI: **Gemini, GPT-3.5, DeepSeek**

- **API Access**: RESTful API for integration- ✅ 3 chế độ: Tâm lý, Đời sống, Trò chuyện

- ✅ Lưu lịch sử conversation

---- ✅ Real-time chat interface



## 🚀 Quick Start### 🎤 Speech to Text

- ✅ Nhận dạng giọng nói **tiếng Việt**

### Prerequisites- ✅ **Speaker Diarization** (phân tách người nói)

- ✅ Hỗ trợ nhiều format: WAV, MP3, M4A, FLAC

- **Python 3.10.6** (required)- ✅ WebSocket real-time updates

- **NVIDIA GPU** with CUDA 11.8+ (for AI models)- ✅ PhoWhisper & Whisper models

- **16GB+ RAM** (32GB recommended)

- **50GB+ free disk space**### 💾 Text to SQL

- **Git** for cloning repository- ✅ Tạo SQL từ ngôn ngữ tự nhiên

- ✅ **Gemini AI** powered

### 1. Clone Repository- ✅ Memory system - học từ lịch sử

- ✅ Hỗ trợ nhiều loại database

```bash- ✅ Evaluation metrics

git clone https://github.com/SkastVnT/AI-Assistant.git

cd AI-Assistant---

```

## 🚀 Khởi động nhanh

### 2. Choose and Setup Service

### Cách 1: Khởi động Hub Gateway

Each service has its own setup guide. Navigate to the service folder:```bash

# Clone repository

**For ChatBot:**git clone https://github.com/SkastVnT/AI-Assistant.git

```bashcd AI-Assistant

cd ChatBot

# Follow ChatBot/README.md for setup# Cài đặt dependencies

```pip install -r requirements.txt



**For Text2SQL:**# Khởi động Hub

```bashpython hub.py

cd "Text2SQL Services"```

# Follow Text2SQL Services/README.md for setup

```Truy cập: **http://localhost:3000**



**For Speech2Text:**### Cách 2: Khởi động tất cả services

```bash

cd "Speech2Text Services"**Windows:**

# Follow Speech2Text Services/README.md for setup```bash

```start_all.bat

```

**For Stable Diffusion:**

```bash**Linux/Mac:**

cd stable-diffusion-webui```bash

# Follow stable-diffusion-webui/README.md for setupchmod +x start_all.sh

```./start_all.sh

```

### 3. Quick Launch Scripts (Windows)

---

```bash

# ChatBot with Stable Diffusion (recommended)## 🏗️ Kiến trúc

.\scripts\startup\start_chatbot_with_sd.bat

```

# ChatBot only┌─────────────────────────────────────────┐

.\scripts\startup\start_chatbot_only.bat│   AI Assistant Hub (Port 3000)          │

```│   - Gateway & UI                        │

│   - Service discovery                   │

---└──────────────┬──────────────────────────┘

               │

## 🗂️ Project Structure    ┌──────────┼──────────┐

    │          │          │

```    ▼          ▼          ▼

AI-Assistant/┌────────┐ ┌────────┐ ┌────────┐

├── ChatBot/                      # Chatbot service│ChatBot │ │Speech  │ │Text2SQL│

│   ├── app.py                    # Main application│:5000   │ │:5001   │ │:5002   │

│   ├── requirements.txt          # Dependencies└────────┘ └────────┘ └────────┘

│   ├── README.md                 # Service documentation```

│   ├── venv_chatbot/             # Virtual environment

│   ├── templates/                # HTML templates---

│   ├── static/                   # CSS, JS, images

│   ├── models/                   # Local AI models## 🛠️ Cài đặt

│   └── Storage/                  # Generated images

│### Yêu cầu hệ thống

├── Text2SQL Services/            # Text2SQL service- **Python:** 3.8+

│   ├── app.py                    # Main application- **RAM:** 8GB (tối thiểu), 16GB (khuyến nghị)

│   ├── requirements.txt          # Dependencies- **Storage:** 10GB+ free space

│   ├── README.md                 # Service documentation- **GPU:** Optional (tốt cho Speech2Text)

│   ├── templates/                # HTML templates

│   └── data/                     # Training data### Bước 1: Clone repository

│```bash

├── Speech2Text Services/         # Speech2Text servicegit clone https://github.com/SkastVnT/AI-Assistant.git

│   ├── requirements.txt          # Dependenciescd AI-Assistant

│   ├── README.md                 # Service documentation```

│   ├── app/                      # Application code

│   │   ├── core/                 # Core functionality### Bước 2: Cài đặt dependencies

│   │   ├── api/                  # API endpoints

│   │   └── web_ui.py             # Web interface**Hub:**

│   └── data/                     # Audio data```bash

│pip install -r requirements.txt

├── stable-diffusion-webui/       # Stable Diffusion service```

│   ├── webui.py                  # Main WebUI

│   ├── requirements.txt          # Dependencies**ChatBot:**

│   ├── README.md                 # Service documentation```bash

│   ├── models/                   # SD models (large files)cd ChatBot

│   └── outputs/                  # Generated imagespip install -r requirements.txt

│cd ..

├── docs/                         # Documentation```

│   ├── GETTING_STARTED.md        # Getting started guide

│   ├── PROJECT_STRUCTURE.md      # Project structure**Speech2Text:**

│   └── guides/                   # Various guides```bash

│cd "Speech2Text Services"

├── scripts/                      # Utility scriptspip install -r requirements.txt

│   └── startup/                  # Launch scriptscd ..

│```

├── requirements.txt              # Root dependencies

├── README.md                     # This file**Text2SQL:**

└── .gitignore                    # Git ignore rules```bash

```cd "Text2SQL Services"

pip install -r requirements.txt

---cd ..

```

## 🛠️ Installation

### Bước 3: Cấu hình API Keys

### System Requirements

Tạo file `.env` tại thư mục gốc:

| Component | Minimum | Recommended |

|-----------|---------|-------------|```env

| Python | 3.10.6 | 3.10.6 |# OpenAI

| GPU | NVIDIA GTX 1060 6GB | RTX 3060 12GB+ |OPENAI_API_KEY=sk-...

| RAM | 16GB | 32GB |

| Storage | 50GB | 100GB SSD |# DeepSeek

| OS | Windows 10 | Windows 11 |DEEPSEEK_API_KEY=sk-...



### Install Python 3.10.6# Google Gemini

GEMINI_API_KEY_1=AIza...

```bashGEMINI_API_KEY_2=AIza...

# Download from python.org

# Or use pyenv (recommended)# HuggingFace

pyenv install 3.10.6HF_API_TOKEN=hf_...

pyenv global 3.10.6

```# Flask

FLASK_SECRET_KEY=your-secret-key

### Install CUDA 11.8```



1. Download from [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-11-8-0-download-archive)Copy `.env` vào các thư mục services tương ứng.

2. Install following the wizard

3. Verify: `nvidia-smi`---



### Install PyTorch## 📖 Hướng dẫn sử dụng



```bash### Khởi động Hub Gateway

# For CUDA 11.8

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118```bash

```python hub.py

```

---

Truy cập **http://localhost:3000** để xem dashboard và chọn service.

## 📚 Documentation

### Khởi động từng service riêng

### Service Documentation

**Terminal 1 - ChatBot:**

- [ChatBot README](ChatBot/README.md) - ChatBot setup and usage```bash

- [Text2SQL README](Text2SQL%20Services/README.md) - Text2SQL setup and usagecd ChatBot

- [Speech2Text README](Speech2Text%20Services/README.md) - Speech2Text setup and usagepython app.py

- [Stable Diffusion README](stable-diffusion-webui/README.md) - SD WebUI setup and usage```



### General Documentation**Terminal 2 - Speech2Text:**

```bash

- [Getting Started](docs/GETTING_STARTED.md) - First-time setup guidecd "Speech2Text Services/app"

- [Project Structure](docs/PROJECT_STRUCTURE.md) - Detailed project structurepython web_ui.py --port 5001

- [Quick Reference](docs/QUICK_REFERENCE.md) - Quick reference guide```



### Guides**Terminal 3 - Text2SQL:**

```bash

- [Image Generation Guide](ChatBot/docs/IMAGE_GENERATION_TOOL_GUIDE.md)cd "Text2SQL Services"

- [LoRA & VAE Guide](ChatBot/docs/LORA_VAE_GUIDE.md)python app.py --port 5002

- [Troubleshooting](docs/guides/TROUBLESHOOTING.md)```



---### Sử dụng services



## 🌐 Service Endpoints1. Mở **http://localhost:3000**

2. Click vào card của service bạn muốn dùng

| Service | Port | URL | Description |3. Service sẽ mở trong tab mới

|---------|------|-----|-------------|4. Bắt đầu sử dụng!

| ChatBot | 5000 | http://localhost:5000 | Main chatbot interface |

| Text2SQL | 5001 | http://localhost:5001 | SQL generation interface |---

| Speech2Text | 5002 | http://localhost:5002 | Transcription interface |

| Stable Diffusion | 7860 | http://localhost:7860 | Image generation UI |## 📚 Documentation

| SD API | 7860 | http://localhost:7860/docs | API documentation |

### Quick Start Guides

---- � [Quick Start](QUICKSTART.md) - Hướng dẫn khởi động nhanh

- 🎯 [Quick Reference](QUICK_REFERENCE.md) - Cheat sheet & commands

## 🔧 Configuration

### Architecture & Design

### Environment Variables- 📘 [Hub Gateway Guide](docs/HUB_README.md) - Chi tiết về Hub Gateway

- 🏗️ [Project Structure](docs/PROJECT_STRUCTURE.md) - Cấu trúc project đầy đủ

Each service uses `.env` file for configuration. Copy `.env.example` to `.env` in each service folder:- 🔄 [Refactoring Summary](docs/REFACTORING_SUMMARY.md) - Quá trình refactor



**ChatBot (.env):**### Service Documentation

```env- 📙 [ChatBot README](ChatBot/README.md) - Hướng dẫn ChatBot service

OPENAI_API_KEY=your_openai_key- 📕 [Speech2Text README](Speech2Text%20Services/README.md) - Hướng dẫn Speech2Text

GOOGLE_API_KEY=your_gemini_key- 📓 [Text2SQL README](Text2SQL%20Services/README) - Hướng dẫn Text2SQL

SD_API_URL=http://127.0.0.1:7860

```### Project Info

- 🎉 [Mission Complete](docs/MISSION_COMPLETE.md) - Tổng kết hoàn thành

**Text2SQL (.env):**

```env---

GOOGLE_API_KEY=your_gemini_key

CLICKHOUSE_HOST=localhost## 🎯 Use Cases

CLICKHOUSE_DATABASE=default

```### ChatBot

- Tư vấn tâm lý, tâm sự

**Speech2Text (.env):**- Giải pháp đời sống, công việc

```env- Trò chuyện giải trí

HF_TOKEN=your_huggingface_token  # Optional for gated models

```### Speech2Text

- Phiên âm cuộc họp, hội thảo

---- Chuyển đổi podcast/video thành text

- Phân tích cuộc trò chuyện

## 🐛 Troubleshooting

### Text2SQL

### Common Issues- Truy vấn database bằng ngôn ngữ tự nhiên

- Data analytics không cần SQL

**1. Import torch error**- Business intelligence

```bash

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118---

```

## 🐛 Troubleshooting

**2. CUDA not detected**

```bash### Port đã được sử dụng?

# Verify CUDA installation```bash

nvidia-smi# Windows

netstat -ano | findstr :5000

# Reinstall PyTorch with CUDA

pip uninstall torch torchvision torchaudio# Linux/Mac

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118lsof -i :5000

``````



**3. Port already in use**### Lỗi API Key?

```bash- Kiểm tra file `.env` có đúng format

# Change port in service .env file or config- Verify API keys còn hoạt động

FLASK_PORT=5050- Check quota của API keys

```

### Out of Memory?

**4. Virtual environment issues**- Chạy từng service một

```bash- Đóng các app khác

# Delete and recreate venv- Nâng cấp RAM

Remove-Item -Recurse venv_*

python -m venv venv_servicenameXem thêm trong [HUB_README.md](HUB_README.md)

.\venv_servicename\Scripts\activate

pip install -r requirements.txt---

```

## 🔒 Security

---

⚠️ **QUAN TRỌNG:**

## 🔄 Updates & Versions- **KHÔNG** commit file `.env` vào Git

- **KHÔNG** share API keys

### Latest Version: Ver_1 (October 2025)- Sử dụng `.env` riêng cho mỗi môi trường

- Đổi `FLASK_SECRET_KEY` định kỳ

**What's New:**

- ✅ All services integrated in single repository---

- ✅ Updated to Python 3.10.6

- ✅ Comprehensive README for each service## 📊 Project Structure

- ✅ Updated requirements.txt with version pinning

- ✅ Improved .gitignore for better repository management```

- ✅ Stable Diffusion and Speech2Text fully integratedAI-Assistant/

├── hub.py                      # Hub Gateway main file

### Previous Versions:├── templates/

- **Img2Img Branch**: Added img2img support with LoRA and VAE│   └── index.html             # Hub UI (Tailwind CSS)

- **ChatBotCoding Branch**: Initial chatbot implementation├── requirements.txt           # Hub dependencies

├── start_all.bat/sh          # Start all services script

---├── QUICKSTART.md             # Quick start guide

├── HUB_README.md             # Hub detailed docs

## 📝 License│

├── ChatBot/                   # ChatBot Service

This project is licensed under the MIT License. See individual service folders for specific licensing information.│   ├── app.py

│   ├── templates/

### Third-Party Software│   ├── requirements.txt

│   └── README.md

- **Stable Diffusion WebUI**: AGPL-3.0 License│

- **Transformers**: Apache 2.0 License├── Speech2Text Services/      # Speech2Text Service

- **Flask**: BSD-3-Clause License│   ├── app/

│   │   └── web_ui.py

---│   ├── requirements.txt

│   └── README.md

## 🤝 Contributing│

└── Text2SQL Services/         # Text2SQL Service

Contributions are welcome! Please:    ├── app.py

    ├── requirements.txt

1. Fork the repository    └── README

2. Create a feature branch (`git checkout -b feature/AmazingFeature`)```

3. Commit your changes (`git commit -m 'Add AmazingFeature'`)

4. Push to the branch (`git push origin feature/AmazingFeature`)---

5. Open a Pull Request

## 🤝 Đóng góp

---

Contributions are welcome! 

## 📧 Support

1. Fork the project

- **Issues**: [GitHub Issues](https://github.com/SkastVnT/AI-Assistant/issues)2. Create your feature branch (`git checkout -b feature/AmazingFeature`)

- **Discussions**: [GitHub Discussions](https://github.com/SkastVnT/AI-Assistant/discussions)3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)

4. Push to the branch (`git push origin feature/AmazingFeature`)

---5. Open a Pull Request



## 🙏 Acknowledgments---



- **AUTOMATIC1111** - Stable Diffusion WebUI## 📝 TODO

- **OpenAI** - GPT models

- **Google** - Gemini API- [ ] Docker Compose deployment

- **HuggingFace** - Transformers and models- [ ] User authentication system

- **Qwen Team** - Qwen local models- [ ] Real-time service monitoring

- **VinAI** - PhoWhisper Vietnamese ASR- [ ] API Gateway with rate limiting

- [ ] Centralized logging

---- [ ] Unit tests

- [ ] CI/CD pipeline

<div align="center">- [ ] Database integration

- [ ] WebSocket support for all services

**Made with ❤️ by SkastVnT**- [ ] Multi-language support



⭐ Star this repo if you find it helpful!---



</div>## 📄 License


This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

Made with ❤️ by **AI Assistant Team**

### Contributors
- [SkastVnT](https://github.com/SkastVnT) - Project Lead

---

## 🌟 Support

Nếu project này hữu ích, hãy cho một ⭐️!

---

## 📞 Contact

- **GitHub:** [@SkastVnT](https://github.com/SkastVnT)
- **Repository:** [AI-Assistant](https://github.com/SkastVnT/AI-Assistant)
- **Issues:** [Report Bug](https://github.com/SkastVnT/AI-Assistant/issues)

---

## 🎉 Acknowledgments

- OpenAI for GPT-3.5
- Google for Gemini AI
- DeepSeek for DeepSeek model
- HuggingFace for model hosting
- All open-source contributors

---

<div align="center">

**[⬆ Back to Top](#-ai-assistant---integrated-multi-service-platform)**

Made with 💜 in Vietnam

</div>
