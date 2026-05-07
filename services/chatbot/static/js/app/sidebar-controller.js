/**
 * sidebar-controller.js — conversation list, new chat, refresh, single delete.
 *
 * Locked feature set: { New chat, list, switch, single delete, refresh }.
 * Explicitly absent: bulk delete, drag reorder, storage gauge, quota, payment.
 */

import { dom } from './dom.js';
import { chatStore } from './chat-store.js';
import { appState, patch } from './state.js';
import { streamController } from './stream-controller.js';
import { renderMessageList, setTitle } from './chat-renderer.js';
import { toast } from './toast.js';

function _convId(c) { return c._id || c.id; }
function _convTitle(c) { return c.title || c.name || 'Untitled'; }

function _setActive(id) {
    const list = dom('conversationList');
    if (!list) return;
    list.querySelectorAll('.sidebar__item').forEach((el) => {
        el.classList.toggle('is-active', el.dataset.convId === id);
    });
}

function _renderList() {
    const list = dom('conversationList');
    if (!list) return;
    list.innerHTML = '';
    if (!appState.conversations.length) {
        const empty = document.createElement('div');
        empty.className = 'sidebar__empty';
        empty.textContent = 'No conversations yet.';
        list.appendChild(empty);
        return;
    }
    const frag = document.createDocumentFragment();
    for (const c of appState.conversations) {
        const id = _convId(c);
        const item = document.createElement('div');
        item.className = 'sidebar__item';
        item.dataset.convId = id;
        if (id === appState.currentConversationId) item.classList.add('is-active');
        item.innerHTML = `
            <button class="sidebar__item-label" type="button"></button>
            <button class="sidebar__item-delete" type="button" title="Delete" aria-label="Delete">×</button>
        `;
        item.querySelector('.sidebar__item-label').textContent = _convTitle(c);
        item.querySelector('.sidebar__item-label').addEventListener('click', () => _switch(id));
        item.querySelector('.sidebar__item-delete').addEventListener('click', (e) => {
            e.stopPropagation();
            _deleteOne(id, item);
        });
        frag.appendChild(item);
    }
    list.appendChild(frag);
}

async function _switch(id) {
    if (id === appState.currentConversationId) return;
    if (streamController.isStreaming()) {
        streamController.stop();
        await new Promise((r) => setTimeout(r, 50));
    }
    try {
        const data = await chatStore.switchTo(id);
        const conv = (appState.conversations.find((c) => _convId(c) === id)) || {};
        setTitle(_convTitle(conv));
        renderMessageList(appState.messages);
        _setActive(id);
        try { history.replaceState({}, '', '/c/' + encodeURIComponent(id)); } catch {}
    } catch {}
}

async function _newChat() {
    if (streamController.isStreaming()) streamController.stop();
    try {
        const data = await chatStore.create();
        const id = data.conversation_id || data.id || data._id;
        await refresh();
        if (id) {
            patch({ currentConversationId: id, messages: [] });
            setTitle('');
            renderMessageList([]);
            _setActive(id);
            try { history.replaceState({}, '', '/c/' + encodeURIComponent(id)); } catch {}
        }
    } catch {}
}

async function _deleteOne(id, itemEl) {
    if (!confirm('Delete this conversation?')) return;
    itemEl?.classList.add('is-deleting');
    try {
        await chatStore.deleteOne(id);
        if (id === appState.currentConversationId) {
            patch({ currentConversationId: null, messages: [] });
            setTitle('');
            renderMessageList([]);
            try { history.replaceState({}, '', '/'); } catch {}
        }
        await refresh();
    } catch {
        itemEl?.classList.remove('is-deleting');
    }
}

export async function refresh() {
    const status = dom('sidebarStatus');
    if (status) status.textContent = 'Loading…';
    await chatStore.listConversations();
    _renderList();
    if (status) status.textContent = `${appState.conversations.length} chat${appState.conversations.length === 1 ? '' : 's'}`;
}

export function initSidebar() {
    dom('newChatBtn').addEventListener('click', _newChat);
    dom('refreshConvsBtn').addEventListener('click', refresh);

    document.addEventListener('appstatechange', (e) => {
        if (e.detail?.type === 'patch' && (e.detail.changes?.conversations || e.detail.changes?.currentConversationId !== undefined)) {
            _renderList();
        }
    });
}
