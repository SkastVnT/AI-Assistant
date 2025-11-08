/**
 * Simple Working ChatBot V2 - Complete Rewrite
 * NO localStorage dependency, all features work
 */

let currentChatId = null;
let isGenerating = false;
let conversationHistory = []; // Store in memory

console.log('🚀 Loading Simple ChatBot V2...');

document.addEventListener('DOMContentLoaded', function() {
    console.log('✅ DOM Ready - Initializing...');
    
    // Get ALL elements and log them
    const sendBtn = document.getElementById('sendBtn');
    const messageInput = document.getElementById('messageInput');
    const chatContainer = document.getElementById('chatContainer');
    const newChatBtn = document.getElementById('newChatBtn');
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
    const sidebar = document.getElementById('sidebar');
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    const clearBtn = document.getElementById('clearBtn');
    const stopBtn = document.getElementById('stopBtn');
    const imageGenBtn = document.getElementById('imageGenBtn');
    const exportBtn = document.getElementById('exportBtn');
    const memoryBtn = document.getElementById('memoryBtn');
    
    console.log('📦 Elements found:', {
        sendBtn: !!sendBtn,
        messageInput: !!messageInput,
        chatContainer: !!chatContainer,
        newChatBtn: !!newChatBtn,
        sidebarToggleBtn: !!sidebarToggleBtn,
        sidebar: !!sidebar,
        themeToggleBtn: !!themeToggleBtn,
        clearBtn: !!clearBtn,
        stopBtn: !!stopBtn,
        imageGenBtn: !!imageGenBtn,
        exportBtn: !!exportBtn,
        memoryBtn: !!memoryBtn
    });
    
    // Initialize (no localStorage, just set defaults)
    try {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
        }
    } catch (e) {
        console.warn('localStorage not available:', e);
    }
    
    // ========== SEND MESSAGE ==========
    async function sendMessage() {
        console.log('📤 Send message clicked');
        const message = messageInput.value.trim();
        if (!message) {
            console.log('⚠️ Empty message');
            return;
        }
        if (isGenerating) {
            console.log('⚠️ Already generating');
            return;
        }
        
        console.log('✅ Sending:', message);
        isGenerating = true;
        messageInput.value = '';
        messageInput.style.height = 'auto';
        
        // Toggle buttons
        if (stopBtn && sendBtn) {
            stopBtn.style.display = 'flex';
            sendBtn.style.display = 'none';
        }
        
        // Add user message
        addMessage(message, 'user');
        conversationHistory.push({ role: 'user', content: message });
        
        // Add loading
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message assistant-message';
        loadingDiv.id = 'loading-message';
        loadingDiv.innerHTML = `
            <div class="message-avatar">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
                </svg>
            </div>
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span><span></span><span></span>
                </div>
            </div>
        `;
        chatContainer.appendChild(loadingDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        try {
            console.log('🌐 Fetching /chat...');
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    message: message,
                    chat_id: currentChatId 
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            console.log('✅ Response received:', data);
            
            loadingDiv.remove();
            addMessage(data.response, 'assistant');
            conversationHistory.push({ role: 'assistant', content: data.response });
            
            if (data.chat_id) {
                currentChatId = data.chat_id;
            }
            
        } catch (error) {
            console.error('❌ Error:', error);
            loadingDiv.remove();
            addMessage('❌ Error: ' + error.message, 'assistant');
        }
        
        isGenerating = false;
        if (stopBtn && sendBtn) {
            stopBtn.style.display = 'none';
            sendBtn.style.display = 'flex';
        }
    }
    
    // ========== ADD MESSAGE WITH AVATAR ==========
    function addMessage(text, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}-message`;
        
        // Create avatar
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        
        if (role === 'user') {
            // User icon
            avatar.innerHTML = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                    <circle cx="12" cy="7" r="4"/>
                </svg>
            `;
        } else {
            // AI icon
            avatar.innerHTML = `
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
                </svg>
            `;
        }
        
        // Create content
        const content = document.createElement('div');
        content.className = 'message-content';
        
        // Render markdown if marked.js available
        if (typeof marked !== 'undefined') {
            content.innerHTML = marked.parse(text);
        } else {
            content.innerHTML = `<p>${text.replace(/\n/g, '<br>')}</p>`;
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(content);
        chatContainer.appendChild(messageDiv);
        scrollToBottom();
        
        // Highlight code if hljs available
        if (typeof hljs !== 'undefined') {
            content.querySelectorAll('pre code').forEach(block => {
                hljs.highlightElement(block);
            });
        }
    }
    
    // ========== NEW CHAT ==========
    function startNewChat() {
        console.log('🆕 New Chat clicked');
        const hasMessages = chatContainer.querySelectorAll('.message').length > 0;
        if (hasMessages && !confirm('Start a new conversation? Current chat will be lost.')) {
            return;
        }
        
        currentChatId = null;
        conversationHistory = [];
        chatContainer.innerHTML = `
            <div class="welcome-screen">
                <div class="welcome-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83"/>
                    </svg>
                </div>
                <h2>AI Assistant</h2>
                <p>Xin chào! Tôi có thể giúp gì cho bạn hôm nay? 😊</p>
            </div>
        `;
        showNotification('✅ New chat started!', 'success');
        console.log('✅ New chat started');
    }
    
    // ========== CLEAR CHAT ==========
    function clearChat() {
        console.log('🗑️ Clear clicked');
        if (!confirm('Clear this conversation?')) return;
        
        conversationHistory = [];
        chatContainer.innerHTML = `
            <div class="welcome-screen">
                <div class="welcome-icon">
                    <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M3 6h18M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/>
                    </svg>
                </div>
                <h2>Conversation Cleared</h2>
                <p>Start a new message!</p>
            </div>
        `;
        showNotification('✅ Conversation cleared!', 'success');
        console.log('✅ Chat cleared');
    }
    
    // ========== SIDEBAR TOGGLE ==========
    function toggleSidebar() {
        console.log('📂 Sidebar toggle clicked');
        sidebar.classList.toggle('collapsed');
        try {
            localStorage.setItem('sidebarCollapsed', sidebar.classList.contains('collapsed'));
        } catch (e) {
            console.warn('Cannot save sidebar state:', e);
        }
        console.log('✅ Sidebar toggled');
    }
    
    // ========== DARK MODE ==========
    function toggleDarkMode() {
        console.log('🌓 Dark mode toggle clicked');
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        
        try {
            localStorage.setItem('theme', isDark ? 'dark' : 'light');
        } catch (e) {
            console.warn('Cannot save theme:', e);
        }
        
        showNotification(`✅ ${isDark ? 'Dark' : 'Light'} mode activated`, 'success');
        console.log(`✅ ${isDark ? 'Dark' : 'Light'} mode`);
    }
    
    // ========== IMAGE GENERATION ==========
    async function openImageGen() {
        console.log('🎨 Image Gen clicked');
        const prompt = window.prompt('Enter image description:');
        if (!prompt) {
            console.log('⚠️ No prompt entered');
            return;
        }
        
        showNotification('🎨 Generating image...', 'info');
        console.log('🎨 Generating:', prompt);
        
        try {
            const response = await fetch('/generate_image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: prompt })
            });
            
            const data = await response.json();
            console.log('✅ Image response:', data);
            
            if (data.image_url) {
                const imgMessage = `![${prompt}](${data.image_url})`;
                addMessage(imgMessage, 'assistant');
                showNotification('✅ Image generated!', 'success');
            } else if (data.error) {
                showNotification('❌ Error: ' + data.error, 'error');
            } else {
                showNotification('❌ Failed to generate image', 'error');
            }
        } catch (error) {
            console.error('❌ Image gen error:', error);
            showNotification('❌ Error: ' + error.message, 'error');
        }
    }
    
    // ========== EXPORT ==========
    function exportChat() {
        console.log('💾 Export clicked');
        const messages = Array.from(chatContainer.querySelectorAll('.message'));
        
        if (messages.length === 0) {
            showNotification('⚠️ No messages to export', 'info');
            return;
        }
        
        let exportText = '# Chat Export\n\n';
        exportText += `Date: ${new Date().toLocaleString()}\n\n`;
        exportText += '---\n\n';
        
        messages.forEach((msg, idx) => {
            const role = msg.classList.contains('user-message') ? '👤 User' : '🤖 Assistant';
            const content = msg.querySelector('.message-content')?.textContent.trim() || '';
            if (content && !content.includes('...')) { // Skip loading indicators
                exportText += `### ${role}\n\n${content}\n\n---\n\n`;
            }
        });
        
        const blob = new Blob([exportText], { type: 'text/markdown' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `chat-export-${new Date().toISOString().slice(0,19).replace(/:/g,'-')}.md`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        showNotification('✅ Chat exported!', 'success');
        console.log('✅ Export complete');
    }
    
    // ========== STOP GENERATION ==========
    function stopGeneration() {
        console.log('⏹️ Stop clicked');
        isGenerating = false;
        if (stopBtn && sendBtn) {
            stopBtn.style.display = 'none';
            sendBtn.style.display = 'flex';
        }
        const loading = document.getElementById('loading-message');
        if (loading) {
            loading.remove();
        }
        showNotification('⏹️ Generation stopped', 'info');
    }
    
    // ========== UTILITIES ==========
    function scrollToBottom() {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
    
    function autoResize() {
        messageInput.style.height = 'auto';
        messageInput.style.height = Math.min(messageInput.scrollHeight, 200) + 'px';
    }
    
    function showNotification(message, type = 'info') {
        console.log(`📢 Notification [${type}]:`, message);
        
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            padding: 12px 20px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            opacity: 0;
            transform: translateY(-20px);
            transition: all 0.3s ease;
        `;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.opacity = '1';
            notification.style.transform = 'translateY(0)';
        }, 10);
        
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transform = 'translateY(-20px)';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }
    
    // ========== EVENT LISTENERS ==========
    console.log('🔗 Setting up event listeners...');
    
    if (sendBtn) {
        sendBtn.addEventListener('click', function(e) {
            e.preventDefault();
            console.log('🖱️ Send button clicked');
            sendMessage();
        });
        console.log('✅ Send button listener added');
    } else {
        console.error('❌ Send button NOT found!');
    }
    
    if (messageInput) {
        messageInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                console.log('⌨️ Enter key pressed');
                sendMessage();
            }
        });
        messageInput.addEventListener('input', autoResize);
        console.log('✅ Message input listeners added');
    } else {
        console.error('❌ Message input NOT found!');
    }
    
    if (newChatBtn) {
        newChatBtn.addEventListener('click', startNewChat);
        console.log('✅ New chat button listener added');
    }
    
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', toggleSidebar);
        console.log('✅ Sidebar toggle listener added');
    }
    
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', toggleDarkMode);
        console.log('✅ Theme toggle listener added');
    }
    
    if (clearBtn) {
        clearBtn.addEventListener('click', clearChat);
        console.log('✅ Clear button listener added');
    }
    
    if (stopBtn) {
        stopBtn.addEventListener('click', stopGeneration);
        console.log('✅ Stop button listener added');
    }
    
    if (imageGenBtn) {
        imageGenBtn.addEventListener('click', openImageGen);
        console.log('✅ Image gen button listener added');
    }
    
    if (exportBtn) {
        exportBtn.addEventListener('click', exportChat);
        console.log('✅ Export button listener added');
    }
    
    console.log('🎉 ChatBot V2 initialized successfully!');
    showNotification('✅ ChatBot ready!', 'success');
});
