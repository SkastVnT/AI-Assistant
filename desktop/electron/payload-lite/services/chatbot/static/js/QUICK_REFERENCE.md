# 🚀 Quick Reference - Modular ChatBot

## 📦 Import Modules

```javascript
import { ChatManager } from './modules/chat-manager.js';
import { APIService } from './modules/api-service.js';
import { UIUtils } from './modules/ui-utils.js';
import { MessageRenderer } from './modules/message-renderer.js';
import { FileHandler } from './modules/file-handler.js';
import { MemoryManager } from './modules/memory-manager.js';
import { ImageGeneration } from './modules/image-gen.js';
import { ExportHandler } from './modules/export-handler.js';
import { CONFIG } from './config.js';
```

## 🎯 Common Tasks

### Send a Message
```javascript
const app = window.chatBotApp;
await app.sendMessage();
```

### Create New Chat
```javascript
app.newChat();
```

### Switch Chat
```javascript
app.handleSwitchChat('chat_1234567890');
```

### Delete Chat
```javascript
app.handleDeleteChat('chat_1234567890');
```

### Toggle Dark Mode
```javascript
app.uiUtils.toggleDarkMode();
```

### Open Image Generation Modal
```javascript
await app.openImageGenModal();
```

### Export Chat as PDF
```javascript
await app.exportChat();
```

### Save Chat as Memory
```javascript
await app.saveCurrentChatAsMemory();
```

## 🔧 Module APIs

### ChatManager

```javascript
const chatManager = new ChatManager();

// Load sessions
chatManager.loadSessions();

// Create new chat
const chatId = chatManager.newChat();

// Switch chat
chatManager.switchChat(chatId);

// Delete chat
const result = chatManager.deleteChat(chatId);

// Save sessions
await chatManager.saveSessions();

// Manual cleanup
const result = chatManager.manualCleanup(keepCount);

// Generate title
const title = await chatManager.generateTitle(message);

// Get storage info
const info = chatManager.getStorageInfo();

// Get current session
const session = chatManager.getCurrentSession();

// Update current session
chatManager.updateCurrentSession(messages);
```

### APIService

```javascript
const apiService = new APIService();

// Send chat message
const response = await apiService.sendMessage(
    message, model, context, tools, deepThinking, history, files, memories
);

// Check local models
const status = await apiService.checkLocalModelsStatus();

// Check SD status
const sdStatus = await apiService.checkSDStatus();

// Load SD models
const models = await apiService.loadSDModels();

// Generate image (Text2Img)
const result = await apiService.generateImage(params);

// Generate image (Img2Img)
const result = await apiService.generateImg2Img(params);

// Save memory
const result = await apiService.saveMemory(title, content, images);

// Load memories
const memories = await apiService.listMemories();
```

### UIUtils

```javascript
const uiUtils = new UIUtils();

// Initialize elements
const elements = uiUtils.initElements();

// Show/hide loading
uiUtils.showLoading();
uiUtils.hideLoading();

// Open/close modal
uiUtils.openModal('imageGenModal');
uiUtils.closeModal('imageGenModal');

// Toggle dark mode
const isDark = uiUtils.toggleDarkMode();

// Toggle sidebar
uiUtils.toggleSidebar();

// Update storage display
uiUtils.updateStorageDisplay(storageInfo);

// Render chat list
uiUtils.renderChatList(sessions, currentId, onSwitch, onDelete);

// Get form values
const values = uiUtils.getFormValues();

// Clear input
uiUtils.clearInput();

// Scroll to bottom
uiUtils.scrollToBottom();
```

### MessageRenderer

```javascript
const renderer = new MessageRenderer();

// Add message
const messageDiv = renderer.addMessage(
    container, content, isUser, model, context, timestamp
);

// Copy to clipboard
await renderer.copyMessageToClipboard(content, button);

// Copy table
await renderer.copyTableToClipboard(table, button);

// Show edit form
renderer.showEditForm(messageDiv, originalContent);

// Make images clickable
renderer.makeImagesClickable(onImageClick);

// Reattach event listeners
renderer.reattachEventListeners(container, onEdit, onCopy, onImageClick);

// Set edit save callback
renderer.setEditSaveCallback(callback);
```

### FileHandler

```javascript
const fileHandler = new FileHandler();

// Setup file input
fileHandler.setupFileInput(inputElement, onChange);

// Setup paste handler
fileHandler.setupPasteHandler(element, onChange);

// Render file list
fileHandler.renderFileList(containerElement);

// Remove file
fileHandler.removeFile(index);

// Get files
const files = fileHandler.getFiles();

// Clear files
fileHandler.clearFiles();

// Read as base64
const base64 = await fileHandler.readFileAsBase64(file);

// Validate file
const isValid = fileHandler.isValidFileType(file, allowedTypes);
```

### MemoryManager

```javascript
const memoryManager = new MemoryManager(apiService);

// Load memories
const memories = await memoryManager.loadMemories();

// Save memory
const result = await memoryManager.saveMemory(title, content, images);

// Delete memory
const result = await memoryManager.deleteMemory(memoryId);

// Toggle memory selection
memoryManager.toggleMemory(memoryId);

// Get selected memories
const selected = memoryManager.getSelectedMemories();

// Clear selection
memoryManager.clearSelection();

// Render memory list
memoryManager.renderMemoryList(container, onToggle, onDelete);

// Extract images from chat
const images = memoryManager.extractImagesFromChat(container);

// Build memory content
const content = memoryManager.buildMemoryContent(container);
```

### ImageGeneration

```javascript
const imageGen = new ImageGeneration(apiService);

// Open modal
await imageGen.openModal();

// Close modal
imageGen.closeModal();

// Switch tab
imageGen.switchTab('text2img'); // or 'img2img'

// Check SD status
const isOnline = await imageGen.checkSDStatus();

// Load resources
await imageGen.loadSDModels();
await imageGen.loadSamplers();
await imageGen.loadLoras();
await imageGen.loadVaes();

// Get selected LoRAs
const loras = imageGen.getSelectedLoras('loraList');

// Generate Text2Img
const result = await imageGen.generateText2Img(params);

// Generate Img2Img
const result = await imageGen.generateImg2Img(params);

// Handle source image upload
imageGen.handleSourceImageUpload(file);

// Extract features
const data = await imageGen.extractFeatures(['deepdanbooru']);

// Toggle tag/category
imageGen.toggleTag(tagName);
imageGen.toggleCategory(categoryName);

// Get active tags
const activeTags = imageGen.getActiveTags();

// Download image
imageGen.downloadImage();
```

### ExportHandler

```javascript
const exportHandler = new ExportHandler();

// Download as PDF
const success = await exportHandler.downloadChatAsPDF(
    container, 
    (status) => console.log(status)
);

// Download as JSON
exportHandler.downloadChatAsJSON(chatHistory);

// Download as Text
exportHandler.downloadChatAsText(container);
```

## ⚙️ Configuration

```javascript
import { CONFIG } from './config.js';

// Model names
const modelName = CONFIG.MODEL_NAMES['gemini'];

// Context names
const contextName = CONFIG.CONTEXT_NAMES['casual'];

// Storage settings
const maxSize = CONFIG.STORAGE.MAX_SIZE_MB;

// Image generation defaults
const defaultWidth = CONFIG.IMAGE_GEN.DEFAULT_WIDTH;

// API endpoints
const chatEndpoint = CONFIG.API_ENDPOINTS.CHAT;
```

## 🐛 Debugging

### Check App State
```javascript
// Access app instance
const app = window.chatBotApp;

// Check manager
console.log(app.chatManager.chatSessions);
console.log(app.chatManager.currentChatId);

// Check tools
console.log(app.activeTools);

// Check modules
console.dir(app.apiService);
console.dir(app.uiUtils);
```

### Log Events
```javascript
// Add custom logging
console.log('[YourModule]', 'Action:', data);

// Enable verbose logging
localStorage.setItem('debug', 'true');
```

### Test Functions
```javascript
// Test chat operations
app.chatManager.newChat();
app.chatManager.saveSessions();

// Test API
const data = await app.apiService.checkSDStatus();
console.log(data);

// Test UI
app.uiUtils.showLoading();
setTimeout(() => app.uiUtils.hideLoading(), 2000);
```

## 📊 Event Listeners

### Setup Custom Listener
```javascript
// In main.js setupEventListeners()
elements.myButton.addEventListener('click', () => {
    this.handleMyAction();
});
```

### Remove Listener
```javascript
const handler = () => { ... };
element.addEventListener('click', handler);
element.removeEventListener('click', handler);
```

## 🎨 Custom Styling

### Add Custom CSS Class
```javascript
// In module
element.classList.add('my-custom-class');
element.classList.remove('my-custom-class');
element.classList.toggle('my-custom-class');
```

### Inline Styles
```javascript
element.style.display = 'none';
element.style.color = '#ff0000';
```

## 🔐 Best Practices

### ✅ DO
```javascript
// Use async/await
async function fetchData() {
    try {
        const data = await apiService.getData();
        return data;
    } catch (error) {
        console.error('Error:', error);
        throw error;
    }
}

// Check before accessing
if (element) {
    element.textContent = 'Hello';
}

// Use constants
const MAX_RETRIES = 3;
```

### ❌ DON'T
```javascript
// Don't use global variables
window.myGlobalVar = 123; // ❌

// Don't modify prototypes
Array.prototype.myMethod = function() {}; // ❌

// Don't ignore errors
try {
    await apiCall();
} catch (e) {
    // Empty catch ❌
}
```

## 🚀 Performance Tips

### Debounce Input
```javascript
let timeout;
input.addEventListener('input', () => {
    clearTimeout(timeout);
    timeout = setTimeout(() => {
        // Process input
    }, 300);
});
```

### Lazy Load Images
```javascript
img.loading = 'lazy';
```

### Use DocumentFragment
```javascript
const fragment = document.createDocumentFragment();
items.forEach(item => {
    const div = document.createElement('div');
    div.textContent = item;
    fragment.appendChild(div);
});
container.appendChild(fragment);
```

## 📚 Resources

- [ES6 Modules](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Modules)
- [Async/Await](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/async_function)
- [Clean Code](https://github.com/ryanmcdermott/clean-code-javascript)

---

**Quick Tips:**
- Use `console.dir()` to inspect objects
- Use browser DevTools for debugging
- Check Network tab for API calls
- Use Console to test functions
- Read module README.md for details
