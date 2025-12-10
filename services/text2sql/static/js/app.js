// Text2SQL JavaScript Application
// ============================================

// Global State
let currentChatId = null;
let chatHistory = [];
let uploadedSchemas = [];
let currentModel = 'gemini';
let currentDbType = 'clickhouse';
let deepThinking = false;

// DOM Elements
const chatContainer = document.getElementById('chatContainer');
const userInput = document.getElementById('userInput');
const sendBtn = document.getElementById('sendBtn');
const uploadBtn = document.getElementById('uploadBtn');
const uploadSection = document.getElementById('uploadSection');
const schemaPreview = document.getElementById('schemaPreview');
const darkModeBtn = document.getElementById('darkModeBtn');
const newChatBtn = document.getElementById('newChatBtn');
const clearBtn = document.getElementById('clearBtn');
const modelSelect = document.getElementById('modelSelect');
const dbTypeSelect = document.getElementById('dbTypeSelect');
const deepThinkingCheck = document.getElementById('deepThinkingCheck');
const statusText = document.getElementById('statusText');
const wordCount = document.getElementById('wordCount');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeApp();
    setupEventListeners();
    loadChatHistory();
    checkDarkMode();
});

function initializeApp() {
    console.log('Text2SQL initialized');
    updateStorageInfo();
}

function setupEventListeners() {
    // Send message
    sendBtn.addEventListener('click', sendMessage);
    userInput.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Character count
    userInput.addEventListener('input', () => {
        wordCount.textContent = `${userInput.value.length} ký tự`;
    });

    // Upload
    uploadBtn.addEventListener('click', () => {
        uploadSection.style.display = 'flex';
    });

    document.getElementById('cancelUploadBtn').addEventListener('click', () => {
        uploadSection.style.display = 'none';
    });

    document.getElementById('schemaFiles').addEventListener('change', handleFileSelect);
    document.getElementById('confirmUploadBtn').addEventListener('click', uploadSchemas);

    // Schema preview
    document.getElementById('closeSchemaBtn').addEventListener('click', () => {
        schemaPreview.style.display = 'none';
    });

    // Settings
    modelSelect.addEventListener('change', (e) => {
        currentModel = e.target.value;
        showToast(`Đã chuyển sang model: ${e.target.value}`);
    });

    dbTypeSelect.addEventListener('change', (e) => {
        currentDbType = e.target.value;
        showToast(`Đã chuyển sang database: ${e.target.value}`);
    });

    deepThinkingCheck.addEventListener('change', (e) => {
        deepThinking = e.target.checked;
        showToast(deepThinking ? '🧠 Đã bật suy luận sâu' : 'Đã tắt suy luận sâu');
    });

    // Dark mode
    darkModeBtn.addEventListener('click', toggleDarkMode);

    // Chat management
    newChatBtn.addEventListener('click', createNewChat);
    clearBtn.addEventListener('click', clearHistory);

    // Attach button
    document.getElementById('attachBtn').addEventListener('click', () => {
        document.getElementById('hiddenFileInput').click();
    });

    document.getElementById('hiddenFileInput').addEventListener('change', handleAttachFiles);
}

// ============================================
// File Upload Functions
// ============================================

function handleFileSelect(e) {
    const files = Array.from(e.target.files);
    const fileList = document.getElementById('fileList');
    const fileCount = document.getElementById('fileCount');
    
    fileList.innerHTML = '';
    
    if (files.length === 0) {
        fileCount.textContent = 'Chưa chọn file';
        return;
    }
    
    fileCount.textContent = `${files.length} file được chọn`;
    
    files.forEach((file, index) => {
        const fileItem = document.createElement('div');
        fileItem.className = 'file-item';
        fileItem.innerHTML = `
            <span>📄 ${file.name} (${formatFileSize(file.size)})</span>
            <span class="file-item-remove" onclick="removeFile(${index})">✕</span>
        `;
        fileList.appendChild(fileItem);
    });
}

function removeFile(index) {
    const input = document.getElementById('schemaFiles');
    const dt = new DataTransfer();
    const files = Array.from(input.files);
    
    files.forEach((file, i) => {
        if (i !== index) dt.items.add(file);
    });
    
    input.files = dt.files;
    handleFileSelect({ target: input });
}

async function uploadSchemas() {
    const input = document.getElementById('schemaFiles');
    const files = Array.from(input.files);
    
    if (files.length === 0) {
        showToast('⚠️ Vui lòng chọn file schema', 'error');
        return;
    }
    
    const uploadStatus = document.getElementById('uploadStatus');
    uploadStatus.innerHTML = '<p style="color: #007bff;">📤 Đang upload và phân tích schema...</p>';
    
    const formData = new FormData();
    files.forEach(file => {
        formData.append('files', file);
    });
    
    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            uploadedSchemas = result.schemas || [];
            uploadStatus.innerHTML = `<p style="color: #28a745;">✅ Upload thành công! ${files.length} file đã được phân tích.</p>`;
            
            // Show schema preview
            displaySchemaPreview(result.schemas);
            
            showToast('✅ Schema đã được upload thành công!', 'success');
            
            setTimeout(() => {
                uploadSection.style.display = 'none';
                input.value = '';
                document.getElementById('fileList').innerHTML = '';
                document.getElementById('fileCount').textContent = 'Chưa chọn file';
            }, 2000);
        } else {
            uploadStatus.innerHTML = `<p style="color: #dc3545;">❌ ${result.message || 'Upload thất bại'}</p>`;
            showToast('❌ Upload thất bại', 'error');
        }
    } catch (error) {
        console.error('Upload error:', error);
        uploadStatus.innerHTML = `<p style="color: #dc3545;">❌ Lỗi: ${error.message}</p>`;
        showToast('❌ Lỗi kết nối', 'error');
    }
}

function displaySchemaPreview(schemas) {
    const schemaContent = document.getElementById('schemaContent');
    
    if (!schemas || schemas.length === 0) {
        schemaContent.innerHTML = '<p style="color: #666;">Chưa có schema nào</p>';
        return;
    }
    
    let html = '';
    schemas.forEach((schema, index) => {
        html += `
            <div style="margin-bottom: 20px;">
                <h5 style="color: #667eea; margin-bottom: 10px;">📄 ${schema.filename || `Schema ${index + 1}`}</h5>
                <pre>${escapeHtml(schema.content || schema.text || 'N/A')}</pre>
            </div>
        `;
    });
    
    schemaContent.innerHTML = html;
    schemaPreview.style.display = 'block';
}

function handleAttachFiles(e) {
    const files = Array.from(e.target.files);
    if (files.length > 0) {
        showToast(`📎 ${files.length} file đã được đính kèm`, 'info');
    }
}

// ============================================
// Chat Functions
// ============================================

async function sendMessage() {
    const message = userInput.value.trim();
    
    if (!message) {
        showToast('⚠️ Vui lòng nhập câu hỏi', 'warning');
        return;
    }
    
    if (uploadedSchemas.length === 0) {
        showToast('⚠️ Vui lòng upload schema trước', 'warning');
        return;
    }
    
    // Disable input
    sendBtn.disabled = true;
    userInput.disabled = true;
    statusText.textContent = 'Đang xử lý...';
    
    // Add user message
    addMessage(message, 'user');
    userInput.value = '';
    wordCount.textContent = '0 ký tự';
    
    // Show loading
    const loadingId = addLoadingMessage();
    
    try {
        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                model: currentModel,
                db_type: currentDbType,
                deep_thinking: deepThinking,
                schemas: uploadedSchemas
            })
        });
        
        const result = await response.json();
        
        // Remove loading
        removeLoadingMessage(loadingId);
        
        if (result.status === 'success') {
            // Check response type
            if (result.type === 'questions') {
                // Display generated questions
                addQuestionsMessage(result.questions, currentModel, currentDbType);
                showToast(`✅ Đã tạo ${result.questions.length} câu hỏi mẫu`, 'success');
            } else if (result.type === 'learned') {
                // Display learned confirmation
                addLearnedMessage(result.question, result.sql);
                showToast('✅ Đã lưu vào knowledge base', 'success');
            } else {
                // Display SQL response
                addSQLMessage(result.sql, result.explanation || '', currentModel, currentDbType);
                
                // Save to history
                saveChatMessage(message, result.sql);
            }
        } else {
            addMessage(`❌ Lỗi: ${result.message || 'Không thể tạo SQL'}`, 'assistant');
        }
    } catch (error) {
        console.error('Chat error:', error);
        removeLoadingMessage(loadingId);
        addMessage(`❌ Lỗi kết nối: ${error.message}`, 'assistant');
    }
    
    // Re-enable input
    sendBtn.disabled = false;
    userInput.disabled = false;
    userInput.focus();
    statusText.textContent = 'Sẵn sàng';
}

function addMessage(text, sender = 'assistant') {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    const textDiv = document.createElement('div');
    textDiv.textContent = text;
    
    const infoDiv = document.createElement('div');
    infoDiv.className = 'message-info';
    infoDiv.textContent = sender === 'user' ? 'Bạn' : `${currentModel} • ${currentDbType}`;
    
    contentDiv.appendChild(textDiv);
    contentDiv.appendChild(infoDiv);
    messageDiv.appendChild(contentDiv);
    
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function addSQLMessage(sql, explanation, model, dbType) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Explanation
    if (explanation) {
        const explanationDiv = document.createElement('div');
        explanationDiv.textContent = explanation;
        explanationDiv.style.marginBottom = '10px';
        contentDiv.appendChild(explanationDiv);
    }
    
    // SQL Block
    const sqlBlock = document.createElement('div');
    sqlBlock.className = 'sql-block';
    
    const pre = document.createElement('pre');
    const code = document.createElement('code');
    code.className = 'language-sql';
    code.textContent = sql;
    
    pre.appendChild(code);
    sqlBlock.appendChild(pre);
    
    // Copy button
    const copyBtn = document.createElement('button');
    copyBtn.className = 'copy-sql-btn';
    copyBtn.textContent = '📋 Copy';
    copyBtn.onclick = () => copySQL(sql, copyBtn);
    sqlBlock.appendChild(copyBtn);
    
    contentDiv.appendChild(sqlBlock);
    
    // Info
    const infoDiv = document.createElement('div');
    infoDiv.className = 'message-info';
    infoDiv.textContent = `${model} • ${dbType}`;
    contentDiv.appendChild(infoDiv);
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // Highlight syntax
    if (window.hljs) {
        hljs.highlightElement(code);
    }
}

function addQuestionsMessage(questions, model, dbType) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Header
    const header = document.createElement('div');
    header.innerHTML = '<strong>📝 Câu hỏi mẫu từ Schema:</strong>';
    header.style.marginBottom = '15px';
    contentDiv.appendChild(header);
    
    // Questions list
    questions.forEach((item, index) => {
        const questionBlock = document.createElement('div');
        questionBlock.style.marginBottom = '20px';
        questionBlock.style.padding = '15px';
        questionBlock.style.background = 'rgba(102, 126, 234, 0.05)';
        questionBlock.style.borderRadius = '8px';
        questionBlock.style.borderLeft = '3px solid #667eea';
        
        // Question
        const questionDiv = document.createElement('div');
        questionDiv.innerHTML = `<strong>${index + 1}. ${escapeHtml(item.question)}</strong>`;
        questionDiv.style.marginBottom = '10px';
        questionDiv.style.color = '#667eea';
        questionBlock.appendChild(questionDiv);
        
        // SQL
        const sqlBlock = document.createElement('div');
        sqlBlock.className = 'sql-block';
        sqlBlock.style.marginTop = '10px';
        
        const pre = document.createElement('pre');
        pre.style.margin = '0';
        
        const code = document.createElement('code');
        code.className = 'language-sql';
        code.textContent = item.sql;
        
        pre.appendChild(code);
        sqlBlock.appendChild(pre);
        
        // Copy button for each SQL
        const copyBtn = document.createElement('button');
        copyBtn.className = 'copy-sql-btn';
        copyBtn.textContent = '📋';
        copyBtn.onclick = () => copySQL(item.sql, copyBtn);
        sqlBlock.appendChild(copyBtn);
        
        questionBlock.appendChild(sqlBlock);
        contentDiv.appendChild(questionBlock);
        
        // Highlight syntax
        if (window.hljs) {
            hljs.highlightElement(code);
        }
    });
    
    // Info
    const infoDiv = document.createElement('div');
    infoDiv.className = 'message-info';
    infoDiv.textContent = `${model} • ${dbType} • Generated ${questions.length} questions`;
    infoDiv.style.marginTop = '15px';
    contentDiv.appendChild(infoDiv);
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function addLearnedMessage(question, sql) {
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Success message
    const successDiv = document.createElement('div');
    successDiv.innerHTML = `<strong>✅ Đã học SQL cho câu hỏi:</strong>`;
    successDiv.style.marginBottom = '10px';
    successDiv.style.color = '#28a745';
    contentDiv.appendChild(successDiv);
    
    // Question
    const questionDiv = document.createElement('div');
    questionDiv.textContent = question;
    questionDiv.style.marginBottom = '10px';
    questionDiv.style.padding = '10px';
    questionDiv.style.background = 'rgba(40, 167, 69, 0.1)';
    questionDiv.style.borderRadius = '5px';
    contentDiv.appendChild(questionDiv);
    
    // SQL
    const sqlBlock = document.createElement('div');
    sqlBlock.className = 'sql-block';
    
    const pre = document.createElement('pre');
    const code = document.createElement('code');
    code.className = 'language-sql';
    code.textContent = sql;
    
    pre.appendChild(code);
    sqlBlock.appendChild(pre);
    
    contentDiv.appendChild(sqlBlock);
    
    // Info
    const infoDiv = document.createElement('div');
    infoDiv.className = 'message-info';
    infoDiv.textContent = 'Saved to Knowledge Base';
    contentDiv.appendChild(infoDiv);
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // Highlight syntax
    if (window.hljs) {
        hljs.highlightElement(code);
    }
}

function addLoadingMessage() {
    const id = 'loading-' + Date.now();
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message assistant';
    messageDiv.id = id;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    contentDiv.innerHTML = '<div>🤔 Đang phân tích và tạo SQL query...</div>';
    
    messageDiv.appendChild(contentDiv);
    chatContainer.appendChild(messageDiv);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    return id;
}

function removeLoadingMessage(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

function copySQL(sql, button) {
    navigator.clipboard.writeText(sql).then(() => {
        const originalText = button.textContent;
        button.textContent = '✅ Copied!';
        setTimeout(() => {
            button.textContent = originalText;
        }, 2000);
    });
}

// ============================================
// Chat History Management
// ============================================

function createNewChat() {
    currentChatId = null;
    chatContainer.innerHTML = `
        <div class="message assistant">
            <div class="message-content">
                <div>👋 Xin chào! Tôi là AI Text2SQL Assistant. Hãy upload schema của database và đặt câu hỏi, tôi sẽ chuyển đổi thành SQL query chính xác cho bạn!</div>
                <div class="message-info">Gemini • ClickHouse</div>
            </div>
        </div>
    `;
    showToast('✨ Đã tạo chat mới', 'success');
}

function loadChatHistory() {
    const saved = localStorage.getItem('text2sql_chats');
    if (saved) {
        chatHistory = JSON.parse(saved);
        renderChatList();
    }
}

function saveChatMessage(question, sql) {
    const chat = {
        id: currentChatId || Date.now(),
        question: question,
        sql: sql,
        timestamp: new Date().toISOString()
    };
    
    chatHistory.unshift(chat);
    
    // Keep only last 50 chats
    if (chatHistory.length > 50) {
        chatHistory = chatHistory.slice(0, 50);
    }
    
    localStorage.setItem('text2sql_chats', JSON.stringify(chatHistory));
    renderChatList();
    updateStorageInfo();
}

function renderChatList() {
    const chatList = document.getElementById('chatList');
    
    if (chatHistory.length === 0) {
        chatList.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">Chưa có lịch sử</p>';
        return;
    }
    
    chatList.innerHTML = '';
    
    chatHistory.forEach((chat) => {
        const item = document.createElement('div');
        item.className = 'chat-item';
        item.onclick = () => loadChat(chat.id);
        
        const title = document.createElement('div');
        title.className = 'chat-item-title';
        title.textContent = chat.question.substring(0, 50) + (chat.question.length > 50 ? '...' : '');
        
        const preview = document.createElement('div');
        preview.className = 'chat-item-preview';
        preview.textContent = 'SQL: ' + chat.sql.substring(0, 60) + '...';
        
        const time = document.createElement('div');
        time.className = 'chat-item-time';
        time.textContent = formatDate(chat.timestamp);
        
        item.appendChild(title);
        item.appendChild(preview);
        item.appendChild(time);
        
        chatList.appendChild(item);
    });
}

function loadChat(id) {
    const chat = chatHistory.find(c => c.id === id);
    if (chat) {
        currentChatId = id;
        chatContainer.innerHTML = '';
        addMessage(chat.question, 'user');
        addSQLMessage(chat.sql, '', currentModel, currentDbType);
        showToast('📖 Đã tải lịch sử chat', 'info');
    }
}

function clearHistory() {
    if (confirm('Bạn có chắc muốn xóa toàn bộ lịch sử?')) {
        chatHistory = [];
        localStorage.removeItem('text2sql_chats');
        renderChatList();
        createNewChat();
        updateStorageInfo();
        showToast('🗑️ Đã xóa lịch sử', 'success');
    }
}

// ============================================
// Utility Functions
// ============================================

function toggleDarkMode() {
    document.body.classList.toggle('dark-mode');
    const isDark = document.body.classList.contains('dark-mode');
    localStorage.setItem('darkMode', isDark);
    darkModeBtn.textContent = isDark ? '☀️' : '🌙';
}

function checkDarkMode() {
    const isDark = localStorage.getItem('darkMode') === 'true';
    if (isDark) {
        document.body.classList.add('dark-mode');
        darkModeBtn.textContent = '☀️';
    }
}

function updateStorageInfo() {
    const chatsSize = new Blob([JSON.stringify(chatHistory)]).size;
    const schemasSize = new Blob([JSON.stringify(uploadedSchemas)]).size;
    const total = chatsSize + schemasSize;
    
    document.getElementById('storageInfo').textContent = 
        `Storage: ${formatFileSize(total)} | ${chatHistory.length} chats`;
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return 'Vừa xong';
    if (diff < 3600000) return Math.floor(diff / 60000) + ' phút trước';
    if (diff < 86400000) return Math.floor(diff / 3600000) + ' giờ trước';
    
    return date.toLocaleDateString('vi-VN');
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return text.replace(/[&<>"']/g, m => map[m]);
}

function showToast(message, type = 'info') {
    // Simple toast notification
    const toast = document.createElement('div');
    toast.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        background: ${type === 'error' ? '#dc3545' : type === 'success' ? '#28a745' : '#667eea'};
        color: white;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
        z-index: 10000;
        animation: slideInRight 0.3s ease;
    `;
    toast.textContent = message;
    
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'fadeOut 0.3s ease';
        setTimeout(() => toast.remove(), 300);
    }, 3000);
}

// Download chat history
document.getElementById('downloadBtn').addEventListener('click', () => {
    if (chatHistory.length === 0) {
        showToast('⚠️ Không có lịch sử để tải', 'warning');
        return;
    }
    
    const dataStr = JSON.stringify(chatHistory, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `text2sql-history-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
    
    showToast('✅ Đã tải lịch sử SQL', 'success');
});

// ============================================
// AI Learning Functions
// ============================================

document.getElementById('learningBtn').addEventListener('click', () => {
    openLearningModal();
});

document.getElementById('closeLearningBtn').addEventListener('click', () => {
    document.getElementById('learningModal').style.display = 'none';
});

document.getElementById('refreshLearningBtn').addEventListener('click', () => {
    loadKnowledgeBase();
});

document.getElementById('clearLearningBtn').addEventListener('click', () => {
    clearKnowledgeBase();
});

async function openLearningModal() {
    document.getElementById('learningModal').style.display = 'flex';
    await loadKnowledgeBase();
}

async function loadKnowledgeBase() {
    try {
        const response = await fetch('/knowledge/list');
        const result = await response.json();
        
        if (result.status === 'success') {
            displayKnowledge(result.knowledge);
            document.getElementById('knowledgeCount').textContent = 
                `${result.count} câu SQL đã học`;
        }
    } catch (error) {
        console.error('Error loading knowledge:', error);
        showToast('❌ Lỗi tải knowledge base', 'error');
    }
}

function displayKnowledge(knowledge) {
    const list = document.getElementById('learningList');
    
    if (!knowledge || knowledge.length === 0) {
        list.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">Chưa có dữ liệu học</p>';
        return;
    }
    
    list.innerHTML = '';
    
    knowledge.forEach((item, index) => {
        const itemDiv = document.createElement('div');
        itemDiv.className = 'learning-item';
        
        const questionDiv = document.createElement('div');
        questionDiv.className = 'learning-item-question';
        questionDiv.textContent = `${index + 1}. ${item.question}`;
        
        const sqlDiv = document.createElement('div');
        sqlDiv.className = 'learning-item-sql';
        sqlDiv.textContent = item.sql;
        
        const timeDiv = document.createElement('div');
        timeDiv.className = 'learning-item-time';
        timeDiv.textContent = `Học lúc: ${formatDate(item.learned_at)}`;
        
        itemDiv.appendChild(questionDiv);
        itemDiv.appendChild(sqlDiv);
        itemDiv.appendChild(timeDiv);
        
        list.appendChild(itemDiv);
    });
}

async function clearKnowledgeBase() {
    if (!confirm('⚠️ Bạn có chắc muốn xóa toàn bộ knowledge base?')) {
        return;
    }
    
    try {
        const response = await fetch('/knowledge/clear', {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('✅ Đã xóa knowledge base', 'success');
            await loadKnowledgeBase();
        }
    } catch (error) {
        console.error('Error clearing knowledge:', error);
        showToast('❌ Lỗi xóa knowledge base', 'error');
    }
}

// ============================================
// Database Connection Functions
// ============================================

function openDatabaseModal() {
    const modal = document.getElementById('databaseModal');
    modal.style.display = 'flex';
    loadSavedConnections();
}

function closeDatabaseModal() {
    const modal = document.getElementById('databaseModal');
    modal.style.display = 'none';
}

async function testConnection() {
    const dbType = document.getElementById('dbType').value;
    const connectionType = document.getElementById('connectionType').value;
    const host = document.getElementById('host').value;
    const port = document.getElementById('port').value;
    const uri = document.getElementById('uri').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const database = document.getElementById('database').value;
    
    const statusIndicator = document.getElementById('statusIndicator');
    const statusMessage = document.getElementById('statusMessage');
    
    statusIndicator.textContent = '🟡';
    statusIndicator.className = 'status-indicator testing';
    statusMessage.textContent = 'Đang kiểm tra kết nối...';
    
    try {
        const response = await fetch('/api/database/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                db_type: dbType,
                connection_type: connectionType,
                host,
                port,
                uri,
                username,
                password,
                database
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            statusIndicator.textContent = '🟢';
            statusIndicator.className = 'status-indicator connected';
            statusMessage.textContent = result.message;
            showToast(result.message, 'success');
        } else {
            statusIndicator.textContent = '🔴';
            statusIndicator.className = 'status-indicator disconnected';
            statusMessage.textContent = result.message;
            showToast(result.message, 'error');
        }
    } catch (error) {
        statusIndicator.textContent = '🔴';
        statusIndicator.className = 'status-indicator disconnected';
        statusMessage.textContent = 'Lỗi kết nối';
        showToast('❌ Lỗi: ' + error.message, 'error');
    }
}

async function saveConnection() {
    const dbType = document.getElementById('dbType').value;
    const connectionType = document.getElementById('connectionType').value;
    const host = document.getElementById('host').value;
    const port = document.getElementById('port').value;
    const uri = document.getElementById('uri').value;
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;
    const database = document.getElementById('database').value;
    
    const connectionName = prompt('Tên connection:', `${dbType}_${connectionType}`);
    if (!connectionName) return;
    
    try {
        const response = await fetch('/api/database/save-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                connection_name: connectionName,
                db_type: dbType,
                connection_type: connectionType,
                host,
                port,
                uri,
                username,
                password,
                database
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('💾 Đã lưu connection', 'success');
            await loadSavedConnections();
        } else {
            showToast('❌ ' + result.message, 'error');
        }
    } catch (error) {
        showToast('❌ Lỗi: ' + error.message, 'error');
    }
}

async function loadSavedConnections() {
    try {
        const response = await fetch('/api/database/connections');
        const result = await response.json();
        
        const list = document.getElementById('connectionsList');
        list.innerHTML = '';
        
        if (result.connections.length === 0) {
            list.innerHTML = '<p style="color: #999; text-align: center;">Chưa có connection nào</p>';
            return;
        }
        
        result.connections.forEach(conn => {
            const item = document.createElement('div');
            item.className = 'connection-item';
            
            const info = document.createElement('div');
            info.className = 'connection-info';
            
            const name = document.createElement('div');
            name.className = 'connection-name';
            name.textContent = conn.name;
            
            const details = document.createElement('div');
            details.className = 'connection-details';
            if (conn.connection_type === 'atlas') {
                details.textContent = `${conn.db_type} (Atlas)`;
            } else {
                details.textContent = `${conn.db_type} - ${conn.host}:${conn.port}/${conn.database}`;
            }
            
            info.appendChild(name);
            info.appendChild(details);
            
            const actions = document.createElement('div');
            actions.className = 'connection-actions';
            
            const useBtn = document.createElement('button');
            useBtn.className = 'use-btn';
            useBtn.textContent = 'Dùng';
            useBtn.onclick = () => useConnection(conn.id);
            
            const deleteBtn = document.createElement('button');
            deleteBtn.className = 'delete-connection-btn';
            deleteBtn.textContent = 'Xóa';
            deleteBtn.onclick = () => deleteConnection(conn.id);
            
            actions.appendChild(useBtn);
            actions.appendChild(deleteBtn);
            
            item.appendChild(info);
            item.appendChild(actions);
            
            list.appendChild(item);
        });
    } catch (error) {
        console.error('Error loading connections:', error);
    }
}

async function useConnection(connectionId) {
    try {
        const response = await fetch(`/api/database/use-connection/${connectionId}`, {
            method: 'POST'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('✅ ' + result.message, 'success');
            
            const statusIndicator = document.getElementById('statusIndicator');
            const statusMessage = document.getElementById('statusMessage');
            statusIndicator.textContent = '🟢';
            statusIndicator.className = 'status-indicator connected';
            statusMessage.textContent = 'Đã kết nối: ' + result.connection.name;
        } else {
            showToast('❌ ' + result.message, 'error');
        }
    } catch (error) {
        showToast('❌ Lỗi: ' + error.message, 'error');
    }
}

async function deleteConnection(connectionId) {
    if (!confirm('⚠️ Xóa connection này?')) return;
    
    try {
        const response = await fetch(`/api/database/delete-connection/${connectionId}`, {
            method: 'DELETE'
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            showToast('🗑️ Đã xóa connection', 'success');
            await loadSavedConnections();
        }
    } catch (error) {
        showToast('❌ Lỗi: ' + error.message, 'error');
    }
}

// Handle connection type change
document.addEventListener('DOMContentLoaded', () => {
    const connectionType = document.getElementById('connectionType');
    const dbType = document.getElementById('dbType');
    
    if (connectionType) {
        connectionType.addEventListener('change', () => {
            const type = connectionType.value;
            const hostGroup = document.getElementById('hostGroup');
            const portGroup = document.getElementById('portGroup');
            const uriGroup = document.getElementById('uriGroup');
            const usernameGroup = document.getElementById('usernameGroup');
            const passwordGroup = document.getElementById('passwordGroup');
            
            if (type === 'atlas') {
                hostGroup.style.display = 'none';
                portGroup.style.display = 'none';
                uriGroup.style.display = 'flex';
                usernameGroup.style.display = 'none';
                passwordGroup.style.display = 'none';
            } else {
                hostGroup.style.display = 'flex';
                portGroup.style.display = 'flex';
                uriGroup.style.display = 'none';
                usernameGroup.style.display = 'flex';
                passwordGroup.style.display = 'flex';
            }
        });
    }
    
    // Set default ports based on database type
    if (dbType) {
        dbType.addEventListener('change', () => {
            const type = dbType.value;
            const portInput = document.getElementById('port');
            
            if (type === 'clickhouse') {
                portInput.value = '8123';
            } else if (type === 'mongodb') {
                portInput.value = '27017';
            }
        });
    }
    
    // Database button
    const databaseBtn = document.getElementById('databaseBtn');
    if (databaseBtn) {
        databaseBtn.addEventListener('click', openDatabaseModal);
    }
});
