/**
 * chat-store.js — Mongo-first conversation repository with localStorage cache.
 *
 * Source of truth: backend (Mongo). localStorage is a fallback cache only.
 * Namespace: ui2:* (avoids collision with legacy keys).
 *
 * Structured messages: { id, role, content, parts, images, createdAt, status }
 * NEVER store rendered HTML.
 * NEVER persist base64 image data — strip before save.
 */

import { api } from './api.js';
import { appState, patch } from './state.js';
import { toast } from './toast.js';

const NS = 'ui2:';
const KEY_INDEX = NS + 'conversationsIndex';
const KEY_LAST = NS + 'lastActiveChatId';
const KEY_THEME = NS + 'theme';
const CONV_PREFIX = NS + 'conv:';
const MSG_CAP = 200;

function _convKey(id) { return CONV_PREFIX + id; }

function _safeParse(s, fallback) {
    if (!s) return fallback;
    try { return JSON.parse(s); } catch { return fallback; }
}

function _stripBase64(messages) {
    return messages.map((m) => {
        if (!m.images || !m.images.length) return m;
        const images = m.images.map((img) => {
            if (typeof img === 'string') {
                if (img.startsWith('data:')) return { stripped: true };
                return { url: img };
            }
            const out = { ...img };
            if (out.data && typeof out.data === 'string' && out.data.startsWith('data:')) delete out.data;
            if (out.b64 || out.base64) { delete out.b64; delete out.base64; out.stripped = true; }
            return out;
        });
        return { ...m, images };
    });
}

function _capMessages(messages) {
    if (!Array.isArray(messages)) return [];
    if (messages.length <= MSG_CAP) return messages;
    return messages.slice(messages.length - MSG_CAP);
}

/* ---------- localStorage layer ---------- */

const cache = {
    getIndex() { return _safeParse(localStorage.getItem(KEY_INDEX), []); },
    setIndex(list) {
        try { localStorage.setItem(KEY_INDEX, JSON.stringify(list)); }
        catch (e) { console.warn('[chat-store] cache index write failed', e); }
    },
    getConv(id) { return _safeParse(localStorage.getItem(_convKey(id)), null); },
    setConv(id, conv) {
        const safe = { ...conv, messages: _stripBase64(_capMessages(conv.messages || [])) };
        try { localStorage.setItem(_convKey(id), JSON.stringify(safe)); }
        catch (e) { console.warn('[chat-store] cache conv write failed', e); }
    },
    deleteConv(id) {
        try { localStorage.removeItem(_convKey(id)); } catch {}
    },
    getLast() { return localStorage.getItem(KEY_LAST); },
    setLast(id) {
        try {
            if (id) localStorage.setItem(KEY_LAST, id);
            else localStorage.removeItem(KEY_LAST);
        } catch {}
    },
    getTheme() { return localStorage.getItem(KEY_THEME); },
    setTheme(t) { try { localStorage.setItem(KEY_THEME, t); } catch {} },
};

/* ---------- public API ---------- */

export const chatStore = {
    cache,

    /** List conversations. Mongo first; falls back to cache on failure. */
    async listConversations() {
        try {
            const data = await api.listConversations();
            // Backend returns { conversations: [...] } or array
            const list = Array.isArray(data) ? data : (data.conversations || []);
            cache.setIndex(list);
            patch({ conversations: list, backendOk: true });
            return list;
        } catch (e) {
            console.warn('[chat-store] listConversations backend failed:', e?.message || e);
            const list = cache.getIndex();
            patch({ conversations: list, backendOk: false });
            toast.warn('Backend unreachable — showing cached conversations.');
            return list;
        }
    },

    /** Create a new conversation server-side; returns its id. */
    async create() {
        try {
            const data = await api.createConversation();
            const id = data.conversation_id || data.id || data._id;
            if (id) {
                const idx = cache.getIndex();
                idx.unshift({ _id: id, title: data.title || 'New chat', updated_at: Date.now() });
                cache.setIndex(idx);
                cache.setLast(id);
            }
            return data;
        } catch (e) {
            console.error('[chat-store] create failed', e);
            toast.error('Failed to create conversation: ' + (e.message || e));
            throw e;
        }
    },

    async switchTo(id) {
        try {
            const data = await api.switchConversation(id);
            cache.setLast(id);
            patch({ currentConversationId: id, messages: data.messages || data.history || [] });
            return data;
        } catch (e) {
            console.error('[chat-store] switch failed', e);
            toast.error('Failed to switch conversation: ' + (e.message || e));
            throw e;
        }
    },

    async deleteOne(id) {
        try {
            await api.deleteConversation(id);
            cache.deleteConv(id);
            const idx = cache.getIndex().filter((c) => (c._id || c.id) !== id);
            cache.setIndex(idx);
            if (cache.getLast() === id) cache.setLast(null);
            return true;
        } catch (e) {
            console.error('[chat-store] delete failed', e);
            toast.error('Delete failed: ' + (e.message || e));
            throw e;
        }
    },

    /** Persist the active conversation messages to local cache. */
    persistActive() {
        const id = appState.currentConversationId;
        if (!id) return;
        cache.setConv(id, { id, messages: appState.messages });
    },

    appendMessage(msg) {
        appState.messages = _capMessages([...appState.messages, msg]);
        chatStore.persistActive();
    },

    replaceLastAssistant(updates) {
        for (let i = appState.messages.length - 1; i >= 0; i--) {
            if (appState.messages[i].role === 'assistant') {
                appState.messages[i] = { ...appState.messages[i], ...updates };
                chatStore.persistActive();
                return;
            }
        }
    },

    getActive() {
        const id = appState.currentConversationId || cache.getLast();
        if (!id) return null;
        const cached = cache.getConv(id);
        return { id, messages: cached?.messages || [] };
    },

    getTheme() { return cache.getTheme() || 'dark'; },
    setTheme(t) { cache.setTheme(t); },
};
