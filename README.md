# 🤖 AI Assistant - Integrated Multi-Service Platform

<div align="center">

![AI Assistant](https://img.shields.io/badge/AI-Assistant-purple?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.8+-blue?style=for-the-badge&logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?style=for-the-badge&logo=flask)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Nền tảng tích hợp đa dịch vụ AI mạnh mẽ**

[Khởi động nhanh](#-khởi-động-nhanh) • [Tính năng](#-tính-năng) • [Cài đặt](#️-cài-đặt) • [Hướng dẫn](#-hướng-dẫn-sử-dụng) • [Đóng góp](#-đóng-góp)

</div>

---

## 📋 Giới thiệu

**AI Assistant Hub** là một nền tảng tổng hợp các dịch vụ AI tiên tiến, bao gồm:

- 🤖 **AI ChatBot** - Trợ lý AI đa năng với Gemini, GPT-3.5, DeepSeek
- 🎤 **Speech to Text** - Chuyển đổi giọng nói thành văn bản (tiếng Việt)
- 💾 **Text to SQL** - Tạo câu truy vấn SQL từ ngôn ngữ tự nhiên

Tất cả được kết nối qua một **Gateway Hub** với giao diện web đẹp mắt, hiện đại.

---

## ✨ Tính năng

### 🚀 AI Assistant Hub Gateway
- ✅ Giao diện web đẹp với **Tailwind CSS**
- ✅ Điều hướng tập trung đến các services
- ✅ Monitoring và health checks
- ✅ Responsive design, dark theme
- ✅ Quick start scripts

### 🤖 AI ChatBot
- ✅ 3 mô hình AI: **Gemini, GPT-3.5, DeepSeek**
- ✅ 3 chế độ: Tâm lý, Đời sống, Trò chuyện
- ✅ Lưu lịch sử conversation
- ✅ Real-time chat interface

### 🎤 Speech to Text
- ✅ Nhận dạng giọng nói **tiếng Việt**
- ✅ **Speaker Diarization** (phân tách người nói)
- ✅ Hỗ trợ nhiều format: WAV, MP3, M4A, FLAC
- ✅ WebSocket real-time updates
- ✅ PhoWhisper & Whisper models

### 💾 Text to SQL
- ✅ Tạo SQL từ ngôn ngữ tự nhiên
- ✅ **Gemini AI** powered
- ✅ Memory system - học từ lịch sử
- ✅ Hỗ trợ nhiều loại database
- ✅ Evaluation metrics

---

## 🚀 Khởi động nhanh

### Cách 1: Khởi động Hub Gateway
```bash
# Clone repository
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant

# Cài đặt dependencies
pip install -r requirements.txt

# Khởi động Hub
python hub.py
```

Truy cập: **http://localhost:3000**

### Cách 2: Khởi động tất cả services

**Windows:**
```bash
start_all.bat
```

**Linux/Mac:**
```bash
chmod +x start_all.sh
./start_all.sh
```

---

## 🏗️ Kiến trúc

```
┌─────────────────────────────────────────┐
│   AI Assistant Hub (Port 3000)          │
│   - Gateway & UI                        │
│   - Service discovery                   │
└──────────────┬──────────────────────────┘
               │
    ┌──────────┼──────────┐
    │          │          │
    ▼          ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐
│ChatBot │ │Speech  │ │Text2SQL│
│:5000   │ │:5001   │ │:5002   │
└────────┘ └────────┘ └────────┘
```

---

## 🛠️ Cài đặt

### Yêu cầu hệ thống
- **Python:** 3.8+
- **RAM:** 8GB (tối thiểu), 16GB (khuyến nghị)
- **Storage:** 10GB+ free space
- **GPU:** Optional (tốt cho Speech2Text)

### Bước 1: Clone repository
```bash
git clone https://github.com/SkastVnT/AI-Assistant.git
cd AI-Assistant
```

### Bước 2: Cài đặt dependencies

**Hub:**
```bash
pip install -r requirements.txt
```

**ChatBot:**
```bash
cd ChatBot
pip install -r requirements.txt
cd ..
```

**Speech2Text:**
```bash
cd "Speech2Text Services"
pip install -r requirements.txt
cd ..
```

**Text2SQL:**
```bash
cd "Text2SQL Services"
pip install -r requirements.txt
cd ..
```

### Bước 3: Cấu hình API Keys

Tạo file `.env` tại thư mục gốc:

```env
# OpenAI
OPENAI_API_KEY=sk-...

# DeepSeek
DEEPSEEK_API_KEY=sk-...

# Google Gemini
GEMINI_API_KEY_1=AIza...
GEMINI_API_KEY_2=AIza...

# HuggingFace
HF_API_TOKEN=hf_...

# Flask
FLASK_SECRET_KEY=your-secret-key
```

Copy `.env` vào các thư mục services tương ứng.

---

## 📖 Hướng dẫn sử dụng

### Khởi động Hub Gateway

```bash
python hub.py
```

Truy cập **http://localhost:3000** để xem dashboard và chọn service.

### Khởi động từng service riêng

**Terminal 1 - ChatBot:**
```bash
cd ChatBot
python app.py
```

**Terminal 2 - Speech2Text:**
```bash
cd "Speech2Text Services/app"
python web_ui.py --port 5001
```

**Terminal 3 - Text2SQL:**
```bash
cd "Text2SQL Services"
python app.py --port 5002
```

### Sử dụng services

1. Mở **http://localhost:3000**
2. Click vào card của service bạn muốn dùng
3. Service sẽ mở trong tab mới
4. Bắt đầu sử dụng!

---

## 📚 Documentation

### Quick Start Guides
- � [Quick Start](QUICKSTART.md) - Hướng dẫn khởi động nhanh
- 🎯 [Quick Reference](QUICK_REFERENCE.md) - Cheat sheet & commands

### Architecture & Design
- 📘 [Hub Gateway Guide](docs/HUB_README.md) - Chi tiết về Hub Gateway
- 🏗️ [Project Structure](docs/PROJECT_STRUCTURE.md) - Cấu trúc project đầy đủ
- 🔄 [Refactoring Summary](docs/REFACTORING_SUMMARY.md) - Quá trình refactor

### Service Documentation
- 📙 [ChatBot README](ChatBot/README.md) - Hướng dẫn ChatBot service
- 📕 [Speech2Text README](Speech2Text%20Services/README.md) - Hướng dẫn Speech2Text
- 📓 [Text2SQL README](Text2SQL%20Services/README) - Hướng dẫn Text2SQL

### Project Info
- 🎉 [Mission Complete](docs/MISSION_COMPLETE.md) - Tổng kết hoàn thành

---

## 🎯 Use Cases

### ChatBot
- Tư vấn tâm lý, tâm sự
- Giải pháp đời sống, công việc
- Trò chuyện giải trí

### Speech2Text
- Phiên âm cuộc họp, hội thảo
- Chuyển đổi podcast/video thành text
- Phân tích cuộc trò chuyện

### Text2SQL
- Truy vấn database bằng ngôn ngữ tự nhiên
- Data analytics không cần SQL
- Business intelligence

---

## 🐛 Troubleshooting

### Port đã được sử dụng?
```bash
# Windows
netstat -ano | findstr :5000

# Linux/Mac
lsof -i :5000
```

### Lỗi API Key?
- Kiểm tra file `.env` có đúng format
- Verify API keys còn hoạt động
- Check quota của API keys

### Out of Memory?
- Chạy từng service một
- Đóng các app khác
- Nâng cấp RAM

Xem thêm trong [HUB_README.md](HUB_README.md)

---

## 🔒 Security

⚠️ **QUAN TRỌNG:**
- **KHÔNG** commit file `.env` vào Git
- **KHÔNG** share API keys
- Sử dụng `.env` riêng cho mỗi môi trường
- Đổi `FLASK_SECRET_KEY` định kỳ

---

## 📊 Project Structure

```
AI-Assistant/
├── hub.py                      # Hub Gateway main file
├── templates/
│   └── index.html             # Hub UI (Tailwind CSS)
├── requirements.txt           # Hub dependencies
├── start_all.bat/sh          # Start all services script
├── QUICKSTART.md             # Quick start guide
├── HUB_README.md             # Hub detailed docs
│
├── ChatBot/                   # ChatBot Service
│   ├── app.py
│   ├── templates/
│   ├── requirements.txt
│   └── README.md
│
├── Speech2Text Services/      # Speech2Text Service
│   ├── app/
│   │   └── web_ui.py
│   ├── requirements.txt
│   └── README.md
│
└── Text2SQL Services/         # Text2SQL Service
    ├── app.py
    ├── requirements.txt
    └── README
```

---

## 🤝 Đóng góp

Contributions are welcome! 

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

---

## 📝 TODO

- [ ] Docker Compose deployment
- [ ] User authentication system
- [ ] Real-time service monitoring
- [ ] API Gateway with rate limiting
- [ ] Centralized logging
- [ ] Unit tests
- [ ] CI/CD pipeline
- [ ] Database integration
- [ ] WebSocket support for all services
- [ ] Multi-language support

---

## 📄 License

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
