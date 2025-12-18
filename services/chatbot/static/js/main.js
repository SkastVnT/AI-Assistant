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
import { ExportHandler } from './modules/export-handler.js';
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
        this.exportHandler = new ExportHandler();
        
        // Expose chatManager and chatApp globally
        window.chatManager = this.chatManager;
        window.chatApp = this;
        
        // State
        this.activeTools = new Set();
        this.conversationActive = false;
        this.currentAbortController = null;
        this.messageHistory = {}; // Store message versions: { messageId: [version1, version2, ...] }
        this.currentMessageId = null;
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
        this.loadCurrentChat();
        
        // Setup UI
        this.uiUtils.initDarkMode();
        this.uiUtils.setupAutoResize(elements.messageInput);
        
        // Setup event listeners
        this.setupEventListeners();
        
        console.log('[App] Setting up file upload handler...');
        console.log('[App] fileInput element:', elements.fileInput);
        
        // Setup file handling with AUTO-ANALYSIS
        const newFileInput = this.fileHandler.setupFileInput(elements.fileInput, async (files) => {
            console.log('[App] ===== FILE UPLOAD CALLBACK =====');
            console.log('[App] Received files:', files.length, files);
            
            try {
                // Process NEW files only
                const processedFiles = [];
                for (let file of files) {
                    console.log('[App] Processing file:', file.name);
                    try {
                        const fileData = await this.fileHandler.processFile(file);
                        console.log('[App] Processed successfully:', fileData.name);
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
                        console.error('[App] File processing error:', error);
                    }
                }
                
                if (processedFiles.length === 0) {
                    console.log('[App] No files processed');
                    newFileInput.value = '';
                    return;
                }
                
                console.log('[App] Adding', processedFiles.length, 'files to session');
                // Add processed files to session
                for (let fileData of processedFiles) {
                    this.fileHandler.currentSessionFiles.push(fileData);
                }
                this.saveFilesToCurrentSession();
                
                // Show NEW files in chat with instructions
                const timestamp = this.uiUtils.formatTimestamp(new Date());
                this.messageRenderer.addFileMessage(elements.chatContainer, processedFiles, timestamp);
                
                // Show instruction message to user
                const instructionTimestamp = this.uiUtils.formatTimestamp(new Date());
                const customPromptUsed = window.customPromptEnabled === true;
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    `✅ **Đã tải lên ${processedFiles.length} file.** Bạn có thể hỏi tôi về nội dung file bây giờ! 💬`,
                    false,
                    'system',
                    'info',
                    instructionTimestamp,
                    null,
                    customPromptUsed
                );
                
                // Clear the input
                newFileInput.value = '';
            } catch (error) {
                console.error('Upload error:', error);
                // Show error in chat instead of alert
                const errorTimestamp = this.uiUtils.formatTimestamp(new Date());
                const customPromptUsed = window.customPromptEnabled === true;
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    `❌ **Lỗi upload file:** ${error.message}`,
                    false,
                    'system',
                    'error',
                    errorTimestamp,
                    null,
                    customPromptUsed
                );
                newFileInput.value = '';
            }
        });
        
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
        this.uiUtils.updateStorageDisplay(this.chatManager.getStorageInfo());
        this.uiUtils.renderChatList(
            this.chatManager.chatSessions,
            this.chatManager.currentChatId,
            (chatId) => this.handleSwitchChat(chatId),
            (chatId) => this.handleDeleteChat(chatId)
        );
        
        // Check local models
        await this.checkLocalModels();
        
        // Setup message renderer callback
        this.messageRenderer.setEditSaveCallback((messageDiv, newContent, originalContent) => {
            this.handleEditSave(messageDiv, newContent, originalContent);
        });
        
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
            (chatId) => this.handleDeleteChat(chatId)
        );
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
        
        // Clear chat
        elements.clearBtn.addEventListener('click', () => this.clearChat());
        
        // New chat
        elements.newChatBtn.addEventListener('click', () => this.newChat());
        
        // Stop generation button
        const stopBtn = document.getElementById('stopGenerationBtn');
        if (stopBtn) {
            stopBtn.addEventListener('click', () => this.stopGeneration());
        }
        
        // Dark mode toggle
        elements.darkModeBtn.addEventListener('click', () => {
            this.uiUtils.toggleDarkMode();
        });
        
        // Sidebar toggle
        elements.sidebarToggle.addEventListener('click', () => {
            this.uiUtils.toggleSidebar();
        });
        
        // Tool buttons
        if (elements.googleSearchBtn) {
            elements.googleSearchBtn.addEventListener('click', () => {
                this.toggleTool('google-search', elements.googleSearchBtn);
            });
        }
        
        if (elements.githubBtn) {
            elements.githubBtn.addEventListener('click', () => {
                this.toggleTool('github', elements.githubBtn);
            });
        }
        
        if (elements.imageGenToolBtn) {
            elements.imageGenToolBtn.addEventListener('click', () => {
                this.toggleTool('image-generation', elements.imageGenToolBtn);
            });
        }
        
        // Image generation button
        if (elements.imageGenBtn) {
            elements.imageGenBtn.addEventListener('click', () => this.openImageGenModal());
        }
        
        // Img2Img tool button
        if (elements.img2imgToolBtn) {
            elements.img2imgToolBtn.addEventListener('click', async () => {
                await this.openImageGenModal();
                setTimeout(() => this.imageGen.switchTab('img2img'), 100);
            });
        }
        
        // Upload files button
        const uploadFilesBtn = document.getElementById('uploadFilesBtn');
        if (uploadFilesBtn && elements.fileInput) {
            uploadFilesBtn.addEventListener('click', () => {
                console.log('[App] Upload button clicked, triggering file input');
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
        const session = this.chatManager.getCurrentSession();
        if (!session) return;
        
        const elements = this.uiUtils.elements;
        
        // Load messages
        if (session.messages.length > 0) {
            elements.chatContainer.innerHTML = session.messages.join('');
            
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
                            messageDiv.dataset.currentVersion = (versions.length - 1).toString();
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
            
            // Make images clickable
            setTimeout(() => {
                this.messageRenderer.makeImagesClickable((img) => this.openImagePreview(img));
            }, 200);
        } else {
            this.uiUtils.clearChat();
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
        const formValues = this.uiUtils.getFormValues();
        let message = formValues.message.trim();
        
        // Get session files
        const sessionFiles = this.fileHandler.getSessionFiles();
        
        if (!message && sessionFiles.length === 0) {
            return;
        }
        
        // Auto-include file context if files are attached
        if (sessionFiles.length > 0) {
            const fileContext = this.buildFileContext(sessionFiles);
            if (fileContext) {
                message = `${fileContext}\n\n${message || 'Hãy phân tích các file được đính kèm.'}`;
            }
            // Auto-enable deep thinking when files are attached for better analysis
            formValues.deepThinking = true;
            console.log('[App] Auto-enabled Deep Thinking due to attached files');
        }
        
        // Generate message ID for versioning
        this.currentMessageId = 'msg_' + Date.now();
        
        // Show loading
        this.uiUtils.showLoading();
        
        // Add user message to chat
        const timestamp = this.uiUtils.formatTimestamp(new Date());
        const customPromptUsed = window.customPromptEnabled === true;
        this.messageRenderer.addMessage(
            elements.chatContainer,
            message,
            true,
            formValues.model,
            formValues.context,
            timestamp,
            null,
            customPromptUsed
        );
        
        // If deep thinking is enabled, add thinking container with loading state
        let thinkingContainer = null;
        if (formValues.deepThinking) {
            const thinkingSection = this.messageRenderer.createThinkingSection(null, true);
            elements.chatContainer.appendChild(thinkingSection);
            thinkingContainer = thinkingSection;
            
            // Scroll to bottom to show thinking
            elements.chatContainer.scrollTop = elements.chatContainer.scrollHeight;
        }
        
        // Clear input (but keep files attached for this session)
        this.uiUtils.clearInput();
        
        // Create AbortController for this request
        this.currentAbortController = new AbortController();
        
        try {
            // Build history for context
            const history = this.buildConversationHistory();
            
            // Get selected memories
            const selectedMemories = this.memoryManager.getSelectedMemories();
            
            // Send to API with abort signal
            const data = await this.apiService.sendMessage(
                message,
                formValues.model,
                formValues.context,
                Array.from(this.activeTools),
                formValues.deepThinking,
                history,
                this.fileHandler.getFiles(), // Empty for now, all handled in message
                selectedMemories,
                this.currentAbortController.signal,
                (window.customPromptEnabled && window.customPromptValue) ? window.customPromptValue : ''  // Only pass if enabled
            );
            
            // Add response to chat with version support
            const responseTimestamp = this.uiUtils.formatTimestamp(new Date());
            const responseContent = data.error ? `❌ **Lỗi:** ${data.error}` : data.response;
            
            // If deep thinking was enabled and we have thinking_process
            if (formValues.deepThinking && data.thinking_process && thinkingContainer) {
                // Update thinking container with actual thinking process
                this.messageRenderer.updateThinkingContent(thinkingContainer, data.thinking_process);
            } else if (thinkingContainer) {
                // Remove thinking container if no thinking process returned
                thinkingContainer.remove();
            }
            
            // Check if custom prompt is being used
            const customPromptUsed = window.customPromptEnabled === true;
            
            const responseMsg = this.messageRenderer.addMessage(
                elements.chatContainer,
                responseContent,
                false,
                formValues.model,
                formValues.context,
                responseTimestamp,
                data.thinking_process || null,
                customPromptUsed
            );
            
            // Update the latest version with the new response
            // Find the user message with messageId
            const userMessages = elements.chatContainer.querySelectorAll('.message.user[data-message-id]');
            if (userMessages.length > 0) {
                const lastUserMsg = userMessages[userMessages.length - 1];
                const messageId = lastUserMsg.dataset.messageId;
                
                if (messageId) {
                    // Get history and update last version's response
                    const history = this.messageRenderer.getMessageHistory(messageId);
                    if (history.length > 0) {
                        const lastVersion = history[history.length - 1];
                        lastVersion.assistantResponse = responseContent;
                        
                        // Save to chatManager
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
            
            // Make images clickable
            setTimeout(() => {
                this.messageRenderer.makeImagesClickable((img) => this.openImagePreview(img));
            }, 100);
            
        } catch (error) {
            // Remove thinking container if error
            if (thinkingContainer) {
                thinkingContainer.remove();
            }
            
            // Check if it was aborted by user
            if (error.name === 'AbortError') {
                console.log('Generation stopped by user');
                // Don't show error message, user intentionally stopped
            } else {
                const errorTimestamp = this.uiUtils.formatTimestamp(new Date());
                const customPromptUsed = window.customPromptEnabled === true;
                this.messageRenderer.addMessage(
                    elements.chatContainer,
                    `❌ **Lỗi kết nối:** ${error.message}`,
                    false,
                    formValues.model,
                    formValues.context,
                    errorTimestamp,
                    null,
                    customPromptUsed
                );
                // Save session with updated timestamp (new message even if error)
                this.saveCurrentSession(true);
            }
        } finally {
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
            
            // Make images clickable
            setTimeout(() => {
                this.messageRenderer.makeImagesClickable((img) => this.openImagePreview(img));
            }, 100);
            
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
                context += `(Image file - visual content)\n`;
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
        const messages = Array.from(elements.chatContainer.children).map(el => el.outerHTML);
        
        this.chatManager.updateCurrentSession(messages, updateTimestamp);
        await this.chatManager.saveSessions();
        
        this.uiUtils.updateStorageDisplay(this.chatManager.getStorageInfo());
        this.uiUtils.renderChatList(
            this.chatManager.chatSessions,
            this.chatManager.currentChatId,
            (chatId) => this.handleSwitchChat(chatId),
            (chatId) => this.handleDeleteChat(chatId)
        );
    }

    /**
     * Clear chat
     */
    clearChat() {
        if (!this.uiUtils.showConfirm('Bạn có chắc muốn xóa toàn bộ lịch sử chat này?')) {
            return;
        }
        
        this.uiUtils.clearChat();
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
        
        // Clear files when creating new chat
        this.fileHandler.clearSessionFiles();
        this.fileHandler.renderSessionFiles(this.uiUtils.elements.fileList);
        
        this.saveCurrentSession();
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
        
        const result = this.chatManager.deleteChat(chatId);
        
        if (!result.success) {
            this.uiUtils.showAlert(result.message);
            return;
        }
        
        this.loadCurrentChat();
        this.saveCurrentSession();
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
        // This functionality can be added later
        console.log('[Image Preview] Open:', imgElement.src);
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new ChatBotApp();
    app.init();
    
    // Expose to window for global access
    window.chatBotApp = app;
    
    // Expose cleanup function
    window.manualCleanup = () => {
        const result = app.chatManager.manualCleanup(5);
        if (result.success) {
            app.saveCurrentSession();
            app.uiUtils.showAlert(result.message);
        } else {
            app.uiUtils.showAlert(result.message);
        }
    };
    
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
                    <div class="category-tags">
                        ${catTags.map(tag => `
                            <span class="tag-item" onclick="toggleTag('${tag.name}')" 
                                  title="Confidence: ${(tag.confidence * 100).toFixed(1)}%">
                                ${tag.name} <small>(${(tag.confidence * 100).toFixed(0)}%)</small>
                            </span>
                        `).join('')}
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
            app.uiUtils.showAlert('✅ Đã tạo ảnh thành công!');
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
            app.uiUtils.showAlert('✅ Đã tạo ảnh thành công!');
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
        btn.textContent = '🤖 Đang tạo prompt bằng Grok AI...';
        
        try {
            const result = await app.imageGen.generatePromptFromTags();
            
            if (result && result.prompt) {
                // Fill the generated prompt into img2img prompt textarea
                const promptTextarea = document.getElementById('img2imgPrompt');
                const negativeTextarea = document.getElementById('img2imgNegativePrompt');
                
                if (promptTextarea) {
                    promptTextarea.value = result.prompt;
                    
                    // Smooth scroll to prompt textarea
                    promptTextarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    
                    // Highlight the textarea briefly
                    promptTextarea.style.transition = 'all 0.3s';
                    promptTextarea.style.boxShadow = '0 0 20px rgba(102, 126, 234, 0.6)';
                    setTimeout(() => {
                        promptTextarea.style.boxShadow = '';
                    }, 1500);
                }
                
                // Fill negative prompt with NSFW filtering
                if (negativeTextarea && result.negative_prompt) {
                    negativeTextarea.value = result.negative_prompt;
                    
                    // Brief highlight for negative prompt too
                    negativeTextarea.style.transition = 'all 0.3s';
                    negativeTextarea.style.boxShadow = '0 0 20px rgba(255, 87, 34, 0.6)';
                    setTimeout(() => {
                        negativeTextarea.style.boxShadow = '';
                    }, 1500);
                }
                
                alert(`✅ Đã tạo prompt tự động!\n\n📝 Prompt: ${result.prompt.substring(0, 80)}...\n\n🚫 Negative (có lọc NSFW): ${result.negative_prompt.substring(0, 60)}...`);
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
    window.handleSourceImageUpload = (event) => app.imageGen.handleSourceImageUpload(event);
    
    // Expose message rendering functions
    window.openImagePreview = (img) => app.messageRenderer.openImagePreview(img);
    window.closeImagePreview = () => app.messageRenderer.closeImagePreview();
    window.downloadPreviewImage = () => app.messageRenderer.downloadPreviewImage();
    
    // Expose export functions
    window.downloadChatAsPDF = () => app.exportHandler.downloadChatAsPDF(app.currentSession, app.chatManager.sessions);
    window.downloadChatAsJSON = () => app.exportHandler.downloadChatAsJSON(app.currentSession, app.chatManager.sessions);
    window.downloadChatAsText = () => app.exportHandler.downloadChatAsText(app.currentSession, app.chatManager.sessions);
    
    // Expose app for debugging
    window.chatApp = app;
    console.log('[App] ChatBot app exposed to window.chatApp');
});
