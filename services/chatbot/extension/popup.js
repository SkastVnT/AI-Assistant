/**
 * AI Assistant Extension — Popup Script
 * Mini chat interface that communicates with the AI Assistant server
 */

// State
let conversationHistory = [];
let serverUrl = 'http://localhost:5000';
let apiKey = 'ai-assistant-ext-key-2024';
let model = 'grok';
let pageContext = null;

// DOM elements
const messagesEl = document.getElementById('messages');
const inputEl = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');
const statusDot = document.getElementById('statusDot');
const settingsBtn = document.getElementById('settingsBtn');
const settingsPanel = document.getElementById('settingsPanel');
const contextBar = document.getElementById('contextBar');
const contextText = document.getElementById('contextText');
const capturePageBtn = document.getElementById('capturePageBtn');
const saveSettingsBtn = document.getElementById('saveSettings');

// ─── Initialize ───
async function init() {
    // Load settings
    const stored = await chrome.storage.sync.get(['serverUrl', 'apiKey', 'model']);
    if (stored.serverUrl) serverUrl = stored.serverUrl;
    if (stored.apiKey) apiKey = stored.apiKey;
    if (stored.model) model = stored.model;

    document.getElementById('serverUrl').value = serverUrl;
    document.getElementById('apiKey').value = apiKey;
    document.getElementById('modelSelect').value = model;

    // Load conversation history
    const local = await chrome.storage.local.get(['chatHistory', 'lastContext']);
    if (local.chatHistory) {
        conversationHistory = local.chatHistory;
        renderHistory();
    }
    if (local.lastContext && (Date.now() - local.lastContext.timestamp < 300000)) {
        pageContext = local.lastContext;
        showContext(pageContext);
    }

    // Check server health
    checkHealth();

    // Get current page info
    chrome.runtime.sendMessage({ type: 'GET_PAGE_INFO' }, (info) => {
        if (info && info.url) {
            const bar = document.getElementById('contextBar');
            bar.style.display = 'flex';
            contextText.textContent = info.title || info.url;
            
            if (info.selection) {
                pageContext = { text: info.selection, url: info.url, title: info.title };
                showContext(pageContext);
            }
        }
    });
}

// ─── Health Check ───
async function checkHealth() {
    try {
        const res = await fetch(`${serverUrl}/api/v1/health`, { 
            signal: AbortSignal.timeout(3000) 
        });
        if (res.ok) {
            statusDot.classList.add('online');
            statusDot.title = 'Connected';
        }
    } catch {
        statusDot.classList.remove('online');
        statusDot.title = 'Offline';
    }
}

// ─── Context ───
function showContext(ctx) {
    contextBar.style.display = 'flex';
    const preview = ctx.text ? ctx.text.substring(0, 80) + '...' : ctx.title || ctx.url;
    contextText.textContent = `📋 ${preview}`;
}

capturePageBtn.addEventListener('click', () => {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (!tabs[0]) return;
        chrome.tabs.sendMessage(tabs[0].id, { type: 'GET_PAGE_CONTENT' }, async (content) => {
            if (content) {
                pageContext = {
                    text: content.text || content.selection,
                    url: content.url,
                    title: content.title
                };
                showContext(pageContext);

                // Also send to server
                try {
                    await fetch(`${serverUrl}/api/v1/context`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': apiKey
                        },
                        body: JSON.stringify({
                            url: content.url,
                            title: content.title,
                            content: (content.text || '').substring(0, 8000)
                        })
                    });
                    addSystemMessage('Page context captured & sent to server');
                } catch (e) {
                    addSystemMessage('Failed to send context to server');
                }
            }
        });
    });
});

// ─── Chat ───
async function sendMessage() {
    const text = inputEl.value.trim();
    if (!text) return;

    inputEl.value = '';
    addMessage('user', text);
    conversationHistory.push({ role: 'user', content: text });

    // Show typing indicator
    const typingEl = addMessage('assistant', '<span class="loading-dots">Thinking</span>');

    sendBtn.disabled = true;

    try {
        const body = {
            message: text,
            model: model,
            history: conversationHistory.slice(-20),
            language: 'vi'
        };

        // Include page context if available
        if (pageContext && pageContext.text) {
            body.page_context = pageContext.text.substring(0, 6000);
        }

        const res = await fetch(`${serverUrl}/api/v1/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': apiKey
            },
            body: JSON.stringify(body)
        });

        const data = await res.json();

        // Remove typing indicator
        typingEl.remove();

        if (data.error) {
            addMessage('assistant', `❌ ${data.error}`);
        } else {
            const response = data.response || 'No response';
            addMessage('assistant', response);
            conversationHistory.push({ role: 'assistant', content: response });
        }
    } catch (e) {
        typingEl.remove();
        addMessage('assistant', `❌ Connection error: ${e.message}`);
    }

    sendBtn.disabled = false;
    inputEl.focus();

    // Save history
    chrome.storage.local.set({ 
        chatHistory: conversationHistory.slice(-50) 
    });
}

function addMessage(role, content) {
    const div = document.createElement('div');
    div.className = `msg ${role}`;
    div.innerHTML = content;
    messagesEl.appendChild(div);
    messagesEl.scrollTop = messagesEl.scrollHeight;
    return div;
}

function addSystemMessage(text) {
    addMessage('system', text);
}

function renderHistory() {
    messagesEl.innerHTML = '';
    conversationHistory.forEach(msg => {
        addMessage(msg.role, msg.content);
    });
}

// ─── Event Listeners ───
sendBtn.addEventListener('click', sendMessage);
inputEl.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Auto-resize textarea
inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = Math.min(inputEl.scrollHeight, 80) + 'px';
});

// Settings
settingsBtn.addEventListener('click', () => {
    settingsPanel.classList.toggle('show');
});

saveSettingsBtn.addEventListener('click', () => {
    serverUrl = document.getElementById('serverUrl').value || 'http://localhost:5000';
    apiKey = document.getElementById('apiKey').value || 'ai-assistant-ext-key-2024';
    model = document.getElementById('modelSelect').value || 'grok';

    chrome.storage.sync.set({ serverUrl, apiKey, model });
    settingsPanel.classList.remove('show');
    checkHealth();
    addSystemMessage('Settings saved ✓');
});

// Start
init();
