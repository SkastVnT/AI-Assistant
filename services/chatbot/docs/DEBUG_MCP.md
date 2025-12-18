# 🐛 MCP Debug Guide

## Kiểm tra MCP hoạt động đúng

### 1. Check Backend Logs

Khi bật MCP và chọn file, bạn sẽ thấy logs:

```
✅ MCP Client enabled (Standalone mode)
📌 Using 1 selected files for context
📖 Reading file: D:\WORK\testtt\test_sum.py
✅ Successfully read test_sum.py (10 lines)
📝 Injected code context (500 chars, 1 files)
```

### 2. Check Browser Console (F12)

```javascript
// Khi click file, sẽ thấy:
✅ MCP Controller initialized

// Khi send message:
Selected files: ["D:\\WORK\\testtt\\test_sum.py"]
```

### 3. Test Flow

```
1. Bật MCP checkbox → Status: 🟢 Đang bật
2. Chọn folder → Files hiển thị
3. Click vào file test_sum.py → File highlight màu tím
4. Check "📌 Files đã chọn (1)" ở dưới
5. Gửi câu hỏi: "Giải thích code này"
6. Backend logs sẽ show file được đọc
```

### 4. Common Issues

**Issue**: File không được inject
**Fix**: Check console xem `mcp_selected_files` có được gửi không

**Issue**: Context rỗng
**Fix**: Check file path có đúng format Windows không (backslash)

**Issue**: AI không hiểu context
**Fix**: Increase max_lines từ 100 → 200 (đã fix)

### 5. Manual Test

```javascript
// Trong console browser:
window.mcpController.getSelectedFilePaths()
// Output: ["D:\\WORK\\testtt\\test_sum.py"]

window.mcpController.selectedFiles
// Output: [{path: "...", name: "test_sum.py", ...}]
```

### 6. Backend API Test

```bash
# Check if file can be read
curl -X GET "http://localhost:5001/api/mcp/read-file?path=D:\WORK\testtt\test_sum.py&max_lines=200"
```

## ✅ Expected Behavior

Khi hỏi "Giải thích code này" với file test_sum.py được chọn:

**Backend sẽ nhận:**
```json
{
  "message": "Giải thích code này",
  "mcp_selected_files": ["D:\\WORK\\testtt\\test_sum.py"]
}
```

**Backend sẽ inject:**
```markdown
📁 CODE CONTEXT FROM LOCAL FILES:

### 📄 File: test_sum.py
```python
def sum_numbers(a, b):
    return a + b

result = sum_numbers(5, 3)
print(result)
```

---

**USER QUESTION:**
Giải thích code này
```

**AI sẽ thấy full context và trả lời chính xác về file!**
