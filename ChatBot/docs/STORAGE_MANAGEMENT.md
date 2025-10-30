# 📊 Storage Management Feature

## Overview
This document describes the localStorage quota management features added to handle large base64 images from 4K image generation.

## Problem
- **Issue**: localStorage quota exceeded (5-10MB limit) when saving chat sessions with multiple 4K images
- **Error**: `QuotaExceededError: Failed to execute 'setItem' on 'Storage': Setting the value of 'chatSessions' exceeded the quota`
- **Cause**: Base64 encoded 4K images can be 2-3MB each, and 5-6 chat sessions can fill the quota

## Solution

### 1. Automatic Cleanup on Quota Error
**Location**: `ChatBot/templates/index.html` - `saveSessions()` function (lines 1223-1271)

**Features**:
- Detects `QuotaExceededError` automatically
- Sorts sessions by `updatedAt` timestamp
- Keeps only 5 most recent sessions
- Alerts user about cleanup
- Retries save after cleanup
- Logs storage size in MB

**Code**:
```javascript
function saveSessions() {
    try {
        const sessionsData = JSON.stringify(chatSessions);
        const sizeInMB = (new Blob([sessionsData]).size / 1024 / 1024).toFixed(2);
        console.log(`[STORAGE] Saving ${Object.keys(chatSessions).length} sessions, size: ${sizeInMB}MB`);
        localStorage.setItem('chatSessions', sessionsData);
    } catch (e) {
        if (e.name === 'QuotaExceededError' || e.code === 22) {
            alert('⚠️ Bộ nhớ trình duyệt đã đầy! Đang tự động dọn dẹp...');
            
            // Auto-cleanup: keep only 5 most recent sessions
            const sortedSessions = Object.entries(chatSessions)
                .sort((a, b) => new Date(b[1].updatedAt) - new Date(a[1].updatedAt))
                .slice(0, 5);
            
            chatSessions = Object.fromEntries(sortedSessions);
            
            // Retry save
            try {
                const sessionsData = JSON.stringify(chatSessions);
                const sizeInMB = (new Blob([sessionsData]).size / 1024 / 1024).toFixed(2);
                console.log(`[STORAGE] After cleanup: ${Object.keys(chatSessions).length} sessions, size: ${sizeInMB}MB`);
                localStorage.setItem('chatSessions', sessionsData);
                renderChatList();
                alert('✅ Đã dọn dẹp và giữ lại 5 chat gần nhất!');
            } catch (retryError) {
                alert('❌ Không thể lưu dữ liệu. Vui lòng xóa bớt chat cũ.');
                console.error('[STORAGE] Error after cleanup:', retryError);
            }
        } else {
            console.error('[STORAGE] Error saving sessions:', e);
        }
    }
    updateStorageDisplay();
}
```

### 2. Real-time Storage Usage Display
**Location**: `ChatBot/templates/index.html` - Sidebar (line 1058-1060) & `updateStorageDisplay()` (lines 1275-1302)

**Features**:
- Shows current storage usage: "📊 Lưu trữ: X.XXmB / 10MB (XX%)"
- Color-coded indicator:
  - 🟢 Green: 0-50% usage
  - 🟠 Orange: 50-80% usage
  - 🔴 Red: 80-100% usage
- Updates automatically after each save

**UI**:
```html
<div style="padding: 10px; font-size: 11px; color: #888; border-bottom: 1px solid #333;">
    <span id="storageInfo">Đang tính...</span>
</div>
```

**Code**:
```javascript
function updateStorageDisplay() {
    try {
        const sessionsData = JSON.stringify(chatSessions);
        const sizeInMB = (new Blob([sessionsData]).size / 1024 / 1024).toFixed(2);
        const maxSizeMB = 10;
        const percentage = ((sizeInMB / maxSizeMB) * 100).toFixed(0);
        
        const storageInfo = document.getElementById('storageInfo');
        const color = percentage > 80 ? '#ff4444' : percentage > 50 ? '#ffa500' : '#4CAF50';
        
        storageInfo.innerHTML = `
            <span style="color: ${color};">📊 Lưu trữ: ${sizeInMB}MB / ${maxSizeMB}MB (${percentage}%)</span>
            <button onclick="manualCleanup()">🗑️ Dọn dẹp</button>
        `;
    } catch (e) {
        console.error('[STORAGE] Error updating storage display:', e);
    }
}
```

### 3. Manual Cleanup Button
**Location**: `ChatBot/templates/index.html` - `manualCleanup()` function (lines 1304-1328)

**Features**:
- Allows user to proactively clean up before hitting quota
- Shows confirmation dialog with current session count
- Keeps 5 most recent sessions
- Updates current chat if deleted
- Shows success message with cleanup count

**Code**:
```javascript
function manualCleanup() {
    const sessionCount = Object.keys(chatSessions).length;
    if (sessionCount <= 5) {
        alert('Chỉ còn ' + sessionCount + ' chat, không cần dọn dẹp.');
        return;
    }
    
    if (confirm(`Xóa các chat cũ và chỉ giữ lại 5 chat gần nhất?\nHiện tại có ${sessionCount} chat.`)) {
        const sortedSessions = Object.entries(chatSessions)
            .sort((a, b) => new Date(b[1].updatedAt) - new Date(a[1].updatedAt))
            .slice(0, 5);
        
        const oldCount = sessionCount;
        chatSessions = Object.fromEntries(sortedSessions);
        
        // Update current chat if deleted
        if (!chatSessions[currentChatId]) {
            currentChatId = sortedSessions[0][0];
            loadChat(currentChatId);
        }
        
        saveSessions();
        renderChatList();
        
        alert(`✅ Đã xóa ${oldCount - 5} chat cũ!\nGiữ lại 5 chat gần nhất.`);
    }
}
```

## User Experience

### Normal Operation
1. User generates images and creates chat sessions
2. Storage display shows real-time usage
3. When storage approaches limit, color changes to orange/red
4. User can click "🗑️ Dọn dẹp" to manually cleanup

### Quota Exceeded
1. User attempts to save a session that exceeds quota
2. System detects `QuotaExceededError`
3. Alert: "⚠️ Bộ nhớ trình duyệt đã đầy! Đang tự động dọn dẹp..."
4. Auto-cleanup keeps 5 most recent sessions
5. Retry save automatically
6. Alert: "✅ Đã dọn dẹp và giữ lại 5 chat gần nhất!"
7. Storage display updates to show new usage

### Manual Cleanup
1. User clicks "🗑️ Dọn dẹp" button in sidebar
2. Confirmation dialog shows current session count
3. User confirms cleanup
4. System keeps 5 most recent sessions
5. Alert shows number of deleted sessions
6. Chat list updates automatically
7. If current chat was deleted, switches to most recent chat

## Configuration

### Adjustable Parameters
- **Max sessions to keep**: Currently 5 (change in both `saveSessions()` and `manualCleanup()`)
- **Max storage size**: Currently 10MB (change `maxSizeMB` in `updateStorageDisplay()`)
- **Color thresholds**: 
  - Red: >80% usage
  - Orange: >50% usage
  - Green: ≤50% usage

### Future Improvements
1. **IndexedDB migration**: Support larger storage (50MB+) for more image-heavy chats
2. **Server-side storage**: Save images on server instead of browser
3. **Image compression**: Reduce base64 size before storage
4. **Configurable session limit**: Allow user to set how many sessions to keep
5. **Export/Import sessions**: Download/upload chat history as JSON files
6. **Selective cleanup**: Choose which sessions to delete instead of automatic "keep 5"

## Testing

### Test Scenario 1: Normal Usage
1. Generate multiple 4K images (2560x2560)
2. Create multiple chat sessions
3. Observe storage display updating
4. Verify color changes at different usage levels

### Test Scenario 2: Quota Exceeded
1. Generate enough 4K images to fill localStorage (5-6 chats)
2. Try to create new chat or save session
3. Verify auto-cleanup triggers
4. Verify only 5 most recent sessions remain
5. Verify storage display updates

### Test Scenario 3: Manual Cleanup
1. Create more than 5 chat sessions
2. Click "🗑️ Dọn dẹp" button
3. Verify confirmation dialog
4. Confirm cleanup
5. Verify 5 sessions remain
6. Verify storage display updates
7. If current chat deleted, verify switch to recent chat

## Related Features
- **Text-to-Image Tool**: 🎨 Tạo ảnh (generates large base64 images)
- **Chat Session Management**: Save/load chat history with images
- **4K Image Support**: Up to 2560x2560 resolution
- **Infinite Timeout**: Wait until image generation completes

## References
- `ChatBot/templates/index.html`: Main UI with storage management
- `ChatBot/src/utils/sd_client.py`: Stable Diffusion API client
- `ChatBot/IMAGE_GENERATION_TOOL_GUIDE.md`: Image generation documentation
- `ChatBot/README.md`: Main ChatBot documentation

## Changelog
- **2024-01-XX**: Added automatic cleanup on quota error
- **2024-01-XX**: Added real-time storage usage display
- **2024-01-XX**: Added manual cleanup button
- **2024-01-XX**: Integrated with saveSessions() for auto-update

---

**Version**: 1.5
**Last Updated**: 2024-01-XX
**Author**: AI Assistant
