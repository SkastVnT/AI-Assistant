/**
 * api.js — thin wrappers around chatbot REST + SSE endpoints.
 *
 * Backend contract is unchanged. We do NOT wrap or rename event names.
 */

let _fetchHook = null;

export function setFetchHook(fn) { _fetchHook = fn; }

async function _fetch(url, opts = {}) {
    const t0 = performance.now();
    let resp;
    try {
        resp = await fetch(url, opts);
    } catch (e) {
        if (_fetchHook) _fetchHook({ url, method: opts.method || 'GET', error: String(e), ms: performance.now() - t0 });
        throw e;
    }
    if (_fetchHook) _fetchHook({ url, method: opts.method || 'GET', status: resp.status, ms: performance.now() - t0 });
    return resp;
}

async function _json(url, opts = {}) {
    const resp = await _fetch(url, opts);
    const ct = resp.headers.get('content-type') || '';
    const data = ct.includes('application/json') ? await resp.json().catch(() => ({})) : { raw: await resp.text() };
    if (!resp.ok) {
        const err = new Error(data?.error || data?.message || `HTTP ${resp.status}`);
        err.status = resp.status;
        err.data = data;
        throw err;
    }
    return data;
}

/* ---------- conversations ---------- */

export const api = {
    listConversations: () => _json('/conversations'),
    deleteAllConversations: () => _json('/conversations', { method: 'DELETE' }),
    createConversation: () => _json('/conversations/new', { method: 'POST' }),
    switchConversation: (id) => _json(`/conversations/${encodeURIComponent(id)}/switch`, { method: 'POST' }),
    deleteConversation: (id) => _json(`/conversations/${encodeURIComponent(id)}`, { method: 'DELETE' }),
    getHistory: () => _json('/history'),
    clearHistory: () => _json('/clear', { method: 'POST' }),
    generateTitle: (firstMessage) => _json('/api/generate-title', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: firstMessage }),
    }),
};

/* ---------- streaming ---------- */

/**
 * Open an SSE stream against POST /chat/stream.
 *
 * @param {object}   payload   request body
 * @param {object}   options
 * @param {string}   options.streamId      client-generated id; sent in X-Stream-Id header
 * @param {AbortSignal} options.signal     abort controller signal
 * @param {function} options.onEvent       called with ({event, data}) for every SSE frame
 * @returns {Promise<void>}                resolves when stream ends; rejects on transport error
 */
export async function streamChat(payload, { streamId, signal, onEvent }) {
    const resp = await fetch('/chat/stream', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            'X-Stream-Id': streamId || '',
        },
        body: JSON.stringify(payload),
        signal,
    });
    if (_fetchHook) _fetchHook({ url: '/chat/stream', method: 'POST', status: resp.status, sse: true });
    if (!resp.ok) {
        let detail = '';
        try {
            const txt = await resp.text();
            try { detail = JSON.parse(txt).error || JSON.parse(txt).message || txt.slice(0, 500); }
            catch { detail = txt.slice(0, 500); }
        } catch {}
        const err = new Error(`HTTP ${resp.status}${detail ? ': ' + detail : ''}`);
        err.status = resp.status;
        throw err;
    }

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';
    let currentEvent = 'message';

    while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();
        for (const raw of lines) {
            const line = raw.replace(/\r$/, '');
            if (!line) { currentEvent = 'message'; continue; }
            if (line.startsWith('event: ')) {
                currentEvent = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
                const dataStr = line.slice(6);
                let data;
                try { data = JSON.parse(dataStr); }
                catch { console.warn('[sse] malformed frame:', dataStr.slice(0, 200)); continue; }
                try { onEvent({ event: currentEvent, data }); }
                catch (e) { console.error('[sse] onEvent threw', e); }
            }
        }
    }
}
