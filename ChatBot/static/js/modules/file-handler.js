/**
 * File Handler Module
 * Handles file uploads, paste events, and file management
 */

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

        console.log('[FileHandler] Setting up file input listener');
        console.log('[FileHandler] Element:', fileInput);
        console.log('[FileHandler] Element ID:', fileInput.id);
        console.log('[FileHandler] Element tag:', fileInput.tagName);
        console.log('[FileHandler] Element type:', fileInput.type);
        
        // Remove any existing listeners first
        const oldInput = fileInput.cloneNode(true);
        fileInput.parentNode.replaceChild(oldInput, fileInput);
        
        // Add new listener with addEventListener (more reliable)
        oldInput.addEventListener('change', function(event) {
            console.log('[FileHandler] ===== FILE INPUT CHANGED =====');
            console.log('[FileHandler] Event:', event);
            console.log('[FileHandler] Target:', event.target);
            console.log('[FileHandler] Files:', event.target.files);
            console.log('[FileHandler] Files count:', event.target.files.length);
            
            if (event.target.files && event.target.files.length > 0) {
                const newFiles = Array.from(event.target.files);
                console.log('[FileHandler] New files array:', newFiles);
                
                if (onFilesChange) {
                    console.log('[FileHandler] Calling onFilesChange callback with', newFiles.length, 'files');
                    onFilesChange(newFiles);
                } else {
                    console.error('[FileHandler] No onFilesChange callback provided!');
                }
            } else {
                console.warn('[FileHandler] No files selected');
            }
        });
        
        console.log('[FileHandler] File input listener setup complete');
        
        // Return the new element reference
        return oldInput;
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
                fileData.content = await this.compressImage(base64, 0.3); // Aggressive compression
                fileData.preview = fileData.content;
                console.log('[FileHandler] Image compressed successfully');
            } else if (file.type.startsWith('text/') || 
                       file.type === 'application/json' ||
                       file.name.endsWith('.py') || 
                       file.name.endsWith('.js') || 
                       file.name.endsWith('.html') || 
                       file.name.endsWith('.css')) {
                console.log('[FileHandler] Processing as text file...');
                // For text files, store as text
                fileData.content = await this.readFileAsText(file);
                console.log('[FileHandler] Text file read successfully');
            } else if (file.type === 'application/pdf' || 
                       file.type === 'application/msword' || 
                       file.type === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' ||
                       file.name.endsWith('.xlsx') ||
                       file.name.endsWith('.csv')) {
                console.log('[FileHandler] Processing as document...');
                // For documents, store base64 and let backend handle
                fileData.content = await this.readFileAsBase64(file);
                console.log('[FileHandler] Document read successfully');
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
            
            return `
                <div class="file-attachment-card" data-index="${index}">
                    ${file.preview ? `
                        <div class="file-attachment-preview">
                            <img src="${file.preview}" alt="${this.escapeHtml(file.name)}">
                        </div>
                    ` : `
                        <div class="file-attachment-icon">
                            ${icon}
                        </div>
                    `}
                    <div class="file-attachment-info">
                        <div class="file-attachment-name" title="${this.escapeHtml(file.name)}">
                            ${this.escapeHtml(file.name)}
                        </div>
                        <div class="file-attachment-meta">
                            ${sizeFormatted}
                        </div>
                    </div>
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
        const file = this.currentSessionFiles[index];
        if (file.preview) {
            // Open image preview modal if exists
            if (window.openImagePreview) {
                const img = new Image();
                img.src = file.preview;
                window.openImagePreview(img);
            }
        } else if (file.content && !file.content.startsWith('data:')) {
            // Show text content in a modal or console
            console.log('File content:', file.content.substring(0, 500) + '...');
        }
    }

    /**
     * Set callback for file changes
     */
    setOnFilesChange(callback) {
        this.onFilesChange = callback;
    }
}
