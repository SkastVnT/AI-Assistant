/**
 * SPEECH2TEXT MODERN UI - MAIN APPLICATION
 * ChatBot-style interface with WebSocket real-time updates
 */

class Speech2TextApp {
    constructor() {
        // WebSocket connection
        this.socket = null;
        
        // State
        this.currentSessionId = null;
        this.sessions = [];
        this.selectedFile = null;
        this.isProcessing = false;
        this.currentResults = null;
        
        // Elements
        this.elements = {};
        
        // Storage limit (500MB)
        this.STORAGE_LIMIT = 500 * 1024 * 1024;
    }

    /**
     * Initialize application
     */
    async init() {
        console.log('[App] Initializing Speech2Text Modern UI...');
        
        // Get DOM elements
        this.initElements();
        
        // Setup WebSocket
        this.initWebSocket();
        
        // Load sessions
        this.loadSessions();
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Init dark mode
        this.initDarkMode();
        
        // Update storage info
        this.updateStorageInfo();
        
        console.log('[App] Initialization complete!');
    }

    /**
     * Initialize DOM elements
     */
    initElements() {
        this.elements = {
            // Sidebar
            sidebar: document.getElementById('sidebar'),
            sidebarToggle: document.getElementById('sidebarToggle'),
            sessionList: document.getElementById('sessionList'),
            newSessionBtn: document.getElementById('newSessionBtn'),
            cleanupBtn: document.getElementById('cleanupBtn'),
            
            // Storage
            storageStatus: document.getElementById('storageStatus'),
            storageProgressBar: document.getElementById('storageProgressBar'),
            storagePercentage: document.getElementById('storagePercentage'),
            
            // Controls
            modelSelect: document.getElementById('modelSelect'),
            enhancementSelect: document.getElementById('enhancementSelect'),
            diarizationCheck: document.getElementById('diarizationCheck'),
            exportBtn: document.getElementById('exportBtn'),
            darkModeBtn: document.getElementById('darkModeBtn'),
            clearResultsBtn: document.getElementById('clearResultsBtn'),
            
            // Results
            resultsContainer: document.getElementById('resultsContainer'),
            
            // Progress
            progressSection: document.getElementById('progressSection'),
            progressTitle: document.getElementById('progressTitle'),
            progressPercent: document.getElementById('progressPercent'),
            progressBar: document.getElementById('progressBar'),
            progressMessage: document.getElementById('progressMessage'),
            cancelBtn: document.getElementById('cancelBtn'),
            
            // Upload
            uploadArea: document.getElementById('uploadArea'),
            audioInput: document.getElementById('audioInput'),
            fileInfo: document.getElementById('fileInfo'),
            fileName: document.getElementById('fileName'),
            fileSize: document.getElementById('fileSize'),
            removeFileBtn: document.getElementById('removeFileBtn'),
            processBtn: document.getElementById('processBtn'),
            
            // Modal
            exportModal: document.getElementById('exportModal')
        };
    }

    /**
     * Initialize WebSocket connection
     */
    initWebSocket() {
        console.log('[WebSocket] Connecting to server...');
        
        this.socket = io('http://localhost:5001', {
            transports: ['websocket', 'polling']
        });
        
        this.socket.on('connect', () => {
            console.log('[WebSocket] Connected to server');
        });
        
        this.socket.on('disconnect', () => {
            console.log('[WebSocket] Disconnected from server');
        });
        
        this.socket.on('progress', (data) => {
            this.handleProgress(data);
        });
        
        this.socket.on('complete', (data) => {
            this.handleComplete(data);
        });
        
        this.socket.on('error', (data) => {
            this.handleError(data);
        });
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        // Sidebar toggle
        this.elements.sidebarToggle.addEventListener('click', () => {
            this.elements.sidebar.classList.toggle('open');
        });
        
        // New session
        this.elements.newSessionBtn.addEventListener('click', () => {
            this.createNewSession();
        });
        
        // Cleanup storage
        this.elements.cleanupBtn.addEventListener('click', () => {
            this.cleanupStorage();
        });
        
        // Dark mode toggle
        this.elements.darkModeBtn.addEventListener('click', () => {
            this.toggleDarkMode();
        });
        
        // Clear results
        this.elements.clearResultsBtn.addEventListener('click', () => {
            this.clearResults();
        });
        
        // Export button
        this.elements.exportBtn.addEventListener('click', () => {
            this.showExportModal();
        });
        
        // Cancel processing
        this.elements.cancelBtn.addEventListener('click', () => {
            this.cancelProcessing();
        });
        
        // Upload area click
        this.elements.uploadArea.addEventListener('click', () => {
            if (!this.isProcessing) {
                this.elements.audioInput.click();
            }
        });
        
        // File input change
        this.elements.audioInput.addEventListener('change', (e) => {
            this.handleFileSelect(e.target.files[0]);
        });
        
        // Remove file
        this.elements.removeFileBtn.addEventListener('click', () => {
            this.removeFile();
        });
        
        // Process button
        this.elements.processBtn.addEventListener('click', () => {
            this.processAudio();
        });
        
        // Drag and drop
        this.elements.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.elements.uploadArea.classList.add('drag-over');
        });
        
        this.elements.uploadArea.addEventListener('dragleave', () => {
            this.elements.uploadArea.classList.remove('drag-over');
        });
        
        this.elements.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.elements.uploadArea.classList.remove('drag-over');
            
            if (!this.isProcessing && e.dataTransfer.files.length > 0) {
                this.handleFileSelect(e.dataTransfer.files[0]);
            }
        });
    }

    /**
     * Handle file selection
     */
    handleFileSelect(file) {
        if (!file) return;
        
        // Validate file type
        const allowedTypes = ['audio/mpeg', 'audio/wav', 'audio/x-m4a', 'audio/flac', 'audio/ogg'];
        const allowedExtensions = ['.mp3', '.wav', '.m4a', '.flac', '.ogg'];
        
        const extension = '.' + file.name.split('.').pop().toLowerCase();
        
        if (!allowedTypes.includes(file.type) && !allowedExtensions.includes(extension)) {
            alert('❌ File không hợp lệ! Chỉ hỗ trợ: MP3, WAV, M4A, FLAC, OGG');
            return;
        }
        
        // Validate file size (500MB)
        if (file.size > 500 * 1024 * 1024) {
            alert('❌ File quá lớn! Kích thước tối đa: 500MB');
            return;
        }
        
        this.selectedFile = file;
        
        // Show file info
        this.elements.fileName.textContent = file.name;
        this.elements.fileSize.textContent = this.formatFileSize(file.size);
        this.elements.fileInfo.style.display = 'flex';
        
        // Enable process button
        this.elements.processBtn.disabled = false;
        
        // Hide upload area
        this.elements.uploadArea.style.display = 'none';
        
        console.log('[File] Selected:', file.name, this.formatFileSize(file.size));
    }

    /**
     * Remove selected file
     */
    removeFile() {
        this.selectedFile = null;
        this.elements.fileInfo.style.display = 'none';
        this.elements.uploadArea.style.display = 'block';
        this.elements.processBtn.disabled = true;
        this.elements.audioInput.value = '';
    }

    /**
     * Process audio file
     */
    async processAudio() {
        if (!this.selectedFile || this.isProcessing) return;
        
        this.isProcessing = true;
        
        // Generate session ID
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
        this.currentSessionId = `session_${timestamp}`;
        
        // Show progress
        this.elements.progressSection.style.display = 'block';
        this.elements.processBtn.disabled = true;
        
        // Prepare form data
        const formData = new FormData();
        formData.append('audio', this.selectedFile);
        formData.append('session_id', this.currentSessionId);
        formData.append('model', this.elements.modelSelect.value);
        formData.append('enhancement', this.elements.enhancementSelect.value);
        formData.append('diarization', this.elements.diarizationCheck.checked);
        
        try {
            console.log('[Process] Starting audio processing...');
            
            const response = await fetch('http://localhost:5001/api/process', {
                method: 'POST',
                body: formData
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const data = await response.json();
            console.log('[Process] Upload successful:', data);
            
            // Add to sessions
            this.addSession({
                id: this.currentSessionId,
                name: this.selectedFile.name,
                timestamp: new Date(),
                status: 'processing'
            });
            
        } catch (error) {
            console.error('[Process] Error:', error);
            alert('❌ Lỗi upload file: ' + error.message);
            this.isProcessing = false;
            this.elements.progressSection.style.display = 'none';
            this.elements.processBtn.disabled = false;
        }
    }

    /**
     * Handle progress update from WebSocket
     */
    handleProgress(data) {
        console.log('[Progress]', data);
        
        const { step, progress, message } = data;
        
        // Update UI
        this.elements.progressTitle.textContent = this.getStepTitle(step);
        this.elements.progressPercent.textContent = `${progress}%`;
        this.elements.progressBar.style.width = `${progress}%`;
        this.elements.progressMessage.textContent = message;
    }

    /**
     * Handle completion from WebSocket
     */
    handleComplete(data) {
        console.log('[Complete]', data);
        
        this.isProcessing = false;
        this.currentResults = data;
        
        // Hide progress
        this.elements.progressSection.style.display = 'none';
        
        // Show results
        this.displayResults(data);
        
        // Enable export
        this.elements.exportBtn.disabled = false;
        
        // Update session
        this.updateSessionStatus(this.currentSessionId, 'completed');
        
        // Clear file selection
        this.removeFile();
        
        // Show notification
        this.showNotification('✅ Xử lý hoàn tất!', 'success');
    }

    /**
     * Handle error from WebSocket
     */
    handleError(data) {
        console.error('[Error]', data);
        
        this.isProcessing = false;
        this.elements.progressSection.style.display = 'none';
        this.elements.processBtn.disabled = false;
        
        alert('❌ Lỗi xử lý: ' + data.message);
        
        // Update session
        if (this.currentSessionId) {
            this.updateSessionStatus(this.currentSessionId, 'failed');
        }
    }

    /**
     * Cancel processing
     */
    cancelProcessing() {
        if (!this.isProcessing) return;
        
        console.log('[Cancel] Cancelling processing...');
        
        this.socket.emit('cancel');
        this.isProcessing = false;
        this.elements.progressSection.style.display = 'none';
        this.elements.processBtn.disabled = false;
        
        // Update session
        if (this.currentSessionId) {
            this.updateSessionStatus(this.currentSessionId, 'cancelled');
        }
        
        this.showNotification('⏹️ Đã hủy xử lý', 'warning');
    }

    /**
     * Display results in UI
     */
    displayResults(data) {
        const container = this.elements.resultsContainer;
        container.innerHTML = '';
        
        // Timeline Transcript Card
        const timelineCard = this.createResultCard({
            title: '📝 Timeline Transcript',
            icon: '⏱️',
            content: data.timeline,
            stats: [
                { label: 'Speakers', value: data.num_speakers },
                { label: 'Segments', value: data.num_segments },
                { label: 'Duration', value: `${data.duration.toFixed(1)}s` }
            ]
        });
        container.appendChild(timelineCard);
        
        // Enhanced Transcript Card
        if (data.enhanced && data.enhanced !== data.timeline) {
            const enhancedCard = this.createResultCard({
                title: '✨ Enhanced Transcript',
                icon: '🤖',
                content: data.enhanced,
                stats: [
                    { label: 'Model', value: 'Qwen' },
                    { label: 'Processing Time', value: `${data.processingTime.toFixed(1)}s` }
                ]
            });
            container.appendChild(enhancedCard);
        }
        
        // Processing Info Card
        const infoCard = this.createInfoCard(data);
        container.appendChild(infoCard);
    }

    /**
     * Create result card
     */
    createResultCard({ title, icon, content, stats }) {
        const card = document.createElement('div');
        card.className = 'result-card';
        
        const header = document.createElement('div');
        header.className = 'result-header';
        
        const titleDiv = document.createElement('div');
        titleDiv.className = 'result-title';
        titleDiv.innerHTML = `<span>${icon}</span> ${title}`;
        
        const actions = document.createElement('div');
        actions.className = 'result-actions';
        
        const copyBtn = document.createElement('button');
        copyBtn.className = 'result-btn';
        copyBtn.textContent = '📋 Copy';
        copyBtn.onclick = () => this.copyToClipboard(content);
        
        actions.appendChild(copyBtn);
        header.appendChild(titleDiv);
        header.appendChild(actions);
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'result-content';
        contentDiv.textContent = content;
        
        card.appendChild(header);
        card.appendChild(contentDiv);
        
        if (stats && stats.length > 0) {
            const statsDiv = document.createElement('div');
            statsDiv.className = 'result-stats';
            
            stats.forEach(stat => {
                const statItem = document.createElement('div');
                statItem.className = 'stat-item';
                statItem.innerHTML = `
                    ${stat.label}: <span class="stat-value">${stat.value}</span>
                `;
                statsDiv.appendChild(statItem);
            });
            
            card.appendChild(statsDiv);
        }
        
        return card;
    }

    /**
     * Create info card
     */
    createInfoCard(data) {
        const card = document.createElement('div');
        card.className = 'result-card';
        card.innerHTML = `
            <div class="result-header">
                <div class="result-title">
                    <span>ℹ️</span> Processing Information
                </div>
            </div>
            <div class="result-stats">
                <div class="stat-item">Session: <span class="stat-value">${data.session_id}</span></div>
                <div class="stat-item">Processing Time: <span class="stat-value">${data.processingTime.toFixed(2)}s</span></div>
                <div class="stat-item">Prompt Version: <span class="stat-value">${data.promptVersion}</span></div>
            </div>
        `;
        return card;
    }

    /**
     * Copy text to clipboard
     */
    async copyToClipboard(text) {
        try {
            await navigator.clipboard.writeText(text);
            this.showNotification('📋 Đã copy vào clipboard!', 'success');
        } catch (error) {
            console.error('[Clipboard] Error:', error);
            alert('❌ Không thể copy: ' + error.message);
        }
    }

    /**
     * Get step title for progress
     */
    getStepTitle(step) {
        const titles = {
            'preprocessing': '🔄 Preprocessing',
            'diarization': '🎭 Speaker Diarization',
            'segmentation': '✂️ Segmentation',
            'whisper': '🎤 Whisper Transcription',
            'phowhisper': '🇻🇳 PhoWhisper Transcription',
            'timeline': '⏱️ Building Timeline',
            'qwen': '🤖 AI Enhancement',
            'complete': '✅ Complete',
            'error': '❌ Error'
        };
        return titles[step] || step;
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
     * Show notification
     */
    showNotification(message, type = 'info') {
        // Simple alert for now - can be enhanced with toast notifications
        console.log(`[Notification] ${type.toUpperCase()}: ${message}`);
        
        // You can implement a toast notification here
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.textContent = message;
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            background: ${type === 'success' ? '#4caf50' : type === 'error' ? '#ff5252' : '#2196f3'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
            z-index: 10000;
            animation: slideInRight 0.3s ease;
        `;
        
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.style.animation = 'slideOutRight 0.3s ease';
            setTimeout(() => notification.remove(), 300);
        }, 3000);
    }

    /**
     * Session Management
     */
    loadSessions() {
        const saved = localStorage.getItem('s2t_sessions');
        this.sessions = saved ? JSON.parse(saved) : [];
        this.renderSessions();
    }

    saveSessions() {
        localStorage.setItem('s2t_sessions', JSON.stringify(this.sessions));
    }

    addSession(session) {
        this.sessions.unshift(session);
        this.saveSessions();
        this.renderSessions();
        this.updateStorageInfo();
    }

    updateSessionStatus(sessionId, status) {
        const session = this.sessions.find(s => s.id === sessionId);
        if (session) {
            session.status = status;
            this.saveSessions();
            this.renderSessions();
        }
    }

    deleteSession(sessionId) {
        if (!confirm('Bạn có chắc muốn xóa phiên này?')) return;
        
        this.sessions = this.sessions.filter(s => s.id !== sessionId);
        this.saveSessions();
        this.renderSessions();
        this.updateStorageInfo();
        
        if (this.currentSessionId === sessionId) {
            this.clearResults();
        }
    }

    createNewSession() {
        this.currentSessionId = null;
        this.currentResults = null;
        this.clearResults();
        this.removeFile();
        this.showNotification('✨ Đã tạo phiên mới', 'success');
    }

    renderSessions() {
        const container = this.elements.sessionList;
        container.innerHTML = '';
        
        if (this.sessions.length === 0) {
            container.innerHTML = '<div style="padding: 20px; text-align: center; color: var(--text-secondary); font-size: 13px;">Chưa có phiên nào</div>';
            return;
        }
        
        this.sessions.forEach(session => {
            const item = document.createElement('div');
            item.className = 'session-item';
            if (session.id === this.currentSessionId) {
                item.classList.add('active');
            }
            
            const statusEmoji = {
                'processing': '⏳',
                'completed': '✅',
                'failed': '❌',
                'cancelled': '⏹️'
            }[session.status] || '📝';
            
            item.innerHTML = `
                <div class="session-name">${statusEmoji} ${session.name}</div>
                <div class="session-info">
                    <span>${new Date(session.timestamp).toLocaleString('vi-VN')}</span>
                </div>
                <button class="session-delete" data-id="${session.id}">🗑️</button>
            `;
            
            item.onclick = (e) => {
                if (!e.target.classList.contains('session-delete')) {
                    this.loadSession(session.id);
                }
            };
            
            item.querySelector('.session-delete').onclick = (e) => {
                e.stopPropagation();
                this.deleteSession(session.id);
            };
            
            container.appendChild(item);
        });
    }

    loadSession(sessionId) {
        // Load session results from server
        console.log('[Session] Loading session:', sessionId);
        this.currentSessionId = sessionId;
        this.renderSessions();
        // TODO: Implement session loading from server
    }

    /**
     * Storage Management
     */
    async updateStorageInfo() {
        try {
            // Calculate total storage from sessions
            const totalSize = this.sessions.reduce((sum, s) => sum + (s.size || 0), 0);
            const percentage = (totalSize / this.STORAGE_LIMIT) * 100;
            
            this.elements.storagePercentage.textContent = `${percentage.toFixed(1)}%`;
            this.elements.storageProgressBar.style.width = `${percentage}%`;
            
            // Update status
            if (percentage < 70) {
                this.elements.storageStatus.textContent = 'OK';
                this.elements.storageProgressBar.style.background = 'var(--accent-green)';
            } else if (percentage < 90) {
                this.elements.storageStatus.textContent = 'Warning';
                this.elements.storageProgressBar.style.background = 'var(--accent-orange)';
            } else {
                this.elements.storageStatus.textContent = 'Full';
                this.elements.storageProgressBar.style.background = 'var(--accent-red)';
            }
        } catch (error) {
            console.error('[Storage] Error:', error);
        }
    }

    async cleanupStorage() {
        if (!confirm('⚠️ Xóa TẤT CẢ phiên đã lưu? Hành động này không thể hoàn tác!')) return;
        
        try {
            const response = await fetch('http://localhost:5001/clear-sessions', {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error('Failed to clear sessions');
            }
            
            const data = await response.json();
            
            // Clear local storage
            this.sessions = [];
            this.saveSessions();
            this.renderSessions();
            this.updateStorageInfo();
            
            this.showNotification(`🗑️ Đã xóa ${data.sessions_deleted} phiên`, 'success');
        } catch (error) {
            console.error('[Cleanup] Error:', error);
            alert('❌ Lỗi cleanup: ' + error.message);
        }
    }

    /**
     * Clear current results
     */
    clearResults() {
        this.elements.resultsContainer.innerHTML = `
            <div class="welcome-message">
                <div class="welcome-icon">🎙️</div>
                <h2>Chào mừng đến với Speech2Text Assistant!</h2>
                <p>Upload file âm thanh để bắt đầu chuyển đổi giọng nói thành văn bản</p>
                <div class="feature-list">
                    <div class="feature-item">✅ Hỗ trợ: MP3, WAV, M4A, FLAC, OGG</div>
                    <div class="feature-item">✅ Phân tách người nói tự động</div>
                    <div class="feature-item">✅ AI Enhancement với Qwen</div>
                    <div class="feature-item">✅ Timeline transcript chi tiết</div>
                </div>
            </div>
        `;
        
        this.currentResults = null;
        this.elements.exportBtn.disabled = true;
    }

    /**
     * Export functionality
     */
    showExportModal() {
        if (!this.currentResults) return;
        this.elements.exportModal.classList.add('show');
    }

    /**
     * Dark mode
     */
    initDarkMode() {
        const saved = localStorage.getItem('s2t_dark_mode');
        if (saved === 'true') {
            document.body.classList.add('dark-mode');
        }
    }

    toggleDarkMode() {
        document.body.classList.toggle('dark-mode');
        const isDark = document.body.classList.contains('dark-mode');
        localStorage.setItem('s2t_dark_mode', isDark);
    }
}

// Global export functions for modal
window.closeExportModal = function() {
    document.getElementById('exportModal').classList.remove('show');
};

window.exportTimeline = async function() {
    if (!app.currentResults) return;
    const blob = new Blob([app.currentResults.timeline], { type: 'text/plain' });
    downloadBlob(blob, `timeline_${app.currentSessionId}.txt`);
    closeExportModal();
};

window.exportEnhanced = async function() {
    if (!app.currentResults) return;
    const blob = new Blob([app.currentResults.enhanced], { type: 'text/plain' });
    downloadBlob(blob, `enhanced_${app.currentSessionId}.txt`);
    closeExportModal();
};

window.exportSegments = async function() {
    if (!app.currentResults || !app.currentResults.files.segments) return;
    
    try {
        const response = await fetch(`http://localhost:5001/download/${app.currentSessionId}/segments`);
        const blob = await response.blob();
        downloadBlob(blob, `segments_${app.currentSessionId}.txt`);
        closeExportModal();
    } catch (error) {
        alert('❌ Lỗi export: ' + error.message);
    }
};

window.exportAll = async function() {
    // TODO: Implement ZIP export
    alert('🚧 Tính năng đang phát triển!');
    closeExportModal();
};

function downloadBlob(blob, filename) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Initialize app when DOM is ready
let app;
document.addEventListener('DOMContentLoaded', () => {
    app = new Speech2TextApp();
    app.init();
});
