/**
 * Split View Manager — side-by-side chat viewer with drag-to-import
 */

export class SplitViewManager {
    constructor(chatManager, uiUtils) {
        this.chatManager = chatManager;
        this.uiUtils = uiUtils;
        this.isActive = false;
        this.rightChatId = null;
        this.mainEl = document.querySelector('.main');
        this.chatArea = document.getElementById('chatArea');
        this._initEdgeDropZones();
    }

    toggle() {
        this.isActive ? this.close() : this.open();
    }

    open() {
        if (this.isActive) return;
        this.isActive = true;

        const btn = document.getElementById('splitViewBtn');
        if (btn) btn.classList.add('active');

        // Build split wrapper that replaces chatArea
        this.splitEl = document.createElement('div');
        this.splitEl.className = 'split-wrapper';

        // Remember chatArea's position before moving it
        this._chatAreaNextSibling = this.chatArea.nextSibling;

        // Left pane = current chat (keep original chatArea inside)
        this.leftPane = this._buildPane('left');
        this.leftPane.querySelector('.split-pane__body').appendChild(this.chatArea);
        this.chatArea.style.display = '';

        // Divider
        this.divider = document.createElement('div');
        this.divider.className = 'split-divider';
        this.divider.innerHTML = '<span class="split-divider__grip">⋮</span>';
        this._initResize();

        // Right pane = picker
        this.rightPane = this._buildPane('right');
        this._showPicker();

        this.splitEl.append(this.leftPane, this.divider, this.rightPane);
        
        // Insert split wrapper where chatArea was
        this.mainEl.insertBefore(this.splitEl, this._chatAreaNextSibling);
        this.mainEl.classList.add('split-active');

        // Setup sidebar drag-into-split
        this._initSidebarDrop();

        if (window.lucide) lucide.createIcons({ nodes: [this.splitEl] });
    }

    close() {
        if (!this.isActive) return;
        this.isActive = false;
        this.rightChatId = null;

        const btn = document.getElementById('splitViewBtn');
        if (btn) btn.classList.remove('active');

        // Move chatArea back to its original position
        this.mainEl.insertBefore(this.chatArea, this.splitEl);
        this.chatArea.style.display = '';

        this.splitEl.remove();
        this.splitEl = null;
        this._chatAreaNextSibling = null;
        this.mainEl.classList.remove('split-active');
    }

    /* ── Pane builders ─────────────────────────────── */

    _buildPane(side) {
        const pane = document.createElement('div');
        pane.className = `split-pane split-pane--${side}`;
        pane.innerHTML = `
            <div class="split-pane__header">
                <span class="split-pane__title">${side === 'left' ? this._currentTitle() : 'Chọn cuộc trò chuyện'}</span>
                ${side === 'right' ? '<button class="split-pane__close" title="Đóng"><i data-lucide="x" style="width:14px;height:14px;"></i></button>' : ''}
            </div>
            <div class="split-pane__body"></div>
        `;
        if (side === 'right') {
            pane.querySelector('.split-pane__close').addEventListener('click', () => this.close());
        }
        // Allow drop from sidebar
        pane.addEventListener('dragover', e => { e.preventDefault(); e.dataTransfer.dropEffect = 'move'; pane.classList.add('split-pane--drop-target'); });
        pane.addEventListener('dragleave', () => pane.classList.remove('split-pane--drop-target'));
        pane.addEventListener('drop', e => {
            e.preventDefault();
            pane.classList.remove('split-pane--drop-target');
            const chatId = e.dataTransfer.getData('text/plain');
            if (!chatId || !this.chatManager.chatSessions[chatId]) return;

            if (side === 'left') {
                // Switch the main chat to the dropped chat
                if (this.chatManager.switchChat) {
                    this.chatManager.switchChat(chatId);
                }
                const title = pane.querySelector('.split-pane__title');
                const s = this.chatManager.chatSessions[chatId];
                if (title && s) title.textContent = s.title;
            } else {
                this._loadChat(pane, chatId);
            }
        });
        return pane;
    }

    _currentTitle() {
        const s = this.chatManager.chatSessions[this.chatManager.currentChatId];
        return this._esc(s ? s.title : 'Chat');
    }

    /* ── Chat picker (right pane default) ──────────── */

    _showPicker() {
        const body = this.rightPane.querySelector('.split-pane__body');
        const sessions = this.chatManager.chatSessions;
        const currentId = this.chatManager.currentChatId;
        const ids = Object.keys(sessions).filter(id => id !== currentId);

        if (ids.length === 0) {
            body.innerHTML = `<div class="split-empty">
                <i data-lucide="message-circle" style="width:32px;height:32px;opacity:0.3;"></i>
                <p>Không có cuộc trò chuyện nào khác</p>
                <small>Tạo cuộc trò chuyện mới rồi quay lại đây</small>
            </div>`;
            return;
        }

        body.innerHTML = `
            <div class="split-picker">
                <div class="split-picker__hint">
                    <i data-lucide="mouse-pointer-click" style="width:14px;height:14px;"></i>
                    Chọn hoặc kéo thả chat từ sidebar vào đây
                </div>
                <div class="split-picker__list">
                    ${ids.map(id => {
                        const s = sessions[id];
                        const count = s.messages ? s.messages.length : 0;
                        const preview = count > 0
                            ? (s.messages[1] || s.messages[0] || '').replace(/<[^>]*>/g, '').substring(0, 60)
                            : 'Chưa có tin nhắn';
                        return `<button class="split-picker__item" data-chat-id="${id}">
                            <div class="split-picker__item-title">${this._esc(s.title)}</div>
                            <div class="split-picker__item-meta">
                                <span>${count} tin nhắn</span>
                                <span class="split-picker__item-preview">${this._esc(preview)}</span>
                            </div>
                        </button>`;
                    }).join('')}
                </div>
            </div>
        `;

        body.querySelectorAll('.split-picker__item').forEach(btn => {
            btn.addEventListener('click', () => {
                this._loadChat(this.rightPane, btn.dataset.chatId);
            });
        });
    }

    /* ── Load chat into a pane ─────────────────────── */

    _loadChat(pane, chatId) {
        const session = this.chatManager.chatSessions[chatId];
        if (!session) return;

        const isRight = pane.classList.contains('split-pane--right');
        if (isRight) this.rightChatId = chatId;

        // Update header
        const title = pane.querySelector('.split-pane__title');
        if (title) title.textContent = session.title;

        // Render messages
        const body = pane.querySelector('.split-pane__body');
        body.innerHTML = '';

        const messagesEl = document.createElement('div');
        messagesEl.className = 'split-pane__messages';

        if (session.messages && session.messages.length > 0) {
            messagesEl.innerHTML = session.messages.join('');
        } else {
            messagesEl.innerHTML = '<div class="split-empty"><p>Chưa có tin nhắn</p></div>';
        }

        body.appendChild(messagesEl);
        body.scrollTop = body.scrollHeight;

        if (window.lucide) lucide.createIcons({ nodes: [body] });
    }

    /* ── Edge drop zones (drag chat to corners to split) ── */

    _initEdgeDropZones() {
        // Create overlay with left/right drop zones (hidden until drag starts)
        this._overlay = document.createElement('div');
        this._overlay.className = 'split-edge-overlay';
        this._overlay.innerHTML = `
            <div class="split-edge-zone split-edge-zone--left" data-side="left">
                <i data-lucide="panel-left" style="width:28px;height:28px;"></i>
                <span>Mở bên trái</span>
            </div>
            <div class="split-edge-zone split-edge-zone--right" data-side="right">
                <i data-lucide="panel-right" style="width:28px;height:28px;"></i>
                <span>Mở bên phải</span>
            </div>
        `;
        this.mainEl.appendChild(this._overlay);
        if (window.lucide) lucide.createIcons({ nodes: [this._overlay] });

        // Watch for drag events on the whole document
        document.addEventListener('dragstart', (e) => {
            const item = e.target.closest?.('.sidebar__chat-item');
            if (!item || this.isActive) return;
            // Show overlay after a short delay
            setTimeout(() => {
                this._overlay.classList.add('visible');
            }, 200);
        });

        document.addEventListener('dragend', () => {
            this._overlay.classList.remove('visible');
            this._overlay.querySelectorAll('.split-edge-zone').forEach(z => z.classList.remove('active'));
        });

        // Zone hover & drop
        this._overlay.querySelectorAll('.split-edge-zone').forEach(zone => {
            let zoneCounter = 0;
            zone.addEventListener('dragenter', (e) => {
                e.preventDefault();
                zoneCounter++;
                zone.classList.add('active');
            });
            zone.addEventListener('dragleave', () => {
                zoneCounter--;
                if (zoneCounter <= 0) {
                    zoneCounter = 0;
                    zone.classList.remove('active');
                }
            });
            zone.addEventListener('dragover', (e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
            });
            zone.addEventListener('drop', (e) => {
                e.preventDefault();
                this._overlay.classList.remove('visible');
                zone.classList.remove('active');

                const chatId = e.dataTransfer.getData('text/plain');
                if (!chatId || !this.chatManager.chatSessions[chatId]) return;

                const side = zone.dataset.side;
                this._openWithChat(chatId, side);
            });
        });
    }

    /**
     * Open split view and load a specific chat into the given side
     */
    _openWithChat(chatId, side) {
        if (this.isActive) return;

        // Open split first
        this.open();

        if (side === 'right') {
            // Load dropped chat into right pane
            this._loadChat(this.rightPane, chatId);
        } else {
            // Switch main chat to the dropped chat, show current chat in right
            const currentId = this.chatManager.currentChatId;
            if (this.chatManager.switchChat) {
                this.chatManager.switchChat(chatId);
            }
            const title = this.leftPane.querySelector('.split-pane__title');
            const s = this.chatManager.chatSessions[chatId];
            if (title && s) title.textContent = s.title;
            // Load old current chat into right pane
            if (currentId && currentId !== chatId) {
                this._loadChat(this.rightPane, currentId);
            }
        }
    }

    /* ── Sidebar drag-to-split ─────────────────────── */

    _initSidebarDrop() {
        // The sidebar items already have draggable + dragstart from ui-utils.
        // Drop targets on panes are set up in _buildPane.
    }

    /* ── Divider resize ────────────────────────────── */

    _initResize() {
        let active = false;
        const onMove = (e) => {
            if (!active) return;
            const x = e.touches ? e.touches[0].clientX : e.clientX;
            const rect = this.splitEl.getBoundingClientRect();
            const pct = ((x - rect.left) / rect.width) * 100;
            if (pct > 25 && pct < 75) {
                this.leftPane.style.flex = `0 0 ${pct}%`;
                this.rightPane.style.flex = `0 0 ${100 - pct - 0.3}%`;
            }
        };
        const onEnd = () => {
            active = false;
            this.divider.classList.remove('active');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            document.removeEventListener('mousemove', onMove);
            document.removeEventListener('touchmove', onMove);
            document.removeEventListener('mouseup', onEnd);
            document.removeEventListener('touchend', onEnd);
        };
        const onStart = (e) => {
            e.preventDefault();
            active = true;
            this.divider.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            document.addEventListener('mousemove', onMove);
            document.addEventListener('touchmove', onMove);
            document.addEventListener('mouseup', onEnd);
            document.addEventListener('touchend', onEnd);
        };
        this.divider.addEventListener('mousedown', onStart);
        this.divider.addEventListener('touchstart', onStart, { passive: false });
    }

    _esc(text) {
        const d = document.createElement('div');
        d.textContent = text || '';
        return d.innerHTML;
    }
}
