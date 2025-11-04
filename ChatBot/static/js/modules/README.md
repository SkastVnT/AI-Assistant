# ChatBot JavaScript Modules

Cấu trúc code đã được refactor theo chuẩn **Clean Code** và **Modular Design**.

## 📁 Cấu trúc thư mục

```
static/js/
├── config.js                 # Configuration constants
├── main.js                   # Application entry point
└── modules/
    ├── api-service.js        # API communication layer
    ├── chat-manager.js       # Chat session management
    ├── export-handler.js     # PDF/Text export functionality
    ├── file-handler.js       # File upload & management
    ├── image-gen.js          # Stable Diffusion image generation
    ├── memory-manager.js     # AI learning/memory system
    ├── message-renderer.js   # Message rendering & markdown
    └── ui-utils.js           # UI utilities & DOM manipulation
```

## 📦 Modules

### 1. **main.js** - Entry Point
- Khởi tạo và kết nối tất cả modules
- Quản lý application state
- Xử lý event listeners chính

```javascript
import { ChatBotApp } from './main.js';
const app = new ChatBotApp();
app.init();
```

### 2. **config.js** - Configuration
- Chứa tất cả constants và settings
- Model names, API endpoints
- UI settings, storage limits

```javascript
import { CONFIG } from './config.js';
const modelName = CONFIG.MODEL_NAMES['gemini'];
```

### 3. **chat-manager.js** - Chat Session Management
**Class:** `ChatManager`, `ChatSession`

**Chức năng:**
- Quản lý chat sessions (CRUD)
- LocalStorage persistence
- Compression & storage management
- Title generation

**Key Methods:**
```javascript
loadSessions()
saveSessions()
newChat()
switchChat(chatId)
deleteChat(chatId)
manualCleanup(keepCount)
generateTitle(message)
```

### 4. **api-service.js** - API Communication
**Class:** `APIService`

**Chức năng:**
- Wrapper cho tất cả API calls
- Error handling
- Request/Response formatting

**Key Methods:**
```javascript
sendMessage(message, model, context, ...)
checkLocalModelsStatus()
checkSDStatus()
loadSDModels()
generateImage(params)
generateImg2Img(params)
saveMemory(title, content, images)
```

### 5. **ui-utils.js** - UI Utilities
**Class:** `UIUtils`

**Chức năng:**
- DOM manipulation
- Modal management
- Theme toggle (dark/light mode)
- Sidebar controls
- Loading states

**Key Methods:**
```javascript
initElements()
showLoading() / hideLoading()
openModal(id) / closeModal(id)
toggleDarkMode()
toggleSidebar()
updateStorageDisplay(info)
renderChatList(sessions, ...)
```

### 6. **message-renderer.js** - Message Rendering
**Class:** `MessageRenderer`

**Chức năng:**
- Render messages với Markdown
- Code syntax highlighting
- Copy to clipboard
- Edit message functionality
- Image click handlers

**Key Methods:**
```javascript
addMessage(container, content, isUser, model, context, timestamp)
copyMessageToClipboard(content, button)
copyTableToClipboard(table, button)
showEditForm(messageDiv, originalContent)
makeImagesClickable(onImageClick)
reattachEventListeners(container, ...)
```

### 7. **file-handler.js** - File Management
**Class:** `FileHandler`

**Chức năng:**
- File upload handling
- Paste event for files
- File list rendering
- File validation

**Key Methods:**
```javascript
setupFileInput(input, onChange)
setupPasteHandler(element, onChange)
renderFileList(container)
removeFile(index)
readFileAsBase64(file)
```

### 8. **memory-manager.js** - AI Memory System
**Class:** `MemoryManager`

**Chức năng:**
- Load/Save/Delete memories
- Memory selection
- Extract content & images from chat

**Key Methods:**
```javascript
loadMemories()
saveMemory(title, content, images)
deleteMemory(memoryId)
toggleMemory(memoryId)
getSelectedMemories()
extractImagesFromChat(container)
```

### 9. **image-gen.js** - Image Generation
**Class:** `ImageGeneration`

**Chức năng:**
- Stable Diffusion integration
- Text2Img & Img2Img
- Model/LoRA/VAE management
- Feature extraction
- Tag filtering

**Key Methods:**
```javascript
openModal()
switchTab(tabName)
generateText2Img(params)
generateImg2Img(params)
handleSourceImageUpload(file)
extractFeatures(models)
toggleTag(tagName)
```

### 10. **export-handler.js** - Export Functionality
**Class:** `ExportHandler`

**Chức năng:**
- Export chat to PDF (with images)
- Export to JSON
- Export to plain text

**Key Methods:**
```javascript
downloadChatAsPDF(container, onProgress)
downloadChatAsJSON(history)
downloadChatAsText(container)
```

## 🔄 Data Flow

```
User Action
    ↓
main.js (Event Handler)
    ↓
Module (Business Logic)
    ↓
api-service.js (API Call)
    ↓
Backend Server
    ↓
Response Processing
    ↓
ui-utils.js / message-renderer.js (Update UI)
    ↓
chat-manager.js (Save State)
```

## 🎯 Design Principles

### 1. **Separation of Concerns**
- Mỗi module có trách nhiệm riêng biệt
- UI logic tách biệt với business logic
- API calls được centralize

### 2. **Single Responsibility**
- Mỗi class/function làm 1 việc duy nhất
- Easy to test và maintain

### 3. **DRY (Don't Repeat Yourself)**
- Code reuse thông qua modules
- Shared utilities

### 4. **Modularity**
- ES6 modules với import/export
- Loose coupling, high cohesion

### 5. **Error Handling**
- Try-catch blocks
- User-friendly error messages
- Console logging for debugging

## 📝 Usage Example

```javascript
// In index.html
<script type="module" src="/static/js/main.js"></script>

// Access app instance
window.chatBotApp.sendMessage();
window.chatBotApp.openImageGenModal();
```

## 🔧 Development

### Adding New Feature

1. Tạo module mới trong `modules/`
2. Import vào `main.js`
3. Initialize trong `ChatBotApp.init()`
4. Setup event listeners
5. Update README

### Testing

```javascript
// Test individual module
import { ChatManager } from './modules/chat-manager.js';
const manager = new ChatManager();
manager.loadSessions();
console.log(manager.chatSessions);
```

## 📚 Dependencies

- **marked.js** - Markdown parsing
- **highlight.js** - Code syntax highlighting
- **jsPDF** - PDF generation
- **html2canvas** - HTML to canvas conversion

## 🚀 Benefits of Refactoring

✅ **Maintainability** - Dễ maintain và debug
✅ **Scalability** - Dễ thêm features mới
✅ **Testability** - Có thể test từng module độc lập
✅ **Readability** - Code rõ ràng, dễ hiểu
✅ **Reusability** - Modules có thể reuse
✅ **Performance** - Lazy loading, tree shaking support

## 📖 Migration Notes

### From Old Code

**Before:**
```javascript
// All code in <script> tags in index.html
function sendMessage() { ... }
let chatSessions = {};
```

**After:**
```javascript
// Modular structure
import { ChatBotApp } from './main.js';
const app = new ChatBotApp();
app.sendMessage();
```

### Breaking Changes

⚠️ Global functions are now methods of `window.chatBotApp`
⚠️ Variables are encapsulated in classes
⚠️ Need to use ES6 module imports

## 🔍 Debugging

```javascript
// Enable verbose logging
console.log('[Module Name] Action:', data);

// Access app state
console.log(window.chatBotApp.chatManager.chatSessions);
console.log(window.chatBotApp.activeTools);
```

## 📦 Build & Deployment

Không cần build step vì sử dụng native ES6 modules.

**Requirements:**
- Modern browser với ES6 support
- HTTP/HTTPS server (không work với `file://`)

**Production:**
- Có thể minify với tools như Terser
- Có thể bundle với Webpack/Rollup nếu muốn

---

**Author:** ChatBot Development Team
**Version:** 2.0.0 (Refactored)
**Last Updated:** November 2025
