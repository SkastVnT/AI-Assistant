/**
 * dom.js — single source of cached DOM references.
 * Throws on missing required ids so failures are loud, not silent.
 */

const REQUIRED_IDS = [
    'sidebar', 'newChatBtn', 'refreshConvsBtn', 'conversationList', 'sidebarStatus',
    'topbar', 'sidebarToggleBtn', 'conversationTitle', 'rightPanelToggleBtn',
    'themeToggleBtn', 'debugToggleBtn',
    'chatContainer', 'messageList', 'streamStatus', 'streamStatusText',
    'composer', 'composerChips', 'composerInput', 'attachFilesBtn', 'fileInput',
    'sendBtn', 'stopBtn', 'toolsBar',
    'rightPanel', 'galleryGrid', 'galleryCount',
    'modalRoot', 'toastRoot', 'debugPanel',
];

const cache = {};

export function initDom() {
    const missing = [];
    for (const id of REQUIRED_IDS) {
        const el = document.getElementById(id);
        if (!el) { missing.push(id); continue; }
        cache[id] = el;
    }
    if (missing.length) {
        const msg = `[dom] Missing required elements: ${missing.join(', ')}`;
        console.error(msg);
        throw new Error(msg);
    }
    return cache;
}

export function dom(id) {
    if (!cache[id]) {
        const el = document.getElementById(id);
        if (el) cache[id] = el;
    }
    return cache[id];
}

export const $ = dom;
