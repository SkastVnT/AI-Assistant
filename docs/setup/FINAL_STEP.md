# 🎉 SETUP ĐÃ HOÀN TẤT 95%!

## ✅ ĐÃ CÀI ĐẶT:

### Dependencies
- ✓ Flask 3.0.0
- ✓ OpenAI (latest SDK v2.6.1)  
- ✓ Google Generative AI 0.8.5
- ✓ python-dotenv 1.0.0
- ✓ flask-cors 4.0.0
- ✓ packaging (dependency)

### Folder Structure
- ✓ ChatBot/
- ✓ ChatBot/templates/
- ✓ config/
- ✓ src/

### Scripts
- ✓ check_system.py - Kiểm tra hệ thống
- ✓ start_chatbot.bat - Khởi động nhanh
- ✓ .env.example - Mẫu cấu hình

---

## 🔧 BƯỚC CUỐI CÙNG - TẠO FILE .env:

### Bước 1: Copy file mẫu

**Windows PowerShell:**
```powershell
# Root .env (optional - chỉ cần nếu dùng Hub Gateway)
Copy-Item .env.example .env

# ChatBot .env (BẮT BUỘC)
Copy-Item ChatBot\.env.example ChatBot\.env
```

**Hoặc copy thủ công:**
- Copy `.env.example` → `.env`
- Copy `ChatBot\.env.example` → `ChatBot\.env`

---

### Bước 2: Thêm API Keys vào `ChatBot\.env`

Mở file `ChatBot\.env` và thay thế `YOUR_KEY_HERE` bằng API keys thật:

```env
OPENAI_API_KEY=sk-proj-SZNV...YOUR_REAL_KEY...
DEEPSEEK_API_KEY=sk-1f010...YOUR_REAL_KEY...
GEMINI_API_KEY_1=AIzaSyB0h_O7...YOUR_REAL_KEY...
GEMINI_API_KEY_2=AIzaSyCba...YOUR_REAL_KEY...
```

---

### Bước 3: Lấy API Keys (MIỄN PHÍ)

#### 🔹 Gemini API (Khuyến nghị - FREE unlimited)
1. Truy cập: https://aistudio.google.com/apikey
2. Đăng nhập Google
3. Click "Create API Key"
4. Copy key vào `GEMINI_API_KEY_1`

#### 🔹 OpenAI API (Trả phí - có $5 free credit)
1. Truy cập: https://platform.openai.com/api-keys
2. Đăng nhập/Đăng ký
3. Click "Create new secret key"
4. Copy key vào `OPENAI_API_KEY`

#### 🔹 DeepSeek API (Trả phí - rẻ nhất)
1. Truy cập: https://platform.deepseek.com/api_keys
2. Đăng nhập/Đăng ký
3. Click "Create API Key"
4. Copy key vào `DEEPSEEK_API_KEY`

---

## 🚀 KHỞI ĐỘNG CHATBOT:

### Cách 1: Dùng Batch Script (Đơn giản nhất)

Double-click vào file: **`start_chatbot.bat`**

### Cách 2: Dùng PowerShell

```powershell
cd i:\AI-Assistant\ChatBot
python app.py
```

### Cách 3: Kiểm tra trước khi chạy

```powershell
# Kiểm tra hệ thống
python check_system.py

# Nếu OK, khởi động
cd ChatBot
python app.py
```

---

## 🌐 MỞ TRÌNH DUYỆT:

Sau khi khởi động thành công, mở:

**http://127.0.0.1:5000**

hoặc

**http://localhost:5000**

---

## 🎯 TEST NHANH (sau khi tạo .env):

```powershell
# Test Gemini API
cd ChatBot
python test_gemini.py

# Test Google Search & GitHub APIs  
python test_tools.py
```

---

## 📋 CHECKLIST CUỐI:

- [ ] Đã copy `ChatBot\.env.example` → `ChatBot\.env`
- [ ] Đã thêm ít nhất 1 API key (Gemini khuyến nghị)
- [ ] Chạy `python check_system.py` và thấy "HỆ THỐNG SẴN SÀNG"
- [ ] Khởi động `python app.py` thành công
- [ ] Mở http://127.0.0.1:5000 và thấy giao diện ChatBot
- [ ] Gửi tin nhắn test và nhận được phản hồi

---

## ❓ NẾU GẶP LỖI:

### Lỗi: "OPENAI_API_KEY not found"
→ Chưa tạo file `ChatBot\.env` hoặc chưa thêm API key

### Lỗi: "gemini-pro not found (404)"
→ Đã fix trong code, dùng gemini-2.0-flash

### Lỗi: "Address already in use"
→ Port 5000 đang được dùng. Thay đổi port trong `.env`:
```
CHATBOT_PORT=5001
```

### ChatBot không phản hồi
→ Kiểm tra API key có đúng không, thử key khác

---

## 📞 HỖ TRỢ:

- Đọc: `SETUP_NEW_DEVICE.txt` (hướng dẫn chi tiết)
- Đọc: `ChatBot/USAGE_GUIDE.md` (hướng dẫn sử dụng)
- Đọc: `SETUP_COMPLETED.md` (tổng hợp tính năng)

---

**Chúc bạn sử dụng vui vẻ! 🎉**

Setup Date: October 28, 2025  
Python Version: 3.10.11  
Developer: Thanh Nguyen
