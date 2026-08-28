# Hướng dẫn sử dụng MCP Server - Tiếng Việt

## 🎯 MCP là gì?

**Model Context Protocol (MCP)** là một giao thức chuẩn mở giúp các AI (như ChatGPT, Claude) có thể:
- 📂 Truy cập files và dữ liệu của bạn
- 🔧 Sử dụng các công cụ (tools)
- 💾 Đọc database, logs, configs
- 🌐 Gọi API bên ngoài

**Ví dụ đơn giản**: Thay vì copy-paste code vào ChatGPT, bạn chỉ cần hỏi "Hãy đọc file app.py và giải thích cho tôi" - AI sẽ tự động đọc file từ máy bạn!

## 🎁 Ưu điểm của giải pháp này

✅ **100% Miễn phí** - Không tốn một xu nào  
✅ **Không cần API key** - Chạy local trên máy  
✅ **Mã nguồn mở** - Bạn có thể xem và chỉnh sửa  
✅ **Dễ cài đặt** - Chỉ cần vài bước đơn giản  
✅ **Bảo mật** - Dữ liệu không rời khỏi máy bạn  

## 📦 Cài đặt từng bước

### Bước 1: Cài đặt Python (nếu chưa có)

1. Tải Python 3.8+ từ: https://www.python.org/downloads/
2. Khi cài, **PHẢI TICK** vào "Add Python to PATH"
3. Kiểm tra: mở Command Prompt và gõ:
   ```bash
   python --version
   ```

### Bước 2: Cài đặt MCP SDK

Mở Command Prompt tại thư mục `services/mcp-server`:

```bash
cd <duong-dan-toi-repo>\AI-Assistant\services\mcp-server
pip install "mcp[cli]"
```

Đợi khoảng 1-2 phút để cài đặt xong.

### Bước 3: Chạy thử server

Click đúp vào file `start-mcp-server.bat` hoặc gõ:

```bash
python server.py
```

Nếu thấy như này là thành công:
```
🚀 Starting AI-Assistant MCP Server...
📁 Base Directory: C:\...\AI-Assistant
🔧 Tools available: 6
📦 Resources available: 4
💬 Prompts available: 3
✅ Server is ready!
```

## 🔗 Kết nối với Claude Desktop

### Cách 1: Sử dụng Claude Desktop (Khuyến nghị - MIỄN PHÍ)

1. **Tải Claude Desktop**:
   - Truy cập: https://claude.ai/download
   - Tải về và cài đặt (miễn phí 100%)
   - Đăng nhập bằng email

2. **Cấu hình MCP Server**:
   
   **Windows**: Mở file này bằng Notepad:
   ```
   %APPDATA%\Claude\claude_desktop_config.json
   ```
   
   Copy/paste nội dung sau (thay đường dẫn cho đúng):
   ```json
   {
     "mcpServers": {
       "ai-assistant": {
         "command": "python",
         "args": [
           "C:\\Users\\Asus\\Downloads\\Compressed\\AI-Assistant\\services\\mcp-server\\server.py"
         ]
       }
     }
   }
   ```

3. **Khởi động lại Claude Desktop**:
   - Thoát hoàn toàn (không chỉ minimize)
   - Mở lại
   - Tìm icon 🔌 ở góc dưới - đó là dấu hiệu đã kết nối!

### Cách 2: Sử dụng với VS Code + Copilot (Nếu bạn dùng)

VS Code đã hỗ trợ MCP từ phiên bản mới. Bạn có thể thêm MCP server vào settings.

### Cách 3: Sử dụng MCP Inspector (Để test)

```bash
npx @modelcontextprotocol/inspector python server.py
```

Một web interface sẽ mở để bạn test các tools.

## 🎨 Ví dụ thực tế

### Ví dụ 1: Tìm file

**Hỏi Claude**:
```
Tìm giúp tôi tất cả các file Python có chứa từ "chatbot"
```

**Claude sẽ gọi tool**: `search_files(query="chatbot", file_type="py")`

**Kết quả**: Danh sách tất cả file .py có "chatbot" trong tên

### Ví dụ 2: Đọc và giải thích code

**Hỏi Claude**:
```
Đọc file services/chatbot/app.py và giải thích cho tôi code làm gì
```

**Claude sẽ**:
1. Gọi `read_file_content("services/chatbot/app.py")`
2. Đọc nội dung
3. Giải thích chi tiết

### Ví dụ 3: Phân tích logs

**Hỏi Claude**:
```
Kiểm tra logs của chatbot service trong 50 dòng cuối, có lỗi gì không?
```

**Claude sẽ**:
1. Gọi `search_logs(service="chatbot", last_n_lines=50)`
2. Phân tích logs
3. Chỉ ra lỗi (nếu có)

### Ví dụ 4: Review code

**Hỏi Claude**:
```
Hãy review code trong file server.py và đưa ra góp ý cải thiện
```

**Claude sẽ**:
1. Đọc file
2. Phân tích code quality
3. Đưa ra suggestions cụ thể

### Ví dụ 5: Tổng quan project

**Hỏi Claude**:
```
Cho tôi biết project AI-Assistant có những gì?
```

**Claude sẽ**:
1. Gọi `get_project_info()`
2. Liệt kê các services
3. Mô tả cấu trúc

## 🔧 Các tools có sẵn

| Tool | Chức năng | Ví dụ sử dụng |
|------|-----------|---------------|
| `search_files` | Tìm files | "Tìm file config" |
| `read_file_content` | Đọc file | "Đọc README.md" |
| `list_directory` | Liệt kê thư mục | "Có gì trong folder services?" |
| `get_project_info` | Info project | "Project này làm gì?" |
| `search_logs` | Tìm logs | "Kiểm tra lỗi trong logs" |
| `calculate` | Tính toán | "Tính sqrt(144)" |

## 🚀 Mở rộng thêm (Nâng cao)

### Thêm tool mới

Mở file `server.py`, thêm vào:

```python
@mcp.tool()
def send_email(to: str, subject: str, body: str) -> Dict[str, Any]:
    """Gửi email"""
    # Code gửi email của bạn
    return {"status": "sent"}
```

Sau đó AI có thể: "Gửi email cho john@example.com với subject là..."

### Kết nối với Database

```python
@mcp.tool()
def query_database(sql: str) -> Dict[str, Any]:
    """Truy vấn database"""
    import sqlite3
    conn = sqlite3.connect('your_db.db')
    cursor = conn.cursor()
    cursor.execute(sql)
    results = cursor.fetchall()
    return {"results": results}
```

### Tích hợp API bên ngoài

```python
@mcp.tool()
def get_weather(city: str) -> Dict[str, Any]:
    """Lấy thông tin thời tiết"""
    import requests
    # Dùng free API như openweathermap
    response = requests.get(f"https://api.openweathermap.org/...")
    return response.json()
```

## ❓ Câu hỏi thường gặp (FAQ)

### Q: MCP có tốn tiền không?
**A**: KHÔNG! Hoàn toàn miễn phí. FastMCP SDK là open source (MIT License).

### Q: Có cần API key không?
**A**: KHÔNG cần! Server chạy local trên máy bạn.

### Q: Dữ liệu có bị gửi đi đâu không?
**A**: KHÔNG! Server chỉ chạy local. Claude Desktop chỉ nhận kết quả, không nhận raw data.

### Q: Tôi phải dùng Claude Desktop à?
**A**: Không bắt buộc. Bạn có thể dùng:
- Claude Desktop (free)
- VS Code + Copilot (nếu có subscription)
- Bất kỳ MCP client nào khác
- MCP Inspector để test

### Q: Tôi không biết code, có dùng được không?
**A**: CÓ! Chỉ cần:
1. Cài Python
2. Chạy file .bat
3. Cấu hình Claude Desktop
4. Hỏi bằng tiếng Việt thông thường!

### Q: Server có chạy mãi không?
**A**: KHÔNG. Server chỉ chạy khi Claude Desktop cần. Khi đóng Claude Desktop, server tự tắt.

### Q: Tôi muốn thêm tính năng mới?
**A**: Dễ! Xem phần "Mở rộng thêm" ở trên. Hoặc hỏi Claude: "Làm sao để thêm tool mới vào MCP server?"

## 🎓 Tài liệu học thêm

### Video tutorials:
- Search YouTube: "MCP Model Context Protocol tutorial"
- Search Bilibili (Trung Quốc): "MCP 教程"

### Tài liệu chính thức:
- https://modelcontextprotocol.io (Tiếng Anh)
- https://modelcontextprotocol.info/zh-tw/ (Tiếng Trung)
- https://blog.csdn.net (Search "MCP" - nhiều bài tiếng Trung)

### Community:
- GitHub: https://github.com/modelcontextprotocol
- Discord: MCP Community Discord

## 💪 Tiếp theo bạn nên làm gì?

1. ✅ **Test server**: Chạy `start-mcp-server.bat`
2. ✅ **Cài Claude Desktop**: Tải về và cấu hình
3. ✅ **Thử nghiệm**: Hỏi Claude vài câu như ví dụ trên
4. ✅ **Tùy chỉnh**: Thêm tools phù hợp với project của bạn
5. ✅ **Chia sẻ**: Giới thiệu MCP cho team!

## 🎉 Chúc mừng!

Bạn đã có một MCP Server hoàn chỉnh, miễn phí và mã nguồn mở!

**Giờ bạn có thể**:
- ✨ Để AI đọc và phân tích code
- 🔍 Tìm kiếm files và dữ liệu
- 📊 Phân tích logs
- 🤖 Tự động hóa các tác vụ
- 🚀 Và nhiều hơn nữa!

---

**Cần hỗ trợ?**
- Đọc lại phần FAQ
- Xem README.md
- Tạo issue trên GitHub

**Chúc bạn thành công! 🎊**
