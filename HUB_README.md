# AI Assistant Hub

🚀 **Gateway tổng hợp cho các dịch vụ AI**

Một nền tảng tích hợp đa dịch vụ AI mạnh mẽ, bao gồm ChatBot, Speech-to-Text và Text-to-SQL.

---

## 📦 Các Services

### 1. 🤖 AI ChatBot
**Port:** 5000  
**Mô tả:** Trợ lý AI hỗ trợ tâm lý, tâm sự và giải pháp đời sống

**Tính năng:**
- Hỗ trợ 3 mô hình AI: Gemini, GPT-3.5, DeepSeek
- Chat về tâm lý, tâm sự
- Tư vấn giải pháp đời sống
- Trò chuyện vui vẻ, thân thiện

**Khởi động:**
```bash
cd ChatBot
pip install -r requirements.txt
python app.py
```

---

### 2. 🎤 Speech to Text
**Port:** 5001  
**Mô tả:** Chuyển đổi giọng nói thành văn bản với AI

**Tính năng:**
- Nhận dạng giọng nói tiếng Việt
- Hỗ trợ nhiều định dạng audio
- Phân tách người nói (Diarization)
- Xuất kết quả văn bản

**Khởi động:**
```bash
cd "Speech2Text Services/app"
pip install -r ../requirements.txt
python web_ui.py --port 5001
```

---

### 3. 💾 Text to SQL
**Port:** 5002  
**Mô tả:** Chuyển đổi ngôn ngữ tự nhiên thành câu truy vấn SQL

**Tính năng:**
- Tạo câu SQL từ ngôn ngữ tự nhiên
- Hỗ trợ nhiều loại database
- Tích hợp Gemini AI
- Lưu trữ và học từ lịch sử

**Khởi động:**
```bash
cd "Text2SQL Services"
pip install -r requirements.txt
python app.py --port 5002
```

---

## 🚀 Cài đặt và Sử dụng

### Bước 1: Cài đặt Hub
```bash
# Tại thư mục gốc
pip install -r requirements.txt
```

### Bước 2: Cấu hình API Keys
Tạo/cập nhật file `.env` tại thư mục gốc và các services:

```env
# API Keys cho các services
OPENAI_API_KEY=your_openai_key
DEEPSEEK_API_KEY=your_deepseek_key
GEMINI_API_KEY_1=your_gemini_key
HF_API_TOKEN=your_huggingface_token
FLASK_SECRET_KEY=your_secret_key
```

### Bước 3: Khởi động Hub Gateway
```bash
python hub.py
```

Gateway sẽ chạy tại: http://localhost:8080

### Bước 4: Khởi động các Services (riêng lẻ)

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

### Bước 5: Truy cập
Mở trình duyệt và truy cập: **http://localhost:8080**

---

## 🎯 Sử dụng

1. **Truy cập Hub Gateway** tại http://localhost:8080
2. **Chọn service** bạn muốn sử dụng từ giao diện
3. **Click vào card** để mở service trong tab mới
4. **Tương tác** với service theo nhu cầu

---

## 🏗️ Kiến trúc

```
AI Assistant Hub (Port 8080)
│
├── ChatBot Service (Port 5000)
│   ├── Gemini AI
│   ├── OpenAI GPT-3.5
│   └── DeepSeek
│
├── Speech2Text Service (Port 5001)
│   ├── Whisper
│   ├── PhoWhisper
│   └── Speaker Diarization
│
└── Text2SQL Service (Port 5002)
    ├── Gemini AI
    ├── SQLCoder
    └── Memory System
```

---

## ⚙️ Cấu hình Services

### ChatBot
```bash
cd ChatBot
cp .env.example .env
# Chỉnh sửa .env với API keys của bạn
```

### Speech2Text
```bash
cd "Speech2Text Services"
cp .env.example .env
# Chỉnh sửa .env với HF token và các keys khác
```

### Text2SQL
```bash
cd "Text2SQL Services"
cp .env.example .env
# Chỉnh sửa .env với Gemini API key
```

---

## 📋 Yêu cầu hệ thống

### Tối thiểu:
- Python 3.8+
- 8GB RAM
- 10GB ổ cứng trống

### Khuyến nghị:
- Python 3.10+
- 16GB RAM
- GPU (cho Speech2Text)
- 20GB ổ cứng trống

---

## 🐛 Xử lý sự cố

### Service không khởi động?
1. Kiểm tra port đã được sử dụng chưa:
   ```bash
   # Windows
   netstat -ano | findstr :5000
   
   # Linux/Mac
   lsof -i :5000
   ```

2. Kiểm tra API keys trong file `.env`

3. Kiểm tra dependencies đã cài đầy đủ:
   ```bash
   pip install -r requirements.txt
   ```

### Lỗi kết nối giữa Hub và Services?
- Đảm bảo tất cả services đang chạy
- Kiểm tra firewall không chặn các port
- Thử truy cập trực tiếp service URLs

### Out of Memory?
- Chạy từng service một để tiết kiệm RAM
- Đóng các ứng dụng không cần thiết
- Xem xét nâng cấp RAM

---

## 🔒 Bảo mật

⚠️ **Quan trọng:**
- **KHÔNG** commit file `.env` vào Git
- **KHÔNG** chia sẻ API keys công khai
- Sử dụng `.env` riêng cho từng môi trường
- Đổi `FLASK_SECRET_KEY` thường xuyên

---

## 📝 Logs và Monitoring

Logs được lưu tại:
- Hub: `./logs/hub.log`
- ChatBot: `./ChatBot/logs/`
- Speech2Text: `./Speech2Text Services/logs/`
- Text2SQL: `./Text2SQL Services/logs/`

---

## 🤝 Đóng góp

Contributions are welcome! Please feel free to submit a Pull Request.

---

## 📄 License

MIT License - Xem file LICENSE để biết thêm chi tiết

---

## 👥 Team

Made with ❤️ by AI Assistant Team

---

## 📞 Liên hệ & Hỗ trợ

- GitHub: https://github.com/SkastVnT/AI-Assistant
- Issues: https://github.com/SkastVnT/AI-Assistant/issues

---

## 🎉 Tính năng sắp tới

- [ ] Dashboard monitoring real-time
- [ ] User authentication
- [ ] Service health checks tự động
- [ ] Docker compose deployment
- [ ] API Gateway với rate limiting
- [ ] Logging và analytics tập trung

---

**Happy Coding! 🚀**
