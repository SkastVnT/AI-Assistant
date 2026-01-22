/**
 * MCP Integration JavaScript
 * Handles Model Context Protocol integration in ChatBot
 */

class MCPController {
    constructor() {
        this.enabled = false;
        this.folders = [];
        this.files = [];
        this.selectedFiles = [];
        this.initializeUI();
        this.setupEventListeners();
    }

    initializeUI() {
        this.checkbox = document.getElementById('mcpEnabledCheck');
        this.selectBtn = document.getElementById('mcpSelectFolderBtn');
        this.statusSpan = document.getElementById('mcpStatus');
        this.folderList = document.getElementById('mcpFolderList');
        this.fileList = document.getElementById('mcpFileList');
        this.fileSearch = document.getElementById('mcpFileSearch');
        this.selectedFilesDiv = document.getElementById('mcpSelectedFiles');
        this.selectedFileList = document.getElementById('selectedFileList');
        this.selectedFileCount = document.getElementById('selectedFileCount');
        this.sidebar = document.getElementById('mcpSidebar');
        this.toggleBtn = document.getElementById('mcpToggleBtn');
        this.isOpen = false; // Start collapsed
        
        // Log để debug
        console.log('MCP UI Elements:', {
            checkbox: this.checkbox,
            selectBtn: this.selectBtn,
            statusSpan: this.statusSpan,
            sidebar: this.sidebar,
            toggleBtn: this.toggleBtn
        });
    }

    setupEventListeners() {
        // MCP Enable/Disable
        this.checkbox.addEventListener('change', (e) => {
            if (e.target.checked) {
                this.enable();
            } else {
                this.disable();
            }
        });

        // Select Folder Button
        this.selectBtn.addEventListener('click', () => {
            this.selectFolder();
        });

        // File Search
        this.fileSearch.addEventListener('input', (e) => {
            this.filterFiles(e.target.value);
        });

        // Toggle Sidebar
        this.toggleBtn.addEventListener('click', () => {
            this.toggleSidebar();
        });
        
        // Close button in sidebar header
        const closeBtn = document.getElementById('mcpCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closeSidebar();
            });
        }
    }
    
    closeSidebar() {
        this.isOpen = false;
        this.sidebar.classList.remove('open');
        this.toggleBtn.classList.remove('sidebar-open');
        this.toggleBtn.textContent = '▶';
        this.toggleBtn.title = 'Mở rộng MCP';
    }

    toggleSidebar() {
        this.isOpen = !this.isOpen;
        if (this.isOpen) {
            this.sidebar.classList.add('open');
            this.toggleBtn.classList.add('sidebar-open');
            this.toggleBtn.textContent = '◀';
            this.toggleBtn.title = 'Thu gọn MCP';
        } else {
            this.closeSidebar();
        }
    }

    async enable() {
        try {
            const response = await fetch('/api/mcp/enable', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            const result = await response.json();

            if (result.success) {
                this.enabled = true;
                this.selectBtn.disabled = false;
                this.fileSearch.disabled = false;
                this.updateStatus('active', '🟢 Enabled');
                this.showNotification('✅ MCP Enabled', 'success');
            } else {
                throw new Error(result.error || 'Failed to enable MCP');
            }
        } catch (error) {
            console.error('MCP enable error:', error);
            this.checkbox.checked = false;
            this.showNotification('❌ Cannot connect to MCP Server', 'error');
        }
    }

    async disable() {
        try {
            const response = await fetch('/api/mcp/disable', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' }
            });

            this.enabled = false;
            this.selectBtn.disabled = true;
            this.fileSearch.disabled = true;
            this.updateStatus('', '⚪ Tắt');
            this.folders = [];
            this.files = [];
            this.selectedFiles = [];
            this.folderList.style.display = 'none';
            this.folderList.innerHTML = '';
            this.fileList.innerHTML = '<div class="mcp-empty-state"><p>📂 Chưa chọn folder</p><p style="font-size: 11px; color: #888;">Bật MCP và chọn folder để xem files</p></div>';
            this.updateSelectedFiles();
            this.showNotification('MCP đã tắt', 'info');
        } catch (error) {
            console.error('MCP disable error:', error);
        }
    }

    async selectFolder() {
        // Use the new folder input with webkitdirectory
        const folderInput = document.getElementById('mcpFolderInput');
        if (folderInput) {
            folderInput.click();
        } else {
            console.error('Folder input not found');
        }
    }

    // Keep this for backwards compatibility but don't use
    createFolderModal_deprecated() {
        const modal = document.createElement('div');
        modal.className = 'modal';
        modal.style.display = 'block';
        modal.innerHTML = `
            <div class="modal-content" style="max-width: 600px;">
                <div class="modal-header">
                    <h2>📁 Chọn Folder Local</h2>
                    <button class="close-modal" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <p style="margin-bottom: 15px; color: #666;">
                        Nhập đường dẫn folder từ hệ thống local của bạn:
                    </p>
                    <input 
                        type="text" 
                        id="folderPathInput" 
                        placeholder="C:\\Users\\YourName\\Projects\\MyCode"
                        style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-family: monospace;"
                    >
                    <div style="margin-top: 10px; font-size: 12px; color: #888;">
                        Ví dụ: <code>C:\\Users\\Asus\\Downloads\\Compressed\\AI-Assistant</code>
                    </div>
                    <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end;">
                        <button 
                            class="new-chat-btn" 
                            style="background: #6c757d;"
                            onclick="this.closest('.modal').remove()"
                        >
                            Hủy
                        </button>
                        <button 
                            class="new-chat-btn" 
                            id="confirmFolderBtn"
                        >
                            ✓ Thêm Folder
                        </button>
                    </div>
                </div>
            </div>
        `;

        // Add event listener for confirm button
        const confirmBtn = modal.querySelector('#confirmFolderBtn');
        const input = modal.querySelector('#folderPathInput');

        confirmBtn.addEventListener('click', async () => {
            const folderPath = input.value.trim();
            if (folderPath) {
                await this.addFolder(folderPath);
                modal.remove();
            }
        });

        // Enter key to confirm
        input.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                confirmBtn.click();
            }
        });

        // Focus input
        setTimeout(() => input.focus(), 100);

        return modal;
    }

    async addFolder(folderPath) {
        try {
            const response = await fetch('/api/mcp/add-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ folder_path: folderPath })
            });

            const result = await response.json();

            if (result.success) {
                this.folders.push(folderPath);
                this.updateFolderList();
                await this.loadFiles();
                this.showNotification(`✅ Đã thêm folder: ${folderPath}`, 'success');
            } else {
                throw new Error(result.error || 'Invalid folder path');
            }
        } catch (error) {
            console.error('Add folder error:', error);
            this.showNotification(`❌ ${error.message}`, 'error');
        }
    }

    async loadFiles() {
        try {
            const response = await fetch('/api/mcp/list-files');
            const result = await response.json();

            if (result.success) {
                this.files = result.files;
                this.renderFileList();
            }
        } catch (error) {
            console.error('Load files error:', error);
        }
    }

    renderFileList() {
        if (this.files.length === 0) {
            this.fileList.innerHTML = '<div class="mcp-empty-state"><p>📂 Folder trống</p><p style="font-size: 11px; color: #888;">Không tìm thấy file</p></div>';
            return;
        }

        const fileIcons = {
            '.py': '🐍',
            '.js': '📜',
            '.ts': '📘',
            '.tsx': '⚛️',
            '.jsx': '⚛️',
            '.html': '🌐',
            '.css': '🎨',
            '.md': '📝',
            '.json': '📋',
            '.txt': '📄',
            '.yml': '⚙️',
            '.yaml': '⚙️'
        };

        this.fileList.innerHTML = this.files.map(file => {
            const icon = fileIcons[file.extension] || '📄';
            const size = this.formatFileSize(file.size);
            const isSelected = this.selectedFiles.some(f => f.path === file.path);

            return `
                <div class="mcp-file-item ${isSelected ? 'selected' : ''}" data-path="${file.path}">
                    <span class="mcp-file-icon">${icon}</span>
                    <div class="mcp-file-info">
                        <div class="mcp-file-name">${file.name}</div>
                        <div class="mcp-file-path">${file.relative_path}</div>
                    </div>
                    <span class="mcp-file-size">${size}</span>
                </div>
            `;
        }).join('');

        // Add click handlers
        this.fileList.querySelectorAll('.mcp-file-item').forEach(item => {
            item.addEventListener('click', () => {
                const path = item.dataset.path;
                this.toggleFileSelection(path);
            });
        });
    }

    toggleFileSelection(filePath) {
        const file = this.files.find(f => f.path === filePath);
        if (!file) return;

        const index = this.selectedFiles.findIndex(f => f.path === filePath);
        
        if (index > -1) {
            // Deselect
            this.selectedFiles.splice(index, 1);
        } else {
            // Select
            this.selectedFiles.push(file);
        }

        this.renderFileList();
        this.updateSelectedFiles();
    }

    updateSelectedFiles() {
        if (this.selectedFiles.length === 0) {
            this.selectedFilesDiv.style.display = 'none';
            return;
        }

        this.selectedFilesDiv.style.display = 'block';
        this.selectedFileCount.textContent = this.selectedFiles.length;

        this.selectedFileList.innerHTML = this.selectedFiles.map(file => `
            <div class="selected-file-chip">
                <span>${file.name}</span>
                <span class="remove" onclick="mcpController.deselectFile('${file.path.replace(/\\/g, '\\\\')}')">×</span>
            </div>
        `).join('');
    }

    deselectFile(filePath) {
        this.toggleFileSelection(filePath);
    }

    filterFiles(query) {
        if (!query) {
            this.renderFileList();
            return;
        }

        const filtered = this.files.filter(file => 
            file.name.toLowerCase().includes(query.toLowerCase()) ||
            file.relative_path.toLowerCase().includes(query.toLowerCase())
        );

        const temp = this.files;
        this.files = filtered;
        this.renderFileList();
        this.files = temp;
    }

    formatFileSize(bytes) {
        if (bytes < 1024) return bytes + ' B';
        if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
        return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
    }

    async removeFolder(folderPath) {
        try {
            const response = await fetch('/api/mcp/remove-folder', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ folder_path: folderPath })
            });

            this.folders = this.folders.filter(f => f !== folderPath);
            this.updateFolderList();
            await this.loadFiles();
            this.showNotification('🗑️ Đã xóa folder', 'info');
        } catch (error) {
            console.error('Remove folder error:', error);
        }
    }

    getSelectedFilesContext() {
        if (this.selectedFiles.length === 0) {
            return null;
        }

        let context = '\n\n📁 **SELECTED FILES FOR CONTEXT:**\n\n';
        
        for (const file of this.selectedFiles.slice(0, 5)) {
            context += `### 📄 ${file.relative_path}\n`;
            context += `Size: ${this.formatFileSize(file.size)}\n\n`;
        }

        return context;
    }
    getSelectedFilePaths() {
        return this.selectedFiles.map(f => f.path);
    }
    updateFolderList() {
        if (this.folders.length === 0) {
            this.folderList.style.display = 'none';
            return;
        }

        this.folderList.style.display = 'block';
        this.folderList.innerHTML = this.folders.map(folder => `
            <div class="mcp-folder-tag">
                <span>📁 ${this.truncatePath(folder)}</span>
                <span class="remove-folder" onclick="mcpController.removeFolder('${folder.replace(/\\/g, '\\\\')}')">
                    ×
                </span>
            </div>
        `).join('');
    }

    truncatePath(path) {
        const parts = path.split(/[\/\\]/);
        if (parts.length > 3) {
            return `...\\${parts.slice(-2).join('\\')}`;
        }
        return path;
    }

    updateStatus(className, text) {
        this.statusSpan.className = className;
        this.statusSpan.innerHTML = `<span data-lang-key="mcp.status.${className || 'disabled'}">${text}</span>`;
    }

    showNotification(message, type = 'info') {
        // Reuse existing notification system if available
        if (typeof showNotification === 'function') {
            showNotification(message, type);
        } else {
            // Fallback to console
            console.log(`[MCP ${type.toUpperCase()}]: ${message}`);
            alert(message);
        }
    }

    isEnabled() {
        return this.enabled;
    }

    getFolders() {
        return this.folders;
    }
}

// Global instance
let mcpController;

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    mcpController = new MCPController();
    window.mcpController = mcpController;  // Expose globally
    console.log('✅ MCP Controller initialized');
});
