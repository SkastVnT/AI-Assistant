# ChatGPT-Style UI Upgrade Plan

## 📋 Overview
Nâng cấp giao diện ChatBot lên phong cách ChatGPT với các tính năng mới, đồng thời giữ nguyên **TẤT CẢ** các tính năng và tools hiện có.

---

## 🎯 Goals
1. ✅ Giao diện ChatGPT-style: clean, modern, professional
2. ✅ Search chat functionality
3. ✅ Message version navigation (< 2/2 >)
4. ✅ Projects system (group chats, shared learning)
5. ✅ Toggle sidebar
6. ✅ **GIỮ NGUYÊN** tất cả tính năng: Image Gen, Memory, File Upload, Tools, etc.

---

## 📁 Phase 1: Design & HTML/CSS ✅ COMPLETED

### Files Created:
- ✅ `templates/index_chatgpt_v2.html` - New HTML with ChatGPT structure
- ✅ `static/css/style_chatgpt_v2.css` - New CSS with modern design

### Features Implemented:
1. **Sidebar (Left Panel)**
   - New chat button
   - Search box for chat history
   - Projects section (collapsible)
   - Chat history section (collapsible)
   - Storage info (compact)
   - Toggle sidebar button

2. **Main Content Area**
   - Minimal header with settings
   - Collapsible controls panel
   - Clean chat interface
   - Message version navigation placeholders
   - Modern input area with tools

3. **Design System**
   - CSS variables for theming
   - Dark mode support
   - Smooth transitions
   - Responsive layout
   - ChatGPT-inspired spacing and colors

---

## 📁 Phase 2: Search Functionality (NEXT)

### Implementation Plan:

#### 2.1 Search UI (Already in HTML)
```html
<div class="sidebar-search">
  <input id="chatSearchInput" placeholder="Search chats...">
  <button id="searchClearBtn">×</button>
</div>
```

#### 2.2 Search Logic (To Add in JS)
```javascript
// In chat-manager.js
searchChats(query) {
    if (!query) return this.chatSessions;
    
    const results = {};
    query = query.toLowerCase();
    
    for (const [id, session] of Object.entries(this.chatSessions)) {
        // Search in title
        if (session.title.toLowerCase().includes(query)) {
            results[id] = { ...session, matchType: 'title' };
            continue;
        }
        
        // Search in messages
        const messageMatch = session.messages.some(msg => {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = msg;
            const text = tempDiv.textContent.toLowerCase();
            return text.includes(query);
        });
        
        if (messageMatch) {
            results[id] = { ...session, matchType: 'content' };
        }
    }
    
    return results;
}
```

#### 2.3 Search Event Handlers
```javascript
// In main_v2.js
setupSearchHandlers() {
    const searchInput = document.getElementById('chatSearchInput');
    const clearBtn = document.getElementById('searchClearBtn');
    
    searchInput.addEventListener('input', (e) => {
        const query = e.target.value;
        const results = this.chatManager.searchChats(query);
        this.renderSearchResults(results);
        clearBtn.style.display = query ? 'block' : 'none';
    });
    
    clearBtn.addEventListener('click', () => {
        searchInput.value = '';
        this.loadAllChats();
        clearBtn.style.display = 'none';
    });
}
```

---

## 📁 Phase 3: Message History Navigation (< 2/2 >)

### Implementation Plan:

#### 3.1 Data Structure
```javascript
// Extend messageHistory in main app
this.messageHistory = {
    'msg_123': [
        { version: 1, content: '...', timestamp: '...', model: 'gemini' },
        { version: 2, content: '...', timestamp: '...', model: 'gemini' },
        { version: 3, content: '...', timestamp: '...', model: 'openai' }
    ]
};
this.currentVersionIndex = {};  // { 'msg_123': 2 }
```

#### 3.2 UI Component
```html
<!-- Add to message footer -->
<div class="message-version-nav" data-message-id="msg_123">
    <button class="version-nav-btn prev">
        <svg><!-- Left arrow --></svg>
    </button>
    <span class="version-indicator">2 / 3</span>
    <button class="version-nav-btn next">
        <svg><!-- Right arrow --></svg>
    </button>
</div>
```

#### 3.3 Navigation Logic
```javascript
navigateMessageVersion(messageId, direction) {
    const versions = this.messageHistory[messageId];
    if (!versions || versions.length <= 1) return;
    
    const currentIndex = this.currentVersionIndex[messageId] || versions.length - 1;
    let newIndex = currentIndex + direction;
    
    // Clamp to valid range
    if (newIndex < 0) newIndex = 0;
    if (newIndex >= versions.length) newIndex = versions.length - 1;
    
    this.currentVersionIndex[messageId] = newIndex;
    
    // Update UI
    const messageDiv = document.querySelector(`[data-message-id="${messageId}"]`);
    const version = versions[newIndex];
    messageDiv.querySelector('.message-text').innerHTML = version.content;
    messageDiv.querySelector('.version-indicator').textContent = 
        `${newIndex + 1} / ${versions.length}`;
    
    // Update nav buttons state
    this.updateVersionNavButtons(messageId);
}
```

---

## 📁 Phase 4: Projects System

### Implementation Plan:

#### 4.1 Data Structure
```javascript
// Add to ChatManager
this.projects = {
    'proj_1': {
        id: 'proj_1',
        name: 'Web Development',
        description: 'All chats about web dev',
        chatIds: ['chat_1', 'chat_5', 'chat_12'],
        sharedContext: '',  // Compiled learning from all chats
        createdAt: new Date(),
        updatedAt: new Date()
    }
};
```

#### 4.2 UI Components
```html
<!-- Project Item -->
<div class="project-item" data-project-id="proj_1">
    <div class="project-header">
        <svg class="project-icon">📁</svg>
        <span class="project-name">Web Development</span>
        <button class="project-toggle">▼</button>
    </div>
    <div class="project-chats">
        <!-- Chat items inside project -->
    </div>
    <div class="project-actions">
        <button class="add-chat-to-project">+ Add chat</button>
    </div>
</div>
```

#### 4.3 Shared Learning Logic
```javascript
// When sending message in a project
async sendMessageWithProjectContext(message, projectId) {
    const project = this.getProject(projectId);
    const sharedContext = await this.buildProjectContext(project);
    
    const fullPrompt = `
Project Context: ${project.name}
${sharedContext}

Current Question: ${message}
    `;
    
    return this.apiService.sendMessage(fullPrompt, ...otherParams);
}

buildProjectContext(project) {
    // Compile key learnings from all chats in project
    let context = '';
    
    for (const chatId of project.chatIds) {
        const chat = this.chatManager.getSession(chatId);
        // Extract important messages/code/insights
        context += this.extractKeyInsights(chat);
    }
    
    return context;
}
```

---

## 📁 Phase 5: Toggle Sidebar & UI Polish

### Implementation Plan:

#### 5.1 Toggle Functionality
```javascript
toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
    
    // Save state
    localStorage.setItem('sidebarCollapsed', 
        sidebar.classList.contains('collapsed'));
}

// On load
const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
if (sidebarCollapsed) {
    document.getElementById('sidebar').classList.add('collapsed');
}
```

#### 5.2 Animations & Transitions
```css
/* Already in CSS */
.sidebar {
    transition: transform var(--transition-normal), 
                width var(--transition-normal);
}

.message {
    animation: messageSlideIn 0.3s ease;
}
```

#### 5.3 Mobile Responsive
```css
@media (max-width: 768px) {
    .sidebar {
        position: fixed;
        transform: translateX(-100%);
    }
    
    .sidebar.open {
        transform: translateX(0);
    }
}
```

---

## 📁 Phase 6: Integration & Testing

### 6.1 Merge Existing Features

**All existing features MUST work:**
- ✅ Image Generation (Text2Img, Img2Img)
- ✅ Memory/Learning System
- ✅ File Upload & Analysis
- ✅ Tools (Google Search, GitHub, etc.)
- ✅ Multi-model support
- ✅ Dark mode
- ✅ Export (PDF, JSON, Text)
- ✅ Edit message functionality
- ✅ Code highlighting
- ✅ Markdown rendering

### 6.2 Testing Checklist

#### UI Tests:
- [ ] Sidebar search works
- [ ] Projects can be created/deleted
- [ ] Chats can be added to projects
- [ ] Message version navigation works
- [ ] Sidebar toggles correctly
- [ ] Mobile responsive works
- [ ] Dark mode switches properly

#### Feature Tests:
- [ ] Image generation still works
- [ ] Memory system functional
- [ ] File upload processes correctly
- [ ] All tools activate properly
- [ ] Models switch correctly
- [ ] Export functions work
- [ ] Edit message preserved

#### Integration Tests:
- [ ] New chat in project
- [ ] Search while in project
- [ ] File upload in project chat
- [ ] Image gen with project context
- [ ] Memory sharing across project

---

## 🚀 Implementation Order

### Week 1:
1. ✅ Phase 1: HTML/CSS Design (DONE)
2. Create base JavaScript structure
3. Implement search functionality

### Week 2:
4. Implement message version navigation
5. Create projects data structure
6. Build projects UI

### Week 3:
7. Implement project shared learning
8. Add toggle sidebar
9. UI polish & animations

### Week 4:
10. Integration testing
11. Bug fixes
12. Documentation
13. Deployment

---

## 📝 File Structure

```
ChatBot/
├── templates/
│   ├── index.html (original - keep)
│   └── index_chatgpt_v2.html (new)
├── static/
│   ├── css/
│   │   ├── style.css (original)
│   │   └── style_chatgpt_v2.css (new)
│   └── js/
│       ├── main.js (original)
│       ├── main_v2.js (new - will create)
│       └── modules/
│           ├── chat-manager.js (extend)
│           ├── projects-manager.js (new)
│           ├── search-handler.js (new)
│           └── version-navigator.js (new)
└── docs/
    └── CHATGPT_UPGRADE_PLAN.md (this file)
```

---

## 🔄 Migration Strategy

### Option 1: Parallel Development (Recommended)
- Keep `index.html` + `style.css` + `main.js` (original)
- Develop `index_chatgpt_v2.html` + `style_chatgpt_v2.css` + `main_v2.js`
- Users can switch via route: `/` (old) or `/v2` (new)
- Once stable, replace old with new

### Option 2: In-place Upgrade
- Backup original files
- Replace HTML/CSS/JS
- Test extensively
- Rollback if issues

### Option 3: Feature Flag
- Single codebase
- Toggle features via settings
- Gradual rollout

**Recommendation: Option 1** for safety during development.

---

## 🎨 Design Tokens

```css
/* Light Mode */
--bg-primary: #FFFFFF
--bg-secondary: #F7F7F8
--text-primary: #2D333A
--accent-primary: #10A37F

/* Dark Mode */
--bg-primary: #212121
--bg-secondary: #2F2F2F
--text-primary: #ECECF1
--accent-primary: #19C37D
```

---

## 📚 References

- ChatGPT UI: https://chat.openai.com
- Design inspiration: Minimal, clean, functional
- Color scheme: Professional green accents
- Typography: System fonts for performance

---

## ✅ Success Criteria

1. **Visual**: Looks like ChatGPT
2. **Functional**: All new features work
3. **Compatible**: All old features preserved
4. **Performance**: No slowdowns
5. **Responsive**: Works on all devices
6. **Accessible**: Keyboard navigation works

---

## 🐛 Known Issues & TODOs

- [ ] Implement full Text2Img/Img2Img modal content in HTML
- [ ] Create JavaScript for search functionality
- [ ] Build message version navigator
- [ ] Implement projects system backend
- [ ] Add keyboard shortcuts
- [ ] Optimize for performance
- [ ] Add unit tests

---

**Last Updated**: 2025-01-07
**Status**: Phase 1 Complete ✅
**Next**: Phase 2 - Search Implementation
