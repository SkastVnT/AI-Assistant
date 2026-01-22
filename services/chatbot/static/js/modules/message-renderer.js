/**
 * Message Renderer Module
 * Handles message rendering, markdown parsing, code highlighting
 */

export class MessageRenderer {
    constructor() {
        this.modelNames = {
            'gemini': 'Gemini',
            'grok': 'GROK',
            'openai': 'GPT-4o-mini',
            'deepseek': 'DeepSeek',
            'deepseek-reasoner': '🧠 DeepSeek R1 (Reasoning)',
            'qwen': 'Qwen1.5b',
            'bloomvn': 'BloomVN-8B API',
            'bloomvn-local': 'BloomVN-8B Local',
            'qwen1.5-local': 'Qwen1.5 Local',
            'qwen2.5-local': 'Qwen2.5-14B Local'
        };
        
        this.contextNames = {
            'casual': 'Trò chuyện vui vẻ',
            'psychological': 'Tâm lý - Tâm sự',
            'lifestyle': 'Giải pháp đời sống',
            'programming': '💻 Hỗ trợ lập trình'
        };

        this.messageHistory = new Map(); // Store message edit history
        this.initMarked();
    }

    /**
     * Initialize marked.js configuration
     */
    initMarked() {
        if (typeof marked !== 'undefined') {
            marked.setOptions({
                breaks: true,
                gfm: true,
                highlight: function(code, lang) {
                    if (typeof hljs !== 'undefined') {
                        if (lang && hljs.getLanguage(lang)) {
                            return hljs.highlight(code, { language: lang }).value;
                        }
                        return hljs.highlightAuto(code).value;
                    }
                    return code;
                }
            });
        }
    }

    /**
     * Create and add message to chat
     */
    addMessage(chatContainer, content, isUser, model, context, timestamp, thinkingProcess = null, customPromptUsed = false, agentConfig = null) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
        messageDiv.dataset.timestamp = timestamp;
        messageDiv.dataset.model = model || '';
        messageDiv.dataset.context = context || '';
        
        // Assign unique message ID for user messages (for history tracking)
        if (isUser) {
            messageDiv.dataset.messageId = `msg_${Date.now()}_${Math.random()}`;
        }
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        // Add thinking process if provided (for assistant with deep thinking)
        if (!isUser && thinkingProcess) {
            const thinkingDiv = this.createThinkingSection(thinkingProcess);
            contentDiv.appendChild(thinkingDiv);
        }
        
        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';
        
        if (isUser) {
            textDiv.textContent = content;
        } else {
            // Parse markdown for assistant messages
            if (typeof marked !== 'undefined') {
                textDiv.innerHTML = marked.parse(content);
                
                // Highlight code blocks
                if (typeof hljs !== 'undefined') {
                    textDiv.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(block);
                    });
                }
                
                // Add copy button for tables
                textDiv.querySelectorAll('table').forEach((table) => {
                    const copyBtn = document.createElement('button');
                    copyBtn.className = 'copy-table-btn';
                    copyBtn.textContent = '📋 Copy bảng';
                    copyBtn.onclick = () => this.copyTableToClipboard(table, copyBtn);
                    table.parentNode.insertBefore(copyBtn, table.nextSibling);
                });
            } else {
                textDiv.textContent = content;
            }
        }
        
        contentDiv.appendChild(textDiv);
        
        // Add model/context info for assistant
        if (!isUser && model && context) {
            const infoDiv = document.createElement('div');
            infoDiv.className = 'message-info';
            
            // Determine prompt/config type indicator
            let configIndicator = '📝 Base Prompt';
            let configDetails = '';
            
            if (agentConfig && agentConfig.enabled) {
                const thinkingMode = agentConfig.thinkingBudget || 'off';
                const temp = agentConfig.temperature || 0.7;
                
                if (thinkingMode === 'advanced') {
                    configIndicator = '🚀 Config Agent (Advanced)';
                    configDetails = ` • T:${temp}`;
                } else if (thinkingMode === 'on') {
                    configIndicator = '⚡ Config Agent (Thinking)';
                    configDetails = ` • T:${temp}`;
                } else {
                    configIndicator = '⚡ Config Agent';
                    configDetails = ` • T:${temp}`;
                }
            } else if (customPromptUsed) {
                configIndicator = '🛠️ Custom Prompt';
            }
            
            infoDiv.textContent = `${this.modelNames[model] || model} • ${this.contextNames[context] || context} • ${configIndicator}${configDetails}`;
            contentDiv.appendChild(infoDiv);
        }
        
        // Add timestamp with version counter for assistant messages
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        
        if (!isUser) {
            // Add version counter badge
            const versionBadge = document.createElement('span');
            versionBadge.className = 'message-version-badge';
            versionBadge.textContent = '1/1';
            timestampDiv.appendChild(versionBadge);
            
            const separator = document.createElement('span');
            separator.textContent = ' • ';
            timestampDiv.appendChild(separator);
        }
        
        const timeSpan = document.createElement('span');
        timeSpan.textContent = timestamp;
        timestampDiv.appendChild(timeSpan);
        
        contentDiv.appendChild(timestampDiv);
        
        // Add action buttons
        this.addMessageButtons(contentDiv, content, isUser, messageDiv);
        
        messageDiv.appendChild(contentDiv);
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return messageDiv;
    }

    /**
     * Add file attachment message to chat
     */
    addFileMessage(chatContainer, files, timestamp) {
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message file-message user';
        messageDiv.dataset.timestamp = timestamp;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        
        const headerDiv = document.createElement('div');
        headerDiv.className = 'file-message-header';
        headerDiv.innerHTML = `📎 <strong>Đã tải lên ${files.length} file${files.length > 1 ? 's' : ''}</strong>`;
        contentDiv.appendChild(headerDiv);
        
        // Create file cards grid
        const filesGrid = document.createElement('div');
        filesGrid.className = 'file-message-grid';
        
        files.forEach((file, index) => {
            const fileCard = document.createElement('div');
            fileCard.className = 'file-message-card';
            
            // Icon or preview
            if (file.preview) {
                fileCard.innerHTML = `
                    <div class="file-message-preview">
                        <img src="${file.preview}" alt="${this.escapeHtml(file.name)}">
                    </div>
                `;
            } else {
                const icon = this.getFileIcon(file.type, file.name);
                fileCard.innerHTML = `
                    <div class="file-message-icon">${icon}</div>
                `;
            }
            
            // File info
            const infoDiv = document.createElement('div');
            infoDiv.className = 'file-message-info';
            infoDiv.innerHTML = `
                <div class="file-message-name" title="${this.escapeHtml(file.name)}">${this.escapeHtml(file.name)}</div>
                <div class="file-message-meta">${this.formatFileSize(file.size)}</div>
            `;
            fileCard.appendChild(infoDiv);
            
            filesGrid.appendChild(fileCard);
        });
        
        contentDiv.appendChild(filesGrid);
        
        // Add timestamp
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        timestampDiv.textContent = timestamp;
        contentDiv.appendChild(timestampDiv);
        
        messageDiv.appendChild(contentDiv);
        chatContainer.appendChild(messageDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        return messageDiv;
    }

    /**
     * Get file icon emoji
     */
    getFileIcon(type, name) {
        if (type.startsWith('image/')) return '🖼️';
        if (type.startsWith('video/')) return '🎥';
        if (type.startsWith('audio/')) return '🎵';
        if (type === 'application/pdf') return '📕';
        if (type === 'application/msword' || type.includes('wordprocessing')) return '📘';
        if (type.includes('spreadsheet') || name.endsWith('.xlsx')) return '📊';
        if (type === 'application/json') return '📋';
        if (name.endsWith('.py')) return '🐍';
        if (name.endsWith('.js')) return '📜';
        if (name.endsWith('.html')) return '🌐';
        if (name.endsWith('.css')) return '🎨';
        if (type.startsWith('text/')) return '📄';
        return '📎';
    }

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    /**
     * Create thinking process section (collapsible)
     */
    createThinkingSection(thinkingProcess, isLoading = false) {
        const container = document.createElement('div');
        container.className = 'thinking-container';
        if (isLoading) {
            container.dataset.loading = 'true';
        }
        
        const header = document.createElement('div');
        header.className = 'thinking-header';
        
        const icon = document.createElement('span');
        icon.className = 'thinking-icon';
        icon.textContent = isLoading ? '⏳' : '🧠';
        
        const title = document.createElement('span');
        title.className = 'thinking-title';
        title.textContent = isLoading ? 'Thinking...' : 'Thought Process';
        
        const badge = document.createElement('span');
        badge.className = 'thinking-badge';
        badge.textContent = isLoading ? 'Analyzing' : 'Complete';
        badge.style.cssText = `
            font-size: 10px;
            padding: 2px 8px;
            border-radius: 10px;
            background: ${isLoading ? 'rgba(102, 126, 234, 0.2)' : 'rgba(16, 185, 129, 0.2)'};
            color: ${isLoading ? '#667eea' : '#10b981'};
            font-weight: 600;
            margin-left: 8px;
        `;
        
        const toggle = document.createElement('span');
        toggle.className = 'thinking-toggle';
        toggle.textContent = '▼';
        
        header.appendChild(icon);
        header.appendChild(title);
        header.appendChild(badge);
        header.appendChild(toggle);
        
        const content = document.createElement('div');
        content.className = 'thinking-content';
        
        if (isLoading) {
            content.innerHTML = `
                <div style="display: flex; align-items: center; gap: 10px; color: #667eea;">
                    <span style="animation: pulse 1.5s infinite;">🔍</span>
                    <span>Analyzing the problem and generating response...</span>
                </div>
                <div style="margin-top: 8px; font-size: 12px; color: #888;">
                    The AI is thinking deeply about your request. This may take a moment for complex queries.
                </div>
            `;
        } else if (thinkingProcess) {
            // Parse thinking process
            if (typeof thinkingProcess === 'string') {
                content.textContent = thinkingProcess;
            } else {
                content.textContent = JSON.stringify(thinkingProcess, null, 2);
            }
        }
        
        // Toggle functionality
        header.addEventListener('click', () => {
            header.classList.toggle('collapsed');
            content.classList.toggle('collapsed');
        });
        
        container.appendChild(header);
        container.appendChild(content);
        
        return container;
    }
    
    /**
     * Update thinking process content
     */
    updateThinkingContent(container, thinkingProcess) {
        const content = container.querySelector('.thinking-content');
        const header = container.querySelector('.thinking-header');
        const title = header.querySelector('.thinking-title');
        const icon = header.querySelector('.thinking-icon');
        const badge = header.querySelector('.thinking-badge');
        
        if (content && title) {
            // Update icon and title
            if (icon) icon.textContent = '🧠';
            title.textContent = 'Thought Process';
            
            // Update badge
            if (badge) {
                badge.textContent = 'Complete';
                badge.style.background = 'rgba(16, 185, 129, 0.2)';
                badge.style.color = '#10b981';
            }
            
            // Update content
            if (typeof thinkingProcess === 'string') {
                // Format thinking process nicely
                const formatted = thinkingProcess
                    .split('\n')
                    .map(line => {
                        if (line.trim().startsWith('Step') || line.trim().startsWith('Analysis')) {
                            return `<strong style="color: #667eea;">${line}</strong>`;
                        }
                        return line;
                    })
                    .join('\n');
                content.innerHTML = `<pre style="white-space: pre-wrap; margin: 0; font-family: inherit;">${thinkingProcess}</pre>`;
            } else {
                content.textContent = JSON.stringify(thinkingProcess, null, 2);
            }
            
            // Remove loading state
            container.removeAttribute('data-loading');
            container.style.animation = 'none';
        }
    }

    /**
     * Add action buttons to message
     */
    addMessageButtons(contentDiv, content, isUser, messageDiv) {
        const actionsDiv = document.createElement('div');
        actionsDiv.className = 'message-actions';
        
        if (!isUser) {
            // Copy button
            const copyBtn = this.createActionButton('copy-btn', '📋', 'Copy');
            copyBtn.onclick = () => this.copyMessageToClipboard(content, copyBtn);
            actionsDiv.appendChild(copyBtn);
            
            // Like button
            const likeBtn = this.createActionButton('like-btn', '👍', 'Good response');
            likeBtn.onclick = () => this.toggleFeedback(likeBtn, 'like', messageDiv);
            actionsDiv.appendChild(likeBtn);
            
            // Dislike button
            const dislikeBtn = this.createActionButton('dislike-btn', '👎', 'Bad response');
            dislikeBtn.onclick = () => this.toggleFeedback(dislikeBtn, 'dislike', messageDiv);
            actionsDiv.appendChild(dislikeBtn);
            
            // Regenerate button
            const regenBtn = this.createActionButton('regenerate-btn', '🔄', 'Regenerate');
            regenBtn.onclick = () => this.regenerateResponse(messageDiv);
            actionsDiv.appendChild(regenBtn);
            
            // More options button
            const moreBtn = this.createActionButton('more-btn', '⋯', 'More');
            moreBtn.onclick = () => this.showMoreOptions(messageDiv, moreBtn);
            actionsDiv.appendChild(moreBtn);
        } else {
            // Edit button for user messages
            const editBtn = this.createActionButton('edit-btn', '✏️', 'Edit');
            editBtn.onclick = () => this.showEditForm(messageDiv, content);
            actionsDiv.appendChild(editBtn);
            
            // More options button
            const moreBtn = this.createActionButton('more-btn', '⋯', 'More');
            moreBtn.onclick = () => this.showMoreOptions(messageDiv, moreBtn);
            actionsDiv.appendChild(moreBtn);
        }
        
        contentDiv.appendChild(actionsDiv);
    }

    /**
     * Create action button
     */
    createActionButton(className, icon, title) {
        const button = document.createElement('button');
        button.className = `message-action-btn ${className}`;
        button.innerHTML = icon;
        button.title = title;
        return button;
    }
    
    /**
     * Toggle feedback (like/dislike)
     */
    toggleFeedback(button, type, messageDiv) {
        const actionsDiv = button.parentElement;
        const likeBtn = actionsDiv.querySelector('.like-btn');
        const dislikeBtn = actionsDiv.querySelector('.dislike-btn');
        
        if (button.classList.contains('active')) {
            button.classList.remove('active');
            delete messageDiv.dataset.feedback;
        } else {
            likeBtn.classList.remove('active');
            dislikeBtn.classList.remove('active');
            button.classList.add('active');
            messageDiv.dataset.feedback = type;
        }
    }
    
    /**
     * Regenerate response
     */
    regenerateResponse(messageDiv) {
        // Find the user message before this assistant message
        let prevMessage = messageDiv.previousElementSibling;
        while (prevMessage && !prevMessage.classList.contains('user')) {
            prevMessage = prevMessage.previousElementSibling;
        }
        
        if (!prevMessage || !window.chatApp) return;
        
        const userText = prevMessage.querySelector('.message-text')?.textContent;
        if (!userText) return;
        
        // Store current response as version
        const currentResponse = messageDiv.querySelector('.message-text')?.innerHTML;
        const messageId = prevMessage.dataset.messageId || `msg_${Date.now()}_${Math.random()}`;
        prevMessage.dataset.messageId = messageId;
        
        // Save current version before regenerating (user message + current response)
        if (!this.messageHistory.has(messageId)) {
            this.messageHistory.set(messageId, []);
            // Save initial version
            this.addMessageVersion(messageId, userText, currentResponse, new Date().toISOString());
            if (window.chatManager) {
                window.chatManager.saveMessageVersion(messageId, userText, currentResponse, new Date().toISOString());
            }
        }
        
        // Add new empty version that will be filled when response arrives
        this.addMessageVersion(messageId, userText, '', new Date().toISOString());
        if (window.chatManager) {
            window.chatManager.saveMessageVersion(messageId, userText, '', new Date().toISOString());
        }
        
        // Update version indicator
        const history = this.getMessageHistory(messageId);
        prevMessage.dataset.currentVersion = (history.length - 1).toString();
        this.updateVersionIndicator(prevMessage);
        
        // Remove current assistant message
        messageDiv.remove();
        
        // Show loading indicator
        const chatContainer = prevMessage.parentElement;
        if (window.chatApp && window.chatApp.uiUtils) {
            window.chatApp.uiUtils.showLoading();
        }
        
        // Get current form values
        const formValues = window.chatApp.uiUtils.getFormValues();
        
        // Build conversation history
        const history_context = window.chatApp.buildConversationHistory();
        
        // Get selected memories
        const selectedMemories = window.chatApp.memoryManager.getSelectedMemories();
        
        // Create new AbortController
        window.chatApp.currentAbortController = new AbortController();
        
        // Send API request
        window.chatApp.apiService.sendMessage(
            userText,
            formValues.model,
            formValues.context,
            Array.from(window.chatApp.activeTools),
            formValues.deepThinking,
            history_context,
            [],
            selectedMemories,
            window.chatApp.currentAbortController.signal
        ).then(data => {
            // Hide loading
            window.chatApp.uiUtils.hideLoading();
            
            // Add response
            const responseTimestamp = window.chatApp.uiUtils.formatTimestamp(new Date());
            const responseContent = data.error ? `❌ **Lỗi:** ${data.error}` : data.response;
            
            window.chatApp.messageRenderer.addMessage(
                chatContainer,
                responseContent,
                false,
                formValues.model,
                formValues.context,
                responseTimestamp
            );
            
            // Update version history with the new response
            const historyVersions = this.getMessageHistory(messageId);
            if (historyVersions.length > 0) {
                historyVersions[historyVersions.length - 1].assistantResponse = responseContent;
                
                // Save to chatManager
                if (window.chatManager) {
                    const session = window.chatManager.getCurrentSession();
                    if (session && session.messageVersions && session.messageVersions[messageId]) {
                        const versions = session.messageVersions[messageId];
                        if (versions.length > 0) {
                            versions[versions.length - 1].assistantResponse = responseContent;
                            window.chatManager.saveSessions();
                        }
                    }
                }
            }
            
            // Save session
            window.chatApp.saveCurrentSession(true);
            
            // Make images clickable
            setTimeout(() => {
                window.chatApp.messageRenderer.makeImagesClickable((img) => window.chatApp.openImagePreview(img));
            }, 100);
            
        }).catch(error => {
            window.chatApp.uiUtils.hideLoading();
            
            if (error.name === 'AbortError') {
                console.log('[Regenerate] Request aborted by user');
            } else {
                console.error('[Regenerate] Error:', error);
                const errorMsg = window.chatApp.messageRenderer.addMessage(
                    chatContainer,
                    `❌ **Lỗi:** ${error.message || 'Không thể tạo lại response'}`,
                    false,
                    formValues.model,
                    formValues.context,
                    window.chatApp.uiUtils.formatTimestamp(new Date())
                );
            }
        });
    }
    
    /**
     * Show more options menu
     */
    showMoreOptions(messageDiv, button) {
        const isUser = messageDiv.classList.contains('user');
        const content = messageDiv.querySelector('.message-text')?.textContent || '';
        
        const menu = document.createElement('div');
        menu.className = 'message-options-menu';
        menu.innerHTML = `
            <button class="option-item" data-action="copy">
                <span>📋</span> Copy message
            </button>
            ${!isUser ? `
            <button class="option-item" data-action="export">
                <span>📤</span> Export to file
            </button>
            ` : ''}
            <button class="option-item" data-action="delete">
                <span>🗑️</span> Delete message
            </button>
        `;
        
        // Position menu
        const rect = button.getBoundingClientRect();
        menu.style.position = 'fixed';
        menu.style.top = `${rect.bottom + 5}px`;
        menu.style.left = `${rect.left - 100}px`;
        
        // Add event listeners
        menu.querySelectorAll('.option-item').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                this.handleMenuAction(action, messageDiv, content);
                menu.remove();
            });
        });
        
        // Close on click outside
        setTimeout(() => {
            document.addEventListener('click', function closeMenu(e) {
                if (!menu.contains(e.target)) {
                    menu.remove();
                    document.removeEventListener('click', closeMenu);
                }
            });
        }, 10);
        
        document.body.appendChild(menu);
    }
    
    /**
     * Handle menu action
     */
    handleMenuAction(action, messageDiv, content) {
        switch(action) {
            case 'copy':
                this.copyMessageToClipboard(content, null);
                break;
            case 'export':
                this.exportMessageToFile(content);
                break;
            case 'delete':
                if (confirm('Delete this message?')) {
                    messageDiv.remove();
                }
                break;
        }
    }
    
    /**
     * Export message to file
     */
    exportMessageToFile(content) {
        const blob = new Blob([content], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `message_${Date.now()}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
    
    /**
     * Copy message to clipboard
     */
    async copyMessageToClipboard(content, button) {
        const plainText = content.replace(/<[^>]*>/g, '').trim();
        
        try {
            await navigator.clipboard.writeText(plainText);
            
            if (button) {
                const originalHTML = button.innerHTML;
                button.innerHTML = '✅';
                button.classList.add('copied');
                
                setTimeout(() => {
                    button.innerHTML = originalHTML;
                    button.classList.remove('copied');
                }, 2000);
            } else {
                // Show temporary notification
                const notification = document.createElement('div');
                notification.className = 'copy-notification';
                notification.textContent = '✅ Copied to clipboard!';
                document.body.appendChild(notification);
                setTimeout(() => notification.remove(), 2000);
            }
        } catch (err) {
            console.error('Failed to copy:', err);
            alert('Không thể copy. Vui lòng thử lại!');
        }
    }

    /**
     * Copy table to clipboard
     */
    async copyTableToClipboard(table, button) {
        // Convert table to TSV (Tab-separated values) for Excel compatibility
        let tsv = '';
        const rows = table.querySelectorAll('tr');
        
        rows.forEach(row => {
            const cells = row.querySelectorAll('th, td');
            const rowData = [];
            cells.forEach(cell => {
                rowData.push(cell.textContent.trim());
            });
            tsv += rowData.join('\t') + '\n';
        });
        
        try {
            await navigator.clipboard.writeText(tsv);
            const originalText = button.textContent;
            button.textContent = '✅ Đã copy!';
            button.classList.add('copied');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copied');
            }, 2000);
        } catch (err) {
            console.error('Failed to copy:', err);
            alert('Không thể copy bảng. Vui lòng thử lại.');
        }
    }

    /**
     * Show edit form for user message
     */
    showEditForm(messageDiv, originalContent) {
        // Check if edit form already exists
        if (messageDiv.querySelector('.edit-form')) {
            return;
        }
        
        // Save current content to history before editing (if not already saved)
        const messageId = messageDiv.dataset.messageId || `msg_${Date.now()}_${Math.random()}`;
        messageDiv.dataset.messageId = messageId;
        
        // Initialize current version index
        if (!messageDiv.dataset.currentVersion) {
            messageDiv.dataset.currentVersion = '0';
        }
        
        // Get corresponding assistant response
        let assistantMsg = messageDiv.nextElementSibling;
        while (assistantMsg && !assistantMsg.classList.contains('assistant')) {
            assistantMsg = assistantMsg.nextElementSibling;
        }
        const assistantResponse = assistantMsg ? assistantMsg.querySelector('.message-text')?.innerHTML : '';
        
        // Only save to history if this is the first edit
        if (!this.messageHistory.has(messageId)) {
            this.addMessageVersion(messageId, originalContent, assistantResponse, new Date().toISOString());
            // Also save to chatManager for persistence
            if (window.chatManager) {
                window.chatManager.saveMessageVersion(messageId, originalContent, assistantResponse, new Date().toISOString());
            }
        }
        
        // Create edit form
        const editForm = document.createElement('div');
        editForm.className = 'edit-form';
        
        const textarea = document.createElement('textarea');
        textarea.value = originalContent;
        textarea.placeholder = 'Chỉnh sửa tin nhắn...';
        
        const buttonsDiv = document.createElement('div');
        buttonsDiv.className = 'edit-form-buttons';
        
        const saveBtn = document.createElement('button');
        saveBtn.className = 'edit-save-btn';
        saveBtn.textContent = '💾 Lưu & Tạo lại response';
        saveBtn.onclick = () => {
            const newContent = textarea.value.trim();
            if (newContent && newContent !== originalContent) {
                // Find and save old assistant response before removing
                let nextMsg = messageDiv.nextElementSibling;
                while (nextMsg && !nextMsg.classList.contains('assistant')) {
                    nextMsg = nextMsg.nextElementSibling;
                }
                const oldResponse = nextMsg ? nextMsg.querySelector('.message-text')?.innerHTML : '';
                
                // Save new version with empty response (will be filled after regeneration)
                this.addMessageVersion(messageId, newContent, '', new Date().toISOString());
                if (window.chatManager) {
                    window.chatManager.saveMessageVersion(messageId, newContent, '', new Date().toISOString());
                }
                
                // Update message content
                const textDiv = messageDiv.querySelector('.message-text');
                textDiv.textContent = newContent;
                
                // Update version indicator
                const history = this.getMessageHistory(messageId);
                const currentIdx = history.length - 1;
                messageDiv.dataset.currentVersion = currentIdx.toString();
                this.updateVersionIndicator(messageDiv);
                
                // Remove edit form
                editForm.remove();
                
                // Find and remove subsequent assistant message
                if (nextMsg) {
                    nextMsg.remove();
                }
                
                // Regenerate response with edited message
                if (window.chatApp && this.onEditSave) {
                    this.onEditSave(messageDiv, newContent, originalContent);
                }
            }
        };
        
        const cancelBtn = document.createElement('button');
        cancelBtn.className = 'edit-cancel-btn';
        cancelBtn.textContent = '❌ Hủy';
        cancelBtn.onclick = () => editForm.remove();
        
        buttonsDiv.appendChild(saveBtn);
        buttonsDiv.appendChild(cancelBtn);
        editForm.appendChild(textarea);
        editForm.appendChild(buttonsDiv);
        
        messageDiv.querySelector('.message-content').appendChild(editForm);
        textarea.focus();
    }

    /**
     * Add message version to history
     */
    addMessageVersion(messageId, userContent, assistantResponse, timestamp) {
        if (!this.messageHistory.has(messageId)) {
            this.messageHistory.set(messageId, []);
        }
        
        this.messageHistory.get(messageId).push({
            userContent: userContent,
            assistantResponse: assistantResponse,
            timestamp: timestamp
        });
    }
    
    /**
     * Update version indicator with navigation buttons
     */
    updateVersionIndicator(messageDiv) {
        const messageId = messageDiv.dataset.messageId;
        if (!messageId) return;
        
        const history = this.getMessageHistory(messageId);
        if (history.length <= 1) return;
        
        const currentIdx = parseInt(messageDiv.dataset.currentVersion || '0');
        const total = history.length;
        
        // Find or create version badge in timestamp
        const timestampDiv = messageDiv.querySelector('.message-timestamp');
        if (!timestampDiv) return;
        
        let versionBadge = timestampDiv.querySelector('.message-version-badge');
        if (!versionBadge) {
            versionBadge = document.createElement('span');
            versionBadge.className = 'message-version-badge';
            timestampDiv.insertBefore(versionBadge, timestampDiv.firstChild);
            
            const separator = document.createElement('span');
            separator.textContent = ' • ';
            timestampDiv.insertBefore(separator, versionBadge.nextSibling);
        }
        
        // Create navigation controls
        const navContainer = document.createElement('span');
        navContainer.className = 'version-navigation';
        
        // Back button
        const backBtn = document.createElement('button');
        backBtn.className = 'version-nav-btn';
        backBtn.innerHTML = '◀';
        backBtn.title = 'Previous version';
        backBtn.disabled = currentIdx === 0;
        backBtn.onclick = () => this.navigateVersion(messageDiv, currentIdx - 1);
        
        // Version counter
        const counter = document.createElement('span');
        counter.className = 'version-counter';
        counter.textContent = `${currentIdx + 1}/${total}`;
        
        // Forward button
        const forwardBtn = document.createElement('button');
        forwardBtn.className = 'version-nav-btn';
        forwardBtn.innerHTML = '▶';
        forwardBtn.title = 'Next version';
        forwardBtn.disabled = currentIdx === total - 1;
        forwardBtn.onclick = () => this.navigateVersion(messageDiv, currentIdx + 1);
        
        navContainer.appendChild(backBtn);
        navContainer.appendChild(counter);
        navContainer.appendChild(forwardBtn);
        
        versionBadge.innerHTML = '';
        versionBadge.appendChild(navContainer);
    }
    
    /**
     * Navigate to specific version
     */
    navigateVersion(messageDiv, newIndex) {
        const messageId = messageDiv.dataset.messageId;
        const history = this.getMessageHistory(messageId);
        
        if (newIndex < 0 || newIndex >= history.length) return;
        
        // Update user message content
        const textDiv = messageDiv.querySelector('.message-text');
        textDiv.textContent = history[newIndex].userContent;
        
        // Update or create assistant response
        let assistantMsg = messageDiv.nextElementSibling;
        while (assistantMsg && !assistantMsg.classList.contains('assistant')) {
            assistantMsg = assistantMsg.nextElementSibling;
        }
        
        // Check if this version has a response (not empty string)
        const hasResponse = history[newIndex].assistantResponse && history[newIndex].assistantResponse.trim() !== '';
        
        if (hasResponse) {
            if (assistantMsg) {
                // Update existing assistant message
                const assistantTextDiv = assistantMsg.querySelector('.message-text');
                assistantTextDiv.innerHTML = history[newIndex].assistantResponse;
                
                // Re-highlight code blocks
                if (typeof hljs !== 'undefined') {
                    assistantTextDiv.querySelectorAll('pre code').forEach((block) => {
                        hljs.highlightElement(block);
                    });
                }
            } else {
                // Create new assistant message with full structure
                const chatContainer = messageDiv.parentElement;
                const model = messageDiv.dataset.model || 'gemini';
                const context = messageDiv.dataset.context || 'casual';
                const timestamp = messageDiv.dataset.timestamp || new Date().toLocaleTimeString('vi-VN');
                
                // Use addMessage to create properly formatted assistant message
                const tempContainer = document.createElement('div');
                this.addMessage(tempContainer, history[newIndex].assistantResponse, false, model, context, timestamp);
                
                // Insert the created message after user message
                const newAssistantMsg = tempContainer.firstChild;
                messageDiv.parentNode.insertBefore(newAssistantMsg, messageDiv.nextSibling);
            }
        }
        // Note: If no response in this version, keep the current assistant message as-is
        // Don't remove it - user might be navigating through versions temporarily
        
        // Update current version
        messageDiv.dataset.currentVersion = newIndex.toString();
        
        // Refresh version indicator
        this.updateVersionIndicator(messageDiv);
    }

    /**
     * Get message history
     */
    getMessageHistory(messageId) {
        return this.messageHistory.get(messageId) || [];
    }

    /**
     * Make images clickable for preview
     */
    makeImagesClickable(onImageClick) {
        // Query for images in message content and generated preview images
        const images = document.querySelectorAll('.message-content img, .message-text img, .generated-preview, img[alt="Generated Image"]');
        console.log(`[Image Preview] Found ${images.length} images`);
        
        images.forEach(img => {
            if (!img.hasAttribute('data-clickable')) {
                img.setAttribute('data-clickable', 'true');
                img.style.cursor = 'zoom-in';
                img.addEventListener('click', function(e) {
                    e.stopPropagation();
                    console.log('[Image Preview] Image clicked:', this.src?.substring(0, 100));
                    if (onImageClick) {
                        onImageClick(this);
                    }
                });
                console.log('[Image Preview] Made clickable:', img.alt || img.src?.substring(0, 50));
            }
        });
    }

    /**
     * Re-attach event listeners after loading chat
     */
    reattachEventListeners(chatContainer, onEditSave, onCopy, onImageClick) {
        // Re-attach all message action buttons
        chatContainer.querySelectorAll('.message').forEach(messageDiv => {
            const isUser = messageDiv.classList.contains('user');
            const content = messageDiv.querySelector('.message-text')?.textContent || '';
            const contentHTML = messageDiv.querySelector('.message-text')?.innerHTML || '';
            
            // Find action buttons container
            const actionsDiv = messageDiv.querySelector('.message-actions');
            if (!actionsDiv) return;
            
            if (!isUser) {
                // Assistant message actions
                const copyBtn = actionsDiv.querySelector('.copy-btn');
                if (copyBtn) {
                    copyBtn.onclick = () => this.copyMessageToClipboard(contentHTML, copyBtn);
                }
                
                const likeBtn = actionsDiv.querySelector('.like-btn');
                if (likeBtn) {
                    likeBtn.onclick = () => this.toggleFeedback(likeBtn, 'like', messageDiv);
                }
                
                const dislikeBtn = actionsDiv.querySelector('.dislike-btn');
                if (dislikeBtn) {
                    dislikeBtn.onclick = () => this.toggleFeedback(dislikeBtn, 'dislike', messageDiv);
                }
                
                const regenBtn = actionsDiv.querySelector('.regenerate-btn');
                if (regenBtn) {
                    regenBtn.onclick = () => this.regenerateResponse(messageDiv);
                }
                
                const moreBtn = actionsDiv.querySelector('.more-btn');
                if (moreBtn) {
                    moreBtn.onclick = () => this.showMoreOptions(messageDiv, moreBtn);
                }
            } else {
                // User message actions
                const editBtn = actionsDiv.querySelector('.edit-btn');
                if (editBtn) {
                    editBtn.onclick = () => this.showEditForm(messageDiv, content);
                }
                
                const moreBtn = actionsDiv.querySelector('.more-btn');
                if (moreBtn) {
                    moreBtn.onclick = () => this.showMoreOptions(messageDiv, moreBtn);
                }
            }
        });
        
        // Re-attach version navigation buttons
        chatContainer.querySelectorAll('.version-nav-btn').forEach(btn => {
            const messageDiv = btn.closest('.message');
            if (!messageDiv) return;
            
            const currentVersion = parseInt(messageDiv.dataset.currentVersion || '0');
            const isBack = btn.innerHTML === '◀';
            const newIndex = isBack ? currentVersion - 1 : currentVersion + 1;
            
            btn.onclick = () => this.navigateVersion(messageDiv, newIndex);
        });
        
        // Legacy buttons (old style - keep for compatibility)
        chatContainer.querySelectorAll('.edit-message-btn').forEach(btn => {
            const messageDiv = btn.closest('.message');
            const textContent = messageDiv.querySelector('.message-text')?.textContent || '';
            btn.onclick = () => this.showEditForm(messageDiv, textContent);
        });
        
        chatContainer.querySelectorAll('.copy-message-btn').forEach(btn => {
            const messageDiv = btn.closest('.message');
            const textContent = messageDiv.querySelector('.message-text')?.textContent || '';
            btn.onclick = () => this.copyMessageToClipboard(textContent, btn);
        });
        
        // Table copy buttons
        chatContainer.querySelectorAll('.copy-table-btn').forEach(btn => {
            const table = btn.previousElementSibling;
            if (table && table.tagName === 'TABLE') {
                btn.onclick = () => this.copyTableToClipboard(table, btn);
            }
        });
        
        // Make images clickable
        if (onImageClick) {
            this.makeImagesClickable(onImageClick);
        }
    }

    /**
     * Set edit save callback
     */
    setEditSaveCallback(callback) {
        this.onEditSave = callback;
    }
    
    /**
     * Open image preview modal
     */
    openImagePreview(imgElement) {
        console.log('[Image Preview] Opening preview for:', imgElement.src);
        const modal = document.getElementById('imagePreviewModal');
        const previewImg = document.getElementById('imagePreviewContent');
        const previewInfo = document.getElementById('imagePreviewInfo');
        
        if (modal && previewImg) {
            previewImg.src = imgElement.src;
            modal.classList.add('active');
            
            if (previewInfo) {
                // Show image info
                const img = new Image();
                img.onload = () => {
                    previewInfo.innerHTML = `
                        <p>📐 Dimensions: ${img.width} x ${img.height}</p>
                        <p>📁 Size: ${(imgElement.src.length / 1024).toFixed(2)} KB</p>
                    `;
                };
                img.src = imgElement.src;
            }
        }
    }
    
    /**
     * Close image preview modal
     */
    closeImagePreview() {
        const modal = document.getElementById('imagePreviewModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }
    
    /**
     * Download preview image
     */
    downloadPreviewImage() {
        const previewImg = document.getElementById('imagePreviewContent');
        if (previewImg && previewImg.src) {
            const link = document.createElement('a');
            link.href = previewImg.src;
            link.download = `image_${Date.now()}.png`;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }
    }
}
