/**
 * Main Application Entry Point
 * Initializes and connects all modules
 */

import { ChatManager } from './modules/chat-manager.js';
import { APIService } from './modules/api-service.js';
import { UIUtils } from './modules/ui-utils.js';
import { MessageRenderer } from './modules/message-renderer.js';
import { FileHandler } from './modules/file-handler.js';
import { MemoryManager } from './modules/memory-manager.js';
import { ImageGeneration } from './modules/image-gen.js';
import { ImageGenV2 } from './modules/image-gen-v2.js';
import { VideoGen } from './modules/video-gen.js';
import { ExportHandler } from './modules/export-handler.js';
import { SplitViewManager } from './modules/split-view.js';
import { initLanguage } from './language-switcher.js';

class ChatBotApp {
    constructor() {
        // Initialize all modules
        this.chatManager = new ChatManager();
        this.apiService = new APIService();
        this.uiUtils = new UIUtils();
        this.messageRenderer = new MessageRenderer();
        this.fileHandler = new FileHandler();
        this.memoryManager = new MemoryManager(this.apiService);
        this.imageGen = new ImageGeneration(this.apiService);
        this.imageGenV2 = new ImageGenV2(this.apiService);
        this.videoGen = new VideoGen();
        this.exportHandler = new ExportHandler();
        
        // Expose chatManager and chatApp globally
        window.chatManager = this.chatManager;
        window.chatApp = this;
        
        // State — no tools active by default
        this.activeTools = new Set();
        this.conversationActive = false;
        this.currentAbortController = null;
        this.messageHistory = {}; // Store message versions: { messageId: [version1, version2, ...] }
        this.currentMessageId = null;
        
        // Split view (initialized after DOM ready)
        this.splitViewManager = null;
    }

    /**
     * Escape HTML special characters to prevent XSS
     */
    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    /**
     * Initialize the application
     */
    async init() {
        console.log('[App] Initializing ChatBot application...');
        
        // Initialize language switcher
        initLanguage();
        
        // Listen for chat list update event
        window.addEventListener('chatListNeedsUpdate', () => {
            this.renderChatList();
        });
        
        // Initialize UI elements
        const elements = this.uiUtils.initElements();
        
        // Load chat sessions
        this.chatManager.loadSessions();
        console.log('[DEBUG] After loadSessions: chatSessions=', Object.keys(this.chatManager.chatSessions), 'currentId=', this.chatManager.currentChatId);
        this.renderChatList();
        try {
            this.loadCurrentChat();
        } catch (e) {
            console.error('[App] loadCurrentChat failed:', e);
        }
        
        // Setup UI
        this.uiUtils.initDarkMode();
        this.uiUtils.setupAutoResize(elements.messageInput);
        
        // Setup event listeners
        try {
            this.setupEventListeners();
        } catch (e) {
            console.error('[App] setupEventListeners failed:', e);
        }
        
        console.log('[App] Setting up file upload handler...');
        console.log('[App] fileInput element:', elements.fileInput);
        
        // Staged files waiting to be sent with the next message
        this._stagedFiles = [];

        // Setup file handling — STAGING MODE (files wait until user sends message)
        const newFileInput = this.fileHandler.setupFileInput(elements.fileInput, async (files) => {
            try {
                for (let file of files) {
                    try {
                        const fileData = await this.fileHandler.processFile(file);
                        this._stagedFiles.push(fileData);
                    } catch (error) {
                        console.error('[App] File processing error:', error);
                    }
                }
                newFileInput.value = '';
                this._renderStagingArea();
            } catch (error) {
                console.error('Upload error:', error);
                newFileInput.value = '';
            }
        });

        // Render staging previews above the textarea (compact card style matching file-attachment-card)
        this._renderStagingArea = () => {
            const area = document.getElementById('fileStagingArea');
            if (!area) return;
            if (this._stagedFiles.length === 0) {
                area.style.display = 'none';
                area.innerHTML = '';
                return;
            }
            area.style.display = 'flex';
            area.innerHTML = this._stagedFiles.map((f, i) => {
                const isTable = !!(f.tableData && f.tableData.headers && f.tableData.headers.length > 0);
                const isImage = f.type && f.type.startsWith('image/') && f.preview;
                const icon = this.fileHandler.getFileIcon ? this.fileHandler.getFileIcon(f.type || '', f.name) : '📄';

                let iconOrPreview;
                if (isImage) {
                    iconOrPreview = `<div class="file-staging__card-preview"><img src="${this.fileHandler.escapeHtml(f.preview)}" alt=""></div>`;
                } else if (isTable) {
                    iconOrPreview = `<div class="file-staging__card-icon">📊</div>`;
                } else {
                    iconOrPreview = `<div class="file-staging__card-icon">${icon}</div>`;
                }

                const sizeStr = this.fileHandler.formatFileSize ? this.fileHandler.formatFileSize(f.size) : '';
                const meta = isTable
                    ? `${f.tableData.rows.length} hàng · ${f.tableData.headers.length} cột`
                    : sizeStr;

                return `<div class="file-staging__card file-staging__clickable${isTable ? ' file-staging__card--table' : ''}" data-idx="${i}" title="${this.fileHandler.escapeHtml(f.name)}">
                    ${iconOrPreview}
                    <div class="file-staging__card-info">
                        <div class="file-staging__card-name">${this.fileHandler.escapeHtml(f.name)}</div>
                        <div class="file-staging__card-meta">${meta}</div>
                    </div>
                    <button class="file-staging__remove" data-idx="${i}" title="Xóa">×</button>
                </div>`;
            }).join('');

            // Remove buttons
            area.querySelectorAll('.file-staging__remove').forEach(btn => {
                btn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    const idx = parseInt(e.currentTarget.dataset.idx);
                    this._stagedFiles.splice(idx, 1);
                    this._renderStagingArea();
                });
            });
            // Click-to-preview on the card itself
            area.querySelectorAll('.file-staging__clickable').forEach(el => {
                el.addEventListener('click', (e) => {
                    if (e.target.classList.contains('file-staging__remove')) return;
                    const idx = parseInt(el.dataset.idx);
                    const fileData = this._stagedFiles[idx];
                    if (fileData) this.fileHandler.previewFileData(fileData);
                });
            });
        };

        // Drag & drop support on the input area
        const inputArea = document.querySelector('.input-area');
        if (inputArea) {
            ['dragenter', 'dragover'].forEach(evt => {
                inputArea.addEventListener(evt, (e) => { e.preventDefault(); inputArea.classList.add('input-area--dragover'); });
            });
            ['dragleave', 'drop'].forEach(evt => {
                inputArea.addEventListener(evt, () => { inputArea.classList.remove('input-area--dragover'); });
            });
            inputArea.addEventListener('drop', async (e) => {
                e.preventDefault();
                const droppedFiles = Array.from(e.dataTransfer.files);
                if (droppedFiles.length > 0) {
                    for (const file of droppedFiles) {
                        try {
                            const fileData = await this.fileHandler.processFile(file);
                            this._stagedFiles.push(fileData);
                        } catch (err) {
                            console.error('[App] Drop file error:', err);
                        }
                    }
                    this._renderStagingArea();
                }
            });
        }

        // Flush staged files into session when message is sent.
        // Returns the flushed files so the caller can embed them in the message bubble.
        this._flushStagedFiles = () => {
            if (this._stagedFiles.length === 0) return [];
            const flushed = [...this._stagedFiles];
            for (let fileData of flushed) {
                this.fileHandler.currentSessionFiles.push(fileData);
            }
            this.saveFilesToCurrentSession();
            this._stagedFiles = [];
            this._renderStagingArea();
            // Re-render session file list so remove buttons are available
            this.fileHandler.renderSessionFiles(elements.fileList);
            return flushed;
        };
        
        // Update elements reference to use new file input
        if (newFileInput) {
            elements.fileInput = newFileInput;
        }
        
        this.fileHandler.setupPasteHandler(elements.messageInput, async (files) => {
            try {
                // Don't clear old files - allow accumulation
                // this.fileHandler.clearSessionFiles();
                // this.fileHandler.clearFiles();
                
                // Process NEW files only
                const processedFiles = [];
                for (let file of files) {
                    try {
                        const fileData = await this.fileHandler.processFile(file);
                        processedFiles.push(fileData);
                    } catch (error) {
                        // Show error in chat instead of alert
                        const errorTimestamp = this.uiUtils.formatTimestamp(new Date());
                        const customPromptUsed = window.customPromptEnabled === true;
                        this.messageRenderer.addMessage(
                            elements.chatContainer,
                            `❌ **Lỗi xử lý file "${file.name}":** ${error.message}`,
                            false,
                            'system',
                            'error',
                            errorTimestamp,
                            null,
                            customPromptUsed
                        );
                        console.error('File processing error:', error);
                    }
                }
                
                if (processedFiles.length === 0) return;
                
                // Add processed files to session (accumulate) - FIXED: use processedFiles instead of raw files
                for (let fileData of processedFiles) {
                    this.fileHandler.currentSessionFiles.push(fileData);
                }
                this.saveFilesToCurrentSession();
                
                // Show NEW files in chat with instructions
                const timestamp = this.uiUtils.formatTimestamp(new Date());
                this.messageRenderer.addFileMessage(elements.chatContainer, processedFiles, timestamp);
                
                // Show instruction message
                const instructionTimestamp = this.uiUtils.formatTimestamp(new Date());
                const customPromptUsed = window.customPromptEnabled === true;
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    `✅ **Đã paste ${processedFiles.length} file.** Hỏi tôi bất kỳ điều gì về file! 💬`,
                    false,
                    'system',
                    'info',
                    instructionTimestamp,
                    null,
                    customPromptUsed
                );
            } catch (error) {
                console.error('Paste error:', error);
                // Show error in chat instead of alert
                const errorTimestamp = this.uiUtils.formatTimestamp(new Date());
                const customPromptUsed = window.customPromptEnabled === true;
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    `❌ **Lỗi paste file:** ${error.message}`,
                    false,
                    'system',
                    'error',
                    errorTimestamp,
                    null,
                    customPromptUsed
                );
            }
        });
        
        // Set callback for file changes (when files are removed)
        this.fileHandler.setOnFilesChange(() => {
            this.saveFilesToCurrentSession();
        });
        
        // Update UI
        console.log('[DEBUG] init() renderChatList: chatSessions=', Object.keys(this.chatManager.chatSessions), 'currentId=', this.chatManager.currentChatId);
        this.uiUtils.updateStorageDisplay(this.chatManager.getStorageInfo());
        this.uiUtils.renderChatList(
            this.chatManager.chatSessions,
            this.chatManager.currentChatId,
            (chatId) => this.handleSwitchChat(chatId),
            (chatId) => this.handleDeleteChat(chatId),
            (fromId, toId, position) => this.handleReorderChat(fromId, toId, position),
            (chatId) => this.handleTogglePin(chatId)
        );
        
        // Check local models
        await this.checkLocalModels();
        
        // Setup message renderer callback
        this.messageRenderer.setEditSaveCallback((messageDiv, newContent, originalContent) => {
            this.handleEditSave(messageDiv, newContent, originalContent);
        });
        
        // Delayed re-render to catch any async timing issues
        setTimeout(() => {
            console.log('[DEBUG] Delayed re-render: chatSessions=', Object.keys(this.chatManager.chatSessions));
            this.renderChatList();
        }, 500);
        
        console.log('[App] Initialization complete!');
    }

    /**
     * Render chat list (wrapper method for event listener)
     */
    renderChatList() {
        this.uiUtils.renderChatList(
            this.chatManager.chatSessions,
            this.chatManager.currentChatId,
            (chatId) => this.handleSwitchChat(chatId),
            (chatId) => this.handleDeleteChat(chatId),
            (fromId, toId, position) => this.handleReorderChat(fromId, toId, position),
            (chatId) => this.handleTogglePin(chatId)
        );
    }

    /**
     * Handle drag & drop reorder
     */
    handleReorderChat(fromId, toId, position) {
        this.chatManager.reorderChats(fromId, toId, position);
        this.renderChatList();
    }

    /**
     * Handle pin/unpin chat
     */
    handleTogglePin(chatId) {
        this.chatManager.togglePin(chatId);
        this.renderChatList();
    }

    /**
     * Setup all event listeners
     */
    setupEventListeners() {
        const elements = this.uiUtils.elements;
        
        // Send message
        elements.sendBtn.addEventListener('click', () => this.sendMessage());
        elements.messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Warn when textarea is getting close to the auto-convert threshold
        const LONG_WARN = 2500;
        const LONG_LIMIT = 3000;
        const inputHint = document.getElementById('messageInputLengthHint');
        elements.messageInput.addEventListener('input', () => {
            const len = elements.messageInput.value.length;
            if (inputHint) {
                if (len >= LONG_LIMIT) {
                    inputHint.textContent = `Văn bản quá dài (${len} ký tự) — sẽ tự động chuyển thành file .txt khi gửi`;
                    inputHint.style.display = 'block';
                    inputHint.className = 'message-input-hint message-input-hint--warn';
                } else if (len >= LONG_WARN) {
                    inputHint.textContent = `${len}/${LONG_LIMIT} ký tự — gần đến giới hạn`;
                    inputHint.style.display = 'block';
                    inputHint.className = 'message-input-hint message-input-hint--info';
                } else {
                    inputHint.style.display = 'none';
                }
            }
        });
        
        // Clear chat
        elements.clearBtn.addEventListener('click', () => this.clearChat());
        
        // New chat
        elements.newChatBtn.addEventListener('click', () => {
            this.newChat();
            // Close sidebar on mobile
            if (window.innerWidth <= 768) {
                this.uiUtils.closeSidebar();
            }
        });

        // Sidebar refresh
        const chatRefreshBtn = document.getElementById('chatRefreshBtn');
        if (chatRefreshBtn) {
            chatRefreshBtn.addEventListener('click', () => {
                chatRefreshBtn.classList.add('is-refreshing');
                this.renderChatList();
                setTimeout(() => chatRefreshBtn.classList.remove('is-refreshing'), 650);
            });
        }
        
        // Stop generation button
        const stopBtn = document.getElementById('stopGenerationBtn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopGeneration());
        }
        
        // Dark mode toggle
        elements.darkModeBtn.addEventListener('click', () => {
            this.uiUtils.toggleDarkMode();
        });
        
        // Split View toggle
        this.splitViewManager = new SplitViewManager(this.chatManager, this.uiUtils);
        const splitViewBtn = document.getElementById('splitViewBtn');
        if (splitViewBtn) {
            splitViewBtn.addEventListener('click', () => {
                this.splitViewManager.toggle();
            });
        }
        
        // Eye Care mode toggle
        const eyeCareBtn = document.getElementById('eyeCareBtn');
        if (eyeCareBtn) {
            eyeCareBtn.addEventListener('click', () => {
                this.uiUtils.toggleEyeCareMode();
            });
        }

        // ── More menu (topbar overflow) ──
        const moreMenuBtn = document.getElementById('moreMenuBtn');
        const moreMenuDropdown = document.getElementById('moreMenuDropdown');
        if (moreMenuBtn && moreMenuDropdown) {
            moreMenuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                moreMenuDropdown.classList.toggle('hidden');
            });
            document.addEventListener('click', (e) => {
                if (!moreMenuDropdown.contains(e.target) && e.target !== moreMenuBtn) {
                    moreMenuDropdown.classList.add('hidden');
                }
            });
        }
        
        // Sidebar toggle (chat history)
        const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');
        if (sidebarToggleBtn) {
            sidebarToggleBtn.addEventListener('click', () => {
                this.uiUtils.toggleSidebar();
            });
        }
        
        // Initialize sidebar state
        this.uiUtils.initSidebarState();
        
        // Legacy mobile sidebar toggle
        if (elements.sidebarToggle) {
            elements.sidebarToggle.addEventListener('click', () => {
                this.uiUtils.toggleSidebar();
            });
        }
        
        // MCP Tab switching
        this.setupMcpTabs();
        
        // Image generation button (ComfyUI legacy)
        if (elements.imageGenBtn) {
            elements.imageGenBtn.addEventListener('click', () => this.openImageGenModal());
        }

        // Image Generation V2 button (multi-provider)
        const igv2Btn = document.getElementById('imageGenV2Btn');
        if (igv2Btn) {
            igv2Btn.addEventListener('click', () => {
                this.imageGenV2.openModal();
            });
        }
        // Expose V2 globally for onclick handlers
        window.imageGenV2 = this.imageGenV2;

        // Video Generation (Sora 2) button
        const videoGenBtn = document.getElementById('videoGenBtn');
        if (videoGenBtn) {
            videoGenBtn.addEventListener('click', () => {
                this.videoGen.openModal();
            });
        }
        window.videoGen = this.videoGen;
        
        // Upload files button
        const uploadFilesBtn = document.getElementById('uploadFilesBtn');
        if (uploadFilesBtn && elements.fileInput) {
            uploadFilesBtn.addEventListener('click', () => {
                if (typeof closeToolsMenu === 'function') closeToolsMenu();
                elements.fileInput.click();
            });
        }
        
        // Memory panel
        if (elements.memoryBtn) {
            elements.memoryBtn.addEventListener('click', () => this.toggleMemoryPanel());
        }
        
        if (elements.saveMemoryBtn) {
            elements.saveMemoryBtn.addEventListener('click', () => this.saveCurrentChatAsMemory());
        }
        
        // Export/Download
        if (elements.downloadBtn) {
            elements.downloadBtn.addEventListener('click', () => this.exportChat());
        }
        
        // Model select change
        if (elements.modelSelect) {
            elements.modelSelect.addEventListener('change', () => {
                this.uiUtils.updateDeepThinkingVisibility(elements.modelSelect.value);
            });
        }
    }

    /**
     * Load current chat into UI
     */
    loadCurrentChat() {
        // Close thinking side panel when switching conversations
        if (window.ThinkingPanel) window.ThinkingPanel.close();
        const session = this.chatManager.getCurrentSession();
        if (!session) return;
        
        const elements = this.uiUtils.elements;
        const messages = Array.isArray(session.messages) ? session.messages : [];
        
        // Load messages
        if (messages.length > 0) {
            this.uiUtils.hideWelcomeScreen();
            const joined = session.messages.join('');
            elements.chatContainer.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(joined) : joined;
            
            // Restore message version history from session
            if (session.messageVersions) {
                Object.keys(session.messageVersions).forEach(messageId => {
                    const versions = session.messageVersions[messageId];
                    if (versions && versions.length > 0) {
                        // Restore to messageRenderer's history
                        this.messageRenderer.messageHistory.set(messageId, versions);
                        
                        // Update version indicators for messages with history
                        const messageDiv = elements.chatContainer.querySelector(`[data-message-id="${messageId}"]`);
                        if (messageDiv && versions.length > 1) {
                            const restoredCurrent = messageDiv.dataset.currentVersion;
                            messageDiv.dataset.currentVersion = (restoredCurrent !== undefined && restoredCurrent !== null && restoredCurrent !== '')
                                ? restoredCurrent
                                : (versions.length - 1).toString();
                            this.messageRenderer.updateVersionIndicator(messageDiv);
                        }
                    }
                });
            }
            
            // Reattach event listeners
            this.messageRenderer.reattachEventListeners(
                elements.chatContainer,
                null,
                null,
                (img) => this.openImagePreview(img)
            );
            
            // Make images clickable (with retry)
            const makeClickable = () => this.messageRenderer.makeImagesClickable((img) => this.openImagePreview(img));
            setTimeout(makeClickable, 200);
            setTimeout(makeClickable, 600);
        } else {
            this.uiUtils.clearChat();
            this.uiUtils.showWelcomeScreen();
        }
        
        // Load attached files for this session
        this.fileHandler.loadSessionFiles(session.attachedFiles || []);
        this.fileHandler.renderSessionFiles(elements.fileList);
    }

    /**
     * Save files to current session
     */
    saveFilesToCurrentSession() {
        const session = this.chatManager.getCurrentSession();
        if (session) {
            session.attachedFiles = this.fileHandler.getSessionFiles();
            this.chatManager.saveSessions();
        }
    }

    /**
     * Send message
     */
    async sendMessage() {
        const elements = this.uiUtils.elements;

        // ── Auto-convert very long input to a staged .txt file ──────────────
        const LONG_TEXT_THRESHOLD = 3000; // characters
        const rawInput = elements.messageInput ? elements.messageInput.value : '';
        if (rawInput.length > LONG_TEXT_THRESHOLD && this._stagedFiles !== undefined) {
            const blob = new Blob([rawInput], { type: 'text/plain' });
            const file = new File([blob], 'message.txt', { type: 'text/plain' });
            try {
                const fileData = await this.fileHandler.processFile(file);
                this._stagedFiles.push(fileData);
                // Clear textarea but leave a short summary prompt so user can add context
                if (elements.messageInput) elements.messageInput.value = '';
                this._renderStagingArea && this._renderStagingArea();
            } catch (err) {
                console.error('[App] Auto-convert to file error:', err);
            }
        }

        // Flush any staged files into the session before sending; capture for inline display
        const flushedFiles = this._flushStagedFiles ? this._flushStagedFiles() : [];

        const formValues = this.uiUtils.getFormValues();
        let message = formValues.message.trim();
        
        // Get session files
        const sessionFiles = this.fileHandler.getSessionFiles();
        
        if (!message && sessionFiles.length === 0) {
            return;
        }

        // Get active tools early — needed for routing
        const activeTools = window.getActiveTools ? window.getActiveTools() : Array.from(this.activeTools);

        // ── Image Generation V2 — Tool-aware routing ─────────
        // Route to image gen if: (1) tool is ON, OR (2) message looks like an image request
        const imageGenToolActive = activeTools.includes('image-generation');
        const isImageIntent = message && (imageGenToolActive || ImageGenV2.isImageRequest(message));
        if (isImageIntent) {
            console.log('[App] Image generation routing:', imageGenToolActive ? 'tool active' : 'intent detected');
            const timestamp = this.uiUtils.formatTimestamp(new Date());
            this.messageRenderer.addMessage(
                elements.chatContainer, message, true,
                formValues.model, formValues.context, timestamp
            );
            this.uiUtils.clearInput();

            // ── Provider Choice Dialog (LOCAL / API / CANCEL) with 30s timeout ──
            const providerChoice = await new Promise((resolve) => {
                const TIMEOUT_SECONDS = 30;
                const choiceContainer = document.createElement('div');
                choiceContainer.className = 'message assistant';
                choiceContainer.innerHTML = `
                    <div class="message__avatar message__avatar--agent"><img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false"></div>
                    <div class="message__body">
                        <div class="message-content">
                            <div class="igv2-provider-choice">
                                <div class="igv2-choice-header">
                                    <span class="igv2-choice-icon">⚡</span>
                                    <span class="igv2-choice-title">Chọn phương thức tạo ảnh</span>
                                    <span class="igv2-choice-timer">${TIMEOUT_SECONDS}s</span>
                                </div>
                                <div class="igv2-choice-buttons">
                                    <button class="igv2-choice-btn igv2-choice-local" data-choice="local">
                                        <span class="igv2-choice-btn-icon">🖥️</span>
                                        <span class="igv2-choice-btn-label">LOCAL</span>
                                        <span class="igv2-choice-btn-desc">ComfyUI · Miễn phí</span>
                                    </button>
                                    <button class="igv2-choice-btn igv2-choice-api" data-choice="api">
                                        <span class="igv2-choice-btn-icon">☁️</span>
                                        <span class="igv2-choice-btn-label">API</span>
                                        <span class="igv2-choice-btn-desc">Cloud · Nhanh & chất lượng</span>
                                    </button>
                                    <button class="igv2-choice-btn igv2-choice-cancel" data-choice="cancel">
                                        <span class="igv2-choice-btn-icon">❌</span>
                                        <span class="igv2-choice-btn-label">HỦY</span>
                                        <span class="igv2-choice-btn-desc">Không tạo ảnh</span>
                                    </button>
                                </div>
                                <div class="igv2-choice-progress">
                                    <div class="igv2-choice-progress-bar"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                `;
                elements.chatContainer.appendChild(choiceContainer);
                elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

                const timerEl = choiceContainer.querySelector('.igv2-choice-timer');
                const progressBar = choiceContainer.querySelector('.igv2-choice-progress-bar');
                let remaining = TIMEOUT_SECONDS;
                let resolved = false;

                const finalize = (choice) => {
                    if (resolved) return;
                    resolved = true;
                    clearInterval(countdownInterval);
                    // Mark selected button
                    choiceContainer.querySelectorAll('.igv2-choice-btn').forEach(btn => {
                        btn.disabled = true;
                        if (btn.dataset.choice === choice) btn.classList.add('selected');
                        else btn.classList.add('dimmed');
                    });
                    timerEl.textContent = choice === 'cancel' ? 'Đã hủy' : choice === 'local' ? 'LOCAL' : 'API';
                    resolve(choice);
                };

                choiceContainer.querySelectorAll('.igv2-choice-btn').forEach(btn => {
                    btn.addEventListener('click', () => finalize(btn.dataset.choice));
                });

                const countdownInterval = setInterval(() => {
                    remaining--;
                    if (timerEl) timerEl.textContent = `${remaining}s`;
                    if (progressBar) progressBar.style.width = `${(remaining / TIMEOUT_SECONDS) * 100}%`;
                    if (remaining <= 0) {
                        finalize('cancel');
                    }
                }, 1000);
                // Initial progress bar
                if (progressBar) progressBar.style.width = '100%';
            });

            if (providerChoice === 'cancel') {
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    '⏰ Đã hủy tạo ảnh — không có phản hồi hoặc người dùng chọn HỦY.',
                    false, formValues.model, formValues.context,
                    this.uiUtils.formatTimestamp(new Date())
                );
                elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
                await this.saveCurrentSession(true);
                return;
            }

            const imageGenOptions = providerChoice === 'local'
                ? { quality: 'free', provider: 'comfyui' }
                : { quality: 'auto' };
            console.log('[App] Provider choice:', providerChoice, imageGenOptions);

            // Create streaming status container (like thinking but for image gen)
            const statusContainer = document.createElement('div');
            statusContainer.className = 'message assistant';
            statusContainer.innerHTML = `
                <div class="message__avatar message__avatar--agent"><img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false"></div>
                <div class="message__body">
                    <div class="message-content">
                        <div class="igv2-stream-status">
                            <div class="igv2-stream-header">
                                <span class="igv2-stream-icon spinning">⚙️</span>
                                <span class="igv2-stream-title">Image Generation</span>
                            </div>
                            <div class="igv2-stream-steps"></div>
                        </div>
                    </div>
                </div>
            `;
            elements.chatContainer.appendChild(statusContainer);
            elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

            const stepsContainer = statusContainer.querySelector('.igv2-stream-steps');
            const headerIcon = statusContainer.querySelector('.igv2-stream-icon');
            let currentStepEl = null;

            const addStep = (icon, text, className = '') => {
                const step = document.createElement('div');
                step.className = `igv2-stream-step ${className}`;
                step.innerHTML = `<span class="igv2-step-icon">${icon}</span><span class="igv2-step-text">${text}</span>`;
                stepsContainer.appendChild(step);
                currentStepEl = step;
                elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
                return step;
            };

            const updateStep = (stepEl, icon, text, className = '') => {
                if (!stepEl) return;
                stepEl.className = `igv2-stream-step ${className}`;
                stepEl.innerHTML = `<span class="igv2-step-icon">${icon}</span><span class="igv2-step-text">${text}</span>`;
            };

            const conversationId = this.chatManager.getCurrentSession()?.id || '';
            this.currentAbortController = new AbortController();

            let providerStep = null;
            const result = await this.imageGenV2.generateFromChatStream(
                message, conversationId, this.currentAbortController.signal,
                {
                    onStatus: (data) => {
                        if (data.phase === 'enhance') {
                            if (data.enhanced_prompt) {
                                addStep('✨', `Prompt enhanced`, 'done');
                            } else {
                                addStep('✨', data.step, 'active');
                            }
                        } else if (data.phase === 'select') {
                            if (data.providers) {
                                addStep('📡', `Providers: ${data.providers.join(', ')}`, 'done');
                            } else {
                                addStep('🔍', data.step, 'active');
                            }
                        } else {
                            addStep('⚙️', data.step, 'active');
                        }
                    },
                    onProviderTry: (data) => {
                        providerStep = addStep('🔄', `Trying ${data.provider} (${data.attempt}/${data.total_providers})...`, 'active');
                    },
                    onProviderFail: (data) => {
                        updateStep(providerStep, '❌', `${data.provider} failed: ${data.error}`, 'fail');
                        providerStep = null;
                    },
                    onProviderSuccess: (data) => {
                        updateStep(providerStep, '✅', `${data.provider} / ${data.model} — ${Math.round(data.latency_ms)}ms`, 'done');
                        headerIcon.textContent = '✅';
                        headerIcon.classList.remove('spinning');
                    },
                    onError: (data) => {
                        addStep('❌', data.error, 'fail');
                        headerIcon.textContent = '❌';
                        headerIcon.classList.remove('spinning');
                    },
                },
                imageGenOptions,
            );

            if (result.success) {
                let imgSrc = '';
                let imageId = '';
                if (result.images?.length > 0 && result.images[0].url) {
                    imgSrc = result.images[0].url;
                    imageId = result.images[0].image_id || '';
                } else if (result.images_url?.length > 0) {
                    imgSrc = result.images_url[0];
                }

                const meta = `🎨 **${result.provider}** / ${result.model} | ${Math.round(result.latency_ms)}ms | $${result.cost_usd}`;
                const enhanced = result.prompt_used ? `\n📝 ${result.prompt_used.substring(0, 150)}` : '';
                const htmlAttrEsc = (value) => String(value || '')
                    .replace(/&/g, '&amp;')
                    .replace(/"/g, '&quot;')
                    .replace(/'/g, '&#39;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;');
                const promptEsc = htmlAttrEsc(result.prompt_used || message);
                const imgSrcAttr = htmlAttrEsc(imgSrc);
                const imageIdAttr = htmlAttrEsc(imageId);
                const overlayButtons = `
                    <div class="igv2-img-overlay">
                        <button type="button" class="igv2-img-btn" title="Tải ảnh" data-igv2-action="download" data-img-src="${imgSrcAttr}" data-image-id="${imageIdAttr}">⬇</button>
                        <button type="button" class="igv2-img-btn" title="Thông tin" data-igv2-action="info" data-image-id="${imageIdAttr}">ℹ</button>
                        ${imageId ? `<button type="button" class="igv2-img-btn igv2-save-btn" title="Lưu & Upload Drive" data-igv2-action="save" data-image-id="${imageIdAttr}">☁</button>` : ''}
                    </div>`;
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    `<div class="igv2-chat-image" data-image-id="${imageIdAttr}" data-prompt="${promptEsc}">${overlayButtons}<img src="${imgSrc}" alt="Generated" data-igv2-open="${imgSrcAttr}"><div class="igv2-chat-meta">${meta}${enhanced}</div></div>`,
                    false, formValues.model, formValues.context,
                    this.uiUtils.formatTimestamp(new Date())
                );

                // Store image gen metadata on the message div for regeneration
                const lastAssistantMsg = elements.chatContainer.querySelector('.message.assistant:last-child');
                if (lastAssistantMsg) {
                    lastAssistantMsg.dataset.igv2Provider = providerChoice;  // 'local' or 'api'
                    lastAssistantMsg.dataset.igv2Prompt = message;           // original user prompt
                    lastAssistantMsg.dataset.igv2RegenCount = '0';
                    lastAssistantMsg.dataset.igv2ConversationId = conversationId;
                    lastAssistantMsg.dataset.igv2IsImage = 'true';
                }

                // ── 4-Agents Deep Thinking Analysis (when multi-thinking mode) ──
                if (formValues.thinkingMode === 'multi-thinking' && result.success) {
                    const thinkingSection = this.messageRenderer.createThinkingSection(null, true);
                    const thinkMsgEl = document.createElement('div');
                    thinkMsgEl.className = 'message assistant';
                    thinkMsgEl.innerHTML = '<div class="message__avatar message__avatar--agent"><img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false"></div><div class="message__body"><div class="message-content"></div></div>';
                    thinkMsgEl.querySelector('.message-content').appendChild(thinkingSection);
                    elements.chatContainer.appendChild(thinkMsgEl);
                    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

                    const analysisSteps = [
                        { icon: '🔍', text: `**Phân tích prompt** — "${(result.prompt_used || message).substring(0, 80)}..."` },
                        { icon: '🎨', text: `**Provider:** ${result.provider} / ${result.model}` },
                        { icon: '⚡', text: `**Hiệu suất:** ${Math.round(result.latency_ms)}ms · Chi phí: $${result.cost_usd}` },
                        { icon: '📐', text: `**Đánh giá bố cục:** Ảnh được tạo với kích thước ${result.metadata?.width || '?'}×${result.metadata?.height || '?'}` },
                        { icon: '✨', text: `**Chất lượng:** ${providerChoice === 'local' ? 'ComfyUI local — miễn phí, tùy chỉnh tốt' : 'Cloud API — chất lượng cao, tốc độ nhanh'}` },
                        { icon: '✅', text: '**Kết luận:** Ảnh đã được tạo thành công. Bạn có thể yêu cầu chỉnh sửa thêm.' },
                    ];

                    for (let i = 0; i < analysisSteps.length; i++) {
                        await new Promise(r => setTimeout(r, 400));
                        this.messageRenderer.addThinkingStep(
                            thinkingSection,
                            `${analysisSteps[i].icon} ${analysisSteps[i].text}`
                        );
                        elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
                    }

                    // Finalize thinking
                    if (this.messageRenderer.finalizeThinking) {
                        this.messageRenderer.finalizeThinking(thinkingSection);
                    }
                }
            } else {
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    `❌ Không thể tạo ảnh: ${result.error}`,
                    false, formValues.model, formValues.context,
                    this.uiUtils.formatTimestamp(new Date())
                );
                // Store image gen metadata on error message too for retry
                const lastErrMsg = elements.chatContainer.querySelector('.message.assistant:last-child');
                if (lastErrMsg) {
                    lastErrMsg.dataset.igv2Provider = providerChoice;
                    lastErrMsg.dataset.igv2Prompt = message;
                    lastErrMsg.dataset.igv2RegenCount = '0';
                    lastErrMsg.dataset.igv2ConversationId = conversationId;
                    lastErrMsg.dataset.igv2IsImage = 'true';
                }
            }
            elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
            await this.saveCurrentSession(true);
            return;  // Don't send to chat API
        }
        // ── End Image Gen V2 ─────────────────────────────────

        // ── Img2Img Tool — route to img2img API when active ──
        const img2imgToolActive = activeTools.includes('img2img');
        if (img2imgToolActive && message) {
            // Find the last generated image in the conversation to use as source
            const allImages = elements.chatContainer.querySelectorAll('.igv2-chat-image img, .generated-preview img, .message img[src*="/api/image-gen/"], .message img[src*="/storage/images/"]');
            const lastImg = allImages.length > 0 ? allImages[allImages.length - 1] : null;
            
            if (lastImg) {
                console.log('[App] Img2Img tool active, using last image as source');
                const timestamp = this.uiUtils.formatTimestamp(new Date());
                this.messageRenderer.addMessage(
                    elements.chatContainer, message, true,
                    formValues.model, formValues.context, timestamp
                );
                this.uiUtils.clearInput();

                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    '🖼️ Đang chuyển đổi ảnh (Img2Img)...',
                    false, formValues.model, formValues.context,
                    this.uiUtils.formatTimestamp(new Date())
                );

                try {
                    // Fetch source image as base64
                    const imgResp = await fetch(lastImg.src);
                    const blob = await imgResp.blob();
                    const base64 = await new Promise((resolve, reject) => {
                        const reader = new FileReader();
                        reader.onload = () => resolve(reader.result.split(',')[1]);
                        reader.onerror = reject;
                        reader.readAsDataURL(blob);
                    });

                    const result = await this.apiService.generateImg2Img({
                        init_images: [base64],
                        prompt: message,
                        negative_prompt: 'bad quality, blurry, nsfw, nude',
                        denoising_strength: 0.6,
                        steps: 28,
                        width: 512,
                        height: 512,
                    });

                    // Remove loading message
                    const lastAssistant = elements.chatContainer.querySelector('.message.assistant:last-child');
                    if (lastAssistant) lastAssistant.remove();

                    if (result.images && result.images.length > 0) {
                        const imgSrc = result.images[0].startsWith('data:')
                            ? result.images[0]
                            : `data:image/png;base64,${result.images[0]}`;
                        this.messageRenderer.addMessage(
                            elements.chatContainer,
                            `<div class="igv2-chat-image"><img src="${imgSrc}" alt="Img2Img Result"><div class="igv2-chat-meta">🖼️ Img2Img | Prompt: ${message.substring(0, 80)}</div></div>`,
                            false, formValues.model, formValues.context,
                            this.uiUtils.formatTimestamp(new Date())
                        );
                    } else {
                        this.messageRenderer.addMessage(
                            elements.chatContainer,
                            `❌ Img2Img thất bại: ${result.error || 'Không nhận được ảnh'}`,
                            false, formValues.model, formValues.context,
                            this.uiUtils.formatTimestamp(new Date())
                        );
                    }
                } catch (e) {
                    const lastAssistant = elements.chatContainer.querySelector('.message.assistant:last-child');
                    if (lastAssistant) lastAssistant.remove();
                    this.messageRenderer.addMessage(
                        elements.chatContainer,
                        `❌ Img2Img lỗi: ${e.message}`,
                        false, formValues.model, formValues.context,
                        this.uiUtils.formatTimestamp(new Date())
                    );
                }

                elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
                await this.saveCurrentSession(true);
                return;
            }
            // No source image found → fall through to normal chat
            console.log('[App] Img2Img active but no source image found, falling through to chat');
        }
        // ── End Img2Img ──────────────────────────────────────
        
        // Handle Auto mode - decide if deep thinking is needed
        let deepThinking = formValues.deepThinking;
        if (deepThinking === 'auto' && window.coordinatedReasoning) {
            deepThinking = window.coordinatedReasoning.autoDecideMode(message);
            console.log('[App] Auto mode decided:', deepThinking ? 'deep thinking' : 'instant');
        }
        
        // Auto-include file context if files are attached
        // Keep original message for display, build augmented message for API
        const originalUserMessage = message;

        // Inject quoted context if any (select-and-reply feature)
        const quotedCtx = this.messageRenderer.consumeQuotedContext();
        if (quotedCtx) {
            message = `[Ngữ cảnh được chọn — ưu tiên trả lời dựa trên đoạn này]\n> ${quotedCtx}\n\n${message}`;
        }

        // Extract image base64 data URLs for vision API (sent separately from text)
        const imageDataUrls = [];
        if (sessionFiles.length > 0) {
            // Separate images from text files
            const textFiles = [];
            for (const file of sessionFiles) {
                if (file.type && file.type.startsWith('image/') && file.content && file.content.startsWith('data:')) {
                    imageDataUrls.push(file.content);
                } else {
                    textFiles.push(file);
                }
            }
            // Build text context only for non-image files
            const fileContext = this.buildFileContext(textFiles);
            if (fileContext || imageDataUrls.length > 0) {
                const textPart = fileContext ? `${fileContext}\n\n` : '';
                const imagePart = imageDataUrls.length > 0 ? `📷 ${imageDataUrls.length} image(s) attached for analysis.\n\n` : '';
                message = `${textPart}${imagePart}${message || 'Hãy phân tích các file được đính kèm.'}`;
            }
            // Auto-enable deep thinking when files are attached for better analysis
            deepThinking = true;
            console.log('[App] Auto-enabled Deep Thinking due to attached files, images:', imageDataUrls.length);
        }
        
        // activeTools already declared above (before image gen routing)
        
        // Include MCP context if enabled
        const mcpContextStr = this.getMcpContextString ? this.getMcpContextString() : '';
        const mcpOcrContextStr = (window.mcpController && window.mcpController.getOcrContextString)
            ? window.mcpController.getOcrContextString()
            : '';
        let mcpIndicator = '';
        if (mcpContextStr || mcpOcrContextStr) {
            const fullMcpContext = [mcpContextStr, mcpOcrContextStr].filter(Boolean).join('\n\n---\n\n');
            message = `[MCP Context được cung cấp - hãy sử dụng thông tin này để trả lời]\n\n${fullMcpContext}\n\n---\n\nUser question: ${message}`;
            mcpIndicator = ' 📎 MCP';
            console.log('[App] MCP context injected, length:', fullMcpContext.length);
        }
        
        // Generate message ID for versioning
        this.currentMessageId = 'msg_' + Date.now();
        
        // Show loading with thinking mode indicator
        const thinkingMode = formValues.thinkingMode || 'instant';
        this.uiUtils.showLoading(thinkingMode);
        if (window.showToolStatus) window.showToolStatus();
        
        // Add user message to chat (with attached files if any)
        const timestamp = this.uiUtils.formatTimestamp(new Date());
        const customPromptUsed = window.customPromptEnabled === true;
        this.messageRenderer.addMessage(
            elements.chatContainer,
            originalUserMessage || message,
            true,
            formValues.model,
            formValues.context,
            timestamp,
            null,
            customPromptUsed,
            null,
            flushedFiles.length > 0 ? flushedFiles : null
        );
        
        // If image-generation tool is active, show inline loading placeholder
        let imageLoadingPlaceholder = null;
        const hasImageTool = activeTools.includes('image-generation');
        if (hasImageTool) {
            const placeholder = document.createElement('div');
            placeholder.className = 'message assistant';
            placeholder.innerHTML = `
                <div class="message__avatar message__avatar--agent"><img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false"></div>
                <div class="message__body">
                    <div class="message-content">
                        <div class="image-gen-loading" id="imageGenLoadingPlaceholder">
                            <div class="loading-spinner"></div>
                            <div class="loading-text">🎨 Đang tạo ảnh...</div>
                            <div class="loading-progress" style="font-size:11px;color:var(--text-tertiary);">Analyzing prompt → Selecting provider → Generating</div>
                        </div>
                    </div>
                </div>
            `;
            elements.chatContainer.appendChild(placeholder);
            imageLoadingPlaceholder = placeholder;
            elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
        }
        
        // Close any open thinking panel when a new message is sent
        if (window.ThinkingPanel) window.ThinkingPanel.close();
        // Thinking container created on-demand when thinking events arrive
        let thinkingContainer = null;
        
        // Clear input (but keep files attached for this session)
        this.uiUtils.clearInput();
        
        // Create AbortController for this request
        this.currentAbortController = new AbortController();
        
        try {
            // Build history for context
            const history = this.buildConversationHistory();
            
            // Get selected memories
            const selectedMemories = this.memoryManager.getSelectedMemories();
            
            // Get agent config if enabled
            const agentConfig = window.getAgentConfig ? window.getAgentConfig() : null;

            // ── Use SSE streaming for live thinking + response ──
            let fullResponse = '';
            let thinkingSteps = [];
            let thinkingData = {};
            let streamFailed = false;
            let thinkingReceived = false;
            let streamCompleteData = {};
            let streamSuggestions = [];
            const _streamStartMs = performance.now();

            // Prepare streaming message div for progressive rendering
            const responseTimestamp = this.uiUtils.formatTimestamp(new Date());
            const streamMsgDiv = document.createElement('div');
            streamMsgDiv.className = 'message assistant';
            streamMsgDiv.dataset.timestamp = responseTimestamp;
            streamMsgDiv.dataset.model = formValues.model || '';
            streamMsgDiv.style.display = 'none'; // Hidden until first chunk arrives
            const streamAvatar = document.createElement('div');
            streamAvatar.className = 'message__avatar message__avatar--agent';
            streamAvatar.innerHTML = '<img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false">';
            streamMsgDiv.appendChild(streamAvatar);
            const streamBody = document.createElement('div');
            streamBody.className = 'message__body';
            const streamContentDiv = document.createElement('div');
            streamContentDiv.className = 'message-content';
            const streamTextDiv = document.createElement('div');
            streamTextDiv.className = 'message-text streaming-cursor';
            streamContentDiv.appendChild(streamTextDiv);
            streamBody.appendChild(streamContentDiv);
            streamMsgDiv.appendChild(streamBody);
            elements.chatContainer.appendChild(streamMsgDiv);

            try {
                await this.apiService.sendStreamMessage(
                    {
                        message: message,
                        model: formValues.model,
                        context: formValues.context,
                        deepThinking: deepThinking,
                        thinkingMode: thinkingMode,
                        history: history,
                        memories: selectedMemories,
                        customPrompt: agentConfig ? agentConfig.systemPrompt : '',
                        images: imageDataUrls.length > 0 ? imageDataUrls : undefined,
                        tools: activeTools,
                        skill: window.skillManager ? window.skillManager.getActiveSkillId() : '',
                        ...window.getAdvancedModelParams(),
                    },
                    this.currentAbortController.signal,
                    {
                        onMetadata: (data) => {
                            if (window.skillManager && data.skill_source === 'auto' && data.skill) {
                                window.skillManager.showAutoRouted(data.skill, data.skill_name, data.skill_auto_keywords);
                            }
                        },
                        onThinkingStart: (data) => {
                            thinkingReceived = true;
                            // Create thinking container on-demand if not already present
                            if (!thinkingContainer) {
                                thinkingContainer = this.messageRenderer.createThinkingSection(null, true);
                                // Insert before the stream message div
                                streamMsgDiv.parentNode.insertBefore(thinkingContainer, streamMsgDiv);
                            }
                            if (data?.request_id && thinkingContainer) {
                                thinkingContainer.dataset.requestId = data.request_id;
                            }
                        },
                        onThinking: (data) => {
                            thinkingReceived = true;
                            if (!thinkingContainer) {
                                thinkingContainer = this.messageRenderer.createThinkingSection(null, true);
                                streamMsgDiv.parentNode.insertBefore(thinkingContainer, streamMsgDiv);
                            }
                            if (data?.request_id && thinkingContainer) {
                                thinkingContainer.dataset.requestId = data.request_id;
                            }
                            thinkingSteps.push(data.step);
                            this.messageRenderer.addThinkingStep(
                                thinkingContainer, data.step, !!data.is_reasoning_chunk,
                                data.trajectory_id || null
                            );
                            elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
                        },
                        onThinkingEnd: (data) => {
                            thinkingData = data;
                            if (thinkingContainer) {
                                if (data?.request_id) {
                                    thinkingContainer.dataset.requestId = data.request_id;
                                }
                                this.messageRenderer.finalizeThinking(thinkingContainer, data);
                            }
                        },
                        onChunk: (data) => {
                            // On first content chunk, clean up empty thinking container
                            if (thinkingContainer && !thinkingReceived) {
                                thinkingContainer.remove();
                                thinkingContainer = null;
                            }
                            // Show the streaming message on first chunk
                            if (streamMsgDiv.style.display === 'none') {
                                streamMsgDiv.style.display = '';
                            }
                            fullResponse += data.content;
                            // Progressive markdown rendering
                            if (typeof marked !== 'undefined') {
                                const rawHtml = marked.parse(fullResponse);
                                streamTextDiv.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;
                            } else {
                                streamTextDiv.textContent = fullResponse;
                            }
                            elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
                        },
                        onComplete: (data) => {
                            fullResponse = data.response || fullResponse;
                            streamCompleteData = data;
                            // Clean up thinking container if it never got content
                            if (thinkingContainer && !thinkingReceived) {
                                thinkingContainer.remove();
                                thinkingContainer = null;
                            }
                            // Safeguard: stop timer if thinking_end event was never received
                            if (thinkingContainer && this.messageRenderer.finalizeThinking) {
                                this.messageRenderer.finalizeThinking(thinkingContainer, {});
                            }
                        },
                        onSuggestions: (data) => {
                            if (data.items && data.items.length > 0) {
                                streamSuggestions = data.items;
                            }
                        },
                        onError: (data) => {
                            console.error('[Stream] Error:', data.error);
                            streamFailed = true;
                        },
                    }
                );
            } catch (streamErr) {
                if (streamErr.name === 'AbortError') throw streamErr;
                console.warn('[Stream] SSE failed, falling back to regular POST:', streamErr.message);
                streamFailed = true;
            }

            // ── Fallback to regular POST if streaming failed ──
            if (streamFailed) {
                // Clean up streaming elements
                streamMsgDiv.remove();
                
                const data = await this.apiService.sendMessage(
                    message,
                    formValues.model,
                    formValues.context,
                    activeTools,
                    deepThinking,
                    history,
                    [],  // files already included in message context
                    selectedMemories,
                    this.currentAbortController.signal,
                    agentConfig ? agentConfig.systemPrompt : '',
                    agentConfig
                );
                fullResponse = data.error ? `❌ **Lỗi:** ${data.error}` : data.response;
                
                // Update thinking with data from non-streaming response
                if (data.thinking_process) {
                    if (!thinkingContainer) {
                        thinkingContainer = this.messageRenderer.createThinkingSection(null, false);
                        elements.chatContainer.insertBefore(thinkingContainer, streamMsgDiv.nextSibling || null);
                    }
                    this.messageRenderer.updateThinkingContent(thinkingContainer, data.thinking_process);
                } else if (thinkingContainer) {
                    this.messageRenderer.finalizeThinking(thinkingContainer, { summary: 'Hoàn thành' });
                }
            }

            // ── Finalize response display ──
            const responseContent = fullResponse;

            // Handle image response
            const isImageResponse = responseContent && (responseContent.includes('Image Generated') || responseContent.includes('generated-preview') || responseContent.includes('Image Generation Failed'));
            if (imageLoadingPlaceholder && isImageResponse) {
                const resultDiv = document.createElement('div');
                resultDiv.className = 'message assistant';
                resultDiv.dataset.timestamp = responseTimestamp;
                resultDiv.dataset.model = formValues.model || '';
                const avatarDiv = document.createElement('div');
                avatarDiv.className = 'message__avatar message__avatar--agent';
                avatarDiv.innerHTML = '<img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false">';
                resultDiv.appendChild(avatarDiv);
                const bodyDiv = document.createElement('div');
                bodyDiv.className = 'message__body';
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                const textDiv = document.createElement('div');
                textDiv.className = 'message-text image-gen-result';
                if (typeof marked !== 'undefined') {
                    const rawHtml = marked.parse(responseContent);
                    textDiv.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;
                } else {
                    textDiv.textContent = responseContent;
                }
                contentDiv.appendChild(textDiv);
                bodyDiv.appendChild(contentDiv);
                this.messageRenderer.addMessageButtons(contentDiv, responseContent, false, resultDiv);
                resultDiv.appendChild(bodyDiv);
                
                imageLoadingPlaceholder.replaceWith(resultDiv);
                if (window.lucide) lucide.createIcons({ nodes: [resultDiv] });
                // Remove the streaming div since we replaced with image
                streamMsgDiv.remove();
                elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
            } else {
                if (imageLoadingPlaceholder) imageLoadingPlaceholder.remove();
                
                // Remove streaming cursor class and finalize the streamed message
                streamTextDiv.classList.remove('streaming-cursor');
                
                // If streaming was used, the streamMsgDiv already has content.
                // Re-render final markdown cleanly and add buttons.
                if (!streamFailed && streamMsgDiv.style.display !== 'none') {
                    if (typeof marked !== 'undefined') {
                        const rawHtml = marked.parse(responseContent);
                        streamTextDiv.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;
                    }
                    // Highlight code blocks
                    if (typeof hljs !== 'undefined') {
                        streamTextDiv.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
                    }
                    this.messageRenderer.enhanceCodeBlocks(streamTextDiv);
                    // Enhance tables with interactive viewer
                    this.messageRenderer.enhanceMarkdownTables(streamTextDiv);
                    // Add action buttons to streaming message
                    this.messageRenderer.addMessageButtons(streamContentDiv, responseContent, false, streamMsgDiv);

                    // ── Stats badge (time · model · tokens) ──
                    const _clientElapsed = ((performance.now() - _streamStartMs) / 1000);
                    const _serverElapsed = streamCompleteData.elapsed_time || _clientElapsed;
                    const _tokens = streamCompleteData.tokens || 0;
                    const _maxTokens = streamCompleteData.max_tokens || 0;
                    const _modelName = this.messageRenderer.modelNames[formValues.model] || formValues.model;
                    const _speedLabel = _serverElapsed < 2 ? 'Fast' : _serverElapsed < 5 ? '' : 'Slow';
                    this.messageRenderer.addResponseStats(streamContentDiv, {
                        elapsed: _serverElapsed,
                        model: _modelName,
                        tokens: _tokens,
                        maxTokens: _maxTokens,
                        speedLabel: _speedLabel,
                        thinkingMode: thinkingMode,
                    });

                    if (window.lucide) lucide.createIcons({ nodes: [streamMsgDiv] });
                } else if (streamFailed) {
                    // Non-streaming fallback: use addMessage
                    const agentConfigForDisplay = window.getAgentConfig ? window.getAgentConfig() : null;
                    this.messageRenderer.addMessage(
                        elements.chatContainer,
                        responseContent,
                        false,
                        formValues.model,
                        formValues.context,
                        responseTimestamp,
                        thinkingData.steps || null,
                        customPromptUsed,
                        agentConfigForDisplay
                    );
                }
            }
            
            // Update the latest version with the new response
            const userMessages = elements.chatContainer.querySelectorAll('.message.user[data-message-id]');
            if (userMessages.length > 0) {
                const lastUserMsg = userMessages[userMessages.length - 1];
                const messageId = lastUserMsg.dataset.messageId;
                
                if (messageId) {
                    const msgHistory = this.messageRenderer.getMessageHistory(messageId);
                    if (msgHistory.length > 0) {
                        const lastVersion = msgHistory[msgHistory.length - 1];
                        lastVersion.assistantResponse = responseContent;
                        
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
                }
            }
            
            // Save to version history (version 1)
            if (!this.messageHistory[this.currentMessageId]) {
                this.messageHistory[this.currentMessageId] = [];
            }
            this.messageHistory[this.currentMessageId].push({
                version: 1,
                content: responseContent,
                timestamp: responseTimestamp,
                model: formValues.model,
                context: formValues.context
            });
            
            // Save session with updated timestamp (new message)
            this.saveCurrentSession(true);

            // Auto-generate title from latest user message (fire-and-forget)
            this.autoGenerateTitleIfNeeded(formValues.message.trim());
            
            // Log to Firebase (async, non-blocking)
            if (window.logChatToFirebase && !streamFailed) {
                window.logChatToFirebase(message, formValues.model, fullResponse, []);
            }
            
            // Make images clickable (with retry for dynamically loaded images)
            const makeClickable = () => this.messageRenderer.makeImagesClickable((img) => this.openImagePreview(img));
            setTimeout(makeClickable, 100);
            setTimeout(makeClickable, 500);

            // ── Follow-up suggestions + Think Harder ──
            if (!streamFailed && this.messageRenderer.features?.suggestionChips !== false) {
                const suggestionsContainer = document.createElement('div');
                suggestionsContainer.className = 'follow-up-suggestions';

                // "Think Harder" button (only if current mode is instant)
                if (thinkingMode === 'instant') {
                    const thinkBtn = document.createElement('button');
                    thinkBtn.className = 'suggestion-chip suggestion-chip--think';
                    thinkBtn.innerHTML = '<i data-lucide="brain" class="lucide"></i> Deep Thinking';
                    thinkBtn.title = '4-Agents involvement';
                    thinkBtn.onclick = () => {
                        // Re-send last message with multi-thinking mode
                        suggestionsContainer.remove();
                        const lastUserMsg = message;
                        if (window.selectThinkingMode) {
                            window.selectThinkingMode('multi-thinking', 'layers', '4-Agents');
                        }
                        // Set input and trigger send
                        this.uiUtils.setInputValue(lastUserMsg);
                        setTimeout(() => { document.getElementById('sendBtn')?.click(); }, 100);
                    };
                    suggestionsContainer.appendChild(thinkBtn);
                }

                // Append container early so Think Harder button shows immediately
                elements.chatContainer.appendChild(suggestionsContainer);
                if (window.lucide) lucide.createIcons({ nodes: [suggestionsContainer] });

                const _renderChips = (suggestions) => {
                    // Remove any skeleton loaders
                    suggestionsContainer.querySelectorAll('.suggestion-chip--loading').forEach(el => el.remove());
                    suggestions.forEach(text => {
                        const chip = document.createElement('button');
                        chip.className = 'suggestion-chip';
                        chip.innerHTML = `<span class="suggestion-chip__icon">↗</span><span class="suggestion-chip__text">${this._escapeHtml(text)}</span>`;
                        chip.onclick = () => {
                            suggestionsContainer.remove();
                            this.uiUtils.setInputValue(text);
                            setTimeout(() => { document.getElementById('sendBtn')?.click(); }, 100);
                        };
                        suggestionsContainer.appendChild(chip);
                    });
                    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
                };

                if (streamSuggestions.length > 0) {
                    // Server already sent suggestions via SSE — render immediately
                    _renderChips(streamSuggestions);
                } else if (responseContent) {
                    // Show skeleton placeholders while we fetch AI-generated suggestions
                    for (let i = 0; i < 3; i++) {
                        const s = document.createElement('span');
                        s.className = 'suggestion-chip suggestion-chip--loading';
                        s.innerHTML = '<span class="suggestion-chip__icon">↗</span><span class="suggestion-chip__text">…</span>';
                        suggestionsContainer.appendChild(s);
                    }
                    elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;

                    // Detect language from response
                    const _lang = /[àáâãäåæçèéêëìíîïðñòóôõöøùúûüý]/i.test(responseContent) ? 'vi' : 'en';
                    fetch('/api/chat/suggestions', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            message: message.slice(0, 500),
                            response: responseContent.slice(0, 1000),
                            model: formValues.model,
                            language: _lang,
                        }),
                        signal: AbortSignal.timeout(15000),
                    })
                    .then(r => r.ok ? r.json() : null)
                    .then(data => {
                        if (data?.suggestions?.length > 0) {
                            _renderChips(data.suggestions);
                        } else {
                            suggestionsContainer.querySelectorAll('.suggestion-chip--loading').forEach(el => el.remove());
                        }
                    })
                    .catch(() => {
                        suggestionsContainer.querySelectorAll('.suggestion-chip--loading').forEach(el => el.remove());
                    });
                }
            }
            
        } catch (error) {
            // Remove thinking container if error
            if (thinkingContainer) {
                thinkingContainer.remove();
            }
            // Remove image loading placeholder on error
            if (imageLoadingPlaceholder) imageLoadingPlaceholder.remove();
            
            // Check if it was aborted by user
            if (error.name === 'AbortError') {
                console.log('Generation stopped by user');
            } else {
                const errorTimestamp = this.uiUtils.formatTimestamp(new Date());
                const customPromptUsed2 = window.customPromptEnabled === true;
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    `❌ **Lỗi kết nối:** ${error.message}`,
                    false,
                    formValues.model,
                    formValues.context,
                    errorTimestamp,
                    null,
                    customPromptUsed2
                );
                this.saveCurrentSession(true);
            }
        } finally {
            if (window.hideToolStatus) window.hideToolStatus();
            this.uiUtils.hideLoading();
            this.currentAbortController = null;
        }
    }

    /**
     * Analyze uploaded files automatically
     */
    async analyzeUploadedFiles(files) {
        const elements = this.uiUtils.elements;
        const formValues = this.uiUtils.getFormValues();
        
        // Build analysis prompt
        let analysisPrompt = `📎 **Phân tích file đã tải lên:**\n\n`;
        analysisPrompt += `Có ${files.length} file được tải lên. Hãy phân tích chi tiết nội dung:\n\n`;
        
        files.forEach((file, index) => {
            analysisPrompt += `**File ${index + 1}: ${file.name}**\n`;
            analysisPrompt += `- Loại: ${file.type || 'unknown'}\n`;
            analysisPrompt += `- Kích thước: ${this.messageRenderer.formatFileSize(file.size)}\n`;
            
            // Include content for analysis
            if (file.content && typeof file.content === 'string') {
                if (!file.content.startsWith('data:')) {
                    // Text content
                    const maxLength = 15000;
                    const content = file.content.length > maxLength 
                        ? file.content.substring(0, maxLength) + '\n...(truncated)'
                        : file.content;
                    analysisPrompt += `\n**Nội dung:**\n\`\`\`\n${content}\n\`\`\`\n`;
                } else if (file.type.startsWith('image/')) {
                    analysisPrompt += `\n(Đây là file ảnh)\n`;
                }
            }
            analysisPrompt += `\n---\n\n`;
        });
        
        analysisPrompt += `\n**Yêu cầu phân tích:**\n`;
        analysisPrompt += `1. Tóm tắt nội dung chính của từng file\n`;
        analysisPrompt += `2. Phát hiện các vấn đề hoặc điểm đặc biệt\n`;
        analysisPrompt += `3. Đưa ra nhận xét và đề xuất (nếu có)\n`;
        analysisPrompt += `4. Trả lời các câu hỏi liên quan nếu cần\n`;
        
        // Show loading
        this.uiUtils.showLoading();
        
        // Create AbortController
        this.currentAbortController = new AbortController();
        this.currentMessageId = 'msg_' + Date.now();
        
        try {
            // Build history
            const history = this.buildConversationHistory();
            
            // Get memories
            const selectedMemories = this.memoryManager.getSelectedMemories();
            
            // Send to AI for analysis
            const data = await this.apiService.sendMessage(
                analysisPrompt,
                formValues.model,
                'programming', // Use programming context for file analysis
                Array.from(this.activeTools),
                false, // No deep thinking for file analysis
                history,
                [], // No additional files
                selectedMemories,
                this.currentAbortController.signal
            );
            
            // Add AI analysis response
            const responseTimestamp = this.uiUtils.formatTimestamp(new Date());
            const responseContent = data.error 
                ? `❌ **Lỗi phân tích:** ${data.error}` 
                : data.response;
            
            const customPromptUsed = window.customPromptEnabled === true;
            
            this.messageRenderer.addMessage(
                elements.chatContainer,
                responseContent,
                false,
                formValues.model,
                'programming',
                responseTimestamp,
                null,  // No thinking process
                customPromptUsed
            );
            
            // Save session
            this.saveCurrentSession(true);
            
            // Make images clickable (with retry)
            const makeClickable = () => this.messageRenderer.makeImagesClickable((img) => this.openImagePreview(img));
            setTimeout(makeClickable, 100);
            setTimeout(makeClickable, 500);
            
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('File analysis error:', error);
                const errorTimestamp = this.uiUtils.formatTimestamp(new Date());
                const customPromptUsed = window.customPromptEnabled === true;
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    `❌ **Lỗi phân tích file:** ${error.message}`,
                    false,
                    formValues.model,
                    'programming',
                    errorTimestamp,
                    null,
                    customPromptUsed
                );
            }
        } finally {
            this.uiUtils.hideLoading();
            this.currentAbortController = null;
        }
    }

    /**
     * Build file context from attached files
     */
    buildFileContext(files) {
        if (!files || files.length === 0) return '';
        
        let context = '📎 **Attached Files Context:**\n\n';
        
        files.forEach((file, index) => {
            context += `**File ${index + 1}: ${file.name}**\n`;
            context += `Type: ${file.type || 'unknown'}\n`;
            context += `Size: ${this.fileHandler.formatFileSize(file.size)}\n`;
            
            // Include text content if available
            if (file.content && typeof file.content === 'string' && !file.content.startsWith('data:')) {
                // Truncate if too long
                const maxLength = 10000;
                const content = file.content.length > maxLength 
                    ? file.content.substring(0, maxLength) + '\n...(truncated)'
                    : file.content;
                context += `\nContent:\n\`\`\`\n${content}\n\`\`\`\n`;
            } else if (file.type && file.type.startsWith('image/')) {
                // Images are sent via vision API separately, just note it here
                context += `(Image file attached — sent to vision API)\n`;
            } else if (file.content && file.content.startsWith('data:')) {
                context += `(Binary file — text extraction unavailable)\n`;
            }
            context += '\n---\n\n';
        });
        
        return context;
    }

    /**
     * Stop current generation
     */
    stopGeneration() {
        if (this.currentAbortController) {
            this.currentAbortController.abort();
            console.log('[App] Generation stopped by user');
            
            // Show notification
            const elements = this.uiUtils.elements;
            const timestamp = this.uiUtils.formatTimestamp(new Date());
            
            // Find the last assistant message and mark it as partial
            const messages = Array.from(elements.chatContainer.children);
            const lastMessage = messages[messages.length - 1];
            
            if (lastMessage && lastMessage.classList.contains('assistant')) {
                // Add "stopped" indicator
                const messageContent = lastMessage.querySelector('.message-content');
                if (messageContent) {
                    const stoppedIndicator = document.createElement('div');
                    stoppedIndicator.className = 'message-stopped-indicator';
                    stoppedIndicator.innerHTML = '⏹️ <em>Đã dừng bởi người dùng</em>';
                    messageContent.appendChild(stoppedIndicator);
                }
                
                // Save this partial response as version 1
                const messageText = lastMessage.querySelector('.message-text')?.innerHTML || '';
                if (this.currentMessageId) {
                    if (!this.messageHistory[this.currentMessageId]) {
                        this.messageHistory[this.currentMessageId] = [];
                    }
                    this.messageHistory[this.currentMessageId].push({
                        version: 1,
                        content: messageText,
                        timestamp: timestamp,
                        stopped: true
                    });
                }
            }
            
            // Save session
            this.saveCurrentSession(true);
            
            this.currentAbortController = null;
        }
    }

    /**
     * Build conversation history
     */
    buildConversationHistory() {
        const elements = this.uiUtils.elements;
        const messages = Array.from(elements.chatContainer.children);
        const history = [];
        
        messages.forEach(msgEl => {
            const isUser = msgEl.classList.contains('user');
            const content = msgEl.querySelector('.message-text')?.textContent || '';
            
            history.push({
                role: isUser ? 'user' : 'assistant',
                content: content
            });
        });
        
        return history;
    }

    /**
     * Save current session
     */
    async saveCurrentSession(updateTimestamp = false) {
        const elements = this.uiUtils.elements;

        // Sync per-version downstream branches before persisting HTML.
        this.syncConversationBranches();

        // Exclude the welcome screen element from saved messages
        const messages = Array.from(elements.chatContainer.children)
            .filter(el => el.id !== 'welcomeScreen')
            .map(el => el.outerHTML);
        console.log('[DEBUG] saveCurrentSession: chatId=', this.chatManager.currentChatId, 'messages=', messages.length, 'updateTimestamp=', updateTimestamp);
        
        this.chatManager.updateCurrentSession(messages, updateTimestamp);
        await this.chatManager.saveSessions();
        
        this.uiUtils.updateStorageDisplay(this.chatManager.getStorageInfo());
        this.uiUtils.renderChatList(
            this.chatManager.chatSessions,
            this.chatManager.currentChatId,
            (chatId) => this.handleSwitchChat(chatId),
            (chatId) => this.handleDeleteChat(chatId),
            (fromId, toId, position) => this.handleReorderChat(fromId, toId, position),
            (chatId) => this.handleTogglePin(chatId)
        );
    }

    syncConversationBranches() {
        const session = this.chatManager.getCurrentSession();
        const chatContainer = this.uiUtils?.elements?.chatContainer;
        if (!session || !chatContainer) return;

        if (!session.conversationBranches) {
            session.conversationBranches = {};
        }

        const allMessages = Array.from(chatContainer.children).filter(el => el.id !== 'welcomeScreen');
        allMessages.forEach((msgEl, idx) => {
            if (!msgEl.classList.contains('user')) return;
            const messageId = msgEl.dataset.messageId;
            if (!messageId) return;

            const currentVersion = parseInt(msgEl.dataset.currentVersion || '0', 10);
            if (Number.isNaN(currentVersion)) return;

            if (!session.conversationBranches[messageId]) {
                session.conversationBranches[messageId] = {};
            }

            const downstream = allMessages.slice(idx + 1).map(el => el.outerHTML);
            session.conversationBranches[messageId][currentVersion] = downstream;
        });
    }

    applyVersionBranch(messageDiv, versionIndex) {
        const session = this.chatManager.getCurrentSession();
        const chatContainer = this.uiUtils?.elements?.chatContainer;
        if (!session || !chatContainer || !messageDiv) return;

        const messageId = messageDiv.dataset.messageId;
        if (!messageId) return;

        const branchesByMessage = session.conversationBranches?.[messageId];
        if (!branchesByMessage) return;

        const branchMessages = branchesByMessage[versionIndex];
        if (!Array.isArray(branchMessages)) return;

        // Remove everything after anchor message.
        let node = messageDiv.nextElementSibling;
        while (node) {
            const next = node.nextElementSibling;
            node.remove();
            node = next;
        }

        // Rebuild downstream branch from snapshot.
        branchMessages.forEach(html => {
            const temp = document.createElement('div');
            temp.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(html) : html;
            const newNode = temp.firstElementChild;
            if (newNode) {
                chatContainer.appendChild(newNode);
            }
        });

        // Re-attach actions after DOM restore.
        this.messageRenderer.reattachEventListeners(
            chatContainer,
            null,
            null,
            (img) => this.openImagePreview(img)
        );
        this.messageRenderer.makeImagesClickable((img) => this.openImagePreview(img));

        // Persist selected branch immediately (without bumping updatedAt order).
        this.saveCurrentSession(false);
    }

    /**
     * Fork session from a specific message
     */
    handleForkSession(messageDiv) {
        const chatContainer = this.uiUtils.elements.chatContainer;
        const allMessages = Array.from(chatContainer.children).filter(el => el.id !== 'welcomeScreen');
        const msgIndex = allMessages.indexOf(messageDiv);
        if (msgIndex === -1) return;

        // Save current session first so messages array is up-to-date
        this.saveCurrentSession();

        const sourceChatId = this.chatManager.currentChatId;
        const newId = this.chatManager.forkSession(sourceChatId, msgIndex);
        if (!newId) return;

        // Load the forked session
        this.loadCurrentChat();
        this.renderChatList();

        // Scroll to bottom
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Brief notification
        const lang = localStorage.getItem('chatbot_language') || 'vi';
        this.showForkNotification(
            lang === 'vi'
                ? '🔀 Đã tách nhánh! Bạn có thể tiếp tục chat từ đây.'
                : '🔀 Forked! You can continue chatting from here.'
        );
    }

    /**
     * Show a temporary toast notification for fork
     */
    showForkNotification(message) {
        const toast = document.createElement('div');
        toast.className = 'fork-toast';
        toast.textContent = message;
        document.body.appendChild(toast);
        requestAnimationFrame(() => toast.classList.add('show'));
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 2500);
    }

    /**
     * Clear chat
     */
    clearChat() {
        if (!this.uiUtils.showConfirm('Bạn có chắc muốn xóa toàn bộ lịch sử chat này?')) {
            return;
        }
        // Close thinking side panel on clear
        if (window.ThinkingPanel) window.ThinkingPanel.close();
        this.uiUtils.clearChat();
        // Show welcome screen again
        this.uiUtils.showWelcomeScreen();
        this.chatManager.updateCurrentSession([]);
        
        // Also clear files for this session
        this.fileHandler.clearSessionFiles();
        this.fileHandler.renderSessionFiles(this.uiUtils.elements.fileList);
        this.saveFilesToCurrentSession();
        
        this.saveCurrentSession();
    }

    /**
     * New chat
     */
    newChat() {
        this.saveCurrentSession();
        this.chatManager.newChat();
        this.uiUtils.clearChat();
        this.uiUtils.showWelcomeScreen();
        
        // Clear files when creating new chat
        this.fileHandler.clearSessionFiles();
        this.fileHandler.renderSessionFiles(this.uiUtils.elements.fileList);
        
        this.saveCurrentSession();
        this.renderChatList();
    }

    /**
     * Switch chat
     */
    handleSwitchChat(chatId) {
        this.saveCurrentSession();
        this.chatManager.switchChat(chatId);
        this.loadCurrentChat();
        this.saveCurrentSession();
        
        // Close sidebar on mobile
        if (window.innerWidth <= 768) {
            this.uiUtils.closeSidebar();
        }
    }

    /**
     * Delete chat
     */
    handleDeleteChat(chatId) {
        if (!this.uiUtils.showConfirm('Bạn có chắc muốn xóa cuộc trò chuyện này?')) {
            return;
        }

        const wasCurrent = chatId === this.chatManager.currentChatId;
        
        const result = this.chatManager.deleteChat(chatId);
        
        if (!result.success) {
            this.uiUtils.showAlert(result.message);
            return;
        }

        if (result.remainingCount === 0) {
            this.uiUtils.clearChat();
            this.uiUtils.showWelcomeScreen();
            this.fileHandler.clearSessionFiles();
            this.fileHandler.renderSessionFiles(this.uiUtils.elements.fileList);
        } else if (wasCurrent) {
            this.loadCurrentChat();
        }

        this.renderChatList();
        this.uiUtils.updateStorageDisplay(this.chatManager.getStorageInfo());
    }

    /**
     * Toggle tool
     */
    toggleTool(tool, button) {
        if (this.activeTools.has(tool)) {
            this.activeTools.delete(tool);
            button.classList.remove('active');
        } else {
            this.activeTools.add(tool);
            button.classList.add('active');
        }
    }

    /**
     * Check local models status
     */
    async checkLocalModels() {
        const data = await this.apiService.checkLocalModelsStatus();
        if (data.available && data.models) {
            this.uiUtils.updateModelOptions(data.models);
        }
    }

    /**
     * Open image generation modal
     */
    async openImageGenModal() {
        await this.imageGen.openModal();
    }

    /**
     * Toggle memory panel
     */
    async toggleMemoryPanel() {
        const elements = this.uiUtils.elements;
        const isVisible = elements.memoryPanel.style.display !== 'none';
        
        elements.memoryPanel.style.display = isVisible ? 'none' : 'block';
        
        if (!isVisible) {
            await this.memoryManager.loadMemories();
            this.memoryManager.renderMemoryList(
                elements.memoryListEl,
                null,
                async (memoryId) => {
                    if (this.uiUtils.showConfirm('Xóa memory này?')) {
                        await this.memoryManager.deleteMemory(memoryId);
                        this.memoryManager.renderMemoryList(elements.memoryListEl, null, null);
                    }
                }
            );
        }
    }

    /**
     * Save current chat as memory
     */
    async saveCurrentChatAsMemory() {
        const elements = this.uiUtils.elements;
        const messages = Array.from(elements.chatContainer.children);
        
        if (messages.length === 0) {
            this.uiUtils.showAlert('Không có nội dung để lưu!');
            return;
        }
        
        // Build content
        const content = this.memoryManager.buildMemoryContent(elements.chatContainer);
        const images = this.memoryManager.extractImagesFromChat(elements.chatContainer);
        
        // Generate title
        const firstUserMsg = messages.find(m => m.classList.contains('user'));
        const firstText = firstUserMsg?.querySelector('.message-text')?.textContent || 'Untitled';
        const title = await this.chatManager.generateTitle(firstText);
        
        try {
            await this.memoryManager.saveMemory(title, content, images);
            this.uiUtils.showAlert('✅ Đã lưu vào bộ nhớ AI!');
            await this.toggleMemoryPanel(); // Refresh
        } catch (error) {
            this.uiUtils.showAlert('❌ Lỗi khi lưu: ' + error.message);
        }
    }

    /**
     * Export chat
     */
    async exportChat() {
        const elements = this.uiUtils.elements;
        
        // Show loading message
        const customPromptUsed = window.customPromptEnabled === true;
        const loadingMsg = this.messageRenderer.addMessage(
            elements.chatContainer,
            '🔄 Đang tạo PDF...',
            false,
            'System',
            'casual',
            this.uiUtils.formatTimestamp(new Date()),
            null,
            customPromptUsed
        );
        
        const success = await this.exportHandler.downloadChatAsPDF(
            elements.chatContainer,
            (status) => console.log('[Export]', status)
        );
        
        // Remove loading message
        if (loadingMsg) {
            loadingMsg.remove();
        }
    }

    /**
     * Handle edit save
     */
    async handleEditSave(messageDiv, newContent, originalContent) {
        if (!newContent.trim()) {
            this.uiUtils.showAlert('Tin nhắn không được để trống!');
            return;
        }
        
        if (newContent === originalContent) {
            this.uiUtils.showAlert('Nội dung không thay đổi!');
            return;
        }
        
        const elements = this.uiUtils.elements;
        const allMessages = Array.from(elements.chatContainer.children);
        const messageIndex = allMessages.indexOf(messageDiv);
        
        // Build history before edit
        const historyBeforeEdit = [];
        for (let i = 0; i < messageIndex; i++) {
            const msg = allMessages[i];
            const isUser = msg.classList.contains('user');
            const textContent = msg.querySelector('.message-text')?.textContent || '';
            
            historyBeforeEdit.push({
                role: isUser ? 'user' : 'assistant',
                content: textContent
            });
        }
        
        // Update message text
        const textDiv = messageDiv.querySelector('.message-text');
        textDiv.textContent = newContent;
        messageDiv.querySelector('.edit-form')?.remove();
        
        // Remove messages after this one
        for (let i = allMessages.length - 1; i > messageIndex; i--) {
            allMessages[i].remove();
        }
        
        // Show loading
        this.uiUtils.showLoading();
        
        try {
            const formValues = this.uiUtils.getFormValues();
            const data = await this.apiService.sendMessage(
                newContent,
                formValues.model,
                formValues.context,
                [],
                formValues.deepThinking,
                historyBeforeEdit,
                [],
                []
            );
            
            const responseTimestamp = this.uiUtils.formatTimestamp(new Date());
            const responseContent = data.error ? `❌ **Lỗi:** ${data.error}` : data.response;
            const customPromptUsed = window.customPromptEnabled === true;
            
            this.messageRenderer.addMessage(
                elements.chatContainer,
                responseContent,
                false,
                formValues.model,
                formValues.context,
                responseTimestamp,
                null,
                customPromptUsed
            );
            
            // Update version history with the new response
            const messageId = messageDiv.dataset.messageId;
            if (messageId) {
                const history = this.messageRenderer.getMessageHistory(messageId);
                if (history.length > 0) {
                    // Update the last version with the response
                    history[history.length - 1].assistantResponse = responseContent;
                    
                    // Save to chatManager localStorage
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
            }
            
            // Save session
            await this.saveCurrentSession();
            
        } catch (error) {
            this.uiUtils.showAlert('❌ Lỗi kết nối: ' + error.message);
        } finally {
            this.uiUtils.hideLoading();
        }
    }

    /**
     * Open image preview
     */
    openImagePreview(imgElement) {
        console.log('[Image Preview] Opening preview...');
        this.messageRenderer.openImagePreview(imgElement);
    }
    
    /**
     * Setup MCP Tab switching and functionality
     */
    setupMcpTabs() {
        const tabs = document.querySelectorAll('#mcpTabFolder, #mcpTabUrl, #mcpTabUpload');
        const folderSource = document.getElementById('mcpFolderSource');
        const urlSource = document.getElementById('mcpUrlSource');
        const uploadSource = document.getElementById('mcpUploadSource');
        const mcpEnabledCheck = document.getElementById('mcpEnabledCheck');
        
        // Store for MCP context
        this.mcpContext = {
            enabled: false,
            folders: [],
            urls: [],
            uploads: []
        };
        
        // Tab switching
        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                if (tab.disabled) return;
                
                // Update active state
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                
                // Show/hide source panels
                const source = tab.dataset.source;
                if (folderSource) folderSource.style.display = source === 'folder' ? 'block' : 'none';
                if (urlSource) urlSource.style.display = source === 'url' ? 'block' : 'none';
                if (uploadSource) uploadSource.style.display = source === 'upload' ? 'block' : 'none';
            });
        });
        
        // MCP Enable/Disable
        if (mcpEnabledCheck) {
            mcpEnabledCheck.addEventListener('change', () => {
                const enabled = mcpEnabledCheck.checked;
                this.mcpContext.enabled = enabled;
                tabs.forEach(tab => tab.disabled = !enabled);
                
                // Update status badge
                const status = document.getElementById('mcpStatus');
                if (status) {
                    status.innerHTML = enabled 
                        ? '<span style="color: #10b981;">🟢 Đang bật</span>' 
                        : '<span>⚪ Off</span>';
                    status.classList.toggle('active', enabled);
                }
                
                // Enable/disable inputs
                const selectFolderBtn = document.getElementById('mcpSelectFolderBtn');
                const urlInput = document.getElementById('mcpUrlInput');
                const fetchUrlBtn = document.getElementById('mcpFetchUrlBtn');
                const uploadBtn = document.getElementById('mcpUploadBtn');
                const searchInput = document.getElementById('mcpFileSearch');
                
                if (selectFolderBtn) selectFolderBtn.disabled = !enabled;
                if (urlInput) urlInput.disabled = !enabled;
                if (fetchUrlBtn) fetchUrlBtn.disabled = !enabled;
                if (uploadBtn) uploadBtn.disabled = !enabled;
                if (searchInput) searchInput.disabled = !enabled;
            });
        }
        
        // Folder picker using webkitdirectory
        const selectFolderBtn = document.getElementById('mcpSelectFolderBtn');
        const folderInput = document.getElementById('mcpFolderInput');
        const folderList = document.getElementById('mcpFolderList');
        
        if (selectFolderBtn && folderInput) {
            selectFolderBtn.addEventListener('click', () => folderInput.click());
            
            folderInput.addEventListener('change', async (e) => {
                const files = e.target.files;
                if (!files.length) return;
                
                // Get folder name from first file's path
                const firstPath = files[0].webkitRelativePath || files[0].name;
                const folderName = firstPath.split('/')[0];
                
                // Show loading
                selectFolderBtn.innerHTML = '⏳ Đang tải...';
                selectFolderBtn.disabled = true;
                
                try {
                    // Process files from folder
                    const folderData = {
                        name: folderName,
                        files: [],
                        content: ''
                    };
                    
                    // Read file contents (limit to text files and certain extensions)
                    const textExtensions = ['.txt', '.md', '.py', '.js', '.ts', '.json', '.html', '.css', '.yaml', '.yml', '.xml', '.csv', '.sql', '.sh', '.bat'];
                    
                    for (const file of files) {
                        const ext = '.' + file.name.split('.').pop().toLowerCase();
                        if (textExtensions.includes(ext) && file.size < 100000) { // Max 100KB per file
                            try {
                                const content = await file.text();
                                folderData.files.push({
                                    path: file.webkitRelativePath,
                                    name: file.name,
                                    content: content.substring(0, 5000) // Limit content
                                });
                            } catch (err) {
                                console.log(`[MCP] Skip unreadable file: ${file.name}`);
                            }
                        }
                    }
                    
                    // Build summary content
                    folderData.content = folderData.files.map(f => 
                        `--- ${f.path} ---\n${f.content}`
                    ).join('\n\n');
                    
                    // Add to context
                    this.mcpContext.folders.push(folderData);
                    
                    // Show in list
                    if (folderList) {
                        folderList.style.display = 'block';
                        const tag = document.createElement('div');
                        tag.className = 'mcp-folder-tag';
                        tag.innerHTML = `📁 ${this._escapeHtml(folderName)} (${folderData.files.length} files) <button class="mcp-remove-btn" data-type="folder" data-name="${this._escapeHtml(folderName)}">×</button>`;
                        tag.querySelector('button').addEventListener('click', (e) => {
                            this.mcpContext.folders = this.mcpContext.folders.filter(f => f.name !== folderName);
                            tag.remove();
                            if (folderList.children.length === 0) folderList.style.display = 'none';
                            this.updateMcpIndicator();
                        });
                        folderList.appendChild(tag);
                    }
                    
                    // Update file browser display
                    this.updateMcpFileList();
                    this.updateMcpIndicator();
                    
                } catch (error) {
                    console.error('[MCP] Folder read error:', error);
                    alert('Lỗi đọc folder');
                } finally {
                    selectFolderBtn.innerHTML = '📁 <span>Select Folder</span>';
                    selectFolderBtn.disabled = false;
                    folderInput.value = '';
                }
            });
        }
        
        // URL Fetch button
        const fetchUrlBtn = document.getElementById('mcpFetchUrlBtn');
        const urlInput = document.getElementById('mcpUrlInput');
        if (fetchUrlBtn && urlInput) {
            fetchUrlBtn.addEventListener('click', async () => {
                const url = urlInput.value.trim();
                if (!url) return;
                
                fetchUrlBtn.disabled = true;
                fetchUrlBtn.innerHTML = '⏳...';
                
                try {
                    const response = await fetch('/api/mcp/fetch-url', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ url })
                    });
                    
                    const data = await response.json();
                    if (data.success) {
                        // Store URL content
                        this.mcpContext.urls.push({
                            url: url,
                            title: data.title,
                            content: data.content
                        });
                        
                        // Add to URL list
                        const urlList = document.getElementById('mcpUrlList');
                        if (urlList) {
                            const tag = document.createElement('div');
                            tag.className = 'mcp-folder-tag';
                            const hostname = new URL(url.startsWith('http') ? url : 'https://' + url).hostname;
                            tag.innerHTML = `🌐 ${this._escapeHtml(hostname)} <button class="mcp-remove-btn">×</button>`;
                            tag.querySelector('button').addEventListener('click', () => {
                                this.mcpContext.urls = this.mcpContext.urls.filter(u => u.url !== url);
                                tag.remove();
                                this.updateMcpIndicator();
                            });
                            urlList.appendChild(tag);
                        }
                        urlInput.value = '';
                        this.updateMcpIndicator();
                    } else {
                        alert('Lỗi fetch URL: ' + (data.error || 'Unknown error'));
                    }
                } catch (error) {
                    console.error('[MCP] URL fetch error:', error);
                    alert('Lỗi kết nối');
                } finally {
                    fetchUrlBtn.disabled = false;
                    fetchUrlBtn.innerHTML = '🔍 Fetch';
                }
            });
        }
        
        // Upload button with OCR
        const uploadBtn = document.getElementById('mcpUploadBtn');
        const fileUpload = document.getElementById('mcpFileUpload');
        if (uploadBtn && fileUpload) {
            uploadBtn.addEventListener('click', () => fileUpload.click());
            
            fileUpload.addEventListener('change', async (e) => {
                const files = e.target.files;
                if (!files.length) return;
                
                const uploadList = document.getElementById('mcpUploadList');
                uploadBtn.innerHTML = '⏳ Đang xử lý...';
                uploadBtn.disabled = true;
                
                for (const file of files) {
                    try {
                        // Upload file and get OCR content
                        const formData = new FormData();
                        formData.append('file', file);
                        
                        const response = await fetch('/api/mcp/upload-file', {
                            method: 'POST',
                            body: formData
                        });
                        
                        const data = await response.json();
                        
                        if (data.success) {
                            this.mcpContext.uploads.push({
                                filename: file.name,
                                content: data.content
                            });
                            
                            // Show file tag
                            if (uploadList) {
                                const tag = document.createElement('div');
                                tag.className = 'mcp-folder-tag';
                                tag.innerHTML = `📄 ${this._escapeHtml(file.name)} <button class="mcp-remove-btn">×</button>`;
                                tag.querySelector('button').addEventListener('click', () => {
                                    this.mcpContext.uploads = this.mcpContext.uploads.filter(u => u.filename !== file.name);
                                    tag.remove();
                                    this.updateMcpIndicator();
                                });
                                uploadList.appendChild(tag);
                            }
                        }
                    } catch (error) {
                        console.error(`[MCP] Upload error for ${file.name}:`, error);
                    }
                }
                
                uploadBtn.innerHTML = '📤 <span>Upload Files (OCR)</span>';
                uploadBtn.disabled = false;
                fileUpload.value = '';
                this.updateMcpIndicator();
            });
        }
    }
    
    // Update MCP indicator showing context count
    updateMcpIndicator() {
        const count = this.mcpContext.folders.length + this.mcpContext.urls.length + this.mcpContext.uploads.length;
        const badge = document.getElementById('selectedFileCount');
        const selectedFiles = document.getElementById('mcpSelectedFiles');
        
        if (badge) badge.textContent = count;
        if (selectedFiles) {
            selectedFiles.style.display = count > 0 ? 'block' : 'none';
        }
    }
    
    // Update MCP file list display
    updateMcpFileList() {
        const fileList = document.getElementById('mcpFileList');
        if (!fileList) return;
        
        const allFiles = [];
        
        // Add folder files
        this.mcpContext.folders.forEach(folder => {
            folder.files.forEach(file => {
                allFiles.push({ type: 'folder', icon: '📄', name: file.path });
            });
        });
        
        // Add URLs
        this.mcpContext.urls.forEach(url => {
            allFiles.push({ type: 'url', icon: '🌐', name: url.title || url.url });
        });
        
        // Add uploads
        this.mcpContext.uploads.forEach(upload => {
            allFiles.push({ type: 'upload', icon: '📎', name: upload.filename });
        });
        
        if (allFiles.length === 0) {
            fileList.innerHTML = `<div class="mcp-empty-state">
                <p>📂</p>
                <p style="font-size: 13px; font-weight: 600; color: #667eea;">No context loaded</p>
                <p style="font-size: 11px; color: #888;">Enable MCP and select a source</p>
            </div>`;
            return;
        }
        
        fileList.innerHTML = allFiles.map(f => 
            `<div class="mcp-file-item">${f.icon} ${f.name}</div>`
        ).join('');
    }
    
    // Get MCP context for injection into message
    getMcpContextString() {
        if (!this.mcpContext || !this.mcpContext.enabled) return '';
        
        const parts = [];
        
        // Folder contents
        this.mcpContext.folders.forEach(folder => {
            parts.push(`[Folder: ${folder.name}]\n${folder.content}`);
        });
        
        // URL contents
        this.mcpContext.urls.forEach(url => {
            parts.push(`[URL: ${url.title}]\n${url.content}`);
        });
        
        // Upload contents
        this.mcpContext.uploads.forEach(upload => {
            parts.push(`[File: ${upload.filename}]\n${upload.content}`);
        });
        
        return parts.join('\n\n---\n\n');
    }

    /**
     * Auto-generate conversation title using qwen2.5:0.5b via Ollama
     * Triggers only when the title is still the default placeholder
     * @param {string} rawUserMessage - The latest user message (before any context injection)
     */
    async autoGenerateTitleIfNeeded(rawUserMessage) {
        const session = this.chatManager.getCurrentSession();
        if (!session) return;
        const lang = localStorage.getItem('chatbot_language') || 'vi';
        const defaults = ['Cuộc trò chuyện mới', 'New conversation', 'Untitled'];
        if (!defaults.includes(session.title)) return; // already has a meaningful title
        try {
            const title = await this.chatManager.generateTitle(rawUserMessage);
            if (title && !defaults.includes(title)) {
                session.title = title;
                await this.chatManager.saveSessions();
                this.renderChatList();
                console.log('[AutoTitle] Title set to:', title);
            }
        } catch (e) {
            console.error('[AutoTitle] Error:', e);
        }
    }
}

// ── Image overlay button handlers (global) ──────────────────────────────────

window._igv2Download = function(imgSrc, imageId) {
    const a = document.createElement('a');
    // Prefer the local serve URL for clean filename
    a.href = imageId ? `/api/image-gen/images/${imageId}` : imgSrc;
    a.download = imageId ? `${imageId}.png` : 'generated.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
};

window._igv2Info = async function(imageId, triggerEl) {
    // Remove any existing popup first
    document.querySelectorAll('.igv2-info-popup').forEach(p => p.remove());
    if (!imageId) return;

    const popup = document.createElement('div');
    popup.className = 'igv2-info-popup';
    popup.textContent = 'Đang tải…';
    triggerEl.closest('.igv2-chat-image').appendChild(popup);

    try {
        const resp = await fetch(`/api/image-gen/meta/${imageId}`);
        if (!resp.ok) throw new Error('Not found');
        const m = await resp.json();
        const _esc = (s) => { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; };
        const rawHtml = [
            m.provider ? `<b>Provider:</b> ${_esc(m.provider)}` : '',
            m.model    ? `<b>Model:</b> ${_esc(m.model)}` : '',
            m.prompt   ? `<b>Prompt:</b> ${_esc(m.prompt.substring(0,200))}` : '',
            m.created_at ? `<b>Created:</b> ${_esc(new Date(m.created_at).toLocaleString())}` : '',
            m.image_id ? `<b>ID:</b> ${_esc(m.image_id)}` : '',
        ].filter(Boolean).join('<br>');
        popup.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;
    } catch {
        popup.textContent = 'Không tải được thông tin.';
    }

    // Close on outside click
    const close = (e) => { if (!popup.contains(e.target) && e.target !== triggerEl) { popup.remove(); document.removeEventListener('click', close, true); } };
    setTimeout(() => document.addEventListener('click', close, true), 50);
};

window._igv2Save = async function(imageId, triggerEl) {
    if (!imageId) return;
    triggerEl.disabled = true;
    triggerEl.textContent = '⏳';
    try {
        const resp = await fetch(`/api/image-gen/save/${imageId}`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            triggerEl.textContent = '✅';
            triggerEl.title = data.drive_url ? `Drive: ${data.drive_url}` : 'Đã lưu!';
            if (data.drive_url) {
                const a = document.createElement('a');
                a.href = data.drive_url;
                a.target = '_blank';
                a.style.cssText = 'position:absolute;opacity:0;pointer-events:none';
                // Don't auto-open; just update tooltip
            }
        } else {
            triggerEl.textContent = '❌';
            triggerEl.title = data.error || 'Lỗi khi lưu';
            setTimeout(() => { triggerEl.textContent = '☁'; triggerEl.disabled = false; }, 3000);
        }
    } catch (e) {
        triggerEl.textContent = '❌';
        triggerEl.title = String(e);
        setTimeout(() => { triggerEl.textContent = '☁'; triggerEl.disabled = false; }, 3000);
    }
};

if (!window.__igv2OverlayDelegationBound) {
    window.__igv2OverlayDelegationBound = true;
    document.addEventListener('click', (event) => {
        const actionBtn = event.target.closest('.igv2-img-btn[data-igv2-action]');
        if (actionBtn) {
            event.preventDefault();
            event.stopPropagation();

            const action = actionBtn.getAttribute('data-igv2-action');
            const imageId = actionBtn.getAttribute('data-image-id') || '';
            const imgSrc = actionBtn.getAttribute('data-img-src') || '';

            if (action === 'download') {
                window._igv2Download(imgSrc, imageId);
            } else if (action === 'info') {
                window._igv2Info(imageId, actionBtn);
            } else if (action === 'save') {
                window._igv2Save(imageId, actionBtn);
            }
            return;
        }

        const imageEl = event.target.closest('.igv2-chat-image img[data-igv2-open]');
        if (imageEl) {
            const targetUrl = imageEl.getAttribute('data-igv2-open');
            if (targetUrl) {
                window.open(targetUrl, '_blank', 'noopener');
            }
        }
    });
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new ChatBotApp();
    app.init();
    
    // Expose to window for global access
    window.chatBotApp = app;
    
    // === GALLERY MODAL: Click overlay to close ===
    const galleryModal = document.getElementById('galleryModal');
    if (galleryModal) {
        galleryModal.addEventListener('click', (e) => {
            // Close if clicking the modal overlay itself
            if (e.target === galleryModal) {
                closeGallery();
            }
        });
    }
    
    // Helper function to display extracted tags for Img2Img
    function displayExtractedTags(tags, categories) {
        const container = document.getElementById('extractedTags');
        const list = document.getElementById('tagsList');
        
        if (!container || !list) {
            console.error('[Display Tags] Container or list not found');
            return;
        }
        
        // Category icons
        const categoryIcons = {
            hair: '💇', eyes: '👀', face: '😊', clothing: '👗',
            accessories: '💍', body: '🧘', pose: '🤸', background: '🌄',
            character: '👤', style: '🎨', quality: '⭐', other: '🏷️'
        };
        
        // Initialize selectedTags if not exists (all selected by default)
        if (!window.selectedImageTags) {
            window.selectedImageTags = new Set(tags.map(t => t.name));
        }
        
        // Build HTML by category
        let html = '';
        Object.keys(categories).forEach(catName => {
            const catTags = categories[catName];
            if (!catTags || catTags.length === 0) return;
            
            const icon = categoryIcons[catName] || '🏷️';
            const catTitle = catName.charAt(0).toUpperCase() + catName.slice(1);
            
            html += `
                <div class="tag-category">
                    <div class="category-header" onclick="toggleCategory('${catName}')">
                        ${icon} <strong>${catTitle}</strong> (${catTags.length})
                        <span class="category-toggle">▼</span>
                    </div>
                    <div class="category-tags" id="cat-${catName}">
                        ${catTags.map(tag => {
                            const isSelected = window.selectedImageTags.has(tag.name);
                            return `
                            <span class="tag-item ${isSelected ? 'tag-selected' : 'tag-unselected'}" 
                                  onclick="toggleImageTag('${tag.name.replace(/'/g, "\\'")}', this)" 
                                  title="${isSelected ? 'Click để bỏ chọn' : 'Click để chọn'} (Confidence: ${(tag.confidence * 100).toFixed(1)}%)">
                                ${tag.name} <small>(${(tag.confidence * 100).toFixed(0)}%)</small>
                            </span>
                        `}).join('')}
                    </div>
                </div>
            `;
        });
        
        list.innerHTML = html;
        container.style.display = 'block';
        
        // Enable generate button
        const generateBtn = document.getElementById('generateImg2ImgBtn');
        if (generateBtn) {
            generateBtn.disabled = false;
        }
        
        console.log('[Display Tags] Displayed', tags.length, 'tags in', Object.keys(categories).length, 'categories');
    }
    
    // Expose image generation functions for onclick handlers
    window.closeImageModal = () => app.imageGen.closeModal();
    window.switchImageGenTab = (tab) => app.imageGen.switchTab(tab);
    window.randomPrompt = () => app.imageGen.randomPrompt();
    window.randomNegativePrompt = () => app.imageGen.randomNegativePrompt();
    window.randomImg2ImgPrompt = () => app.imageGen.randomImg2ImgPrompt();
    window.randomImg2ImgNegativePrompt = () => app.imageGen.randomImg2ImgNegativePrompt();
    window.addLoraSelection = () => app.imageGen.addLoraSelection();
    window.addImg2imgLoraSelection = () => app.imageGen.addImg2imgLoraSelection();
    window.removeLoraSelection = (id) => app.imageGen.removeLoraSelection(id);
    window.removeImg2imgLoraSelection = (id) => app.imageGen.removeImg2imgLoraSelection(id);
    
    window.generateImage = async () => {
        const btn = document.getElementById('generateImageBtn');
        if (!btn) return;
        
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ Đang tạo ảnh...';
        
        try {
            await app.imageGen.generateText2Img();
            // Ảnh sẽ tự động hiện trong chat, không cần alert
        } catch (error) {
            console.error('[Generate Image] Error:', error);
            app.uiUtils.showAlert('❌ Lỗi: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };
    
    window.generateImg2Img = async () => {
        const btn = document.getElementById('generateImg2ImgBtn');
        if (!btn) return;
        
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ Đang tạo ảnh...';
        
        try {
            await app.imageGen.generateImg2Img();
            // Ảnh sẽ tự động hiện trong chat, không cần alert
        } catch (error) {
            console.error('[Generate Img2Img] Error:', error);
            app.uiUtils.showAlert('❌ Lỗi: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };
    
    window.extractFeatures = async () => {
        const btn = event.target;
        if (!btn) return;
        
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ Đang trích xuất...';
        
        try {
            const data = await app.imageGen.extractFeatures();
            
            if (data && data.tags) {
                // Display tags in UI
                displayExtractedTags(data.tags, data.categories || {});
                alert(`✅ Đã trích xuất ${data.tags.length} tags!`);
            }
        } catch (error) {
            console.error('[Extract Features] Error:', error);
            alert('❌ Lỗi: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };
    
    window.autoGeneratePromptFromTags = async () => {
        const btn = event.target;
        if (!btn) return;
        
        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '🤖 Đang tạo prompt & chọn best options...';
        
        try {
            const result = await app.imageGen.generatePromptFromTags();
            
            if (result && result.prompt) {
                const promptTextarea = document.getElementById('img2imgPrompt');
                const negativeTextarea = document.getElementById('img2imgNegativePrompt');
                
                if (promptTextarea) {
                    promptTextarea.value = result.prompt;
                    promptTextarea.style.transition = 'all 0.3s';
                    promptTextarea.style.boxShadow = '0 0 20px rgba(102, 126, 234, 0.6)';
                    setTimeout(() => { promptTextarea.style.boxShadow = ''; }, 1500);
                }
                
                if (negativeTextarea && result.negative_prompt) {
                    negativeTextarea.value = result.negative_prompt;
                    negativeTextarea.style.transition = 'all 0.3s';
                    negativeTextarea.style.boxShadow = '0 0 20px rgba(255, 87, 34, 0.6)';
                    setTimeout(() => { negativeTextarea.style.boxShadow = ''; }, 1500);
                }
                
                // Auto-pick best Model, LoRA, VAE, Sampler
                app.imageGen.autoPickBestOptions();
                
                // Scroll to prompt and show summary
                if (promptTextarea) {
                    promptTextarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }
                
                const modelVal = document.getElementById('img2imgModelSelect')?.value || '—';
                const vaeVal = document.getElementById('img2imgVaeSelect')?.value || 'Default';
                const promptPreview = result.prompt.substring(0, 60);
                alert(`✅ Auto-configured!\n\n📝 Prompt: ${promptPreview}...\n🎨 Model: ${modelVal}\n🔧 VAE: ${vaeVal}\n🎯 LoRA + params đã tự động chọn`);
            }
        } catch (error) {
            console.error('[Auto-Generate Prompt] Error:', error);
            alert('❌ Lỗi: ' + error.message + '\n\n💡 Kiểm tra GROK_API_KEY trong file .env');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };
    
    window.toggleTag = (tag) => app.imageGen.toggleTag(tag);
    window.toggleCategory = (category) => app.imageGen.toggleCategory(category);
    window.copyImageToChat = () => app.imageGen.sendImageToChat();
    window.downloadGeneratedImage = () => app.imageGen.downloadGeneratedImage();
    window.shareImageToImgBB = () => app.imageGen.shareImageToImgBB();
    window.handleSourceImageUpload = (event) => app.imageGen.handleSourceImageUpload(event);

    // Advanced image gen features
    window.applyNegativePreset = (v) => app.imageGen.applyNegativePreset(v);
    window.showPromptHistory = () => app.imageGen.showPromptHistory();
    window.handleInpaintSourceUpload = (event) => app.imageGen.handleInpaintSourceUpload(event);
    window.clearInpaintMask = () => app.imageGen.clearInpaintMask();
    window.generateInpaint = () => app.imageGen.generateInpaint();
    window.handleControlnetSourceUpload = (event) => app.imageGen.handleControlnetSourceUpload(event);
    window.generateControlNet = () => app.imageGen.generateControlNet();
    window.handleUpscaleSourceUpload = (event) => app.imageGen.handleUpscaleSourceUpload(event);
    window.generateUpscale = () => app.imageGen.generateUpscale();
    window.generateBatch = () => app.imageGen.generateBatch();
    window._showBatchImage = (idx) => {
        const results = app.imageGen._batchResults;
        if (results && results[idx]) {
            app.imageGen._showGeneratedImage(results[idx].image, 'batch');
        }
    };
    // Load negative presets on modal open
    app.imageGen.loadNegativePresets();
    window.closeGeneratedImageOverlay = (event) => {
        const container = document.getElementById('generatedImageContainer');
        if (container) {
            // If event is provided and clicked element is the overlay (not modal content), close it
            if (!event || event.target === container) {
                container.style.display = 'none';
            }
        }
    };
    
    // Expose message rendering functions
    window.openImagePreview = (img) => app.messageRenderer.openImagePreview(img);
    window.closeImagePreview = () => app.messageRenderer.closeImagePreview();
    window.downloadPreviewImage = () => app.messageRenderer.downloadPreviewImage();
    
    // Image preview zoom state
    let currentZoom = 1.0;
    
    window.zoomPreviewImage = (delta) => {
        const previewImg = document.getElementById('imagePreviewContent');
        if (previewImg) {
            currentZoom = Math.max(0.5, Math.min(5.0, currentZoom + delta));
            previewImg.style.transform = `scale(${currentZoom})`;
        }
    };
    
    window.resetPreviewZoom = () => {
        const previewImg = document.getElementById('imagePreviewContent');
        if (previewImg) {
            currentZoom = 1.0;
            previewImg.style.transform = 'scale(1)';
        }
    };

    // Pinch-to-zoom on mobile for lightbox
    (() => {
        const wrap = document.getElementById('lightboxImageWrap');
        if (!wrap) return;
        let startDist = 0;
        let startZoom = 1;
        wrap.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                startDist = Math.hypot(
                    e.touches[0].clientX - e.touches[1].clientX,
                    e.touches[0].clientY - e.touches[1].clientY
                );
                startZoom = currentZoom;
            }
        }, { passive: true });
        wrap.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                const dist = Math.hypot(
                    e.touches[0].clientX - e.touches[1].clientX,
                    e.touches[0].clientY - e.touches[1].clientY
                );
                const scale = dist / startDist;
                currentZoom = Math.max(0.5, Math.min(5.0, startZoom * scale));
                const img = document.getElementById('imagePreviewContent');
                if (img) img.style.transform = `scale(${currentZoom})`;
            }
        }, { passive: true });
        // Double-tap to toggle zoom
        let lastTap = 0;
        wrap.addEventListener('touchend', (e) => {
            if (e.touches.length > 0) return;
            const now = Date.now();
            if (now - lastTap < 300) {
                // Double tap
                if (currentZoom > 1.1) {
                    resetPreviewZoom();
                } else {
                    zoomPreviewImage(1.5);
                }
            }
            lastTap = now;
        });
        // Mouse wheel zoom
        wrap.addEventListener('wheel', (e) => {
            e.preventDefault();
            zoomPreviewImage(e.deltaY < 0 ? 0.2 : -0.2);
        }, { passive: false });

        // === Swipe-down to close lightbox ===
        let swipeStartY = 0;
        let swipeDeltaY = 0;
        let isSwiping = false;
        const modal = document.getElementById('imagePreviewModal');
        const lightboxEl = modal ? modal.querySelector('.lightbox') : null;

        wrap.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1 && currentZoom <= 1.05) {
                swipeStartY = e.touches[0].clientY;
                isSwiping = true;
                swipeDeltaY = 0;
            }
        }, { passive: true });

        wrap.addEventListener('touchmove', (e) => {
            if (!isSwiping || e.touches.length !== 1) return;
            swipeDeltaY = e.touches[0].clientY - swipeStartY;
            if (swipeDeltaY > 0 && lightboxEl) {
                const progress = Math.min(swipeDeltaY / 200, 1);
                lightboxEl.style.transform = `translateY(${swipeDeltaY}px)`;
                lightboxEl.style.opacity = 1 - progress * 0.5;
            }
        }, { passive: true });

        wrap.addEventListener('touchend', () => {
            if (!isSwiping) return;
            isSwiping = false;
            if (swipeDeltaY > 120) {
                // Swipe far enough → close
                if (lightboxEl) {
                    lightboxEl.style.transition = 'transform 0.2s, opacity 0.2s';
                    lightboxEl.style.transform = 'translateY(100%)';
                    lightboxEl.style.opacity = '0';
                }
                setTimeout(() => {
                    closeImagePreview();
                    if (lightboxEl) {
                        lightboxEl.style.transition = '';
                        lightboxEl.style.transform = '';
                        lightboxEl.style.opacity = '';
                    }
                }, 200);
            } else if (lightboxEl) {
                // Snap back
                lightboxEl.style.transition = 'transform 0.2s, opacity 0.2s';
                lightboxEl.style.transform = '';
                lightboxEl.style.opacity = '';
                setTimeout(() => { lightboxEl.style.transition = ''; }, 200);
            }
            swipeDeltaY = 0;
        });

        // === Tap background (outside image) to close ===
        wrap.addEventListener('click', (e) => {
            if (e.target === wrap && currentZoom <= 1.05) {
                closeImagePreview();
            }
        });
    })();

    // === Long-press on gallery items (mobile) to show delete ===
    (() => {
        let pressTimer = null;
        let activeItem = null;

        document.addEventListener('touchstart', (e) => {
            const item = e.target.closest('.gallery-item');
            if (!item) return;
            pressTimer = setTimeout(() => {
                // Dismiss any previously active item
                if (activeItem && activeItem !== item) {
                    activeItem.classList.remove('show-actions');
                }
                item.classList.toggle('show-actions');
                activeItem = item.classList.contains('show-actions') ? item : null;
            }, 500);
        }, { passive: true });

        document.addEventListener('touchend', () => { clearTimeout(pressTimer); });
        document.addEventListener('touchmove', () => { clearTimeout(pressTimer); });

        // Dismiss actions when tapping elsewhere
        document.addEventListener('click', (e) => {
            if (activeItem && !e.target.closest('.gallery-item')) {
                activeItem.classList.remove('show-actions');
                activeItem = null;
            }
        });
    })();

    // Toggle image tag selection
    window.toggleImageTag = (tagName, element) => {
        if (!window.selectedImageTags) {
            window.selectedImageTags = new Set();
        }
        
        if (window.selectedImageTags.has(tagName)) {
            // Deselect
            window.selectedImageTags.delete(tagName);
            element.classList.remove('tag-selected');
            element.classList.add('tag-unselected');
            element.title = `Click để chọn (${element.querySelector('small').textContent})`;
        } else {
            // Select
            window.selectedImageTags.add(tagName);
            element.classList.remove('tag-unselected');
            element.classList.add('tag-selected');
            element.title = `Click để bỏ chọn (${element.querySelector('small').textContent})`;
        }
        
        console.log('[Tag Toggle]', tagName, window.selectedImageTags.has(tagName) ? 'SELECTED' : 'UNSELECTED');
        console.log('[Tag Toggle] Total selected:', window.selectedImageTags.size);
    };
    
    // Get selected tags for prompt generation
    window.getSelectedImageTags = () => {
        return Array.from(window.selectedImageTags || []);
    };
    
    // Expose export functions
    window.downloadChatAsPDF = () => app.exportHandler.downloadChatAsPDF(app.currentSession, app.chatManager.sessions);
    window.downloadChatAsJSON = () => app.exportHandler.downloadChatAsJSON(app.currentSession, app.chatManager.sessions);
    window.downloadChatAsText = () => app.exportHandler.downloadChatAsText(app.currentSession, app.chatManager.sessions);

    // ── Advanced Model Settings panel ───────────────────────────────
    (() => {
        const ADV_STORAGE_KEY = 'adv_model_params';
        const DEFAULTS = { temperature: 0.7, temperatureDeep: 0.5, maxTokensDeep: 4096, topP: null };

        function loadAdv() {
            try { return Object.assign({}, DEFAULTS, JSON.parse(localStorage.getItem(ADV_STORAGE_KEY) || '{}')); }
            catch { return Object.assign({}, DEFAULTS); }
        }
        function saveAdv(vals) {
            localStorage.setItem(ADV_STORAGE_KEY, JSON.stringify(vals));
        }

        const panel   = document.getElementById('advSettingsPanel');
        const togBtn  = document.getElementById('advSettingsBtn');
        const resetBtn = document.getElementById('advSettingsReset');

        const sliders = {
            temperature:     document.getElementById('advTemperature'),
            temperatureDeep: document.getElementById('advTemperatureDeep'),
            maxTokensDeep:   document.getElementById('advMaxTokensDeep'),
            topP:            document.getElementById('advTopP'),
        };
        const valueEls = {
            temperature:     document.getElementById('advTemperatureVal'),
            temperatureDeep: document.getElementById('advTemperatureDeepVal'),
            maxTokensDeep:   document.getElementById('advMaxTokensDeepVal'),
            topP:            document.getElementById('advTopPVal'),
        };

        function fmt(key, val) {
            if (key === 'topP') return val >= 1 ? 'default' : String(val);
            if (key === 'maxTokensDeep') return String(val);
            return Number(val).toFixed(2);
        }

        function applyToUI(vals) {
            for (const key of Object.keys(sliders)) {
                const s = sliders[key];
                const e = valueEls[key];
                if (!s || !e) continue;
                const v = (vals[key] != null) ? vals[key] : (key === 'topP' ? 1 : DEFAULTS[key]);
                s.value = v;
                e.textContent = fmt(key, v);
            }
        }

        // Init from storage
        const current = loadAdv();
        applyToUI(current);

        // Wire sliders
        for (const [key, slider] of Object.entries(sliders)) {
            if (!slider) continue;
            slider.addEventListener('input', () => {
                const val = parseFloat(slider.value);
                valueEls[key].textContent = fmt(key, val);
                const saved = loadAdv();
                saved[key] = (key === 'topP' && val >= 1) ? null : val;
                saveAdv(saved);
            });
        }

        // Toggle panel
        if (togBtn && panel) {
            togBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const open = panel.classList.toggle('adv-settings--open');
                panel.setAttribute('aria-hidden', open ? 'false' : 'true');
                togBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
                togBtn.classList.toggle('active', open);
            });
            // Close on outside click
            document.addEventListener('click', (e) => {
                if (!panel.contains(e.target) && e.target !== togBtn) {
                    panel.classList.remove('adv-settings--open');
                    panel.setAttribute('aria-hidden', 'true');
                    togBtn.setAttribute('aria-expanded', 'false');
                    togBtn.classList.remove('active');
                }
            });
        }

        // Reset
        if (resetBtn) {
            resetBtn.addEventListener('click', () => {
                saveAdv(DEFAULTS);
                applyToUI(DEFAULTS);
            });
        }

        // Global getter for sendStreamMessage
        window.getAdvancedModelParams = () => {
            const v = loadAdv();
            return {
                temperature:     v.temperature,
                temperatureDeep: v.temperatureDeep,
                maxTokensDeep:   v.maxTokensDeep,
                topP:            v.topP, // null means "don't send"
            };
        };
    })();
    
    // === GALLERY FUNCTIONS ===
    const escapeHtml = (text) => {
        const div = document.createElement('div');
        div.textContent = text == null ? '' : String(text);
        return div.innerHTML;
    };

    window.openGallery = async () => {
        const modal = document.getElementById('galleryModal');
        const grid = document.getElementById('galleryGrid');
        const stats = document.getElementById('galleryStats');
        
        if (!modal) return;
        
        modal.classList.add('active', 'open');
        grid.innerHTML = '<div style="text-align: center; padding: 50px; color: #999;">⏳ Đang tải ảnh...</div>';
        
        try {
            const url = '/api/gallery/images?all=true';
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success && data.images.length > 0) {
                const sourceText = data.source === 'mongodb' ? ' ☁️' : ' 💾';
                stats.textContent = `📊 Tổng số: ${data.total} ảnh (Tất cả)${sourceText}`;
                
                grid.innerHTML = data.images.map(img => {
                    const metadataStr = JSON.stringify(img.metadata).replace(/"/g, '&quot;');
                    const rawFilename = img.filename || (img.path || '').split('/').pop() || '';
                    const filename = escapeHtml(rawFilename);
                    // JS-safe: escape single quotes and backslashes for onclick contexts
                    const jsFilename = rawFilename.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                    // Prefer cloud URL (ImgBB CDN) for display, fallback to local path
                    const displayUrl = escapeHtml(img.cloud_url || img.path || img.url || '');
                    const isCloud = !!img.cloud_url;
                    const hasDrive = !!img.drive_url;
                    const imageDataStr = encodeURIComponent(JSON.stringify({
                        id: img.id || '',
                        filename: rawFilename,
                        path: img.cloud_url || img.path || img.url || '',
                        cloud_url: img.cloud_url || '',
                        drive_url: img.drive_url || '',
                        share_url: img.share_url || img.drive_url || img.cloud_url || img.path || img.url || '',
                        created: img.created || img.created_at || '',
                        creator: img.creator || '',
                        db_status: img.db_status || {},
                        metadata: img.metadata || {}
                    }));
                    const jsImgId = (img.id || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                    const safePrompt = escapeHtml(img.prompt || '');
                    const safeCreated = escapeHtml(img.created || '');
                    const safeFallback = escapeHtml(img.local_path || img.path || '');
                    return `
                        <div class="gallery-item" data-path="${displayUrl}" data-filename="${filename}" data-metadata="${metadataStr}">
                            <img src="${displayUrl}" alt="${filename}" loading="lazy" onerror="this.src='${safeFallback}'">
                            ${isCloud ? '<span class="gallery-cloud-badge" title="Stored in cloud">☁️</span>' : ''}
                            ${hasDrive ? '<span class="gallery-drive-badge" title="Saved to Drive">📁</span>' : ''}
                            <div class="gallery-item-info">
                                <div style="font-size:10px;opacity:0.7;">📅 ${safeCreated}</div>
                                <div class="gallery-item-prompt" title="${safePrompt}">
                                    ${escapeHtml((img.prompt || '').substring(0, 60))}${(img.prompt || '').length > 60 ? '…' : ''}
                                </div>
                            </div>
                            <button class="gallery-info-btn" onclick="event.stopPropagation(); showGalleryImageInfo('${jsFilename}', '${jsImgId}', '${imageDataStr}')" title="Thông tin ảnh">
                                ℹ️
                            </button>
                            <button class="gallery-upload-btn" onclick="event.stopPropagation(); uploadGalleryImageToDB('${jsFilename}')" title="Upload metadata + ảnh lên MongoDB/Firebase/Drive">
                                ⬆️
                            </button>
                            <button class="gallery-delete-btn" onclick="event.stopPropagation(); deleteGalleryImage('${jsFilename}')" title="Xóa ảnh">
                                🗑️
                            </button>
                        </div>
                    `;
                }).join('');
                
                // Add click event listeners to gallery items
                document.querySelectorAll('.gallery-item').forEach(item => {
                    item.addEventListener('click', () => {
                        const path = item.getAttribute('data-path');
                        const metadataStr = item.getAttribute('data-metadata');
                        try {
                            const metadata = JSON.parse(metadataStr);
                            viewGalleryImage(path, metadata);
                        } catch (e) {
                            console.error('[Gallery] Failed to parse metadata:', e);
                            viewGalleryImage(path, {});
                        }
                    });
                });
            } else {
                const emptyMsg = showAll ? '🖼️ No pictures yet' : '🖼️ No pictures';
                grid.innerHTML = `<div class="gallery-empty">${emptyMsg}</div>`;
                stats.textContent = '📊 Total: 0 Pictures';
            }
        } catch (error) {
            console.error('[Gallery] Error:', error);
            grid.innerHTML = '<div class="gallery-empty">❌ Error while loading images</div>';
        }
    };

    // Backward compatibility: old button may still call this
    window.toggleGalleryMode = () => {
        openGallery();
    };
    
    window.closeGallery = () => {
        const modal = document.getElementById('galleryModal');
        if (modal) modal.classList.remove('active', 'open');
    };
    
    window.refreshGallery = async () => {
        console.log('[Gallery] Refreshing...');
        await openGallery();
    };

    window.showGalleryImageInfo = async (filename, imageId = '', encodedImageData = '') => {
        const modal = document.getElementById('galleryInfoModal');
        const body = document.getElementById('galleryInfoBody');
        if (!modal || !body) return;

        modal.classList.add('active', 'open');
        body.innerHTML = '<div style="padding:12px 0; color: var(--text-tertiary);">⏳ Đang tải thông tin ảnh...</div>';

        let fromCard = {};
        if (encodedImageData) {
            try {
                fromCard = JSON.parse(decodeURIComponent(encodedImageData));
            } catch (_) {}
        }

        const toSafeText = (value) => {
            if (value === null || value === undefined || value === '') return 'Khong co';
            if (typeof value === 'boolean') return value ? 'Co' : 'Khong';
            if (typeof value === 'object') return JSON.stringify(value);
            return String(value);
        };

        const toSafeLink = (value) => {
            const raw = String(value || '').trim();
            if (!raw || !/^https?:\/\//i.test(raw)) return '';
            return raw;
        };

        const dateText = (value) => {
            const raw = String(value || '').trim();
            if (!raw) return 'Khong ro';
            const d = new Date(raw);
            if (Number.isNaN(d.getTime())) return raw;
            return d.toLocaleString('vi-VN');
        };

        const renderRow = (label, value, options = {}) => {
            const full = options.full ? ' gallery-info-row--full' : '';
            const statusClass = options.statusClass ? ` ${options.statusClass}` : '';
            if (options.link) {
                const safeHref = escapeHtml(options.link);
                return `
                    <div class="gallery-info-row${full}">
                        <span class="gallery-info-label">${escapeHtml(label)}</span>
                        <a class="gallery-info-value gallery-info-value--link" href="${safeHref}" target="_blank" rel="noopener noreferrer">${escapeHtml(value)}</a>
                    </div>
                `;
            }
            if (options.status) {
                return `
                    <div class="gallery-info-row${full}">
                        <span class="gallery-info-label">${escapeHtml(label)}</span>
                        <span class="gallery-info-value gallery-info-status${statusClass}">${escapeHtml(value)}</span>
                    </div>
                `;
            }
            return `
                <div class="gallery-info-row${full}">
                    <span class="gallery-info-label">${escapeHtml(label)}</span>
                    <span class="gallery-info-value">${escapeHtml(value)}</span>
                </div>
            `;
        };

        const renderInfoBody = (payload = {}) => {
            const metadata = payload.metadata || fromCard.metadata || {};
            const db = payload.db_status || fromCard.db_status || {};
            const links = payload.links || {
                share_url: fromCard.share_url || fromCard.drive_url || fromCard.cloud_url || fromCard.path || '',
                drive_folder_url: 'https://drive.google.com/drive/folders/11MN5m72gl84LsP1NMfBjeX9YAzsIlRxz?usp=sharing'
            };

            const creator = toSafeText(payload.creator || fromCard.creator || 'unknown');
            const createdAt = dateText(payload.created_at || fromCard.created || '');
            const shareLink = toSafeLink(links.share_url || fromCard.share_url || '');
            const driveFolder = toSafeLink(links.drive_folder_url || '');
            const mongoText = db.mongodb ? 'Da dong bo' : 'Chua dong bo';
            const firebaseText = db.firebase ? 'Da dong bo' : 'Chua dong bo';

            const allMeta = Object.entries(metadata)
                .filter(([_, v]) => v !== null && v !== undefined && String(v).trim() !== '')
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([k, v]) => renderRow(k, toSafeText(v)))
                .join('');

            body.innerHTML = `
                <div class="gallery-info-card">
                    <div class="gallery-info-card__title">Tong quan</div>
                    <div class="gallery-info-grid">
                        ${renderRow('Nguoi tao', creator)}
                        ${renderRow('Thoi gian tao', createdAt)}
                        ${renderRow('MongoDB', mongoText, { status: true, statusClass: db.mongodb ? 'gallery-info-status--ok' : '' })}
                        ${renderRow('Firebase', firebaseText, { status: true, statusClass: db.firebase ? 'gallery-info-status--ok' : '' })}
                        ${shareLink ? renderRow('Share link', shareLink, { full: true, link: shareLink }) : ''}
                        ${driveFolder ? renderRow('Drive folder', driveFolder, { full: true, link: driveFolder }) : ''}
                    </div>
                </div>

                <div class="gallery-info-card">
                    <div class="gallery-info-card__title">Thong so anh</div>
                    <div class="gallery-info-grid">${allMeta || renderRow('Metadata', 'Khong co metadata', { full: true })}</div>
                </div>

                <div class="gallery-info-actions">
                    <button class="btn btn--sm btn--primary" onclick="uploadGalleryImageToDB('${escapeHtml(filename)}')">⬆️ Upload len DB</button>
                    ${(links.share_url || fromCard.share_url) ? `<button class="btn btn--sm btn--ghost" onclick="copyGalleryShareLink('${escapeHtml(links.share_url || fromCard.share_url)}')">🔗 Copy Share Link</button>` : ''}
                </div>
            `;
        };

        try {
            const response = await fetch(`/api/gallery/image-info?filename=${encodeURIComponent(filename)}`);
            if (response.status === 404) {
                renderInfoBody({});
                return;
            }
            const data = await response.json();
            if (!data.success) throw new Error(data.error || 'Cannot load image info');
            renderInfoBody(data);
        } catch (error) {
            console.error('[Gallery] image-info error:', error);
            // Graceful fallback: still show what we currently know from gallery card
            renderInfoBody({});
        }
    };

    window.closeGalleryInfo = () => {
        const modal = document.getElementById('galleryInfoModal');
        if (modal) modal.classList.remove('active', 'open');
    };

    window.copyGalleryShareLink = async (url) => {
        try {
            await navigator.clipboard.writeText(url || '');
            alert('✅ Đã copy share link');
        } catch (_) {
            prompt('Copy link:', url || '');
        }
    };

    window.uploadGalleryImageToDB = async (filename) => {
        if (!filename) return;
        try {
            let response = await fetch('/api/gallery/upload-db', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filename })
            });

            // Fallback for older backend versions that do not have /api/gallery/upload-db
            if (response.status === 404) {
                const item = document.querySelector(`.gallery-item[data-filename="${CSS.escape(filename)}"]`);
                const imagePath = item?.getAttribute('data-path') || `/storage/images/${filename}`;
                const metadataRaw = item?.getAttribute('data-metadata') || '{}';
                let metadata = {};
                try { metadata = JSON.parse(metadataRaw); } catch (_) {}
                metadata.filename = filename;

                const imgResp = await fetch(imagePath);
                if (!imgResp.ok) throw new Error('Cannot fetch local image for fallback upload');
                const blob = await imgResp.blob();
                const b64 = await new Promise((resolve, reject) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve((reader.result || '').toString());
                    reader.onerror = () => reject(new Error('Cannot convert image to base64'));
                    reader.readAsDataURL(blob);
                });

                response = await fetch('/api/save-generated-image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: b64, metadata })
                });
                if (response.status === 404) {
                    response = await fetch('/api/save-image', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ image: b64, metadata })
                    });
                }
            }

            const data = await response.json().catch(() => ({}));
            if (!response.ok || (data.success === false)) {
                throw new Error(data.error || `Upload failed (${response.status})`);
            }
            alert('✅ Đã upload lên MongoDB/Firebase/Drive (nếu cấu hình Drive endpoint hợp lệ).');
            await refreshGallery();
        } catch (error) {
            console.error('[Gallery] upload-db error:', error);
            alert('❌ Upload DB lỗi: ' + (error.message || 'Unknown error'));
        }
    };
    
    window.deleteGalleryImage = async (filename) => {
        if (!confirm(`Bạn có chắc muốn xóa ảnh "${filename}"?`)) return;
        
        try {
            const response = await fetch(`/api/delete-image/${filename}`, {
                method: 'DELETE'
            });
            const data = await response.json();
            
            if (data.success) {
                console.log('[Gallery] Image deleted:', filename);
                // Refresh gallery
                await refreshGallery();
            } else {
                alert('Lỗi: ' + (data.error || 'Không thể xóa ảnh'));
            }
        } catch (error) {
            console.error('[Gallery] Delete error:', error);
            alert('Lỗi khi xóa ảnh');
        }
    };
    
    window.viewGalleryImage = (imagePath, metadata) => {
        console.log('[Gallery] Opening image:', imagePath);
        
        const modal = document.getElementById('imagePreviewModal');
        const img = document.getElementById('imagePreviewContent');
        const info = document.getElementById('imagePreviewInfo');
        
        if (modal && img) {
            // Reset zoom
            if (window.resetPreviewZoom) resetPreviewZoom();
            img.src = imagePath;
            // Store path for download
            img.dataset.downloadUrl = imagePath;
            modal.classList.add('active');
            document.body.style.overflow = 'hidden';
            
            if (info && metadata) {
                const m = metadata;
                const metaItems = [
                    m.model && { label: 'Model', value: m.model },
                    m.sampler && { label: 'Sampler', value: m.sampler },
                    m.steps && { label: 'Steps', value: m.steps },
                    m.cfg_scale && { label: 'CFG', value: m.cfg_scale },
                    (m.width && m.height) && { label: 'Size', value: `${m.width}×${m.height}` },
                    m.denoising_strength && { label: 'Denoise', value: m.denoising_strength },
                    m.vae && { label: 'VAE', value: m.vae },
                    m.seed && { label: 'Seed', value: m.seed },
                ].filter(Boolean);

                const loraStr = m.lora_models
                    ? (typeof m.lora_models === 'string' ? m.lora_models : JSON.stringify(m.lora_models))
                    : '';

                info.innerHTML = `
                    ${m.prompt ? `<div class="lightbox__prompt"><span class="lightbox__meta-label">Prompt</span><br>${m.prompt}</div>` : ''}
                    ${m.negative_prompt ? `<div class="lightbox__prompt" style="opacity:0.7;font-size:11px;"><span class="lightbox__meta-label">Negative</span><br>${m.negative_prompt}</div>` : ''}
                    <div class="lightbox__meta-grid">
                        ${metaItems.map(i => `
                            <div class="lightbox__meta-item">
                                <span class="lightbox__meta-label">${i.label}</span>
                                <span class="lightbox__meta-value">${i.value}</span>
                            </div>
                        `).join('')}
                        ${loraStr ? `<div class="lightbox__meta-item" style="grid-column:1/-1"><span class="lightbox__meta-label">LoRA</span><span class="lightbox__meta-value">${loraStr}</span></div>` : ''}
                    </div>
                `;
            } else if (info) {
                info.innerHTML = '';
            }
        }
    };
    
    // Gallery button event
    const galleryBtn = document.getElementById('galleryBtn');
    if (galleryBtn) {
        galleryBtn.addEventListener('click', openGallery);
    }

    // History modal close
    window.closeHistoryModal = () => {
        const modal = document.getElementById('historyModal');
        if (modal) modal.classList.remove('active', 'open');
    };

    // Expose app for debugging
    window.chatApp = app;
    console.log('[App] ChatBot app exposed to window.chatApp');
});
