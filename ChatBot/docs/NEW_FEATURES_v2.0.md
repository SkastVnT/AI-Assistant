# 🚀 New Features Documentation - ChatBot v2.0

## Tổng quan phiên bản 2.0

Phiên bản 2.0 mang đến nhiều cải tiến quan trọng về UI/UX, quản lý file, và trải nghiệm người dùng.

---

## 📋 Table of Contents

1. [UI/UX Improvements](#1-uiux-improvements)
2. [Storage Display Enhancement](#2-storage-display-enhancement)
3. [Stop Generation Feature](#3-stop-generation-feature)
4. [Message History Versioning](#4-message-history-versioning)
5. [File Upload Revolution](#5-file-upload-revolution)
6. [Auto-File Analysis](#6-auto-file-analysis)
7. [Technical Implementation](#7-technical-implementation)

---

## 1. UI/UX Improvements

### 1.1 Full-Screen ChatGPT-like Layout

**Trước đây:**
- Chat container giới hạn 500px height
- Có padding và margins không cần thiết
- Không tận dụng không gian màn hình

**Bây giờ:**
```css
body {
    height: 100vh;
    overflow: hidden;
}

.main-wrapper {
    height: 100vh;
    max-width: 100%;
}

.chat-container {
    flex: 1;
    overflow-y: auto;
}
```

**Lợi ích:**
- Tận dụng 100% không gian màn hình
- Messages hiển thị rộng hơn (85% width thay vì 70%)
- Trải nghiệm tương tự ChatGPT

### 1.2 Enhanced Chat Items Visibility

**Cải tiến sidebar chat items:**
- ✅ Borders và shadows rõ ràng hơn
- ✅ Icons phân biệt: 💬 (chat thường) vs ✨ (chat đặc biệt)
- ✅ Active state với solid blue color (#667eea)
- ✅ White indicator bar bên trái khi active
- ✅ Loại bỏ transform animations gây distraction

```css
.chat-item.active {
    background: #667eea;
    color: white;
    border-left: 4px solid white;
}
```

### 1.3 GitHub Badge Integration

**Thêm attribution badge ở header:**
```html
<a href="https://github.com/SkastVnT/AI-Assistant" class="github-badge">
    <svg><!-- GitHub icon --></svg>
    <span>@SkastVnT</span>
</a>
```

**Features:**
- SVG icon với smooth hover effects
- Responsive: hide text on mobile, show icon only
- Dark mode support
- Opens in new tab

### 1.4 Centered Header Title

**Layout improvement:**
```css
.header > div {
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.header > div > div {
    text-align: center;
    flex: 1;
}
```

---

## 2. Storage Display Enhancement

### 2.1 Fancy Progress Bar

**Trước:**
```
📊 Lưu trữ: 0.00MB / 200MB (0%)
```

**Sau:**
```
💚 0.00MB / 200MB    [Tốt]
[████░░░░░░░░░░░░] 
0% đã dùng    [🗑️ Dọn dẹp]
```

### 2.2 Implementation

```javascript
updateStorageDisplay(storageInfo) {
    const { sizeInMB, maxSizeMB, percentage, color } = storageInfo;
    
    let statusIcon = '💚', statusText = 'Tốt';
    if (percentage > 80) {
        statusIcon = '🔴';
        statusText = 'Đầy';
    } else if (percentage > 50) {
        statusIcon = '🟡';
        statusText = 'Cảnh báo';
    }
    
    // Render with progress bar
}
```

### 2.3 Features

- **Status Icons:**
  - 💚 Green: 0-50% (Tốt)
  - 🟡 Yellow: 50-80% (Cảnh báo)
  - 🔴 Red: 80-100% (Đầy)

- **Progress Bar:**
  - Animated width transition
  - Dynamic color based on usage
  - Gradient background
  - Box shadow effects

- **Cleanup Button:**
  - Hover effects
  - One-click cleanup
  - Keeps 5 most recent chats

---

## 3. Stop Generation Feature

### 3.1 Overview

Cho phép người dùng dừng AI generation giữa chừng và giữ lại partial response.

### 3.2 User Interface

**Loading Indicator with Stop Button:**
```html
<div class="loading" id="loading">
    <div class="spinner"></div>
    <span>Đang suy nghĩ...</span>
    <button class="stop-generation-btn" id="stopGenerationBtn">
        ⏹️ Dừng lại
    </button>
</div>
```

**Styling:**
```css
.stop-generation-btn {
    background: linear-gradient(135deg, #ff5252 0%, #d32f2f 100%);
    color: white;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(211, 47, 47, 0.3);
}
```

### 3.3 Technical Implementation

**AbortController Integration:**
```javascript
// In sendMessage()
this.currentAbortController = new AbortController();

const data = await this.apiService.sendMessage(
    message,
    model,
    context,
    tools,
    deepThinking,
    history,
    files,
    memories,
    this.currentAbortController.signal  // ← AbortSignal
);
```

**Stop Handler:**
```javascript
stopGeneration() {
    if (this.currentAbortController) {
        this.currentAbortController.abort();
        
        // Add stopped indicator
        const stoppedIndicator = document.createElement('div');
        stoppedIndicator.className = 'message-stopped-indicator';
        stoppedIndicator.innerHTML = '⏹️ <em>Đã dừng bởi người dùng</em>';
        
        // Save partial response to history
        this.saveCurrentSession(true);
    }
}
```

### 3.4 Stopped Message Indicator

```css
.message-stopped-indicator {
    margin-top: 10px;
    padding: 8px 12px;
    background: rgba(255, 152, 0, 0.1);
    border-left: 3px solid #ff9800;
    color: #f57c00;
}
```

**Displayed as:**
```
⏹️ Đã dừng bởi người dùng
```

---

## 4. Message History Versioning

### 4.1 Concept

Khi user dừng generation và gửi tin nhắn mới, tạo các versions:
- Version 1: Partial response (stopped)
- Version 2: New complete response
- Version 3: Another regeneration
- ...

### 4.2 Data Structure

```javascript
messageHistory = {
    'msg_1234567890': [
        {
            version: 1,
            content: 'Partial response...',
            timestamp: '13:45:22',
            model: 'gemini',
            context: 'casual',
            stopped: true
        },
        {
            version: 2,
            content: 'Complete response...',
            timestamp: '13:46:10',
            model: 'gemini',
            context: 'casual',
            stopped: false
        }
    ]
}
```

### 4.3 Implementation

**Save to History:**
```javascript
// After receiving response
if (!this.messageHistory[this.currentMessageId]) {
    this.messageHistory[this.currentMessageId] = [];
}

this.messageHistory[this.currentMessageId].push({
    version: this.messageHistory[this.currentMessageId].length + 1,
    content: responseContent,
    timestamp: responseTimestamp,
    model: formValues.model,
    context: formValues.context,
    stopped: false
});
```

### 4.4 Future Enhancement Ideas

- UI to browse through versions
- Compare different versions side-by-side
- Restore previous version
- Merge content from multiple versions

---

## 5. File Upload Revolution

### 5.1 Old vs New

**Trước đây:**
```
Input Area:
┌─────────────────────────┐
│ [📎 file1.txt] [x]     │
│ [📎 file2.py]  [x]     │
│ [Message input...]      │
└─────────────────────────┘
```

**Bây giờ:**
```
Chat Container:
┌─────────────────────────┐
│ User Message            │
├─────────────────────────┤
│ 📎 Đã tải lên 2 files  │
│ ┌──────┐ ┌──────┐      │
│ │ 📄   │ │ 🐍   │      │
│ │file1 │ │file2 │      │
│ └──────┘ └──────┘      │
├─────────────────────────┤
│ AI: [Auto analysis...]  │
└─────────────────────────┘
```

### 5.2 File Message Component

```javascript
addFileMessage(chatContainer, files, timestamp) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message file-message user';
    
    // Header
    const header = `📎 Đã tải lên ${files.length} files`;
    
    // File cards grid
    const filesGrid = files.map(file => `
        <div class="file-message-card">
            ${file.preview ? 
                `<img src="${file.preview}">` : 
                `<div class="file-message-icon">${icon}</div>`
            }
            <div class="file-message-name">${file.name}</div>
            <div class="file-message-meta">${size}</div>
        </div>
    `).join('');
    
    // Append to chat
    chatContainer.appendChild(messageDiv);
}
```

### 5.3 CSS Styling

```css
.file-message {
    justify-content: flex-end;
}

.file-message .message-content {
    background: linear-gradient(135deg, 
        rgba(102, 126, 234, 0.1) 0%, 
        rgba(118, 75, 162, 0.1) 100%);
    border: 2px solid rgba(102, 126, 234, 0.3);
    max-width: 90%;
}

.file-message-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 10px;
}

.file-message-card {
    background: white;
    border-radius: 8px;
    padding: 10px;
    transition: all 0.2s;
}

.file-message-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
}
```

### 5.4 Supported File Types

| Type | Icon | Processing |
|------|------|-----------|
| Images (jpg, png, gif) | 🖼️ | Base64 + Preview |
| Python (.py) | 🐍 | Text content |
| JavaScript (.js) | 📜 | Text content |
| HTML (.html) | 🌐 | Text content |
| CSS (.css) | 🎨 | Text content |
| JSON (.json) | 📋 | Text content |
| PDF (.pdf) | 📕 | Base64 (backend) |
| Word (.doc, .docx) | 📘 | Base64 (backend) |
| Excel (.xlsx) | 📊 | Base64 (backend) |
| Text (.txt) | 📄 | Text content |

---

## 6. Auto-File Analysis

### 6.1 Workflow

```
1. User uploads file(s)
   ↓
2. Files processed & displayed in chat
   ↓
3. Auto-generate analysis prompt
   ↓
4. Send to AI (no user action needed)
   ↓
5. Display analysis result
```

### 6.2 Analysis Prompt Template

```javascript
async analyzeUploadedFiles(files) {
    let prompt = `📎 **Phân tích file đã tải lên:**\n\n`;
    prompt += `Có ${files.length} file được tải lên.\n\n`;
    
    files.forEach((file, index) => {
        prompt += `**File ${index + 1}: ${file.name}**\n`;
        prompt += `- Loại: ${file.type}\n`;
        prompt += `- Kích thước: ${formatSize(file.size)}\n`;
        
        if (file.content && !file.content.startsWith('data:')) {
            // Text content
            const maxLength = 15000;
            const content = file.content.length > maxLength 
                ? file.content.substring(0, maxLength) + '\n...(truncated)'
                : file.content;
            prompt += `\n**Nội dung:**\n\`\`\`\n${content}\n\`\`\`\n`;
        }
        prompt += `\n---\n\n`;
    });
    
    prompt += `\n**Yêu cầu phân tích:**\n`;
    prompt += `1. Tóm tắt nội dung chính\n`;
    prompt += `2. Phát hiện vấn đề/điểm đặc biệt\n`;
    prompt += `3. Nhận xét và đề xuất\n`;
    prompt += `4. Trả lời câu hỏi liên quan\n`;
    
    // Send to AI automatically
    await this.apiService.sendMessage(prompt, ...);
}
```

### 6.3 Example Analysis Output

**Input:** `example.py` (Python code)

**AI Output:**
```markdown
📎 **Phân tích file: example.py**

## 📋 Tóm tắt
File này chứa implementation của một chatbot Flask với các tính năng:
- Multi-model support (GPT-4, Gemini, Local models)
- Image generation integration
- Memory management system

## 🔍 Phát hiện
1. ✅ Code structure rõ ràng với separation of concerns
2. ⚠️ Missing error handling trong một số API calls
3. ⚠️ Hardcoded API keys (nên dùng environment variables)

## 💡 Đề xuất
1. Thêm try-catch blocks cho API calls
2. Move API keys to .env file
3. Add rate limiting cho API endpoints
4. Implement logging system

## 📊 Statistics
- Lines of code: 450
- Functions: 25
- Classes: 3
- Dependencies: 10
```

### 6.4 Configuration

**File Size Limits:**
```javascript
const FILE_SIZE_LIMITS = {
    maxFileSize: 10 * 1024 * 1024,  // 10MB per file
    maxTotalSize: 50 * 1024 * 1024,  // 50MB total
    maxContentLength: 15000  // 15KB for text analysis
};
```

**Supported Extensions:**
```javascript
const SUPPORTED_EXTENSIONS = [
    '.txt', '.md', '.json',
    '.py', '.js', '.html', '.css',
    '.pdf', '.doc', '.docx',
    '.jpg', '.png', '.gif', '.webp'
];
```

---

## 7. Technical Implementation

### 7.1 Module Architecture

```
static/js/
├── main.js                    # Main app controller
├── modules/
│   ├── chat-manager.js       # Session & storage management
│   ├── api-service.js        # API communications
│   ├── ui-utils.js           # UI helpers
│   ├── message-renderer.js   # Message rendering + file messages
│   ├── file-handler.js       # File processing & management
│   ├── memory-manager.js     # Memory features
│   ├── image-gen.js          # Image generation
│   └── export-handler.js     # PDF export
```

### 7.2 Key Data Flows

**File Upload Flow:**
```
User selects file
    ↓
FileHandler.processFile()
    ↓
addFilesToSession()
    ↓
MessageRenderer.addFileMessage()
    ↓
analyzeUploadedFiles()
    ↓
APIService.sendMessage()
    ↓
MessageRenderer.addMessage() (AI response)
```

**Stop Generation Flow:**
```
User clicks Stop button
    ↓
stopGeneration()
    ↓
AbortController.abort()
    ↓
Catch AbortError
    ↓
Add stopped indicator
    ↓
Save partial response to history
```

### 7.3 Storage Management

**ChatSession Structure:**
```javascript
class ChatSession {
    constructor(id) {
        this.id = id;
        this.title = 'Cuộc trò chuyện mới';
        this.messages = [];
        this.attachedFiles = [];  // ← New: Files for this session
        this.createdAt = new Date();
        this.updatedAt = new Date();
    }
}
```

**Timestamp Update Logic:**
```javascript
updateCurrentSession(messages, updateTimestamp = false) {
    if (this.currentChatId && this.chatSessions[this.currentChatId]) {
        this.chatSessions[this.currentChatId].messages = messages;
        
        // Only update timestamp when explicitly requested
        // (e.g., new message sent, not when switching chats)
        if (updateTimestamp) {
            this.chatSessions[this.currentChatId].updatedAt = new Date();
        }
    }
}
```

**Why This Matters:**
- Prevents chat items from "jumping" when switching
- Timestamp only updates on actual new messages
- Fixes the "pop-up animation" issue

### 7.4 AbortController Pattern

```javascript
// Create controller
this.currentAbortController = new AbortController();

// Pass signal to fetch
fetch('/api/endpoint', {
    signal: this.currentAbortController.signal,
    // ... other options
});

// Abort when needed
this.currentAbortController.abort();

// Handle abort error
catch (error) {
    if (error.name === 'AbortError') {
        // User cancelled - handle gracefully
    } else {
        // Real error - show to user
    }
}
```

---

## 8. Performance Optimizations

### 8.1 File Processing

**Lazy Loading:**
- Files only processed when uploaded
- Content only read when needed for analysis
- Thumbnails generated on-demand

**Compression:**
- Images compressed to 60% quality
- Max dimensions: 800x800px
- Reduces storage by ~70%

### 8.2 Storage Optimization

**Automatic Cleanup:**
```javascript
handleQuotaExceeded() {
    // Keep only 5 most recent sessions
    const sortedIds = Object.keys(this.chatSessions)
        .sort((a, b) => 
            this.chatSessions[b].updatedAt - 
            this.chatSessions[a].updatedAt
        );
    
    const idsToKeep = sortedIds.slice(0, 5);
    // Delete older sessions
}
```

**Compression Strategy:**
- Text content: As-is
- Images: Base64 JPEG 60% quality
- Large files: Truncate for analysis

### 8.3 UI Performance

**Debouncing:**
```javascript
// Auto-resize textarea
let resizeTimeout;
textarea.addEventListener('input', () => {
    clearTimeout(resizeTimeout);
    resizeTimeout = setTimeout(() => {
        textarea.style.height = 'auto';
        textarea.style.height = textarea.scrollHeight + 'px';
    }, 100);
});
```

**Virtual Scrolling:**
- Chat container uses overflow-y: auto
- Messages rendered as needed
- Smooth scrolling with CSS

---

## 9. Browser Compatibility

### 9.1 Supported Browsers

| Browser | Version | Status |
|---------|---------|--------|
| Chrome | 90+ | ✅ Full support |
| Firefox | 88+ | ✅ Full support |
| Safari | 14+ | ✅ Full support |
| Edge | 90+ | ✅ Full support |

### 9.2 Required Features

- **ES6 Modules** (import/export)
- **Fetch API** with AbortController
- **FileReader API**
- **localStorage** (200MB+)
- **CSS Grid & Flexbox**
- **CSS Custom Properties**

---

## 10. Future Enhancements

### 10.1 Planned Features

**Q1 2025:**
- [ ] Message version browsing UI
- [ ] Drag & drop file upload
- [ ] File preview modal
- [ ] Batch file operations

**Q2 2025:**
- [ ] Voice input/output
- [ ] Real-time collaboration
- [ ] Cloud sync
- [ ] Mobile app

### 10.2 Technical Debt

- [ ] Migrate to TypeScript
- [ ] Add unit tests
- [ ] Implement e2e tests
- [ ] Performance profiling
- [ ] Accessibility audit

---

## 11. Troubleshooting

### 11.1 Common Issues

**Files not uploading:**
```javascript
// Check console for errors
console.log('File size:', file.size);
console.log('File type:', file.type);

// Verify file size limits
if (file.size > 10 * 1024 * 1024) {
    alert('File too large! Max 10MB');
}
```

**Auto-analysis not working:**
```javascript
// Check if API service is available
console.log('API Service:', this.apiService);

// Verify abort controller
console.log('Abort Controller:', this.currentAbortController);
```

**Storage full:**
```javascript
// Manual cleanup
window.manualCleanup();

// Check storage info
console.log(chatManager.getStorageInfo());
```

### 11.2 Debug Mode

```javascript
// Enable debug logging
localStorage.setItem('DEBUG', 'true');

// View logs
console.log('[DEBUG]', message, data);
```

---

## 12. Changelog

### v2.0.0 (Current)
- ✨ Full-screen ChatGPT-like layout
- ✨ Fancy storage display with progress bar
- ✨ Stop generation feature
- ✨ Message history versioning
- ✨ File upload in chat container
- ✨ Auto-file analysis
- 🐛 Fixed chat item timestamp update bug
- 🎨 Enhanced UI with better visibility
- 🔧 GitHub badge integration

### v1.8.0
- Added img2img support
- LoRA and VAE integration
- Memory system improvements

### v1.5.0
- Initial release
- Basic chat functionality
- Image generation

---

## 📚 References

- [Fetch API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API)
- [AbortController - MDN](https://developer.mozilla.org/en-US/docs/Web/API/AbortController)
- [FileReader API - MDN](https://developer.mozilla.org/en-US/docs/Web/API/FileReader)
- [CSS Grid Layout - MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/CSS_Grid_Layout)

---

**Last Updated:** November 4, 2025
**Version:** 2.0.0
**Author:** @SkastVnT
