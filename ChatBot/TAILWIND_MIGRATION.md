# 🎨 ChatBot v2.0 - Tailwind CSS Migration Guide

## ✅ Đã hoàn thành

### 1. **Tách file HTML thành modules**
```
OLD: index.html (3700+ lines)
NEW: 
- index_new.html (300 lines)
- app.js (300 lines)
- memory.js (200 lines)
- image-gen.js (300 lines)
- pdf-export.js (150 lines)
- styles.css (400 lines)
```

### 2. **Tailwind CSS Integration**
- Sử dụng Tailwind CDN
- Utility-first CSS classes
- Responsive design
- Dark mode support

### 3. **Cải thiện màu chữ**
✅ Light mode: Text màu tối (#2d3748) - dễ đọc
✅ Dark mode: Text màu sáng (#e2e8f0) - dễ đọc
✅ Active chat item: Text trắng trên background gradient

### 4. **Fix chat list behavior**
✅ **KHÔNG tự động pop-up** khi update
✅ Chỉ sort theo thời gian khi load lần đầu
✅ Update in-place không làm thay đổi thứ tự

## 🚀 Cách sử dụng

### Chạy server:
```bash
cd I:\AI-Assistant\ChatBot
python app.py
```

### Truy cập:
- **Version mới (Tailwind)**: http://127.0.0.1:5000/
- **Version cũ (backup)**: http://127.0.0.1:5000/old

## 📂 Cấu trúc mới

```
ChatBot/
├── app.py (updated)
├── templates/
│   ├── index.html (old - backup)
│   └── index_new.html (NEW - Tailwind)
├── static/
│   ├── css/
│   │   └── styles.css (NEW)
│   └── js/
│       ├── app.js (NEW)
│       ├── memory.js (NEW)
│       ├── image-gen.js (NEW)
│       └── pdf-export.js (NEW)
└── data/
    └── memory/
```

## 🎯 Tính năng

✅ Chat với AI (Gemini, Qwen, BloomVN)
✅ Deep Thinking mode
✅ AI Learning với memories
✅ Tạo ảnh với Stable Diffusion
✅ Export chat ra PDF (có cả ảnh và metadata)
✅ Lưu bài học với images vào folder
✅ Dark mode
✅ Responsive mobile
✅ Chat history sidebar

## 🐛 Bugs đã fix

1. ✅ Chat list không tự đẩy lên đầu khi cập nhật
2. ✅ Màu chữ dễ đọc trên nền trắng
3. ✅ Sidebar collapse trên mobile
4. ✅ PDF export với metadata
5. ✅ Memory save với multiple images
6. ✅ Safe DOM manipulation

## 🎨 CSS Classes (Tailwind)

### Layout:
```html
<div class="flex flex-col h-screen">
<div class="grid grid-cols-3 gap-4">
<div class="space-y-4">
```

### Colors:
```html
<div class="bg-purple-600 text-white">
<div class="dark:bg-gray-800 dark:text-gray-200">
```

### Responsive:
```html
<div class="lg:block md:grid-cols-3">
```

## 🔧 Configuration

### Dark Mode:
Tự động lưu vào localStorage:
```javascript
localStorage.setItem('darkMode', true/false)
```

### Chat History:
Lưu trong localStorage:
```javascript
localStorage.setItem('chatHistory', JSON.stringify(chats))
```

### Memory Context:
Tick vào checkbox bên cạnh bài học để enable

## 📝 API Endpoints

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/` | GET | Home page (Tailwind version) |
| `/old` | GET | Old version (backup) |
| `/chat` | POST | Send chat message |
| `/api/memory/save` | POST | Save memory |
| `/api/memory/list` | GET | List memories |
| `/api/memory/delete/:id` | DELETE | Delete memory |
| `/api/generate-image` | POST | Generate image |
| `/storage/images/:filename` | GET | Get image |

## 🎯 Testing

### Test chat list behavior:
1. Tạo vài cuộc trò chuyện
2. Chuyển đổi giữa các chat
3. Gửi tin nhắn mới
4. ✅ Kiểm tra: Chat hiện tại KHÔNG đẩy lên đầu

### Test dark mode:
1. Click nút "🌙 Dark Mode"
2. ✅ Kiểm tra: Text dễ đọc ở cả 2 modes
3. Reload page
4. ✅ Kiểm tra: Dark mode được giữ

### Test PDF export:
1. Chat với AI, tạo vài ảnh
2. Click "📥 PDF"
3. ✅ Kiểm tra: PDF có ảnh + metadata

### Test memory:
1. Bật "📚 AI Learning"
2. Chat có ảnh
3. Click "💾 Lưu bài học"
4. ✅ Kiểm tra: Folder có ảnh trong image_gen/

## 🎨 Customization

### Thay đổi màu theme:
Edit `styles.css`:
```css
.sidebar-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
```

### Thay đổi font:
```css
@import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;500;700&display=swap');

body {
    font-family: 'Roboto', sans-serif;
}
```

## 🚨 Troubleshooting

### Server không start:
```bash
# Check port 5000
netstat -ano | findstr :5000
# Kill process if needed
taskkill /PID <PID> /F
```

### Static files không load:
- Check folder `static/` tồn tại
- Check file paths trong `index_new.html`
- Check Flask static_folder config

### Dark mode không hoạt động:
- Check localStorage có key `darkMode`
- Check `body.dark-mode` class được toggle
- Check CSS dark mode selectors

### Chat history không lưu:
- Check localStorage quota
- Check browser console for errors
- Clear localStorage và thử lại

## 📚 Documentation

- `REFACTORING_v2.0.md`: Chi tiết refactoring
- `EXPORT_PDF_FEATURE.md`: PDF export guide
- `MEMORY_WITH_IMAGES_FEATURE.md`: Memory feature
- `IMAGE_GENERATION_TOOL_GUIDE.md`: Image generation

## ⚙️ Dependencies

- Flask (backend)
- Tailwind CSS (CDN)
- Marked.js (Markdown)
- Highlight.js (Code syntax)
- jsPDF (PDF generation)
- html2canvas (HTML to canvas)

## 🎯 Next Steps

1. ✅ Test extensively
2. ⏳ Migrate old chats to new format (if needed)
3. ⏳ Add more Tailwind customization
4. ⏳ Optimize bundle size (custom Tailwind build)
5. ⏳ Add unit tests

---

**Version**: 2.0.0  
**Last Updated**: 2025-10-29  
**Status**: ✅ Production Ready
