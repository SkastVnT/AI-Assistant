# 🎬 MCP Server - Video Tutorial Script

## 📹 Video 1: Giới thiệu MCP là gì? (3 phút)

### Scene 1: Hook (15s)
```
[Screen: ChatGPT interface]
Narrator: "Bạn có bao giờ muốn ChatGPT hoặc Claude có thể đọc files trên máy bạn không?"

[Screen: Highlight copy-paste văn bản]
Narrator: "Thay vì copy-paste code từng file..."

[Screen: MCP logo animation]
Narrator: "Giờ đây có Model Context Protocol - MCP!"
```

### Scene 2: MCP là gì? (45s)
```
[Screen: Diagram MCP architecture]
Narrator: "MCP là một giao thức mã nguồn mở do Anthropic phát triển"

[Animation: AI ↔ MCP ↔ Data]
Narrator: "Giống như USB-C cho phần cứng, MCP là chuẩn kết nối cho AI"

[Screen: Show examples]
Narrator: "AI có thể:"
- ✅ Đọc files và code
- ✅ Tìm kiếm dữ liệu
- ✅ Phân tích logs
- ✅ Thực thi công cụ

[Screen: FREE badge]
Narrator: "Và điều tuyệt vời nhất - HOÀN TOÀN MIỄN PHÍ!"
```

### Scene 3: Demo thực tế (90s)
```
[Screen: Claude Desktop]
Narrator: "Hãy xem ví dụ thực tế"

[Type]: "Tìm tất cả file Python liên quan đến chatbot"
[Show]: Claude gọi search_files() và trả về kết quả

[Type]: "Đọc file app.py và giải thích cho tôi"
[Show]: Claude đọc file và giải thích chi tiết

[Type]: "Có lỗi gì trong logs không?"
[Show]: Claude phân tích logs và chỉ ra issues

Narrator: "Thật dễ dàng phải không?"
```

### Scene 4: Call to Action (30s)
```
[Screen: Project link]
Narrator: "MCP Server cho AI-Assistant project đã sẵn sàng"

[Show]: Quick stats
- ✅ 6 Tools
- ✅ 4 Resources
- ✅ 3 Prompts
- ✅ 100% FREE

Narrator: "Link GitHub trong description. Cài đặt chỉ 5 phút!"

[End screen]: Like, Subscribe, Comment
```

---

## 📹 Video 2: Hướng dẫn cài đặt (10 phút)

### Part 1: Prerequisites (2 phút)
```
[Screen: Python.org]
Step 1: Check Python
- python --version
- Nếu chưa có: Download từ python.org
- ⚠️ Nhớ tick "Add to PATH"

[Screen: Terminal]
Step 2: Test Python
- python --version ✅
- pip --version ✅
```

### Part 2: Clone & Install (3 phút)
```
[Screen: GitHub]
Step 1: Clone project
- git clone https://github.com/SkastVnT/AI-Assistant
- cd AI-Assistant/services/mcp-server

[Screen: Terminal]
Step 2: Install MCP SDK
- pip install "mcp[cli]"
- Đợi 1-2 phút
- ✅ Successfully installed

[Screen: File explorer]
Step 3: Kiểm tra files
- server.py ✅
- requirements.txt ✅
- start-mcp-server.bat ✅
```

### Part 3: Test Server (2 phút)
```
[Screen: Terminal]
Run server:
- python server.py

[Show output]:
🚀 Starting AI-Assistant MCP Server...
📁 Base Directory: ...
🔧 Tools available: 6
📦 Resources available: 4
💬 Prompts available: 3
✅ Server is ready!

Narrator: "Thành công! Server đã chạy!"
```

### Part 4: Claude Desktop Setup (3 phút)
```
[Screen: Claude.ai/download]
Step 1: Download Claude Desktop
- Click Download
- Install & Login

[Screen: File explorer]
Step 2: Config file
- Press Win+R
- Type: %APPDATA%\Claude
- Create/Edit: claude_desktop_config.json

[Screen: Notepad]
Step 3: Paste config
- Open config.json from mcp-server folder
- Copy content
- ⚠️ SỬA ĐƯỜNG DẪN cho đúng!

[Screen: Claude Desktop]
Step 4: Restart Claude
- Quit completely
- Open again
- Look for 🔌 icon
- ✅ Connected!

[Screen: Demo]
Step 5: Test
Type: "Hãy tìm file README.md và đọc cho tôi"
[Show]: Claude successfully reads file
```

---

## 📹 Video 3: Advanced Usage (15 phút)

### Segment 1: Các Tools có sẵn (5 phút)
```
Demo từng tool:
1. search_files - Tìm kiếm files
2. read_file_content - Đọc nội dung
3. list_directory - Liệt kê thư mục
4. get_project_info - Thông tin project
5. search_logs - Tìm logs
6. calculate - Tính toán
```

### Segment 2: Use Cases (5 phút)
```
1. Code Review
   - "Review file X và đưa ra góp ý"

2. Bug Finding
   - "Tìm bugs trong code"
   - "Kiểm tra logs có lỗi không"

3. Documentation
   - "Tạo documentation cho file này"

4. Refactoring
   - "Suggest cách improve code"

5. Learning
   - "Giải thích cách code này hoạt động"
```

### Segment 3: Tùy chỉnh (5 phút)
```
[Screen: server.py]
Hướng dẫn thêm tool mới:

@mcp.tool()
def my_tool(param: str) -> Dict:
    # Your code
    return {"result": "success"}

[Demo]: Test tool mới

[Screen: Examples]
Các ý tưởng:
- Send email
- Query database
- Call external API
- Process images
- Etc.
```

---

## 📹 Video 4: Troubleshooting (7 phút)

### Common Issues:

```
Issue 1: "Module 'mcp' not found" (1 phút)
Solution: pip install "mcp[cli]"

Issue 2: Claude không thấy server (2 phút)
Solutions:
- Kiểm tra đường dẫn trong config
- Restart Claude hoàn toàn
- Check Python in PATH

Issue 3: Server không start (2 phút)
Solutions:
- Test: python server.py
- Check error messages
- Verify Python version

Issue 4: Tools không hoạt động (2 phút)
Solutions:
- Check file paths
- Verify permissions
- Review logs
```

---

## 📝 Notes cho người quay video

### Equipment:
- Screen recording: OBS Studio / Camtasia
- Mic: Clear audio quality
- Resolution: 1920x1080 minimum

### Style:
- **Pace**: Moderate, clear speaking
- **Language**: Vietnamese with English terms
- **Subtitles**: Add Vietnamese subs
- **Music**: Soft background music

### Editing:
- Cut long waits
- Highlight important commands
- Add text overlays for key points
- Include timestamps in description

### Publishing:
- **Title**: "MCP Server Tutorial - Kết nối AI với Project của bạn [Miễn phí]"
- **Tags**: MCP, Model Context Protocol, Claude, AI, Python, Tutorial, Tiếng Việt
- **Description**: Include GitHub link, timestamps, resources
- **Thumbnail**: Eye-catching with "FREE" badge

---

## 🎯 Key Messages to Emphasize

1. ✅ **100% FREE** - Repeat this multiple times
2. ✅ **EASY** - Show it's just a few commands
3. ✅ **POWERFUL** - Demo impressive features
4. ✅ **SAFE** - Data stays on your machine
5. ✅ **OPEN SOURCE** - You can customize it

---

**Good luck with your video! 🎬**
