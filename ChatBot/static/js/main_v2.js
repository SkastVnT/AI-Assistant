/**
 * Main V2 Application Entry Point
 * ChatGPT-style UI with enhanced features
 */

import ChatManager from './modules/chat-manager.js';
import APIService from './modules/api-service.js';
import MessageRenderer from './modules/message-renderer.js';
import FileHandler from './modules/file-handler.js';
import ImageGenerator from './modules/image-gen.js';
import MemoryManager from './modules/memory-manager.js';
import ExportHandler from './modules/export-handler.js';
import UIUtils from './modules/ui-utils.js';
import PerformanceUtils from './modules/performance-utils.js';
import SearchHandler from './modules/search-handler.js';
import VersionNavigator from './modules/version-navigator.js';
import ProjectsManager from './modules/projects-manager.js';
import PreferencesManager, { SidebarToggle, NotificationManager } from './modules/preferences-manager.js';

/**
 * Application state
 */
const app = {
    chatManager: null,
    apiService: null,
    messageRenderer: null,
    fileHandler: null,
    imageGenerator: null,
    memoryManager: null,
    exportHandler: null,
    searchHandler: null,
    versionNavigator: null,
    projectsManager: null,
    preferencesManager: null,
    sidebarToggle: null,
    notificationManager: null,
    initialized: false
};

/**
 * Initialize all application modules
 */
async function initializeApp() {
    try {
        console.log('🚀 Initializing ChatGPT V2 Interface...');
        
        // Initialize preferences manager first (Phase 5)
        app.preferencesManager = new PreferencesManager();
        app.preferencesManager.initialize();
        
        // Initialize notification manager (Phase 5)
        app.notificationManager = new NotificationManager(app.preferencesManager);
        
        // Initialize core services
        app.apiService = new APIService();
        app.messageRenderer = new MessageRenderer();
        
        // Initialize chat manager (core module)
        app.chatManager = new ChatManager(app.apiService, app.messageRenderer);
        
        // Initialize feature modules
        app.fileHandler = new FileHandler(app.chatManager);
        app.imageGenerator = new ImageGenerator(app.chatManager, app.apiService);
        app.memoryManager = new MemoryManager(app.apiService);
        app.exportHandler = new ExportHandler(app.chatManager);
        
        // Initialize search handler (Phase 2)
        app.searchHandler = new SearchHandler(app.chatManager);
        
        // Initialize version navigator (Phase 3)
        app.versionNavigator = new VersionNavigator(app.chatManager, app.messageRenderer);
        
        // Initialize projects manager (Phase 4)
        app.projectsManager = new ProjectsManager(app.chatManager, app.memoryManager);
        
        // Initialize sidebar toggle (Phase 5)
        app.sidebarToggle = new SidebarToggle(app.preferencesManager);
        
        // Initialize all modules
        await Promise.all([
            app.chatManager.init(),
            app.fileHandler.init(),
            app.imageGenerator.init(),
            app.memoryManager.init(),
            app.exportHandler.init(),
            app.searchHandler.init(),
            app.versionNavigator.init(),
            app.projectsManager.init()
        ]);
        
        // Setup event listeners
        setupEventListeners();
        
        // Setup UI components
        setupUI();
        
        // Load chat history
        await loadChatHistory();
        
        app.initialized = true;
        console.log('✅ Application initialized successfully');
        
        // Show success notification
        app.notificationManager.show('ChatGPT V2 loaded successfully', 'success', 2000);
        
        // Performance monitoring
        if (window.performance) {
            const perfData = performance.getEntriesByType('navigation')[0];
            console.log(`⚡ Load time: ${perfData.loadEventEnd - perfData.fetchStart}ms`);
        }
        
    } catch (error) {
        console.error('❌ Failed to initialize application:', error);
        showErrorNotification('Failed to initialize application. Please refresh the page.');
    }
}

/**
 * Setup all event listeners
 */
function setupEventListeners() {
    // Send message
    const sendBtn = document.getElementById('sendBtn');
    const messageInput = document.getElementById('messageInput');
    
    if (sendBtn) {
        sendBtn.addEventListener('click', handleSendMessage);
    }
    
    if (messageInput) {
        messageInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSendMessage();
            }
        });
        
        // Auto-resize textarea
        messageInput.addEventListener('input', autoResizeTextarea);
    }
    
    // New chat button
    const newChatBtn = document.getElementById('newChatBtn');
    if (newChatBtn) {
        newChatBtn.addEventListener('click', handleNewChat);
    }
    
    // Sidebar toggle
    const toggleSidebarBtn = document.getElementById('toggleSidebar');
    if (toggleSidebarBtn) {
        toggleSidebarBtn.addEventListener('click', toggleSidebar);
    }
    
    // Dark mode toggle
    const darkModeToggle = document.getElementById('darkModeToggle');
    const themeToggleBtn = document.getElementById('themeToggleBtn');
    
    if (darkModeToggle) {
        darkModeToggle.addEventListener('click', toggleDarkMode);
    }
    
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = app.preferencesManager.get('theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            app.preferencesManager.applyTheme(newTheme);
            app.notificationManager.show(
                `Switched to ${newTheme} mode`, 
                'success', 
                1500
            );
        });
    }
    
    // Model selector
    const modelSelector = document.getElementById('modelSelector');
    if (modelSelector) {
        modelSelector.addEventListener('change', handleModelChange);
    }
    
    // File upload
    const fileInput = document.getElementById('fileInput');
    const attachFileBtn = document.getElementById('attachFileBtn');
    
    if (attachFileBtn && fileInput) {
        attachFileBtn.addEventListener('click', () => fileInput.click());
        fileInput.addEventListener('change', handleFileUpload);
    }
    
    // Stop generation
    const stopBtn = document.getElementById('stopBtn');
    if (stopBtn) {
        stopBtn.addEventListener('click', handleStopGeneration);
    }
    
    // Export buttons
    setupExportButtons();
    
    // Keyboard shortcuts
    document.addEventListener('keydown', handleKeyboardShortcuts);
    
    // Handle window resize for responsive behavior
    window.addEventListener('resize', PerformanceUtils.debounce(handleResize, 300));
    
    console.log('✅ Event listeners setup complete');
}

/**
 * Setup UI components and initial states
 */
function setupUI() {
    // Load dark mode preference
    const darkMode = localStorage.getItem('darkMode') === 'true';
    if (darkMode) {
        document.body.classList.add('dark-mode');
        updateDarkModeIcon(true);
    }
    
    // Load sidebar state
    const sidebarCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (sidebarCollapsed) {
        document.body.classList.add('sidebar-collapsed');
    }
    
    // Load model preference
    const savedModel = localStorage.getItem('selectedModel');
    const modelSelector = document.getElementById('modelSelector');
    if (savedModel && modelSelector) {
        modelSelector.value = savedModel;
    }
    
    // Initialize tooltips
    initializeTooltips();
    
    console.log('✅ UI setup complete');
}

/**
 * Load chat history from storage
 */
async function loadChatHistory() {
    try {
        const chats = await app.chatManager.loadChats();
        renderChatList(chats);
        
        // Load most recent chat if exists
        if (chats.length > 0) {
            await app.chatManager.loadChat(chats[0].id);
        } else {
            // Start new chat if no history
            await handleNewChat();
        }
    } catch (error) {
        console.error('Failed to load chat history:', error);
    }
}

/**
 * Render chat list in sidebar
 */
function renderChatList(chats) {
    const chatList = document.getElementById('chatList');
    if (!chatList) return;
    
    chatList.innerHTML = '';
    
    if (chats.length === 0) {
        chatList.innerHTML = `
            <div class="empty-state">
                <p>No chats yet</p>
                <p class="empty-state-hint">Start a new conversation</p>
            </div>
        `;
        return;
    }
    
    // Group chats by date
    const grouped = groupChatsByDate(chats);
    
    Object.entries(grouped).forEach(([date, dateChats]) => {
        // Add date header
        const dateHeader = document.createElement('div');
        dateHeader.className = 'chat-date-header';
        dateHeader.textContent = date;
        chatList.appendChild(dateHeader);
        
        // Add chats for this date
        dateChats.forEach(chat => {
            const chatItem = createChatListItem(chat);
            chatList.appendChild(chatItem);
        });
    });
}

/**
 * Create chat list item element
 */
function createChatListItem(chat) {
    const item = document.createElement('div');
    item.className = 'chat-item';
    item.dataset.chatId = chat.id;
    
    if (chat.id === app.chatManager.currentChatId) {
        item.classList.add('active');
    }
    
    const title = chat.title || 'New Chat';
    const preview = chat.lastMessage || 'No messages yet';
    const date = formatChatDate(chat.updated_at);
    
    item.innerHTML = `
        <div class="chat-item-content">
            <div class="chat-item-title">${UIUtils.escapeHtml(title)}</div>
            <div class="chat-item-preview">${UIUtils.escapeHtml(preview)}</div>
        </div>
        <div class="chat-item-actions">
            <button class="chat-item-action" data-action="rename" title="Rename">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"></path>
                    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"></path>
                </svg>
            </button>
            <button class="chat-item-action" data-action="delete" title="Delete">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                </svg>
            </button>
        </div>
    `;
    
    // Click to load chat
    item.addEventListener('click', (e) => {
        if (!e.target.closest('.chat-item-action')) {
            app.chatManager.loadChat(chat.id);
        }
    });
    
    // Action buttons
    const renameBtn = item.querySelector('[data-action="rename"]');
    const deleteBtn = item.querySelector('[data-action="delete"]');
    
    renameBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        handleRenameChat(chat.id);
    });
    
    deleteBtn?.addEventListener('click', (e) => {
        e.stopPropagation();
        handleDeleteChat(chat.id);
    });
    
    return item;
}

/**
 * Group chats by date (Today, Yesterday, Last 7 days, etc.)
 */
function groupChatsByDate(chats) {
    const groups = {
        'Today': [],
        'Yesterday': [],
        'Last 7 Days': [],
        'Last 30 Days': [],
        'Older': []
    };
    
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const lastWeek = new Date(today);
    lastWeek.setDate(lastWeek.getDate() - 7);
    const lastMonth = new Date(today);
    lastMonth.setDate(lastMonth.getDate() - 30);
    
    chats.forEach(chat => {
        const chatDate = new Date(chat.updated_at);
        
        if (chatDate >= today) {
            groups['Today'].push(chat);
        } else if (chatDate >= yesterday) {
            groups['Yesterday'].push(chat);
        } else if (chatDate >= lastWeek) {
            groups['Last 7 Days'].push(chat);
        } else if (chatDate >= lastMonth) {
            groups['Last 30 Days'].push(chat);
        } else {
            groups['Older'].push(chat);
        }
    });
    
    // Remove empty groups
    return Object.fromEntries(
        Object.entries(groups).filter(([_, chats]) => chats.length > 0)
    );
}

/**
 * Format chat date for display
 */
function formatChatDate(date) {
    const d = new Date(date);
    const now = new Date();
    const diff = now - d;
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);
    
    if (hours < 1) return 'Just now';
    if (hours < 24) return `${hours}h ago`;
    if (days < 7) return `${days}d ago`;
    
    return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

/**
 * Handle send message
 */
async function handleSendMessage() {
    const messageInput = document.getElementById('messageInput');
    if (!messageInput) return;
    
    const message = messageInput.value.trim();
    if (!message) return;
    
    // Clear input
    messageInput.value = '';
    autoResizeTextarea({ target: messageInput });
    
    // Disable send button
    const sendBtn = document.getElementById('sendBtn');
    if (sendBtn) {
        sendBtn.disabled = true;
    }
    
    try {
        // Send message through chat manager
        await app.chatManager.sendMessage(message);
    } catch (error) {
        console.error('Failed to send message:', error);
        showErrorNotification('Failed to send message. Please try again.');
    } finally {
        // Re-enable send button
        if (sendBtn) {
            sendBtn.disabled = false;
        }
        messageInput.focus();
    }
}

/**
 * Handle new chat
 */
async function handleNewChat() {
    try {
        await app.chatManager.createNewChat();
        showSuccessNotification('New chat started');
    } catch (error) {
        console.error('Failed to create new chat:', error);
        showErrorNotification('Failed to create new chat');
    }
}

/**
 * Handle rename chat
 */
async function handleRenameChat(chatId) {
    const chat = app.chatManager.getChat(chatId);
    if (!chat) return;
    
    const newTitle = prompt('Enter new chat title:', chat.title || 'New Chat');
    if (newTitle && newTitle.trim()) {
        try {
            await app.chatManager.renameChat(chatId, newTitle.trim());
            showSuccessNotification('Chat renamed');
        } catch (error) {
            console.error('Failed to rename chat:', error);
            showErrorNotification('Failed to rename chat');
        }
    }
}

/**
 * Handle delete chat
 */
async function handleDeleteChat(chatId) {
    if (!confirm('Are you sure you want to delete this chat?')) {
        return;
    }
    
    try {
        await app.chatManager.deleteChat(chatId);
        showSuccessNotification('Chat deleted');
    } catch (error) {
        console.error('Failed to delete chat:', error);
        showErrorNotification('Failed to delete chat');
    }
}

/**
 * Toggle sidebar
 */
function toggleSidebar() {
    const collapsed = document.body.classList.toggle('sidebar-collapsed');
    localStorage.setItem('sidebarCollapsed', collapsed);
}

/**
 * Toggle dark mode
 */
function toggleDarkMode() {
    const darkMode = document.body.classList.toggle('dark-mode');
    localStorage.setItem('darkMode', darkMode);
    updateDarkModeIcon(darkMode);
}

/**
 * Update dark mode icon
 */
function updateDarkModeIcon(isDark) {
    const icon = document.querySelector('#darkModeToggle svg');
    if (!icon) return;
    
    if (isDark) {
        icon.innerHTML = `
            <circle cx="12" cy="12" r="5"></circle>
            <line x1="12" y1="1" x2="12" y2="3"></line>
            <line x1="12" y1="21" x2="12" y2="23"></line>
            <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
            <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
            <line x1="1" y1="12" x2="3" y2="12"></line>
            <line x1="21" y1="12" x2="23" y2="12"></line>
            <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
            <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
        `;
    } else {
        icon.innerHTML = `
            <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>
        `;
    }
}

/**
 * Handle model change
 */
function handleModelChange(e) {
    const model = e.target.value;
    localStorage.setItem('selectedModel', model);
    app.chatManager.setModel(model);
}

/**
 * Handle file upload
 */
async function handleFileUpload(e) {
    const files = Array.from(e.target.files);
    if (files.length === 0) return;
    
    try {
        await app.fileHandler.handleFiles(files);
        showSuccessNotification(`${files.length} file(s) uploaded`);
    } catch (error) {
        console.error('Failed to upload files:', error);
        showErrorNotification('Failed to upload files');
    }
    
    // Clear input
    e.target.value = '';
}

/**
 * Handle stop generation
 */
function handleStopGeneration() {
    app.chatManager.stopGeneration();
    showInfoNotification('Generation stopped');
}

/**
 * Setup export buttons
 */
function setupExportButtons() {
    const exportPdfBtn = document.getElementById('exportPdf');
    const exportJsonBtn = document.getElementById('exportJson');
    const exportTextBtn = document.getElementById('exportText');
    
    if (exportPdfBtn) {
        exportPdfBtn.addEventListener('click', () => app.exportHandler.exportToPdf());
    }
    
    if (exportJsonBtn) {
        exportJsonBtn.addEventListener('click', () => app.exportHandler.exportToJson());
    }
    
    if (exportTextBtn) {
        exportTextBtn.addEventListener('click', () => app.exportHandler.exportToText());
    }
}

/**
 * Handle keyboard shortcuts
 */
function handleKeyboardShortcuts(e) {
    // Ctrl/Cmd + K: Focus message input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        document.getElementById('messageInput')?.focus();
    }
    
    // Ctrl/Cmd + Shift + N: New chat
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'N') {
        e.preventDefault();
        handleNewChat();
    }
    
    // Ctrl/Cmd + B: Toggle sidebar
    if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
        e.preventDefault();
        toggleSidebar();
    }
    
    // Search shortcut is handled by SearchHandler module
}

/**
 * Auto-resize textarea
 */
function autoResizeTextarea(e) {
    const textarea = e.target;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 200) + 'px';
}

/**
 * Handle window resize
 */
function handleResize() {
    // Adjust layout for mobile
    if (window.innerWidth < 768) {
        document.body.classList.add('mobile');
    } else {
        document.body.classList.remove('mobile');
    }
}

/**
 * Initialize tooltips
 */
function initializeTooltips() {
    // Add tooltips to buttons with title attribute
    document.querySelectorAll('[title]').forEach(element => {
        element.addEventListener('mouseenter', showTooltip);
        element.addEventListener('mouseleave', hideTooltip);
    });
}

/**
 * Show tooltip
 */
function showTooltip(e) {
    const title = e.target.getAttribute('title');
    if (!title) return;
    
    // Create tooltip element
    const tooltip = document.createElement('div');
    tooltip.className = 'tooltip';
    tooltip.textContent = title;
    tooltip.id = 'active-tooltip';
    
    document.body.appendChild(tooltip);
    
    // Position tooltip
    const rect = e.target.getBoundingClientRect();
    tooltip.style.top = rect.bottom + 8 + 'px';
    tooltip.style.left = rect.left + (rect.width / 2) - (tooltip.offsetWidth / 2) + 'px';
}

/**
 * Hide tooltip
 */
function hideTooltip() {
    const tooltip = document.getElementById('active-tooltip');
    if (tooltip) {
        tooltip.remove();
    }
}

/**
 * Show notification
 */
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    document.body.appendChild(notification);
    
    // Trigger animation
    setTimeout(() => notification.classList.add('show'), 10);
    
    // Auto-hide after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

function showSuccessNotification(message) {
    showNotification(message, 'success');
}

function showErrorNotification(message) {
    showNotification(message, 'error');
}

function showInfoNotification(message) {
    showNotification(message, 'info');
}

/**
 * Initialize app when DOM is ready
 */
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeApp);
} else {
    initializeApp();
}

/**
 * Export app instance for debugging
 */
window.ChatApp = app;
