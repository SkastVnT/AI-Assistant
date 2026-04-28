/**
 * File Handler Module
 * Handles file uploads, paste events, and file management
 */

import { csvPreview } from './csv-preview.js';

export class FileHandler {
    constructor() {
        this.uploadedFiles = []; // Temporary storage for current upload
        this.currentSessionFiles = []; // Files for current chat session
    }

    /**
     * Setup file input listener
     */
    setupFileInput(fileInput, onFilesChange) {
        if (!fileInput) {
            console.error('[FileHandler] fileInput element not found!');
            return;
        }

        // Add change listener directly (no clone needed)
        fileInput.addEventListener('change', function(event) {
            if (event.target.files && event.target.files.length > 0) {
                const newFiles = Array.from(event.target.files);
                if (onFilesChange) {
                    onFilesChange(newFiles);
                }
            }
        });
        
        // Return the same element reference
        return fileInput;
    }

    /**
     * Setup paste event for files
     */
    setupPasteHandler(element, onFilesChange) {
        if (!element) return;

        element.addEventListener('paste', async (e) => {
            const items = e.clipboardData.items;
            const newFiles = [];
            
            for (let item of items) {
                // Handle text paste (default behavior)
                if (item.type === 'text/plain') {
                    continue;
                }
                
                // Handle file paste
                if (item.kind === 'file') {
                    e.preventDefault();
                    const file = item.getAsFile();
                    if (file) {
                        newFiles.push(file);
                    }
                }
            }
            
            // Call callback with new files only
            if (newFiles.length > 0 && onFilesChange) {
                onFilesChange(newFiles);
            }
        });
    }

    /**
     * Render file list UI
     */
    renderFileList(fileListContainer) {
        if (!fileListContainer) return;

        fileListContainer.innerHTML = '';
        this.uploadedFiles.forEach((file, index) => {
            const tag = document.createElement('div');
            tag.className = 'file-tag';
            tag.innerHTML = `
                📄 ${this.escapeHtml(file.name)}
                <span class="file-tag-remove" data-index="${index}">✕</span>
            `;
            fileListContainer.appendChild(tag);
        });

        // Attach remove listeners
        fileListContainer.querySelectorAll('.file-tag-remove').forEach(span => {
            span.addEventListener('click', () => {
                const index = parseInt(span.dataset.index);
                this.removeFile(index);
                this.renderFileList(fileListContainer);
            });
        });
    }

    /**
     * Remove file by index
     */
    removeFile(index) {
        this.uploadedFiles.splice(index, 1);
    }

    /**
     * Get all uploaded files
     */
    getFiles() {
        return this.uploadedFiles;
    }

    /**
     * Clear all files
     */
    clearFiles() {
        this.uploadedFiles = [];
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
     * Read file as base64
     */
    async readFileAsBase64(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            reader.readAsDataURL(file);
        });
    }

    /**
     * Validate file type
     */
    isValidFileType(file, allowedTypes = ['image/*', 'text/*', 'application/pdf']) {
        return allowedTypes.some(type => {
            if (type.endsWith('/*')) {
                const category = type.split('/')[0];
                return file.type.startsWith(category + '/');
            }
            return file.type === type;
        });
    }

    /**
     * Get file size in human readable format
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    /**
     * Compress image to reduce storage size
     */
    async compressImage(base64String, quality = 0.6) {
        return new Promise((resolve) => {
            if (!base64String || !base64String.includes('data:image')) {
                resolve(base64String);
                return;
            }
            
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                // Resize to max 1200px
                const maxSize = 1200;
                let width = img.width;
                let height = img.height;
                
                if (width > maxSize || height > maxSize) {
                    if (width > height) {
                        height = (height / width) * maxSize;
                        width = maxSize;
                    } else {
                        width = (width / height) * maxSize;
                        height = maxSize;
                    }
                }
                
                canvas.width = width;
                canvas.height = height;
                ctx.drawImage(img, 0, 0, width, height);
                
                // Convert to JPEG with quality
                const compressed = canvas.toDataURL('image/jpeg', quality);
                console.log(`[COMPRESS] Original: ${(base64String.length / 1024).toFixed(0)}KB → Compressed: ${(compressed.length / 1024).toFixed(0)}KB`);
                resolve(compressed);
            };
            img.onerror = () => resolve(base64String);
            img.src = base64String;
        });
    }

    /**
     * Process and save file to current session
     */
    async processFile(file) {
        console.log('[FileHandler] Processing file:', file.name, 'Size:', this.formatFileSize(file.size), 'Type:', file.type);
        
        // Validate file size - max 50MB
        const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
        if (file.size > MAX_FILE_SIZE) {
            throw new Error(`File quá lớn! Tối đa 50MB. File này: ${this.formatFileSize(file.size)}`);
        }
        
        const fileData = {
            name: file.name,
            type: file.type,
            size: file.size,
            uploadedAt: new Date().toISOString()
        };

        try {
            // Read file content based on type
            if (file.type.startsWith('image/')) {
                console.log('[FileHandler] Processing as image...');
                // For images, compress heavily to reduce storage
                const base64 = await this.readFileAsBase64(file);
                console.log('[FileHandler] Image read, compressing...');
                fileData.content = await this.compressImage(base64, 0.6); // Balanced quality for AI vision
                fileData.preview = fileData.content;
                console.log('[FileHandler] Image compressed successfully');
            } else if (file.name.endsWith('.csv') || file.name.endsWith('.tsv')) {
                console.log('[FileHandler] Processing as tabular file...');
                // For CSV/TSV: read as text, parse into table for inline preview,
                // and keep raw text so AI can also read the content.
                fileData.content = await this.readFileAsText(file);
                fileData.tableData = csvPreview.parse(fileData.content, file.name);
                console.log(`[FileHandler] Table parsed: ${fileData.tableData.rows.length} rows, ${fileData.tableData.headers.length} cols`);
            } else if (file.type.startsWith('text/') || 
                       file.type === 'application/json' ||
                       file.name.endsWith('.py') || 
                       file.name.endsWith('.js') || 
                       file.name.endsWith('.ts') || 
                       file.name.endsWith('.tsx') || 
                       file.name.endsWith('.jsx') || 
                       file.name.endsWith('.html') || 
                       file.name.endsWith('.css') ||
                       file.name.endsWith('.md') ||
                       file.name.endsWith('.xml') ||
                       file.name.endsWith('.yaml') ||
                       file.name.endsWith('.yml') ||
                       file.name.endsWith('.sql') ||
                       file.name.endsWith('.sh') ||
                       file.name.endsWith('.bat') ||
                       file.name.endsWith('.log') ||
                       file.name.endsWith('.env') ||
                       file.name.endsWith('.txt')) {
                console.log('[FileHandler] Processing as text file...');
                // For text files, store as text
                fileData.content = await this.readFileAsText(file);
                console.log('[FileHandler] Text file read successfully');
            } else if (file.type === 'application/pdf' || 
                       file.type === 'application/msword' || 
                       file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
                       file.name.endsWith('.docx') ||
                       file.name.endsWith('.doc') ||
                       file.name.endsWith('.xlsx') ||
                       file.name.endsWith('.xls')) {
                console.log('[FileHandler] Processing as document — extracting text via backend...');
                const base64 = await this.readFileAsBase64(file);
                try {
                    const resp = await fetch('/api/extract-file-text', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ file_b64: base64, filename: file.name })
                    });
                    const result = await resp.json();
                    if (result.success && result.text) {
                        fileData.content = result.text;
                        fileData.extractedByOCR = true;
                        console.log('[FileHandler] Document text extracted successfully');
                    } else {
                        // Fallback: store note so AI knows a file was attached
                        fileData.content = `[Document: ${file.name} — text extraction failed: ${result.error || 'unknown error'}]`;
                        console.warn('[FileHandler] Extraction failed:', result.error);
                    }
                } catch (e) {
                    fileData.content = `[Document: ${file.name} — could not extract text]`;
                    console.warn('[FileHandler] Extraction request error:', e);
                }
            } else {
                console.log('[FileHandler] Unknown file type, reading as base64...');
                // Unknown types, try base64
                fileData.content = await this.readFileAsBase64(file);
            }
            
            console.log('[FileHandler] File processed successfully:', file.name);
            return fileData;
        } catch (error) {
            console.error('[FileHandler] Error processing file:', error);
            throw new Error(`Không thể đọc file: ${error.message}`);
        }
    }

    /**
     * Read file as text
     */
    async readFileAsText(file) {
        return new Promise((resolve, reject) => {
            const reader = new FileReader();
            reader.onload = (e) => resolve(e.target.result);
            reader.onerror = (e) => reject(e);
            reader.readAsText(file);
        });
    }

    /**
     * Add files to current session
     */
    async addFilesToSession(files) {
        for (let file of files) {
            const fileData = await this.processFile(file);
            this.currentSessionFiles.push(fileData);
        }
    }

    /**
     * Load files from session data
     */
    loadSessionFiles(files) {
        this.currentSessionFiles = files || [];
    }

    /**
     * Get current session files
     */
    getSessionFiles() {
        return this.currentSessionFiles;
    }

    /**
     * Remove file from session
     */
    removeSessionFile(index) {
        this.currentSessionFiles.splice(index, 1);
    }

    /**
     * Clear session files
     */
    clearSessionFiles() {
        this.currentSessionFiles = [];
    }

    /**
     * Render session files as ChatGPT-style attachment cards
     */
    renderSessionFiles(container) {
        if (!container) return;

        if (this.currentSessionFiles.length === 0) {
            container.innerHTML = '';
            container.style.display = 'none';
            return;
        }

        container.style.display = 'grid';
        container.innerHTML = this.currentSessionFiles.map((file, index) => {
            const icon = this.getFileIcon(file.type, file.name);
            const sizeFormatted = this.formatFileSize(file.size);
            const isTable = !!file.tableData;

            const metaText = isTable
                ? `${file.tableData.rows.length} hàng · ${file.tableData.headers.length} cột`
                : sizeFormatted;

            const iconOrPreview = file.preview
                ? `<div class="file-attachment-preview"><img src="${file.preview}" alt="${this.escapeHtml(file.name)}"></div>`
                : isTable
                    ? `<div class="file-attachment-icon file-attachment-icon--table">📊</div>`
                    : `<div class="file-attachment-icon">${icon}</div>`;

            return `
                <div class="file-attachment-card${isTable ? ' file-attachment-card--table' : ''}" data-index="${index}" title="${isTable ? 'Nhấn để xem bảng' : this.escapeHtml(file.name)}">
                    ${iconOrPreview}
                    <div class="file-attachment-info">
                        <div class="file-attachment-name" title="${this.escapeHtml(file.name)}">
                            ${this.escapeHtml(file.name)}
                        </div>
                        <div class="file-attachment-meta">
                            ${metaText}
                        </div>
                    </div>
                    ${isTable ? '<span class="file-table-badge">Xem bảng</span>' : ''}
                    <button class="file-attachment-remove" data-index="${index}" title="Xóa file">
                        ✕
                    </button>
                </div>
            `;
        }).join('');

        // Attach remove listeners
        container.querySelectorAll('.file-attachment-remove').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const index = parseInt(btn.dataset.index);
                this.removeSessionFile(index);
                this.renderSessionFiles(container);
                // Trigger save callback if provided
                if (this.onFilesChange) {
                    this.onFilesChange();
                }
            });
        });

        // Make cards clickable to preview
        container.querySelectorAll('.file-attachment-card').forEach(card => {
            card.addEventListener('click', () => {
                const index = parseInt(card.dataset.index);
                this.previewFile(index);
            });
        });
    }

    /**
     * Get file icon emoji based on type
     */
    getFileIcon(type, name) {
        if (type.startsWith('image/')) return '🖼️';
        if (type.startsWith('video/')) return '🎥';
        if (type.startsWith('audio/')) return '🎵';
        if (type === 'application/pdf') return '📕';
        if (type === 'application/msword' || type.includes('wordprocessing')) return '📘';
        if (type.includes('spreadsheet') || name.endsWith('.xlsx') || name.endsWith('.xls')) return '📊';
        if (type === 'application/json') return '📋';
        if (name.endsWith('.py')) return '🐍';
        if (name.endsWith('.js')) return '📜';
        if (name.endsWith('.html')) return '🌐';
        if (name.endsWith('.css')) return '🎨';
        if (type.startsWith('text/')) return '📄';
        return '📎';
    }

    /**
     * Preview file (for future implementation)
     */
    previewFile(index) {
        this.previewFileData(this.currentSessionFiles[index]);
    }

    /**
     * Preview any file data object (works for both session files and staged files)
     */
    previewFileData(file) {
        if (!file) return;
        if (file.tableData && file.tableData.headers.length > 0) {
            // Interactive table viewer (CSV / TSV / XLSX)
            csvPreview.show(file.tableData, file.name);
        } else if (file.preview || (file.type && file.type.startsWith('image/'))) {
            // Image preview lightbox
            const src = file.preview || file.content;
            if (!src) return;
            if (window.openImagePreview) {
                const img = new Image();
                img.src = src;
                window.openImagePreview(img);
            }
        } else if (file.content && !file.content.startsWith('data:')) {
            // Text / code viewer modal
            this._showTextPreviewModal(file.content, file.name);
        } else {
            this._showUnsupportedModal(file.name);
        }
    }

    /** Build and show a text/code preview overlay */
    _showTextPreviewModal(content, filename) {
        let overlay = document.getElementById('fileTextPreviewOverlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.id = 'fileTextPreviewOverlay';
            overlay.className = 'file-text-preview-overlay';
            overlay.innerHTML = `
                <div class="file-text-preview-panel">
                    <div class="file-text-preview-header">
                        <span class="file-text-preview-filename"></span>
                        <button class="file-text-preview-close" title="Đóng (Esc)">
                            <svg viewBox="0 0 24 24" width="18" height="18" stroke="currentColor" stroke-width="2" fill="none"><path d="M18 6 6 18M6 6l12 12"/></svg>
                        </button>
                    </div>
                    <div class="file-text-preview-body">
                        <pre class="file-text-preview-content"></pre>
                    </div>
                </div>
            `;
            overlay.querySelector('.file-text-preview-close').addEventListener('click', () => this._closeTextPreviewModal());
            overlay.addEventListener('click', e => { if (e.target === overlay) this._closeTextPreviewModal(); });
            document.addEventListener('keydown', e => {
                if (e.key === 'Escape' && overlay.classList.contains('open')) this._closeTextPreviewModal();
            });
            document.body.appendChild(overlay);
        }
        overlay.querySelector('.file-text-preview-filename').textContent = filename || '';
        overlay.querySelector('.file-text-preview-content').textContent = content;
        overlay.classList.add('open');
        document.body.style.overflow = 'hidden';
    }

    _closeTextPreviewModal() {
        const overlay = document.getElementById('fileTextPreviewOverlay');
        if (overlay) overlay.classList.remove('open');
        document.body.style.overflow = '';
    }

    /** Notify user that preview is not supported for this file type */
    _showUnsupportedModal(filename) {
        const ext = (filename || '').split('.').pop().toUpperCase();
        const msg = ext
            ? `Không hỗ trợ xem trước file .${ext}`
            : 'Không hỗ trợ xem trước file này';
        // Re-use a small toast/snackbar if available, otherwise fallback to alert
        if (window.showToast) {
            window.showToast(msg, 'info');
        } else {
            alert(msg);
        }
    }

    /**
     * Set callback for file changes
     */
    setOnFilesChange(callback) {
        this.onFilesChange = callback;
    }
}
