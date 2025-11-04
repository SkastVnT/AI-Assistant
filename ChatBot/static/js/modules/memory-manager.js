/**
 * Memory Manager Module
 * Handles AI learning/memory CRUD operations
 */

export class MemoryManager {
    constructor(apiService) {
        this.apiService = apiService;
        this.allMemories = [];
        this.selectedMemories = new Set();
    }

    /**
     * Load all memories from server
     */
    async loadMemories() {
        try {
            const data = await this.apiService.listMemories();
            if (data.memories) {
                this.allMemories = data.memories;
                return this.allMemories;
            }
            return [];
        } catch (error) {
            console.error('Error loading memories:', error);
            throw error;
        }
    }

    /**
     * Render memory list UI
     */
    renderMemoryList(containerElement, onToggle, onDelete) {
        if (!containerElement) return;

        if (this.allMemories.length === 0) {
            containerElement.innerHTML = '<div style="text-align: center; padding: 20px; color: #999;">Chưa có bài học nào được lưu.</div>';
            return;
        }

        containerElement.innerHTML = this.allMemories.map(mem => {
            const isChecked = this.selectedMemories.has(mem.id);
            const preview = mem.content.substring(0, 100) + (mem.content.length > 100 ? '...' : '');
            
            return `
                <div class="memory-item">
                    <input type="checkbox" 
                           id="mem-${mem.id}" 
                           data-memory-id="${mem.id}"
                           ${isChecked ? 'checked' : ''}>
                    <div class="memory-item-content">
                        <div class="memory-item-title">${this.escapeHtml(mem.title)}</div>
                        <div class="memory-item-preview">${this.escapeHtml(preview)}</div>
                    </div>
                    <div class="memory-item-actions">
                        <button class="memory-delete-btn" data-memory-id="${mem.id}">🗑️</button>
                    </div>
                </div>
            `;
        }).join('');

        // Attach event listeners
        containerElement.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                const memoryId = checkbox.dataset.memoryId;
                this.toggleMemory(memoryId);
                if (onToggle) onToggle(memoryId);
            });
        });

        containerElement.querySelectorAll('.memory-delete-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const memoryId = btn.dataset.memoryId;
                if (onDelete) await onDelete(memoryId);
            });
        });
    }

    /**
     * Toggle memory selection
     */
    toggleMemory(memoryId) {
        if (this.selectedMemories.has(memoryId)) {
            this.selectedMemories.delete(memoryId);
        } else {
            this.selectedMemories.add(memoryId);
        }
        console.log('Selected memories:', Array.from(this.selectedMemories));
    }

    /**
     * Get selected memories
     */
    getSelectedMemories() {
        return Array.from(this.selectedMemories);
    }

    /**
     * Clear selected memories
     */
    clearSelection() {
        this.selectedMemories.clear();
    }

    /**
     * Save memory
     */
    async saveMemory(title, content, images = []) {
        try {
            const result = await this.apiService.saveMemory(title, content, images);
            await this.loadMemories(); // Refresh list
            return result;
        } catch (error) {
            console.error('Error saving memory:', error);
            throw error;
        }
    }

    /**
     * Delete memory
     */
    async deleteMemory(memoryId) {
        try {
            const result = await this.apiService.deleteMemory(memoryId);
            this.selectedMemories.delete(memoryId);
            await this.loadMemories(); // Refresh list
            return result;
        } catch (error) {
            console.error('Error deleting memory:', error);
            throw error;
        }
    }

    /**
     * Load specific memory
     */
    async loadMemory(memoryId) {
        try {
            return await this.apiService.loadMemory(memoryId);
        } catch (error) {
            console.error('Error loading memory:', error);
            throw error;
        }
    }

    /**
     * Extract images from chat messages
     */
    extractImagesFromChat(chatContainer) {
        const images = [];
        const allImages = chatContainer.querySelectorAll('img');
        
        allImages.forEach(imageEl => {
            if (imageEl && imageEl.src) {
                const imgSrc = imageEl.src;
                console.log('Found image:', imgSrc);
                
                if (imgSrc.startsWith('http') && imgSrc.includes('/storage/images/')) {
                    // Server-stored image
                    const relativePath = imgSrc.substring(imgSrc.indexOf('/storage/images/'));
                    images.push({ url: relativePath });
                    console.log('Added server image:', relativePath);
                } else if (imgSrc.startsWith('data:image')) {
                    // Base64 image
                    images.push({ base64: imgSrc });
                    console.log('Added base64 image');
                }
            }
        });
        
        return images;
    }

    /**
     * Build memory content from chat
     */
    buildMemoryContent(chatContainer) {
        let content = '';
        const messages = Array.from(chatContainer.children);
        
        messages.forEach(msg => {
            const isUser = msg.classList.contains('user');
            const textEl = msg.querySelector('.message-text');
            
            if (textEl) {
                const text = textEl.textContent || '';
                content += `${isUser ? 'User' : 'AI'}: ${text}\n\n`;
            }
        });
        
        return content;
    }

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}
