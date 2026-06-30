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
     * Initialize theme.
     * Two themes only: 'dark' (default, no class) and 'eye-care' (body.eye-care-mode).
     * Any legacy 'light' value in localStorage is migrated to 'dark'.
     */
    initDarkMode() {
        let savedTheme = localStorage.getItem('theme') || 'dark';
        if (savedTheme !== 'eye-care') savedTheme = 'dark';
        this.theme = savedTheme;

        document.body.classList.remove('light-mode', 'eye-care-mode', 'dark-mode');

        if (savedTheme === 'eye-care') {
            document.body.classList.add('eye-care-mode');
        }

        this._refreshThemeIcons();
        localStorage.setItem('theme', this.theme);
    }

    /**
     * Toggle between dark and eye-comfort themes.
     */
    toggleDarkMode() {
        this.theme = (this.theme === 'eye-care') ? 'dark' : 'eye-care';
        document.body.classList.remove('light-mode', 'dark-mode', 'eye-care-mode');
        if (this.theme === 'eye-care') {
            document.body.classList.add('eye-care-mode');
        }
        this._refreshThemeIcons();
        localStorage.setItem('theme', this.theme);
        return this.theme === 'dark';
    }

    /**
     * Eye-comfort toggle (alias for toggleDarkMode for backward-compat with eyeCareBtn).
     */
    toggleEyeCareMode() {
        this.toggleDarkMode();
        return this.theme === 'eye-care';
    }

    _refreshThemeIcons() {
        const isEyeCare = this.theme === 'eye-care';
        if (this.elements.darkModeBtn && window.swapLucideIcon) {
            window.swapLucideIcon(this.elements.darkModeBtn, isEyeCare ? 'moon' : 'sun-dim');
            this.elements.darkModeBtn.title = isEyeCare ? 'Switch to Dark theme' : 'Switch to Eye Comfort theme';
        }
        const eyeCareBtn = document.getElementById('eyeCareBtn');
        if (eyeCareBtn && window.swapLucideIcon) {
            window.swapLucideIcon(eyeCareBtn, isEyeCare ? 'sun-dim' : 'eye');
            eyeCareBtn.title = isEyeCare ? 'Turn off Eye Comfort' : 'Turn on Eye Comfort';
        }
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
    showLoading(thinkingMode = 'instant') {
        if (this.elements.loading) {
            this.elements.loading.style.display = 'block';
            this.elements.loading.classList.remove('hidden');
            this.elements.loading.classList.add('active');
        }
        // Mode-specific status text
        const loadingText = document.getElementById('loadingText');
        if (loadingText) {
            const modeLabels = {
                'instant':        '⚡ Đang trả lời...',
                'thinking':       '🤔 Đang phân tích...',
                'multi-thinking': '🧠 Đang suy nghĩ...',
            };
            loadingText.textContent = modeLabels[thinkingMode] || '⚡ Đang trả lời...';
        }
        // Live elapsed timer
        const timerEl = document.getElementById('loadingTimer');
        if (timerEl) {
            timerEl.textContent = '0s';
            this._loadingStartTime = Date.now();
            clearInterval(this._loadingTimerInterval);
            this._loadingTimerInterval = setInterval(() => {
                const elapsed = Math.round((Date.now() - this._loadingStartTime) / 1000);
                timerEl.textContent = elapsed + 's';
            }, 1000);
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
        // Stop the elapsed timer
        clearInterval(this._loadingTimerInterval);
        const timerEl = document.getElementById('loadingTimer');
        if (timerEl) timerEl.textContent = '';
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
                    <button class="storage-cleanup-btn" data-action="storage:cleanup" title="Dọn các cuộc trò chuyện cũ (chỉ chạy khi bạn bấm)">
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
     * Build a smart preview + asset counts from a session's HTML messages.
     * Returns { preview, previewClass, imageCount, videoCount }.
     */
    _summarizeChatMessages(messages) {
        const out = { preview: 'Chưa có tin nhắn', previewClass: 'sidebar__chat-preview--empty', imageCount: 0, videoCount: 0 };
        if (!Array.isArray(messages) || messages.length === 0) return out;
        // Tally generated assets across the whole session.
        for (const m of messages) {
            if (typeof m !== 'string') continue;
            // Count <img> that are part of generated images (data URIs, blob,
            // /static/uploads/, /images/, image-message wrappers). Conservative:
            // count any <img> — most chat <img> tags ARE generated assets.
            const imgs = m.match(/<img[\s>]/gi);
            if (imgs) out.imageCount += imgs.length;
            const vids = m.match(/<video[\s>]/gi);
            if (vids) out.videoCount += vids.length;
        }
        // Pick a preview source: prefer the user prompt (msg 0 is usually
        // user, msg 1 is assistant). Fall back to the last message.
        const firstUser = typeof messages[0] === 'string' ? messages[0] : '';
        const fallback = typeof messages[messages.length - 1] === 'string'
            ? messages[messages.length - 1] : '';
        const source = firstUser || fallback;
        const text = String(source).replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim();
        if (text) {
            out.preview = this.escapeHtml(text.length > 60 ? text.slice(0, 60) + '…' : text);
            out.previewClass = '';
        } else if (out.imageCount > 0 || out.videoCount > 0) {
            const parts = [];
            if (out.imageCount > 0) parts.push(`${out.imageCount} ảnh`);
            if (out.videoCount > 0) parts.push(`${out.videoCount} video`);
            out.preview = `Đã tạo ${parts.join(' + ')}`;
            out.previewClass = 'sidebar__chat-preview--asset';
        }
        return out;
    }

    /**
     * Compact relative timestamp: just now / 5m / 2h / Yesterday / 12 Mar.
     */
    _relativeTime(ts) {
        const ms = ts instanceof Date ? ts.getTime() : Number(ts);
        if (!ms) return '';
        const now = Date.now();
        const diff = Math.max(0, now - ms);
        const m = Math.floor(diff / 60000);
        if (m < 1) return 'vừa xong';
        if (m < 60) return `${m}m`;
        const h = Math.floor(m / 60);
        if (h < 24) return `${h}h`;
        const d = Math.floor(h / 24);
        if (d === 1) return 'Hôm qua';
        if (d < 7) return `${d}d`;
        try {
            return new Date(ts).toLocaleDateString('vi-VN', { day: '2-digit', month: 'short' });
        } catch { return ''; }
    }

    /** Coarse day-bucket key used for separator headers in the sidebar. */
    _dayGroupKey(ts) {
        if (!ts) return 'earlier';
        const now = Date.now();
        const diffH = (now - ts) / 3600000;
        if (diffH < 24) return 'today';
        if (diffH < 48) return 'yesterday';
        if (diffH < 24 * 7) return 'week';
        return 'earlier';
    }

    /** Insert <h4> separators between day-group buckets. Idempotent. */
    _injectDayGroupHeaders() {
        const list = this.elements.chatList;
        if (!list) return;
        // Remove any old separators (re-render path).
        list.querySelectorAll('.sidebar__chat-group').forEach(el => el.remove());
        const labels = {
            today: 'Hôm nay',
            yesterday: 'Hôm qua',
            week: 'Tuần này',
            earlier: 'Trước đó',
        };
        let lastGroup = null;
        const items = Array.from(list.querySelectorAll('.sidebar__chat-item'));
        items.forEach(item => {
            const g = item.dataset.dayGroup || 'earlier';
            if (g !== lastGroup) {
                const header = document.createElement('div');
                header.className = `sidebar__chat-group sidebar__chat-group--${g}`;
                header.textContent = labels[g] || g;
                list.insertBefore(header, item);
                lastGroup = g;
            }
        });
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

        // Ensure select state is initialized
        if (!this._selectedIds) this._selectedIds = new Set();
        const selectMode = !!this._selectMode;
        
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
            // Smart preview: detect generated assets (images/video) so the user
            // can tell what was created at a glance, instead of "No messages".
            const meta = this._summarizeChatMessages(messages);
            const preview = meta.preview;
            const msgCount = messages.length;
            const isChecked = this._selectedIds.has(id);
            const tsLabel = this._relativeTime(session.updatedAt || session.createdAt || 0);
            const groupKey = this._dayGroupKey(session.updatedAt || session.createdAt || 0);
            const groupHeader = (window.chatManager && !window.chatManager.getSortedChatIds)
                ? '' // Suppress headers when caller already fed an explicit ordering
                : '';

            const badges = [];
            if (meta.imageCount > 0) {
                badges.push(`<span class="sidebar__chat-badge sidebar__chat-badge--image" title="${meta.imageCount} ảnh đã tạo"><i data-lucide="image"></i> ${meta.imageCount}</span>`);
            }
            if (meta.videoCount > 0) {
                badges.push(`<span class="sidebar__chat-badge sidebar__chat-badge--video" title="${meta.videoCount} video đã tạo"><i data-lucide="video"></i> ${meta.videoCount}</span>`);
            }
            if (msgCount > 0) {
                badges.push(`<span class="sidebar__chat-context" title="${msgCount} tin nhắn"><i data-lucide="message-square"></i> ${msgCount}</span>`);
            }
            const badgeHtml = badges.length
                ? `<div class="sidebar__chat-badges">${badges.join('')}</div>`
                : '';

            return `
                <div class="sidebar__chat-item ${isActive ? 'active' : ''} ${isPinned ? 'pinned' : ''} ${selectMode ? 'select-mode' : ''} ${isChecked ? 'selected' : ''}"
                     data-chat-id="${id}" data-day-group="${groupKey}" draggable="${selectMode ? 'false' : 'true'}">
                    ${selectMode ? `<input type="checkbox" class="sidebar__chat-checkbox" data-chat-id="${id}" ${isChecked ? 'checked' : ''}>` : '<span class="drag-handle" title="Drag to reorder">⠿</span>'}
                    <div class="sidebar__chat-info">
                        <div class="sidebar__chat-titlerow">
                            <div class="sidebar__chat-title">${this.escapeHtml(session.title)}</div>
                            ${tsLabel ? `<span class="sidebar__chat-time" title="${new Date(session.updatedAt || session.createdAt || 0).toLocaleString()}">${tsLabel}</span>` : ''}
                        </div>
                        <div class="sidebar__chat-preview ${meta.previewClass}">${preview}</div>
                        ${badgeHtml}
                    </div>
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

        // Inject day-group separators (Today / Yesterday / This week / Earlier)
        this._injectDayGroupHeaders();

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
                if (this._selectMode) {
                    // In select mode: toggle checkbox on row click (unless checkbox itself was clicked)
                    if (!e.target.closest('.sidebar__chat-checkbox')) {
                        const cb = item.querySelector('.sidebar__chat-checkbox');
                        if (cb) { cb.checked = !cb.checked; cb.dispatchEvent(new Event('change', { bubbles: true })); }
                    }
                    return;
                }
                if (!e.target.closest('.sidebar__chat-menu-btn')) {
                    onSwitchChat(chatId);
                    if (this.isMobile()) this.closeSidebar();
                }
            });
        });

        // Checkbox change listeners (select mode)
        this.elements.chatList.querySelectorAll('.sidebar__chat-checkbox').forEach(cb => {
            cb.addEventListener('change', (e) => {
                e.stopPropagation();
                const id = cb.dataset.chatId;
                const item = cb.closest('.sidebar__chat-item');
                if (cb.checked) {
                    this._selectedIds.add(id);
                    item?.classList.add('selected');
                } else {
                    this._selectedIds.delete(id);
                    item?.classList.remove('selected');
                }
                this._updateSelectToolbar();
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
        if (!selectMode) {
            try {
                this._setupChatDragDrop(onReorder);
            } catch (e) {
                console.error('[DEBUG] _setupChatDragDrop failed:', e);
            }
        }
    }

    /** Toggle select mode on/off */
    toggleSelectMode() {
        this._selectMode = !this._selectMode;
        this._selectedIds = new Set();

        const toolbar = document.getElementById('chatSelectToolbar');
        const selectBtn = document.getElementById('chatSelectBtn');
        if (toolbar) toolbar.style.display = this._selectMode ? 'flex' : 'none';
        if (selectBtn) selectBtn.classList.toggle('active', this._selectMode);

        // Rerender with/without checkboxes
        if (this._chatCallbacks && this._chatSessions) {
            const { onSwitchChat, onDeleteChat, onTogglePin } = this._chatCallbacks;
            this.renderChatList(
                this._chatSessions,
                window.chatManager?.currentChatId,
                onSwitchChat, onDeleteChat,
                () => {}, onTogglePin
            );
        }
        this._updateSelectToolbar();

        // Wire Select All
        const selectAll = document.getElementById('chatSelectAll');
        if (selectAll) {
            selectAll.checked = false;
            selectAll.onchange = () => {
                const checked = selectAll.checked;
                this.elements.chatList.querySelectorAll('.sidebar__chat-checkbox').forEach(cb => {
                    cb.checked = checked;
                    const id = cb.dataset.chatId;
                    const item = cb.closest('.sidebar__chat-item');
                    if (checked) { this._selectedIds.add(id); item?.classList.add('selected'); }
                    else { this._selectedIds.delete(id); item?.classList.remove('selected'); }
                });
                this._updateSelectToolbar();
            };
        }
    }

    /** Update delete button count + disabled state */
    _updateSelectToolbar() {
        const n = this._selectedIds ? this._selectedIds.size : 0;
        const deleteBtn = document.getElementById('chatDeleteSelectedBtn');
        const countEl = document.getElementById('chatDeleteSelectedCount');
        const selectAll = document.getElementById('chatSelectAll');

        if (deleteBtn) deleteBtn.disabled = n === 0;
        if (countEl) countEl.textContent = n > 0 ? `Xóa (${n})` : 'Xóa';

        // Sync select-all indeterminate state
        const total = this.elements.chatList?.querySelectorAll('.sidebar__chat-checkbox').length || 0;
        if (selectAll) {
            selectAll.checked = total > 0 && n === total;
            selectAll.indeterminate = n > 0 && n < total;
        }
    }

    /** Delete all selected chats — single confirmation for the whole batch. */
    async deleteSelectedChats() {
        if (!this._selectedIds || this._selectedIds.size === 0) return;
        const ids = Array.from(this._selectedIds);
        const ok = await this.showConfirmAsync(
            `Xóa ${ids.length} cuộc trò chuyện đã chọn?`,
            { danger: true, okText: 'Xóa', cancelText: 'Huỷ' }
        );
        if (!ok) return;
        ids.forEach(id => {
            if (this._chatCallbacks?.onDeleteChat) {
                // Pass a flag so handleDeleteChat doesn't re-confirm.
                this._chatCallbacks.onDeleteChat(id, { skipConfirm: true });
            }
        });
        this._selectMode = false;
        this._selectedIds = new Set();
        const toolbar = document.getElementById('chatSelectToolbar');
        const selectBtn = document.getElementById('chatSelectBtn');
        if (toolbar) toolbar.style.display = 'none';
        if (selectBtn) selectBtn.classList.remove('active');
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

        // Position near anchor — defer one frame so offsetWidth/Height are measured after paint
        requestAnimationFrame(() => {
            const rect = anchorEl.getBoundingClientRect();
            let top = rect.bottom + 4;
            let left = rect.right - menu.offsetWidth;
            if (left < 8) left = 8;
            if (top + menu.offsetHeight > window.innerHeight - 8) {
                top = rect.top - menu.offsetHeight - 4;
            }
            menu.style.top = top + 'px';
            menu.style.left = left + 'px';
        });

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
     * Show alert message (Electron-safe — uses inline modal, not window.alert).
     * Returns a Promise that resolves when the user dismisses.
     */
    showAlert(message, type = 'info') {
        return UIUtils._showModal({ message, kind: 'alert', type });
    }

    /**
     * Synchronous-style confirm fallback. Prefer await showConfirmAsync(message).
     * Returns boolean — but in Electron the inline modal is async, so we resolve
     * immediately as `true` to keep legacy code paths from blocking. New code
     * should use showConfirmAsync.
     */
    showConfirm(message) {
        // Legacy callers expect a synchronous boolean. If `confirm` is unavailable
        // (Electron sandbox), fall through to the async modal but return true so
        // execution continues; new code paths should migrate to showConfirmAsync.
        try {
            if (typeof window.confirm === 'function') {
                return window.confirm(message);
            }
        } catch (_) { /* sandboxed */ }
        // No way to block — surface modal and assume confirmation.
        UIUtils._showModal({ message, kind: 'confirm-info' }).catch(() => {});
        return true;
    }

    /**
     * Async confirm — Electron-safe. Resolves true/false.
     */
    showConfirmAsync(message, opts = {}) {
        return UIUtils._showModal({ message, kind: 'confirm', ...opts });
    }

    /**
     * Async prompt — Electron-safe replacement for window.prompt().
     * Resolves with the entered string, or null on cancel.
     */
    showPromptAsync(message, defaultValue = '', opts = {}) {
        return UIUtils._showModal({
            message, kind: 'prompt', defaultValue, ...opts
        });
    }

    /** Internal: render an inline modal and return a Promise. */
    static _showModal({ message, kind, type = 'info', defaultValue = '',
                       okText = 'OK', cancelText = 'Cancel', danger = false }) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'app-modal__overlay';
            overlay.setAttribute('role', 'dialog');
            overlay.setAttribute('aria-modal', 'true');

            const isPrompt = kind === 'prompt';
            const isConfirm = kind === 'confirm' || kind === 'confirm-info';
            const isAlert = kind === 'alert';

            const safeMsg = String(message ?? '')
                .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');

            overlay.innerHTML = `
                <div class="app-modal__panel app-modal__panel--${type}" role="document">
                    <div class="app-modal__body">${safeMsg.replace(/\n/g, '<br>')}</div>
                    ${isPrompt ? `<input type="text" class="app-modal__input" id="appModalInput" />` : ''}
                    <div class="app-modal__actions">
                        ${(isConfirm || isPrompt) ? `<button type="button" class="btn btn--ghost" data-action="cancel">${cancelText}</button>` : ''}
                        <button type="button" class="btn ${danger ? 'btn--danger' : 'btn--primary'}" data-action="ok">${okText}</button>
                    </div>
                </div>
            `;
            document.body.appendChild(overlay);

            const input = overlay.querySelector('#appModalInput');
            if (input) { input.value = defaultValue || ''; setTimeout(() => input.focus(), 30); }

            const cleanup = (val) => {
                document.removeEventListener('keydown', onKey, true);
                overlay.remove();
                resolve(val);
            };
            const onKey = (e) => {
                if (e.key === 'Escape') {
                    e.stopPropagation();
                    cleanup(isPrompt ? null : false);
                } else if (e.key === 'Enter' && (isPrompt || isConfirm || isAlert)) {
                    if (e.target.tagName === 'TEXTAREA') return;
                    e.preventDefault();
                    cleanup(isPrompt ? (input?.value ?? '') : true);
                }
            };
            document.addEventListener('keydown', onKey, true);
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay && !isAlert) cleanup(isPrompt ? null : false);
                const action = e.target.closest('[data-action]')?.dataset?.action;
                if (action === 'ok') cleanup(isPrompt ? (input?.value ?? '') : true);
                else if (action === 'cancel') cleanup(isPrompt ? null : false);
            });
        });
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

    /**
     * Show a brief toast notification.
     * @param {string} msg - Message text
     * @param {string} [type='info'] - 'info' | 'success' | 'error' | 'warning'
     * @param {number} [duration=3000] - Visible duration in ms
     */
    showToast(msg, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = msg;
        document.body.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = '0';
            toast.style.transition = 'opacity 0.3s';
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}
