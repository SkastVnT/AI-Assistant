# 🚀 HƯỚNG DẪN SỬ DỤNG MCP SERVER

## 📋 MCP Server là gì?

**Model Context Protocol (MCP)** cho phép các AI assistants như Claude Desktop **truy cập vào dự án của bạn** để:
- 🔍 Tìm kiếm files
- 📖 Đọc code
- 📊 Phân tích logs
- 🔧 Thực hiện tính toán
- 💡 Đưa ra gợi ý code

---

## 🎯 CÁC BƯỚC SỬ DỤNG

### **Bước 1: Tải Claude Desktop** (MIỄN PHÍ)

1. Truy cập: https://claude.ai/download
2. Tải **Claude for Desktop** (Windows/Mac/Linux)
3. Cài đặt và đăng nhập (miễn phí)

---

### **Bước 2: Cấu hình Claude Desktop kết nối với MCP Server**

#### **Option A: Tự động (Khuyến nghị)**

Chạy file cấu hình có sẵn:

```bash
# Mở PowerShell tại thư mục dự án
cd <duong-dan-toi-repo>\AI-Assistant\services\mcp-server

# Copy config vào Claude Desktop
copy config.json "%APPDATA%\Claude\claude_desktop_config.json"
```

#### **Option B: Thủ công**

1. Mở file config của Claude Desktop:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```

2. Thêm cấu hình này (thay đường dẫn cho đúng):

```json
{
  "mcpServers": {
    "ai-assistant": {
      "command": "python",
      "args": [
        "C:\\Users\\Asus\\Downloads\\Compressed\\AI-Assistant\\services\\mcp-server\\server.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\Asus\\Downloads\\Compressed\\AI-Assistant"
      }
    }
  }
}
```

3. **Lưu file** và **khởi động lại Claude Desktop**

---

### **Bước 3: Kiểm tra kết nối**

1. Mở **Claude Desktop**
2. Nhìn góc dưới bên phải, bạn sẽ thấy **biểu tượng 🔌 MCP**
3. Click vào đó → Xem danh sách servers → Tìm **"ai-assistant"**
4. Nếu thấy ✅ màu xanh → **Kết nối thành công!**

---

## 💬 CÁCH SỬ DỤNG TRONG CLAUDE DESKTOP

### **1️⃣ Tìm kiếm files trong dự án**

**Hỏi Claude:**
```
Tìm tất cả file Python có chứa "ChatBot" trong dự án
```

**Claude sẽ dùng tool:**
```python
search_files(query="ChatBot", file_type="py")
```

**Kết quả:**
```
✅ Tìm thấy 5 files:
- services/chatbot/app.py
- services/chatbot/models.py
- services/chatbot/routes.py
- ...
```

---

### **2️⃣ Đọc nội dung file**

**Hỏi Claude:**
```
Đọc file services/chatbot/app.py từ dòng 1 đến 50
```

**Claude sẽ dùng tool:**
```python
read_file_content(file_path="services/chatbot/app.py", start_line=1, end_line=50)
```

---

### **3️⃣ Phân tích logs**

**Hỏi Claude:**
```
Tìm tất cả lỗi ERROR trong logs của chatbot service
```

**Claude sẽ dùng tool:**
```python
search_logs(service_name="chatbot", level="ERROR")
```

---

### **4️⃣ Xem thông tin dự án**

**Hỏi Claude:**
```
Dự án này có những service nào?
```

**Claude sẽ dùng tool:**
```python
get_project_info()
```

**Kết quả:**
```
📦 AI-Assistant Project
📂 Services:
  - ChatBot (Port 5001)
  - Text2SQL (Port 5002)
  - Document Intelligence (Port 5003)
  - Speech2Text (Port 7860)
  - Stable Diffusion (Port 7861)
  - ...
```

---

### **5️⃣ Thực hiện tính toán**

**Hỏi Claude:**
```
Tính (1024 * 8) / 1000
```

**Claude sẽ dùng tool:**
```python
calculate(expression="(1024 * 8) / 1000")
```

**Kết quả:**
```
8.192
```

---

## 🎨 SỬ DỤNG PROMPTS (Mẫu câu lệnh sẵn)

### **Code Review**

**Hỏi Claude:**
```
Review code file services/chatbot/app.py
```

**Claude sẽ tự động:**
1. Đọc file
2. Phân tích code
3. Đưa ra nhận xét về:
   - Security issues
   - Performance problems
   - Best practices
   - Suggestions

---

### **Debug Code**

**Hỏi Claude:**
```
Debug lỗi trong file services/chatbot/routes.py dòng 125
```

**Claude sẽ:**
1. Đọc code xung quanh dòng 125
2. Tìm logs liên quan
3. Xác định nguyên nhân
4. Đề xuất fix

---

### **Explain Code**

**Hỏi Claude:**
```
Giải thích function process_message trong services/chatbot/app.py
```

**Claude sẽ:**
1. Đọc function
2. Phân tích logic
3. Giải thích bằng tiếng Việt
4. Vẽ flowchart nếu cần

---

## 📦 SỬ DỤNG RESOURCES (Tài nguyên tĩnh)

Claude có thể truy cập trực tiếp các resources:

### **1. Model Config**
```
Cấu hình model hiện tại của dự án là gì?
```
→ Claude đọc `config://model`

### **2. Logging Config**
```
Logging được cấu hình như thế nào?
```
→ Claude đọc `config://logging`

### **3. Documentation**
```
README của dự án nói gì?
```
→ Claude đọc `docs://readme`

### **4. Project Structure**
```
Cấu trúc thư mục dự án ra sao?
```
→ Claude đọc `docs://structure`

---

## 🔥 VÍ DỤ THỰC TÊ

### **Scenario 1: Tìm và sửa bug**

**Bạn:**
```
Service chatbot bị lỗi khi gửi tin nhắn dài. Tìm và sửa giúp tôi.
```

**Claude sẽ:**
1. ✅ `search_logs(service_name="chatbot", level="ERROR")`
2. ✅ `read_file_content("services/chatbot/app.py")`
3. ✅ Phân tích lỗi
4. ✅ Đề xuất code fix
5. ✅ Giải thích tại sao lỗi

---

### **Scenario 2: Thêm tính năng mới**

**Bạn:**
```
Tôi muốn thêm cache cho chatbot service. Hướng dẫn tôi.
```

**Claude sẽ:**
1. ✅ `get_project_info()` - Xem cấu trúc
2. ✅ `read_file_content("services/chatbot/app.py")` - Đọc code hiện tại
3. ✅ Đề xuất implementation với Redis
4. ✅ Viết code mẫu
5. ✅ Hướng dẫn test

---

### **Scenario 3: Code review toàn bộ service**

**Bạn:**
```
Review toàn bộ code của Text2SQL service
```

**Claude sẽ:**
1. ✅ `search_files(query="text2sql", file_type="py")`
2. ✅ Đọc tất cả files
3. ✅ Phân tích:
   - Security vulnerabilities
   - SQL injection risks
   - Performance bottlenecks
   - Code quality
4. ✅ Đề xuất improvements

---

### **Scenario 4: Tạo documentation**

**Bạn:**
```
Tạo API documentation cho chatbot service
```

**Claude sẽ:**
1. ✅ Đọc tất cả routes
2. ✅ Phân tích endpoints
3. ✅ Tạo OpenAPI/Swagger spec
4. ✅ Viết examples

---

## 🛠️ TIPS & TRICKS

### **💡 Tip 1: Kết hợp nhiều tools**

**Thông minh:**
```
Tìm tất cả files có TODO, đọc nội dung, và tạo danh sách task
```

Claude sẽ tự động:
1. `search_files("TODO")`
2. `read_file_content()` cho từng file
3. Tổng hợp thành checklist

---

### **💡 Tip 2: Sử dụng context**

**Tốt hơn:**
```
Trong file services/chatbot/app.py, function nào xử lý streaming?
```

**Hơn là:**
```
Tìm function xử lý streaming
```

---

### **💡 Tip 3: Yêu cầu cụ thể**

**Tốt:**
```
Đọc file app.py từ dòng 100-150 và giải thích logic xử lý error
```

**Tệ:**
```
Giải thích app.py
```

---

## 🚨 TROUBLESHOOTING

### **❌ Claude không thấy MCP Server**

**Giải pháp:**
1. Kiểm tra file config:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```
2. Đảm bảo đường dẫn đúng (dùng `\\` cho Windows)
3. Khởi động lại Claude Desktop

---

### **❌ Lỗi "Module not found"**

**Giải pháp:**
1. Kiểm tra Python environment:
   ```bash
   python -c "import mcp"
   ```
2. Cài đặt lại:
   ```bash
   pip install "mcp[cli]>=1.0.0"
   ```

---

### **❌ Tools không hoạt động**

**Giải pháp:**
1. Kiểm tra logs trong MCP server terminal
2. Xem file `resources/logs/mcp_server.log`
3. Thử test trực tiếp:
   ```bash
   cd services/mcp-server
   python server.py
   ```

---

## 📚 TÀI LIỆU THAM KHẢO

- 📖 [Tài liệu đầy đủ (README.md)](README.md)
- 🎓 [Quick Start Guide (QUICKSTART.md)](QUICKSTART.md)
- 🇻🇳 [Hướng dẫn tiếng Việt (HUONG_DAN.md)](HUONG_DAN.md)
- 🗺️ [Roadmap phát triển (ROADMAP.md)](ROADMAP.md)
- 📊 [Architecture Diagrams (DIAGRAMS.md)](DIAGRAMS.md)

---

## 🎯 KẾT LUẬN

**MCP Server cho phép bạn:**
- ✅ Tương tác với dự án AI-Assistant qua Claude Desktop
- ✅ Tự động hóa code review, debugging, documentation
- ✅ Tìm kiếm, đọc, phân tích code nhanh chóng
- ✅ Không cần rời khỏi Claude để làm việc với dự án

**Bắt đầu ngay:**
1. Tải Claude Desktop
2. Cấu hình kết nối (copy config.json)
3. Hỏi Claude: "Dự án AI-Assistant có gì?"

---

## 💬 HỖ TRỢ

**Có vấn đề?**
- Xem logs: `resources/logs/mcp_server.log`
- Đọc docs: `services/mcp-server/README.md`
- Check config: `services/mcp-server/config.json`

**Cần thêm tính năng?**
- Xem roadmap: `services/mcp-server/ROADMAP.md`
- Thêm tools: `services/mcp-server/tools/advanced_tools.py`

---

🎉 **Chúc bạn sử dụng MCP Server hiệu quả!**
