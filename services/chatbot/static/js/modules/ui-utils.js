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
        // Cache welcome screen permanently — survives innerHTML clears
        this._welcomeScreen = document.getElementById('welcomeScreen');

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
     * New CSS: dark is default (no class), light = body.light-mode, eye-care = body.eye-care-mode
     */
    initDarkMode() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        this.theme = savedTheme;
        
        // Remove all theme classes first
        document.body.classList.remove('light-mode', 'eye-care-mode', 'dark-mode');
        
        if (savedTheme === 'light') {
            document.body.classList.add('light-mode');
            if (this.elements.darkModeBtn && window.swapLucideIcon) {
                window.swapLucideIcon(this.elements.darkModeBtn, 'moon');
            }
        } else if (savedTheme === 'eye-care') {
            document.body.classList.add('eye-care-mode');
            const eyeCareBtn = document.getElementById('eyeCareBtn');
            if (eyeCareBtn && window.swapLucideIcon) {
                window.swapLucideIcon(eyeCareBtn, 'sun-dim');
            }
            if (this.elements.darkModeBtn && window.swapLucideIcon) {
                window.swapLucideIcon(this.elements.darkModeBtn, 'moon');
            }
        } else {
            // Dark mode (default) — no class needed
            if (this.elements.darkModeBtn && window.swapLucideIcon) {
                window.swapLucideIcon(this.elements.darkModeBtn, 'sun');
            }
        }
    }

    /**
     * Toggle dark mode
     * Cycles: dark → light → dark
     */
    toggleDarkMode() {
        // Remove eye-care mode if active
        document.body.classList.remove('eye-care-mode');
        const eyeCareBtn = document.getElementById('eyeCareBtn');
        if (eyeCareBtn && window.swapLucideIcon) window.swapLucideIcon(eyeCareBtn, 'eye');
        
        // Toggle: dark (no class) ↔ light (light-mode class)
        const isCurrentlyLight = document.body.classList.contains('light-mode');
        document.body.classList.remove('dark-mode'); // Remove legacy class
        
        if (isCurrentlyLight) {
            // Switch to dark
            document.body.classList.remove('light-mode');
            this.theme = 'dark';
        } else {
            // Switch to light
            document.body.classList.add('light-mode');
            this.theme = 'light';
        }
        
        const isDark = this.theme === 'dark';
        if (this.elements.darkModeBtn && window.swapLucideIcon) {
            window.swapLucideIcon(this.elements.darkModeBtn, isDark ? 'sun' : 'moon');
        }
        
        localStorage.setItem('theme', this.theme);
        return isDark;
    }
    
    /**
     * Toggle Eye Care mode - reduces blue light with warm colors
     */
    toggleEyeCareMode() {
        // Remove other theme classes
        document.body.classList.remove('dark-mode', 'light-mode');
        if (this.elements.darkModeBtn && window.swapLucideIcon) {
            window.swapLucideIcon(this.elements.darkModeBtn, 'moon');
        }
        
        document.body.classList.toggle('eye-care-mode');
        const isEyeCare = document.body.classList.contains('eye-care-mode');
        
        const eyeCareBtn = document.getElementById('eyeCareBtn');
        if (eyeCareBtn && window.swapLucideIcon) {
            window.swapLucideIcon(eyeCareBtn, isEyeCare ? 'sun-dim' : 'eye');
            eyeCareBtn.title = isEyeCare ? 'Turn off Eye Care Mode' : 'Turn on Eye Care Mode';
        }
        
        this.theme = isEyeCare ? 'eye-care' : 'dark';
        localStorage.setItem('theme', this.theme);
        return isEyeCare;
    }

    /**
     * Check if viewport is mobile sized
     */
    isMobile() {
        return window.innerWidth <= 768;
    }

    /**
     * Update sidebar overlay visibility (mobile)
     */
    _updateSidebarOverlay(sidebarOpen) {
        const overlay = document.getElementById('sidebarOverlay');
        if (!overlay) return;
        if (sidebarOpen) {
            overlay.classList.remove('hidden');
        } else {
            overlay.classList.add('hidden');
        }
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
            
            // Update overlay on mobile
            if (this.isMobile()) {
                this._updateSidebarOverlay(!isCollapsed);
            }
            
            // Save preference (only on desktop)
            if (!this.isMobile()) {
                localStorage.setItem('sidebarCollapsed', isCollapsed ? 'true' : 'false');
            }
        }
    }
    
    /**
     * Initialize sidebar state from localStorage
     */
    initSidebarState() {
        // Ensure sidebar element exists and is visible first
        if (this.elements.sidebar) {
            this.elements.sidebar.classList.remove('collapsed');
            this.elements.sidebar.style.display = '';
            this.elements.sidebar.style.visibility = '';
            this.elements.sidebar.style.opacity = '';
        }

        // Always collapse on mobile
        if (this.isMobile()) {
            if (this.elements.sidebar) {
                this.elements.sidebar.classList.add('collapsed');
            }
            this._updateSidebarOverlay(false);

            // Tap overlay to close sidebar
            const overlay = document.getElementById('sidebarOverlay');
            if (overlay) {
                overlay.addEventListener('click', () => {
                    this.closeSidebar();
                });
            }
            return;
        }
        
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
            // Hide overlay on mobile
            this._updateSidebarOverlay(false);
        }
    }

    /**
     * Show loading
     */
    showLoading() {
        if (this.elements.loading) {
            this.elements.loading.style.display = 'block';
            this.elements.loading.classList.remove('hidden');
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
            this.elements.loading.style.display = 'none';
            this.elements.loading.classList.add('hidden');
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
            modal.classList.add('active', 'open');
            document.body.style.overflow = 'hidden';
        }
    }

    /**
     * Close modal with animation
     */
    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.classList.remove('active', 'open');
            document.body.style.overflow = 'auto';
        }
    }

    /**
     * Update storage display with fancy progress bar
     */
    updateStorageDisplay(storageInfo) {
        if (!this.elements.storageInfo || !storageInfo) return;
        
        const { sizeInMB, maxSizeMB, percentage, color, sessionCount } = storageInfo;
        
        // Prevent runtime errors when rendering storage widget.
        let statusIcon = '🟢';
        let statusText = 'Good';
        if (percentage >= 90) {
            statusIcon = '🔴';
            statusText = 'Critical';
        } else if (percentage >= 75) {
            statusIcon = '🟠';
            statusText = 'Warning';
        } else if (percentage >= 50) {
            statusIcon = '🟡';
            statusText = 'Moderate';
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
                    <span class="storage-percentage">${percentage}% Used</span>
                    <button class="storage-cleanup-btn" onclick="window.manualCleanup()" title="Clear old chats (keep last 5)">
                        <i data-lucide="trash-2" style="width:12px;height:12px;"></i> Clear
                    </button>
                </div>
                <span class="storage__label">
                    <i data-lucide="database" style="width:11px;height:11px;"></i>
                    ${sizeInMB} / ${maxSizeMB} MB
                </span>
            </div>
        `;
        if (window.lucide) lucide.createIcons({ nodes: [this.elements.storageInfo] });
    }

    /**
     * Render chat list with drag & drop support
     */
    renderChatList(chatSessions, currentChatId, onSwitchChat, onDeleteChat, onReorder, onTogglePin) {
        if (!this.elements.chatList) {
            console.warn('[DEBUG] renderChatList: chatList element is NULL!');
            return;
        }

        // Store callbacks for context menu
        this._chatCallbacks = { onSwitchChat, onDeleteChat, onTogglePin };
        this._chatSessions = chatSessions;
        
        // Use ChatManager's sorted order if available, otherwise fallback
        let sortedChats;
        if (window.chatManager && window.chatManager.getSortedChatIds) {
            sortedChats = window.chatManager.getSortedChatIds();
        } else {
            sortedChats = Object.keys(chatSessions).sort((a, b) => 
                chatSessions[b].updatedAt - chatSessions[a].updatedAt
            );
        }
        
        this.elements.chatList.innerHTML = sortedChats.map(id => {
            const session = chatSessions[id];
            if (!session) return '';
            const isActive = id === currentChatId;
            const isPinned = session.pinned || false;
            const messages = Array.isArray(session.messages) ? session.messages : [];
            const firstMsg = messages[1] || messages[0];
            const preview = messages.length > 0 && typeof firstMsg === 'string'
                ? firstMsg.replace(/<[^>]*>/g, '').substring(0, 50) + '...'
                : 'No messages';
            const msgCount = messages.length;
            
            return `
                <div class="sidebar__chat-item ${isActive ? 'active' : ''} ${isPinned ? 'pinned' : ''}" 
                     data-chat-id="${id}" draggable="true">
                    <span class="drag-handle" title="Drag to reorder">⠿</span>
                    <div class="sidebar__chat-info">
                        <div class="sidebar__chat-title">${this.escapeHtml(session.title)}</div>
                        <div class="sidebar__chat-preview">${this.escapeHtml(preview)}</div>
                    </div>
                    ${msgCount > 0 ? `<span class="sidebar__chat-context"><i data-lucide="message-square" style="width:10px;height:10px;"></i> ${msgCount}</span>` : ''}
                    <div class="sidebar__chat-actions">
                        ${isPinned ? '<span class="sidebar__chat-pin-indicator" title="Pinned"><i data-lucide="pin" style="width:11px;height:11px;"></i></span>' : ''}
                        <button class="sidebar__chat-menu-btn" data-chat-id="${id}" title="Menu">
                            <svg width="14" height="14" viewBox="0 0 16 16" fill="currentColor">
                                <circle cx="8" cy="3" r="1.5"/><circle cx="8" cy="8" r="1.5"/><circle cx="8" cy="13" r="1.5"/>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
        }).join('');

        // Refresh Lucide icons in chat list
        if (window.lucide) {
            lucide.createIcons({ nodes: [this.elements.chatList] });
        }

        // Show menu button on hover
        this.elements.chatList.querySelectorAll('.sidebar__chat-item').forEach(item => {
            item.addEventListener('mouseenter', () => {
                const menuBtn = item.querySelector('.sidebar__chat-menu-btn');
                if (menuBtn) menuBtn.style.opacity = '1';
            });
            item.addEventListener('mouseleave', () => {
                const menuBtn = item.querySelector('.sidebar__chat-menu-btn');
                if (menuBtn) menuBtn.style.opacity = '';
            });
        });

        // Attach click event listeners
        this.elements.chatList.querySelectorAll('.sidebar__chat-item').forEach(item => {
            const chatId = item.dataset.chatId;
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.sidebar__chat-menu-btn')) {
                    onSwitchChat(chatId);
                    if (this.isMobile()) this.closeSidebar();
                }
            });
        });

        // Ellipsis menu button listeners
        this.elements.chatList.querySelectorAll('.sidebar__chat-menu-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this._showChatContextMenu(btn.dataset.chatId, btn, chatSessions);
            });
        });

        // ─── Drag & Drop ───
        try {
            this._setupChatDragDrop(onReorder);
        } catch (e) {
            console.error('[DEBUG] _setupChatDragDrop failed:', e);
        }
    }

    /**
     * Show context menu for a chat item
     */
    _showChatContextMenu(chatId, anchorEl, chatSessions) {
        // Remove any existing menu
        const old = document.querySelector('.chat-ctx-menu');
        if (old) old.remove();

        const session = chatSessions[chatId];
        if (!session) return;
        const isPinned = session.pinned || false;

        const menu = document.createElement('div');
        menu.className = 'chat-ctx-menu';
        menu.innerHTML = `
            <button class="chat-ctx-item" data-action="pin">
                <i data-lucide="${isPinned ? 'pin-off' : 'pin'}" style="width:14px;height:14px;"></i>
                ${isPinned ? 'Bỏ ghim' : 'Ghim'}
            </button>
            <button class="chat-ctx-item" data-action="rename">
                <i data-lucide="pencil" style="width:14px;height:14px;"></i>
                Đổi tên
            </button>
            <button class="chat-ctx-item" data-action="export">
                <i data-lucide="download" style="width:14px;height:14px;"></i>
                Xuất chat
            </button>
            <div class="chat-ctx-divider"></div>
            <button class="chat-ctx-item chat-ctx-item--danger" data-action="delete">
                <i data-lucide="trash-2" style="width:14px;height:14px;"></i>
                Xóa
            </button>
        `;
        document.body.appendChild(menu);

        // Position near anchor
        const rect = anchorEl.getBoundingClientRect();
        let top = rect.bottom + 4;
        let left = rect.right - menu.offsetWidth;
        // Keep within viewport
        if (left < 8) left = 8;
        if (top + menu.offsetHeight > window.innerHeight - 8) {
            top = rect.top - menu.offsetHeight - 4;
        }
        menu.style.top = top + 'px';
        menu.style.left = left + 'px';

        if (window.lucide) lucide.createIcons({ nodes: [menu] });

        // Handle actions
        menu.addEventListener('click', (e) => {
            const btn = e.target.closest('[data-action]');
            if (!btn) return;
            const action = btn.dataset.action;
            menu.remove();

            if (action === 'pin' && this._chatCallbacks?.onTogglePin) {
                this._chatCallbacks.onTogglePin(chatId);
            } else if (action === 'delete' && this._chatCallbacks?.onDeleteChat) {
                this._chatCallbacks.onDeleteChat(chatId);
            } else if (action === 'rename') {
                this._inlineRenameChat(chatId);
            } else if (action === 'export') {
                // Switch to this chat first, then export
                if (this._chatCallbacks?.onSwitchChat) {
                    this._chatCallbacks.onSwitchChat(chatId);
                }
                setTimeout(() => {
                    if (window.downloadChatAsJSON) window.downloadChatAsJSON();
                }, 200);
            }
        });

        // Close on outside click
        const closeMenu = (e) => {
            if (!menu.contains(e.target) && !anchorEl.contains(e.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu, true);
            }
        };
        // Delay to avoid immediate close from the same click
        requestAnimationFrame(() => {
            document.addEventListener('click', closeMenu, true);
        });
    }

    /**
     * Inline rename a chat in the sidebar
     */
    _inlineRenameChat(chatId) {
        const item = this.elements.chatList?.querySelector(`[data-chat-id="${chatId}"]`);
        if (!item) return;
        const titleEl = item.querySelector('.sidebar__chat-title');
        if (!titleEl) return;

        const oldTitle = titleEl.textContent;
        const input = document.createElement('input');
        input.type = 'text';
        input.className = 'sidebar__chat-rename-input';
        input.value = oldTitle;
        input.maxLength = 100;
        titleEl.replaceWith(input);
        input.focus();
        input.select();

        const commit = () => {
            const newTitle = input.value.trim() || oldTitle;
            // Restore title element
            const newTitleEl = document.createElement('div');
            newTitleEl.className = 'sidebar__chat-title';
            newTitleEl.textContent = newTitle;
            input.replaceWith(newTitleEl);
            // Persist
            if (window.chatManager && window.chatManager.chatSessions[chatId]) {
                window.chatManager.chatSessions[chatId].title = newTitle;
                window.chatManager.chatSessions[chatId].updatedAt = new Date();
                window.chatManager.chatSessions[chatId].order = null;
                window.chatManager.saveSessions();
                window.dispatchEvent(new Event('chatListNeedsUpdate'));
            }
        };

        input.addEventListener('blur', commit);
        input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') { e.preventDefault(); input.blur(); }
            if (e.key === 'Escape') { input.value = oldTitle; input.blur(); }
        });
    }

    /**
     * Setup drag & drop for chat list items
     */
    _setupChatDragDrop(onReorder) {
        let draggedId = null;
        const chatList = this.elements.chatList;
        
        chatList.querySelectorAll('.sidebar__chat-item').forEach(item => {
            item.addEventListener('dragstart', (e) => {
                draggedId = item.dataset.chatId;
                item.classList.add('dragging');
                e.dataTransfer.effectAllowed = 'move';
                e.dataTransfer.setData('text/plain', draggedId);
                // Slight delay to allow CSS transition
                requestAnimationFrame(() => item.style.opacity = '0.4');
            });

            item.addEventListener('dragend', () => {
                item.classList.remove('dragging');
                item.style.opacity = '';
                // Clear all drop indicators
                chatList.querySelectorAll('.drag-over-top, .drag-over-bottom').forEach(el => {
                    el.classList.remove('drag-over-top', 'drag-over-bottom');
                });
            });

            item.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                
                const rect = item.getBoundingClientRect();
                const midY = rect.top + rect.height / 2;
                
                // Clear previous indicators on this item
                item.classList.remove('drag-over-top', 'drag-over-bottom');
                
                if (e.clientY < midY) {
                    item.classList.add('drag-over-top');
                } else {
                    item.classList.add('drag-over-bottom');
                }
            });

            item.addEventListener('dragleave', () => {
                item.classList.remove('drag-over-top', 'drag-over-bottom');
            });

            item.addEventListener('drop', (e) => {
                e.preventDefault();
                const fromId = e.dataTransfer.getData('text/plain');
                const toId = item.dataset.chatId;
                
                if (fromId && toId && fromId !== toId && onReorder) {
                    const rect = item.getBoundingClientRect();
                    const midY = rect.top + rect.height / 2;
                    const position = e.clientY < midY ? 'before' : 'after';
                    onReorder(fromId, toId, position);
                }
                
                item.classList.remove('drag-over-top', 'drag-over-bottom');
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
            // Detach welcome screen first so innerHTML doesn't destroy the node
            if (this._welcomeScreen && this._welcomeScreen.parentNode === this.elements.chatContainer) {
                this.elements.chatContainer.removeChild(this._welcomeScreen);
            }
            this.elements.chatContainer.innerHTML = '';
        }
    }

    showWelcomeScreen() {
        const ws = this._welcomeScreen || document.getElementById('welcomeScreen');
        if (!ws || !this.elements.chatContainer) return;
        ws.style.display = '';
        if (ws.parentNode !== this.elements.chatContainer) {
            this.elements.chatContainer.appendChild(ws);
        }
    }

    hideWelcomeScreen() {
        const ws = this._welcomeScreen || document.getElementById('welcomeScreen');
        if (ws) ws.style.display = 'none';
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
        // Get thinking mode from the new selector (instant or multi-thinking)
        const thinkingMode = window.getThinkingMode ? window.getThinkingMode() : 'instant';
        const deepThinking = thinkingMode === 'multi-thinking';
        
        return {
            model: this.elements.modelSelect?.value || 'grok',
            context: this.elements.contextSelect?.value || 'casual',
            deepThinking: deepThinking,
            thinkingMode: thinkingMode,
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
