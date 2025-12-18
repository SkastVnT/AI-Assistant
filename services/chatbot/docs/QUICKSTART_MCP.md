# ⚡ MCP ChatBot - Quick Start Guide

## 🚀 5 Minutes Setup

### 1. Khởi động ChatBot

```bash
cd services/chatbot
python app.py
```

Mở browser: **http://localhost:5000**

---

### 2. Bật MCP trong UI

1. Tìm section **MCP Controls** (bên dưới controls)
2. ✅ Click checkbox: **"🔗 MCP: Truy cập file local"**
3. Xem status đổi thành: **🟢 Đang bật**

---

### 3. Chọn Folder

1. Click button: **📁 Chọn folder**
2. Nhập đường dẫn, ví dụ:
   ```
   C:\Users\Asus\Downloads\Compressed\AI-Assistant
   ```
3. Click: **✓ Thêm Folder**

---

### 4. Test với ChatBot

Gửi tin nhắn:

```
Giải thích code trong file app.py
```

hoặc

```
Tìm tất cả Python files trong project này
```

ChatBot sẽ tự động:
- 🔍 Search files liên quan
- 📖 Đọc nội dung
- 🤖 Trả lời với code context

---

## 🎯 Example Questions

### Code Understanding
```
"Explain how the Flask app works"
"What does the ChatbotAgent class do?"
"Show me the database connection code"
```

### Bug Finding
```
"Find bugs in database.py"
"Check for security issues"
"Are there any unused imports?"
```

### Project Analysis
```
"What is this project about?"
"List all API endpoints"
"Show me the project structure"
```

---

## 🛠️ Troubleshooting

### MCP không bật được?

**Giải pháp:**
1. Mở **F12 Console** → Xem errors
2. Kiểm tra Flask logs
3. Restart ChatBot

### Không đọc được files?

**Giải pháp:**
1. Kiểm tra đường dẫn folder có đúng
2. Kiểm tra permissions
3. Thử folder khác

### Context quá dài?

**Giải pháp:**
- Hỏi cụ thể hơn (file name hoặc function name)
- Chọn folder nhỏ hơn

---

## 📚 Full Documentation

- **Complete Guide**: [MCP_INTEGRATION.md](MCP_INTEGRATION.md)
- **Summary**: [MCP_INTEGRATION_SUMMARY.md](MCP_INTEGRATION_SUMMARY.md)
- **API Reference**: See docs above

---

## ✅ Features

- ✅ Bật/tắt MCP từ UI
- ✅ Chọn multiple folders
- ✅ Search files nhanh
- ✅ Auto inject code context
- ✅ Support Python, JS, TS, MD, etc.
- ✅ Dark mode compatible

---

**That's it! Enjoy MCP! 🎉**

Need help? Check [MCP_INTEGRATION.md](MCP_INTEGRATION.md) for details.
