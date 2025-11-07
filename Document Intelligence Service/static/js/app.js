// Document Intelligence Service - Frontend JavaScript

class DocumentIntelligenceApp {
    constructor() {
        this.currentFile = null;
        this.currentResult = null;
        this.initializeElements();
        this.attachEventListeners();
        this.checkHealth();
    }

    initializeElements() {
        // Upload elements
        this.uploadArea = document.getElementById('uploadArea');
        this.fileInput = document.getElementById('fileInput');
        this.selectFileBtn = document.getElementById('selectFileBtn');
        this.fileInfo = document.getElementById('fileInfo');
        this.fileName = document.getElementById('fileName');
        this.fileSize = document.getElementById('fileSize');
        this.previewImage = document.getElementById('previewImage');
        this.removeFileBtn = document.getElementById('removeFileBtn');

        // Process elements
        this.processBtn = document.getElementById('processBtn');
        this.progressContainer = document.getElementById('progressContainer');
        this.progressFill = document.getElementById('progressFill');
        this.progressText = document.getElementById('progressText');

        // Options
        this.autoRotate = document.getElementById('autoRotate');
        this.includeConfidence = document.getElementById('includeConfidence');
        this.saveOutput = document.getElementById('saveOutput');
        this.minConfidence = document.getElementById('minConfidence');
        this.confidenceValue = document.getElementById('confidenceValue');

        // AI Options
        this.aiStatusBadge = document.getElementById('aiStatusBadge');
        this.aiClassify = document.getElementById('aiClassify');
        this.aiExtract = document.getElementById('aiExtract');
        this.aiSummary = document.getElementById('aiSummary');
        this.aiTab = document.getElementById('aiTab');

        // AI Sections
        this.aiClassificationSection = document.getElementById('aiClassificationSection');
        this.aiExtractionSection = document.getElementById('aiExtractionSection');
        this.aiSummarySection = document.getElementById('aiSummarySection');
        this.documentType = document.getElementById('documentType');
        this.extractedData = document.getElementById('extractedData');
        this.summaryText = document.getElementById('summaryText');

        // AI Tools
        this.aiQuestion = document.getElementById('aiQuestion');
        this.aiAskBtn = document.getElementById('aiAskBtn');
        this.aiAnswer = document.getElementById('aiAnswer');
        this.targetLanguage = document.getElementById('targetLanguage');
        this.aiTranslateBtn = document.getElementById('aiTranslateBtn');
        this.aiTranslation = document.getElementById('aiTranslation');
        this.aiInsightsBtn = document.getElementById('aiInsightsBtn');
        this.aiInsights = document.getElementById('aiInsights');

        // Stats
        this.statsCard = document.getElementById('statsCard');
        this.statBlocks = document.getElementById('statBlocks');
        this.statChars = document.getElementById('statChars');
        this.statLines = document.getElementById('statLines');
        this.statConfidence = document.getElementById('statConfidence');

        // Results
        this.emptyState = document.getElementById('emptyState');
        this.resultContent = document.getElementById('resultContent');
        this.resultActions = document.getElementById('resultActions');
        this.extractedText = document.getElementById('extractedText');
        this.blocksList = document.getElementById('blocksList');
        this.jsonOutput = document.getElementById('jsonOutput');

        // Actions
        this.copyBtn = document.getElementById('copyBtn');
        this.downloadTxtBtn = document.getElementById('downloadTxtBtn');
        this.downloadJsonBtn = document.getElementById('downloadJsonBtn');

        // Modal
        this.helpModal = document.getElementById('helpModal');
        this.helpBtn = document.getElementById('helpBtn');
        this.closeHelpModal = document.getElementById('closeHelpModal');

        // Toast
        this.toast = document.getElementById('toast');
        this.toastMessage = document.getElementById('toastMessage');
        
        // AI State
        this.aiEnabled = false;
        this.ocrText = '';
    }

    attachEventListeners() {
        // Upload
        this.selectFileBtn.addEventListener('click', () => this.fileInput.click());
        this.fileInput.addEventListener('change', (e) => this.handleFileSelect(e));
        this.uploadArea.addEventListener('click', () => this.fileInput.click());
        this.uploadArea.addEventListener('dragover', (e) => this.handleDragOver(e));
        this.uploadArea.addEventListener('dragleave', (e) => this.handleDragLeave(e));
        this.uploadArea.addEventListener('drop', (e) => this.handleDrop(e));
        this.removeFileBtn.addEventListener('click', () => this.removeFile());

        // Process
        this.processBtn.addEventListener('click', () => this.processDocument());

        // Options
        this.minConfidence.addEventListener('input', (e) => {
            this.confidenceValue.textContent = e.target.value + '%';
        });

        // AI Master Toggle
        const aiMasterToggle = document.getElementById('aiMasterToggle');
        const aiFeatures = document.getElementById('aiFeatures');
        if (aiMasterToggle) {
            aiMasterToggle.addEventListener('change', (e) => {
                const enabled = e.target.checked;
                if (aiFeatures) {
                    aiFeatures.classList.toggle('disabled', !enabled);
                }
                // Update badge
                if (this.aiStatusBadge) {
                    if (enabled && this.aiEnabled) {
                        this.aiStatusBadge.textContent = 'ACTIVE';
                        this.aiStatusBadge.className = 'badge-ai active';
                    } else if (!enabled) {
                        this.aiStatusBadge.textContent = 'OFF';
                        this.aiStatusBadge.className = 'badge-ai inactive';
                    }
                }
                this.showToast(enabled ? '✅ AI đã bật' : '❌ AI đã tắt');
            });
        }

        // Tabs
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => this.switchTab(e.target.dataset.tab));
        });

        // Actions
        this.copyBtn.addEventListener('click', () => this.copyText());
        this.downloadTxtBtn.addEventListener('click', () => this.downloadTxt());
        this.downloadJsonBtn.addEventListener('click', () => this.downloadJson());

        // AI Tools
        this.aiAskBtn.addEventListener('click', () => this.askQuestion());
        this.aiTranslateBtn.addEventListener('click', () => this.translateDocument());
        this.aiInsightsBtn.addEventListener('click', () => this.generateInsights());
        
        // Enter key for question
        this.aiQuestion.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.askQuestion();
        });

        // Modal
        this.helpBtn.addEventListener('click', () => this.showHelp());
        // Use data-modal attribute like other modals
        if (this.closeHelpModal) {
            this.closeHelpModal.addEventListener('click', () => this.hideHelp());
        }
        this.helpModal.addEventListener('click', (e) => {
            if (e.target === this.helpModal) this.hideHelp();
        });
    }

    async checkHealth() {
        try {
            const response = await fetch('/api/health');
            const data = await response.json();
            console.log('Service health:', data);
            
            // Update AI backend availability
            const aiMasterToggle = document.getElementById('aiMasterToggle');
            const aiFeatures = document.getElementById('aiFeatures');
            
            if (data.features && data.features.ai_enhancement) {
                // AI backend is available
                this.aiEnabled = true;
                
                // Check if user has it toggled on
                const userEnabled = aiMasterToggle ? aiMasterToggle.checked : true;
                
                if (userEnabled) {
                    this.aiStatusBadge.textContent = 'ACTIVE';
                    this.aiStatusBadge.className = 'badge-ai active';
                    this.aiTab.style.display = 'inline-flex';
                } else {
                    this.aiStatusBadge.textContent = 'OFF';
                    this.aiStatusBadge.className = 'badge-ai inactive';
                    this.aiTab.style.display = 'none';
                }
            } else {
                // AI backend not available
                this.aiEnabled = false;
                this.aiStatusBadge.textContent = 'INACTIVE';
                this.aiStatusBadge.className = 'badge-ai inactive';
                this.aiTab.style.display = 'none';
                
                // Disable master toggle and features
                if (aiMasterToggle) {
                    aiMasterToggle.checked = false;
                    aiMasterToggle.disabled = true;
                }
                if (aiFeatures) {
                    aiFeatures.classList.add('disabled');
                }
            }
        } catch (error) {
            console.error('Health check failed:', error);
            this.showToast('⚠️ Cannot connect to server', 'warning');
            this.aiStatusBadge.textContent = 'ERROR';
            this.aiStatusBadge.className = 'badge-ai inactive';
        }
    }

    // File Handling
    handleFileSelect(event) {
        const file = event.target.files[0];
        if (file) {
            this.loadFile(file);
        }
    }

    handleDragOver(event) {
        event.preventDefault();
        this.uploadArea.classList.add('dragover');
    }

    handleDragLeave(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('dragover');
    }

    handleDrop(event) {
        event.preventDefault();
        this.uploadArea.classList.remove('dragover');
        
        const file = event.dataTransfer.files[0];
        if (file) {
            this.loadFile(file);
        }
    }

    loadFile(file) {
        // Validate file size
        const maxSize = 20 * 1024 * 1024; // 20MB
        if (file.size > maxSize) {
            this.showToast('❌ File quá lớn! Tối đa 20MB', 'error');
            return;
        }

        // Validate file type
        const allowedTypes = ['image/jpeg', 'image/png', 'image/bmp', 'image/tiff', 'image/webp', 'application/pdf'];
        if (!allowedTypes.includes(file.type)) {
            this.showToast('❌ Định dạng file không hỗ trợ!', 'error');
            return;
        }

        this.currentFile = file;
        
        // Update UI
        this.fileName.textContent = file.name;
        this.fileSize.textContent = this.formatFileSize(file.size);
        
        // Show preview for images
        if (file.type.startsWith('image/')) {
            const reader = new FileReader();
            reader.onload = (e) => {
                this.previewImage.src = e.target.result;
                this.previewImage.style.display = 'block';
            };
            reader.readAsDataURL(file);
        } else {
            this.previewImage.style.display = 'none';
        }

        // Show file info
        this.uploadArea.style.display = 'none';
        this.fileInfo.style.display = 'flex';
        this.processBtn.disabled = false;

        this.showToast('✅ File đã được tải lên', 'success');
    }

    removeFile() {
        this.currentFile = null;
        this.fileInput.value = '';
        this.uploadArea.style.display = 'block';
        this.fileInfo.style.display = 'none';
        this.processBtn.disabled = true;
        this.previewImage.src = '';
    }

    formatFileSize(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i];
    }

    // Processing
    async processDocument() {
        if (!this.currentFile) {
            this.showToast('❌ Vui lòng chọn file!', 'error');
            return;
        }

        // Show progress
        this.processBtn.disabled = true;
        this.progressContainer.style.display = 'block';
        this.updateProgress(10, 'Đang tải file...');

        const formData = new FormData();
        formData.append('file', this.currentFile);

        // Options
        const options = {
            save_output: this.saveOutput.checked,
            include_blocks: true,
            min_confidence: parseFloat(this.minConfidence.value) / 100
        };
        
        // Check if AI is enabled by both backend AND user toggle
        const aiMasterToggle = document.getElementById('aiMasterToggle');
        const userEnabledAI = aiMasterToggle ? aiMasterToggle.checked : false;
        
        // Add AI options if both backend supports it and user has it enabled
        if (this.aiEnabled && userEnabledAI) {
            options.ai_classify = this.aiClassify.checked;
            options.ai_extract = this.aiExtract.checked;
            options.ai_summary = this.aiSummary.checked;
        } else {
            // Explicitly disable AI if user toggled it off
            options.ai_classify = false;
            options.ai_extract = false;
            options.ai_summary = false;
        }
        
        formData.append('options', JSON.stringify(options));

        try {
            this.updateProgress(30, 'Đang xử lý OCR...');

            const response = await fetch('/api/upload', {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            if (this.aiEnabled && (options.ai_classify || options.ai_extract || options.ai_summary)) {
                this.updateProgress(70, 'Đang phân tích AI...');
                await new Promise(resolve => setTimeout(resolve, 500)); // Visual delay
            }

            this.updateProgress(100, 'Hoàn thành!');

            if (result.success) {
                this.currentResult = result;
                this.displayResult(result);
                
                // Display AI results if available
                if (result.ai_analysis) {
                    this.displayAIResults(result.ai_analysis);
                }
                
                this.showToast('✅ Xử lý thành công!', 'success');
            } else {
                throw new Error(result.error || 'Processing failed');
            }

        } catch (error) {
            console.error('Processing error:', error);
            this.showToast('❌ Lỗi xử lý: ' + error.message, 'error');
        } finally {
            setTimeout(() => {
                this.progressContainer.style.display = 'none';
                this.processBtn.disabled = false;
                this.updateProgress(0, '');
            }, 1000);
        }
    }

    updateProgress(percent, text) {
        this.progressFill.style.width = percent + '%';
        this.progressText.textContent = text;
    }

    displayResult(result) {
        // Hide empty state
        this.emptyState.style.display = 'none';
        this.resultContent.style.display = 'block';
        this.resultActions.style.display = 'flex';

        // Display text
        const text = result.full_text || result.text || '';
        this.extractedText.textContent = text;

        // Display blocks
        if (result.blocks || (result.pages && result.pages[0]?.blocks)) {
            const blocks = result.blocks || result.pages.flatMap(p => p.blocks || []);
            this.displayBlocks(blocks);
        }

        // Display JSON
        this.jsonOutput.textContent = JSON.stringify(result, null, 2);

        // Update stats
        const stats = result.statistics || {};
        this.statBlocks.textContent = stats.total_blocks || 0;
        this.statChars.textContent = stats.total_chars || 0;
        this.statLines.textContent = stats.total_lines || 0;
        this.statConfidence.textContent = 
            ((stats.average_confidence || 0) * 100).toFixed(1) + '%';
        
        this.statsCard.style.display = 'block';

        // Switch to text tab
        this.switchTab('text');
    }

    displayBlocks(blocks) {
        this.blocksList.innerHTML = '';
        
        blocks.forEach((block, index) => {
            const blockEl = document.createElement('div');
            blockEl.className = 'block-item';
            
            const confidence = (block.confidence * 100).toFixed(1);
            const confidenceClass = confidence >= 80 ? 'success' : 
                                  confidence >= 60 ? 'warning' : 'danger';
            
            blockEl.innerHTML = `
                <div class="block-header">
                    <span>Block #${index + 1}</span>
                    <span class="block-confidence" style="background: var(--${confidenceClass})">
                        ${confidence}%
                    </span>
                </div>
                <div class="block-text">${block.text}</div>
            `;
            
            this.blocksList.appendChild(blockEl);
        });
    }

    // Tabs
    switchTab(tabName) {
        // Update buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tabName);
        });

        // Update content
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.getElementById(tabName + 'Tab').classList.add('active');
    }

    // Actions
    copyText() {
        const text = this.extractedText.textContent;
        navigator.clipboard.writeText(text).then(() => {
            this.showToast('✅ Đã copy vào clipboard!', 'success');
        }).catch(err => {
            console.error('Copy failed:', err);
            this.showToast('❌ Copy thất bại!', 'error');
        });
    }

    downloadTxt() {
        const text = this.extractedText.textContent;
        const blob = new Blob([text], { type: 'text/plain;charset=utf-8' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ocr_result_${Date.now()}.txt`;
        a.click();
        URL.revokeObjectURL(url);
        this.showToast('✅ Đã tải xuống!', 'success');
    }

    downloadJson() {
        const json = JSON.stringify(this.currentResult, null, 2);
        const blob = new Blob([json], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `ocr_result_${Date.now()}.json`;
        a.click();
        URL.revokeObjectURL(url);
        this.showToast('✅ Đã tải xuống!', 'success');
    }

    // Modal
    showHelp() {
        this.helpModal.style.display = 'flex';
    }

    hideHelp() {
        this.helpModal.style.display = 'none';
    }

    // Toast / Notification
    showToast(message, type = 'success') {
        this.toastMessage.textContent = message;
        
        // Set icon based on type
        const icon = this.toast.querySelector('i');
        icon.className = type === 'success' ? 'fas fa-check-circle' :
                        type === 'error' ? 'fas fa-exclamation-circle' :
                        'fas fa-info-circle';
        
        // Set color
        this.toast.style.background = type === 'success' ? 'var(--success)' :
                                     type === 'error' ? 'var(--danger)' :
                                     'var(--warning)';
        
        this.toast.classList.add('show');
        
        setTimeout(() => {
            this.toast.classList.remove('show');
        }, 3000);
    }

    // Alias for advanced features compatibility
    showNotification(message, type = 'success') {
        this.showToast(message, type);
    }

    // AI Methods
    displayAIResults(aiResults) {
        if (!aiResults || !this.aiEnabled) return;

        // Show AI sections based on results
        if (aiResults.classification) {
            this.aiClassificationSection.style.display = 'block';
            this.documentType.innerHTML = `
                <i class="fas fa-file-alt"></i>
                <span>${aiResults.classification.type}</span>
            `;
        }

        if (aiResults.extraction && Object.keys(aiResults.extraction).length > 0) {
            this.aiExtractionSection.style.display = 'block';
            this.extractedData.innerHTML = '';
            
            for (const [key, value] of Object.entries(aiResults.extraction)) {
                const row = document.createElement('div');
                row.className = 'data-row';
                row.innerHTML = `
                    <div class="data-key">${key}:</div>
                    <div class="data-value">${value}</div>
                `;
                this.extractedData.appendChild(row);
            }
        }

        if (aiResults.summary) {
            this.aiSummarySection.style.display = 'block';
            this.summaryText.textContent = aiResults.summary;
        }

        // Store OCR text for AI tools
        if (this.currentResult && this.currentResult.text) {
            this.ocrText = this.currentResult.text;
        }
    }

    async askQuestion() {
        const question = this.aiQuestion.value.trim();
        if (!question) {
            this.showToast('⚠️ Vui lòng nhập câu hỏi', 'warning');
            return;
        }

        if (!this.ocrText) {
            this.showToast('⚠️ Chưa có document để hỏi', 'warning');
            return;
        }

        this.aiAnswer.style.display = 'block';
        this.aiAnswer.innerHTML = '<div class="ai-loading">Đang xử lý câu hỏi...</div>';
        this.aiAskBtn.disabled = true;

        try {
            const response = await fetch('/api/ai/qa', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: this.ocrText,
                    question: question
                })
            });

            const data = await response.json();

            if (data.success) {
                this.aiAnswer.innerHTML = `
                    <strong>Câu hỏi:</strong> ${question}<br><br>
                    <strong>Trả lời:</strong><br>${data.answer}
                `;
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            console.error('AI Q&A error:', error);
            this.aiAnswer.innerHTML = `
                <div class="ai-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    Lỗi: ${error.message}
                </div>
            `;
        } finally {
            this.aiAskBtn.disabled = false;
        }
    }

    async translateDocument() {
        if (!this.ocrText) {
            this.showToast('⚠️ Chưa có document để dịch', 'warning');
            return;
        }

        const targetLang = this.targetLanguage.value;
        this.aiTranslation.style.display = 'block';
        this.aiTranslation.innerHTML = '<div class="ai-loading">Đang dịch...</div>';
        this.aiTranslateBtn.disabled = true;

        try {
            const response = await fetch('/api/ai/translate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: this.ocrText,
                    target_language: targetLang
                })
            });

            const data = await response.json();

            if (data.success) {
                this.aiTranslation.innerHTML = `
                    <strong>Dịch sang ${targetLang.toUpperCase()}:</strong><br><br>
                    ${data.translation}
                `;
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            console.error('Translation error:', error);
            this.aiTranslation.innerHTML = `
                <div class="ai-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    Lỗi: ${error.message}
                </div>
            `;
        } finally {
            this.aiTranslateBtn.disabled = false;
        }
    }

    async generateInsights() {
        if (!this.ocrText) {
            this.showToast('⚠️ Chưa có document để phân tích', 'warning');
            return;
        }

        this.aiInsights.style.display = 'block';
        this.aiInsights.innerHTML = '<div class="ai-loading">Đang phân tích...</div>';
        this.aiInsightsBtn.disabled = true;

        try {
            const response = await fetch('/api/ai/insights', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: this.ocrText
                })
            });

            const data = await response.json();

            if (data.success) {
                let html = '<strong>Phân tích chuyên sâu:</strong><br><br>';
                
                const insights = data.insights;
                if (insights.document_purpose) {
                    html += `<h5>📋 Mục đích:</h5><p>${insights.document_purpose}</p>`;
                }
                if (insights.key_points && insights.key_points.length > 0) {
                    html += '<h5>🔑 Điểm chính:</h5><ul>';
                    insights.key_points.forEach(point => {
                        html += `<li>${point}</li>`;
                    });
                    html += '</ul>';
                }
                if (insights.entities && insights.entities.length > 0) {
                    html += '<h5>👤 Thực thể:</h5><ul>';
                    insights.entities.forEach(entity => {
                        html += `<li>${entity}</li>`;
                    });
                    html += '</ul>';
                }
                if (insights.recommendations) {
                    html += `<h5>💡 Đề xuất:</h5><p>${insights.recommendations}</p>`;
                }

                this.aiInsights.innerHTML = html;
            } else {
                throw new Error(data.error || 'Unknown error');
            }
        } catch (error) {
            console.error('Insights error:', error);
            this.aiInsights.innerHTML = `
                <div class="ai-error">
                    <i class="fas fa-exclamation-triangle"></i>
                    Lỗi: ${error.message}
                </div>
            `;
        } finally {
            this.aiInsightsBtn.disabled = false;
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('📄 Document Intelligence Service - Frontend Ready');
    window.app = new DocumentIntelligenceApp();
});
