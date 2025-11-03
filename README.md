#  AI-Assistant - Nền Tảng Tích Hợp Đa Dịch Vụ AI

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)
![AI](https://img.shields.io/badge/AI-Powered-purple?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Nền tảng tích hợp 4 dịch vụ AI mạnh mẽ: ChatBot, Text2SQL, Speech2Text, Image Generation**

[Tính năng](#-tính-năng-nổi-bật)  [Khởi động nhanh](#-quick-start)  [Cài đặt](#-yêu-cầu-hệ-thống)  [Tài liệu](#-tài-liệu)

</div>

---

##  Tổng Quan

**AI-Assistant** là nền tảng AI tích hợp gồm **4 dịch vụ độc lập**, mỗi service có thể chạy riêng hoặc kết hợp với nhau. Dự án được xây dựng theo chuẩn **Generative AI Template** với kiến trúc modular, production-ready.

###  Các Dịch Vụ

| Service | Mô Tả | Port | Status | Docs |
|---------|-------|------|--------|------|
|  **ChatBot** | Multi-model AI (Gemini, GPT-4, Qwen) + Image Gen | 5001 |  Ready | [ Docs](ChatBot/README.md) |
|  **Text2SQL**  | Natural Language  SQL với AI Learning | 5002 |  Production | [ Docs](Text2SQL%20Services/README.md) |
|  **Speech2Text** | Vietnamese transcription + Diarization | 7860 |  Beta | [ Docs](Speech2Text%20Services/README.md) |
|  **Stable Diffusion** | AI Image Generation (AUTOMATIC1111 WebUI) | 7861 |  Ready | [ Docs](stable-diffusion-webui/README.md) |

---

##  Tính Năng Nổi Bật

###  ChatBot Service (v2.0)

-  **Multi-Model Support**: Gemini 2.0 Flash, GPT-4, DeepSeek, Qwen 1.5B (local), BloomVN
-  **Image Generation**: Tích hợp Stable Diffusion với LoRA & VAE support
-  **AI Memory System**: Lưu trữ conversations và generated images
-  **Tools Integration**: Google Search, GitHub Search
-  **Export PDF**: Export conversations kèm images và metadata
-  **Modern UI**: Tailwind CSS, responsive design, dark mode support

 **[Chi tiết đầy đủ ](ChatBot/README.md)** |  **Port**: 5001

---

###  Text2SQL Service  **MỚI NHẤT v2.0**

-  **Natural Language to SQL**: Chuyển đổi tiếng Việt/English thành SQL queries
-  **Multi-Database Support**: ClickHouse, MongoDB, PostgreSQL, MySQL, SQL Server
-  **AI Learning System**: Lưu SQL đúng vào Knowledge Base, tự học từ user feedback
-  **Question Generation**: Tự động tạo 5 câu hỏi mẫu từ database schema
-  **Database Connection**: Kết nối trực tiếp localhost & MongoDB Atlas
-  **Deep Thinking Mode**: Enhanced reasoning cho complex queries
-  **Ready to Deploy**: Hướng dẫn deploy FREE trên Render.com

 **[Chi tiết đầy đủ ](Text2SQL%20Services/README.md)** |  **Port**: 5002  
 **[Deployment Guide ](Text2SQL%20Services/README.md#-deployment)**

---

###  Speech2Text Service (v3.6.0+)

-  **Dual-Model Fusion**: Whisper + PhoWhisper cho accuracy tối đa (98%+)
-  **Vietnamese Optimized**: Fine-tuned cho tiếng Việt
-  **Speaker Diarization**: pyannote.audio 3.1 với 95-98% accuracy
-  **Qwen Enhancement**: LLM-powered transcript refinement
-  **Real-time Web UI**: Progress tracking với WebSocket
-  **Multi-format Support**: MP3, WAV, M4A, FLAC

 **[Chi tiết đầy đủ ](Speech2Text%20Services/README.md)** |  **Port**: 7860

---

###  Stable Diffusion WebUI

> **Based on [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui)**  
> *Customized configuration for optimized performance*

-  **Text-to-Image**: Tạo ảnh từ text prompts
-  **Image-to-Image**: Transform và edit images
-  **LoRA + VAE**: Fine-tuned models support
-  **ControlNet**: Precise generation control
-  **API Enabled**: RESTful API, tích hợp sẵn với ChatBot
-  **GPU Optimized**: CUDA 12.1, xformers support

 **[Chi tiết đầy đủ ](stable-diffusion-webui/README.md)** |  **Port**: 7861  
 **[Original Project ](https://github.com/AUTOMATIC1111/stable-diffusion-webui)**

---

##  Quick Start

### 1 Text2SQL (Khuyến nghị - Dễ nhất!)

```bash
# Di chuyển vào thư mục
cd "Text2SQL Services"

# Tạo virtual environment
python -m venv Text2SQL
.\Text2SQL\Scripts\activate

# Cài đặt dependencies
pip install -r requirements.txt

# Cấu hình API key (tạo file .env và thêm GEMINI_API_KEY_1)

# Khởi động service
python app_simple.py
#  http://localhost:5002
```

 **[Chi tiết ](Text2SQL%20Services/README.md)**

---

### 2 ChatBot

```bash
# Di chuyển vào thư mục
cd ChatBot

# Tạo virtual environment
python -m venv venv_chatbot
.\venv_chatbot\Scripts\activate

# Cài đặt dependencies
pip install -r requirements.txt

# Cấu hình API keys (tạo file .env)

# Khởi động service
python app.py
#  http://localhost:5001
```

 **[Chi tiết ](ChatBot/README.md)**

---

### 3 Speech2Text

```bash
# Di chuyển vào thư mục
cd "Speech2Text Services"

# Chạy script cài đặt dependencies
.\scripts\fix_dependencies.bat

# Khởi động Web UI
.\start_webui.bat
#  http://localhost:7860
```

 **[Chi tiết ](Speech2Text%20Services/SETUP_FINAL.md)**

---

### 4 Stable Diffusion

```bash
# Di chuyển vào thư mục
cd stable-diffusion-webui

# Khởi động WebUI
.\webui.bat
#  http://localhost:7861
```

 **[Chi tiết ](stable-diffusion-webui/README.md)**

---

##  Cấu Trúc Dự Án

```
AI-Assistant/

  ChatBot/                   # ChatBot Service (v2.0)
    app.py                   # Main application
    requirements.txt         # Dependencies
    src/                     # Source code
    Storage/                 # Conversations & images

  Text2SQL Services/        # Text2SQL Service (v2.0)
    app_simple.py            # Main application
    requirements.txt         # Dependencies
    src/                     # Source code
    data/                    # Knowledge base & prompts

  Speech2Text Services/     # Speech2Text Service (v3.6)
    app/                     # Web UI application
    src/                     # Core processing
    requirements.txt         # Dependencies

  stable-diffusion-webui/   # Stable Diffusion WebUI
    webui.bat                # Launch script
    launch.py                # Main launcher

  docs/                      # Documentation
  README.md                  # This file
```

---

##  Yêu Cầu Hệ Thống

### Phần Cứng

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **CPU** | 4 cores | 8+ cores |
| **RAM** | 8 GB | 16+ GB |
| **GPU** | Optional | NVIDIA RTX 3060+ |
| **Storage** | 20 GB | 50+ GB SSD |

### Phần Mềm

- **OS**: Windows 10/11, Linux, macOS 11+
- **Python**: 3.10, 3.11 (khuyến nghị 3.10)
- **CUDA**: 12.1+ (nếu dùng GPU NVIDIA)
- **Git**: Latest version

### API Keys (Tùy chọn theo service)

- **Gemini API**: Free tại [ai.google.dev](https://ai.google.dev)
- **OpenAI API**: [platform.openai.com](https://platform.openai.com)
- **HuggingFace Token**: Free tại [huggingface.co](https://huggingface.co)

---

##  Tài Liệu

### Service Documentation

-  **[ChatBot README](ChatBot/README.md)** - Tài liệu ChatBot Service
-  **[Text2SQL README](Text2SQL%20Services/README.md)** - Tài liệu Text2SQL Service  
-  **[Speech2Text README](Speech2Text%20Services/README.md)** - Tài liệu Speech2Text Service
-  **[Stable Diffusion README](stable-diffusion-webui/README.md)** - Tài liệu Stable Diffusion

---

##  Contributing

Chúng tôi hoan nghênh mọi đóng góp! Vui lòng:

1. Fork repository
2. Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

---

##  License

Dự án này được phân phối dưới giấy phép MIT License. Xem file [LICENSE](LICENSE) để biết thêm chi tiết.

---

##  Authors

- **SkastVnT** - [GitHub](https://github.com/SkastVnT)

---

##  Acknowledgments

- [AUTOMATIC1111](https://github.com/AUTOMATIC1111/stable-diffusion-webui) - Stable Diffusion WebUI
- [Google Gemini](https://ai.google.dev) - Gemini API
- [OpenAI](https://openai.com) - GPT models
- [Hugging Face](https://huggingface.co) - Model hosting
- Cộng đồng AI Việt Nam

---

<div align="center">

** Nếu project hữu ích, hãy cho một star! **

Made with  by SkastVnT

</div>