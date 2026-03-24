/**
 * Chat Manager Module
 * Handles chat sessions, storage management, and conversation history
 */

export class ChatSession {
    constructor(id) {
        this.id = id;
        // Get default title based on current language
        const lang = localStorage.getItem('chatbot_language') || 'vi';
        this.title = lang === 'vi' ? 'Cuộc trò chuyện mới' : 'New conversation';
        this.messages = [];
        this.attachedFiles = []; // Store uploaded files for this chat session
        this.messageVersions = {}; // Store message edit versions: { messageId: [{content, response, timestamp}] }
        this.pinned = false;  // Pinned chats always appear at top
        this.order = null;    // Custom order (null = auto-sort by updatedAt)
        this.createdAt = new Date();
        this.updatedAt = new Date();
    }
}

export class ChatManager {
    constructor() {
        this.currentChatId = null;
        this.chatSessions = {};
        this.chatHistory = [];
    }

    /**
     * Load sessions from localStorage
     */
    loadSessions() {
        const saved = localStorage.getItem('chatSessions');
        if (saved) {
            try {
                const parsed = JSON.parse(saved);
                this.chatSessions = {};
                Object.keys(parsed).forEach(id => {
                    // Guard against prototype pollution
                    if (id === '__proto__' || id === 'constructor' || id === 'prototype') return;
                    const session = parsed[id];
                    this.chatSessions[id] = session;
                    this.chatSessions[id].createdAt = new Date(session.createdAt);
                    this.chatSessions[id].updatedAt = new Date(session.updatedAt);
                    // Migration: clean up corrupted sessions that saved welcomeScreen HTML as a message
                    if (session.messages && Array.isArray(session.messages)) {
                        this.chatSessions[id].messages = session.messages.filter(
                            msg => typeof msg === 'string' && !msg.includes('id="welcomeScreen"')
                        );
                    }
                });
                console.log('[ChatManager] Loaded', Object.keys(this.chatSessions).length, 'sessions from localStorage');
            } catch (e) {
                console.error('[ChatManager] Failed to parse saved sessions, resetting:', e);
                localStorage.removeItem('chatSessions');
                this.chatSessions = {};
            }
        }
        
        // If no sessions exist, create first one
        if (Object.keys(this.chatSessions).length === 0) {
            console.log('[ChatManager] No sessions found, creating new chat');
            this.newChat();
        } else {
            // Load the most recent chat
            const sortedIds = Object.keys(this.chatSessions).sort((a, b) => 
                this.chatSessions[b].updatedAt - this.chatSessions[a].updatedAt
            );
            this.currentChatId = sortedIds[0];
            console.log('[ChatManager] Loaded most recent chat:', this.currentChatId);
        }
    }

    /**
     * Compress base64 images to reduce storage size
     */
    async compressBase64Image(base64String, quality = 0.6) {
        return new Promise((resolve) => {
            if (!base64String || !base64String.includes('data:image')) {
                resolve(base64String);
                return;
            }
            
            const img = new Image();
            img.onload = function() {
                const canvas = document.createElement('canvas');
                const ctx = canvas.getContext('2d');
                
                const maxSize = 800;
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
                
                const compressed = canvas.toDataURL('image/jpeg', quality);
                resolve(compressed);
            };
            img.onerror = function() {
                resolve(base64String);
            };
            img.src = base64String;
        });
    }

    /**
     * Compress all images in HTML content
     */
    async compressImagesInHTML(html) {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const images = doc.querySelectorAll('img[src^="data:image"]');
        
        for (let img of images) {
            const compressed = await this.compressBase64Image(img.src, 0.6);
            img.src = compressed;
        }
        
        return doc.documentElement.outerHTML;
    }

    /**
     * Save sessions to localStorage
     */
    async saveSessions() {
        try {
            // Compress images in current session if needed
            if (this.currentChatId && this.chatSessions[this.currentChatId] && 
                this.chatSessions[this.currentChatId].messages) {
                const messages = this.chatSessions[this.currentChatId].messages;
                const hasImages = messages.some(msg => typeof msg === 'string' && msg.includes('data:image'));
                
                if (hasImages) {
                    console.log('[STORAGE] Compressing images in current session...');
                    const compressedMessages = [];
                    for (let msg of messages) {
                        if (typeof msg === 'string' && msg.includes('data:image')) {
                            compressedMessages.push(await this.compressImagesInHTML(msg));
                        } else {
                            compressedMessages.push(msg);
                        }
                    }
                    this.chatSessions[this.currentChatId].messages = compressedMessages;
                }
            }
            
            const sessionsData = JSON.stringify(this.chatSessions);
            const sizeInMB = (new Blob([sessionsData]).size / 1024 / 1024).toFixed(2);
            const maxSizeMB = 200;
            const percentage = (sizeInMB / maxSizeMB) * 100;
            
            console.log(`[STORAGE] Saving ${Object.keys(this.chatSessions).length} sessions, size: ${sizeInMB}MB (${percentage.toFixed(0)}%)`);
            
            // Smart auto-cleanup for public deployment
            this._autoTrimSessions();
            
            // Preventive cleanup if usage > 70%
            if (percentage > 70 && Object.keys(this.chatSessions).length > 5) {
                console.warn('[STORAGE] Usage high! Auto-cleanup to prevent quota error...');
                this.handleQuotaExceeded();
                return true;
            }
            
            localStorage.setItem('chatSessions', sessionsData);
            return true;
        } catch (e) {
            if (e.name === 'QuotaExceededError' || e.code === 22) {
                console.error('[STORAGE] Quota exceeded! Cleaning up old sessions...');
                return this.handleQuotaExceeded();
            } else {
                console.error('[STORAGE] Error saving sessions:', e);
                return false;
            }
        }
    }

    /**
     * Handle storage quota exceeded
     */
    handleQuotaExceeded() {
        console.error('[STORAGE] Quota exceeded! Auto-cleanup starting...');
        
        // Keep only the 3 most recent sessions (more aggressive cleanup)
        const sortedIds = Object.keys(this.chatSessions).sort((a, b) => 
            this.chatSessions[b].updatedAt - this.chatSessions[a].updatedAt
        );
        
        const idsToKeep = sortedIds.slice(0, 3);
        const deletedCount = sortedIds.length - idsToKeep.length;
        const newSessions = {};
        
        idsToKeep.forEach(id => {
            newSessions[id] = this.chatSessions[id];
        });
        
        this.chatSessions = newSessions;
        
        try {
            localStorage.setItem('chatSessions', JSON.stringify(this.chatSessions));
            console.log(`[STORAGE] ✅ Cleanup successful! Deleted ${deletedCount} old chats, kept ${idsToKeep.length}.`);
            
            // If current chat was deleted, switch to most recent
            if (!this.chatSessions[this.currentChatId]) {
                this.currentChatId = idsToKeep[0];
            }
            return true;
        } catch (e2) {
            console.error('[STORAGE] Still failed after cleanup:', e2);
            alert('❌ Không thể lưu chat.\n\nVui lòng:\n1. Export chat quan trọng\n2. Xóa bớt chat cũ\n3. Hoặc clear localStorage');
            return false;
        }
    }

    /**
     * Get storage usage information
     */
    getStorageInfo() {
        try {
            const sessionsData = JSON.stringify(this.chatSessions);
            const sizeInMB = (new Blob([sessionsData]).size / 1024 / 1024).toFixed(2);
            const maxSizeMB = 200;
            const percentage = ((sizeInMB / maxSizeMB) * 100).toFixed(0);
            
            return {
                sizeInMB,
                maxSizeMB,
                percentage,
                sessionCount: Object.keys(this.chatSessions).length,
                color: percentage > 80 ? '#ff4444' : percentage > 50 ? '#ffa500' : '#4CAF50'
            };
        } catch (e) {
            console.error('[STORAGE] Error getting storage info:', e);
            return null;
        }
    }

    /**
     * Smart auto-trim: cap sessions at 30, trim very long conversations to 150 messages
     */
    _autoTrimSessions() {
        const MAX_SESSIONS = 30;
        const MAX_MESSAGES = 150;
        const ids = Object.keys(this.chatSessions);

        // 1. Trim long conversations (keep first 2 system msgs + last MAX_MESSAGES)
        for (const id of ids) {
            const s = this.chatSessions[id];
            if (s.messages && s.messages.length > MAX_MESSAGES) {
                const trimmed = s.messages.length - MAX_MESSAGES;
                s.messages = s.messages.slice(-MAX_MESSAGES);
                console.log(`[STORAGE] Trimmed ${trimmed} old messages from "${s.title}"`);
            }
        }

        // 2. Cap total sessions — remove oldest unpinned sessions beyond limit
        if (ids.length > MAX_SESSIONS) {
            const sorted = ids
                .filter(id => id !== this.currentChatId && !this.chatSessions[id].pinned)
                .sort((a, b) => (this.chatSessions[a].updatedAt || 0) - (this.chatSessions[b].updatedAt || 0));
            const toRemove = sorted.slice(0, ids.length - MAX_SESSIONS);
            for (const id of toRemove) {
                delete this.chatSessions[id];
            }
            if (toRemove.length) console.log(`[STORAGE] Auto-removed ${toRemove.length} old sessions (cap ${MAX_SESSIONS})`);
        }
    }

    /**
     * Create new chat session
     */
    newChat() {
        const id = 'chat_' + Date.now();
        const session = new ChatSession(id);
        this.chatSessions[id] = session;
        this.currentChatId = id;
        this.chatHistory = [];
        this.saveSessions();
        return id;
    }

    /**
     * Switch to existing chat
     */
    switchChat(chatId) {
        if (chatId === this.currentChatId) return false;
        
        this.currentChatId = chatId;
        return true;
    }

    /**
     * Delete chat session
     */
    deleteChat(chatId) {
        delete this.chatSessions[chatId];
        
        // If deleting current chat, switch to another or create new
        if (chatId === this.currentChatId) {
            const remainingIds = Object.keys(this.chatSessions);
            if (remainingIds.length > 0) {
                this.currentChatId = remainingIds[0];
            } else {
                // No chats left, create a new one
                this.newChat();
            }
        }
        
        // If all chats were deleted, ensure we have at least one
        if (Object.keys(this.chatSessions).length === 0) {
            this.newChat();
        }
        
        return { success: true };
    }

    /**
     * Reorder chats — move chat fromId before toId
     */
    reorderChats(fromId, toId, position = 'before') {
        const sortedIds = this.getSortedChatIds();
        const fromIdx = sortedIds.indexOf(fromId);
        if (fromIdx === -1) return;
        
        // Remove from current position
        sortedIds.splice(fromIdx, 1);
        
        // Find new position
        let toIdx = sortedIds.indexOf(toId);
        if (toIdx === -1) toIdx = sortedIds.length;
        if (position === 'after') toIdx += 1;
        
        // Insert at new position
        sortedIds.splice(toIdx, 0, fromId);
        
        // Assign order values
        sortedIds.forEach((id, i) => {
            if (this.chatSessions[id]) {
                this.chatSessions[id].order = i;
            }
        });
        
        this.saveSessions();
    }

    /**
     * Get sorted chat IDs respecting pinned + custom order
     */
    getSortedChatIds() {
        const ids = Object.keys(this.chatSessions);
        const pinned = ids.filter(id => this.chatSessions[id].pinned);
        const unpinned = ids.filter(id => !this.chatSessions[id].pinned);
        
        const sortFn = (a, b) => {
            const sA = this.chatSessions[a];
            const sB = this.chatSessions[b];
            // If both have custom order, use it
            if (sA.order !== null && sA.order !== undefined && sB.order !== null && sB.order !== undefined) {
                return sA.order - sB.order;
            }
            // Otherwise sort by updatedAt descending
            return sB.updatedAt - sA.updatedAt;
        };
        
        pinned.sort(sortFn);
        unpinned.sort(sortFn);
        
        return [...pinned, ...unpinned];
    }

    /**
     * Toggle pin status of a chat
     */
    togglePin(chatId) {
        if (this.chatSessions[chatId]) {
            this.chatSessions[chatId].pinned = !this.chatSessions[chatId].pinned;
            this.saveSessions();
            return this.chatSessions[chatId].pinned;
        }
        return false;
    }

    /**
     * Generate title using Gemini
     */
    async generateTitle(firstMessage) {
        try {
            // Get current language from localStorage
            const currentLang = localStorage.getItem('chatbot_language') || 'vi';
            const languageInstruction = currentLang === 'en' 
                ? 'Generate a concise 3-5 word English title for this conversation. Only return the title, nothing else:'
                : 'Generate a concise 3-5 word Vietnamese title for this conversation. Only return the title, nothing else:';
            
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: `${languageInstruction} "${firstMessage.substring(0, 100)}"`,
                    model: 'grok',
                    context: 'casual',
                    tools: [],
                    deep_thinking: false,
                    language: currentLang
                })
            });
            
            const data = await response.json();
            if (data.response) {
                return data.response.trim().replace(/['"]/g, '');
            }
        } catch (error) {
            console.error('Failed to generate title:', error);
        }
        
        // Fallback: use first few words
        return firstMessage.substring(0, 30) + (firstMessage.length > 30 ? '...' : '');
    }

    /**
     * Get sorted chat list
     */
    getSortedChats() {
        return Object.keys(this.chatSessions).sort((a, b) => 
            this.chatSessions[b].updatedAt - this.chatSessions[a].updatedAt
        );
    }

    /**
     * Get current session
     */
    getCurrentSession() {
        return this.chatSessions[this.currentChatId];
    }
    
    /**
     * Save message version to current session
     */
    saveMessageVersion(messageId, userContent, assistantResponse, timestamp) {
        const session = this.getCurrentSession();
        if (!session) return;
        
        if (!session.messageVersions) {
            session.messageVersions = {};
        }
        
        if (!session.messageVersions[messageId]) {
            session.messageVersions[messageId] = [];
        }
        
        session.messageVersions[messageId].push({
            userContent: userContent,
            assistantResponse: assistantResponse,
            timestamp: timestamp
        });
        
        this.saveSessions();
    }
    
    /**
     * Get message versions from current session
     */
    getMessageVersions(messageId) {
        const session = this.getCurrentSession();
        if (!session || !session.messageVersions) return [];
        return session.messageVersions[messageId] || [];
    }

    /**
     * Update current session
     */
    updateCurrentSession(messages, updateTimestamp = false) {
        if (this.currentChatId && this.chatSessions[this.currentChatId]) {
            this.chatSessions[this.currentChatId].messages = messages;
            // Only update timestamp when explicitly requested (e.g., new message sent)
            if (updateTimestamp) {
                this.chatSessions[this.currentChatId].updatedAt = new Date();
            }
        }
    }
}
