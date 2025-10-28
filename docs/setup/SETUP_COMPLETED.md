# ✅ SETUP HOÀN TẤT - HƯỚNG DẪN SỬ DỤNG

## 🎉 Đã cài đặt thành công:

### ✅ ChatBot Service
- Flask==3.0.0
- openai (latest SDK v2.6.1)
- google-generativeai==0.8.5
- python-dotenv==1.0.0

### ✅ Hub Gateway
- Flask==3.0.0
- flask-cors==4.0.0
- python-dotenv==1.0.0
- requests

### ✅ Python Environment
- Python 3.10.11 ✓

---

## 🔧 CÁC BƯỚC TIẾP THEO:

### 1️⃣ Tạo file `.env` với API keys của bạn

**Root folder** (`i:\AI-Assistant\.env`):
```
HUB_PORT=3000
FLASK_ENV=development
CHATBOT_PORT=5000
SPEECH2TEXT_PORT=5001
TEXT2SQL_PORT=5002

OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
DEEPSEEK_API_KEY=sk-YOUR_KEY_HERE
GEMINI_API_KEY_1=AIzaSy_YOUR_KEY_HERE
GEMINI_API_KEY_2=AIzaSy_YOUR_KEY_HERE
HUGGINGFACE_TOKEN=hf_YOUR_TOKEN_HERE
```

**ChatBot folder** (`i:\AI-Assistant\ChatBot\.env`):
```
OPENAI_API_KEY=sk-proj-YOUR_KEY_HERE
DEEPSEEK_API_KEY=sk-YOUR_KEY_HERE
GEMINI_API_KEY_1=AIzaSy_YOUR_KEY_HERE
GEMINI_API_KEY_2=AIzaSy_YOUR_KEY_HERE
```

💡 **Lưu ý**: File `.env.example` đã được tạo sẵn. Copy và đổi tên thành `.env`, sau đó thay thế YOUR_KEY_HERE bằng API keys thật của bạn.

---

### 2️⃣ Khởi động ChatBot (Cách đơn giản nhất)

Mở PowerShell và chạy:

```powershell
cd i:\AI-Assistant\ChatBot
python app.py
```

Sau đó mở trình duyệt: **http://127.0.0.1:5000**

---

### 3️⃣ Khởi động đầy đủ (Hub Gateway + ChatBot)

**Terminal 1 - Hub Gateway:**
```powershell
cd i:\AI-Assistant
python hub.py
```

**Terminal 2 - ChatBot:**
```powershell
cd i:\AI-Assistant\ChatBot
python app.py
```

---

## 🚀 TÍNH NĂNG CHATBOT

✅ **Chat History Sidebar** - Lưu và quản lý các cuộc trò chuyện
✅ **Auto-Generate Title** - Tự động đặt tên chat bằng Gemini
✅ **Dark Mode** - Chế độ tối bảo vệ mắt
✅ **Deep Thinking Mode** - Suy luận sâu cho câu trả lời chi tiết
✅ **Copy Buttons** - Copy tin nhắn và bảng dễ dàng
✅ **Download Chat** - Xuất lịch sử chat ra file .txt
✅ **File Upload** - Upload và hỏi về nội dung file
✅ **Programming Mode** - Context tối ưu cho lập trình

---

## 🔑 API KEYS - ĐỀ XUẤT

### OpenAI (GPT-4o-mini)
- Cost: $0.15 input / $0.60 output per 1M tokens
- Link: https://platform.openai.com/api-keys

### DeepSeek (deepseek-chat)
- Cost: $0.14 input / $0.28 output per 1M tokens
- Link: https://platform.deepseek.com/api_keys

### Gemini (gemini-2.0-flash)
- Cost: **FREE** (60 requests/minute)
- Link: https://aistudio.google.com/apikey

### HuggingFace (Speech2Text models)
- Cost: **FREE**
- Link: https://huggingface.co/settings/tokens

---

## 🛠️ TROUBLESHOOTING

### Lỗi: "No module named 'xxx'"
```powershell
cd i:\AI-Assistant\ChatBot
pip install -r requirements.txt
```

### ChatBot không gửi được tin nhắn
1. Kiểm tra file `.env` có tồn tại và chứa API keys
2. Refresh trình duyệt (Ctrl+R)
3. Check console (F12) để xem lỗi
4. Restart Flask server

### Port đã được sử dụng
Thay đổi port trong `.env`:
```
CHATBOT_PORT=5001  # hoặc port khác
```

---

## 📝 TEST NHANH

### Test Gemini API:
```powershell
cd i:\AI-Assistant\ChatBot
python test_gemini.py
```

### Test Tools:
```powershell
cd i:\AI-Assistant\ChatBot
python test_tools.py
```

---

## 📚 TÀI LIỆU THAM KHẢO

- **USAGE_GUIDE.md** - Hướng dẫn sử dụng chi tiết
- **CHAT_HISTORY_FEATURE.md** - Tài liệu kỹ thuật Chat History
- **TOOLS_INTEGRATION_GUIDE.md** - Tích hợp Google Search & GitHub
- **SETUP_NEW_DEVICE.txt** - Hướng dẫn setup đầy đủ

---

## 🎯 QUICK START (TL;DR)

```powershell
# 1. Tạo file .env với API keys
# 2. Chạy ChatBot
cd i:\AI-Assistant\ChatBot
python app.py

# 3. Mở trình duyệt
http://127.0.0.1:5000
```

**DONE! 🎉**

---

📅 Setup completed: October 28, 2025
🔧 Python Version: 3.10.11
👨‍💻 Developer: Thanh Nguyen
