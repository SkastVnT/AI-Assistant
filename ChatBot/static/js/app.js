// Global variables
let currentChatId = null;
let allMemories = [];
let selectedMemories = new Set();
let isGeneratingImage = false;

// DOM elements
const chatContainer = document.getElementById('chatContainer');
const messageInput = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const clearBtn = document.getElementById('clearBtn');
const modelSelect = document.getElementById('modelSelect');
const contextSelect = document.getElementById('contextSelect');
const deepThinkingCheckbox = document.getElementById('deepThinking');
const aiLearningCheckbox = document.getElementById('aiLearning');
const darkModeToggle = document.getElementById('darkModeToggle');
const sidebarToggle = document.getElementById('sidebarToggle');
const sidebar = document.querySelector('.sidebar');
const newChatBtn = document.getElementById('newChatBtn');
const chatList = document.getElementById('chatList');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadChatHistory();
    loadMemories();
    loadDarkMode();
    
    // Event listeners
    sendBtn.addEventListener('click', sendMessage);
    clearBtn.addEventListener('click', clearHistory);
    darkModeToggle.addEventListener('click', toggleDarkMode);
    newChatBtn.addEventListener('click', createNewChat);
    sidebarToggle.addEventListener('click', toggleSidebar);
    
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // File upload handling
    document.getElementById('fileInput').addEventListener('change', handleFileUpload);
});

// Dark mode
function loadDarkMode() {
    const darkMode = localStorage.getItem('darkMode') === 'true';
    if (darkMode) {
        document.body.classList.add('dark-mode');
    }
}

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', document.body.classList.contains('dark-mode'));
}

// Sidebar
function toggleSidebar() {
    sidebar.classList.toggle('active');
}

// Chat management
function createNewChat() {
    currentChatId = Date.now().toString();
    chatContainer.innerHTML = '';
    messageInput.value = '';
    
    // Update chat list without reordering
    updateChatListItem(currentChatId, 'Cuộc trò chuyện mới', 'Chưa có tin nhắn');
    setActiveChatItem(currentChatId);
    
    saveChatHistory();
}

function loadChatHistory() {
    const chats = JSON.parse(localStorage.getItem('chatHistory') || '{}');
    
    // Sort by timestamp descending (newest first) ONLY on initial load
    const chatIds = Object.keys(chats).sort((a, b) => {
        const timeA = chats[a].timestamp || 0;
        const timeB = chats[b].timestamp || 0;
        return timeB - timeA;
    });
    
    chatList.innerHTML = '';
    
    if (chatIds.length === 0) {
        currentChatId = Date.now().toString();
        saveChatHistory();
    } else {
        currentChatId = chatIds[0];
        chatIds.forEach(chatId => {
            const chat = chats[chatId];
            addChatItem(chatId, chat.title || 'Cuộc trò chuyện', chat.preview || 'Chưa có tin nhắn', chat.timestamp);
        });
        
        // Load current chat messages
        loadChat(currentChatId);
    }
    
    setActiveChatItem(currentChatId);
}

function addChatItem(chatId, title, preview, timestamp) {
    const chatItem = document.createElement('div');
    chatItem.className = 'chat-item';
    chatItem.dataset.chatId = chatId;
    
    const time = timestamp ? formatTimestamp(new Date(timestamp)) : formatTimestamp(new Date());
    
    chatItem.innerHTML = `
        <div class="chat-item-title">${title}</div>
        <div class="chat-item-preview">${preview}</div>
        <div class="chat-item-time">${time}</div>
        <div class="chat-item-actions">
            <button class="chat-item-btn" onclick="deleteChat('${chatId}')" title="Xóa">🗑️</button>
        </div>
    `;
    
    chatItem.addEventListener('click', (e) => {
        if (!e.target.classList.contains('chat-item-btn')) {
            loadChat(chatId);
        }
    });
    
    chatList.appendChild(chatItem);
}

// Update chat item WITHOUT reordering - just update in place
function updateChatListItem(chatId, title, preview) {
    const existingItem = chatList.querySelector(`[data-chat-id="${chatId}"]`);
    
    if (existingItem) {
        // Update existing item in place
        existingItem.querySelector('.chat-item-title').textContent = title;
        existingItem.querySelector('.chat-item-preview').textContent = preview;
        existingItem.querySelector('.chat-item-time').textContent = formatTimestamp(new Date());
    } else {
        // Add new item at the top
        const chatItem = document.createElement('div');
        chatItem.className = 'chat-item';
        chatItem.dataset.chatId = chatId;
        
        chatItem.innerHTML = `
            <div class="chat-item-title">${title}</div>
            <div class="chat-item-preview">${preview}</div>
            <div class="chat-item-time">${formatTimestamp(new Date())}</div>
            <div class="chat-item-actions">
                <button class="chat-item-btn" onclick="deleteChat('${chatId}')" title="Xóa">🗑️</button>
            </div>
        `;
        
        chatItem.addEventListener('click', (e) => {
            if (!e.target.classList.contains('chat-item-btn')) {
                loadChat(chatId);
            }
        });
        
        chatList.insertBefore(chatItem, chatList.firstChild);
    }
}

function setActiveChatItem(chatId) {
    document.querySelectorAll('.chat-item').forEach(item => {
        item.classList.remove('active');
    });
    
    const activeItem = chatList.querySelector(`[data-chat-id="${chatId}"]`);
    if (activeItem) {
        activeItem.classList.add('active');
    }
}

function loadChat(chatId) {
    currentChatId = chatId;
    chatContainer.innerHTML = '';
    
    const chats = JSON.parse(localStorage.getItem('chatHistory') || '{}');
    const chat = chats[chatId];
    
    if (chat && chat.messages) {
        chat.messages.forEach(msg => {
            addMessage(msg.content, msg.isUser, msg.model, msg.context, msg.timestamp, false);
        });
    }
    
    setActiveChatItem(chatId);
    
    if (window.innerWidth <= 768) {
        sidebar.classList.remove('active');
    }
}

function deleteChat(chatId) {
    if (!confirm('Bạn có chắc muốn xóa cuộc trò chuyện này?')) return;
    
    const chats = JSON.parse(localStorage.getItem('chatHistory') || '{}');
    delete chats[chatId];
    localStorage.setItem('chatHistory', JSON.stringify(chats));
    
    // Remove from UI
    const chatItem = chatList.querySelector(`[data-chat-id="${chatId}"]`);
    if (chatItem) {
        chatItem.remove();
    }
    
    // If deleted current chat, create new one
    if (chatId === currentChatId) {
        createNewChat();
    }
}

function saveChatHistory() {
    const chats = JSON.parse(localStorage.getItem('chatHistory') || '{}');
    
    const messages = Array.from(chatContainer.children)
        .filter(el => el.classList.contains('message'))
        .map(el => ({
            content: el.querySelector('.message-content').innerHTML,
            isUser: el.classList.contains('user'),
            model: el.dataset.model || '',
            context: el.dataset.context || '',
            timestamp: el.dataset.timestamp || new Date().toISOString()
        }));
    
    const title = messages.length > 0 ? 
        messages[0].content.substring(0, 30).replace(/<[^>]*>/g, '') + '...' : 
        'Cuộc trò chuyện mới';
    
    const preview = messages.length > 0 ?
        messages[messages.length - 1].content.substring(0, 50).replace(/<[^>]*>/g, '') + '...' :
        'Chưa có tin nhắn';
    
    chats[currentChatId] = {
        messages,
        title,
        preview,
        timestamp: Date.now()
    };
    
    localStorage.setItem('chatHistory', JSON.stringify(chats));
    
    // Update chat list item WITHOUT reordering
    updateChatListItem(currentChatId, title, preview);
}

// Message handling
function addMessage(content, isUser, model = '', context = '', timestamp = '', saveHistory = true) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    messageDiv.dataset.model = model;
    messageDiv.dataset.context = context;
    messageDiv.dataset.timestamp = timestamp || new Date().toISOString();
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (isUser) {
        contentDiv.textContent = content;
    } else {
        contentDiv.innerHTML = marked.parse(content);
        
        // Syntax highlighting
        contentDiv.querySelectorAll('pre code').forEach((block) => {
            hljs.highlightElement(block);
            addCopyButton(block);
        });
        
        // Add copy message button
        addCopyMessageButton(messageDiv);
    }
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    if (saveHistory) {
        saveChatHistory();
    }
}

function addCopyButton(codeBlock) {
    const button = document.createElement('button');
    button.className = 'copy-btn';
    button.textContent = '📋 Copy';
    button.onclick = () => {
        navigator.clipboard.writeText(codeBlock.textContent);
        button.textContent = '✅ Copied!';
        setTimeout(() => button.textContent = '📋 Copy', 2000);
    };
    codeBlock.parentElement.style.position = 'relative';
    codeBlock.parentElement.insertBefore(button, codeBlock);
}

function addCopyMessageButton(messageDiv) {
    const button = document.createElement('button');
    button.className = 'copy-message-btn';
    button.textContent = '📋';
    button.title = 'Copy message';
    button.onclick = () => {
        const content = messageDiv.querySelector('.message-content').textContent;
        navigator.clipboard.writeText(content);
        button.textContent = '✅';
        setTimeout(() => button.textContent = '📋', 2000);
    };
    messageDiv.appendChild(button);
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    const model = modelSelect.value;
    const context = contextSelect.value;
    const deepThinking = deepThinkingCheckbox.checked;
    const aiLearning = aiLearningCheckbox.checked;
    
    // Add user message
    addMessage(message, true, model, context, formatTimestamp(new Date()));
    messageInput.value = '';
    
    // Check for image generation tool
    if (message.toLowerCase().includes('tạo ảnh') || message.toLowerCase().includes('vẽ') || message.toLowerCase().includes('generate image')) {
        await handleImageGenerationTool(message, model, context, deepThinking);
        return;
    }
    
    // Show loading
    const loadingMsg = document.createElement('div');
    loadingMsg.className = 'message assistant';
    loadingMsg.innerHTML = '<div class="message-content">⏳ Đang suy nghĩ...</div>';
    chatContainer.appendChild(loadingMsg);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    try {
        // Prepare memory context if AI Learning is enabled
        let memoryContext = '';
        const memory_ids = [];
        
        if (aiLearning && selectedMemories.size > 0) {
            const selectedMemoryData = allMemories.filter(m => selectedMemories.has(m.id));
            memoryContext = selectedMemoryData.map(m => 
                `[Bài học: ${m.title}]\n${m.content}`
            ).join('\n\n');
            memory_ids.push(...Array.from(selectedMemories));
        }
        
        // Get file uploads
        const files = document.getElementById('fileInput').files;
        const fileContents = [];
        
        for (let file of files) {
            const content = await readFileAsText(file);
            fileContents.push({
                name: file.name,
                content: content
            });
        }
        
        // Send request
        const response = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message,
                model,
                context,
                deep_thinking: deepThinking,
                ai_learning: aiLearning,
                memory_context: memoryContext,
                memory_ids,
                files: fileContents
            })
        });
        
        const data = await response.json();
        
        // Remove loading
        loadingMsg.remove();
        
        // Add response
        addMessage(data.response, false, model, context, formatTimestamp(new Date()));
        
        // Clear file input
        document.getElementById('fileInput').value = '';
        
    } catch (error) {
        loadingMsg.remove();
        addMessage(`❌ Lỗi: ${error.message}`, false, model, context, formatTimestamp(new Date()));
    }
}

async function clearHistory() {
    if (!confirm('Bạn có chắc muốn xóa lịch sử chat?')) return;
    
    chatContainer.innerHTML = '';
    saveChatHistory();
}

function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => resolve(e.target.result);
        reader.onerror = (e) => reject(e);
        reader.readAsText(file);
    });
}

function handleFileUpload() {
    const files = document.getElementById('fileInput').files;
    if (files.length > 0) {
        const fileNames = Array.from(files).map(f => f.name).join(', ');
        console.log('Files selected:', fileNames);
    }
}

// Utility
function formatTimestamp(date) {
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    return `${hours}:${minutes}:${seconds}`;
}
