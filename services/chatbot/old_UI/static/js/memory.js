// Memory management
async function loadMemories() {
    try {
        const response = await fetch('/api/memory/list');
        const data = await response.json();
        
        if (data.success) {
            allMemories = data.memories;
            renderMemoryList();
        }
    } catch (error) {
        console.error('Error loading memories:', error);
    }
}

function renderMemoryList() {
    const memoryListEl = document.getElementById('memoryList');
    if (!memoryListEl) return;
    
    memoryListEl.innerHTML = '';
    
    if (allMemories.length === 0) {
        memoryListEl.innerHTML = '<p class="text-gray-500 text-center py-4">Chưa có bài học nào</p>';
        return;
    }
    
    allMemories.forEach(memory => {
        const memoryItem = document.createElement('div');
        memoryItem.className = 'memory-item p-3 rounded-lg mb-2 cursor-pointer';
        memoryItem.dataset.memoryId = memory.id;
        
        const isSelected = selectedMemories.has(memory.id);
        if (isSelected) {
            memoryItem.classList.add('border-2', 'border-blue-500');
        }
        
        memoryItem.innerHTML = `
            <div class="flex items-start justify-between">
                <div class="flex-1">
                    <input type="checkbox" 
                           id="memory-${memory.id}" 
                           ${isSelected ? 'checked' : ''}
                           onchange="toggleMemory('${memory.id}')"
                           class="mr-2">
                    <label for="memory-${memory.id}" class="font-medium cursor-pointer">
                        ${memory.title}
                    </label>
                    <p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
                        ${memory.content.substring(0, 100)}...
                    </p>
                    <div class="text-xs text-gray-500 mt-2">
                        ${memory.timestamp ? new Date(memory.timestamp).toLocaleString('vi-VN') : ''}
                    </div>
                    ${memory.tags && memory.tags.length > 0 ? `
                        <div class="flex flex-wrap gap-1 mt-2">
                            ${memory.tags.map(tag => `
                                <span class="px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 text-xs rounded">
                                    ${tag}
                                </span>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
                <button onclick="deleteMemory('${memory.id}')" 
                        class="ml-2 px-2 py-1 bg-red-500 hover:bg-red-600 text-white rounded text-sm"
                        title="Xóa bài học">
                    🗑️
                </button>
            </div>
        `;
        
        memoryListEl.appendChild(memoryItem);
    });
}

function toggleMemory(memoryId) {
    if (selectedMemories.has(memoryId)) {
        selectedMemories.delete(memoryId);
    } else {
        selectedMemories.add(memoryId);
    }
    renderMemoryList();
}

async function saveMemory() {
    const saveMemoryBtn = document.getElementById('saveMemoryBtn');
    if (!saveMemoryBtn) return;
    
    try {
        // Collect all messages
        const messages = Array.from(chatContainer.children)
            .filter(el => el.classList.contains('message'))
            .map(el => ({
                content: el.querySelector('.message-content').innerHTML,
                isUser: el.classList.contains('user'),
                timestamp: el.dataset.timestamp
            }));
        
        if (messages.length === 0) {
            alert('Không có nội dung để lưu!');
            return;
        }
        
        // Show loading
        const loadingMsg = document.createElement('div');
        loadingMsg.className = 'message assistant';
        loadingMsg.innerHTML = '<div class="message-content">⏳ Đang tạo tiêu đề với AI...</div>';
        chatContainer.appendChild(loadingMsg);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
        // Collect all images in chat
        const images = [];
        const imageElements = chatContainer.querySelectorAll('img');
        console.log('Found images:', imageElements.length);
        
        for (let i = 0; i < imageElements.length; i++) {
            const img = imageElements[i];
            let imgSrc = img.src;
            console.log('Processing image:', imgSrc);
            
            if (imgSrc.startsWith('http') && imgSrc.includes('/storage/images/')) {
                // Server-hosted image - extract relative path
                const imagePath = imgSrc.split('/storage/images/')[1];
                images.push({
                    type: 'server',
                    path: imagePath
                });
                console.log('Added server image:', imagePath);
            } else if (imgSrc.startsWith('data:image/')) {
                // Base64 image
                images.push({
                    type: 'base64',
                    data: imgSrc
                });
                console.log('Added base64 image');
            }
        }
        
        console.log('Total images collected:', images.length);
        
        // Build content for AI
        const content = messages.map(m => m.content).join('\n\n');
        
        // Generate title with AI
        const titlePrompt = `Based on this conversation, create a short, descriptive title (max 30 characters, Vietnamese language):

Conversation:
${content.substring(0, 500)}...

Return ONLY the title, nothing else.`;
        
        const titleResponse = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: titlePrompt,
                model: modelSelect.value,
                context: 'precise',
                deep_thinking: false,
                ai_learning: false
            })
        });
        
        const titleData = await titleResponse.json();
        let title = titleData.response.trim();
        
        // Clean up title
        title = title.replace(/["']/g, '').substring(0, 30);
        
        // Remove loading message safely
        if (loadingMsg && loadingMsg.parentNode === chatContainer) {
            chatContainer.removeChild(loadingMsg);
        }
        
        // Show confirmation
        const confirmMsg = images.length > 0 
            ? `Lưu bài học "${title}" với ${images.length} hình ảnh?`
            : `Lưu bài học "${title}"?`;
            
        if (!confirm(confirmMsg)) return;
        
        // Auto-generate tags
        const tags = [];
        const contentLower = content.toLowerCase();
        const commonKeywords = ['python', 'javascript', 'java', 'react', 'vue', 'angular', 'node', 'api', 'database', 'sql', 'docker', 'git', 'linux', 'windows', 'programming', 'code', 'bug', 'error', 'fix', 'anime', 'art', 'design', 'image', 'photo'];
        commonKeywords.forEach(keyword => {
            if (contentLower.includes(keyword)) {
                tags.push(keyword);
            }
        });
        
        // Save to backend
        const saveResponse = await fetch('/api/memory/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title,
                content,
                tags,
                images
            })
        });
        
        const saveData = await saveResponse.json();
        
        if (saveData.success) {
            alert('✅ Đã lưu bài học thành công!');
            loadMemories();
        } else {
            alert('❌ Lỗi khi lưu: ' + saveData.error);
        }
        
    } catch (error) {
        console.error('Error saving memory:', error);
        alert('❌ Lỗi: ' + error.message);
        
        // Safe cleanup
        const loadingMsg = chatContainer.querySelector('.message.assistant:last-child');
        if (loadingMsg && loadingMsg.parentNode === chatContainer) {
            chatContainer.removeChild(loadingMsg);
        }
    }
}

async function deleteMemory(memoryId) {
    if (!confirm('Bạn có chắc muốn xóa bài học này?')) return;
    
    try {
        console.log('Attempting to delete memory:', memoryId);
        
        const response = await fetch(`/api/memory/delete/${memoryId}`, {
            method: 'DELETE'
        });
        
        console.log('Delete request sent to:', `/api/memory/delete/${memoryId}`);
        
        const data = await response.json();
        console.log('Delete response:', data);
        
        if (data.success) {
            alert('✅ Đã xóa bài học thành công!');
            selectedMemories.delete(memoryId);
            loadMemories();
        } else {
            console.error('Delete failed:', data.error);
            alert('❌ Lỗi: ' + data.error);
        }
    } catch (error) {
        console.error('Error deleting memory:', error);
        alert('❌ Lỗi: ' + error.message);
    }
}

// Initialize memory panel
document.addEventListener('DOMContentLoaded', () => {
    const saveMemoryBtn = document.getElementById('saveMemoryBtn');
    if (saveMemoryBtn) {
        saveMemoryBtn.addEventListener('click', saveMemory);
    }
});
