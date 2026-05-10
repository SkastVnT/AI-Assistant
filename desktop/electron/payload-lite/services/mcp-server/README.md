# AI-Assistant MCP Server

🚀 **Model Context Protocol Server cho AI-Assistant Project**

MCP Server này cho phép các AI assistants (như Claude Desktop) kết nối và tương tác với dự án AI-Assistant của bạn một cách chuẩn hóa.

## 📋 Tổng quan

**Model Context Protocol (MCP)** là một tiêu chuẩn mở do Anthropic phát triển, giúp các LLM kết nối với dữ liệu và công cụ bên ngoài. MCP Server này cung cấp:

- ✅ **100% MIỄN PHÍ** - Sử dụng FastMCP SDK (MIT License)
- ✅ **MÃ NGUỒN MỞ** - Toàn bộ code đều open source
- ✅ **KHÔNG CẦN API KEY TRẢ PHÍ** - Chạy local hoàn toàn

## 🎯 Tính năng

### 🔧 Tools (Công cụ)
AI có thể gọi các công cụ sau:

1. **search_files** - Tìm kiếm files trong workspace
2. **read_file_content** - Đọc nội dung file
3. **list_directory** - Liệt kê thư mục
4. **get_project_info** - Lấy thông tin tổng quan project
5. **search_logs** - Tìm kiếm logs từ các services
6. **calculate** - Thực hiện phép tính toán

### 📦 Resources (Tài nguyên)
AI có thể truy cập các tài nguyên:

1. **config://model** - Cấu hình model
2. **config://logging** - Cấu hình logging
3. **docs://readme** - README chính của project
4. **docs://structure** - Tài liệu cấu trúc project

### 💬 Prompts (Mẫu câu)
Template prompts có sẵn:

1. **code_review_prompt** - Review code
2. **debug_prompt** - Debug lỗi
3. **explain_code_prompt** - Giải thích code

## 🚀 Cài đặt nhanh

### Bước 1: Cài đặt dependencies

```bash
# Chuyển vào thư mục MCP server
cd services/mcp-server

# Cài đặt MCP SDK (MIỄN PHÍ)
pip install "mcp[cli]"
```

### Bước 2: Test server

```bash
# Windows
start-mcp-server.bat

# Linux/Mac
chmod +x start-mcp-server.sh
./start-mcp-server.sh
```

Bạn sẽ thấy:
```
🚀 Starting AI-Assistant MCP Server...
📁 Base Directory: C:\...\AI-Assistant
🔧 Tools available: 6
📦 Resources available: 4
💬 Prompts available: 3

✅ Server is ready!
```

## 🔗 Tích hợp với Claude Desktop

### Bước 1: Tải Claude Desktop

1. Tải **Claude Desktop** (MIỄN PHÍ): https://claude.ai/download
2. Cài đặt và đăng nhập

### Bước 2: Cấu hình MCP Server

1. Mở file cấu hình Claude Desktop:
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
   - **Mac**: `~/Library/Application Support/Claude/claude_desktop_config.json`

2. Thêm cấu hình sau:

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

**⚠️ LƯU Ý**: Thay đổi đường dẫn cho phù hợp với máy tính của bạn!

### Bước 3: Khởi động lại Claude Desktop

1. Thoát hoàn toàn Claude Desktop
2. Mở lại ứng dụng
3. Kiểm tra icon 🔌 (MCP) ở góc dưới để xác nhận kết nối

## 💡 Ví dụ sử dụng

Sau khi kết nối, bạn có thể hỏi Claude Desktop:

### 1. Tìm kiếm files
```
"Tìm giúp tôi tất cả các file Python liên quan đến chatbot"
```

### 2. Đọc code
```
"Đọc và giải thích file services/chatbot/app.py cho tôi"
```

### 3. Review code
```
"Hãy review code trong file server.py và đưa ra suggestions"
```

### 4. Phân tích logs
```
"Kiểm tra logs của chatbot service, có lỗi gì không?"
```

### 5. Thống kê project
```
"Cho tôi biết thông tin tổng quan về project AI-Assistant"
```

## 🔍 Test với MCP Inspector

MCP SDK đi kèm với công cụ inspector để test:

```bash
# Cài đặt inspector
npx @modelcontextprotocol/inspector python server.py

# Hoặc dùng Python
python -m mcp.cli server.py
```

## 📁 Cấu trúc thư mục

```
services/mcp-server/
├── server.py                  # Main MCP server
├── requirements.txt           # Dependencies (tất cả miễn phí)
├── config.json               # Cấu hình mẫu cho Claude Desktop
├── start-mcp-server.bat      # Script khởi động (Windows)
├── start-mcp-server.sh       # Script khởi động (Linux/Mac)
├── README.md                 # Tài liệu này
└── __init__.py
```

## 🌟 Tính năng nâng cao

### Mở rộng với tools mới

Thêm tool mới vào `server.py`:

```python
@mcp.tool()
def my_custom_tool(param: str) -> Dict[str, Any]:
    """
    Mô tả tool của bạn.
    
    Args:
        param: Tham số đầu vào
        
    Returns:
        Kết quả trả về
    """
    # Logic của bạn ở đây
    return {"result": "success"}
```

### Thêm resources mới

```python
@mcp.resource("custom://data")
def get_custom_data() -> str:
    """Mô tả resource"""
    # Trả về dữ liệu
    return "Your data here"
```

### Thêm prompts mới

```python
@mcp.prompt()
def my_prompt(context: str) -> str:
    """Prompt template của bạn"""
    return f"Xử lý context: {context}"
```

## 🔧 Troubleshooting

### Lỗi: "Module 'mcp' not found"
```bash
pip install "mcp[cli]"
```

### Lỗi: Claude Desktop không thấy server
1. Kiểm tra đường dẫn trong `claude_desktop_config.json`
2. Đảm bảo Python có trong PATH
3. Khởi động lại Claude Desktop hoàn toàn

### Server không start
```bash
# Test trực tiếp
python server.py

# Kiểm tra logs
```

## 📚 Tài liệu tham khảo

- **MCP Official Docs**: https://modelcontextprotocol.io
- **MCP Python SDK**: https://github.com/modelcontextprotocol/python-sdk
- **FastMCP Guide**: https://github.com/modelcontextprotocol/python-sdk
- **Claude Desktop**: https://claude.ai/download

## 🎓 Học thêm về MCP

### Tiếng Anh:
- https://www.anthropic.com/news/model-context-protocol
- https://modelcontextprotocol.io/docs/getting-started/intro

### Tiếng Trung (đã dịch):
- https://modelcontextprotocol.info/zh-tw/
- https://blog.csdn.net (search "MCP Model Context Protocol")

## ✨ Đóng góp

MCP Server này là một phần của dự án AI-Assistant. Mọi đóng góp đều được hoan nghênh!

1. Fork repo
2. Tạo branch: `git checkout -b feature/mcp-enhancement`
3. Commit changes: `git commit -am 'Add new MCP feature'`
4. Push: `git push origin feature/mcp-enhancement`
5. Tạo Pull Request

## 📄 License

MIT License - Hoàn toàn miễn phí và mã nguồn mở!

## 🆘 Hỗ trợ

Nếu gặp vấn đề, vui lòng:
1. Kiểm tra phần Troubleshooting ở trên
2. Xem MCP official docs
3. Tạo issue trên GitHub repo

---

**Made with ❤️ by AI-Assistant Team**

*MCP Server - Kết nối AI với thế giới thực!*
