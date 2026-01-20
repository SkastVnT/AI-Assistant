/**
 * UI Utilities Module
 * Handles DOM manipulation, modals, theme, and UI interactions
 */

export class UIUtils {
    constructor() {
        this.elements = {};
        this.theme = 'light';
    }

    /**
     * Initialize DOM elements
     */
    initElements() {
        this.elements = {
            chatContainer: document.getElementById('chatContainer'),
            messageInput: document.getElementById('messageInput'),
            sendBtn: document.getElementById('sendBtn'),
            clearBtn: document.getElementById('clearBtn'),
            modelSelect: document.getElementById('modelSelect'),
            contextSelect: document.getElementById('contextSelect'),
            loading: document.getElementById('loading'),
            googleSearchBtn: document.getElementById('googleSearchBtn'),
            githubBtn: document.getElementById('githubBtn'),
            imageGenToolBtn: document.getElementById('imageGenToolBtn'),
            img2imgToolBtn: document.getElementById('img2imgToolBtn'),
            fileInput: document.getElementById('fileInput'),
            fileList: document.getElementById('fileList'),
            deepThinkingCheck: document.getElementById('deepThinkingCheck'),
            darkModeBtn: document.getElementById('darkModeBtn'),
            downloadBtn: document.getElementById('downloadBtn'),
            memoryBtn: document.getElementById('memoryBtn'),
            memoryPanel: document.getElementById('memoryPanel'),
            saveMemoryBtn: document.getElementById('saveMemoryBtn'),
            memoryListEl: document.getElementById('memoryList'),
            imageGenBtn: document.getElementById('imageGenBtn'),
            chatList: document.getElementById('chatList'),
            newChatBtn: document.getElementById('newChatBtn'),
            sidebar: document.getElementById('sidebar'),
            sidebarToggle: document.getElementById('sidebarToggle'),
            sidebarToggleBtn: document.getElementById('sidebarToggleBtn'),
            storageInfo: document.getElementById('storageInfo'),
            // MCP elements
            mcpToggleBtn: document.getElementById('mcpToggleBtn'),
            mcpSidebar: document.getElementById('mcpSidebar'),
            mcpEnabledCheck: document.getElementById('mcpEnabledCheck'),
            mcpTabFolder: document.getElementById('mcpTabFolder'),
            mcpTabUrl: document.getElementById('mcpTabUrl'),
            mcpTabUpload: document.getElementById('mcpTabUpload')
        };

        return this.elements;
    }

    /**
     * Format timestamp
     */
    formatTimestamp(date) {
        const hours = String(date.getHours()).padStart(2, '0');
        const minutes = String(date.getMinutes()).padStart(2, '0');
        const seconds = String(date.getSeconds()).padStart(2, '0');
        return `${hours}:${minutes}:${seconds}`;
    }

    /**
     * Setup auto-resize textarea
     */
    setupAutoResize(textarea) {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 200) + 'px';
        });
    }

    /**
     * Initialize dark mode
     */
    initDarkMode() {
        const savedTheme = localStorage.getItem('theme') || 'light';
        this.theme = savedTheme;
        
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-mode');
            if (this.elements.darkModeBtn) {
                this.elements.darkModeBtn.textContent = '☀️';
            }
        }
    }

    /**
     * Toggle dark mode
     */
    toggleDarkMode() {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        this.theme = isDark ? 'dark' : 'light';
        
        if (this.elements.darkModeBtn) {
            this.elements.darkModeBtn.textContent = isDark ? '☀️' : '🌙';
        }
        
        localStorage.setItem('theme', this.theme);
        return isDark;
    }

    /**
     * Toggle sidebar (chat history)
     */
    toggleSidebar() {
        if (this.elements.sidebar) {
            const isCollapsed = this.elements.sidebar.classList.toggle('collapsed');
            const toggleBtn = document.getElementById('sidebarToggleBtn');
            const toggleIcon = document.getElementById('sidebarToggleIcon');
            
            if (toggleBtn) {
                toggleBtn.classList.toggle('sidebar-open', !isCollapsed);
            }
            if (toggleIcon) {
                toggleIcon.textContent = isCollapsed ? '▶' : '◀';
            }
            
            // Save preference
            localStorage.setItem('sidebarCollapsed', isCollapsed ? 'true' : 'false');
        }
    }
    
    /**
     * Initialize sidebar state from localStorage
     */
    initSidebarState() {
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (isCollapsed && this.elements.sidebar) {
            this.elements.sidebar.classList.add('collapsed');
            const toggleBtn = document.getElementById('sidebarToggleBtn');
            const toggleIcon = document.getElementById('sidebarToggleIcon');
            if (toggleBtn) toggleBtn.classList.remove('sidebar-open');
            if (toggleIcon) toggleIcon.textContent = '▶';
        }
    }

    /**
     * Close sidebar
     */
    closeSidebar() {
        if (this.elements.sidebar) {
            this.elements.sidebar.classList.add('collapsed');
            const toggleBtn = document.getElementById('sidebarToggleBtn');
            if (toggleBtn) toggleBtn.classList.remove('sidebar-open');
        }
    }

    /**
     * Show loading
     */
    showLoading() {
        if (this.elements.loading) {
            this.elements.loading.classList.add('active');
        }
        if (this.elements.sendBtn) {
            this.elements.sendBtn.disabled = true;
        }
    }

    /**
     * Hide loading
     */
    hideLoading() {
        if (this.elements.loading) {
            this.elements.loading.classList.remove('active');
        }
        if (this.elements.sendBtn) {
            this.elements.sendBtn.disabled = false;
        }
    }

    /**
     * Open modal
     */
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Close modal
     */
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active');
            document.body.style.overflow = 'auto';
        }
    }

    /**
     * Update storage display with fancy progress bar
     */
    updateStorageDisplay(storageInfo) {
        if (!this.elements.storageInfo || !storageInfo) return;
        
        const { sizeInMB, maxSizeMB, percentage, color } = storageInfo;
        
        // Determine status icon and message
        let statusIcon = '💚';
        let statusText = 'Tốt';
        if (percentage > 80) {
            statusIcon = '🔴';
            statusText = 'Đầy';
        } else if (percentage > 50) {
            statusIcon = '🟡';
            statusText = 'Cảnh báo';
        }
        
        this.elements.storageInfo.innerHTML = `
            <div class="storage-display">
                <div class="storage-header">
                    <span class="storage-icon">${statusIcon}</span>
                    <span class="storage-text">${sizeInMB}MB / ${maxSizeMB}MB</span>
                    <span class="storage-status">${statusText}</span>
                </div>
                <div class="storage-progress-container">
                    <div class="storage-progress-bar" style="width: ${percentage}%; background: ${color};"></div>
                </div>
                <div class="storage-footer">
                    <span class="storage-percentage">${percentage}% đã dùng</span>
                    <button class="storage-cleanup-btn" onclick="window.manualCleanup()" title="Xóa các chat cũ (giữ lại 5 gần nhất)">
                        🗑️ Dọn dẹp
                    </button>
                </div>
            </div>
        `;
    }

    /**
     * Render chat list
     */
    renderChatList(chatSessions, currentChatId, onSwitchChat, onDeleteChat) {
        if (!this.elements.chatList) return;
        
        const sortedChats = Object.keys(chatSessions).sort((a, b) => 
            chatSessions[b].updatedAt - chatSessions[a].updatedAt
        );
        
        this.elements.chatList.innerHTML = sortedChats.map(id => {
            const session = chatSessions[id];
            const isActive = id === currentChatId;
            const preview = session.messages.length > 0 
                ? (session.messages[1] || session.messages[0]).replace(/<[^>]*>/g, '').substring(0, 50) + '...'
                : 'No messages';
            
            return `
                <div class="chat-item ${isActive ? 'active' : ''}" data-chat-id="${id}">
                    <div class="chat-item-title">${this.escapeHtml(session.title)}</div>
                    <div class="chat-item-preview">${this.escapeHtml(preview)}</div>
                    <div class="chat-item-footer">
                        <span class="chat-item-time">${this.formatTimestamp(session.updatedAt)}</span>
                        <button class="chat-delete-btn" data-chat-id="${id}" title="Xóa">🗑️</button>
                    </div>
                </div>
            `;
        }).join('');

        // Attach event listeners
        this.elements.chatList.querySelectorAll('.chat-item').forEach(item => {
            const chatId = item.dataset.chatId;
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('chat-delete-btn')) {
                    onSwitchChat(chatId);
                }
            });
        });

        this.elements.chatList.querySelectorAll('.chat-delete-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const chatId = btn.dataset.chatId;
                onDeleteChat(chatId);
            });
        });
    }

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * Scroll chat to bottom
     */
    scrollToBottom() {
        if (this.elements.chatContainer) {
            this.elements.chatContainer.scrollTop = this.elements.chatContainer.scrollHeight;
        }
    }

    /**
     * Clear chat container
     */
    clearChat() {
        if (this.elements.chatContainer) {
            this.elements.chatContainer.innerHTML = '';
        }
    }

    /**
     * Show alert message
     */
    showAlert(message, type = 'info') {
        alert(message);
    }

    /**
     * Show confirm dialog
     */
    showConfirm(message) {
        return confirm(message);
    }

    /**
     * Get form values
     */
    getFormValues() {
        return {
            model: this.elements.modelSelect?.value || 'grok',
            context: this.elements.contextSelect?.value || 'casual',
            deepThinking: this.elements.deepThinkingCheck?.checked || false,
            message: this.elements.messageInput?.value || ''
        };
    }

    /**
     * Clear message input
     */
    clearInput() {
        if (this.elements.messageInput) {
            this.elements.messageInput.value = '';
            this.elements.messageInput.style.height = 'auto';
        }
    }

    /**
     * Set input value
     */
    setInputValue(value) {
        if (this.elements.messageInput) {
            this.elements.messageInput.value = value;
            this.elements.messageInput.focus();
        }
    }

    /**
     * Update model options based on availability
     */
    updateModelOptions(modelsStatus) {
        if (!this.elements.modelSelect) return;
        
        const options = this.elements.modelSelect.querySelectorAll('option');
        
        options.forEach(option => {
            const value = option.value;
            if (value.endsWith('-local')) {
                const modelKey = value === 'bloomvn-local' ? 'bloomvn' : 
                                value === 'qwen1.5-local' ? 'qwen1.5' :
                                value === 'qwen2.5-local' ? 'qwen2.5' : null;
                
                if (modelKey && modelsStatus[modelKey]) {
                    if (!modelsStatus[modelKey].available) {
                        option.disabled = true;
                        option.textContent += ' (Chưa tải)';
                    } else if (modelsStatus[modelKey].loaded) {
                        option.textContent = option.textContent.replace(' ⭐', '') + ' ✅';
                    }
                }
            }
        });
    }

    /**
     * Setup click outside modal to close
     */
    setupModalClickOutside(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modalId);
                }
            });
        }
    }

    /**
     * Show/hide deep thinking option based on model
     */
    updateDeepThinkingVisibility(model) {
        const container = document.getElementById('deepThinkingContainer');
        if (container) {
            // Show Deep Thinking for all models
            container.style.display = 'flex';
        }
    }
}
