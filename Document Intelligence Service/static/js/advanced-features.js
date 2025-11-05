// Advanced Features - JavaScript Module
// Batch Processing, Templates, History, Quick Actions

class AdvancedFeatures {
    constructor(app) {
        this.app = app;
        this.initializeElements();
        this.attachEventListeners();
    }

    initializeElements() {
        // Tool buttons
        this.batchBtn = document.getElementById('batchBtn');
        this.templatesBtn = document.getElementById('templatesBtn');
        this.historyBtn = document.getElementById('historyBtn');
        this.quickActionsBtn = document.getElementById('quickActionsBtn');

        // Modals
        this.batchModal = document.getElementById('batchModal');
        this.templatesModal = document.getElementById('templatesModal');
        this.historyModal = document.getElementById('historyModal');
        this.quickActionsModal = document.getElementById('quickActionsModal');

        // Batch elements
        this.batchFileInput = document.getElementById('batchFileInput');
        this.selectBatchFilesBtn = document.getElementById('selectBatchFilesBtn');
        this.batchFilesList = document.getElementById('batchFilesList');
        this.batchFileCount = document.getElementById('batchFileCount');
        this.batchFilesItems = document.getElementById('batchFilesItems');
        this.processBatchBtn = document.getElementById('processBatchBtn');
        this.batchResults = document.getElementById('batchResults');

        // Templates elements
        this.templatesList = document.getElementById('templatesList');

        // History elements
        this.historySearch = document.getElementById('historySearch');
        this.historyList = document.getElementById('historyList');
        this.clearHistoryBtn = document.getElementById('clearHistoryBtn');

        // Quick Actions elements
        this.quickActionResult = document.getElementById('quickActionResult');
        this.quickActionText = document.getElementById('quickActionText');
        this.copyQuickActionBtn = document.getElementById('copyQuickActionBtn');

        // Tools tab
        this.toolsTab = document.getElementById('toolsTab');
    }

    attachEventListeners() {
        // Tool buttons
        this.batchBtn?.addEventListener('click', () => this.openModal('batchModal'));
        this.templatesBtn?.addEventListener('click', () => this.openModal('templatesModal'));
        this.historyBtn?.addEventListener('click', () => this.openModal('historyModal'));
        this.quickActionsBtn?.addEventListener('click', () => this.openModal('quickActionsModal'));

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const modalId = e.target.getAttribute('data-modal');
                this.closeModal(modalId);
            });
        });

        // Close modal on background click
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModal(modal.id);
                }
            });
        });

        // Batch processing
        this.selectBatchFilesBtn?.addEventListener('click', () => this.batchFileInput.click());
        this.batchFileInput?.addEventListener('change', (e) => this.handleBatchFiles(e));
        this.processBatchBtn?.addEventListener('click', () => this.processBatch());

        // History
        this.historySearch?.addEventListener('input', (e) => this.searchHistory(e.target.value));
        this.clearHistoryBtn?.addEventListener('click', () => this.clearHistory());

        // Quick Actions
        document.querySelectorAll('.quick-action-card').forEach(card => {
            card.addEventListener('click', (e) => {
                const action = e.currentTarget.getAttribute('data-quick-action');
                this.executeQuickAction(action);
            });
        });

        this.copyQuickActionBtn?.addEventListener('click', () => this.copyQuickActionResult());

        // Tool actions in result panel
        document.querySelectorAll('.tool-action-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const action = e.currentTarget.getAttribute('data-action');
                this.executeToolAction(action);
            });
        });
    }

    // Modal management
    openModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'flex';
            
            // Load content based on modal
            if (modalId === 'templatesModal') {
                this.loadTemplates();
            } else if (modalId === 'historyModal') {
                this.loadHistory();
            }
        }
    }

    closeModal(modalId) {
        const modal = document.getElementById(modalId);
        if (modal) {
            modal.style.display = 'none';
        }
    }

    // Batch Processing
    handleBatchFiles(event) {
        const files = Array.from(event.target.files);
        
        if (files.length === 0) return;
        
        if (files.length > 10) {
            this.app.showNotification('⚠️ Tối đa 10 files', 'warning');
            return;
        }

        this.batchFileCount.textContent = files.length;
        this.batchFilesItems.innerHTML = '';
        
        files.forEach((file, index) => {
            const item = document.createElement('div');
            item.className = 'batch-file-item';
            item.innerHTML = `
                <span><i class="fas fa-file"></i> ${file.name}</span>
                <span>${this.formatFileSize(file.size)}</span>
            `;
            this.batchFilesItems.appendChild(item);
        });

        this.batchFilesList.style.display = 'block';
    }

    async processBatch() {
        const files = this.batchFileInput.files;
        
        if (files.length === 0) {
            this.app.showNotification('⚠️ Chưa chọn files', 'warning');
            return;
        }

        this.processBatchBtn.disabled = true;
        this.processBatchBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Đang xử lý...';

        const formData = new FormData();
        Array.from(files).forEach(file => {
            formData.append('files', file);
        });

        try {
            const response = await fetch('/api/batch', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (data.success) {
                this.displayBatchResults(data);
                this.app.showNotification(`✅ Đã xử lý ${data.success_count}/${data.total_files} files`, 'success');
            } else {
                this.app.showNotification(`❌ Lỗi: ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Batch processing error:', error);
            this.app.showNotification('❌ Lỗi khi xử lý batch', 'error');
        } finally {
            this.processBatchBtn.disabled = false;
            this.processBatchBtn.innerHTML = '<i class="fas fa-magic"></i> Xử lý Batch';
        }
    }

    displayBatchResults(data) {
        this.batchResults.innerHTML = `
            <h4>Kết quả Batch Processing</h4>
            <p>Tổng: ${data.total_files} | Thành công: ${data.success_count} | Lỗi: ${data.error_count}</p>
        `;

        data.results.forEach(result => {
            const item = document.createElement('div');
            item.className = `batch-result-item ${result.result.success ? '' : 'error'}`;
            
            const icon = result.result.success ? '✅' : '❌';
            const text = result.result.success 
                ? `${result.result.text?.substring(0, 100)}...` 
                : result.result.error;

            item.innerHTML = `
                <div><strong>${icon} ${result.file}</strong></div>
                <div style="font-size: 0.85rem; color: var(--text-muted); margin-top: 4px;">
                    ${text}
                </div>
            `;
            this.batchResults.appendChild(item);
        });

        this.batchResults.style.display = 'block';
    }

    // Templates
    async loadTemplates() {
        try {
            const response = await fetch('/api/templates');
            const data = await response.json();

            if (data.success) {
                this.displayTemplates(data.templates);
            }
        } catch (error) {
            console.error('Error loading templates:', error);
            this.app.showNotification('❌ Lỗi khi tải templates', 'error');
        }
    }

    displayTemplates(templates) {
        this.templatesList.innerHTML = '';

        Object.entries(templates).forEach(([key, template]) => {
            const card = document.createElement('div');
            card.className = 'template-card';
            card.innerHTML = `
                <div class="template-header">
                    <span class="template-icon">${template.icon}</span>
                    <span class="template-name">${template.name}</span>
                </div>
                <div class="template-fields">
                    <strong>Fields:</strong> ${template.fields.join(', ')}
                </div>
            `;
            
            card.addEventListener('click', () => {
                this.matchTemplate(key);
                this.closeModal('templatesModal');
            });

            this.templatesList.appendChild(card);
        });
    }

    async matchTemplate(templateName) {
        if (!this.app.currentResult?.text) {
            this.app.showNotification('⚠️ Chưa có text để match', 'warning');
            return;
        }

        try {
            const response = await fetch('/api/templates/match', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ text: this.app.currentResult.text })
            });

            const data = await response.json();

            if (data.success && data.matched_template) {
                this.app.showNotification(`✅ Matched: ${data.matched_template}`, 'success');
                console.log('Template:', data.template);
            } else {
                this.app.showNotification('ℹ️ Không tìm thấy template phù hợp', 'info');
            }
        } catch (error) {
            console.error('Error matching template:', error);
        }
    }

    // History
    async loadHistory(query = '') {
        try {
            const url = query 
                ? `/api/history/search?q=${encodeURIComponent(query)}`
                : '/api/history';
            
            const response = await fetch(url);
            const data = await response.json();

            if (data.success) {
                const items = query ? data.results : data.history;
                this.displayHistory(items);
            }
        } catch (error) {
            console.error('Error loading history:', error);
            this.app.showNotification('❌ Lỗi khi tải history', 'error');
        }
    }

    displayHistory(items) {
        this.historyList.innerHTML = '';

        if (items.length === 0) {
            this.historyList.innerHTML = '<p style="text-align: center; color: var(--text-muted);">Chưa có lịch sử</p>';
            return;
        }

        items.forEach(item => {
            const card = document.createElement('div');
            card.className = 'history-item';
            
            const date = new Date(item.timestamp);
            const timeStr = date.toLocaleString('vi-VN');

            card.innerHTML = `
                <div class="history-header">
                    <span class="history-filename">
                        <i class="fas fa-file"></i> ${item.filename}
                    </span>
                    <span class="history-time">${timeStr}</span>
                </div>
                <div class="history-preview">${item.text || 'No preview'}</div>
                ${item.document_type ? `<div style="margin-top: 8px;"><span class="badge">${item.document_type}</span></div>` : ''}
            `;

            card.addEventListener('click', () => {
                console.log('History item:', item);
                this.app.showNotification(`📄 ${item.filename}`, 'info');
            });

            this.historyList.appendChild(card);
        });
    }

    searchHistory(query) {
        if (query.length > 0) {
            this.loadHistory(query);
        } else {
            this.loadHistory();
        }
    }

    async clearHistory() {
        if (!confirm('Xóa toàn bộ lịch sử?')) return;

        try {
            const response = await fetch('/api/history/clear', {
                method: 'POST'
            });

            const data = await response.json();

            if (data.success) {
                this.app.showNotification('✅ Đã xóa lịch sử', 'success');
                this.loadHistory();
            }
        } catch (error) {
            console.error('Error clearing history:', error);
            this.app.showNotification('❌ Lỗi khi xóa history', 'error');
        }
    }

    // Quick Actions
    async executeQuickAction(action) {
        if (!this.app.currentResult?.text) {
            this.app.showNotification('⚠️ Chưa có text để xử lý', 'warning');
            return;
        }

        try {
            let response;
            
            if (action === 'clean') {
                response = await fetch('/api/quick-actions/clean', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: this.app.currentResult.text })
                });
            } else if (action === 'extract') {
                response = await fetch('/api/quick-actions/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: this.app.currentResult.text })
                });
            } else {
                response = await fetch('/api/quick-actions/format', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        text: this.app.currentResult.text,
                        action: action 
                    })
                });
            }

            const data = await response.json();

            if (data.success) {
                this.displayQuickActionResult(data, action);
            } else {
                this.app.showNotification(`❌ ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Quick action error:', error);
            this.app.showNotification('❌ Lỗi khi thực hiện action', 'error');
        }
    }

    displayQuickActionResult(data, action) {
        if (action === 'extract') {
            // Display extracted info
            const info = [];
            if (data.numbers?.length) info.push(`Numbers: ${data.numbers.join(', ')}`);
            if (data.dates?.length) info.push(`Dates: ${data.dates.join(', ')}`);
            if (data.emails?.length) info.push(`Emails: ${data.emails.join(', ')}`);
            if (data.phones?.length) info.push(`Phones: ${data.phones.join(', ')}`);
            
            this.quickActionText.value = info.join('\n\n');
        } else {
            this.quickActionText.value = data.text;
        }

        this.quickActionResult.style.display = 'block';
        this.app.showNotification('✅ Action hoàn thành', 'success');
    }

    copyQuickActionResult() {
        this.quickActionText.select();
        document.execCommand('copy');
        this.app.showNotification('✅ Đã copy', 'success');
    }

    // Tool actions in result panel
    async executeToolAction(action) {
        if (!this.app.currentResult?.text) {
            this.app.showNotification('⚠️ Chưa có text', 'warning');
            return;
        }

        // Show tools tab
        this.toolsTab.style.display = 'block';
        this.switchToToolsTab();

        try {
            let response;
            
            if (action === 'clean') {
                response = await fetch('/api/quick-actions/clean', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: this.app.currentResult.text })
                });
            } else if (action === 'extract_info') {
                response = await fetch('/api/quick-actions/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: this.app.currentResult.text })
                });
            } else {
                response = await fetch('/api/quick-actions/format', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ 
                        text: this.app.currentResult.text,
                        action: action 
                    })
                });
            }

            const data = await response.json();

            if (data.success) {
                this.displayToolResult(data, action);
            } else {
                this.app.showNotification(`❌ ${data.error}`, 'error');
            }
        } catch (error) {
            console.error('Tool action error:', error);
            this.app.showNotification('❌ Lỗi', 'error');
        }
    }

    displayToolResult(data, action) {
        const resultDiv = document.getElementById('toolsResult');
        const resultText = document.getElementById('toolsResultText');

        if (action === 'extract_info') {
            const info = [];
            if (data.numbers?.length) info.push(`📊 Numbers: ${data.numbers.join(', ')}`);
            if (data.dates?.length) info.push(`📅 Dates: ${data.dates.join(', ')}`);
            if (data.emails?.length) info.push(`📧 Emails: ${data.emails.join(', ')}`);
            if (data.phones?.length) info.push(`📱 Phones: ${data.phones.join(', ')}`);
            
            resultText.textContent = info.length > 0 ? info.join('\n\n') : 'Không tìm thấy thông tin';
        } else if (action === 'clean' && data.stats) {
            resultText.textContent = data.text + '\n\n' + 
                `📊 Stats:\n` +
                `- Saved ${data.stats.saved_chars} characters\n` +
                `- Removed ${data.stats.removed_lines} duplicate lines`;
        } else {
            resultText.textContent = data.text;
        }

        resultDiv.style.display = 'block';
        this.app.showNotification('✅ Hoàn thành', 'success');
    }

    switchToToolsTab() {
        // Switch to tools tab
        document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
        
        this.toolsTab.classList.add('active');
        document.getElementById('toolsTab').classList.add('active');
    }

    // Utilities
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }
}

// Export for use in main app
window.AdvancedFeatures = AdvancedFeatures;
