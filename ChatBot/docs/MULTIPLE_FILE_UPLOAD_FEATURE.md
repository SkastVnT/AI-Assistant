# 📎 Multiple File Upload & Paste Feature

## Tính năng Upload nhiều file & Copy-Paste

Cho phép tải lên nhiều file cùng lúc và paste nội dung trực tiếp vào chat.

## Cách sử dụng

### 1. Upload nhiều file
1. Click nút **"📎 Upload Files"**
2. Chọn một hoặc nhiều file (Ctrl+Click hoặc Shift+Click)
3. Các file được hiển thị dưới dạng tags màu xanh
4. Click **✕** trên tag để xóa file không cần
5. Gửi tin nhắn - nội dung file sẽ được đính kèm

### 2. Paste file/text
1. Copy file từ File Explorer (Ctrl+C)
2. Click vào textarea message input
3. Paste (Ctrl+V)
4. File sẽ được thêm vào danh sách
5. Hoặc paste text - sẽ paste bình thường

### 3. Các loại file hỗ trợ
- **Text files**: `.txt`, `.md`, `.log`
- **Code files**: `.py`, `.js`, `.html`, `.css`, `.json`
- **Documents**: (đọc nội dung nếu là text-based)

## Features

### ✅ Multiple file selection
- Chọn nhiều file cùng lúc từ file dialog
- Upload thêm file mà không xóa file cũ
- Giới hạn: Không có (nhưng nên < 10 files)

### ✅ File tags display
- Hiển thị file name dưới dạng tag
- Icon 📄 cho mỗi file
- Nút ✕ để xóa từng file
- Color-coded: Xanh dương cho files

### ✅ Paste support
- Paste text: Hoạt động bình thường
- Paste file: Thêm vào danh sách upload
- Paste image: Được lưu dưới dạng file

### ✅ Auto-read content
- Text files được đọc tự động
- Nội dung được thêm vào message
- Format: `--- File: filename ---\nContent\n---`

## UI Components

### File List Container
```html
<div class="file-list" id="fileList">
  <!-- File tags here -->
</div>
```

### File Tag
```html
<div class="file-tag">
  📄 filename.txt
  <span class="file-tag-remove">✕</span>
</div>
```

## JavaScript API

### Variables
```javascript
let uploadedFiles = [];  // Array of File objects
```

### Functions
```javascript
// Render file list
renderFileList()

// Remove file by index
removeFile(index)

// Read file as text (Promise)
readFileAsText(file)
```

### Event Listeners
```javascript
// File input change
fileInput.addEventListener('change', ...)

// Paste event
messageInput.addEventListener('paste', ...)
```

## Message Format

Khi gửi tin nhắn với files:

```
User message...

[3 file(s) attached: file1.py, file2.js, file3.txt]

--- File: file1.py ---
def hello():
    print("Hello")
--- End of file1.py ---

--- File: file2.js ---
console.log("Hello");
--- End of file2.js ---

--- File: file3.txt ---
This is a text file.
--- End of file3.txt ---
```

## Styling

### File Tag CSS
```css
.file-tag {
  background: #e7f3ff;
  border: 1px solid #2196f3;
  border-radius: 5px;
  padding: 4px 8px;
  color: #1976d2;
}
```

### Dark Mode Support
```css
body.dark-mode .file-tag {
  background: rgba(33, 150, 243, 0.2);
  color: #64b5f6;
}
```

## Ví dụ sử dụng

### Example 1: Upload code files
```
1. Click "📎 Upload Files"
2. Select: main.py, utils.py, config.json
3. Type: "Review this code and suggest improvements"
4. Send → AI nhận được cả 3 files
```

### Example 2: Paste code
```
1. Copy code từ editor
2. Paste vào message input (Ctrl+V)
3. Code được paste vào textarea
4. Add context và send
```

### Example 3: Mix files and text
```
1. Upload: database.sql
2. Type: "Optimize these queries"
3. Upload thêm: config.yaml
4. Type: "Using this config"
5. Send → AI nhận full context
```

## Technical Details

### Frontend
- **File Storage**: Array `uploadedFiles[]`
- **File Reading**: FileReader API
- **Paste Detection**: ClipboardEvent API
- **UI Update**: DOM manipulation

### Backend
- **No changes needed** - Files được đọc ở frontend
- Content được gửi như part của message
- AI xử lý như text bình thường

## Limitations

1. **File size**: Browser memory limit (~100MB total)
2. **Binary files**: Không đọc được content (PDF, DOCX, etc.)
3. **Large files**: Có thể làm chậm browser
4. **Image files**: Paste được nhưng chưa hiển thị preview

## Future Improvements

- [ ] PDF content extraction
- [ ] Image preview trong chat
- [ ] File size warning
- [ ] Progress bar cho large files
- [ ] Drag & drop support
- [ ] Cloud storage integration

## Troubleshooting

### Issue: Files không được gửi
- Check: File list có hiển thị tags không?
- Solution: Re-upload files

### Issue: Paste không hoạt động
- Check: Focus vào message input chưa?
- Solution: Click vào textarea trước khi paste

### Issue: Nội dung file không đọc được
- Check: File type có hỗ trợ không?
- Solution: Chỉ upload text-based files

## Version
- **Added in**: v1.7.0
- **Date**: October 29, 2025
- **Status**: ✅ Implemented & Ready
