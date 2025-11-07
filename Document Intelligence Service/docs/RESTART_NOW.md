# 🔄 RESTART SERVICE BÂY GIỜ!

## ✅ API Key đã có trong .env
```
GEMINI_API_KEY=AIzaS...
```

## ⚠️ VẤN ĐỀ
Service đang chạy **chưa load lại .env file**!

## 🚀 CÁCH SỬA (3 BƯỚC ĐƠN GIẢN)

### Bước 1: STOP service đang chạy
Trong terminal đang chạy service, nhấn:
```
Ctrl + C
```

### Bước 2: START lại service
Chạy một trong hai cách:

**Cách 1 - Nhanh (Recommended):**
```powershell
.\restart_service.bat
```

**Cách 2 - Manual:**
```powershell
.\DIS\Scripts\Activate.ps1
$env:PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION='python'
python app.py
```

### Bước 3: Kiểm tra
Mở web: http://127.0.0.1:5003

Bạn sẽ thấy:
```
AI Enhancement (Gemini 2.0 Flash) ✅ ACTIVE
✓ Phân loại document tự động
✓ Trích xuất thông tin thông minh
✓ Tóm tắt nội dung
```

---

## 🎯 KẾT QUẢ MONG ĐỢI

### Console Log:
```
║   🤖 AI: ✅ Enabled (gemini-2.0-flash-exp)
```

### Web UI:
```
AI Enhancement (Gemini 2.0 Flash) [ACTIVE]  ← Màu xanh!
```

---

## ❓ NẾU VẪN INACTIVE

1. **Kiểm tra API key có đúng không:**
```powershell
# Trong PowerShell
$env:GEMINI_API_KEY = "AIzaS..."
python -c "import os; print('API Key:', os.getenv('GEMINI_API_KEY'))"
```

2. **Test API key:**
```powershell
python test_gemini.py
```

3. **Xem log chi tiết:**
- Check console khi start service
- Look for "AI Enhancement" messages

---

## 💡 LÝ DO

Flask `load_dotenv()` chỉ chạy **KHI KHỞI ĐỘNG**, không tự động reload.

Khi bạn thêm/sửa `.env`, bạn PHẢI restart service!

---

**ACTION NOW: Nhấn Ctrl+C trong terminal cũ, rồi chạy `.\restart_service.bat`** 🚀
