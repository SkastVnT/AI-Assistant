/**
 * index.js — boot order matters.
 *
 * 1. Debug panel registers global error hooks FIRST.
 * 2. DOM cache is built and required IDs verified.
 * 3. Theme is restored from localStorage.
 * 4. Controllers wire up listeners (no fetches yet).
 * 5. Initial conversation is resolved from URL or last active id; loaded on demand.
 */

import { initDom, dom } from './dom.js';
import { initDebugPanel } from './debug-panel.js';
import { appState, patch } from './state.js';
import { chatStore } from './chat-store.js';
import { initComposer } from './composer-controller.js';
import { initSidebar, refresh as refreshSidebar } from './sidebar-controller.js';
import { initTools } from './tools-controller.js';
import { initGallery } from './gallery-controller.js';
import { renderMessageList, setTitle } from './chat-renderer.js';
import { toast } from './toast.js';

const THEMES = ['dark', 'eye-comfort'];

function _applyTheme(t) {
    if (!THEMES.includes(t)) t = 'dark';
    document.body.dataset.theme = t;
    appState.theme = t;
    chatStore.setTheme(t);
    const btn = dom('themeToggleBtn');
    if (btn) btn.textContent = t === 'dark' ? '☀' : '🌙';
}

function _wireTopbar() {
    dom('themeToggleBtn').addEventListener('click', () => {
        _applyTheme(appState.theme === 'dark' ? 'eye-comfort' : 'dark');
    });
    dom('sidebarToggleBtn').addEventListener('click', () => {
        const open = document.body.dataset.sidebar === 'open';
        document.body.dataset.sidebar = open ? '' : 'open';
    });
    dom('rightPanelToggleBtn').addEventListener('click', () => {
        const open = document.body.dataset.rightPanel === 'open';
        document.body.dataset.rightPanel = open ? '' : 'open';
    });
}

function _initialConvIdFromUrl() {
    const m = location.pathname.match(/^\/c\/([^/]+)\/?$/);
    if (m) return decodeURIComponent(m[1]);
    return null;
}

async function _loadInitialConversation() {
    const fromUrl = _initialConvIdFromUrl();
    const fromCache = chatStore.cache.getLast();
    const id = fromUrl || fromCache;
    if (!id) {
        renderMessageList([]);
        setTitle('');
        return;
    }
    try {
        await chatStore.switchTo(id);
        const conv = (appState.conversations || []).find((c) => (c._id || c.id) === id);
        setTitle(conv?.title || conv?.name || '');
        renderMessageList(appState.messages);
        try { history.replaceState({}, '', '/c/' + encodeURIComponent(id)); } catch {}
    } catch {
        // soft-fall: show empty state
        const cached = chatStore.cache.getConv(id);
        if (cached?.messages) {
            patch({ currentConversationId: id, messages: cached.messages });
            renderMessageList(cached.messages);
        } else {
            renderMessageList([]);
        }
    }
}

async function boot() {
    try {
        initDom();
    } catch (e) {
        console.error(e);
        document.body.innerHTML = `<pre style="color:#f88;padding:24px;font-family:monospace">UI shell failed to mount.\n${e.message}</pre>`;
        return;
    }
    initDebugPanel();
    _applyTheme(chatStore.getTheme());
    _wireTopbar();
    initTools();
    initComposer();
    initSidebar();
    initGallery();

    try { await refreshSidebar(); } catch (e) { console.warn('sidebar load failed', e); }
    await _loadInitialConversation();

    toast.info('UI ready', { timeout: 1500 });
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot, { once: true });
} else {
    boot();
}
