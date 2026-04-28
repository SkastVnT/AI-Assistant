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
        this.ocrContexts = [];
        // Unified source state (previously split across ChatBotApp.mcpContext)
        this.localFolders = [];   // webkitdirectory folders with content
        this.urls = [];           // fetched URLs with content
        this.uploads = [];        // uploaded files with content
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
        this.ocrBtn = document.getElementById('mcpOcrBtn');
        this.warmCacheBtn = document.getElementById('mcpWarmCacheBtn');
        this.isOpen = false; // Start collapsed
        
        // Log ─æß╗â debug
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

        // OCR selected files via MCP
        if (this.ocrBtn) {
            this.ocrBtn.addEventListener('click', () => {
                this.runOcrForSelectedFiles();
            });
        }

        // Manual warm-cache from current message question
        if (this.warmCacheBtn) {
            this.warmCacheBtn.addEventListener('click', () => {
                const msgInput = document.getElementById('messageInput');
                const question = msgInput && msgInput.value ? msgInput.value.trim() : '';
                this.warmCacheForQuestion(question);
            });
        }
        
        // Close button in sidebar header
        const closeBtn = document.getElementById('mcpCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.closeSidebar();
            });
        }

        // Set up source tabs (folder picker, URL fetch, file upload)
        this.setupSourceTabs();
    }
    
    closeSidebar() {
        this.isOpen = false;
        this.sidebar.classList.remove('open');
        this.toggleBtn.classList.remove('sidebar-open');
        this.toggleBtn.textContent = 'Γû╢';
        this.toggleBtn.title = 'Mß╗ƒ rß╗Öng MCP';
    }

    toggleSidebar() {
        this.isOpen = !this.isOpen;
        if (this.isOpen) {
            this.sidebar.classList.add('open');
            this.toggleBtn.classList.add('sidebar-open');
            this.toggleBtn.textContent = 'ΓùÇ';
            this.toggleBtn.title = 'Thu gß╗ìn MCP';
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
                this.updateStatus('active', '≡ƒƒó Enabled');
                this.showNotification('Γ£à MCP Enabled', 'success');
                // Enable tab buttons
                ['mcpTabFolder', 'mcpTabUrl', 'mcpTabUpload'].forEach(id => {
                    const tab = document.getElementById(id);
                    if (tab) tab.disabled = false;
                });
                // Enable URL and upload inputs
                const urlInput = document.getElementById('mcpUrlInput');
                const fetchUrlBtn = document.getElementById('mcpFetchUrlBtn');
                const uploadBtn = document.getElementById('mcpUploadBtn');
                if (urlInput) urlInput.disabled = false;
                if (fetchUrlBtn) fetchUrlBtn.disabled = false;
                if (uploadBtn) uploadBtn.disabled = false;
            } else {
                throw new Error(result.error || 'Failed to enable MCP');
            }
        } catch (error) {
            console.error('MCP enable error:', error);
            this.checkbox.checked = false;
            this.showNotification('Γ¥î Cannot connect to MCP Server', 'error');
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
            this.updateStatus('', 'ΓÜ¬ Tß║»t');
            // Disable tab buttons
            ['mcpTabFolder', 'mcpTabUrl', 'mcpTabUpload'].forEach(id => {
                const tab = document.getElementById(id);
                if (tab) tab.disabled = true;
            });
            this.folders = [];
            this.files = [];
            this.selectedFiles = [];
            this.ocrContexts = [];
            this.localFolders = [];
            this.urls = [];
            this.uploads = [];
            this.folderList.style.display = 'none';
            this.folderList.innerHTML = '';
            this.fileList.innerHTML = '<div class="mcp-empty-state"><p>≡ƒôé Ch╞░a chß╗ìn folder</p><p style="font-size: 11px; color: #888;">Bß║¡t MCP v├á chß╗ìn folder ─æß╗â xem files</p></div>';
            this.updateSelectedFiles();
            // Disable URL and upload inputs
            const urlInput = document.getElementById('mcpUrlInput');
            const fetchUrlBtn = document.getElementById('mcpFetchUrlBtn');
            const uploadBtn = document.getElementById('mcpUploadBtn');
            if (urlInput) urlInput.disabled = true;
            if (fetchUrlBtn) fetchUrlBtn.disabled = true;
            if (uploadBtn) uploadBtn.disabled = true;
            // Clear URL and upload lists
            const urlList = document.getElementById('mcpUrlList');
            const uploadList = document.getElementById('mcpUploadList');
            if (urlList) urlList.innerHTML = '';
            if (uploadList) uploadList.innerHTML = '';
            this.updateIndicator();
            this.updateFileListDisplay();
            this.showNotification('MCP ─æ├ú tß║»t', 'info');
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
                    <h2>≡ƒôü Chß╗ìn Folder Local</h2>
                    <button class="close-modal" onclick="this.closest('.modal').remove()">&times;</button>
                </div>
                <div style="padding: 20px;">
                    <p style="margin-bottom: 15px; color: #666;">
                        Nhß║¡p ─æ╞░ß╗¥ng dß║½n folder tß╗½ hß╗ç thß╗æng local cß╗ºa bß║ín:
                    </p>
                    <input 
                        type="text" 
                        id="folderPathInput" 
                        placeholder="C:\\Users\\YourName\\Projects\\MyCode"
                        style="width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 6px; font-family: monospace;"
                    >
                    <div style="margin-top: 10px; font-size: 12px; color: #888;">
                        V├¡ dß╗Ñ: <code>C:\\Users\\Asus\\Downloads\\Compressed\\AI-Assistant</code>
                    </div>
                    <div style="margin-top: 20px; display: flex; gap: 10px; justify-content: flex-end;">
                        <button 
                            class="new-chat-btn" 
                            style="background: #6c757d;"
                            onclick="this.closest('.modal').remove()"
                        >
                            Hß╗ºy
                        </button>
                        <button 
                            class="new-chat-btn" 
                            id="confirmFolderBtn"
                        >
                            Γ£ô Th├¬m Folder
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
                this.showNotification(`Γ£à ─É├ú th├¬m folder: ${folderPath}`, 'success');
            } else {
                throw new Error(result.error || 'Invalid folder path');
            }
        } catch (error) {
            console.error('Add folder error:', error);
            this.showNotification(`Γ¥î ${error.message}`, 'error');
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
            this.fileList.innerHTML = '<div class="mcp-empty-state"><p>≡ƒôé Folder trß╗æng</p><p style="font-size: 11px; color: #888;">Kh├┤ng t├¼m thß║Ñy file</p></div>';
            return;
        }

        const fileIcons = {
            '.py': '≡ƒÉì',
            '.js': '≡ƒô£',
            '.ts': '≡ƒôÿ',
            '.tsx': 'ΓÜ¢∩╕Å',
            '.jsx': 'ΓÜ¢∩╕Å',
            '.html': '≡ƒîÉ',
            '.css': '≡ƒÄ¿',
            '.md': '≡ƒô¥',
            '.json': '≡ƒôï',
            '.txt': '≡ƒôä',
            '.yml': 'ΓÜÖ∩╕Å',
            '.yaml': 'ΓÜÖ∩╕Å'
        };

        this.fileList.innerHTML = this.files.map(file => {
            const icon = fileIcons[file.extension] || '≡ƒôä';
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

        // Clear OCR context for deselected files
        const selectedPaths = new Set(this.selectedFiles.map(f => f.path));
        this.ocrContexts = this.ocrContexts.filter(item => selectedPaths.has(item.path));
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
                <span class="remove" onclick="mcpController.deselectFile('${file.path.replace(/\\/g, '\\\\')}')">├ù</span>
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
            this.showNotification('≡ƒùæ∩╕Å ─É├ú x├│a folder', 'info');
        } catch (error) {
            console.error('Remove folder error:', error);
        }
    }

    getSelectedFilesContext() {
        if (this.selectedFiles.length === 0) {
            return null;
        }

        let context = '\n\n≡ƒôü **SELECTED FILES FOR CONTEXT:**\n\n';
        
        for (const file of this.selectedFiles.slice(0, 5)) {
            context += `### ≡ƒôä ${file.relative_path}\n`;
            context += `Size: ${this.formatFileSize(file.size)}\n\n`;
        }

        return context;
    }
    getSelectedFilePaths() {
        return this.selectedFiles.map(f => f.path);
    }

    getOcrContextString() {
        if (!this.ocrContexts || this.ocrContexts.length === 0) {
            return '';
        }

        const parts = [
            '≡ƒô╖ **OCR CONTEXT FROM MCP SELECTED FILES:**'
        ];

        this.ocrContexts.slice(0, 5).forEach(item => {
            parts.push(`\n### OCR: ${item.name}`);
            parts.push(`Method: ${item.method || 'ocr'}`);
            parts.push('```text');
            parts.push(item.text || '');
            parts.push('```');
        });

        return parts.join('\n');
    }

    async warmCacheForQuestion(question) {
        if (!this.enabled) {
            this.showNotification('ΓÜá∩╕Å H├úy bß║¡t MCP tr╞░ß╗¢c', 'warning');
            return;
        }

        if (!question) {
            this.showNotification('ΓÜá∩╕Å Nhß║¡p c├óu hß╗Åi tr╞░ß╗¢c khi warm cache', 'warning');
            return;
        }

        try {
            if (this.warmCacheBtn) this.warmCacheBtn.disabled = true;
            const response = await fetch('/api/mcp/warm-cache', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question,
                    force_refresh: false,
                    cache_ttl_seconds: 900,
                    limit: 20,
                    min_importance: 4,
                    max_chars: 12000
                })
            });

            const result = await response.json();
            if (result.success) {
                const domain = result.domain || 'general';
                this.showNotification(`≡ƒöÑ Warm cache xong (domain: ${domain})`, 'success');
            } else {
                this.showNotification(`ΓÜá∩╕Å Warm cache ch╞░a sß║╡n s├áng: ${result.error || 'unknown'}`, 'warning');
            }
        } catch (error) {
            console.error('MCP warm cache error:', error);
            this.showNotification('ΓÜá∩╕Å Kh├┤ng thß╗â warm cache l├║c n├áy', 'warning');
        } finally {
            if (this.warmCacheBtn) this.warmCacheBtn.disabled = false;
        }
    }

    async runOcrForSelectedFiles() {
        if (!this.enabled) {
            this.showNotification('ΓÜá∩╕Å H├úy bß║¡t MCP tr╞░ß╗¢c', 'warning');
            return;
        }

        if (!this.selectedFiles || this.selectedFiles.length === 0) {
            this.showNotification('ΓÜá∩╕Å Ch╞░a chß╗ìn file n├áo', 'warning');
            return;
        }

        const ocrExts = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.tiff', '.pdf', '.docx', '.doc', '.xlsx', '.xls']);
        const targets = this.selectedFiles.filter(f => ocrExts.has((f.extension || '').toLowerCase()));

        if (targets.length === 0) {
            this.showNotification('ΓÜá∩╕Å File ─æ├ú chß╗ìn kh├┤ng thuß╗Öc loß║íi OCR (ß║únh/PDF/docx/xlsx)', 'warning');
            return;
        }

        try {
            if (this.ocrBtn) this.ocrBtn.disabled = true;
            let successCount = 0;
            const newContexts = [];

            for (const file of targets.slice(0, 5)) {
                try {
                    const response = await fetch('/api/mcp/ocr-extract', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            path: file.path,
                            max_chars: 6000
                        })
                    });
                    const result = await response.json();
                    if (result.success && result.text) {
                        newContexts.push({
                            path: file.path,
                            name: file.name,
                            method: result.method || 'ocr',
                            text: result.text
                        });
                        successCount += 1;
                    }
                } catch (err) {
                    console.warn('OCR failed for file:', file.path, err);
                }
            }

            // Merge/replace by path
            const map = new Map(this.ocrContexts.map(c => [c.path, c]));
            newContexts.forEach(c => map.set(c.path, c));
            this.ocrContexts = Array.from(map.values()).slice(0, 10);

            if (successCount > 0) {
                this.showNotification(`Γ£à OCR xong ${successCount}/${targets.slice(0, 5).length} file. Sß║╜ ─æ╞░a v├áo context khi gß╗¡i chat.`, 'success');
            } else {
                this.showNotification('ΓÜá∩╕Å OCR kh├┤ng tr├¡ch xuß║Ñt ─æ╞░ß╗úc nß╗Öi dung', 'warning');
            }
        } finally {
            if (this.ocrBtn) this.ocrBtn.disabled = false;
        }
    }
    updateFolderList() {
        if (this.folders.length === 0) {
            this.folderList.style.display = 'none';
            return;
        }

        this.folderList.style.display = 'block';
        this.folderList.innerHTML = this.folders.map(folder => `
            <div class="mcp-folder-tag">
                <span>≡ƒôü ${this.truncatePath(folder)}</span>
                <span class="remove-folder" onclick="mcpController.removeFolder('${folder.replace(/\\/g, '\\\\')}')">
                    ├ù
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

    // ΓöÇΓöÇΓöÇ Source Tabs: folder picker, URL fetch, file upload ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    setupSourceTabs() {
        const tabs = document.querySelectorAll('#mcpTabFolder, #mcpTabUrl, #mcpTabUpload');
        const folderSource = document.getElementById('mcpFolderSource');
        const urlSource = document.getElementById('mcpUrlSource');
        const uploadSource = document.getElementById('mcpUploadSource');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                if (tab.disabled) return;
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                const source = tab.dataset.source;
                if (folderSource) folderSource.style.display = source === 'folder' ? 'block' : 'none';
                if (urlSource) urlSource.style.display = source === 'url' ? 'block' : 'none';
                if (uploadSource) uploadSource.style.display = source === 'upload' ? 'block' : 'none';
            });
        });

        this._setupLocalFolderPicker();
        this._setupUrlFetch();
        this._setupFileUpload();
    }

    _setupLocalFolderPicker() {
        const folderInput = document.getElementById('mcpFolderInput');
        const folderListEl = document.getElementById('mcpFolderList');
        if (!this.selectBtn || !folderInput) return;

        folderInput.addEventListener('change', async (e) => {
            const files = e.target.files;
            if (!files.length) return;

            const firstPath = files[0].webkitRelativePath || files[0].name;
            const folderName = firstPath.split('/')[0];

            this.selectBtn.innerHTML = 'ΓÅ│ ─Éang tß║úi...';
            this.selectBtn.disabled = true;

            try {
                const folderData = { name: folderName, files: [], content: '' };
                const textExtensions = ['.txt', '.md', '.py', '.js', '.ts', '.json', '.html', '.css', '.yaml', '.yml', '.xml', '.csv', '.sql', '.sh', '.bat'];

                for (const file of files) {
                    const ext = '.' + file.name.split('.').pop().toLowerCase();
                    if (textExtensions.includes(ext) && file.size < 100000) {
                        try {
                            const content = await file.text();
                            folderData.files.push({
                                path: file.webkitRelativePath,
                                name: file.name,
                                content: content.substring(0, 5000)
                            });
                        } catch (err) {
                            console.log(`[MCP] Skip unreadable file: ${file.name}`);
                        }
                    }
                }

                folderData.content = folderData.files.map(f =>
                    `--- ${f.path} ---\n${f.content}`
                ).join('\n\n');

                this.localFolders.push(folderData);

                if (folderListEl) {
                    folderListEl.style.display = 'block';
                    const tag = document.createElement('div');
                    tag.className = 'mcp-folder-tag';
                    tag.innerHTML = `≡ƒôü ${this._escapeHtml(folderName)} (${folderData.files.length} files) <button class="mcp-remove-btn" data-type="folder" data-name="${this._escapeHtml(folderName)}">├ù</button>`;
                    tag.querySelector('button').addEventListener('click', () => {
                        this.localFolders = this.localFolders.filter(f => f.name !== folderName);
                        tag.remove();
                        if (folderListEl.children.length === 0) folderListEl.style.display = 'none';
                        this.updateIndicator();
                    });
                    folderListEl.appendChild(tag);
                }

                this.updateFileListDisplay();
                this.updateIndicator();
            } catch (error) {
                console.error('[MCP] Folder read error:', error);
                alert('Lß╗ùi ─æß╗ìc folder');
            } finally {
                this.selectBtn.innerHTML = '≡ƒôü <span>Select Folder</span>';
                this.selectBtn.disabled = false;
                folderInput.value = '';
            }
        });
    }

    _setupUrlFetch() {
        const fetchUrlBtn = document.getElementById('mcpFetchUrlBtn');
        const urlInput = document.getElementById('mcpUrlInput');
        if (!fetchUrlBtn || !urlInput) return;

        fetchUrlBtn.addEventListener('click', async () => {
            const url = urlInput.value.trim();
            if (!url) return;

            fetchUrlBtn.disabled = true;
            fetchUrlBtn.innerHTML = 'ΓÅ│...';

            try {
                const response = await fetch('/api/mcp/fetch-url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url })
                });

                const data = await response.json();
                if (data.success) {
                    this.urls.push({ url, title: data.title, content: data.content });

                    const urlList = document.getElementById('mcpUrlList');
                    if (urlList) {
                        const tag = document.createElement('div');
                        tag.className = 'mcp-folder-tag';
                        const hostname = new URL(url.startsWith('http') ? url : 'https://' + url).hostname;
                        tag.innerHTML = `≡ƒîÉ ${this._escapeHtml(hostname)} <button class="mcp-remove-btn">├ù</button>`;
                        tag.querySelector('button').addEventListener('click', () => {
                            this.urls = this.urls.filter(u => u.url !== url);
                            tag.remove();
                            this.updateIndicator();
                        });
                        urlList.appendChild(tag);
                    }
                    urlInput.value = '';
                    this.updateIndicator();
                } else {
                    alert('Lß╗ùi fetch URL: ' + (data.error || 'Unknown error'));
                }
            } catch (error) {
                console.error('[MCP] URL fetch error:', error);
                alert('Lß╗ùi kß║┐t nß╗æi');
            } finally {
                fetchUrlBtn.disabled = false;
                fetchUrlBtn.innerHTML = '≡ƒöì Fetch';
            }
        });
    }

    _setupFileUpload() {
        const uploadBtn = document.getElementById('mcpUploadBtn');
        const fileUpload = document.getElementById('mcpFileUpload');
        if (!uploadBtn || !fileUpload) return;

        uploadBtn.addEventListener('click', () => fileUpload.click());

        fileUpload.addEventListener('change', async (e) => {
            const files = e.target.files;
            if (!files.length) return;

            const uploadList = document.getElementById('mcpUploadList');
            uploadBtn.innerHTML = 'ΓÅ│ ─Éang xß╗¡ l├╜...';
            uploadBtn.disabled = true;

            for (const file of files) {
                try {
                    const formData = new FormData();
                    formData.append('file', file);

                    const response = await fetch('/api/mcp/upload-file', {
                        method: 'POST',
                        body: formData
                    });

                    const data = await response.json();
                    if (data.success) {
                        this.uploads.push({ filename: file.name, content: data.content });

                        if (uploadList) {
                            const tag = document.createElement('div');
                            tag.className = 'mcp-folder-tag';
                            tag.innerHTML = `≡ƒôä ${this._escapeHtml(file.name)} <button class="mcp-remove-btn">├ù</button>`;
                            tag.querySelector('button').addEventListener('click', () => {
                                this.uploads = this.uploads.filter(u => u.filename !== file.name);
                                tag.remove();
                                this.updateIndicator();
                            });
                            uploadList.appendChild(tag);
                        }
                    }
                } catch (error) {
                    console.error(`[MCP] Upload error for ${file.name}:`, error);
                }
            }

            uploadBtn.innerHTML = '≡ƒôñ <span>Upload Files (OCR)</span>';
            uploadBtn.disabled = false;
            fileUpload.value = '';
            this.updateIndicator();
        });
    }

    // ΓöÇΓöÇΓöÇ Unified context (single source of truth) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    /**
     * Get the full MCP context string for injection into chat messages.
     * Combines all sources: local folders, URLs, uploads, and OCR.
     */
    getFullContextString() {
        if (!this.enabled) return '';

        const parts = [];

        this.localFolders.forEach(folder => {
            parts.push(`[Folder: ${folder.name}]\n${folder.content}`);
        });

        this.urls.forEach(url => {
            parts.push(`[URL: ${url.title}]\n${url.content}`);
        });

        this.uploads.forEach(upload => {
            parts.push(`[File: ${upload.filename}]\n${upload.content}`);
        });

        const ocrStr = this.getOcrContextString();
        if (ocrStr) {
            parts.push(ocrStr);
        }

        return parts.join('\n\n---\n\n');
    }

    /**
     * Update the MCP indicator badge showing total context count.
     */
    updateIndicator() {
        const count = this.localFolders.length + this.urls.length + this.uploads.length + this.selectedFiles.length;
        const badge = document.getElementById('selectedFileCount');
        const selectedFilesEl = document.getElementById('mcpSelectedFiles');

        if (badge) badge.textContent = count;
        if (selectedFilesEl) {
            selectedFilesEl.style.display = count > 0 ? 'block' : 'none';
        }
    }

    /**
     * Render the unified file browser showing all MCP sources.
     */
    updateFileListDisplay() {
        const fileListEl = document.getElementById('mcpFileList');
        if (!fileListEl) return;

        const allFiles = [];

        this.localFolders.forEach(folder => {
            folder.files.forEach(file => {
                allFiles.push({ type: 'folder', icon: '≡ƒôä', name: file.path });
            });
        });

        this.urls.forEach(url => {
            allFiles.push({ type: 'url', icon: '≡ƒîÉ', name: url.title || url.url });
        });

        this.uploads.forEach(upload => {
            allFiles.push({ type: 'upload', icon: '≡ƒôÄ', name: upload.filename });
        });

        if (allFiles.length === 0) {
            fileListEl.innerHTML = `<div class="mcp-empty-state">
                <p>≡ƒôé</p>
                <p style="font-size: 13px; font-weight: 600; color: #667eea;">No context loaded</p>
                <p style="font-size: 11px; color: #888;">Enable MCP and select a source</p>
            </div>`;
            return;
        }

        fileListEl.innerHTML = allFiles.map(f =>
            `<div class="mcp-file-item">${f.icon} ${f.name}</div>`
        ).join('');
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
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
    console.log('Γ£à MCP Controller initialized');
});
