/**
 * Message Renderer Module
 * Handles message rendering, markdown parsing, code highlighting
 */

export class MessageRenderer {
    constructor() {
        this.modelNames = {
            'gemini': 'Gemini',
            'openai': 'GPT-4o-mini',
            'deepseek': 'DeepSeek',
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
    addMessage(chatContainer, content, isUser, model, context, timestamp) {
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
            infoDiv.textContent = `${this.modelNames[model] || model} • ${this.contextNames[context] || context}`;
            contentDiv.appendChild(infoDiv);
        }
        
        // Add timestamp
        const timestampDiv = document.createElement('div');
        timestampDiv.className = 'message-timestamp';
        timestampDiv.textContent = timestamp;
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
     * Add action buttons to message
     */
    addMessageButtons(contentDiv, content, isUser, messageDiv) {
        if (!isUser) {
            // Copy button for assistant messages
            const copyMsgBtn = document.createElement('button');
            copyMsgBtn.className = 'copy-message-btn';
            copyMsgBtn.textContent = '📋 Copy';
            copyMsgBtn.onclick = () => this.copyMessageToClipboard(content, copyMsgBtn);
            contentDiv.appendChild(copyMsgBtn);
        } else {
            // Edit button for user messages
            const editBtn = document.createElement('button');
            editBtn.className = 'edit-message-btn';
            editBtn.textContent = '✏️ Edit';
            editBtn.onclick = () => this.showEditForm(messageDiv, content);
            contentDiv.appendChild(editBtn);
        }
    }

    /**
     * Copy message to clipboard
     */
    async copyMessageToClipboard(content, button) {
        const plainText = content.replace(/<[^>]*>/g, '').trim();
        
        try {
            await navigator.clipboard.writeText(plainText);
            const originalText = button.textContent;
            button.textContent = '✅ Đã copy!';
            button.classList.add('copied');
            
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('copied');
            }, 2000);
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
        
        // Only save to history if this is the first edit
        if (!this.messageHistory.has(messageId)) {
            this.addMessageVersion(messageId, originalContent, new Date().toISOString());
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
            if (this.onEditSave) {
                this.onEditSave(messageDiv, textarea.value, originalContent);
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
    addMessageVersion(messageId, content, timestamp) {
        if (!this.messageHistory.has(messageId)) {
            this.messageHistory.set(messageId, []);
        }
        
        this.messageHistory.get(messageId).push({
            content: content,
            timestamp: timestamp
        });
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
        const images = document.querySelectorAll('.message-content img');
        console.log(`[Image Preview] Found ${images.length} images`);
        
        images.forEach(img => {
            if (!img.hasAttribute('data-clickable')) {
                img.setAttribute('data-clickable', 'true');
                img.style.cursor = 'zoom-in';
                img.addEventListener('click', function(e) {
                    e.stopPropagation();
                    console.log('[Image Preview] Image clicked:', this.src);
                    if (onImageClick) {
                        onImageClick(this);
                    }
                });
                console.log('[Image Preview] Made clickable:', img.src);
            }
        });
    }

    /**
     * Re-attach event listeners after loading chat
     */
    reattachEventListeners(chatContainer, onEditSave, onCopy, onImageClick) {
        // Edit buttons
        chatContainer.querySelectorAll('.edit-message-btn').forEach(btn => {
            const messageDiv = btn.closest('.message');
            const textContent = messageDiv.querySelector('.message-text')?.textContent || '';
            btn.onclick = () => this.showEditForm(messageDiv, textContent);
        });
        
        // Copy buttons
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
