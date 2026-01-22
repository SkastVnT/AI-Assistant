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
        
        // Eye Care mode toggle
        const eyeCareBtn = document.getElementById('eyeCareBtn');
        if (eyeCareBtn) {
            eyeCareBtn.addEventListener('click', () => {
                this.uiUtils.toggleEyeCareMode();
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
            
            // Make images clickable (with retry)
            const makeClickable = () => this.messageRenderer.makeImagesClickable((img) => this.openImagePreview(img));
            setTimeout(makeClickable, 200);
            setTimeout(makeClickable, 600);
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
        
        // Include MCP context if enabled
        const mcpContextStr = this.getMcpContextString ? this.getMcpContextString() : '';
        let mcpIndicator = '';
        if (mcpContextStr) {
            message = `[MCP Context được cung cấp - hãy sử dụng thông tin này để trả lời]\n\n${mcpContextStr}\n\n---\n\nUser question: ${message}`;
            mcpIndicator = ' 📎 MCP';
            console.log('[App] MCP context injected, length:', mcpContextStr.length);
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
            
            // Get agent config if enabled
            const agentConfig = window.getAgentConfig ? window.getAgentConfig() : null;
            
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
                agentConfig ? agentConfig.systemPrompt : '',  // System prompt
                agentConfig  // Full agent config for advanced parameters
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
            
            // Get agent config for display
            const agentConfigForDisplay = window.getAgentConfig ? window.getAgentConfig() : null;
            
            const responseMsg = this.messageRenderer.addMessage(
                elements.chatContainer,
                responseContent,
                false,
                formValues.model,
                formValues.context,
                responseTimestamp,
                data.thinking_process || null,
                customPromptUsed,
                agentConfigForDisplay
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
            
            // Make images clickable (with retry for dynamically loaded images)
            const makeClickable = () => this.messageRenderer.makeImagesClickable((img) => this.openImagePreview(img));
            setTimeout(makeClickable, 100);
            setTimeout(makeClickable, 500);  // Retry after 500ms for slower rendering
            
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
        console.log('[Image Preview] Opening preview...');
        this.messageRenderer.openImagePreview(imgElement);
    }
    
    /**
     * Setup MCP Tab switching and functionality
     */
    setupMcpTabs() {
        const tabs = document.querySelectorAll('.mcp-tab');
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
                        tag.innerHTML = `📁 ${folderName} (${folderData.files.length} files) <button class="mcp-remove-btn" data-type="folder" data-name="${folderName}">×</button>`;
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
                            tag.innerHTML = `🌐 ${hostname} <button class="mcp-remove-btn">×</button>`;
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
                                tag.innerHTML = `📄 ${file.name} <button class="mcp-remove-btn">×</button>`;
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
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    const app = new ChatBotApp();
    app.init();
    
    // Expose to window for global access
    window.chatBotApp = app;
    
    // === IMAGE PREVIEW MODAL: Click overlay to close ===
    const imagePreviewModal = document.getElementById('imagePreviewModal');
    if (imagePreviewModal) {
        imagePreviewModal.addEventListener('click', (e) => {
            // Close if clicking the modal overlay itself (not the image or controls)
            if (e.target === imagePreviewModal) {
                app.messageRenderer.closeImagePreview();
            }
        });
    }
    
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
                
                const promptPreview = result.prompt ? result.prompt.substring(0, 80) : 'N/A';
                const negativePreview = result.negative_prompt ? result.negative_prompt.substring(0, 60) : 'N/A';
                alert(`✅ Đã tạo prompt tự động!\n\n📝 Prompt: ${promptPreview}...\n\n🚫 Negative (có lọc NSFW): ${negativePreview}...`);
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
    
    // Zoom preview image
    window.zoomPreviewImage = (delta) => {
        const previewImg = document.getElementById('imagePreviewContent');
        if (previewImg) {
            currentZoom = Math.max(0.5, Math.min(5.0, currentZoom + delta));
            previewImg.style.transform = `scale(${currentZoom})`;
            previewImg.style.cursor = currentZoom > 1 ? 'grab' : 'default';
            console.log('[Image Preview] Zoom:', currentZoom);
        }
    };
    
    // Reset preview zoom
    window.resetPreviewZoom = () => {
        const previewImg = document.getElementById('imagePreviewContent');
        if (previewImg) {
            currentZoom = 1.0;
            previewImg.style.transform = 'scale(1)';
            previewImg.style.cursor = 'default';
            console.log('[Image Preview] Zoom reset');
        }
    };

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
    
    // === GALLERY FUNCTIONS ===
    // Track if showing all images (for owner)
    let galleryShowAll = false;
    
    window.openGallery = async (showAll = false) => {
        galleryShowAll = showAll;
        const modal = document.getElementById('galleryModal');
        const grid = document.getElementById('galleryGrid');
        const stats = document.getElementById('galleryStats');
        
        if (!modal) return;
        
        modal.classList.add('active');
        grid.innerHTML = '<div style="text-align: center; padding: 50px; color: #999;">⏳ Đang tải ảnh...</div>';
        
        try {
            const url = showAll ? '/api/gallery/images?all=true' : '/api/gallery/images';
            const response = await fetch(url);
            const data = await response.json();
            
            if (data.success && data.images.length > 0) {
                const modeText = showAll ? ' (Tất cả)' : ' (Session hiện tại)';
                stats.textContent = `📊 Tổng số: ${data.total} ảnh${modeText}`;
                
                grid.innerHTML = data.images.map(img => {
                    const metadataStr = JSON.stringify(img.metadata).replace(/"/g, '&quot;');
                    const filename = img.filename || img.path.split('/').pop();
                    return `
                        <div class="gallery-item" data-path="${img.path}" data-filename="${filename}" data-metadata="${metadataStr}">
                            <img src="${img.path}" alt="${filename}" loading="lazy">
                            <div class="gallery-item-info">
                                <div style="font-weight: 600;">📅 ${img.created}</div>
                                <div class="gallery-item-prompt" title="${img.prompt}">
                                    💬 ${img.prompt.substring(0, 50)}${img.prompt.length > 50 ? '...' : ''}
                                </div>
                            </div>
                            <button class="gallery-delete-btn" onclick="event.stopPropagation(); deleteGalleryImage('${filename}')" title="Xóa ảnh">
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
    
    window.toggleGalleryMode = () => {
        galleryShowAll = !galleryShowAll;
        openGallery(galleryShowAll);
    };
    
    window.closeGallery = () => {
        const modal = document.getElementById('galleryModal');
        if (modal) modal.classList.remove('active');
    };
    
    window.refreshGallery = async () => {
        console.log('[Gallery] Refreshing...');
        // Re-open with current mode
        await openGallery(galleryShowAll);
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
        console.log('[Gallery] Metadata:', metadata);
        
        // Open image preview
        const modal = document.getElementById('imagePreviewModal');
        const img = document.getElementById('imagePreviewContent');
        const info = document.getElementById('imagePreviewInfo');
        
        if (modal && img) {
            img.src = imagePath;
            modal.classList.add('active'); // Use classList instead of style.display
            
            if (info && metadata) {
                info.innerHTML = `
                    <div style="margin-top: 10px; font-size: 14px;">
                        <div style="margin-bottom: 8px;"><strong>💬 Prompt:</strong> ${metadata.prompt || 'N/A'}</div>
                        <div style="margin-bottom: 8px;"><strong>🚫 Negative:</strong> ${metadata.negative_prompt || 'N/A'}</div>
                        <div style="margin-bottom: 8px;"><strong>🎨 Model:</strong> ${metadata.model || 'N/A'}</div>
                        <div style="margin-bottom: 8px;"><strong>📏 Size:</strong> ${metadata.width || 'N/A'}×${metadata.height || 'N/A'}</div>
                        <div style="margin-bottom: 8px;"><strong>🎲 Steps:</strong> ${metadata.steps || 'N/A'}</div>
                        <div style="margin-bottom: 8px;"><strong>⚙️ CFG Scale:</strong> ${metadata.cfg_scale || 'N/A'}</div>
                        <div style="margin-bottom: 8px;"><strong>⚙️ Sampler:</strong> ${metadata.sampler || 'N/A'}</div>
                        <div style="margin-bottom: 8px;"><strong>🔧 VAE:</strong> ${metadata.vae || 'N/A'}</div>
                        <div style="margin-bottom: 8px;"><strong>🎨 LoRA:</strong> ${metadata.lora_models || 'None'}</div>
                        ${metadata.denoising_strength && metadata.denoising_strength !== 'N/A' ? `<div><strong>🔧 Denoising:</strong> ${metadata.denoising_strength}</div>` : ''}
                    </div>
                `;
            }
        }
    };
    
    // Gallery button event
    const galleryBtn = document.getElementById('galleryBtn');
    if (galleryBtn) {
        galleryBtn.addEventListener('click', openGallery);
    }
    
    // Expose app for debugging
    window.chatApp = app;
    console.log('[App] ChatBot app exposed to window.chatApp');
});
