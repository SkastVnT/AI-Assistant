# 🤖 AI-Assistant - Nền Tảng Tích Hợp Đa Dịch Vụ AI# 🤖 AI-Assistant - Nền Tảng Tích Hợp Đa Dịch Vụ AI 🤖



<div align="center">



![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)<div align="center"><div align="center">

![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)

![AI](https://img.shields.io/badge/AI-Powered-purple?style=for-the-badge)

![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)

**Nền tảng tích hợp 4 dịch vụ AI mạnh mẽ: ChatBot, Text2SQL, Speech2Text, Image Generation**

![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)

[Tính năng](#-tính-năng-nổi-bật) • [Khởi động nhanh](#-quick-start) • [Cài đặt](#️-yêu-cầu-hệ-thống) • [Tài liệu](#-tài-liệu)

![AI](https://img.shields.io/badge/AI-Powered-purple?style=for-the-badge)![AI](https://img.shields.io/badge/AI-Powered-purple?style=for-the-badge)

</div>

![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---



## 📋 Tổng Quan

**Nền tảng tích hợp 4 dịch vụ AI mạnh mẽ: ChatBot, Text2SQL, Speech2Text, Image Generation****Nền tảng tích hợp 4 dịch vụ AI mạnh mẽ: ChatBot, Text2SQL, Speech2Text, Image Generation**

**AI-Assistant** là nền tảng AI tích hợp gồm **4 dịch vụ độc lập**, mỗi service có thể chạy riêng hoặc kết hợp với nhau. Dự án được xây dựng theo chuẩn **Generative AI Template** với kiến trúc modular, production-ready.



### 🎯 Các Dịch Vụ

[Tính năng](#-tính-năng-nổi-bật) • [Khởi động nhanh](#-quick-start) • [Cài đặt](#️-yêu-cầu-hệ-thống) • [Tài liệu](#-tài-liệu)[Tính năng](#-tính-năng-nổi-bật) • [Khởi động nhanh](#-quick-start) • [Cài đặt](#️-cài-đặt) • [Tài liệu](#-tài-liệu)

| Service | Mô Tả | Port | Status | Docs |

|---------|-------|------|--------|------|

| 🤖 **ChatBot** | Multi-model AI (Gemini, GPT-4, Qwen) + Image Gen | 5001 | ✅ Ready | [📖 Docs](ChatBot/README.md) |

| 📊 **Text2SQL** ⭐ | Natural Language → SQL với AI Learning | 5002 | ✅ Production | [📖 Docs](Text2SQL%20Services/README.md) |</div></div>

| 🎤 **Speech2Text** | Vietnamese transcription + Diarization | 7860 | 🔧 Beta | [📖 Docs](Speech2Text%20Services/README.md) |

| 🎨 **Stable Diffusion** | AI Image Generation (AUTOMATIC1111 WebUI) | 7861 | ✅ Ready | [📖 Docs](stable-diffusion-webui/README.md) |



---------



## ✨ Tính Năng Nổi Bật



### 🤖 ChatBot Service (v2.0)## 📋 Tổng Quan## 📋 Tổng Quan



- ✅ **Multi-Model Support**: Gemini 2.0 Flash, GPT-4, DeepSeek, Qwen 1.5B (local), BloomVN

- ✅ **Image Generation**: Tích hợp Stable Diffusion với LoRA & VAE support

- ✅ **AI Memory System**: Lưu trữ conversations và generated images**AI-Assistant** là nền tảng AI tích hợp gồm **4 dịch vụ độc lập**, mỗi service có thể chạy riêng hoặc kết hợp với nhau. Dự án được xây dựng theo chuẩn **Generative AI Template** với kiến trúc modular, production-ready.**AI-Assistant** là nền tảng AI tích hợp gồm **4 dịch vụ độc lập**, mỗi service có thể chạy riêng hoặc kết hợp với nhau:

- ✅ **Tools Integration**: Google Search, GitHub Search

- ✅ **Export PDF**: Export conversations kèm images và metadata

- ✅ **Modern UI**: Tailwind CSS, responsive design, dark mode support

### 🎯 Các Dịch Vụ| Service | Mô Tả | Port | Status | Docs |

👉 **[Chi tiết đầy đủ →](ChatBot/README.md)** | 🚀 **Port**: 5001

|---------|-------|------|--------|------|

---

| Service | Mô Tả | Port | Status | Docs || 🤖 **ChatBot** | Multi-model AI (Gemini, GPT-4, Qwen) + Image Gen | 5001 | ✅ Ready | [📖 Docs](ChatBot/README.md) |

### 📊 Text2SQL Service ⭐ **MỚI NHẤT v2.0**

|---------|-------|------|--------|------|| 📊 **Text2SQL** ⭐ | Natural Language → SQL với AI Learning | 5002 | ✅ Production | [📖 Docs](Text2SQL%20Services/README.md) |

- ✅ **Natural Language to SQL**: Chuyển đổi tiếng Việt/English thành SQL queries

- ✅ **Multi-Database Support**: ClickHouse, MongoDB, PostgreSQL, MySQL, SQL Server| 🤖 **ChatBot** | Multi-model AI (Gemini, GPT-4, Qwen) + Image Gen | 5001 | ✅ Ready | [📖](ChatBot/README.md) || 🎤 **Speech2Text** | Vietnamese transcription + Diarization | 7860 | 🔧 Beta | [📖 Docs](Speech2Text%20Services/README.md) |

- ✅ **AI Learning System**: Lưu SQL đúng vào Knowledge Base, tự học từ user feedback

- ✅ **Question Generation**: Tự động tạo 5 câu hỏi mẫu từ database schema| 📊 **Text2SQL** ⭐ | Natural Language → SQL với AI Learning | 5002 | ✅ Production | [📖](Text2SQL%20Services/README.md) || 🎨 **Stable Diffusion** | AI Image Generation (AUTOMATIC1111 WebUI) | 7861 | ✅ Ready | [📖 Docs](stable-diffusion-webui/README.md) |

- ✅ **Database Connection**: Kết nối trực tiếp localhost & MongoDB Atlas

- ✅ **Deep Thinking Mode**: Enhanced reasoning cho complex queries| 🎤 **Speech2Text** | Vietnamese transcription + Diarization | 7860 | 🔧 Beta | [📖](Speech2Text%20Services/README.md) |

- ✅ **Ready to Deploy**: Hướng dẫn deploy FREE trên Render.com

| 🎨 **Stable Diffusion** | AI Image Generation (AUTOMATIC1111) | 7861 | ✅ Ready | [📖](stable-diffusion-webui/README.md) |

👉 **[Chi tiết đầy đủ →](Text2SQL%20Services/README.md)** | 🚀 **Port**: 5002  

📦 **[Deployment Guide →](Text2SQL%20Services/README.md#-deployment)**



---------



### 🎤 Speech2Text Service (v3.6.0+)



- ✅ **Dual-Model Fusion**: Whisper + PhoWhisper cho accuracy tối đa (98%+)## ✨ Tính Năng Nổi Bật## ✨ Tính Năng Nổi Bật

- ✅ **Vietnamese Optimized**: Fine-tuned cho tiếng Việt

- ✅ **Speaker Diarization**: pyannote.audio 3.1 với 95-98% accuracy

- ✅ **Qwen Enhancement**: LLM-powered transcript refinement

- ✅ **Real-time Web UI**: Progress tracking với WebSocket### 🤖 ChatBot Service (v2.0)### 🤖 ChatBot Service (v2.0)

- ✅ **Multi-format Support**: MP3, WAV, M4A, FLAC



👉 **[Chi tiết đầy đủ →](Speech2Text%20Services/README.md)** | 🚀 **Port**: 7860

- ✅ **Multi-Model Support**: Gemini 2.0 Flash, GPT-4, DeepSeek, Qwen 1.5B (local), BloomVN- ✅ **Multi-Model**: Gemini 2.0, GPT-4, DeepSeek, Qwen 1.5B (local), BloomVN

---

- ✅ **Image Generation**: Tích hợp Stable Diffusion với LoRA & VAE support- ✅ **Image Generation**: Tích hợp Stable Diffusion với LoRA & VAE support

### 🎨 Stable Diffusion WebUI

- ✅ **AI Memory System**: Lưu trữ conversations và generated images- ✅ **AI Memory System**: Lưu conversations + generated images

> **Based on [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui)**  

> *Customized configuration for optimized performance*- ✅ **Tools Integration**: Google Search, GitHub Search- ✅ **Tools Integration**: Google Search, GitHub Search



- ✅ **Text-to-Image**: Tạo ảnh từ text prompts- ✅ **Export PDF**: Export conversations kèm images và metadata- ✅ **Export PDF**: Conversations với images và metadata

- ✅ **Image-to-Image**: Transform và edit images

- ✅ **LoRA + VAE**: Fine-tuned models support- ✅ **Modern UI**: Tailwind CSS, responsive design, dark mode support- ✅ **Modern UI**: Tailwind CSS, responsive, dark mode

- ✅ **ControlNet**: Precise generation control

- ✅ **API Enabled**: RESTful API, tích hợp sẵn với ChatBot

- ✅ **GPU Optimized**: CUDA 12.1, xformers support

👉 **[Chi tiết →](ChatBot/README.md)** | 🚀 **Port**: 5001👉 **[Chi tiết đầy đủ →](ChatBot/README.md)**

👉 **[Chi tiết đầy đủ →](stable-diffusion-webui/README.md)** | 🚀 **Port**: 7861  

🔗 **[Original Project →](https://github.com/AUTOMATIC1111/stable-diffusion-webui)**



---------



## 🚀 Quick Start



### 1️⃣ Text2SQL (Khuyến nghị - Dễ nhất!)### 📊 Text2SQL Service ⭐ **MỚI NHẤT v2.0**### 📊 Text2SQL Service ⭐ **MỚI NHẤT v2.0**



```bash

# Di chuyển vào thư mục

cd "Text2SQL Services"- ✅ **Natural Language to SQL**: Chuyển đổi tiếng Việt/English thành SQL queries- ✅ **NL to SQL**: Chuyển đổi tiếng Việt/English → SQL queries



# Tạo virtual environment- ✅ **Multi-Database Support**: ClickHouse, MongoDB, PostgreSQL, MySQL, SQL Server- ✅ **Multi-Database**: ClickHouse, MongoDB, PostgreSQL, MySQL, SQL Server

python -m venv Text2SQL

.\Text2SQL\Scripts\activate- ✅ **AI Learning System**: Lưu SQL đúng vào Knowledge Base, tự học từ user feedback- ✅ **AI Learning**: Lưu SQL đúng vào Knowledge Base, tự học từ user



# Cài đặt dependencies- ✅ **Question Generation**: Tự động tạo 5 câu hỏi mẫu từ database schema- ✅ **Question Generation**: Tự động tạo 5 câu hỏi mẫu từ schema

pip install -r requirements.txt

- ✅ **Database Connection**: Kết nối trực tiếp localhost & MongoDB Atlas- ✅ **Database Connection**: Kết nối trực tiếp localhost & Atlas databases

# Cấu hình API key

cp .env.example .env- ✅ **Deep Thinking Mode**: Enhanced reasoning cho complex queries- ✅ **Deep Thinking Mode**: Enhanced reasoning cho queries phức tạp

# Chỉnh sửa .env và thêm GEMINI_API_KEY_1

- ✅ **Ready to Deploy**: Hướng dẫn deploy FREE trên Render.com- ✅ **Ready to Deploy**: Hướng dẫn deploy FREE trên Render.com

# Khởi động service

python app_simple.py

# → http://localhost:5002

```👉 **[Chi tiết →](Text2SQL%20Services/README.md)** | 🚀 **Port**: 5002 | 📦 **[Deploy Guide](Text2SQL%20Services/README.md#-deployment)**👉 **[Chi tiết đầy đủ →](Text2SQL%20Services/README.md)**  



**Chi tiết:** [Text2SQL Setup Guide →](Text2SQL%20Services/README.md#-quick-start)🚀 **[Deployment Guide →](Text2SQL%20Services/README.md#-deployment)**



------



### 2️⃣ ChatBot---



```bash### 🎤 Speech2Text Service (v3.6.0+)

# Di chuyển vào thư mục

cd ChatBot### 🎤 Speech2Text Service (v3.6.0+)



# Tạo virtual environment- ✅ **Dual-Model Fusion**: Whisper + PhoWhisper cho accuracy tối đa (98%+)

python -m venv venv_chatbot

.\venv_chatbot\Scripts\activate- ✅ **Vietnamese Optimized**: Fine-tuned cho tiếng Việt- ✅ **Dual-Model Fusion**: Whisper + PhoWhisper cho accuracy tối đa



# Cài đặt dependencies- ✅ **Speaker Diarization**: pyannote.audio 3.1 với 95-98% accuracy- ✅ **Vietnamese Optimized**: 98%+ accuracy cho tiếng Việt

pip install -r requirements.txt

- ✅ **Qwen Enhancement**: LLM-powered transcript refinement- ✅ **Speaker Diarization**: pyannote.audio 3.1 (95-98% accuracy)

# Cấu hình API keys

cp .env.example .env- ✅ **Real-time Web UI**: Progress tracking với WebSocket- ✅ **Qwen Enhancement**: LLM-powered transcript refinement

# Chỉnh sửa .env và thêm OPENAI_API_KEY, GEMINI_API_KEY

- ✅ **Multi-format Support**: MP3, WAV, M4A, FLAC- ✅ **Web UI**: Real-time progress tracking với WebSocket

# Khởi động service

python app.py- ✅ **Multi-format**: MP3, WAV, M4A, FLAC support

# → http://localhost:5001

```👉 **[Chi tiết →](Speech2Text%20Services/README.md)** | 🚀 **Port**: 7860



**Chi tiết:** [ChatBot Setup Guide →](ChatBot/README.md)👉 **[Chi tiết đầy đủ →](Speech2Text%20Services/README.md)**



------



### 3️⃣ Speech2Text---



```bash### 🎨 Stable Diffusion WebUI

# Di chuyển vào thư mục

cd "Speech2Text Services"### 🎨 Stable Diffusion WebUI



# Chạy script cài đặt dependencies> **Based on [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui)**  

.\scripts\fix_dependencies.bat

> *Customized configuration for optimized performance*> **Based on [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui)**  

# Cấu hình HuggingFace token (optional, cho diarization)

# Tạo file .env và thêm HF_TOKEN> *Customized configuration for optimized performance*



# Khởi động Web UI- ✅ **Text-to-Image**: Tạo ảnh từ text prompts

.\start_webui.bat

# → http://localhost:7860- ✅ **Image-to-Image**: Transform và edit images- ✅ **Text-to-Image**: Tạo ảnh từ text prompts

```

- ✅ **LoRA + VAE**: Fine-tuned models support- ✅ **Image-to-Image**: Transform và chỉnh sửa ảnh

**Chi tiết:** [Speech2Text Setup Guide →](Speech2Text%20Services/SETUP_FINAL.md)

- ✅ **ControlNet**: Precise generation control- ✅ **LoRA + VAE**: Fine-tuned models support

---

- ✅ **API Enabled**: RESTful API, tích hợp sẵn với ChatBot- ✅ **ControlNet**: Precise generation control

### 4️⃣ Stable Diffusion

- ✅ **GPU Optimized**: CUDA 12.1, xformers support- ✅ **API Enabled**: RESTful API, tích hợp với ChatBot

```bash

# Di chuyển vào thư mục- ✅ **GPU Optimized**: CUDA 12.1, xformers support

cd stable-diffusion-webui

👉 **[Chi tiết →](stable-diffusion-webui/README.md)** | 🚀 **Port**: 7861 | 🔗 **[Original Project](https://github.com/AUTOMATIC1111/stable-diffusion-webui)**

# Khởi động WebUI với API enabled

.\webui.bat👉 **[Chi tiết đầy đủ →](stable-diffusion-webui/README.md)**  

# → http://localhost:7861

```---🔗 **[Original Project →](https://github.com/AUTOMATIC1111/stable-diffusion-webui)**



**Chi tiết:** [SD WebUI Setup Guide →](stable-diffusion-webui/README.md)



---## 🚀 Quick Start---



## 🗂️ Cấu Trúc Dự Án



```### 1️⃣ Text2SQL (Khuyến nghị - Dễ nhất!)## 🚀 Quick Start

AI-Assistant/

│

├── 📁 config/                    # Configuration management

│   ├── model_config.py          # Service configurations```bash

│   └── logging_config.py        # Logging setup

│# Di chuyển vào thư mục

├── 📁 src/                       # Hub Gateway source code

│   ├── hub.py                   # Main applicationcd "Text2SQL Services"### 1️⃣ Text2SQL (Khuyến nghị - Dễ nhất!)

│   ├── handlers/                # Request handlers

│   └── utils/                   # Utilities (cache, rate limiter)

│

├── 📁 data/                      # Data storage# Tạo virtual environment```bash

│   ├── cache/                   # Response cache

│   ├── prompts/                 # Prompt templatespython -m venv Text2SQLcd "Text2SQL Services"

│   └── outputs/                 # Output files

│.\Text2SQL\Scripts\activatepython -m venv Text2SQL

├── 📁 ChatBot/                   # 🤖 Multi-model AI Chatbot

│   ├── app.py                   # Main application.\Text2SQL\Scripts\activate

│   ├── README.md                # Documentation

│   ├── templates/               # HTML templates# Cài đặt dependenciespip install -r requirements.txt

│   ├── static/                  # CSS, JS, images

│   ├── models/                  # Local Qwen modelspip install -r requirements.txt

│   └── Storage/                 # Generated images

│# Tạo file .env và thêm GEMINI_API_KEY_1

├── 📁 Text2SQL Services/        # 📊 SQL Generator ⭐

│   ├── app_simple.py            # Main application# Cấu hình API keycp .env.example .env

│   ├── data/                    # Schemas, knowledge base

│   │   ├── knowledge_base/      # AI learned SQLcp .env.example .env

│   │   └── sample_schemas/      # Example schemas

│   └── README.md                # Documentation# Chỉnh sửa .env và thêm GEMINI_API_KEY_1# Khởi động

│

├── 📁 Speech2Text Services/     # 🎤 Voice Transcriptionpython app_simple.py

│   ├── app/web_ui.py            # Web interface

│   ├── README.md                # Documentation# Khởi động service# → http://localhost:5002

│   └── SETUP_FINAL.md           # Setup guide

│python app_simple.py```

├── 📁 stable-diffusion-webui/   # 🎨 Image Generation (AUTOMATIC1111)

│   ├── webui.bat                # Windows launcher

│   ├── README.md                # Documentation

│   └── models/                  # SD models# Truy cập: http://localhost:5002**Chi tiết:** [Text2SQL Setup Guide →](Text2SQL%20Services/README.md#-quick-start)

│

├── 📁 docs/                      # Comprehensive documentation```

│   ├── README.md                # Documentation hub

│   ├── PROJECT_STRUCTURE.md     # Architecture details---

│   ├── QUICK_REFERENCE.md       # Command cheat sheet

│   └── guides/                  # Setup & usage guides📖 **[Setup Guide chi tiết →](Text2SQL%20Services/README.md#-quick-start)**

│

├── 📁 scripts/                   # Automation scripts### 2️⃣ ChatBot

│   ├── startup/                 # Service startup scripts

│   └── stable-diffusion/        # SD specific scripts---

│

├── 📁 examples/                  # Usage examples```bash

│   ├── basic_completion.py      # Simple examples

│   └── chain_prompts.py         # Advanced examples### 2️⃣ ChatBotcd ChatBot

│

├── hub.py                        # Hub Gateway entry pointpython -m venv venv_chatbot

├── setup.py                      # Package setup

├── requirements.txt              # Hub dependencies```bash.\venv_chatbot\Scripts\activate

├── Dockerfile                    # Docker configuration

├── .env.example                  # Environment variables template# Di chuyển vào thư mụcpip install -r requirements.txt

└── README.md                     # This file

```cd ChatBot



---# Tạo file .env và thêm API keys



## 🛠️ Yêu Cầu Hệ Thống# Tạo virtual environmentcp .env.example .env



### Tối Thiểupython -m venv venv_chatbot



- **Python**: 3.10.6 hoặc cao hơn.\venv_chatbot\Scripts\activate# Khởi động

- **RAM**: 8GB

- **Storage**: 15GB cho models và cachepython app.py

- **OS**: Windows 10/11, Linux, macOS

# Cài đặt dependencies# → http://localhost:5001

### Khuyến Nghị

pip install -r requirements.txt```

- **Python**: 3.10.11

- **RAM**: 16GB+

- **GPU**: NVIDIA với 6GB+ VRAM (cho Stable Diffusion và local models)

- **CUDA**: 11.8 hoặc 12.1# Cấu hình API keys**Chi tiết:** [ChatBot Setup Guide →](ChatBot/README.md)

- **Storage**: 20GB+ SSD

cp .env.example .env

### Compatibility

# Chỉnh sửa .env và thêm OPENAI_API_KEY, GEMINI_API_KEY---

| Service | CPU Only | GPU Boost | VRAM Required |

|---------|----------|-----------|---------------|

| ChatBot (API only) | ✅ Yes | ❌ No | 0GB |

| ChatBot (with Qwen) | 🐌 Slow | ✅ Yes | 4GB+ |# Khởi động service### 3️⃣ Speech2Text

| Text2SQL | ✅ Yes | ❌ No | 0GB |

| Speech2Text | ✅ Yes | ✅ Yes | 6GB+ |python app.py

| Stable Diffusion | ❌ No | ✅ Required | 6GB+ |

```bash

---

# Truy cập: http://localhost:5001cd "Speech2Text Services"

## 🔑 API Keys

```# Chạy script cài đặt dependencies

### Bắt Buộc (chọn ít nhất 1)

.\scripts\fix_dependencies.bat

- **Gemini API** (FREE): https://makersuite.google.com/app/apikey

  - Dùng cho: Text2SQL, ChatBot📖 **[Setup Guide chi tiết →](ChatBot/README.md#-quick-start)**

  - Free tier: 60 requests/minute

# Khởi động Web UI

### Tùy Chọn

---.\start_webui.bat

- **OpenAI API**: https://platform.openai.com/api-keys

  - Dùng cho: ChatBot GPT-4, Whisper# → http://localhost:7860

  - Cost: Pay-as-you-go

### 3️⃣ Speech2Text```

- **HuggingFace Token** (FREE): https://huggingface.co/settings/tokens

  - Dùng cho: Speech2Text diarization, Local models

  - Free tier: Unlimited

```bash**Chi tiết:** [Speech2Text Setup Guide →](Speech2Text%20Services/SETUP_FINAL.md)

- **DeepSeek API**: https://platform.deepseek.com/api-keys

  - Dùng cho: ChatBot DeepSeek models# Di chuyển vào thư mục

  - Cost: ~$0.14/1M tokens

cd "Speech2Text Services"---

---



## 📚 Tài Liệu

# Chạy script cài đặt (tự động xử lý dependencies)### 4️⃣ Stable Diffusion

### 📖 Service Documentation

.\scripts\fix_dependencies.bat

| Service | Main Docs | Setup Guide | Features |

|---------|-----------|-------------|----------|```bash

| **ChatBot** | [README](ChatBot/README.md) | [Setup](ChatBot/README.md#-quick-start) | [Docs →](ChatBot/docs/) |

| **Text2SQL** | [README](Text2SQL%20Services/README.md) | [Setup](Text2SQL%20Services/README.md#-quick-start) | [AI Learning →](Text2SQL%20Services/README.md) |# Cấu hình HuggingFace token (optional, cho diarization)cd stable-diffusion-webui

| **Speech2Text** | [README](Speech2Text%20Services/README.md) | [Setup](Speech2Text%20Services/SETUP_FINAL.md) | [WebUI →](Speech2Text%20Services/README.md) |

| **Stable Diffusion** | [README](stable-diffusion-webui/README.md) | [Setup](stable-diffusion-webui/README.md) | [Original →](https://github.com/AUTOMATIC1111/stable-diffusion-webui) |# Tạo file .env và thêm HF_TOKEN# Khởi động với API enabled



### 🔍 Feature Guides.\webui.bat



- **Text2SQL v2.0 Features**: [Text2SQL Services/README.md](Text2SQL%20Services/README.md)# Khởi động Web UI# → http://localhost:7861

- **ChatBot Tools Integration**: [ChatBot/README.md](ChatBot/README.md)

- **Local Models Setup**: [ChatBot/README.md](ChatBot/README.md).\start_webui.bat```



---



## 🚀 Deployment# Truy cập: http://localhost:7860**Chi tiết:** [SD WebUI Setup Guide →](stable-diffusion-webui/README.md)



### 🌟 Text2SQL - Ready for Production!```



**Platform:** Render.com (FREE)  ---

**Build Time:** 3-5 minutes  

**Status:** ✅ Ready to deploy📖 **[Setup Guide chi tiết →](Speech2Text%20Services/SETUP_FINAL.md)**



```bash## 🗂️ Cấu Trúc Dự Án

# Quick deploy guide

cd "Text2SQL Services"---

git init && git add . && git commit -m "Deploy"

git push origin main```

```

### 4️⃣ Stable DiffusionAI-Assistant/

👉 **[Chi tiết deployment →](Text2SQL%20Services/README.md#-deployment)**

│

---

```bash├── 📁 config/                    # Configuration management

## 🤝 Contributing

# Di chuyển vào thư mục│   ├── model_config.py          # Service configurations

Contributions are welcome! Please:

cd stable-diffusion-webui│   └── logging_config.py        # Logging setup

1. Fork the repository

2. Create a feature branch (`git checkout -b feature/AmazingFeature`)│

3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)

4. Push to the branch (`git push origin feature/AmazingFeature`)# Khởi động WebUI với API enabled├── 📁 src/                       # Hub Gateway source code

5. Open a Pull Request

.\webui.bat│   ├── hub.py                   # Main application

---

│   ├── handlers/                # Request handlers

## 📝 License

# Hoặc với các flags tùy chỉnh:│   └── utils/                   # Utilities (cache, rate limiter)

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

python launch.py --api --xformers│

---

├── 📁 data/                      # Data storage

## 🙏 Acknowledgments

# Truy cập: http://localhost:7861│   ├── cache/                   # Response cache

- [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) - Stable Diffusion WebUI

- [Google Gemini](https://ai.google.dev/) - AI API```│   ├── prompts/                 # Prompt templates

- [OpenAI](https://openai.com/) - GPT models

- [HuggingFace](https://huggingface.co/) - Model hub│   └── outputs/                 # Output files

- [pyannote.audio](https://github.com/pyannote/pyannote-audio) - Speaker diarization

📖 **[Setup Guide chi tiết →](stable-diffusion-webui/README.md)**│

---

├── 📁 ChatBot/                   # 🤖 Multi-model AI Chatbot

<div align="center">

---│   ├── app.py                   # Main application

**Made with ❤️ by SkastVnT**

│   ├── README.md                # Documentation

⭐ Star this repo if you find it helpful!

## 🗂️ Cấu Trúc Dự Án│   ├── templates/               # HTML templates

</div>

│   ├── static/                  # CSS, JS, images

```│   ├── models/                  # Local Qwen models

AI-Assistant/│   └── Storage/                 # Generated images

││

├── 📁 config/                     # Configuration management├── 📁 Text2SQL Services/        # 📊 SQL Generator ⭐

│   ├── model_config.py           # Service configurations│   ├── app_simple.py            # Main application

│   └── logging_config.py         # Logging setup│   ├── data/                    # Schemas, knowledge base

│

├── 📁 src/                        # Hub Gateway source code│   ├── README.md                 # 📖 Documentation

│   ├── hub.py                    # Main hub application

│   ├── handlers/                 # Request handlers│   ├── data/knowledge_base/      # AI learned SQL

│   └── utils/                    # Utilities (cache, rate limiter)

││   └── sample_schemas/           # Example schemas## 🚀 Quick Start**AI-Assistant** là nền tảng AI tích hợp gồm 4 dịch vụ độc lập:

├── 📁 data/                       # Data storage

│   ├── cache/                    # Response cache│

│   ├── prompts/                  # Prompt templates

│   └── outputs/                  # Output files├── 📁 Speech2Text Services/      # 🎤 Voice Transcription

│

├── 📁 docs/                       # Comprehensive documentation│   ├── app/web_ui.py             # Web interface

│   ├── README.md                 # Documentation hub

│   ├── PROJECT_STRUCTURE.md      # Architecture details│   ├── README.md                 # 📖 Documentation### 1️⃣ Text2SQL (Khuyên dùng - Dễ nhất!)---

│   ├── QUICK_REFERENCE.md        # Command cheat sheet

│   └── guides/                   # Setup & usage guides│   └── SETUP_FINAL.md            # Setup guide

│

├── 📁 ChatBot/                    # 🤖 Multi-model AI Chatbot│

│   ├── app.py                    # Flask application

│   ├── templates/                # HTML templates├── 📁 stable-diffusion-webui/    # 🎨 Image Generation (AUTOMATIC1111)

│   ├── static/                   # CSS, JS, assets

│   ├── models/                   # Local Qwen models│   ├── webui.bat                 # Windows launcher```bash![Python](https://img.shields.io/badge/Python-3.10.6-blue?style=for-the-badge&logo=python)![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)

│   ├── Storage/                  # Generated images

│   └── README.md                 # Service documentation│   ├── README.md                 # 📖 Documentation

│

├── 📁 Text2SQL Services/         # 📊 SQL Generator ⭐│   └── models/                   # SD modelscd "Text2SQL Services"

│   ├── app_simple.py             # Flask application

│   ├── data/                     # Schemas, knowledge base│

│   ├── templates/                # HTML templates

│   ├── static/                   # CSS, JS, assets└── README.md                     # 📄 This filepython -m venv Text2SQL### 📊 Text2SQL Service ⭐ **MỚI NHẤT v2.0**

│   └── README.md                 # Service documentation

│```

├── 📁 Speech2Text Services/      # 🎤 Voice Transcription

│   ├── app/web_ui.py             # Web interface.\Text2SQL\Scripts\activate

│   ├── src/                      # Core processing code

│   ├── data/                     # Audio files, outputs---

│   ├── scripts/                  # Setup & utility scripts

│   └── README.md                 # Service documentationpip install -r requirements.txt- **NL to SQL**: Chuyển tiếng Việt/English → SQL### 1. 🤖 **ChatBot Service**

│

├── 📁 stable-diffusion-webui/    # 🎨 Image Generation## 📚 Documentation

│   ├── webui.py                  # Main application

│   ├── webui.bat                 # Windows launchercp .env.example .env  # Thêm GEMINI_API_KEY_1

│   ├── modules/                  # Core modules

│   ├── models/                   # SD checkpoints, LoRA, VAE### 📖 Service Documentation

│   └── README.md                 # Service documentation

│python app_simple.py- **Multi-DB**: ClickHouse, MongoDB, PostgreSQL, MySQL, SQL Server

├── 📁 scripts/                    # Automation scripts

│   ├── startup/                  # Service startup scripts| Service | Main Docs | Setup Guide | Features |

│   └── stable-diffusion/         # SD specific scripts

│|---------|-----------|-------------|----------|# → http://localhost:5002

├── 📁 examples/                   # Usage examples

│   ├── basic_completion.py       # Simple examples| **ChatBot** | [README](ChatBot/README.md) | [Setup](ChatBot/README.md#-quick-start) | [Docs →](ChatBot/docs/) |

│   └── chain_prompts.py          # Advanced examples

│| **Text2SQL** | [README](Text2SQL%20Services/README.md) | [Setup](Text2SQL%20Services/SETUP_COMPLETE.md) | [AI Learning →](Text2SQL%20Services/AI_LEARNING_GUIDE.md) |```- **AI Learning**: Lưu SQL đúng vào Knowledge Base**Multi-Model Conversational AI với Local LLM & Image Generation**[Quick Start](#-quick-start) • [Services](#-services) • [Installation](#%EF%B8%8F-installation) • [Documentation](#-documentation)

├── hub.py                         # Hub Gateway entry point

├── setup.py                       # Package setup| **Speech2Text** | [README](Speech2Text%20Services/README.md) | [Setup](Speech2Text%20Services/SETUP_FINAL.md) | [WebUI →](Speech2Text%20Services/WEBUI_SETUP_COMPLETE.md) |

├── requirements.txt               # Hub dependencies

├── Dockerfile                     # Docker configuration| **Stable Diffusion** | [README](stable-diffusion-webui/README.md) | [Setup](stable-diffusion-webui/README.md) | [Original →](https://github.com/AUTOMATIC1111/stable-diffusion-webui) |

├── .env.example                   # Environment variables template

└── README.md                      # This file

```

### 🎯 Hướng Dẫn Nhanh**Chi tiết:** [Text2SQL Setup Guide →](Text2SQL%20Services/README.md#-quick-start)- **Question Gen**: Tự động tạo 5 câu hỏi từ schema

---



## 🛠️ Yêu Cầu Hệ Thống

- **Text2SQL v2.0 Features**: [FEATURES_COMPLETE.md](Text2SQL%20Services/FEATURES_COMPLETE.md)

### Tối Thiểu

- **AI Learning Guide**: [AI_LEARNING_GUIDE.md](Text2SQL%20Services/AI_LEARNING_GUIDE.md)

- **Python**: 3.10.6 hoặc cao hơn

- **RAM**: 8GB- **ChatBot Tools Integration**: [TOOLS_INTEGRATION_GUIDE.md](ChatBot/docs/TOOLS_INTEGRATION_GUIDE.md)---- **DB Connection**: Kết nối trực tiếp database

- **Storage**: 15GB cho models và cache

- **OS**: Windows 10/11, Linux, macOS- **Local Models Setup**: [LOCAL_MODELS_GUIDE.md](ChatBot/docs/LOCAL_MODELS_GUIDE.md)



### Khuyến Nghị



- **Python**: 3.10.11---

- **RAM**: 16GB+

- **GPU**: NVIDIA với 6GB+ VRAM (cho Stable Diffusion và local models)### 2️⃣ ChatBot- **Ready to Deploy**: Render.com FREE hosting

- **CUDA**: 11.8 hoặc 12.1

- **Storage**: 20GB+ SSD## 🚀 Deployment



### Compatibility



| Service | CPU Only | GPU Boost | VRAM Required |### 🌟 Text2SQL - Ready for Production!

|---------|----------|-----------|---------------|

| ChatBot (API only) | ✅ Yes | ❌ No | 0GB |```bash- ✅ **Multi-Model AI**: Gemini 2.0, GPT-4, DeepSeek, Qwen 1.5B (local), BloomVN![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)

| ChatBot (with Qwen) | 🐌 Slow | ✅ Yes | 4GB+ |

| Text2SQL | ✅ Yes | ❌ No | 0GB |**Platform:** Render.com (FREE)  

| Speech2Text | ✅ Yes | ✅ Yes | 6GB+ |

| Stable Diffusion | ❌ No | ✅ Required | 6GB+ |**Build Time:** 3-5 minutes  cd ChatBot



---**Status:** ✅ Ready to deploy



## 🔑 API Keyspython -m venv venv_chatbot👉 **[Chi tiết đầy đủ →](Text2SQL%20Services/README.md)**  



### Bắt Buộc (chọn ít nhất 1)```bash



- **Gemini API** (FREE): https://makersuite.google.com/app/apikey# Quick deploy guide.\venv_chatbot\Scripts\activate

  - Dùng cho: Text2SQL, ChatBot

  - Free tier: 60 requests/minutecd "Text2SQL Services"



### Tùy Chọngit init && git add . && git commit -m "Deploy"pip install -r requirements.txt🚀 **[Deployment Guide →](Text2SQL%20Services/README.md#-deployment)**- ✅ **Image Generation**: Stable Diffusion (txt2img, img2img, LoRA, VAE)



- **OpenAI API**: https://platform.openai.com/api-keysgit push origin main

  - Dùng cho: ChatBot GPT-4, Whisper

  - Pay-as-you-go# → Deploy on Render.com with 1-clickcp .env.example .env  # Thêm API keys



- **DeepSeek API**: https://platform.deepseek.com```

  - Dùng cho: ChatBot (cost-effective alternative)

  - Rẻ nhất trong các optionspython app.py



- **HuggingFace Token** (FREE): https://huggingface.co/settings/tokens**Chi tiết đầy đủ:** [Deployment Guide →](Text2SQL%20Services/README.md#-deployment)

  - Dùng cho: Speech2Text diarization

  - Cần accept license tại model page# → http://localhost:5001



### Cấu Hình### 📊 Service Comparison



Tạo file `.env` trong thư mục root và mỗi service:```---- ✅ **AI Memory System**: Lưu trữ conversations với hình ảnh</div>



```env| Service | Size | Free Hosting | Deploy Difficulty | Best For |

# API Keys

GEMINI_API_KEY_1=your_gemini_key_here|---------|------|--------------|-------------------|----------|

OPENAI_API_KEY=your_openai_key_here

DEEPSEEK_API_KEY=your_deepseek_key_here| **Text2SQL** ✅ | 251MB | ✅ Yes (Render) | ⭐ Easy | Production |

HF_TOKEN=your_huggingface_token_here

| **ChatBot (API)** | 200MB | ✅ Yes (Railway) | ⭐⭐ Medium | Demo |**Chi tiết:** [ChatBot Setup Guide →](ChatBot/README.md)

# Service Ports (optional)

CHATBOT_PORT=5001| **ChatBot (Full)** | 4.1GB | ❌ No | ⭐⭐⭐ Hard | Local only |

TEXT2SQL_PORT=5002

SPEECH2TEXT_PORT=7860| **Speech2Text** | 2GB | ❌ No | ⭐⭐⭐ Hard | Local only |

SD_PORT=7861

```| **Stable Diffusion** | 10GB+ | ❌ No | ⭐⭐⭐⭐ Very Hard | Local only |



------### 🎤 Speech2Text Service- ✅ **Message Editing**: Sửa và tạo lại responses



## 💡 Use Cases---



### 📊 Text2SQL

- Business Intelligence dashboards

- Data analysis automation## 🔧 Configuration

- SQL learning platform

- Database query assistant### 3️⃣ Speech2Text- **Dual Engine**: PhoWhisper + Whisper

- Natural language data exploration

### 📌 API Keys Required

### 🤖 ChatBot

- Customer support automation

- Personal AI assistant

- Code helper & debugging```bash

- Image generation chatbot

- Multi-language conversations# Required (ít nhất 1):```bash- **Vietnamese Optimized**: Tối ưu cho tiếng Việt- ✅ **PDF Export**: Xuất conversations kèm hình ảnh![CUDA](https://img.shields.io/badge/CUDA-11.8-green?style=for-the-badge&logo=nvidia)![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)



### 🎤 Speech2TextGEMINI_API_KEY_1=your_key         # FREE at makersuite.google.com

- Meeting transcriptions

- Podcast transcriptionsOPENAI_API_KEY=your_key            # Optionalcd "Speech2Text Services"

- Voice memos to text

- Call center analyticsDEEPSEEK_API_KEY=your_key          # Optional (cheapest)

- Interview documentation

# Follow detailed setup guide- **Speaker Diarization**: Phân tách người nói

### 🎨 Stable Diffusion

- Marketing materials creation# Optional (for ChatBot tools):

- Social media content

- Product mockupsGOOGLE_SEARCH_API_KEY_1=your_key```

- Creative artwork

- Character designGOOGLE_CSE_ID=your_id



---GITHUB_TOKEN=your_token- **Smart Fusion**: Qwen2.5-1.5B LLM enhancement- ✅ **Modern UI**: Responsive design với dark mode



## 📊 Deployment Options```



### Text2SQL - Production Ready**Chi tiết:** [Speech2Text Setup Guide →](Speech2Text%20Services/SETUP_FINAL.md)



| Platform | Cost | Difficulty | Best For |### 🔗 Get API Keys

|----------|------|------------|----------|

| **Render.com** | FREE | ⭐ Easy | Production deployment |- **Web UI**: Giao diện thân thiện

| **Railway.app** | FREE tier | ⭐⭐ Medium | Quick demos |

| **Heroku** | Paid | ⭐⭐ Medium | Enterprise |- **Gemini** (FREE): https://makersuite.google.com/app/apikey

| **Docker** | Self-host | ⭐⭐ Medium | Full control |

- **OpenAI**: https://platform.openai.com/api-keys---

📖 **[Deployment Guide chi tiết →](Text2SQL%20Services/README.md#-deployment)**

- **DeepSeek**: https://platform.deepseek.com

### ChatBot

- **Hugging Face**: https://huggingface.co/settings/tokens- ✅ **Tools Integration**: Google Search, GitHub Search---

- **API-only version** (200MB): Railway.app, Render.com

- **Full version with Qwen** (4GB): Local only hoặc dedicated server



### Speech2Text & Stable Diffusion---### 4️⃣ Stable Diffusion



- **Local deployment** only (require GPU)

- Docker support available

- Cloud GPU instances (expensive)## 💡 Use Cases👉 **[Chi tiết đầy đủ →](Speech2Text%20Services/README.md)**



---



## 🧪 Testing### 📊 Text2SQL```bash



Mỗi service đã bao gồm test scripts:- ✅ Business Intelligence dashboards



```bash- ✅ Data analysis automationcd stable-diffusion-webui

# Test Text2SQL

cd "Text2SQL Services"- ✅ SQL learning platform

python test.py

- ✅ Database query assistant.\webui.bat

# Test ChatBot Gemini integration

cd ChatBot

python test_gemini.py

### 🤖 ChatBot# → http://localhost:7861---

# Test Speech2Text system

cd "Speech2Text Services"- ✅ Customer support

.\test_system.bat

- ✅ Personal assistant```

# Test Stable Diffusion API

cd stable-diffusion-webui- ✅ Code helper (Programming mode)

python test_sd_api.py

```- ✅ Image generation chatbot📁 **Location**: [`ChatBot/`](ChatBot/)  



---



## 📚 Tài Liệu### 🎤 Speech2Text**Chi tiết:** [SD WebUI Setup Guide →](stable-diffusion-webui/README.md)



### 📖 Documentation Hub- ✅ Meeting transcription



- **[Documentation Index](docs/README.md)** - Trung tâm tài liệu- ✅ Podcast transcription### 🎨 Stable Diffusion WebUI

- **[Quick Reference](docs/QUICK_REFERENCE.md)** - Commands cheat sheet

- **[Project Structure](docs/PROJECT_STRUCTURE.md)** - Kiến trúc chi tiết- ✅ Voice memos to text

- **[Getting Started](docs/GETTING_STARTED.md)** - Hướng dẫn bắt đầu

- ✅ Call center analytics---

### 🔧 Setup Guides



- **[ChatBot Setup](ChatBot/README.md)** - ChatBot installation guide

- **[Text2SQL Setup](Text2SQL%20Services/SETUP_COMPLETE.md)** - Text2SQL setup### 🎨 Stable Diffusion- **Text-to-Image**: Tạo ảnh từ text🚀 **Port**: 5001  

- **[Speech2Text Setup](Speech2Text%20Services/SETUP_FINAL.md)** - Speech2Text setup

- **[SD WebUI Setup](stable-diffusion-webui/README.md)** - Stable Diffusion setup- ✅ Marketing materials



### 📘 Feature Guides- ✅ Social media content## 🗂️ Cấu Trúc Dự Án



- **[AI Learning Guide](Text2SQL%20Services/AI_LEARNING_GUIDE.md)** - Text2SQL AI learning- ✅ Product mockups

- **[Image Generation Guide](docs/guides/IMAGE_GENERATION_GUIDE.md)** - SD integration

- **[Memory System](ChatBot/docs/)** - ChatBot memory features- ✅ Creative projects- **Image-to-Image**: Chỉnh sửa ảnh



### 🐛 Troubleshooting



- **[ChatBot Issues](ChatBot/REFACTORING_COMPLETE.md)** - Common ChatBot problems---```

- **[Text2SQL Issues](Text2SQL%20Services/README.md#-troubleshooting)** - Text2SQL fixes

- **[Speech2Text Issues](Speech2Text%20Services/WEBUI_SETUP_COMPLETE.md)** - Speech2Text fixes

- **[SD WebUI Issues](stable-diffusion-webui/TROUBLESHOOTING_SD.md)** - SD troubleshooting

## 🤝 ContributingAI-Assistant/- **LoRA + VAE**: Fine-tuned models📖 **Docs**: [ChatBot README](ChatBot/README.md)## 📋 Overview

---



## 🤝 Contributing

Contributions welcome! Mỗi service có guide riêng:│

Contributions welcome! Vui lòng:



1. Fork repository

2. Tạo feature branch: `git checkout -b feature/AmazingFeature`- **ChatBot**: [Contributing Guide →](ChatBot/README.md#-contributing)├── 📁 ChatBot/                    # 🤖 Multi-model AI Chatbot- **ControlNet**: Precise control

3. Commit changes: `git commit -m 'Add AmazingFeature'`

4. Push to branch: `git push origin feature/AmazingFeature`- **Text2SQL**: [Contributing Guide →](Text2SQL%20Services/README.md#-contributing)

5. Open Pull Request

- **Speech2Text**: [Contributing Guide →](Speech2Text%20Services/README.md)│   ├── app.py                    # Main application

### Development Guidelines

- **Stable Diffusion**: Follow [AUTOMATIC1111 guidelines](https://github.com/AUTOMATIC1111/stable-diffusion-webui#contributing)

- Follow existing code style

- Add tests for new features│   ├── README.md                 # 📖 Documentation- **API Ready**: RESTful API

- Update documentation

- Test thoroughly before PR---



Mỗi service có contributing guidelines riêng:│   ├── models/                   # Local Qwen models

- **[ChatBot Contributing](ChatBot/README.md#-contributing)**

- **[Text2SQL Contributing](Text2SQL%20Services/README.md#-contributing)**## 🐛 Troubleshooting

- **[Stable Diffusion Guidelines](https://github.com/AUTOMATIC1111/stable-diffusion-webui#contributing)**

│   └── Storage/                  # Generated images

---

### Common Issues

## 🐛 Common Issues & Solutions

│

### Port Already in Use

**Port already in use:**

```bash

# Windows```bash├── 📁 Text2SQL Services/         # 📊 SQL Generator ⭐👉 **[Chi tiết đầy đủ →](stable-diffusion-webui/README.md)**---**Unified AI Platform with Multiple Services****Nền tảng tích hợp đa dịch vụ AI mạnh mẽ**

netstat -ano | findstr :5002

taskkill /PID <PID> /Fnetstat -ano | findstr :5002



# Linux/Mactaskkill /PID <PID> /F│   ├── app_simple.py             # Main application

lsof -i :5002

kill -9 <PID>```

```

│   ├── README.md                 # 📖 Documentation

### Module Not Found

**Module not found:**

```bash

# Reinstall dependencies```bash│   ├── data/knowledge_base/      # AI learned SQL

pip install -r requirements.txt --upgrade

pip install -r requirements.txt --upgrade

# Check virtual environment is activated

.\venv\Scripts\activate  # Windows```│   └── sample_schemas/           # Example schemas---

source venv/bin/activate  # Linux/Mac

```



### API Key Errors**API Key errors:**│



- Verify `.env` file exists in correct directory- Check `.env` file exists

- Check API key format is correct

- Test API key validity at provider's website- Verify API key is valid├── 📁 Speech2Text Services/      # 🎤 Voice Transcription

- Restart service after updating `.env`

- Restart application

### GPU Not Detected

│   ├── app/web_ui.py             # Web interface

```bash

# Check CUDA installation**Chi tiết cho từng service:**

nvidia-smi

- ChatBot: [Troubleshooting →](ChatBot/docs/TROUBLESHOOTING.md)│   ├── README.md                 # 📖 Documentation## 🚀 Quick Start### 2. 📊 **Text2SQL Service** ⭐ **NEWEST!****AI-Assistant** is a comprehensive AI platform integrating four powerful services:

# Reinstall PyTorch with CUDA

pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121- Text2SQL: [Troubleshooting →](Text2SQL%20Services/README.md#-troubleshooting)

```

- Speech2Text: [Setup Guide →](Speech2Text%20Services/SETUP_FINAL.md)│   └── SETUP_FINAL.md            # Setup guide

**Xem thêm:** Mỗi service có troubleshooting guide chi tiết trong README của service đó.



---

---│

## 📊 Project Statistics



- **Total Lines of Code**: 10,000+

- **Services**: 4 major services## 📄 License├── 📁 stable-diffusion-webui/    # 🎨 Image Generation

- **Documentation Files**: 20+

- **Supported Languages**: Vietnamese, English

- **AI Models Integrated**: 8+ models

- **Active Development**: ✅ YesMIT License - see [LICENSE](LICENSE) file for details│   ├── webui.bat                 # Windows launcher### 1️⃣ Text2SQL (Khuyên dùng - Dễ nhất!)**Natural Language to SQL Query Converter**



---



## 🙏 Acknowledgments---│   ├── README.md                 # 📖 Documentation



### AI Models & APIs



- **[Google Gemini](https://ai.google.dev/)** - Primary AI engine (FREE)## 🙏 Acknowledgments│   └── models/                   # SD models

- **[OpenAI](https://openai.com/)** - GPT-4 & Whisper models

- **[DeepSeek](https://www.deepseek.com/)** - Cost-effective AI alternative

- **[Alibaba Qwen](https://github.com/QwenLM/Qwen)** - Local LLM support

- **[Stability AI](https://stability.ai/)** - Stable Diffusion models### AI Models & APIs│



### Frameworks & Tools- **Google Gemini** - Primary AI engine



- **[Flask](https://flask.palletsprojects.com/)** - Web framework- **OpenAI** - GPT & Whisper models└── README.md                     # 📄 This file```bash

- **[Tailwind CSS](https://tailwindcss.com/)** - UI framework

- **[AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui)** - SD WebUI- **DeepSeek** - Cost-effective AI

- **[PyAnnote](https://github.com/pyannote/pyannote-audio)** - Speaker diarization

- **[Whisper](https://github.com/openai/whisper)** - Speech recognition- **Qwen (Alibaba)** - Local LLM```

- **[PhoWhisper](https://huggingface.co/vinai/PhoWhisper)** - Vietnamese ASR

- **Stability AI** - Image generation

### Special Thanks

cd "Text2SQL Services"

- OpenAI for Whisper và GPT models

- Google for Gemini API và generous free tier### Frameworks & Tools

- AUTOMATIC1111 for amazing SD WebUI

- VinAI for PhoWhisper Vietnamese model- **Flask** - Web framework---

- All contributors và open-source community

- **ClickHouse** - Database

---

- **MongoDB** - NoSQL databasepython -m venv Text2SQL#### 🆕 Version 2.0 Features:

## 📄 License

- **[AUTOMATIC1111](https://github.com/AUTOMATIC1111)** - Stable Diffusion WebUI

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

- **PyAnnote** - Speaker diarization## 📚 Documentation

### Third-Party Licenses



- Stable Diffusion WebUI: [AGPL-3.0](stable-diffusion-webui/LICENSE.txt)

- Individual services may have additional licenses (check service README)---.\Text2SQL\Scripts\activate



---



## 📞 Support & Contact## 📞 Support### 📖 Service Documentation



### 🐛 Issues & Bug Reports



- **GitHub Issues**: [Report a bug](https://github.com/SkastVnT/AI-Assistant/issues)- **Issues**: [GitHub Issues](https://github.com/SkastVnT/AI-Assistant/issues)pip install -r requirements.txt- ✅ **Natural Language to SQL**: Chuyển đổi tiếng Việt/English sang SQL1. 🤖 **ChatBot** - Multi-model conversational AI with local LLM and image generation

- Include: Service name, error message, steps to reproduce

- **Discussions**: [GitHub Discussions](https://github.com/SkastVnT/AI-Assistant/discussions)

### 💬 Discussions & Questions

| Service | Main Docs | Setup Guide | Features |

- **GitHub Discussions**: [Ask questions](https://github.com/SkastVnT/AI-Assistant/discussions)

- Community support và feature requests---



### 📧 Contact|---------|-----------|-------------|----------|cp .env.example .env  # Thêm GEMINI_API_KEY_1



- **Repository**: [github.com/SkastVnT/AI-Assistant](https://github.com/SkastVnT/AI-Assistant)## 📊 Stats

- **Owner**: SkastVnT

| **ChatBot** | [README](ChatBot/README.md) | [Setup](ChatBot/README.md#-quick-start) | [Docs →](ChatBot/docs/) |

---

![GitHub stars](https://img.shields.io/github/stars/SkastVnT/AI-Assistant?style=social)

## 🌟 Star History

![GitHub forks](https://img.shields.io/github/forks/SkastVnT/AI-Assistant?style=social)| **Text2SQL** | [README](Text2SQL%20Services/README.md) | [Setup](Text2SQL%20Services/SETUP_COMPLETE.md) | [AI Learning →](Text2SQL%20Services/AI_LEARNING_GUIDE.md) |python app_simple.py- ✅ **Multi-Database**: ClickHouse, MongoDB, PostgreSQL, MySQL, SQL Server

If you find this project useful, please consider giving it a ⭐!

![GitHub issues](https://img.shields.io/github/issues/SkastVnT/AI-Assistant)

[![Star History Chart](https://api.star-history.com/svg?repos=SkastVnT/AI-Assistant&type=Date)](https://star-history.com/#SkastVnT/AI-Assistant&Date)

| **Speech2Text** | [README](Speech2Text%20Services/README.md) | [Setup](Speech2Text%20Services/SETUP_FINAL.md) | [WebUI →](Speech2Text%20Services/WEBUI_SETUP_COMPLETE.md) |

---

---

<div align="center">

| **Stable Diffusion** | [README](stable-diffusion-webui/README.md) | [Setup](stable-diffusion-webui/README.md) | Built-in Help |# → http://localhost:5002

**Made with ❤️ by AI Assistant Team**

<div align="center">

**[⬆ Back to Top](#-ai-assistant---nền-tảng-tích-hợp-đa-dịch-vụ-ai)**



</div>

## 🌟 Featured: Text2SQL v2.0

### 🎯 Hướng Dẫn Nhanh```- ✅ **AI Question Generation**: Tự động tạo 5 câu hỏi mẫu từ schema2. 📊 **Text2SQL** - Natural language to SQL query conversion[Quick Start](#-quick-start) • [Services](#-services) • [Installation](#%EF%B8%8F-installation) • [Documentation](#-documentation)[Khởi động nhanh](#-khởi-động-nhanh) • [Tính năng](#-tính-năng) • [Cài đặt](#️-cài-đặt) • [Hướng dẫn](#-hướng-dẫn-sử-dụng) • [Đóng góp](#-đóng-góp)

**Production-ready SQL Generator với AI Learning**



[![Deploy](https://img.shields.io/badge/Deploy-Render.com-00979D?style=for-the-badge&logo=render)](Text2SQL%20Services/README.md#-deployment)

[![Docs](https://img.shields.io/badge/Docs-Read%20More-blue?style=for-the-badge)](Text2SQL%20Services/README.md)- **Text2SQL v2.0 Features**: [FEATURES_COMPLETE.md](Text2SQL%20Services/FEATURES_COMPLETE.md)

[![Demo](https://img.shields.io/badge/Demo-Try%20Now-green?style=for-the-badge)](http://localhost:5002)

- **AI Learning Guide**: [AI_LEARNING_GUIDE.md](Text2SQL%20Services/AI_LEARNING_GUIDE.md)

---

- **ChatBot Tools Integration**: [TOOLS_INTEGRATION_GUIDE.md](ChatBot/docs/TOOLS_INTEGRATION_GUIDE.md)**Chi tiết:** [Text2SQL Setup Guide →](Text2SQL%20Services/README.md#-quick-start)- ✅ **AI Learning System**: Lưu SQL queries đúng vào knowledge base

**Made with ❤️ in Vietnam**

- **Local Models Setup**: [LOCAL_MODELS_GUIDE.md](ChatBot/docs/LOCAL_MODELS_GUIDE.md)

⭐ **Star this repo if you find it helpful!** ⭐



[🔝 Back to Top](#-ai-assistant---nền-tảng-tích-hợp-đa-dịch-vụ-ai)

---

</div>

---- ✅ **Database Connection**: Kết nối trực tiếp với ClickHouse/MongoDB (localhost & Atlas)3. 🎤 **Speech2Text** - Vietnamese speech-to-text transcription

## 🚀 Deployment



### 🌟 Text2SQL - Ready for Production!

### 2️⃣ ChatBot- ✅ **Schema Upload**: Hỗ trợ .txt, .sql, .json, .jsonl

**Platform:** Render.com (FREE)  

**Build Time:** 3-5 minutes  

**Status:** ✅ Ready to deploy

```bash- ✅ **Deep Thinking Mode**: Reasoning nâng cao cho queries phức tạp4. 🎨 **Stable Diffusion WebUI** - Advanced AI image generation

```bash

# Quick deploy guidecd ChatBot

cd "Text2SQL Services"

git init && git add . && git commit -m "Deploy"python -m venv venv_chatbot- ✅ **Knowledge Base Manager**: Quản lý SQL đã học

git push origin main

# → Deploy on Render.com with 1-click.\venv_chatbot\Scripts\activate

```

pip install -r requirements.txt

**Chi tiết đầy đủ:** [Deployment Guide →](Text2SQL%20Services/README.md#-deployment)

cp .env.example .env  # Thêm API keys

### 📊 Service Comparison

python app.py📁 **Location**: [`Text2SQL Services/`](Text2SQL%20Services/)  

| Service | Size | Free Hosting | Deploy Difficulty | Best For |

|---------|------|--------------|-------------------|----------|# → http://localhost:5001

| **Text2SQL** ✅ | 251MB | ✅ Yes (Render) | ⭐ Easy | Production |

| **ChatBot (API)** | 200MB | ✅ Yes (Railway) | ⭐⭐ Medium | Demo |```🚀 **Port**: 5002  Each service operates independently with its own virtual environment, making deployment and maintenance simple and modular.</div></div>

| **ChatBot (Full)** | 4.1GB | ❌ No | ⭐⭐⭐ Hard | Local only |

| **Speech2Text** | 2GB | ❌ No | ⭐⭐⭐ Hard | Local only |

| **Stable Diffusion** | 10GB+ | ❌ No | ⭐⭐⭐⭐ Very Hard | Local only |

**Chi tiết:** [ChatBot Setup Guide →](ChatBot/README.md)📖 **Docs**: [Text2SQL README](Text2SQL%20Services/README.md)  

---



## 🔧 Configuration

---🌟 **Status**: ✅ **Production Ready - Deploy to Render.com FREE!**

### 📌 API Keys Required



```bash

# Required (ít nhất 1):### 3️⃣ Speech2Text

GEMINI_API_KEY_1=your_key         # FREE at makersuite.google.com

OPENAI_API_KEY=your_key            # Optional

DEEPSEEK_API_KEY=your_key          # Optional (cheapest)

```bash------

# Optional (for ChatBot tools):

GOOGLE_SEARCH_API_KEY_1=your_keycd "Speech2Text Services"

GOOGLE_CSE_ID=your_id

GITHUB_TOKEN=your_token# Follow detailed setup guide

```

```

### 🔗 Get API Keys

### 3. 🎤 **Speech2Text Service**

- **Gemini** (FREE): https://makersuite.google.com/app/apikey

- **OpenAI**: https://platform.openai.com/api-keys**Chi tiết:** [Speech2Text Setup Guide →](Speech2Text%20Services/SETUP_FINAL.md)

- **DeepSeek**: https://platform.deepseek.com

- **Hugging Face**: https://huggingface.co/settings/tokens**Vietnamese Speech-to-Text với Speaker Diarization**



------



## 💡 Use Cases## ✨ Features------



### 📊 Text2SQL### 4️⃣ Stable Diffusion

- ✅ Business Intelligence dashboards

- ✅ Data analysis automation- ✅ **PhoWhisper + Whisper**: Dual transcription tối ưu tiếng Việt

- ✅ SQL learning platform

- ✅ Database query assistant```bash



### 🤖 ChatBotcd stable-diffusion-webui- ✅ **Speaker Diarization**: Phân tách và nhận diện người nói

- ✅ Customer support

- ✅ Personal assistant.\webui.bat

- ✅ Code helper (Programming mode)

- ✅ Image generation chatbot# → http://localhost:7861- ✅ **Batch Processing**: Xử lý nhiều file audio



### 🎤 Speech2Text```

- ✅ Meeting transcription

- ✅ Podcast transcription- ✅ **WebUI**: Giao diện web dễ sử dụng### 🤖 ChatBot Service

- ✅ Voice memos to text

- ✅ Call center analytics**Chi tiết:** [SD WebUI Setup Guide →](stable-diffusion-webui/README.md)



### 🎨 Stable Diffusion- ✅ **Multiple Formats**: Hỗ trợ MP3, WAV, M4A, etc.

- ✅ Marketing materials

- ✅ Social media content---

- ✅ Product mockups

- ✅ Creative projects- **Multi-Model AI**: OpenAI GPT-4, Google Gemini, Local Qwen 1.5-1.8B



---## 🗂️ Cấu Trúc Dự Án



## 🤝 Contributing📁 **Location**: [`Speech2Text Services/`](Speech2Text%20Services/)  



Contributions welcome! Mỗi service có guide riêng:```



- **ChatBot**: [Contributing Guide →](ChatBot/README.md#-contributing)AI-Assistant/🚀 **Port**: 7860  - **Image Generation**: Integrated Stable Diffusion with txt2img, img2img, LoRA, VAE## 📋 Overview## 🚀 Quick Start

- **Text2SQL**: [Contributing Guide →](Text2SQL%20Services/README.md#-contributing)

- **Speech2Text**: [Contributing Guide →](Speech2Text%20Services/README.md)│

- **Stable Diffusion**: Follow official AUTOMATIC1111 guidelines

├── 📁 ChatBot/                    # 🤖 Multi-model AI Chatbot📖 **Docs**: [Speech2Text README](Speech2Text%20Services/README.md)

---

│   ├── app.py                    # Main application

## 🐛 Troubleshooting

│   ├── README.md                 # 📖 Documentation- **Memory System**: Conversation history with image storage

### Common Issues

│   ├── models/                   # Local Qwen models

**Port already in use:**

```bash│   └── Storage/                  # Generated images---

netstat -ano | findstr :5002

taskkill /PID <PID> /F│

```

├── 📁 Text2SQL Services/         # 📊 SQL Generator ⭐- **Message Editing**: Edit and regenerate responses

**Module not found:**

```bash│   ├── app_simple.py             # Main application

pip install -r requirements.txt --upgrade

```│   ├── README.md                 # 📖 Documentation### 4. 🎨 **Stable Diffusion WebUI**



**API Key errors:**│   ├── data/knowledge_base/      # AI learned SQL

- Check `.env` file exists

- Verify API key is valid│   └── sample_schemas/           # Example schemas**Advanced AI Image Generation**- **PDF Export**: Export conversations with images

- Restart application

│

**Chi tiết cho từng service:**

- ChatBot: [Troubleshooting →](ChatBot/docs/TROUBLESHOOTING.md)├── 📁 Speech2Text Services/      # 🎤 Voice Transcription

- Text2SQL: [Troubleshooting →](Text2SQL%20Services/README.md#-troubleshooting)

- Speech2Text: [Setup Guide →](Speech2Text%20Services/SETUP_FINAL.md)│   ├── app/web_ui.py             # Web interface



---│   ├── README.md                 # 📖 Documentation- ✅ **Text-to-Image**: Tạo ảnh từ text prompts- **Modern UI**: Responsive Tailwind CSS design**AI-Assistant** is a comprehensive AI platform integrating four powerful services:**New to this project?** Read [`GETTING_STARTED.md`](GETTING_STARTED.md) first!



## 📄 License│   └── SETUP_FINAL.md            # Setup guide



MIT License - see [LICENSE](LICENSE) file for details│- ✅ **Image-to-Image**: Chỉnh sửa và transform ảnh



---├── 📁 stable-diffusion-webui/    # 🎨 Image Generation



## 🙏 Acknowledgments│   ├── webui.bat                 # Windows launcher- ✅ **LoRA Support**: Fine-tuned models



### AI Models & APIs│   ├── README.md                 # 📖 Documentation

- **Google Gemini** - Primary AI engine

- **OpenAI** - GPT & Whisper models│   └── models/                   # SD models- ✅ **VAE Models**: Enhanced quality

- **DeepSeek** - Cost-effective AI

- **Qwen (Alibaba)** - Local LLM│

- **Stability AI** - Image generation

└── README.md                     # 📄 This file- ✅ **ControlNet**: Precise control### 📊 Text2SQL Service

### Frameworks & Tools

- **Flask** - Web framework```

- **ClickHouse** - Database

- **MongoDB** - NoSQL database- ✅ **Multiple Samplers**: DPM++, Euler, DDIM, etc.

- **AUTOMATIC1111** - SD WebUI

- **PyAnnote** - Speaker diarization---



---- **Natural Language Processing**: Convert English to SQL queries



## 📞 Support## 📚 Documentation



- **Issues**: [GitHub Issues](https://github.com/SkastVnT/AI-Assistant/issues)📁 **Location**: [`stable-diffusion-webui/`](stable-diffusion-webui/)  

- **Discussions**: [GitHub Discussions](https://github.com/SkastVnT/AI-Assistant/discussions)

### 📖 Service Documentation

---

🚀 **Port**: 7861  - **Database Integration**: ClickHouse database support1. 🤖 **ChatBot** - Multi-model conversational AI with local LLM and image generation```bash

## 📊 Stats

| Service | Main Docs | Setup Guide | Features |

![GitHub stars](https://img.shields.io/github/stars/SkastVnT/AI-Assistant?style=social)

![GitHub forks](https://img.shields.io/github/forks/SkastVnT/AI-Assistant?style=social)|---------|-----------|-------------|----------|📖 **Docs**: [SD WebUI README](stable-diffusion-webui/README.md)

![GitHub issues](https://img.shields.io/github/issues/SkastVnT/AI-Assistant)

| **ChatBot** | [README](ChatBot/README.md) | [Setup](ChatBot/README.md#-quick-start) | [Docs →](ChatBot/docs/) |

---

| **Text2SQL** | [README](Text2SQL%20Services/README.md) | [Setup](Text2SQL%20Services/SETUP_COMPLETE.md) | [AI Learning →](Text2SQL%20Services/AI_LEARNING_GUIDE.md) |- **Schema Intelligence**: Automatic table and column analysis

<div align="center">

| **Speech2Text** | [README](Speech2Text%20Services/README.md) | [Setup](Speech2Text%20Services/SETUP_FINAL.md) | [WebUI →](Speech2Text%20Services/WEBUI_SETUP_COMPLETE.md) |

## 🌟 Featured: Text2SQL v2.0

| **Stable Diffusion** | [README](stable-diffusion-webui/README.md) | [Setup](stable-diffusion-webui/README.md) | Built-in Help |---

**Production-ready SQL Generator với AI Learning**



[![Deploy](https://img.shields.io/badge/Deploy-Render.com-00979D?style=for-the-badge&logo=render)](Text2SQL%20Services/README.md#-deployment)

[![Docs](https://img.shields.io/badge/Docs-Read%20More-blue?style=for-the-badge)](Text2SQL%20Services/README.md)### 🎯 Hướng Dẫn Nhanh- **Query Validation**: Syntax checking and validation2. 📊 **Text2SQL** - Natural language to SQL query conversion# Launch ChatBot with Stable Diffusion (Auto)

[![Demo](https://img.shields.io/badge/Demo-Try%20Now-green?style=for-the-badge)](http://localhost:5002)



---

- **Text2SQL v2.0 Features**: [FEATURES_COMPLETE.md](Text2SQL%20Services/FEATURES_COMPLETE.md)## ✨ Tính Năng Nổi Bật

**Made with ❤️ in Vietnam**

- **AI Learning Guide**: [AI_LEARNING_GUIDE.md](Text2SQL%20Services/AI_LEARNING_GUIDE.md)

⭐ **Star this repo if you find it helpful!** ⭐

- **ChatBot Tools Integration**: [TOOLS_INTEGRATION_GUIDE.md](ChatBot/docs/TOOLS_INTEGRATION_GUIDE.md)- **Multi-table Support**: Complex joins and relationships

[🔝 Back to Top](#-ai-assistant---nền-tảng-tích-hợp-đa-dịch-vụ-ai)

- **Local Models Setup**: [LOCAL_MODELS_GUIDE.md](ChatBot/docs/LOCAL_MODELS_GUIDE.md)

</div>

### 🎯 Text2SQL v2.0 (Mới nhất!)

---

3. 🎤 **Speech2Text** - Vietnamese speech-to-text transcription.\scripts\startup\start_chatbot.bat

## 🚀 Deployment

```python

### 🌟 Text2SQL - Ready for Production!

# Ví dụ 1: Generate SQL từ ngôn ngữ tự nhiên### 🎤 Speech2Text Service

**Platform:** Render.com (FREE)  

**Build Time:** 3-5 minutes  User: "Top 10 khách hàng có doanh thu cao nhất trong năm 2024"

**Status:** ✅ Ready to deploy

AI: "SELECT customer_id, SUM(amount) FROM orders WHERE YEAR(order_date) = 2024..."- **Vietnamese Optimized**: PhoWhisper + Whisper dual transcription4. 🎨 **Stable Diffusion WebUI** - Advanced AI image generation

```bash

# Quick deploy guide

cd "Text2SQL Services"

git init && git add . && git commit -m "Deploy"# Ví dụ 2: Auto-generate questions từ schema- **Speaker Diarization**: Identify and separate speakers

git push origin main

# → Deploy on Render.com with 1-clickUser: "Tạo câu hỏi cho schema này"

```

AI: Tạo 5 câu hỏi + SQL queries- **Smart Fusion**: Qwen2.5-1.5B LLM for accuracy enhancement# ChatBot only (No image generation)

**Chi tiết đầy đủ:** [Deployment Guide →](Text2SQL%20Services/README.md#-deployment)



### 📊 Service Comparison

# Ví dụ 3: AI Learning- **Format Support**: WAV, MP3, M4A, FLAC

| Service | Size | Free Hosting | Deploy Difficulty | Best For |

|---------|------|--------------|-------------------|----------|User: "Câu SQL đúng: SELECT * FROM users WHERE active = 1"

| **Text2SQL** ✅ | 251MB | ✅ Yes (Render) | ⭐ Easy | Production |

| **ChatBot (API)** | 200MB | ✅ Yes (Railway) | ⭐⭐ Medium | Demo |AI: "✅ Đã học và lưu vào Knowledge Base"- **Web Interface**: Real-time transcription monitoringEach service operates independently with its own virtual environment, making deployment and maintenance simple and modular..\scripts\startup\start_chatbot_only.bat

| **ChatBot (Full)** | 4.1GB | ❌ No | ⭐⭐⭐ Hard | Local only |

| **Speech2Text** | 2GB | ❌ No | ⭐⭐⭐ Hard | Local only |

| **Stable Diffusion** | 10GB+ | ❌ No | ⭐⭐⭐⭐ Very Hard | Local only |

# Ví dụ 4: Database Connection

---

User: Click "🔌 Database" → Test connection → Save

## 🔧 Configuration

AI: "✅ Kết nối MongoDB Atlas thành công!"### 🎨 Stable Diffusion WebUI```

### 📌 API Keys Required

```

```bash

# Required (ít nhất 1):- **Advanced Generation**: txt2img, img2img, inpainting

GEMINI_API_KEY_1=your_key         # FREE at makersuite.google.com

OPENAI_API_KEY=your_key            # Optional---

DEEPSEEK_API_KEY=your_key          # Optional (cheapest)

- **Model Support**: Stable Diffusion 1.5, 2.1, SDXL---

# Optional (for ChatBot tools):

GOOGLE_SEARCH_API_KEY_1=your_key## 🚀 Khởi Động Nhanh

GOOGLE_CSE_ID=your_id

GITHUB_TOKEN=your_token- **Extensions**: LoRA, Hypernetworks, Textual Inversion

```

### Prerequisites

### 🔗 Get API Keys

- **Upscaling**: RealESRGAN, LDSR, SwinIR**Documentation:**

- **Gemini** (FREE): https://makersuite.google.com/app/apikey

- **OpenAI**: https://platform.openai.com/api-keys```

- **DeepSeek**: https://platform.deepseek.com

- **Hugging Face**: https://huggingface.co/settings/tokens✅ Python 3.10+- **API Access**: RESTful API for integration



---✅ Git



## 💡 Use Cases✅ 8GB+ RAM (16GB recommended)## ✨ Features- Setup: `docs/setup/SETUP_NEW_DEVICE.txt`



### 📊 Text2SQL✅ API Keys (Gemini required, others optional)

- ✅ Business Intelligence dashboards

- ✅ Data analysis automation```---

- ✅ SQL learning platform

- ✅ Database query assistant



### 🤖 ChatBot### 🌟 Quick Start: Text2SQL (Recommended)- Image Gen: `docs/guides/IMAGE_GENERATION_GUIDE.md`

- ✅ Customer support

- ✅ Personal assistant

- ✅ Code helper (Programming mode)

- ✅ Image generation chatbot```bash## 🚀 Quick Start



### 🎤 Speech2Textcd "Text2SQL Services"

- ✅ Meeting transcription

- ✅ Podcast transcription### 🤖 ChatBot Service- Troubleshooting: `docs/guides/FIX_*.md`

- ✅ Voice memos to text

- ✅ Call center analytics# Create & activate virtual environment



### 🎨 Stable Diffusionpython -m venv Text2SQL### Prerequisites

- ✅ Marketing materials

- ✅ Social media content.\Text2SQL\Scripts\activate  # Windows

- ✅ Product mockups

- ✅ Creative projects- **Multi-Model AI**: OpenAI GPT-4, Google Gemini, Local Qwen 1.5-1.8B



---# Install dependencies



## 🤝 Contributingpip install -r requirements.txt- **Python 3.10.6** (required)



Contributions welcome! Mỗi service có guide riêng:



- **ChatBot**: [Contributing Guide →](ChatBot/README.md#-contributing)# Configure- **NVIDIA GPU** with CUDA 11.8+ (for AI models)- **Image Generation**: Integrated Stable Diffusion with txt2img, img2img, LoRA, VAE---

- **Text2SQL**: [Contributing Guide →](Text2SQL%20Services/README.md#-contributing)

- **Speech2Text**: [Contributing Guide →](Speech2Text%20Services/README.md)cp .env.example .env

- **Stable Diffusion**: Follow official AUTOMATIC1111 guidelines

# Edit .env: Add GEMINI_API_KEY_1- **16GB+ RAM** (32GB recommended)

---



## 🐛 Troubleshooting

# Run- **50GB+ free disk space**- **Memory System**: Conversation history with image storage

### Common Issues

python app_simple.py

**Port already in use:**

```bash- **Git** for cloning repository

netstat -ano | findstr :5002

taskkill /PID <PID> /F# Open: http://localhost:5002

```

```- **Message Editing**: Edit and regenerate responses## �📋 Giới thiệu

**Module not found:**

```bash

pip install -r requirements.txt --upgrade

```### 🤖 Start ChatBot### 1. Clone Repository



**API Key errors:**

- Check `.env` file exists

- Verify API key is valid```bash- **PDF Export**: Export conversations with images

- Restart application

cd ChatBot

**Chi tiết cho từng service:**

- ChatBot: [Troubleshooting →](ChatBot/docs/TROUBLESHOOTING.md)python -m venv venv_chatbot```bash

- Text2SQL: [Troubleshooting →](Text2SQL%20Services/README.md#-troubleshooting)

- Speech2Text: [Setup Guide →](Speech2Text%20Services/SETUP_FINAL.md).\venv_chatbot\Scripts\activate



---pip install -r requirements.txtgit clone https://github.com/SkastVnT/AI-Assistant.git- **Modern UI**: Responsive Tailwind CSS design**AI Assistant Hub** là một nền tảng tổng hợp các dịch vụ AI tiên tiến, bao gồm:



## 📄 Licensecp .env.example .env



MIT License - see [LICENSE](LICENSE) file for details# Edit .env: Add API keyscd AI-Assistant



---python app.py



## 🙏 Acknowledgments# Open: http://localhost:5001```



### AI Models & APIs```

- **Google Gemini** - Primary AI engine

- **OpenAI** - GPT & Whisper models

- **DeepSeek** - Cost-effective AI

- **Qwen (Alibaba)** - Local LLM---

- **Stability AI** - Image generation

### 2. Choose and Setup Service### 📊 Text2SQL Service- 🤖 **AI ChatBot** - Trợ lý AI đa năng với Gemini, GPT-3.5, DeepSeek

### Frameworks & Tools

- **Flask** - Web framework## 🗂️ Project Structure

- **ClickHouse** - Database

- **MongoDB** - NoSQL database

- **AUTOMATIC1111** - SD WebUI

- **PyAnnote** - Speaker diarization```



---AI-Assistant/Each service has its own setup guide. Navigate to the service folder:- **Natural Language Processing**: Convert English to SQL queries- 🎤 **Speech to Text** - Chuyển đổi giọng nói thành văn bản (tiếng Việt)



## 📞 Support│



- **Issues**: [GitHub Issues](https://github.com/SkastVnT/AI-Assistant/issues)├── 📁 ChatBot/                          # 🤖 Conversational AI

- **Discussions**: [GitHub Discussions](https://github.com/SkastVnT/AI-Assistant/discussions)

│   ├── app.py                          # Main app

---

│   ├── requirements.txt**For ChatBot:**- **Database Integration**: ClickHouse database support- 💾 **Text to SQL** - Tạo câu truy vấn SQL từ ngôn ngữ tự nhiên

## 📊 Stats

│   ├── templates/

![GitHub stars](https://img.shields.io/github/stars/SkastVnT/AI-Assistant?style=social)

![GitHub forks](https://img.shields.io/github/forks/SkastVnT/AI-Assistant?style=social)│   ├── static/```bash

![GitHub issues](https://img.shields.io/github/issues/SkastVnT/AI-Assistant)

│   ├── models/                         # Local Qwen models

---

│   └── docs/cd ChatBot- **Schema Intelligence**: Automatic table and column analysis

<div align="center">

│

## 🌟 Featured: Text2SQL v2.0

├── 📁 Text2SQL Services/               # 📊 SQL Generator ⭐# Follow ChatBot/README.md for setup

**Production-ready SQL Generator với AI Learning**

│   ├── app_simple.py                   # Main app  

[![Deploy](https://img.shields.io/badge/Deploy-Render.com-00979D?style=for-the-badge&logo=render)](Text2SQL%20Services/README.md#-deployment)

[![Docs](https://img.shields.io/badge/Docs-Read%20More-blue?style=for-the-badge)](Text2SQL%20Services/README.md)│   ├── requirements.txt```- **Query Validation**: Syntax checking and validationTất cả được kết nối qua một **Gateway Hub** với giao diện web đẹp mắt, hiện đại.

[![Demo](https://img.shields.io/badge/Demo-Try%20Now-green?style=for-the-badge)](http://localhost:5002)

│   ├── templates/

---

│   ├── static/

**Made with ❤️ in Vietnam**

│   ├── data/

⭐ **Star this repo if you find it helpful!** ⭐

│   │   ├── knowledge_base/            # AI learned SQL**For Text2SQL:**- **Multi-table Support**: Complex joins and relationships

[🔝 Back to Top](#-ai-assistant---nền-tảng-tích-hợp-đa-dịch-vụ-ai)

│   │   └── connections/               # DB connections

</div>

│   ├── sample_schemas/```bash

│   └── docs/

│cd "Text2SQL Services"---

├── 📁 Speech2Text Services/            # 🎤 Transcription

│   ├── app/# Follow Text2SQL Services/README.md for setup

│   └── docs/

│```### 🎤 Speech2Text Service

├── 📁 stable-diffusion-webui/          # 🎨 Image Generation

│   ├── webui.bat

│   └── models/

│**For Speech2Text:**- **Vietnamese Optimized**: PhoWhisper + Whisper dual transcription## ✨ Tính năng

└── README.md                           # This file

``````bash



---cd "Speech2Text Services"- **Speaker Diarization**: Identify and separate speakers



## 🚀 Deployment Guide# Follow Speech2Text Services/README.md for setup



### 🌟 Deploy Text2SQL to Render.com (FREE)```- **Smart Fusion**: Qwen2.5-1.5B LLM for accuracy enhancement### 🚀 AI Assistant Hub Gateway



```bash

# 1. Push to GitHub

cd "Text2SQL Services"**For Stable Diffusion:**- **Format Support**: WAV, MP3, M4A, FLAC- ✅ Giao diện web đẹp với **Tailwind CSS**

git init

git add .```bash

git commit -m "Initial commit"

git remote add origin https://github.com/YOUR_USERNAME/text2sql-ai.gitcd stable-diffusion-webui- **Web Interface**: Real-time transcription monitoring- ✅ Điều hướng tập trung đến các services

git push -u origin main

# Follow stable-diffusion-webui/README.md for setup

# 2. Deploy on Render.com

# - Sign up at render.com```- ✅ Monitoring và health checks

# - Connect GitHub repo

# - Build: pip install -r requirements.txt

# - Start: python app_simple.py

# - Add env: GEMINI_API_KEY_1### 3. Quick Launch Scripts (Windows)### 🎨 Stable Diffusion WebUI- ✅ Responsive design, dark theme



# 3. Done! Live at: https://text2sql-yourname.onrender.com

```

```bash- **Advanced Generation**: txt2img, img2img, inpainting- ✅ Quick start scripts

**Free Tier:** 750 hours/month, 512MB RAM, Auto HTTPS ✅

# ChatBot with Stable Diffusion (recommended)

---

.\scripts\startup\start_chatbot_with_sd.bat- **Model Support**: Stable Diffusion 1.5, 2.1, SDXL

## 📊 Service Comparison



| Service | Size | Deployment | Free Hosting | Best For |

|---------|------|------------|--------------|----------|# ChatBot only- **Extensions**: LoRA, Hypernetworks, Textual Inversion### 🤖 AI ChatBot

| **Text2SQL** ✅ | 251MB | Easy | Yes | Production |

| **ChatBot (API)** | 200MB | Medium | Yes | Demo |.\scripts\startup\start_chatbot_only.bat

| **ChatBot (Full)** | 4.1GB | Hard | No | Local only |

| **Speech2Text** | 2GB | Hard | No | Local only |```- **Upscaling**: RealESRGAN, LDSR, SwinIR- ✅ 3 mô hình AI: **Gemini, GPT-3.5, DeepSeek**

| **Stable Diffusion** | 10GB+ | No | No | Local only |



**💡 Recommendation:** Deploy Text2SQL first!

---- **API Access**: RESTful API for integration- ✅ 3 chế độ: Tâm lý, Đời sống, Trò chuyện

---



## 🔧 Configuration

## 🗂️ Project Structure- ✅ Lưu lịch sử conversation

### Get API Keys:



- **Gemini** (Required): https://makersuite.google.com/app/apikey (FREE)

- **OpenAI** (Optional): https://platform.openai.com/api-keys```---- ✅ Real-time chat interface

- **DeepSeek** (Optional): https://platform.deepseek.com

AI-Assistant/

### Environment Setup:

│

```bash

# .env file├── ChatBot/                          # ChatBot Service

GEMINI_API_KEY_1=your_key_here

OPENAI_API_KEY=your_key_here  # Optional│   ├── app.py                        # Main Flask application## 🚀 Quick Start### 🎤 Speech to Text

DEEPSEEK_API_KEY=your_key_here  # Optional

```│   ├── requirements.txt              # Python dependencies



---│   ├── README.md                     # Service documentation- ✅ Nhận dạng giọng nói **tiếng Việt**



## 📖 Documentation│   ├── .env.example                  # Environment template



- **Text2SQL**: [README](Text2SQL%20Services/README.md) | [AI Learning Guide](Text2SQL%20Services/AI_LEARNING_GUIDE.md) | [Features](Text2SQL%20Services/FEATURES_COMPLETE.md)│   ├── templates/                    # HTML templates### Prerequisites- ✅ **Speaker Diarization** (phân tách người nói)

- **ChatBot**: [README](ChatBot/README.md) | [Tools Guide](ChatBot/docs/TOOLS_INTEGRATION_GUIDE.md) | [Local Models](ChatBot/docs/LOCAL_MODELS_GUIDE.md)

- **Speech2Text**: [README](Speech2Text%20Services/README.md) | [Setup Guide](Speech2Text%20Services/SETUP_FINAL.md)│   │   └── index.html

- **Stable Diffusion**: [README](stable-diffusion-webui/README.md)

│   ├── static/                       # Static files- ✅ Hỗ trợ nhiều format: WAV, MP3, M4A, FLAC

---

│   │   ├── css/

## 🐛 Troubleshooting

│   │   └── js/- **Python 3.10.6** (required)- ✅ WebSocket real-time updates

**Port already in use:**

```bash│   ├── src/                          # Source code

netstat -ano | findstr :5002

taskkill /PID <PID> /F│   │   └── utils/- **NVIDIA GPU** with CUDA 11.8+ (for AI models)- ✅ PhoWhisper & Whisper models

```

│   │       ├── local_model_loader.py

**Module not found:**

```bash│   │       └── sd_client.py- **16GB+ RAM** (32GB recommended)

pip install -r requirements.txt --upgrade

```│   ├── models/                       # Local AI models



**Database connection failed:**│   │   └── Qwen1.5-1.8B-Chat/- **50GB+ free disk space**### 💾 Text to SQL

- Check database is running

- Verify credentials│   ├── Storage/                      # Generated images

- For MongoDB Atlas: whitelist IP

│   │   └── Image_Gen/- **Git** for cloning repository- ✅ Tạo SQL từ ngôn ngữ tự nhiên

---

│   ├── data/                         # User data

## 🤝 Contributing

│   │   └── memory/- ✅ **Gemini AI** powered

Contributions welcome! Please open issues or PRs.

│   └── venv_chatbot/                 # Virtual environment

---

│### 1. Clone Repository- ✅ Memory system - học từ lịch sử

## 📄 License

├── Text2SQL Services/                # Text2SQL Service

MIT License - see [LICENSE](LICENSE)

│   ├── app.py                        # Main Flask application- ✅ Hỗ trợ nhiều loại database

---

│   ├── requirements.txt              # Python dependencies

## 🙏 Acknowledgments

│   ├── README.md                     # Service documentation```bash- ✅ Evaluation metrics

- **Google Gemini** - AI models

- **OpenAI** - GPT & Whisper│   ├── .env.example                  # Environment template

- **Flask** - Web framework

- **ClickHouse** & **MongoDB** - Databases│   ├── templates/                    # HTML templatesgit clone https://github.com/SkastVnT/AI-Assistant.git



---│   ├── src/                          # Source code



<div align="center">│   ├── data/                         # Training datacd AI-Assistant---



## 🌟 Quick Links│   │   └── raw/



| Service | Live Demo | Documentation | Deploy |│   │       └── spider/```

|---------|-----------|---------------|--------|

| Text2SQL | [Demo](#) | [Docs](Text2SQL%20Services/README.md) | [Deploy](#-deployment-guide) |│   ├── sample/                       # Sample files

| ChatBot | [Demo](#) | [Docs](ChatBot/README.md) | [Guide](#) |

│   └── tools/                        # Utility scripts## 🚀 Khởi động nhanh

---

│

**Made with ❤️ in Vietnam**

├── Speech2Text Services/             # Speech2Text Service### 2. Choose and Setup Service

⭐ **Star this repo if helpful!** ⭐

│   ├── requirements.txt              # Python dependencies

[🔝 Back to Top](#-ai-assistant---integrated-multi-service-ai-platform)

│   ├── README.md                     # Service documentation### Cách 1: Khởi động Hub Gateway

</div>

│   ├── .env.example                  # Environment template

│   ├── app/                          # Main applicationEach service has its own setup guide. Navigate to the service folder:```bash

│   │   ├── web_ui.py                 # Web interface

│   │   ├── core/                     # Core functionality# Clone repository

│   │   │   ├── models/

│   │   │   ├── pipelines/**For ChatBot:**git clone https://github.com/SkastVnT/AI-Assistant.git

│   │   │   └── utils/

│   │   ├── api/                      # API endpoints```bashcd AI-Assistant

│   │   ├── config/                   # Configuration

│   │   └── data/                     # Data storagecd ChatBot

│   ├── docs/                         # Documentation

│   └── scripts/                      # Utility scripts# Follow ChatBot/README.md for setup# Cài đặt dependencies

│

├── stable-diffusion-webui/           # Stable Diffusion Service```pip install -r requirements.txt

│   ├── webui.py                      # Main WebUI launcher

│   ├── launch.py                     # Launch script

│   ├── requirements.txt              # Python dependencies

│   ├── README.md                     # Service documentation**For Text2SQL:**# Khởi động Hub

│   ├── models/                       # Model files (large)

│   │   ├── Stable-diffusion/         # SD checkpoints```bashpython hub.py

│   │   ├── Lora/                     # LoRA models

│   │   ├── VAE/                      # VAE modelscd "Text2SQL Services"```

│   │   └── ...

│   ├── outputs/                      # Generated images# Follow Text2SQL Services/README.md for setup

│   ├── extensions/                   # Extensions

│   ├── scripts/                      # Generation scripts```Truy cập: **http://localhost:3000**

│   └── venv_sd/                      # Virtual environment

│

├── docs/                             # Project documentation

│   ├── GETTING_STARTED.md**For Speech2Text:**### Cách 2: Khởi động tất cả services

│   ├── PROJECT_STRUCTURE.md

│   ├── QUICK_REFERENCE.md```bash

│   └── guides/

│cd "Speech2Text Services"**Windows:**

├── scripts/                          # Utility scripts

│   └── startup/                      # Launch scripts# Follow Speech2Text Services/README.md for setup```bash

│       ├── start_chatbot_with_sd.bat

│       └── start_chatbot_only.bat```start_all.bat

│

├── requirements.txt                  # Root dependencies```

├── README.md                         # This file

├── .gitignore                        # Git ignore rules**For Stable Diffusion:**

└── LICENSE                           # License file

``````bash**Linux/Mac:**



---cd stable-diffusion-webui```bash



## 🛠️ Installation# Follow stable-diffusion-webui/README.md for setupchmod +x start_all.sh



### System Requirements```./start_all.sh



| Component | Minimum | Recommended |```

|-----------|---------|-------------|

| Python | 3.10.6 | 3.10.6 |### 3. Quick Launch Scripts (Windows)

| GPU | NVIDIA GTX 1060 6GB | RTX 3060 12GB+ |

| RAM | 16GB | 32GB |---

| Storage | 50GB | 100GB SSD |

| OS | Windows 10 | Windows 11 |```bash



### Install Python 3.10.6# ChatBot with Stable Diffusion (recommended)## 🏗️ Kiến trúc



```bash.\scripts\startup\start_chatbot_with_sd.bat

# Download from python.org

# Or use pyenv (recommended)```

pyenv install 3.10.6

pyenv global 3.10.6# ChatBot only┌─────────────────────────────────────────┐

```

.\scripts\startup\start_chatbot_only.bat│   AI Assistant Hub (Port 3000)          │

### Install CUDA 11.8

```│   - Gateway & UI                        │

1. Download from [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-11-8-0-download-archive)

2. Install following the wizard│   - Service discovery                   │

3. Verify: `nvidia-smi`

---└──────────────┬──────────────────────────┘

### Install PyTorch

               │

```bash

# For CUDA 11.8## 🗂️ Project Structure    ┌──────────┼──────────┐

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

```    │          │          │



---```    ▼          ▼          ▼



## 📚 DocumentationAI-Assistant/┌────────┐ ┌────────┐ ┌────────┐



### Service Documentation├── ChatBot/                      # Chatbot service│ChatBot │ │Speech  │ │Text2SQL│



- [ChatBot README](ChatBot/README.md) - ChatBot setup and usage│   ├── app.py                    # Main application│:5000   │ │:5001   │ │:5002   │

- [Text2SQL README](Text2SQL%20Services/README.md) - Text2SQL setup and usage

- [Speech2Text README](Speech2Text%20Services/README.md) - Speech2Text setup and usage│   ├── requirements.txt          # Dependencies└────────┘ └────────┘ └────────┘

- [Stable Diffusion README](stable-diffusion-webui/README.md) - SD WebUI setup and usage

│   ├── README.md                 # Service documentation```

### General Documentation

│   ├── venv_chatbot/             # Virtual environment

- [Getting Started](docs/GETTING_STARTED.md) - First-time setup guide

- [Project Structure](docs/PROJECT_STRUCTURE.md) - Detailed project structure│   ├── templates/                # HTML templates---

- [Quick Reference](docs/QUICK_REFERENCE.md) - Quick reference guide

│   ├── static/                   # CSS, JS, images

### Guides

│   ├── models/                   # Local AI models## 🛠️ Cài đặt

- [Image Generation Guide](ChatBot/docs/IMAGE_GENERATION_TOOL_GUIDE.md)

- [LoRA & VAE Guide](ChatBot/docs/LORA_VAE_GUIDE.md)│   └── Storage/                  # Generated images

- [Troubleshooting](docs/guides/TROUBLESHOOTING.md)

│### Yêu cầu hệ thống

---

├── Text2SQL Services/            # Text2SQL service- **Python:** 3.8+

## 🌐 Service Endpoints

│   ├── app.py                    # Main application- **RAM:** 8GB (tối thiểu), 16GB (khuyến nghị)

| Service | Port | URL | Description |

|---------|------|-----|-------------|│   ├── requirements.txt          # Dependencies- **Storage:** 10GB+ free space

| ChatBot | 5000 | http://localhost:5000 | Main chatbot interface |

| Text2SQL | 5001 | http://localhost:5001 | SQL generation interface |│   ├── README.md                 # Service documentation- **GPU:** Optional (tốt cho Speech2Text)

| Speech2Text | 5002 | http://localhost:5002 | Transcription interface |

| Stable Diffusion | 7860 | http://localhost:7860 | Image generation UI |│   ├── templates/                # HTML templates

| SD API | 7860 | http://localhost:7860/docs | API documentation |

│   └── data/                     # Training data### Bước 1: Clone repository

---

│```bash

## 🔧 Configuration

├── Speech2Text Services/         # Speech2Text servicegit clone https://github.com/SkastVnT/AI-Assistant.git

### Environment Variables

│   ├── requirements.txt          # Dependenciescd AI-Assistant

Each service uses `.env` file for configuration. Copy `.env.example` to `.env` in each service folder:

│   ├── README.md                 # Service documentation```

**ChatBot (.env):**

```env│   ├── app/                      # Application code

OPENAI_API_KEY=your_openai_key

GOOGLE_API_KEY=your_gemini_key│   │   ├── core/                 # Core functionality### Bước 2: Cài đặt dependencies

SD_API_URL=http://127.0.0.1:7860

```│   │   ├── api/                  # API endpoints



**Text2SQL (.env):**│   │   └── web_ui.py             # Web interface**Hub:**

```env

GOOGLE_API_KEY=your_gemini_key│   └── data/                     # Audio data```bash

CLICKHOUSE_HOST=localhost

CLICKHOUSE_DATABASE=default│pip install -r requirements.txt

```

├── stable-diffusion-webui/       # Stable Diffusion service```

**Speech2Text (.env):**

```env│   ├── webui.py                  # Main WebUI

HF_TOKEN=your_huggingface_token  # Optional for gated models

```│   ├── requirements.txt          # Dependencies**ChatBot:**



---│   ├── README.md                 # Service documentation```bash



## 🐛 Troubleshooting│   ├── models/                   # SD models (large files)cd ChatBot



### Common Issues│   └── outputs/                  # Generated imagespip install -r requirements.txt



**1. Import torch error**│cd ..

```bash

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118├── docs/                         # Documentation```

```

│   ├── GETTING_STARTED.md        # Getting started guide

**2. CUDA not detected**

```bash│   ├── PROJECT_STRUCTURE.md      # Project structure**Speech2Text:**

# Verify CUDA installation

nvidia-smi│   └── guides/                   # Various guides```bash



# Reinstall PyTorch with CUDA│cd "Speech2Text Services"

pip uninstall torch torchvision torchaudio

pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118├── scripts/                      # Utility scriptspip install -r requirements.txt

```

│   └── startup/                  # Launch scriptscd ..

**3. Port already in use**

```bash│```

# Change port in service .env file or config

FLASK_PORT=5050├── requirements.txt              # Root dependencies

```

├── README.md                     # This file**Text2SQL:**

**4. Virtual environment issues**

```bash└── .gitignore                    # Git ignore rules```bash

# Delete and recreate venv

Remove-Item -Recurse venv_*```cd "Text2SQL Services"

python -m venv venv_servicename

.\venv_servicename\Scripts\activatepip install -r requirements.txt

pip install -r requirements.txt

```---cd ..



---```



## 🔄 Updates & Versions## 🛠️ Installation



### Latest Version: Ver_1 (October 2025)### Bước 3: Cấu hình API Keys



**What's New:**### System Requirements

- ✅ All services integrated in single repository

- ✅ Updated to Python 3.10.6Tạo file `.env` tại thư mục gốc:

- ✅ Comprehensive README for each service

- ✅ Updated requirements.txt with version pinning| Component | Minimum | Recommended |

- ✅ Improved .gitignore for better repository management

- ✅ Stable Diffusion and Speech2Text fully integrated|-----------|---------|-------------|```env



### Previous Versions:| Python | 3.10.6 | 3.10.6 |# OpenAI

- **Img2Img Branch**: Added img2img support with LoRA and VAE

- **ChatBotCoding Branch**: Initial chatbot implementation| GPU | NVIDIA GTX 1060 6GB | RTX 3060 12GB+ |OPENAI_API_KEY=sk-...



---| RAM | 16GB | 32GB |



## 📝 License| Storage | 50GB | 100GB SSD |# DeepSeek



This project is licensed under the MIT License. See individual service folders for specific licensing information.| OS | Windows 10 | Windows 11 |DEEPSEEK_API_KEY=sk-...



### Third-Party Software



- **Stable Diffusion WebUI**: AGPL-3.0 License### Install Python 3.10.6# Google Gemini

- **Transformers**: Apache 2.0 License

- **Flask**: BSD-3-Clause LicenseGEMINI_API_KEY_1=AIza...



---```bashGEMINI_API_KEY_2=AIza...



## 🤝 Contributing# Download from python.org



Contributions are welcome! Please:# Or use pyenv (recommended)# HuggingFace



1. Fork the repositorypyenv install 3.10.6HF_API_TOKEN=hf_...

2. Create a feature branch (`git checkout -b feature/AmazingFeature`)

3. Commit your changes (`git commit -m 'Add AmazingFeature'`)pyenv global 3.10.6

4. Push to the branch (`git push origin feature/AmazingFeature`)

5. Open a Pull Request```# Flask



---FLASK_SECRET_KEY=your-secret-key



## 📧 Support### Install CUDA 11.8```



- **Issues**: [GitHub Issues](https://github.com/SkastVnT/AI-Assistant/issues)

- **Discussions**: [GitHub Discussions](https://github.com/SkastVnT/AI-Assistant/discussions)

1. Download from [NVIDIA CUDA Toolkit](https://developer.nvidia.com/cuda-11-8-0-download-archive)Copy `.env` vào các thư mục services tương ứng.

---

2. Install following the wizard

## 🙏 Acknowledgments

3. Verify: `nvidia-smi`---

- **AUTOMATIC1111** - Stable Diffusion WebUI

- **OpenAI** - GPT models

- **Google** - Gemini API

- **HuggingFace** - Transformers and models### Install PyTorch## 📖 Hướng dẫn sử dụng

- **Qwen Team** - Qwen local models

- **VinAI** - PhoWhisper Vietnamese ASR



---```bash### Khởi động Hub Gateway



<div align="center"># For CUDA 11.8



**Made with ❤️ by SkastVnT**pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118```bash



⭐ Star this repo if you find it helpful!```python hub.py



</div>```


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
