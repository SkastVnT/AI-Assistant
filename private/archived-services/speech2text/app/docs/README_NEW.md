# 🎯 Speech2Text - Hệ thống chuyển đổi giọng nói thành văn bản

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CUDA 11.8](https://img.shields.io/badge/CUDA-11.8-green.svg)](https://developer.nvidia.com/cuda-downloads)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Hệ thống Speech-to-Text tiên tiến với hỗ trợ:
- ✅ **Dual Model Transcription**: Whisper + PhoWhisper
- ✅ **Speaker Diarization**: Phân biệt người nói
- ✅ **AI Enhancement**: Qwen 2.5 để cải thiện văn bản
- ✅ **Web UI**: Giao diện web thân thiện
- ✅ **Docker Support**: Deploy dễ dàng

---

## 📁 Cấu trúc Project

```
Speech2Text/
├── 📁 app/                      # Application source code
│   ├── web_ui.py               # Web UI entry point
│   ├── core/                   # Core business logic
│   ├── api/                    # API services
│   ├── config/                 # Configuration
│   ├── templates/              # HTML templates
│   └── tests/                  # Unit tests
│
├── 📁 scripts/                  # Deployment scripts
│   ├── start_webui.bat        # Khởi động Web UI
│   ├── setup.bat              # Cài đặt ban đầu
│   └── ...                    # Các scripts khác
│
├── 📁 docker/                   # Docker configuration
│   ├── docker-compose.yml     # Docker Compose config
│   ├── Dockerfile             # Docker image
│   └── README_WINDOWS.md      # Hướng dẫn Docker
│
├── 📁 tools/                    # Development tools
│   ├── test_cuda.py           # Test CUDA
│   └── system_check.py        # Kiểm tra hệ thống
│
├── 📁 docs/                     # Documentation
│   ├── QUICKSTART.md          # Hướng dẫn nhanh
│   ├── INSTALLATION.md        # Cài đặt chi tiết
│   └── ...                    # Tài liệu khác
│
├── 📁 data/                     # Data directories (gitignored)
│   ├── audio/                 # Input audio
│   ├── results/               # Output results
│   └── cache/                 # Cache
│
├── .env                        # Environment variables
├── requirements.txt            # Python dependencies
└── README.md                   # This file
```

---

## 🚀 Quick Start

### 1. Cài đặt

```bash
# Clone repository
git clone https://github.com/SkastVnT/Speech2Text.git
cd Speech2Text

# Chạy setup
.\scripts\setup.bat
```

### 2. Khởi động Web UI

```bash
.\scripts\start_webui.bat
```

Mở trình duyệt: http://localhost:5000

### 3. Hoặc dùng Docker

```bash
cd docker
.\docker-manage.bat
# Chọn option 3 (Build and start)
```

---

## 📖 Documentation

- [📚 Quickstart Guide](docs/QUICKSTART.md) - Bắt đầu nhanh
- [⚙️ Installation Guide](docs/INSTALLATION.md) - Cài đặt chi tiết
- [🐳 Docker Guide](docker/README_WINDOWS.md) - Sử dụng Docker
- [🔧 Troubleshooting](docs/TROUBLESHOOTING.md) - Xử lý lỗi

---

## 🎯 Features

### Speech Recognition
- **Whisper large-v3**: Model OpenAI cho tiếng Anh
- **PhoWhisper**: Tối ưu cho tiếng Việt
- **Dual Transcription**: Kết hợp cả 2 models

### Speaker Diarization
- **PyAnnote Audio 3.1**: Phân biệt người nói
- **Timeline Transcript**: Transcript theo timeline
- **Multi-speaker Support**: Hỗ trợ 2-5 người nói

### AI Enhancement
- **Qwen 2.5-1.5B**: Cải thiện văn bản
- **Grammar Correction**: Sửa lỗi ngữ pháp
- **Punctuation**: Thêm dấu câu

### Web UI
- **Real-time Progress**: Theo dõi tiến trình
- **File Upload**: Upload audio files
- **Download Results**: Tải kết quả

---

## 🔧 Requirements

### Hardware
- **GPU**: NVIDIA RTX 3060 trở lên (6GB+ VRAM)
- **RAM**: 16GB+ khuyến nghị
- **Storage**: 20GB+ cho models

### Software
- **OS**: Windows 10/11, Linux
- **Python**: 3.10+
- **CUDA**: 11.8
- **Docker**: (Optional) Docker Desktop for Windows

---

## 📦 Installation

### Method 1: Virtual Environment (Khuyến nghị)

```bash
# 1. Tạo virtual environment
python -m venv app\s2t

# 2. Activate
.\app\s2t\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Install PyTorch with CUDA 11.8
pip install torch==2.7.1+cu118 torchaudio==2.7.1+cu118 --index-url https://download.pytorch.org/whl/cu118

# 5. Install pyannote.audio
pip install pyannote.audio==3.1.1

# 6. Configure environment
copy app\config\.env.example app\config\.env
# Edit .env và thêm HF_TOKEN
```

### Method 2: Docker

```bash
cd docker
.\docker-manage.bat
# Chọn option 3
```

---

## 🎮 Usage

### Web UI

```bash
.\scripts\start_webui.bat
```

1. Mở http://localhost:5000
2. Upload file audio (mp3, wav, m4a, flac)
3. Chọn options (speaker diarization, dual model, etc.)
4. Click "Start Processing"
5. Download results

### CLI

```bash
python app\core\run_with_diarization.py --audio path\to\audio.mp3
```

### API

```bash
# Start API server
python app\api\main.py

# Test endpoint
curl http://localhost:8000/api/v1/health
```

---

## 🔑 Configuration

### Environment Variables (.env)

```env
# HuggingFace Token (Required)
HF_TOKEN=your_token_here
HF_API_TOKEN=your_token_here

# API Keys (Optional)
OPENAI_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
DEEPSEEK_API_KEY=your_key_here
```

### Model Configuration

Models sẽ được tự động download vào `app\models\` hoặc cache HuggingFace.

---

## 🐛 Troubleshooting

### GPU Not Detected

```bash
# Check CUDA
python -c "import torch; print(torch.cuda.is_available())"

# Reinstall PyTorch with CUDA
pip install torch==2.7.1+cu118 --index-url https://download.pytorch.org/whl/cu118
```

### Out of Memory

Giảm batch size hoặc sử dụng model nhỏ hơn trong config.

### cuDNN Error

Xem [docs/TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)

---

## 📊 Performance

### Speed (RTX 3060 Ti, 8GB VRAM)
- Whisper large-v3: ~0.3x realtime (CPU), ~3x realtime (GPU)
- PhoWhisper large: ~5x realtime (GPU)
- Qwen enhancement: ~2s per 1000 chars

### Accuracy
- Whisper: WER ~5-10% (English)
- PhoWhisper: WER ~8-15% (Vietnamese)

---

## 🤝 Contributing

Contributions are welcome! See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

---

## 📝 License

MIT License - see LICENSE file

---

## 🙏 Acknowledgments

- [OpenAI Whisper](https://github.com/openai/whisper)
- [vinai/PhoWhisper](https://huggingface.co/vinai/PhoWhisper-large)
- [Qwen/Qwen2.5](https://huggingface.co/Qwen/Qwen2.5-1.5B-Instruct)
- [PyAnnote Audio](https://github.com/pyannote/pyannote-audio)

---

## 📧 Contact

- **Author**: SkastVnT
- **Email**: your.email@example.com
- **GitHub**: https://github.com/SkastVnT/Speech2Text

---

**⭐ If you find this project useful, please give it a star!**
