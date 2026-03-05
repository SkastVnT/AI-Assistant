/**
 * Split View Manager
 * Allows viewing multiple chat conversations side-by-side
 */

export class SplitViewManager {
    constructor(chatManager, uiUtils) {
        this.chatManager = chatManager;
        this.uiUtils = uiUtils;
        this.isActive = false;
        this.panes = []; // [{chatId, container, element}]
        this.mainEl = document.querySelector('.main');
        this.chatArea = document.getElementById('chatArea');
        this.originalChatContainer = document.getElementById('chatContainer');
    }

    /**
     * Toggle split view on/off
     */
    toggle() {
        if (this.isActive) {
            this.closeSplit();
        } else {
            this.openSplit();
        }
    }

    /**
     * Open split view — current chat stays left, picker opens for right pane
     */
    openSplit() {
        if (this.isActive) return;
        this.isActive = true;

        const btn = document.getElementById('splitViewBtn');
        if (btn) btn.classList.add('active');

        // Wrap existing chat area into left pane
        this.mainEl.classList.add('split-view');

        // Create split container
        this.splitContainer = document.createElement('div');
        this.splitContainer.className = 'split-container';
        this.splitContainer.style.cssText = 'display:flex;flex:1;overflow:hidden;';

        // Left pane (current chat)
        const leftPane = this._createPane(this.chatManager.currentChatId, false);
        
        // Move existing chatArea content into left pane
        const leftChatArea = leftPane.querySelector('.split-pane__chat');
        leftChatArea.innerHTML = this.chatArea.innerHTML;

        // Divider
        const divider = document.createElement('div');
        divider.className = 'split-divider';
        this._setupDividerResize(divider);

        // Right pane (empty — show chat picker)
        const rightPane = this._createEmptyPane();

        this.splitContainer.appendChild(leftPane);
        this.splitContainer.appendChild(divider);
        this.splitContainer.appendChild(rightPane);

        // Hide original chat area content and insert split container
        this.chatArea.style.display = 'none';
        this.chatArea.parentNode.insertBefore(this.splitContainer, this.chatArea.nextSibling);

        this.panes = [
            { chatId: this.chatManager.currentChatId, element: leftPane },
        ];

        // Re-init Lucide icons
        if (window.lucide) lucide.createIcons({ nodes: [this.splitContainer] });
    }

    /**
     * Close split view — restore single pane
     */
    closeSplit() {
        if (!this.isActive) return;
        this.isActive = false;

        const btn = document.getElementById('splitViewBtn');
        if (btn) btn.classList.remove('active');

        this.mainEl.classList.remove('split-view');

        // Remove split container
        if (this.splitContainer && this.splitContainer.parentNode) {
            this.splitContainer.parentNode.removeChild(this.splitContainer);
        }

        // Show original chat area again
        this.chatArea.style.display = '';

        this.panes = [];
        this.splitContainer = null;
    }

    /**
     * Create a pane element for a specific chat
     */
    _createPane(chatId, showClose = true) {
        const session = this.chatManager.chatSessions[chatId];
        const title = session ? session.title : 'Chat';

        const pane = document.createElement('div');
        pane.className = 'split-pane';
        pane.dataset.chatId = chatId;

        pane.innerHTML = `
            <div class="split-pane__header">
                <span class="split-pane__header-title">${this._escapeHtml(title)}</span>
                ${showClose ? '<button class="split-pane__close" title="Close pane"><i data-lucide="x" style="width:14px;height:14px;"></i></button>' : ''}
            </div>
            <div class="split-pane__chat chat-area" style="flex:1;overflow-y:auto;">
                <div class="chat-area__messages" style="max-width:100%;padding:16px;"></div>
            </div>
        `;

        // Load messages into this pane
        const messagesContainer = pane.querySelector('.chat-area__messages');
        if (session && session.messages.length > 0) {
            messagesContainer.innerHTML = session.messages.join('');
        } else {
            messagesContainer.innerHTML = '<div style="text-align:center;color:var(--text-tertiary);padding:40px;">No messages yet</div>';
        }

        // Close button handler
        if (showClose) {
            const closeBtn = pane.querySelector('.split-pane__close');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => this.closeSplit());
            }
        }

        return pane;
    }

    /**
     * Create empty pane with chat picker
     */
    _createEmptyPane() {
        const pane = document.createElement('div');
        pane.className = 'split-pane';
        pane.dataset.chatId = '';

        const sessions = this.chatManager.chatSessions;
        const currentId = this.chatManager.currentChatId;
        const chatOptions = Object.keys(sessions)
            .filter(id => id !== currentId)
            .map(id => {
                const s = sessions[id];
                return `<button class="split-chat-pick" data-chat-id="${id}" style="
                    display:block;width:100%;text-align:left;padding:10px 14px;
                    background:var(--bg-secondary);border:1px solid var(--border-secondary);
                    border-radius:var(--radius-sm);cursor:pointer;margin-bottom:6px;
                    color:var(--text-primary);font-size:13px;transition:all 0.15s;">
                    <strong>${this._escapeHtml(s.title)}</strong>
                    <div style="font-size:11px;color:var(--text-tertiary);margin-top:2px;">${s.messages.length} messages</div>
                </button>`;
            }).join('');

        pane.innerHTML = `
            <div class="split-pane__header">
                <span class="split-pane__header-title">Select a conversation</span>
                <button class="split-pane__close" title="Close split"><i data-lucide="x" style="width:14px;height:14px;"></i></button>
            </div>
            <div style="flex:1;overflow-y:auto;padding:16px;">
                ${chatOptions || '<div style="color:var(--text-tertiary);text-align:center;padding:40px;">No other conversations available</div>'}
            </div>
        `;

        // Pick handler
        pane.querySelectorAll('.split-chat-pick').forEach(btn => {
            btn.addEventListener('click', () => {
                const chatId = btn.dataset.chatId;
                this._loadChatIntoPane(pane, chatId);
            });
            btn.addEventListener('mouseenter', () => {
                btn.style.borderColor = 'var(--accent)';
                btn.style.background = 'var(--accent-soft)';
            });
            btn.addEventListener('mouseleave', () => {
                btn.style.borderColor = 'var(--border-secondary)';
                btn.style.background = 'var(--bg-secondary)';
            });
        });

        // Close button
        const closeBtn = pane.querySelector('.split-pane__close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.closeSplit());
        }

        return pane;
    }

    /**
     * Load a specific chat into a pane
     */
    _loadChatIntoPane(pane, chatId) {
        const session = this.chatManager.chatSessions[chatId];
        if (!session) return;

        pane.dataset.chatId = chatId;
        
        // Update header
        const headerTitle = pane.querySelector('.split-pane__header-title');
        if (headerTitle) headerTitle.textContent = session.title;

        // Replace body with chat content
        const existingBody = pane.querySelector('.split-pane__chat') || pane.children[1];
        const chatArea = document.createElement('div');
        chatArea.className = 'split-pane__chat chat-area';
        chatArea.style.cssText = 'flex:1;overflow-y:auto;';
        chatArea.innerHTML = `<div class="chat-area__messages" style="max-width:100%;padding:16px;">${session.messages.join('')}</div>`;

        if (existingBody) {
            pane.replaceChild(chatArea, existingBody);
        } else {
            pane.appendChild(chatArea);
        }

        this.panes.push({ chatId, element: pane });
        
        if (window.lucide) lucide.createIcons({ nodes: [pane] });
    }

    /**
     * Setup divider resize
     */
    _setupDividerResize(divider) {
        let isResizing = false;
        let startX = 0;

        divider.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            divider.classList.add('active');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const container = divider.parentElement;
            const leftPane = divider.previousElementSibling;
            const rightPane = divider.nextElementSibling;
            
            if (!leftPane || !rightPane || !container) return;
            
            const containerRect = container.getBoundingClientRect();
            const leftWidth = ((e.clientX - containerRect.left) / containerRect.width) * 100;
            
            if (leftWidth > 20 && leftWidth < 80) {
                leftPane.style.flex = `0 0 ${leftWidth}%`;
                rightPane.style.flex = `0 0 ${100 - leftWidth - 1}%`;
            }
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                divider.classList.remove('active');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
}
