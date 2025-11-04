# Migration Guide - Chuyển đổi sang Modular Architecture

## 🎯 Mục tiêu

Chuyển đổi từ inline scripts trong `index.html` sang cấu trúc modular với các file JavaScript riêng biệt.

## 📋 Các bước thực hiện

### Bước 1: Backup file gốc

```bash
cd ChatBot/templates
cp index.html index_backup.html
```

### Bước 2: Update HTML header

Trong file `index.html`, thay thế tất cả `<script>` tags (từ dòng 157 đến cuối) bằng:

```html
    <!-- Load Main Application (ES6 Module) -->
    <script type="module" src="{{ url_for('static', filename='js/main.js') }}"></script>
</body>
</html>
```

### Bước 3: Giữ lại HTML structure

**GIỮ NGUYÊN:**
- Toàn bộ HTML từ `<body>` đến dòng 156
- Tất cả các elements với id (modals, forms, containers)
- CSS links trong `<head>`
- External libraries (marked.js, highlight.js, jsPDF, html2canvas)

**XÓA:**
- Tất cả inline `<script>` tags chứa JavaScript code
- Các function definitions trong HTML

### Bước 4: Test chức năng

```bash
# Restart Flask app
cd ..
python app.py
```

Mở browser và test:
- ✅ Gửi tin nhắn
- ✅ Chuyển đổi chat
- ✅ Dark mode
- ✅ File upload
- ✅ Image generation
- ✅ Memory management
- ✅ Export PDF

### Bước 5: Debug nếu cần

Mở DevTools Console (F12) và check:

```javascript
// Check if app loaded
console.log(window.chatBotApp);

// Check modules
console.log(window.chatBotApp.chatManager);
console.log(window.chatBotApp.apiService);
```

## ⚠️ Potential Issues & Solutions

### Issue 1: Module not found

**Error:** `Failed to load module script`

**Solution:** 
- Đảm bảo Flask app đang chạy
- Check path trong `url_for('static', filename='js/main.js')`
- Verify file tồn tại: `static/js/main.js`

### Issue 2: CORS errors

**Error:** `CORS policy blocked`

**Solution:**
- Phải serve qua HTTP server (Flask)
- Không dùng `file://` protocol

### Issue 3: Global functions undefined

**Error:** `toggleCategory is not defined`

**Solution:**
Các functions cần được expose từ modules:

```javascript
// In main.js
window.toggleCategory = (category) => {
    app.imageGen.toggleCategory(category);
};
```

## 🔄 Function Mapping

### Old → New

```javascript
// OLD: Global functions
function sendMessage() { ... }

// NEW: Method của app
window.chatBotApp.sendMessage()
```

```javascript
// OLD: onclick="deleteChat('id')"
onclick="deleteChat('chat123', event)"

// NEW: Data attributes + event delegation
<button class="chat-delete-btn" data-chat-id="chat123">

// In main.js
document.querySelectorAll('.chat-delete-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const chatId = btn.dataset.chatId;
        app.handleDeleteChat(chatId);
    });
});
```

## 📝 HTML Updates Needed

### Update onclick handlers

**Before:**
```html
<button onclick="toggleCategory('hair')">Toggle</button>
```

**After:**
```html
<button class="toggle-category-btn" data-category="hair">Toggle</button>
```

Then in JavaScript:
```javascript
document.querySelectorAll('.toggle-category-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        const category = btn.dataset.category;
        app.imageGen.toggleCategory(category);
    });
});
```

### Update inline event handlers

Thay tất cả:
- `onclick="..."`
- `onchange="..."`
- `oninput="..."`

Bằng event listeners trong main.js

## 🛠️ Development Workflow

### 1. Make changes to modules

```bash
cd static/js/modules
# Edit file
nano chat-manager.js
```

### 2. Reload browser

Hard refresh: `Ctrl + Shift + R` (Clear cache)

### 3. Check console

```javascript
// Test new functionality
window.chatBotApp.chatManager.newChat();
```

## 📦 Adding New Features

### Example: Add new tool button

**1. Add HTML button:**
```html
<button class="tool-btn" id="myNewToolBtn">🔧 New Tool</button>
```

**2. Add event listener in main.js:**
```javascript
setupEventListeners() {
    // ... existing code ...
    
    if (elements.myNewToolBtn) {
        elements.myNewToolBtn.addEventListener('click', () => {
            this.handleNewTool();
        });
    }
}
```

**3. Add handler method:**
```javascript
handleNewTool() {
    console.log('New tool clicked!');
    // Your logic here
}
```

## ✅ Verification Checklist

- [ ] App loads without errors
- [ ] Can send messages
- [ ] Can switch between chats
- [ ] Dark mode works
- [ ] File upload works
- [ ] Image generation modal opens
- [ ] Memory panel works
- [ ] Export PDF works
- [ ] All buttons functional
- [ ] No console errors

## 🚀 Benefits After Migration

✅ **Clean Separation** - HTML chỉ chứa markup, JavaScript riêng biệt

✅ **Easy Maintenance** - Mỗi module có file riêng, dễ tìm và sửa

✅ **Better Performance** - Browser có thể cache modules riêng

✅ **Scalability** - Dễ thêm features mới

✅ **Testability** - Có thể test từng module độc lập

✅ **Code Reuse** - Modules có thể reuse cho projects khác

## 📞 Support

Nếu gặp issues sau migration, check:

1. Browser console (F12)
2. Flask logs
3. Network tab (check if modules loaded)
4. Verify file paths

## 🎓 Learning Resources

- [ES6 Modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)
- [Clean Code Principles](https://github.com/ryanmcdermott/clean-code-javascript)
- [Module Pattern](https://www.patterns.dev/posts/module-pattern/)

---

**Note:** Migration này giữ nguyên 100% functionality, chỉ refactor code structure để dễ maintain và scale hơn.
