# 🧠 MCP SERVER V2.0 - WITH PERSISTENT MEMORY

## 🆕 What's New in V2.0?

MCP Server V2.0 kết hợp **tốt nhất của cả hai thế giới**:

### ✅ **From Original MCP Server:**
- Real-time project access
- File search & read
- Log analysis
- Project information
- Code review prompts

### ✅ **From claude-mem:**
- Persistent memory across sessions
- AI-powered observations
- Full-text search qua history
- Session summaries
- Memory statistics

---

## 🎯 KEY FEATURES

### **1. Real-Time Tools (Original)**
- `search_files()` - Tìm files trong project
- `read_file_content()` - Đọc nội dung files
- `list_directory()` - Liệt kê thư mục
- `get_project_info()` - Thông tin project
- `search_logs()` - Tìm trong logs
- `calculate()` - Tính toán

### **2. Memory Tools (NEW!)**
- `search_memory()` - 🔍 Tìm trong memory của các sessions trước
- `get_recent_context()` - 📋 Lấy context gần đây để inject vào session
- `get_memory_by_file()` - 📁 Xem history của một file cụ thể
- `get_session_history()` - 📅 Lịch sử các sessions
- `save_important_observation()` - 💾 Lưu observation quan trọng
- `get_memory_statistics()` - 📊 Thống kê memory system

### **3. Automatic Memory Saving**
- Mỗi tool execution được log tự động
- AI tạo observations từ tool usage
- Full-text search với SQLite FTS5
- Session summaries

---

## 🚀 QUICK START

### **Bước 1: Start Server V2.0**

```bash
cd services/mcp-server
start-mcp-v2-memory.bat
```

### **Bước 2: Configure Claude Desktop**

Thêm config vào `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai-assistant-v2-memory": {
      "command": "python",
      "args": [
        "C:\\Users\\Asus\\Downloads\\Compressed\\AI-Assistant\\services\\mcp-server\\server_v2_memory.py"
      ],
      "env": {
        "PYTHONPATH": "C:\\Users\\Asus\\Downloads\\Compressed\\AI-Assistant"
      }
    }
  }
}
```

### **Bước 3: Restart Claude Desktop**

Xong! Giờ Claude Desktop đã có memory! 🎉

---

## 💬 USAGE EXAMPLES

### **Example 1: Tìm trong memory**

**Session 1 (Hôm nay):**
```
Bạn: Đọc file services/chatbot/app.py
→ Server tự động lưu observation: "Read chatbot app.py, found Flask routes"
```

**Session 2 (Ngày mai):**
```
Bạn: Hôm qua tôi đã làm gì với chatbot?
Claude: search_memory("chatbot")
→ Kết quả: "Read chatbot app.py, found Flask routes" (từ session 1)
```

---

### **Example 2: Context auto-injection**

Khi start session mới, server tự động inject context:

```
=== PREVIOUS CONTEXT FROM MEMORY ===
Found 30 relevant observations:

1. [🔴 BUGFIX] Fixed memory leak in chatbot service
   Files: services/chatbot/app.py
   Time: 2025-12-15 10:30:00

2. [🟡 FEATURE] Added caching layer to Text2SQL
   Files: services/text2sql/cache.py
   Time: 2025-12-15 09:15:00
   
...

=== END CONTEXT ===
```

---

### **Example 3: Search by file**

```
Bạn: Cho tôi xem tất cả thay đổi đã làm với file chatbot/app.py

Claude sử dụng: get_memory_by_file("services/chatbot/app.py")

Kết quả:
- Fixed bug line 125 (2 days ago)
- Added streaming support (1 week ago)
- Refactored error handling (2 weeks ago)
```

---

### **Example 4: Save important decision**

```
Bạn: Lưu lại quyết định: Chúng ta sẽ dùng Redis cho cache thay vì in-memory

Claude sử dụng: 
save_important_observation(
  observation="Decided to use Redis for caching instead of in-memory",
  observation_type="decision",
  importance=9,
  tags=["architecture", "caching", "redis"]
)

✅ Saved! Có thể tìm lại sau này.
```

---

### **Example 5: View statistics**

```
Bạn: Cho tôi xem thống kê memory

Claude sử dụng: get_memory_statistics()

Kết quả:
- Total sessions: 25
- Total observations: 347
- Total tools used: 1,234
- Top tools:
  1. search_files (423 times)
  2. read_file_content (356 times)
  3. search_logs (187 times)
```

---

## 🗂️ DATABASE STRUCTURE

Memory được lưu trong SQLite database:

```
resources/memory/mcp_memory.db
├── sessions          (Các sessions làm việc)
├── observations      (AI-generated learnings)
├── tool_usage        (Log tất cả tool executions)
├── session_summaries (Summaries của sessions)
├── memory_context    (Pre-computed context)
└── statistics        (Metrics tổng quan)
```

---

## 🎨 OBSERVATION TYPES

Mỗi observation được phân loại:

| Type | Icon | Description |
|------|------|-------------|
| `decision` | 🟤 | Quyết định architecture/design |
| `bugfix` | 🔴 | Sửa bugs |
| `feature` | 🟢 | Thêm tính năng mới |
| `refactor` | 🔵 | Refactor code |
| `discovery` | 💡 | Phát hiện mới |
| `change` | 🟡 | Thay đổi cấu hình |
| `general` | ⚪ | Thông tin chung |

---

## 📊 IMPORTANCE SCALE

- **9-10**: 🔴 Critical - Quyết định quan trọng, bugs nghiêm trọng
- **7-8**: 🟡 High - Features lớn, refactors quan trọng
- **5-6**: 🟠 Medium - Changes thông thường
- **1-4**: 🔵 Low - Thông tin tham khảo

---

## 🔄 SESSION LIFECYCLE

```
1. Start Server
   → Auto-create session
   → Load context from memory (last 30 observations)

2. Use Tools
   → Each tool logged automatically
   → AI creates observation

3. End Server
   → Save session summary
   → Update statistics
```

---

## 🆚 COMPARISON: V1 vs V2

| Feature | V1 (Original) | V2 (Memory) |
|---------|--------------|-------------|
| File Operations | ✅ | ✅ |
| Project Info | ✅ | ✅ |
| Log Search | ✅ | ✅ |
| **Memory Storage** | ❌ | ✅ |
| **Search History** | ❌ | ✅ |
| **AI Observations** | ❌ | ✅ |
| **Session Context** | ❌ | ✅ |
| **Full-Text Search** | ❌ | ✅ |
| **Statistics** | ❌ | ✅ |

---

## 🛠️ ADVANCED FEATURES

### **1. Concept Tags**

Observations được tag với concepts:
- `discovery` - Phát hiện mới
- `problem-solution` - Giải quyết vấn đề
- `pattern` - Patterns trong code
- `architecture` - Quyết định thiết kế
- `performance` - Tối ưu performance

### **2. File References**

Mỗi observation link đến files liên quan:
```json
{
  "observation": "Fixed memory leak",
  "file_references": [
    "services/chatbot/app.py",
    "services/chatbot/models.py"
  ]
}
```

### **3. Full-Text Search (FTS5)**

SQLite FTS5 cho semantic search nhanh:
```sql
SELECT * FROM observations_fts 
WHERE observations_fts MATCH 'memory leak OR performance'
```

---

## 🧹 MAINTENANCE

### **Cleanup Old Data**

```python
memory.cleanup_old_data(days=90)  # Xóa data > 90 ngày
```

### **View Database**

```bash
sqlite3 resources/memory/mcp_memory.db
> .tables
> SELECT * FROM sessions LIMIT 10;
```

### **Backup**

```bash
copy resources\memory\mcp_memory.db resources\memory\backup\
```

---

## 🚨 TROUBLESHOOTING

### **Memory không được lưu?**

```bash
# Check database exists
dir resources\memory\mcp_memory.db

# Check tables
sqlite3 resources\memory\mcp_memory.db ".tables"
```

### **Search không hoạt động?**

```bash
# Rebuild FTS index
sqlite3 resources\memory\mcp_memory.db
> DELETE FROM observations_fts;
> INSERT INTO observations_fts SELECT rowid, * FROM observations;
```

---

## 📚 SEE ALSO

- [Original README](README.md) - MCP Server V1 documentation
- [CACH_SU_DUNG.md](CACH_SU_DUNG.md) - Hướng dẫn sử dụng cơ bản
- [ROADMAP.md](ROADMAP.md) - Kế hoạch phát triển
- [DIAGRAMS.md](DIAGRAMS.md) - Architecture diagrams

---

## 🎉 CONCLUSION

**MCP Server V2.0 = Real-time Access + Persistent Memory**

- ✅ Tất cả tools của V1
- ✅ Memory system như claude-mem
- ✅ Tự động save observations
- ✅ Search qua history
- ✅ Session summaries
- ✅ Full-text search
- ✅ Statistics & metrics

**Bắt đầu ngay:**
```bash
start-mcp-v2-memory.bat
```

🚀 **Happy coding with memory!**
