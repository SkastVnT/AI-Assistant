/**
 * Chat Manager Module
 * Handles chat sessions, storage management, and conversation history
 */

export class ChatSession {
    constructor(id) {
        this.id = id;
        this.title = 'Cuộc trò chuyện mới';
        this.messages = [];
        this.attachedFiles = []; // Store uploaded files for this chat session
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
            const parsed = JSON.parse(saved);
            this.chatSessions = {};
            Object.keys(parsed).forEach(id => {
                const session = parsed[id];
                this.chatSessions[id] = session;
                this.chatSessions[id].createdAt = new Date(session.createdAt);
                this.chatSessions[id].updatedAt = new Date(session.updatedAt);
            });
        }
        
        // If no sessions exist, create first one
        if (Object.keys(this.chatSessions).length === 0) {
            this.newChat();
        } else {
            // Load the most recent chat
            const sortedIds = Object.keys(this.chatSessions).sort((a, b) => 
                this.chatSessions[b].updatedAt - this.chatSessions[a].updatedAt
            );
            this.currentChatId = sortedIds[0];
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
            
            // Preventive cleanup if usage > 90%
            if (percentage > 90 && Object.keys(this.chatSessions).length > 5) {
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
                color: percentage > 80 ? '#ff4444' : percentage > 50 ? '#ffa500' : '#4CAF50'
            };
        } catch (e) {
            console.error('[STORAGE] Error getting storage info:', e);
            return null;
        }
    }

    /**
     * Manual cleanup - keep only recent chats (or clear all and create new)
     */
    manualCleanup(keepCount = 5) {
        const sessionCount = Object.keys(this.chatSessions).length;
        
        // If already less than keepCount, clear all and create new chat
        if (sessionCount <= keepCount) {
            const oldCount = sessionCount;
            this.chatSessions = {};
            this.newChat(); // Create fresh chat
            this.saveSessions();
            return { 
                success: true, 
                message: `Đã xóa sạch ${oldCount} chat và tạo mới!`,
                deletedCount: oldCount
            };
        }
        
        const sortedSessions = Object.entries(this.chatSessions)
            .sort((a, b) => new Date(b[1].updatedAt) - new Date(a[1].updatedAt))
            .slice(0, keepCount);
        
        const oldCount = sessionCount;
        this.chatSessions = Object.fromEntries(sortedSessions);
        
        // Update current chat if it was deleted
        if (!this.chatSessions[this.currentChatId]) {
            this.currentChatId = sortedSessions[0][0];
        }
        
        return { 
            success: true, 
            message: `Đã xóa ${oldCount - keepCount} chat cũ!`,
            deletedCount: oldCount - keepCount
        };
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
        if (Object.keys(this.chatSessions).length === 1) {
            return { success: false, message: 'Không thể xóa cuộc trò chuyện cuối cùng!' };
        }
        
        delete this.chatSessions[chatId];
        
        // If deleting current chat, switch to another
        if (chatId === this.currentChatId) {
            const remainingIds = Object.keys(this.chatSessions);
            if (remainingIds.length > 0) {
                this.currentChatId = remainingIds[0];
            } else {
                this.newChat();
            }
        }
        
        return { success: true };
    }

    /**
     * Generate title using Gemini
     */
    async generateTitle(firstMessage) {
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    message: `Generate a concise 3-5 word Vietnamese title for this conversation. Only return the title, nothing else: "${firstMessage.substring(0, 100)}"`,
                    model: 'gemini',
                    context: 'casual',
                    tools: [],
                    deep_thinking: false
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
