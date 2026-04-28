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
import { initOverlayActions, initLightbox } from './modules/overlay-actions.js';
import {
    initGallery, closeGallery, refreshGallery,
    showGalleryImageInfo, closeGalleryInfo, copyGalleryShareLink,
    uploadGalleryImageToDB, deleteGalleryImage,
} from './modules/gallery-manager.js';
import { initAdvancedSettings } from './modules/adv-settings.js';
import { initImageGenBindings } from './modules/image-gen-bindings.js';
import { initDelegation, registerClickActions, registerAction } from './modules/event-delegation.js';
import {
    initOverlayManager, registerOverlay,
} from './modules/overlay-manager.js';
import {
    collectFormState, routeByIntent, prepareOutgoingPayload,
    runImageRequestFlow, runImg2ImgFlow, runStreamingChatFlow,
} from './modules/send-message-helpers.js';
import { domToStructured, isStructuredSession } from './modules/message-model.js';

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
        
        // State ΓÇö no tools active by default
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

        // Setup file handling ΓÇö STAGING MODE (files wait until user sends message)
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
                this._updateSendReady();
                return;
            }
            area.style.display = 'flex';
            area.innerHTML = this._stagedFiles.map((f, i) => {
                const isTable = !!(f.tableData && f.tableData.headers && f.tableData.headers.length > 0);
                const isImage = f.type && f.type.startsWith('image/') && f.preview;
                const icon = this.fileHandler.getFileIcon ? this.fileHandler.getFileIcon(f.type || '', f.name) : '≡ƒôä';

                let iconOrPreview;
                if (isImage) {
                    iconOrPreview = `<div class="file-staging__card-preview"><img src="${this.fileHandler.escapeHtml(f.preview)}" alt=""></div>`;
                } else if (isTable) {
                    iconOrPreview = `<div class="file-staging__card-icon">≡ƒôè</div>`;
                } else {
                    iconOrPreview = `<div class="file-staging__card-icon">${icon}</div>`;
                }

                const sizeStr = this.fileHandler.formatFileSize ? this.fileHandler.formatFileSize(f.size) : '';
                const meta = isTable
                    ? `${f.tableData.rows.length} h├áng ┬╖ ${f.tableData.headers.length} cß╗Öt`
                    : sizeStr;

                return `<div class="file-staging__card file-staging__clickable${isTable ? ' file-staging__card--table' : ''}" data-idx="${i}" title="${this.fileHandler.escapeHtml(f.name)}">
                    ${iconOrPreview}
                    <div class="file-staging__card-info">
                        <div class="file-staging__card-name">${this.fileHandler.escapeHtml(f.name)}</div>
                        <div class="file-staging__card-meta">${meta}</div>
                    </div>
                    <button class="file-staging__remove" data-idx="${i}" title="X├│a">├ù</button>
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
            this._updateSendReady();
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
                            `Γ¥î **Lß╗ùi xß╗¡ l├╜ file "${file.name}":** ${error.message}`,
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
                    `Γ£à **─É├ú paste ${processedFiles.length} file.** Hß╗Åi t├┤i bß║Ñt kß╗│ ─æiß╗üu g├¼ vß╗ü file! ≡ƒÆ¼`,
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
                    `Γ¥î **Lß╗ùi paste file:** ${error.message}`,
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
                    inputHint.textContent = `V─ân bß║ún qu├í d├ái (${len} k├╜ tß╗▒) ΓÇö sß║╜ tß╗▒ ─æß╗Öng chuyß╗ân th├ánh file .txt khi gß╗¡i`;
                    inputHint.style.display = 'block';
                    inputHint.className = 'message-input-hint message-input-hint--warn';
                } else if (len >= LONG_WARN) {
                    inputHint.textContent = `${len}/${LONG_LIMIT} k├╜ tß╗▒ ΓÇö gß║ºn ─æß║┐n giß╗¢i hß║ín`;
                    inputHint.style.display = 'block';
                    inputHint.className = 'message-input-hint message-input-hint--info';
                } else {
                    inputHint.style.display = 'none';
                }
            }
            this._updateSendReady();
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

        // ΓöÇΓöÇ More menu (topbar overflow) ΓöÇΓöÇ
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
        
        // MCP tabs and sources managed by MCPController (mcp.js)
        // No-op ΓÇö MCPController.setupSourceTabs() handles everything
        
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

        // Set initial send button state based on current input (e.g. if textarea was pre-filled)
        this._updateSendReady();
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

        // Determine which format to load: structured (data-first) or legacy HTML
        const hasStructured = isStructuredSession(session);
        const hasLegacy = Array.isArray(session.messages) && session.messages.length > 0;
        const hasMessages = hasStructured || hasLegacy;

        if (hasMessages) {
            this.uiUtils.hideWelcomeScreen();

            if (hasStructured) {
                // Data-first path: render from structured messages via their cached HTML
                console.log('[App] Loading structured session:', session.structuredMessages.length, 'messages');
                const joined = session.structuredMessages.map(m => m.html || '').join('');
                elements.chatContainer.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(joined) : joined;
            } else {
                // Legacy fallback: render from HTML string array
                console.log('[App] Loading legacy session:', session.messages.length, 'messages');
                const joined = session.messages.join('');
                elements.chatContainer.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(joined) : joined;
            }
            
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
     * Send message ΓÇö orchestrator.
     * Delegates to staged helpers in send-message-helpers.js.
     */
    async sendMessage() {
        // 1. Collect form state (auto-convert long text, flush staged files)
        const state = await collectFormState(this);
        if (!state) return;

        const { elements, flushedFiles, formValues, message, sessionFiles, activeTools } = state;

        // 2. Route by intent
        const { isImageIntent, isImg2Img } = routeByIntent(message, activeTools);

        // 3. Image generation V2 route ΓÇö early return
        if (isImageIntent) {
            return runImageRequestFlow(this, { message, formValues, elements, flushedFiles });
        }

        // 4. Img2Img route ΓÇö early return if handled
        if (isImg2Img && message) {
            const handled = await runImg2ImgFlow(this, { message, formValues, elements });
            if (handled) return;
        }

        // 5. Prepare payload (inject file/MCP/quoted context, resolve thinking mode)
        const payload = prepareOutgoingPayload(this, { message, formValues, sessionFiles });

        // 6. Streaming chat flow (SSE ΓåÆ fallback POST ΓåÆ finalize ΓåÆ suggestions)
        await runStreamingChatFlow(this, {
            ...payload, formValues, elements, activeTools, flushedFiles,
        });

        // Reset button visual after send (textarea was cleared inside runStreamingChatFlow)
        this._updateSendReady();
    }

    /**
     * Analyze uploaded files automatically
     */
    async analyzeUploadedFiles(files) {
        const elements = this.uiUtils.elements;
        const formValues = this.uiUtils.getFormValues();
        
        // Build analysis prompt
        let analysisPrompt = `≡ƒôÄ **Ph├ón t├¡ch file ─æ├ú tß║úi l├¬n:**\n\n`;
        analysisPrompt += `C├│ ${files.length} file ─æ╞░ß╗úc tß║úi l├¬n. H├úy ph├ón t├¡ch chi tiß║┐t nß╗Öi dung:\n\n`;
        
        files.forEach((file, index) => {
            analysisPrompt += `**File ${index + 1}: ${file.name}**\n`;
            analysisPrompt += `- Loß║íi: ${file.type || 'unknown'}\n`;
            analysisPrompt += `- K├¡ch th╞░ß╗¢c: ${this.messageRenderer.formatFileSize(file.size)}\n`;
            
            // Include content for analysis
            if (file.content && typeof file.content === 'string') {
                if (!file.content.startsWith('data:')) {
                    // Text content
                    const maxLength = 15000;
                    const content = file.content.length > maxLength 
                        ? file.content.substring(0, maxLength) + '\n...(truncated)'
                        : file.content;
                    analysisPrompt += `\n**Nß╗Öi dung:**\n\`\`\`\n${content}\n\`\`\`\n`;
                } else if (file.type.startsWith('image/')) {
                    analysisPrompt += `\n(─É├óy l├á file ß║únh)\n`;
                }
            }
            analysisPrompt += `\n---\n\n`;
        });
        
        analysisPrompt += `\n**Y├¬u cß║ºu ph├ón t├¡ch:**\n`;
        analysisPrompt += `1. T├│m tß║»t nß╗Öi dung ch├¡nh cß╗ºa tß╗½ng file\n`;
        analysisPrompt += `2. Ph├ít hiß╗çn c├íc vß║Ñn ─æß╗ü hoß║╖c ─æiß╗âm ─æß║╖c biß╗çt\n`;
        analysisPrompt += `3. ─É╞░a ra nhß║¡n x├⌐t v├á ─æß╗ü xuß║Ñt (nß║┐u c├│)\n`;
        analysisPrompt += `4. Trß║ú lß╗¥i c├íc c├óu hß╗Åi li├¬n quan nß║┐u cß║ºn\n`;
        
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
                ? `Γ¥î **Lß╗ùi ph├ón t├¡ch:** ${data.error}` 
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
                    `Γ¥î **Lß╗ùi ph├ón t├¡ch file:** ${error.message}`,
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
        
        let context = '≡ƒôÄ **Attached Files Context:**\n\n';
        
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
                context += `(Image file attached ΓÇö sent to vision API)\n`;
            } else if (file.content && file.content.startsWith('data:')) {
                context += `(Binary file ΓÇö text extraction unavailable)\n`;
            }
            context += '\n---\n\n';
        });
        
        return context;
    }

    /**
     * Toggle .ready on sendBtn based on whether user has typed something or staged files.
     * Called from the textarea input listener and from _renderStagingArea.
     */
    _updateSendReady() {
        const sendBtn = this.uiUtils.elements && this.uiUtils.elements.sendBtn;
        if (!sendBtn) return;
        const hasText = !!(this.uiUtils.elements.messageInput && this.uiUtils.elements.messageInput.value.trim());
        const hasFiles = this._stagedFiles && this._stagedFiles.length > 0;
        sendBtn.classList.toggle('ready', hasText || hasFiles);
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
                    stoppedIndicator.innerHTML = 'ΓÅ╣∩╕Å <em>─É├ú dß╗½ng bß╗ƒi ng╞░ß╗¥i d├╣ng</em>';
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

        // Collect DOM children (exclude welcome screen)
        const domMessages = Array.from(elements.chatContainer.children)
            .filter(el => el.id !== 'welcomeScreen');

        // Legacy HTML array (kept for backward compat with older loaders)
        const messages = domMessages.map(el => el.outerHTML);

        // Structured data-first array ΓÇö single source of truth for new sessions
        const structuredMessages = domMessages.map(el => domToStructured(el));

        console.log('[DEBUG] saveCurrentSession: chatId=', this.chatManager.currentChatId, 'messages=', messages.length, 'structured=', structuredMessages.length, 'updateTimestamp=', updateTimestamp);
        
        this.chatManager.updateCurrentSession(messages, updateTimestamp, structuredMessages);
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

            // Data-first: capture both structured + HTML for each downstream message.
            // Legacy callers that stored plain arrays are handled in applyVersionBranch().
            const downstream = allMessages.slice(idx + 1);
            session.conversationBranches[messageId][currentVersion] = {
                html: downstream.map(el => el.outerHTML),
                structured: downstream.map(el => domToStructured(el))
            };
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

        const branchData = branchesByMessage[versionIndex];
        // Legacy: plain Array of HTML strings.  New: { html: [...], structured: [...] }
        const branchHtml = Array.isArray(branchData) ? branchData : (branchData?.html || []);
        if (!Array.isArray(branchHtml) || branchHtml.length === 0) return;

        // Remove everything after anchor message.
        let node = messageDiv.nextElementSibling;
        while (node) {
            const next = node.nextElementSibling;
            node.remove();
            node = next;
        }

        // Rebuild downstream branch from HTML snapshot.
        branchHtml.forEach(html => {
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
                ? '≡ƒöÇ ─É├ú t├ích nh├ính! Bß║ín c├│ thß╗â tiß║┐p tß╗Ñc chat tß╗½ ─æ├óy.'
                : '≡ƒöÇ Forked! You can continue chatting from here.'
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
        if (!this.uiUtils.showConfirm('Bß║ín c├│ chß║»c muß╗æn x├│a to├án bß╗Ö lß╗ïch sß╗¡ chat n├áy?')) {
            return;
        }
        // Close thinking side panel on clear
        if (window.ThinkingPanel) window.ThinkingPanel.close();
        this.uiUtils.clearChat();
        // Show welcome screen again
        this.uiUtils.showWelcomeScreen();
        this.chatManager.updateCurrentSession([], false, []);
        
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
        if (!this.uiUtils.showConfirm('Bß║ín c├│ chß║»c muß╗æn x├│a cuß╗Öc tr├▓ chuyß╗çn n├áy?')) {
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
        const isVisible = elements.memoryPanel.classList.contains('open');
        
        elements.memoryPanel.classList.toggle('open', !isVisible);
        
        if (!isVisible) {
            await this.memoryManager.loadMemories();
            this.memoryManager.renderMemoryList(
                elements.memoryListEl,
                null,
                async (memoryId) => {
                    if (this.uiUtils.showConfirm('X├│a memory n├áy?')) {
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
            this.uiUtils.showAlert('Kh├┤ng c├│ nß╗Öi dung ─æß╗â l╞░u!');
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
            this.uiUtils.showAlert('Γ£à ─É├ú l╞░u v├áo bß╗Ö nhß╗¢ AI!');
            await this.toggleMemoryPanel(); // Refresh
        } catch (error) {
            this.uiUtils.showAlert('Γ¥î Lß╗ùi khi l╞░u: ' + error.message);
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
            '≡ƒöä ─Éang tß║ío PDF...',
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
            this.uiUtils.showAlert('Tin nhß║»n kh├┤ng ─æ╞░ß╗úc ─æß╗â trß╗æng!');
            return;
        }
        
        if (newContent === originalContent) {
            this.uiUtils.showAlert('Nß╗Öi dung kh├┤ng thay ─æß╗òi!');
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
            const responseContent = data.error ? `Γ¥î **Lß╗ùi:** ${data.error}` : data.response;
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
                    history[history.length - 1].assistantContent = responseContent;  // data-first: raw API response
                    
                    // Save to chatManager localStorage
                    if (window.chatManager) {
                        const session = window.chatManager.getCurrentSession();
                        if (session && session.messageVersions && session.messageVersions[messageId]) {
                            const versions = session.messageVersions[messageId];
                            if (versions.length > 0) {
                                versions[versions.length - 1].assistantResponse = responseContent;
                                versions[versions.length - 1].assistantContent = responseContent;  // data-first: raw API response
                                window.chatManager.saveSessions();
                            }
                        }
                    }
                }
            }
            
            // Save session
            await this.saveCurrentSession();
            
        } catch (error) {
            this.uiUtils.showAlert('Γ¥î Lß╗ùi kß║┐t nß╗æi: ' + error.message);
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
     * Auto-generate conversation title using qwen2.5:0.5b via Ollama
     * Triggers only when the title is still the default placeholder
     * @param {string} rawUserMessage - The latest user message (before any context injection)
     */
    async autoGenerateTitleIfNeeded(rawUserMessage) {
        const session = this.chatManager.getCurrentSession();
        if (!session) return;
        const lang = localStorage.getItem('chatbot_language') || 'vi';
        const defaults = ['Cuß╗Öc tr├▓ chuyß╗çn mß╗¢i', 'New conversation', 'Untitled'];
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

// ΓöÇΓöÇ Image overlay delegation (runs at module load) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
initOverlayActions();

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new ChatBotApp();
    app.init();

    // ΓöÇΓöÇ Module initialisation ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    initGallery();
    const lightbox = initLightbox(app.messageRenderer);
    initImageGenBindings(app);
    initAdvancedSettings();

    // ΓöÇΓöÇ Event delegation ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ
    initDelegation();

    // ΓöÇΓöÇ Overlay manager ΓÇö unified Escape / outside-click handling ΓöÇΓöÇ
    initOverlayManager();
    registerOverlay('galleryModal',            { type: 'modal' });
    registerOverlay('galleryInfoModal',        { type: 'modal' });
    registerOverlay('imagePreviewModal',       { type: 'modal', onClose: () => { document.body.style.overflow = ''; } });
    registerOverlay('historyModal',            { type: 'modal' });
    registerOverlay('configAgentModal',        { type: 'modal' });
    registerOverlay('imageGenV2Modal',         { type: 'modal' });
    registerOverlay('videoGenModal',           { type: 'modal' });
    registerOverlay('generatedImageContainer', { type: 'modal' });
    registerOverlay('qrPayModal',              { type: 'modal' });
    registerOverlay('changePwModal',           { type: 'modal' });
    registerOverlay('editProfileModal',        { type: 'modal' });
    registerOverlay('userDropdown',            { type: 'dropdown' });

    // Preview actions
    registerClickActions({
        'preview:download': () => lightbox.downloadPreviewImage(),
        'preview:zoom':     (e, el) => lightbox.zoomPreviewImage(parseFloat(el.dataset.zoomDelta || '0')),
        'preview:reset-zoom': () => lightbox.resetPreviewZoom(),
        'preview:close':    () => lightbox.closeImagePreview(),
    });

    // History modal
    registerClickActions({
        'modal:close-history': () => {
            const modal = document.getElementById('historyModal');
            if (modal) modal.classList.remove('active', 'open');
        },
    });

    // Gallery actions
    registerClickActions({
        'gallery:refresh':    () => refreshGallery(),
        'gallery:close':      () => closeGallery(),
        'gallery:close-info': () => closeGalleryInfo(),
        'gallery:info':       (e, el) => showGalleryImageInfo(
            el.dataset.filename || '',
            el.dataset.imageId || '',
            el.dataset.imageData || ''
        ),
        'gallery:upload':     (e, el) => uploadGalleryImageToDB(el.dataset.filename || ''),
        'gallery:delete':     (e, el) => deleteGalleryImage(el.dataset.filename || ''),
        'gallery:copy-link':  (e, el) => copyGalleryShareLink(el.dataset.url || ''),
    });

    // Generated image overlay
    registerClickActions({
        'overlay:close': (e, el) => {
            // Only close when clicking the backdrop itself, not children
            if (e.target === el) {
                el.classList.remove('open');
            }
        },
        'overlay:close-btn': () => {
            const c = document.getElementById('generatedImageContainer');
            if (c) c.classList.remove('open');
        },
        'overlay:share':    () => { if (window.shareImageToImgBB) window.shareImageToImgBB(); },
        'overlay:download': () => { if (window.downloadGeneratedImage) window.downloadGeneratedImage(); },
    });

    // Config Agent modal (functions are in index.html global scope)
    registerClickActions({
        'config:close': () => { if (window.closeConfigAgentModal) window.closeConfigAgentModal(); },
        'config:reset': () => { if (window.resetConfigAgent) window.resetConfigAgent(); },
        'config:save':  () => { if (window.saveConfigAgent) window.saveConfigAgent(); },
    });
    registerAction('change', 'config:toggle', () => {
        if (window.toggleConfigAgent) window.toggleConfigAgent();
    });

    // Password modal (functions are in index.html global scope)
    registerClickActions({
        'modal:close-password':  () => { if (window.closeChangePassword) window.closeChangePassword(); },
        'modal:submit-password': () => { if (window.submitChangePw) window.submitChangePw(); },
    });

    // Profile modal
    registerClickActions({
        'modal:close-profile':  () => { if (window.closeEditProfile) window.closeEditProfile(); },
        'modal:submit-profile': () => { if (window.submitEditProfile) window.submitEditProfile(); },
        'profile:trigger-avatar': () => {
            const input = document.getElementById('epAvatarInput');
            if (input) input.click();
        },
        'profile:clear-avatar': () => { if (window.clearEpAvatar) window.clearEpAvatar(); },
    });
    registerAction('change', 'profile:avatar-file', (e) => {
        if (window.handleEpAvatarFile) window.handleEpAvatarFile(e);
    });

    // QR / Video Unlock modal
    registerClickActions({
        'modal:close-qr':  () => { if (window.closeVideoUnlockModal) window.closeVideoUnlockModal(); },
        'modal:submit-qr': () => { if (window.submitVideoUnlockRequest) window.submitVideoUnlockRequest(); },
        'modal:open-qr':   () => { if (window.openVideoUnlockModal) window.openVideoUnlockModal(); },
    });

    // User dropdown
    registerClickActions({
        'user:toggle-dropdown': () => { if (window.toggleUserDropdown) window.toggleUserDropdown(); },
        'user:open-profile':    () => { if (window.openEditProfile) window.openEditProfile(); },
        'user:open-password':   () => { if (window.openChangePassword) window.openChangePassword(); },
        'user:logout':          () => { try { localStorage.removeItem('ai_session'); } catch (_) {} },
    });

    // Storage cleanup action (for storage widget button)
    registerClickActions({
        'storage:cleanup': () => {
            if (!app.chatManager) return;
            const sorted = Object.keys(app.chatManager.chatSessions || {})
                .sort((a, b) => ((app.chatManager.chatSessions[b] || {}).updatedAt || 0) - ((app.chatManager.chatSessions[a] || {}).updatedAt || 0));
            const keep = new Set(sorted.slice(0, 5));
            sorted.forEach(id => { if (!keep.has(id)) delete app.chatManager.chatSessions[id]; });
            app.chatManager.saveSessions();
            app.uiUtils.renderChatList(app.chatManager.chatSessions, app.currentSession, app.switchChat.bind(app), app.deleteChat.bind(app));
            app.uiUtils.updateStorageDisplay(app.chatManager.chatSessions);
        },
    });

    // Export wrappers (keep temporarily ΓÇö used by history modal buttons)
    window.downloadChatAsPDF = () => app.exportHandler.downloadChatAsPDF(app.currentSession, app.chatManager.sessions);
    window.downloadChatAsJSON = () => app.exportHandler.downloadChatAsJSON(app.currentSession, app.chatManager.sessions);
    window.downloadChatAsText = () => app.exportHandler.downloadChatAsText(app.currentSession, app.chatManager.sessions);

    // Expose app for debugging
    window.chatApp = app;
    console.log('[App] ChatBot app exposed to window.chatApp');
});
