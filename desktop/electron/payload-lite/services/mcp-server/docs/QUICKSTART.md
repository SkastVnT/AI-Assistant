# ⚡ QUICK START - 5 PHÚT BẮT ĐẦU VỚI MCP

## 🎯 Mục tiêu
Trong 5 phút, bạn sẽ có MCP Server chạy và kết nối với Claude Desktop!

## ✅ Checklist

### ☐ Bước 1: Cài Python (30 giây)
```bash
# Kiểm tra Python đã có chưa
python --version

# Nếu chưa có: Tải từ https://python.org (chọn 3.8+)
# ⚠️ Nhớ tick "Add Python to PATH"
```

### ☐ Bước 2: Cài MCP SDK (1 phút)
```bash
# Mở Command Prompt tại thư mục này
cd services\mcp-server

# Cài đặt (MIỄN PHÍ)
pip install "mcp[cli]"
```

### ☐ Bước 3: Test Server (30 giây)
```bash
# Chạy thử
python server.py

# Hoặc click đúp vào
start-mcp-server.bat
```

**Thành công nếu thấy:**
```
🚀 Starting AI-Assistant MCP Server...
✅ Server is ready!
```

### ☐ Bước 4: Tải Claude Desktop (2 phút)
1. Truy cập: https://claude.ai/download
2. Tải về (FREE)
3. Cài đặt
4. Đăng nhập bằng email

### ☐ Bước 5: Kết nối MCP (1 phút)

**Windows:**
1. Nhấn `Win + R`
2. Gõ: `%APPDATA%\Claude`
3. Tạo/sửa file `claude_desktop_config.json`
4. Copy nội dung từ `config.json` (trong thư mục này)
5. **⚠️ SỬA ĐƯỜNG DẪN** cho đúng với máy bạn!

**Ví dụ:**
```json
{
  "mcpServers": {
    "ai-assistant": {
      "command": "python",
      "args": [
        "C:\\Users\\TenBan\\Path\\To\\AI-Assistant\\services\\mcp-server\\server.py"
      ]
    }
  }
}
```

6. Thoát Claude Desktop (hoàn toàn, không minimize)
7. Mở lại
8. Tìm icon 🔌 ở góc dưới

## 🎉 XONG! Thử ngay:

Hỏi Claude:
```
"Hãy tìm tất cả file Python trong project AI-Assistant"
```

hoặc

```
"Cho tôi biết project này có những service gì?"
```

## ❌ Lỗi thường gặp

### "Module 'mcp' not found"
```bash
pip install "mcp[cli]"
```

### Claude không thấy server
- Kiểm tra đường dẫn trong `claude_desktop_config.json`
- Khởi động lại Claude Desktop **HOÀN TOÀN** (Quit, không minimize)
- Kiểm tra Python trong PATH: `python --version`

### Server không chạy
```bash
# Test trực tiếp
python server.py

# Xem lỗi ở terminal
```

## 📚 Tiếp theo?

✅ Đọc `HUONG_DAN.md` - Hướng dẫn đầy đủ  
✅ Xem `examples.py` - Ví dụ sử dụng  
✅ Đọc `README.md` - Chi tiết kỹ thuật  

## 💪 Bạn đã sẵn sàng!

Giờ bạn có thể:
- 🔍 Để Claude tìm files
- 📖 Để Claude đọc code
- 🐛 Để Claude tìm bugs
- 📊 Để Claude phân tích logs
- 🚀 Và nhiều hơn nữa!

---

**Tốn bao nhiêu tiền?** 
→ **0đ - Hoàn toàn MIỄN PHÍ!** ✨

**Cần giúp?** 
→ Đọc FAQ trong `HUONG_DAN.md`

**Chúc mừng! Bạn đã có MCP Server! 🎊**
