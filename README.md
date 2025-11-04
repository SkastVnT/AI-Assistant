<div align="center">

#  AI-Assistant 
### *Nền Tảng Tích Hợp Đa Dịch Vụ AI*

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=22&duration=3000&pause=1000&color=6366F1&center=true&vCenter=true&width=600&lines=ChatBot+%7C+Text2SQL+%7C+Speech2Text+%7C+Image+Gen;Multi-Model+AI+Platform;Built+with+%E2%9D%A4%EF%B8%8F+by+SkastVnT" alt="Typing SVG" />

---

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=for-the-badge&logo=flask&logoColor=white)
![AI](https://img.shields.io/badge/AI-Powered-6366F1?style=for-the-badge&logo=openai&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge&logo=opensourceinitiative&logoColor=white)

<br/>

![Stars](https://img.shields.io/github/stars/SkastVnT/AI-Assistant?style=for-the-badge&logo=github&logoColor=white&color=FFD700)
![Forks](https://img.shields.io/github/forks/SkastVnT/AI-Assistant?style=for-the-badge&logo=github&logoColor=white&color=3B82F6)
![Issues](https://img.shields.io/github/issues/SkastVnT/AI-Assistant?style=for-the-badge&logo=github&logoColor=white&color=10B981)
![Watchers](https://img.shields.io/github/watchers/SkastVnT/AI-Assistant?style=for-the-badge&logo=github&logoColor=white&color=EC4899)

<br/>

### ⭐⭐ **2 STARS ACHIEVED!** ⭐⭐
*Thank you for your support! 🎉*

** Nền tảng tích hợp 4 dịch vụ AI mạnh mẽ **

[ Tính năng](#-tính-năng-nổi-bật)  
[ Quick Start](#-quick-start)  
[ Cài đặt](#-yêu-cầu-hệ-thống)  
[ Tài liệu](#-tài-liệu)

</div>

---

<div align="center">

##  **SHOWCASE** 

</div>

<table>
<tr>
<td width="50%">

###  **ChatBot AI**
<img src="https://img.shields.io/badge/Multi--Model-Support-8B5CF6?style=flat-square" />
<img src="https://img.shields.io/badge/Image-Generation-EC4899?style=flat-square" />

-  Gemini 2.0 Flash
-  Stable Diffusion Integration
-  AI Memory System
-  Google & GitHub Search
-  PDF Export

</td>
<td width="50%">

###  **Text2SQL**  NEW!
<img src="https://img.shields.io/badge/NL-to--SQL-3B82F6?style=flat-square" />
<img src="https://img.shields.io/badge/AI-Learning-10B981?style=flat-square" />

-  Vietnamese Support
-  Multi-Database
-  AI Learning System
-  Question Generation
-  Cloud Deploy Ready

</td>
</tr>
<tr>
<td width="50%">

###  **Speech2Text**
<img src="https://img.shields.io/badge/Accuracy-98%25-10B981?style=flat-square" />
<img src="https://img.shields.io/badge/Vietnamese-Optimized-EF4444?style=flat-square" />

-  Dual-Model Fusion
-  Speaker Diarization
-  Vietnamese Fine-tuned
-  Real-time WebUI
-  Multi-format Support

</td>
<td width="50%">

###  **Stable Diffusion**
<img src="https://img.shields.io/badge/Text-to--Image-F59E0B?style=flat-square" />
<img src="https://img.shields.io/badge/GPU-Optimized-06B6D4?style=flat-square" />

-  Text-to-Image
-  Image-to-Image
-  LoRA & VAE Support
-  ControlNet
-  API Enabled

</td>
</tr>
</table>

---

<div align="center">

##  **TỔNG QUAN**

</div>

> **AI-Assistant** là nền tảng AI tích hợp gồm **4 dịch vụ độc lập**, mỗi service có thể chạy riêng hoặc kết hợp với nhau. Dự án được xây dựng với kiến trúc **modular, production-ready**.

<div align="center">

###  **CÁC DỊCH VỤ**

|  Service |  Mô Tả |  Port |  Status |  Docs |
|:-----------|:---------|:--------|:----------|:--------|
|  **ChatBot v2.0**  | Multi-model AI + Auto-File Analysis + Stop Gen | `5001` | <img src="https://img.shields.io/badge/-Production-10B981?style=flat-square" /> | [ Docs](ChatBot/README.md) |
|  **Text2SQL v2.0**  | Natural Language  SQL + AI Learning | `5002` | <img src="https://img.shields.io/badge/-Production-3B82F6?style=flat-square" /> | [ Docs](Text2SQL%20Services/README.md) |
|  **Speech2Text** | Vietnamese Transcription + Diarization | `7860` | <img src="https://img.shields.io/badge/-Beta-F59E0B?style=flat-square" /> | [ Docs](Speech2Text%20Services/README.md) |
|  **Stable Diffusion** | AI Image Generation (AUTOMATIC1111) | `7861` | <img src="https://img.shields.io/badge/-Ready-10B981?style=flat-square" /> | [ Docs](stable-diffusion-webui/README.md) |

</div>

---

<div align="center">

##  **TÍNH NĂNG NỔI BẬT** 

</div>

<details open>
<summary><b> ChatBot Service (v2.0)</b></summary>
<br>

```mermaid
graph LR
    A[User Input] --> B{Model Selection}
    B --> C[Gemini 2.0]
    B --> D[GPT-4]
    B --> E[Qwen Local]
    C --> F[Response]
    D --> F
    E --> F
    F --> G[Image Gen?]
    G -->|Yes| H[Stable Diffusion]
    G -->|No| I[Output]
    H --> I
```

####  Tính năng chính:

| Feature | Description | Status |
|:--------|:------------|:-------|
|  **Multi-Model** | Gemini 2.0, GPT-4, DeepSeek, Qwen, BloomVN |  |
|  **Auto-File Analysis** | Upload & instant AI insights (50MB max) |  NEW v2.0 |
|  **Stop Generation** | Interrupt AI mid-response & keep output |  NEW v2.0 |
|  **Image Gen** | Stable Diffusion + LoRA + VAE |  |
|  **AI Memory** | Lưu trữ conversations & images |  |
|  **Message Versioning** | Track multiple response versions |  NEW v2.0 |
|  **Tools** | Google Search, GitHub Search |  |
|  **Export** | PDF với metadata |  |
|  **UI** | Full-screen ChatGPT-like, Dark Mode |  v2.0 |

<div align="right">

 **[Chi tiết đầy đủ ](ChatBot/README.md)** |  **Port**: `5001`

</div>

</details>

<details open>
<summary><b> Text2SQL Service  MỚI NHẤT v2.0</b></summary>
<br>

```mermaid
graph TD
    A[ Natural Language Query] --> B[ Gemini AI]
    B --> C{ Check Knowledge Base}
    C -->|Found| D[ Use Saved SQL]
    C -->|Not Found| E[ Generate New SQL]
    E --> F[ User Feedback]
    F -->|Correct| G[ Save to KB]
    F -->|Wrong| H[ Regenerate]
    D --> I[ Execute Query]
    G --> I
    I --> J[ Display Results]
```

####  Tính năng chính:

<table>
<tr>
<td width="50%">

** ChatBot v2.0 Features:**
-  Auto-File Analysis (up to 50MB)
-  Stop Generation mid-response
-  Message History Versioning
-  Full-screen ChatGPT-like UI
-  Smart Storage Management

</td>
<td width="50%">

** Text2SQL v2.0 Features:**
-  Vietnamese + English Support
-  Multi-DB Support
-  AI Learning System
-  Deep Thinking Mode
-  Deploy FREE on Render.com

</td>
</tr>
</table>

<div align="right">

 **[Chi tiết đầy đủ ](Text2SQL%20Services/README.md)** |  **Port**: `5002`  
 **[Deployment Guide ](Text2SQL%20Services/README.md#-deployment)**

</div>

</details>

<details>
<summary><b> Speech2Text Service (v3.6.0+)</b></summary>
<br>

####  Công nghệ:

```
 Audio Input   Whisper + PhoWhisper   Diarization   Qwen Enhancement   Output
```

| Feature | Technology | Accuracy |
|:--------|:-----------|:---------|
|  **Transcription** | Whisper + PhoWhisper Fusion | 98%+ |
|  **Diarization** | pyannote.audio 3.1 | 95-98% |
|  **Vietnamese** | Fine-tuned models | 98%+ |
|  **Enhancement** | Qwen LLM | High |

** Supported Formats:** MP3, WAV, M4A, FLAC

<div align="right">

 **[Chi tiết đầy đủ ](Speech2Text%20Services/README.md)** |  **Port**: `7860`

</div>

</details>

<details>
<summary><b> Stable Diffusion WebUI</b></summary>
<br>

> **Based on:** [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui)  
> **Customized** for optimized performance 

####  Capabilities:

<table>
<tr>
<td width="33%">

** Generation**
- Text-to-Image
- Image-to-Image
- Inpainting
- Outpainting

</td>
<td width="33%">

** Advanced**
- LoRA Models
- VAE Support
- ControlNet
- Textual Inversion

</td>
<td width="33%">

** Integration**
- RESTful API
- ChatBot Integration
- CUDA 12.1 Optimized
- xformers Support

</td>
</tr>
</table>

<div align="right">

 **[Chi tiết đầy đủ ](stable-diffusion-webui/README.md)** |  **Port**: `7861`  
 **[Original Project ](https://github.com/AUTOMATIC1111/stable-diffusion-webui)**

</div>

</details>

---

<div align="center">

##  **QUICK START**

</div>

<table>
<tr>
<td width="50%">

### 1 **Text2SQL** (Recommended! )

```bash
cd "Text2SQL Services"
python -m venv Text2SQL
.\Text2SQL\Scripts\activate
pip install -r requirements.txt
# Setup .env with GEMINI_API_KEY_1
python app_simple.py
```

<div align="center">

 ** http://localhost:5002**

[![Open](https://img.shields.io/badge/-Docs-3B82F6?style=for-the-badge)](Text2SQL%20Services/README.md)

</div>

</td>
<td width="50%">

### 2 **ChatBot**

```bash
cd ChatBot
python -m venv venv_chatbot
.\venv_chatbot\Scripts\activate
pip install -r requirements.txt
# Setup .env with API keys
python app.py
```

<div align="center">

 ** http://localhost:5001**

[![Open](https://img.shields.io/badge/-Docs-8B5CF6?style=for-the-badge)](ChatBot/README.md)

</div>

</td>
</tr>
<tr>
<td width="50%">

### 3 **Speech2Text**

```bash
cd "Speech2Text Services"
.\scripts\fix_dependencies.bat
# Optional: Setup HF_TOKEN
.\start_webui.bat
```

<div align="center">

 ** http://localhost:7860**

[![Open](https://img.shields.io/badge/-Docs-EF4444?style=for-the-badge)](Speech2Text%20Services/SETUP_FINAL.md)

</div>

</td>
<td width="50%">

### 4 **Stable Diffusion**

```bash
cd stable-diffusion-webui
.\webui.bat
```

<div align="center">

 ** http://localhost:7861**

[![Open](https://img.shields.io/badge/-Docs-EC4899?style=for-the-badge)](stable-diffusion-webui/README.md)

</div>

</td>
</tr>
</table>

---

<div align="center">

##  **CẤU TRÚC DỰ ÁN**

</div>

```
 AI-Assistant/

  ChatBot/                     ChatBot Service (v2.0)
     app.py                   Main application
     requirements.txt         Dependencies
     src/                     Source code
     templates/               HTML templates
     static/                  CSS, JS, images
     Storage/                 Conversations & images

  Text2SQL Services/           Text2SQL Service (v2.0) 
     app_simple.py            Main application
     requirements.txt         Dependencies
     src/                     Source code
     config/                  Configurations
     data/                    Knowledge base & prompts

  Speech2Text Services/        Speech2Text Service (v3.6)
     app/                     Web UI application
     src/                     Core processing
     scripts/                 Setup scripts
     requirements.txt         Dependencies

  stable-diffusion-webui/      Stable Diffusion WebUI
     webui.bat                Launch script
     launch.py                Main launcher
     modules/                 Core modules
     extensions/              Extensions

  config/                      Global configurations
  docs/                        Documentation
  examples/                    Code examples
  README.md                    This file
```

---

<div align="center">

##  **YÊU CẦU HỆ THỐNG**

</div>

<table>
<tr>
<td width="50%">

###  **Phần Cứng**

| Component | Minimum | Recommended |
|:----------|:--------|:------------|
|  **CPU** | 4 cores | 8+ cores |
|  **RAM** | 8 GB | 16+ GB |
|  **GPU** | Optional | NVIDIA RTX 3060+ (6GB+) |
|  **Storage** | 20 GB | 50+ GB SSD |

</td>
<td width="50%">

###  **Phần Mềm**

| Software | Version |
|:---------|:--------|
|  **OS** | Windows 10/11, Linux, macOS 11+ |
|  **Python** | 3.10, 3.11 (recommended: 3.10) |
|  **CUDA** | 12.1+ (for NVIDIA GPU) |
|  **Git** | Latest version |

</td>
</tr>
</table>

<div align="center">

###  **API Keys** (Tùy chọn theo service)

[![Gemini](https://img.shields.io/badge/-Gemini_API-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![OpenAI](https://img.shields.io/badge/-OpenAI_API-412991?style=for-the-badge&logo=openai&logoColor=white)](https://platform.openai.com)
[![HuggingFace](https://img.shields.io/badge/-HuggingFace-FFD21E?style=for-the-badge&logo=huggingface&logoColor=black)](https://huggingface.co)

</div>

---

<div align="center">

##  **TÀI LIỆU**

</div>

<table>
<tr>
<td width="25%" align="center">

###  ChatBot

[![Docs](https://img.shields.io/badge/-Documentation-8B5CF6?style=for-the-badge)](ChatBot/README.md)

Multi-model AI với Image Generation

</td>
<td width="25%" align="center">

###  Text2SQL

[![Docs](https://img.shields.io/badge/-Documentation-3B82F6?style=for-the-badge)](Text2SQL%20Services/README.md)

Natural Language to SQL

</td>
<td width="25%" align="center">

###  Speech2Text

[![Docs](https://img.shields.io/badge/-Documentation-EF4444?style=for-the-badge)](Speech2Text%20Services/README.md)

Vietnamese Transcription

</td>
<td width="25%" align="center">

###  Stable Diffusion

[![Docs](https://img.shields.io/badge/-Documentation-EC4899?style=for-the-badge)](stable-diffusion-webui/README.md)

AI Image Generation

</td>
</tr>
</table>

---

<div align="center">

##  **USE CASES**

</div>

<table>
<tr>
<td width="50%">

###  **Business**
-  Business Intelligence Dashboards
-  Database Query Automation
-  Data Analysis without SQL
-  Customer Support Automation

</td>
<td width="50%">

###  **Education & Research**
-  Meeting Transcription
-  Vietnamese Podcast Processing
-  Interview Documentation
-  Multi-speaker Content Analysis

</td>
</tr>
<tr>
<td width="50%">

###  **Creative**
-  Content Creation for Social Media
-  Concept Art Generation
-  Product Visualization
-  Creative Design Assistance

</td>
<td width="50%">

###  **Personal**
-  Personal AI Assistant with File Analysis
-  Auto-analyze documents & code
-  Content Creation with Images
-  Interactive Conversations with Stop Control
-  Smart Storage Management

</td>
</tr>
</table>

---

<div align="center">

##  **WHAT'S NEW IN v2.0**

</div>

<table>
<tr>
<td width="50%">

###  **ChatBot v2.0** (Nov 2025)

** Auto-File Analysis**
```
Upload → AI analyzes instantly
No need to type questions!
```

** Stop Generation**
```
Stop button → Keep partial response
Continue from there
```

** Full-Screen UI**
```
ChatGPT-like experience
100vh layout, better visibility
```

</td>
<td width="50%">

###  **Key Improvements**

-  File upload up to **50MB**
-  Image compression (1200px max)
-  Message history versioning
-  Smart storage with auto-cleanup
-  Enhanced chat item visibility
-  GitHub badge integration
-  ES6 modular architecture
-  Performance optimizations

 **[Full Changelog](ChatBot/CHANGELOG.md)**

</td>
</tr>
</table>

---

<div align="center">

##  **CONTRIBUTING**

![Contributions Welcome](https://img.shields.io/badge/Contributions-Welcome-10B981?style=for-the-badge)

</div>

```mermaid
graph LR
    A[ Fork Repo] --> B[ Create Branch]
    B --> C[ Make Changes]
    C --> D[ Commit]
    D --> E[ Push]
    E --> F[ Pull Request]
    F --> G[ Merge]
```

<div align="center">

**Làm theo các bước sau:**

1.  **Fork** repository này
2.  Tạo branch mới (`git checkout -b feature/AmazingFeature`)
3.  Code your magic 
4.  Commit (`git commit -m ''Add some AmazingFeature''`)
5.  Push (`git push origin feature/AmazingFeature`)
6.  Mở **Pull Request**

</div>

---

<div align="center">

##  **LICENSE**

[![MIT License](https://img.shields.io/badge/License-MIT-10B981?style=for-the-badge&logo=opensourceinitiative&logoColor=white)](LICENSE)

Dự án này được phân phối dưới giấy phép **MIT License**

</div>

---

<div align="center">

##  **AUTHORS & CONTRIBUTORS**

</div>

<table>
<tr>
<td align="center" width="50%">

<img src="https://github.com/SkastVnT.png" width="120" height="120" style="border-radius: 50%; border: 3px solid #6366F1;" />

### **SkastVnT**

[![GitHub](https://img.shields.io/badge/GitHub-SkastVnT-181717?style=for-the-badge&logo=github)](https://github.com/SkastVnT)
[![Email](https://img.shields.io/badge/Email-Contact-EA4335?style=for-the-badge&logo=gmail&logoColor=white)](mailto:your-email@example.com)

**Solo Developer • AI Enthusiast • Full-Stack Engineer**

*Developed with late nights, lots of coffee ☕, and a passion for AI* 

</td>
<td align="center" width="50%">

<img src="https://github.com/sug1omyo.png" width="120" height="120" style="border-radius: 50%; border: 3px solid #10B981;" />

### **sug1omyo**

[![GitHub](https://img.shields.io/badge/GitHub-sug1omyo-181717?style=for-the-badge&logo=github)](https://github.com/sug1omyo)

**Fresher Software Engineer**

*Collaborator & Contributor* 

</td>
</tr>
</table>

<div align="center">

---

<div align="center">

##  **ACKNOWLEDGMENTS**

Cảm ơn các công nghệ và thư viện tuyệt vời:

[![AUTOMATIC1111](https://img.shields.io/badge/AUTOMATIC1111-Stable_Diffusion_WebUI-EC4899?style=for-the-badge&logo=github)](https://github.com/AUTOMATIC1111/stable-diffusion-webui)
[![Google Gemini](https://img.shields.io/badge/Google-Gemini_API-4285F4?style=for-the-badge&logo=google&logoColor=white)](https://ai.google.dev)
[![OpenAI](https://img.shields.io/badge/OpenAI-GPT_Models-412991?style=for-the-badge&logo=openai&logoColor=white)](https://openai.com)
[![Hugging Face](https://img.shields.io/badge/-Hugging_Face-FFD21E?style=for-the-badge&logoColor=black)](https://huggingface.co)

</div>

---

<div align="center">

## 🎖️ **MILESTONES & ACHIEVEMENTS** 🎖️

<table>
<tr>
<td align="center" width="25%">
<img src="https://img.shields.io/badge/⭐-2_Stars-FFD700?style=for-the-badge&logo=github&logoColor=white" />
<br/>
<sub><b>Nov 3, 2025</b></sub>
<br/>
<sub>🎉 First Milestone!</sub>
</td>
<td align="center" width="25%">
<img src="https://img.shields.io/badge/🔱-4_Services-6366F1?style=for-the-badge" />
<br/>
<sub><b>Production Ready</b></sub>
<br/>
<sub>ChatBot • Text2SQL • Speech2Text • SD</sub>
</td>
<td align="center" width="25%">
<img src="https://img.shields.io/badge/👥-2_Contributors-10B981?style=for-the-badge&logo=github&logoColor=white" />
<br/>
<sub><b>Team Growing</b></sub>
<br/>
<sub>SkastVnT • sug1omyo</sub>
</td>
<td align="center" width="25%">
<img src="https://img.shields.io/badge/📦-Open_Source-EC4899?style=for-the-badge&logo=opensourceinitiative&logoColor=white" />
<br/>
<sub><b>MIT Licensed</b></sub>
<br/>
<sub>Free & Open to All</sub>
</td>
</tr>
</table>

### 🎯 **Next Milestones:**
- 🎯 **5 Stars** - Add demo video
- 🎯 **10 Stars** - Release v2.0 with new features
- 🎯 **25 Stars** - Community showcase section
- 🎯 **50 Stars** - Docker support & Easy deployment
- 🎯 **100 Stars** - 🎊 Special celebration!

</div>

---

<div align="center">

##  **STATISTICS**

![GitHub repo size](https://img.shields.io/github/repo-size/SkastVnT/AI-Assistant?style=for-the-badge&logo=github)
![GitHub code size](https://img.shields.io/github/languages/code-size/SkastVnT/AI-Assistant?style=for-the-badge&logo=github)
![Lines of code](https://img.shields.io/tokei/lines/github/SkastVnT/AI-Assistant?style=for-the-badge&logo=github)
![GitHub last commit](https://img.shields.io/github/last-commit/SkastVnT/AI-Assistant?style=for-the-badge&logo=github)

</div>

---

<div align="center">

##  **STAR HISTORY**

[![Star History Chart](https://api.star-history.com/svg?repos=SkastVnT/AI-Assistant&type=Date)](https://star-history.com/#SkastVnT/AI-Assistant&Date)

</div>

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=170&section=footer&text=Thank%20You!&fontSize=50&fontColor=fff&animation=twinkling&fontAlignY=72" width="100%" />

###  **Nếu project này hữu ích, đừng quên cho một !** 

<img src="https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&duration=2000&pause=1000&color=6366F1&center=true&vCenter=true&width=600&lines=Built+with+%E2%9D%A4%EF%B8%8F+and+lots+of+%E2%98%95;Solo+Project+by+SkastVnT;Thanks+for+visiting!+%F0%9F%91%8B" alt="Footer Typing SVG" />

**Made with  by [SkastVnT](https://github.com/SkastVnT)**

* 2025 SkastVnT. All rights reserved.*

</div>