# Virtual Environment Setup Guide
# AI-Assistant Project - All Services

## Tổng Quan

Project này bao gồm 6 dịch vụ chính, mỗi dịch vụ có môi trường ảo riêng:

| Dịch vụ | Virtual Environment | PyTorch Version | Đặc điểm |
|---------|-------------------|-----------------|----------|
| **ChatBot** | `venv_chatbot` | 2.4.0 + CUDA 11.8 | Local LLMs (Qwen, BloomVN) |
| **Stable Diffusion** | `venv_sd` | 2.0.1 + CUDA 11.8 | Image Generation |
| **Document Intelligence** | `venv_dis` | N/A | PaddleOCR + Gemini |
| **Text2SQL** | `venv_text2sql` | N/A | Gemini API + Databases |
| **Speech2Text** | `venv_s2t` | 2.0.1 + CUDA 11.8 | Whisper + PhoWhisper |
| **RAG Services** | `venv_rag` | N/A | LangChain + ChromaDB |

## Setup Tất Cả Các Dịch Vụ (Tự Động)

Chạy script tổng hợp để setup 6 virtual environments:

```batch
cd i:\AI-Assistant\scripts\startup
setup_all_venvs.bat
```

**Thời gian:** 30-60 phút (tùy tốc độ mạng)

## Setup Từng Dịch Vụ Riêng Lẻ

### 1. ChatBot Service

```batch
cd i:\AI-Assistant\ChatBot
scripts\setup_venv_chatbot.bat
```

**Dependencies:**
- PyTorch 2.4.0 + CUDA 11.8
- Transformers 4.40.0+
- xformers 0.0.27
- Local Models: Qwen, BloomVN

**Activate:**
```batch
cd i:\AI-Assistant\ChatBot
venv_chatbot\Scripts\activate.bat
python app.py
```

### 2. Stable Diffusion

```batch
cd i:\AI-Assistant\stable-diffusion-webui
setup_venv_sd.bat
```

**Dependencies:**
- PyTorch 2.0.1 + CUDA 11.8
- xformers 0.0.20
- Stable Diffusion models

**Activate:**
```batch
cd i:\AI-Assistant\stable-diffusion-webui
venv_sd\Scripts\activate.bat
python webui.py --api --xformers
```

### 3. Document Intelligence Service

```batch
cd "i:\AI-Assistant\Document Intelligence Service"
scripts\setup_venv_dis.bat
```

**Dependencies:**
- PaddleOCR 2.7.3
- PaddlePaddle 2.6.1
- Google Generative AI 0.3.2
- PyMuPDF (PDF processing)

**Activate:**
```batch
cd "i:\AI-Assistant\Document Intelligence Service"
venv_dis\Scripts\activate.bat
python app.py
```

### 4. Text2SQL Services

```batch
cd "i:\AI-Assistant\Text2SQL Services"
scripts\setup_venv_text2sql.bat
```

**Dependencies:**
- Flask 3.0.0+
- Google Generative AI 0.8.0+
- ClickHouse Connect
- PyMongo

**Activate:**
```batch
cd "i:\AI-Assistant\Text2SQL Services"
venv_text2sql\Scripts\activate.bat
python app.py
```

### 5. Speech2Text Services

```batch
cd "i:\AI-Assistant\Speech2Text Services"
scripts\setup_venv_s2t.bat
```

**Dependencies:**
- PyTorch 2.0.1 + CUDA 11.8
- Faster-Whisper 1.0.3
- Transformers 4.40.0
- Pyannote.audio 3.1.1

**Activate:**
```batch
cd "i:\AI-Assistant\Speech2Text Services"
venv_s2t\Scripts\activate.bat
python app.py
```

### 6. RAG Services

```batch
cd "i:\AI-Assistant\RAG Services"
scripts\setup_venv_rag.bat
```

**Dependencies:**
- LangChain 0.1.0+
- ChromaDB 0.4.0+
- Sentence-Transformers 2.2.0+
- Google Generative AI

**Activate:**
```batch
cd "i:\AI-Assistant\RAG Services"
venv_rag\Scripts\activate.bat
```

## Cấu Trúc Thư Mục

```
i:\AI-Assistant\
├── scripts\
│   └── startup\
│       └── setup_all_venvs.bat          # Setup tất cả
├── ChatBot\
│   ├── venv_chatbot\                    # Virtual env
│   ├── scripts\
│   │   └── setup_venv_chatbot.bat       # Setup script
│   └── requirements.txt
├── stable-diffusion-webui\
│   ├── venv_sd\                         # Virtual env
│   ├── setup_venv_sd.bat                # Setup script
│   └── requirements.txt
├── Document Intelligence Service\
│   ├── venv_dis\                        # Virtual env
│   ├── scripts\
│   │   └── setup_venv_dis.bat           # Setup script
│   └── requirements.txt
├── Text2SQL Services\
│   ├── venv_text2sql\                   # Virtual env
│   ├── scripts\
│   │   └── setup_venv_text2sql.bat      # Setup script
│   └── requirements.txt
├── Speech2Text Services\
│   ├── venv_s2t\                        # Virtual env
│   ├── scripts\
│   │   └── setup_venv_s2t.bat           # Setup script
│   └── requirements.txt
└── RAG Services\
    ├── venv_rag\                        # Virtual env
    ├── scripts\
    │   └── setup_venv_rag.bat           # Setup script
    └── (dependencies in code)
```

## Yêu Cầu Hệ Thống

### Phần Cứng
- **CPU:** Intel/AMD 8+ cores (khuyến nghị)
- **RAM:** 16GB tối thiểu, 32GB khuyến nghị
- **GPU:** NVIDIA GPU với CUDA 11.8
  - Minimum 6GB VRAM (ChatBot, Speech2Text)
  - Recommended 8GB+ VRAM (Stable Diffusion)
- **Ổ cứng:** 100GB+ dung lượng trống

### Phần Mềm
- **OS:** Windows 10/11
- **Python:** 3.10.6
- **CUDA:** 11.8
- **Git:** Latest version

## Ports Mặc Định

| Service | Port | URL |
|---------|------|-----|
| ChatBot | 5000 | http://localhost:5000 |
| Text2SQL | 5001 | http://localhost:5001 |
| Speech2Text | 5002 | http://localhost:5002 |
| Document Intelligence | 5003 | http://localhost:5003 |
| Stable Diffusion | 7860 | http://localhost:7860 |
| RAG Services | 5004 | http://localhost:5004 |

## Xử Lý Lỗi Thường Gặp

### 1. CUDA Not Available
```batch
# Kiểm tra CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Nếu False, cài đặt lại PyTorch với CUDA
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
```

### 2. Out of Memory (GPU)
- Giảm batch size trong config
- Sử dụng 8-bit quantization cho models
- Đóng các services không dùng

### 3. Module Not Found
```batch
# Activate venv trước
cd <service-folder>
<venv-name>\Scripts\activate.bat

# Cài lại dependencies
pip install -r requirements.txt
```

### 4. Port Already in Use
```batch
# Tìm process đang dùng port
netstat -ano | findstr :5000

# Kill process
taskkill /PID <process-id> /F
```

## Kiểm Tra Cài Đặt

Sau khi setup, kiểm tra từng service:

```batch
# ChatBot
cd i:\AI-Assistant\ChatBot
venv_chatbot\Scripts\activate.bat
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}'); import transformers; print('OK')"

# Stable Diffusion
cd i:\AI-Assistant\stable-diffusion-webui
venv_sd\Scripts\activate.bat
python -c "import torch; print(f'PyTorch: {torch.__version__}')"

# Document Intelligence
cd "i:\AI-Assistant\Document Intelligence Service"
venv_dis\Scripts\activate.bat
python -c "import paddleocr; print('PaddleOCR: OK')"

# Text2SQL
cd "i:\AI-Assistant\Text2SQL Services"
venv_text2sql\Scripts\activate.bat
python -c "import flask; import google.generativeai; print('OK')"

# Speech2Text
cd "i:\AI-Assistant\Speech2Text Services"
venv_s2t\Scripts\activate.bat
python -c "import torch; import transformers; print('OK')"

# RAG Services
cd "i:\AI-Assistant\RAG Services"
venv_rag\Scripts\activate.bat
python -c "import langchain; print('LangChain: OK')"
```

## Ghi Chú

- **Isolation:** Mỗi service có virtual environment riêng để tránh xung đột dependencies
- **PyTorch Versions:** ChatBot (2.4.0) và Speech2Text (2.0.1) dùng phiên bản khác nhau
- **CUDA:** Tất cả services AI đều yêu cầu CUDA 11.8
- **API Keys:** Một số services cần API keys (Gemini, HuggingFace) trong file `.env`

## Liên Hệ & Hỗ Trợ

- **Repository:** https://github.com/SkastVnT/AI-Assistant
- **Issues:** https://github.com/SkastVnT/AI-Assistant/issues
- **Docs:** `i:\AI-Assistant\docs\`
