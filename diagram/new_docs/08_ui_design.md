# 8️⃣ UI DESIGN - Thiết kế giao diện ChatBot

> **Modern Web Interface Design**  
> Responsive, Dark/Light theme, Real-time streaming, Rich formatting

---

## 📋 Mô tả

UI Design document thể hiện:
- **Layout Structure:** Sidebar + Main chat + Controls
- **Components:** Message bubbles, input box, toolbars
- **Responsive Design:** Mobile-first approach
- **Theme Support:** Dark/Light mode
- **Interactive Elements:** Buttons, modals, tooltips

---

## 🎯 Overall Layout

```
┌─────────────────────────────────────────────────────────────┐
│  Header: 🤖 AI ChatBot Assistant + GitHub Badge            │
├─────────┬───────────────────────────────────────────────────┤
│         │  Controls: Model | Mode | Tools | Theme          │
│ Sidebar ├───────────────────────────────────────────────────┤
│         │                                                   │
│ Chat    │                                                   │
│ History │               Message Display Area                │
│         │          (Scrollable, Auto-scroll)                │
│  + New  │                                                   │
│         │                                                   │
│         ├───────────────────────────────────────────────────┤
│         │  Input Box + Upload + Send Button                │
└─────────┴───────────────────────────────────────────────────┘
```

**Breakpoints:**
- Desktop: >1024px (sidebar visible)
- Tablet: 768-1024px (sidebar collapsible)
- Mobile: <768px (sidebar overlay)

---

## 🖼️ Wireframes

### Desktop View (Dark Mode)

```
┌───────────────────────────────────────────────────────────────────┐
│  Header                                                   GitHub  │
│  🤖 AI ChatBot Assistant                                 @SkastVnT│
│  Hỗ trợ tâm lý, tâm sự và giải pháp đời sống                    │
├──────────┬────────────────────────────────────────────────────────┤
│ 💬 Lịch   │ Model: [Gemini ▼] Mode: [Casual ▼] Tools: 📥🎨🧠 🌙 🗑️│
│ sử Chat  ├────────────────────────────────────────────────────────┤
│          │                                                        │
│ [+ Mới]  │  ┌──────────────────────────────────────────┐ ← User  │
│          │  │ How to use async in Python?              │         │
│ 📁 Python│  └──────────────────────────────────────────┘         │
│   Async  │                                                        │
│   (24)   │  ┌────────────────────────────────────────────┐       │
│          │  │ Here's how to use async/await:             │ ← AI  │
│ 📁 Code  │  │                                            │       │
│   Review │  │ ```python                                  │       │
│   (10)   │  │ async def fetch():                         │       │
│          │  │     ...                                    │       │
│ 📁 Tâm sự│  │ ```                                        │       │
│   (5)    │  │                                            │       │
│          │  │ [💾 Lưu] [✏️ Sửa] [⭐ 5]                   │       │
│          │  └────────────────────────────────────────────┘       │
│          │                                                        │
│          │                                                        │
│ Storage: │                                                        │
│ 125 MB   ├────────────────────────────────────────────────────────┤
│          │ ┌───────────────────────────────────────────────────┐ │
│          │ │ Type your message... [📎] [🎤]           [Send] │ │
│          │ └───────────────────────────────────────────────────┘ │
└──────────┴────────────────────────────────────────────────────────┘
```

---

### Mobile View (Collapsed Sidebar)

```
┌─────────────────────────────────────┐
│ ☰  🤖 AI ChatBot        @SkastVnT  │
├─────────────────────────────────────┤
│ Model: Gemini  Tools: 📥🎨🧠🌙     │
├─────────────────────────────────────┤
│                                     │
│  ┌───────────────────────────────┐  │
│  │ User message here             │  │
│  └───────────────────────────────┘  │
│                                     │
│  ┌─────────────────────────────────┐│
│  │ AI response with code:          ││
│  │                                 ││
│  │ ```python                       ││
│  │ async def example():            ││
│  │     pass                        ││
│  │ ```                             ││
│  │                                 ││
│  │ [💾] [✏️] [⭐]                  ││
│  └─────────────────────────────────┘│
│                                     │
├─────────────────────────────────────┤
│ ┌──────────────────────────────┐  │
│ │ Type...  [📎] [🎤]   [Send] │  │
│ └──────────────────────────────┘  │
└─────────────────────────────────────┘
```

---

## 🎨 Component Library

### 1️⃣ Header Component

**Desktop:**
```html
<div class="header">
  <div class="header-content">
    <div class="title-section">
      <h1>🤖 AI ChatBot Assistant</h1>
      <p>Hỗ trợ tâm lý, tâm sự và giải pháp đời sống</p>
    </div>
    <a href="https://github.com/..." class="github-badge">
      <svg>...</svg>
      <span>@SkastVnT</span>
    </a>
  </div>
</div>
```

**Styles:**
```css
.header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  color: white;
  border-radius: 10px;
  margin-bottom: 20px;
}

.header h1 {
  font-size: 28px;
  margin-bottom: 5px;
  display: flex;
  align-items: center;
  gap: 10px;
}

.github-badge {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  text-decoration: none;
  color: white;
  transition: all 0.3s;
}

.github-badge:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.05);
}
```

---

### 2️⃣ Sidebar Component

**Structure:**
```html
<div class="sidebar" id="sidebar">
  <!-- Header -->
  <div class="sidebar-header">
    <h3>💬 Lịch sử Chat</h3>
    <button class="new-chat-btn">+ Mới</button>
  </div>
  
  <!-- Storage Info -->
  <div class="storage-info">
    <span>Storage: 125 MB / 10 GB</span>
  </div>
  
  <!-- Chat List -->
  <div class="chat-list">
    <div class="chat-item active">
      <div class="chat-icon">📁</div>
      <div class="chat-info">
        <div class="chat-title">Python Async Tutorial</div>
        <div class="chat-meta">
          <span class="message-count">24 tin</span>
          <span class="timestamp">2h trước</span>
        </div>
      </div>
      <button class="delete-chat-btn">🗑️</button>
    </div>
    
    <!-- More chat items... -->
  </div>
</div>
```

**Styles:**
```css
.sidebar {
  width: 280px;
  background: #1e1e1e;
  border-right: 1px solid #333;
  display: flex;
  flex-direction: column;
  height: 100vh;
}

.sidebar-header {
  padding: 20px;
  border-bottom: 1px solid #333;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.new-chat-btn {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  padding: 8px 16px;
  border-radius: 20px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s;
}

.new-chat-btn:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

.chat-item {
  padding: 12px 20px;
  display: flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
  transition: background 0.2s;
  border-left: 3px solid transparent;
}

.chat-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

.chat-item.active {
  background: rgba(102, 126, 234, 0.1);
  border-left-color: #667eea;
}

.chat-info {
  flex: 1;
  min-width: 0;
}

.chat-title {
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chat-meta {
  font-size: 12px;
  color: #888;
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
```

---

### 3️⃣ Control Bar Component

```html
<div class="controls">
  <!-- Model Selection -->
  <label>
    Model:
    <select id="modelSelect">
      <option value="gemini">Gemini (Google) - FREE</option>
      <option value="gpt-4o">GPT-4o (OpenAI)</option>
      <option value="deepseek">DeepSeek</option>
      <optgroup label="🖥️ Local Models">
        <option value="qwen-local">Qwen2.5-14B Local ⭐</option>
      </optgroup>
    </select>
  </label>
  
  <!-- Mode Selection -->
  <label>
    Chế độ:
    <select id="contextSelect">
      <option value="casual">Trò chuyện vui vẻ</option>
      <option value="programming">💻 Lập trình</option>
    </select>
  </label>
  
  <!-- Tools -->
  <button class="tool-btn" title="Tải chat">📥</button>
  <button class="tool-btn" title="Tạo ảnh">🎨</button>
  <button class="tool-btn" title="AI học">🧠</button>
  <button class="tool-btn" id="darkModeBtn">🌙</button>
  <button class="tool-btn danger" id="clearBtn">🗑️</button>
</div>
```

**Styles:**
```css
.controls {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  padding: 15px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 10px;
  margin-bottom: 20px;
}

.controls select {
  padding: 8px 12px;
  background: #2a2a2a;
  border: 1px solid #444;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
}

.controls select:hover {
  border-color: #667eea;
}

.tool-btn {
  padding: 8px 16px;
  background: #2a2a2a;
  border: 1px solid #444;
  color: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 16px;
}

.tool-btn:hover {
  background: #667eea;
  border-color: #667eea;
  transform: translateY(-2px);
}

.tool-btn.danger:hover {
  background: #dc3545;
  border-color: #dc3545;
}
```

---

### 4️⃣ Message Component

**User Message:**
```html
<div class="message user-message">
  <div class="message-avatar">👤</div>
  <div class="message-content">
    <div class="message-text">
      How to use async/await in Python?
    </div>
    <div class="message-time">14:30</div>
  </div>
</div>
```

**AI Message:**
```html
<div class="message ai-message">
  <div class="message-avatar">🤖</div>
  <div class="message-content">
    <div class="message-text">
      Here's how to use async/await in Python:
      
      <pre><code class="language-python">
async def fetch_data():
    await asyncio.sleep(1)
    return 'Data'
      </code></pre>
      
      <div class="message-images">
        <img src="..." alt="Diagram" />
      </div>
    </div>
    
    <div class="message-actions">
      <button class="action-btn" title="Lưu vào Memory">💾</button>
      <button class="action-btn" title="Sửa">✏️</button>
      <button class="action-btn" title="Copy">📋</button>
      <div class="rating">
        <span class="star">⭐</span>
        <span class="star">⭐</span>
        <span class="star">⭐</span>
        <span class="star">⭐</span>
        <span class="star">⭐</span>
      </div>
    </div>
    
    <div class="message-time">14:31</div>
  </div>
</div>
```

**Styles:**
```css
.message {
  display: flex;
  gap: 12px;
  margin-bottom: 20px;
  animation: slideIn 0.3s ease;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.user-message {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}

.user-message .message-avatar {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.ai-message .message-avatar {
  background: linear-gradient(135deg, #f093fb, #f5576c);
}

.message-content {
  max-width: 70%;
  background: #2a2a2a;
  padding: 12px 16px;
  border-radius: 12px;
  position: relative;
}

.user-message .message-content {
  background: linear-gradient(135deg, #667eea, #764ba2);
}

.message-text {
  color: white;
  line-height: 1.6;
  word-wrap: break-word;
}

/* Code blocks */
.message-text pre {
  background: #1e1e1e;
  padding: 12px;
  border-radius: 6px;
  overflow-x: auto;
  margin: 10px 0;
}

.message-text code {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
}

/* Images */
.message-images {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.message-images img {
  width: 100%;
  border-radius: 8px;
  cursor: pointer;
  transition: transform 0.3s;
}

.message-images img:hover {
  transform: scale(1.05);
}

/* Actions */
.message-actions {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  align-items: center;
}

.action-btn {
  background: rgba(255, 255, 255, 0.1);
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  transition: all 0.3s;
}

.action-btn:hover {
  background: rgba(255, 255, 255, 0.2);
  transform: scale(1.1);
}

/* Rating stars */
.rating {
  display: flex;
  gap: 4px;
}

.star {
  cursor: pointer;
  font-size: 16px;
  opacity: 0.3;
  transition: all 0.3s;
}

.star.active,
.star:hover {
  opacity: 1;
  transform: scale(1.2);
}

.message-time {
  font-size: 12px;
  color: #888;
  margin-top: 8px;
}
```

---

### 5️⃣ Input Box Component

```html
<div class="input-container">
  <div class="input-wrapper">
    <!-- File Upload (Hidden) -->
    <input type="file" id="fileInput" hidden />
    
    <!-- Text Input -->
    <textarea 
      id="messageInput" 
      placeholder="Nhập tin nhắn... (Shift+Enter xuống dòng)"
      rows="1"
    ></textarea>
    
    <!-- Action Buttons -->
    <div class="input-actions">
      <button class="attach-btn" title="Đính kèm file">📎</button>
      <button class="voice-btn" title="Voice input">🎤</button>
      <button class="send-btn" id="sendBtn">
        <span>Gửi</span>
        <svg>...</svg>
      </button>
    </div>
  </div>
  
  <!-- File Preview (when file selected) -->
  <div class="file-preview" id="filePreview" style="display: none;">
    <div class="file-info">
      <span class="file-icon">📄</span>
      <span class="file-name">document.pdf</span>
      <span class="file-size">2.4 MB</span>
    </div>
    <button class="remove-file-btn">✕</button>
  </div>
  
  <!-- Stop Button (while generating) -->
  <button class="stop-btn" id="stopBtn" style="display: none;">
    ⏹️ Dừng
  </button>
</div>
```

**Styles:**
```css
.input-container {
  position: sticky;
  bottom: 0;
  background: #1e1e1e;
  padding: 20px;
  border-top: 1px solid #333;
}

.input-wrapper {
  display: flex;
  gap: 12px;
  align-items: flex-end;
  background: #2a2a2a;
  border: 2px solid #444;
  border-radius: 12px;
  padding: 12px;
  transition: border-color 0.3s;
}

.input-wrapper:focus-within {
  border-color: #667eea;
}

#messageInput {
  flex: 1;
  background: transparent;
  border: none;
  color: white;
  font-size: 16px;
  resize: none;
  max-height: 200px;
  overflow-y: auto;
}

#messageInput:focus {
  outline: none;
}

.input-actions {
  display: flex;
  gap: 8px;
}

.attach-btn,
.voice-btn {
  background: transparent;
  border: none;
  font-size: 20px;
  cursor: pointer;
  padding: 8px;
  border-radius: 6px;
  transition: all 0.3s;
}

.attach-btn:hover,
.voice-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.send-btn {
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  padding: 10px 24px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 8px;
  transition: all 0.3s;
}

.send-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
}

.send-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* File Preview */
.file-preview {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: rgba(102, 126, 234, 0.1);
  padding: 12px;
  border-radius: 8px;
  margin-top: 12px;
}

.file-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-icon {
  font-size: 24px;
}

.file-name {
  font-weight: 600;
}

.file-size {
  font-size: 12px;
  color: #888;
}

.remove-file-btn {
  background: transparent;
  border: none;
  color: #dc3545;
  font-size: 20px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.remove-file-btn:hover {
  background: rgba(220, 53, 69, 0.2);
}

/* Stop Button */
.stop-btn {
  width: 100%;
  background: #dc3545;
  color: white;
  border: none;
  padding: 12px;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  margin-top: 12px;
  transition: all 0.3s;
}

.stop-btn:hover {
  background: #c82333;
  transform: scale(1.02);
}
```

---

### 6️⃣ Loading States

**Typing Indicator:**
```html
<div class="message ai-message">
  <div class="message-avatar">🤖</div>
  <div class="message-content">
    <div class="typing-indicator">
      <span></span>
      <span></span>
      <span></span>
    </div>
  </div>
</div>
```

**Styles:**
```css
.typing-indicator {
  display: flex;
  gap: 4px;
  padding: 8px;
}

.typing-indicator span {
  width: 8px;
  height: 8px;
  background: #667eea;
  border-radius: 50%;
  animation: typing 1.4s infinite;
}

.typing-indicator span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-indicator span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}
```

---

### 7️⃣ Modal Component (Image Generation)

```html
<div class="modal" id="imageGenModal">
  <div class="modal-content">
    <div class="modal-header">
      <h2>🎨 Tạo ảnh bằng AI</h2>
      <button class="close-btn">✕</button>
    </div>
    
    <div class="modal-body">
      <label>
        Prompt:
        <textarea 
          id="imagePrompt" 
          placeholder="Mô tả ảnh bạn muốn tạo..."
          rows="4"
        ></textarea>
      </label>
      
      <div class="modal-options">
        <label>
          Size:
          <select id="imageSize">
            <option value="512x512">512x512</option>
            <option value="1024x1024">1024x1024</option>
          </select>
        </label>
        
        <label>
          Steps:
          <input type="number" id="imageSteps" value="20" min="10" max="50" />
        </label>
      </div>
      
      <button class="generate-btn">
        ⚡ Tạo ảnh
      </button>
      
      <div class="generation-progress" id="generationProgress">
        <div class="progress-bar"></div>
        <span class="progress-text">Đang tạo ảnh... 45%</span>
      </div>
      
      <div class="generated-image" id="generatedImage">
        <img src="" alt="Generated image" />
      </div>
    </div>
  </div>
</div>
```

**Styles:**
```css
.modal {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.8);
  z-index: 1000;
  align-items: center;
  justify-content: center;
}

.modal.active {
  display: flex;
}

.modal-content {
  background: #1e1e1e;
  border-radius: 12px;
  max-width: 600px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px;
  border-bottom: 1px solid #333;
}

.close-btn {
  background: transparent;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
  transition: all 0.3s;
}

.close-btn:hover {
  background: rgba(255, 255, 255, 0.1);
}

.modal-body {
  padding: 20px;
}

.modal-body textarea {
  width: 100%;
  background: #2a2a2a;
  border: 1px solid #444;
  color: white;
  padding: 12px;
  border-radius: 8px;
  resize: vertical;
}

.modal-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin: 20px 0;
}

.generate-btn {
  width: 100%;
  background: linear-gradient(135deg, #667eea, #764ba2);
  color: white;
  border: none;
  padding: 12px;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
}

.generate-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.5);
}

.generation-progress {
  display: none;
  margin-top: 20px;
}

.generation-progress.active {
  display: block;
}

.progress-bar {
  height: 4px;
  background: #667eea;
  border-radius: 2px;
  animation: progress 2s infinite;
}

@keyframes progress {
  0% { width: 0%; }
  50% { width: 70%; }
  100% { width: 100%; }
}

.progress-text {
  display: block;
  text-align: center;
  margin-top: 8px;
  color: #888;
}

.generated-image {
  display: none;
  margin-top: 20px;
}

.generated-image.active {
  display: block;
}

.generated-image img {
  width: 100%;
  border-radius: 8px;
}
```

---

## 🎨 Theme System

### Dark Mode (Default)

```css
:root {
  --bg-primary: #121212;
  --bg-secondary: #1e1e1e;
  --bg-tertiary: #2a2a2a;
  --text-primary: #ffffff;
  --text-secondary: #888888;
  --border-color: #333333;
  --accent-color: #667eea;
  --accent-gradient: linear-gradient(135deg, #667eea, #764ba2);
}
```

### Light Mode

```css
[data-theme="light"] {
  --bg-primary: #ffffff;
  --bg-secondary: #f5f5f5;
  --bg-tertiary: #e0e0e0;
  --text-primary: #000000;
  --text-secondary: #666666;
  --border-color: #dddddd;
  --accent-color: #667eea;
  --accent-gradient: linear-gradient(135deg, #667eea, #764ba2);
}
```

**Toggle implementation:**
```javascript
const darkModeBtn = document.getElementById('darkModeBtn');
let isDarkMode = true;

darkModeBtn.addEventListener('click', () => {
  isDarkMode = !isDarkMode;
  document.documentElement.setAttribute(
    'data-theme', 
    isDarkMode ? 'dark' : 'light'
  );
  darkModeBtn.textContent = isDarkMode ? '🌙' : '☀️';
  localStorage.setItem('theme', isDarkMode ? 'dark' : 'light');
});
```

---

## 📱 Responsive Design

### Breakpoints

```css
/* Mobile */
@media (max-width: 768px) {
  .sidebar {
    position: fixed;
    left: -280px;
    transition: left 0.3s;
    z-index: 999;
  }
  
  .sidebar.active {
    left: 0;
  }
  
  .sidebar-toggle {
    display: block;
    position: fixed;
    top: 20px;
    left: 20px;
    z-index: 998;
    background: #667eea;
    color: white;
    border: none;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    font-size: 24px;
    cursor: pointer;
  }
  
  .message-content {
    max-width: 90%;
  }
  
  .controls {
    flex-direction: column;
  }
}

/* Tablet */
@media (min-width: 768px) and (max-width: 1024px) {
  .sidebar {
    width: 240px;
  }
  
  .message-content {
    max-width: 80%;
  }
}

/* Desktop */
@media (min-width: 1024px) {
  .sidebar-toggle {
    display: none;
  }
}
```

---

## ⚡ Animations & Transitions

### Message Slide In
```css
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message {
  animation: slideIn 0.4s ease;
}
```

### Button Hover
```css
.button {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.button:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}
```

### Typing Indicator
```css
@keyframes typing {
  0%, 60%, 100% {
    transform: translateY(0);
    opacity: 0.7;
  }
  30% {
    transform: translateY(-10px);
    opacity: 1;
  }
}
```

---

## 🔧 JavaScript Interactions

### Auto-resize Textarea
```javascript
const messageInput = document.getElementById('messageInput');

messageInput.addEventListener('input', function() {
  this.style.height = 'auto';
  this.style.height = (this.scrollHeight) + 'px';
});
```

### Real-time Streaming
```javascript
async function streamAIResponse(prompt) {
  const response = await fetch('/api/chat/stream', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({message: prompt})
  });
  
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  
  let messageDiv = createMessageElement('ai');
  
  while (true) {
    const {done, value} = await reader.read();
    if (done) break;
    
    const chunk = decoder.decode(value);
    messageDiv.querySelector('.message-text').innerHTML += chunk;
    
    // Auto-scroll
    messageDiv.scrollIntoView({behavior: 'smooth', block: 'end'});
  }
}
```

---

<div align="center">

**UI Framework:** Vanilla CSS + JavaScript  
**Theme:** Dark/Light toggle  
**Responsive:** Mobile-first design

[⬅️ Back: Image Storage](07_image_storage_design.md) | [🏠 Diagram Index](../README.md)

</div>
