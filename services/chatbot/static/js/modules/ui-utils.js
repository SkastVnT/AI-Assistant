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
            modal.classList.add('closing');
            document.body.style.overflow = '';
            setTimeout(() => {
                modal.classList.remove('closing');
                modal.style.display = 'none';
            }, 250);
        }
    }

    /**
     * Update storage display with fancy progress bar
     */
    updateStorageDisplay(storageInfo) {
        if (!this.elements.storageInfo || !storageInfo) return;
        
        const { sizeInMB, maxSizeMB, percentage, color, sessionCount } = storageInfo;
        
        this.elements.storageInfo.innerHTML = `
            <div class="storage" title="${sizeInMB} MB / ${maxSizeMB} MB ∙ ${sessionCount} chats ∙ ${percentage}% used">
                <div class="storage__bar">
                    <div class="storage__fill" style="width: ${Math.max(percentage, 1)}%; background: ${color};"></div>
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
        if (!this.elements.chatList) return;
        
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
            const preview = session.messages.length > 0 
                ? (session.messages[1] || session.messages[0]).replace(/<[^>]*>/g, '').substring(0, 50) + '...'
                : 'No messages';
            const msgCount = session.messages.length;
            
            return `
                <div class="sidebar__chat-item ${isActive ? 'active' : ''} ${isPinned ? 'pinned' : ''}" 
                     data-chat-id="${id}" draggable="true">
                    <span class="drag-handle" title="Drag to reorder">⠿</span>
                    <div class="sidebar__chat-title">${this.escapeHtml(session.title)}</div>
                    <div class="sidebar__chat-preview">${this.escapeHtml(preview)}</div>
                    ${msgCount > 0 ? `<span class="sidebar__chat-context"><i data-lucide="message-square" style="width:10px;height:10px;"></i> ${msgCount}</span>` : ''}
                    <button class="sidebar__chat-more" data-chat-id="${id}" title="More">
                        <i data-lucide="ellipsis-vertical" style="width:14px;height:14px;"></i>
                    </button>
                    ${isPinned ? '<span class="sidebar__pin-indicator"><i data-lucide="pin" style="width:9px;height:9px;"></i></span>' : ''}
                </div>
            `;
        }).join('');

        // Refresh Lucide icons in chat list
        if (window.lucide) {
            lucide.createIcons({ nodes: [this.elements.chatList] });
        }

        // Attach click event listeners
        this.elements.chatList.querySelectorAll('.sidebar__chat-item').forEach(item => {
            const chatId = item.dataset.chatId;
            item.addEventListener('click', (e) => {
                if (!e.target.closest('.sidebar__chat-more')) {
                    onSwitchChat(chatId);
                    if (this.isMobile()) this.closeSidebar();
                }
            });
        });

        // Context menu on "..." button
        this.elements.chatList.querySelectorAll('.sidebar__chat-more').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const chatId = btn.dataset.chatId;
                const item = btn.closest('.sidebar__chat-item');
                const isPinned = item && item.classList.contains('pinned');
                this._showChatContextMenu(e, chatId, isPinned, { onDeleteChat, onTogglePin });
            });
        });

        // ─── Drag & Drop ───
        this._setupChatDragDrop(onReorder);
    }

    /**
     * Show context menu for a chat item
     */
    _showChatContextMenu(e, chatId, isPinned, { onDeleteChat, onTogglePin }) {
        // Remove any existing menu
        document.querySelectorAll('.chat-ctx-menu').forEach(m => m.remove());

        const menu = document.createElement('div');
        menu.className = 'chat-ctx-menu';
        menu.innerHTML = `
            <button class="chat-ctx-menu__item" data-action="pin">
                <i data-lucide="${isPinned ? 'pin-off' : 'pin'}" style="width:15px;height:15px;"></i>
                ${isPinned ? 'Bỏ ghim' : 'Ghim'}
            </button>
            <button class="chat-ctx-menu__item" data-action="rename">
                <i data-lucide="pencil" style="width:15px;height:15px;"></i>
                Đổi tên
            </button>
            <button class="chat-ctx-menu__item" data-action="export">
                <i data-lucide="download" style="width:15px;height:15px;"></i>
                Xuất chat
            </button>
            <div class="chat-ctx-menu__divider"></div>
            <button class="chat-ctx-menu__item chat-ctx-menu__item--danger" data-action="delete">
                <i data-lucide="trash-2" style="width:15px;height:15px;"></i>
                Xóa
            </button>
        `;
        document.body.appendChild(menu);

        // Position near the button
        const btnRect = e.currentTarget.getBoundingClientRect();
        let top = btnRect.bottom + 4;
        let left = btnRect.right - menu.offsetWidth;
        // Keep within viewport
        if (left < 8) left = 8;
        if (top + menu.offsetHeight > window.innerHeight - 8) {
            top = btnRect.top - menu.offsetHeight - 4;
        }
        menu.style.top = top + 'px';
        menu.style.left = left + 'px';

        // Render lucide icons inside menu
        if (window.lucide) lucide.createIcons({ nodes: [menu] });

        // Handle menu item clicks
        menu.addEventListener('click', (ev) => {
            const action = ev.target.closest('[data-action]')?.dataset.action;
            if (!action) return;
            menu.remove();

            switch (action) {
                case 'pin':
                    if (onTogglePin) onTogglePin(chatId);
                    break;
                case 'delete':
                    onDeleteChat(chatId);
                    break;
                case 'rename':
                    this._inlineRenameChat(chatId);
                    break;
                case 'export':
                    if (window.app && window.app.exportChat) {
                        window.app.exportChat();
                    }
                    break;
            }
        });

        // Close on outside click
        const closeMenu = (ev) => {
            if (!menu.contains(ev.target)) {
                menu.remove();
                document.removeEventListener('click', closeMenu, true);
            }
        };
        setTimeout(() => document.addEventListener('click', closeMenu, true), 0);
    }

    /**
     * Inline rename a chat title
     */
    _inlineRenameChat(chatId) {
        const item = this.elements.chatList.querySelector(`[data-chat-id="${chatId}"]`);
        if (!item) return;
        const titleEl = item.querySelector('.sidebar__chat-title');
        if (!titleEl) return;

        const oldTitle = titleEl.textContent;
        const input = document.createElement('input');
        input.type = 'text';
        input.value = oldTitle;
        input.className = 'sidebar__chat-rename-input';
        input.style.cssText = 'width:100%;font-size:inherit;font-weight:500;background:var(--bg-secondary);color:var(--text-primary);border:1px solid var(--accent);border-radius:4px;padding:2px 6px;outline:none;';

        titleEl.replaceWith(input);
        input.focus();
        input.select();

        const commit = () => {
            const newTitle = input.value.trim() || oldTitle;
            const newTitleEl = document.createElement('div');
            newTitleEl.className = 'sidebar__chat-title';
            newTitleEl.textContent = newTitle;
            input.replaceWith(newTitleEl);

            if (newTitle !== oldTitle) {
                // Save to localStorage
                const sessions = JSON.parse(localStorage.getItem('chatSessions') || '{}');
                if (sessions[chatId]) {
                    sessions[chatId].title = newTitle;
                    localStorage.setItem('chatSessions', JSON.stringify(sessions));
                }
            }
        };

        input.addEventListener('blur', commit);
        input.addEventListener('keydown', (ev) => {
            if (ev.key === 'Enter') { ev.preventDefault(); input.blur(); }
            if (ev.key === 'Escape') { input.value = oldTitle; input.blur(); }
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
        // Get thinking mode from the new selector
        const thinkingMode = window.getThinkingMode ? window.getThinkingMode() : 'instant';
        let deepThinking = false;
        
        // Determine if deep thinking should be enabled based on mode
        if (thinkingMode === 'thinking' || thinkingMode === 'deep') {
            deepThinking = true;
        } else if (thinkingMode === 'auto') {
            // Auto mode: let coordinatedReasoning decide later
            deepThinking = 'auto';
        }
        
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
