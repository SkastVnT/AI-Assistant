/**
 * state.js — finite state machine for the UI shell.
 *
 * Statuses: idle | composing | uploading | streaming | stopping | error
 *
 * Anyone who needs to react to status changes listens to the
 * `appstatechange` CustomEvent on `document`.
 */

const STATUSES = new Set(['idle', 'composing', 'uploading', 'streaming', 'stopping', 'error']);

export const appState = {
    status: 'idle',
    currentConversationId: null,
    currentStreamId: null,
    activeTools: new Set(),
    stagedFiles: [], // File objects
    theme: 'dark',
    messages: [],    // structured JSON messages of the active conversation
    conversations: [], // conversation index for sidebar
    backendOk: true,
};

let _listeners = [];

export function setStatus(next) {
    if (!STATUSES.has(next)) {
        console.warn('[state] invalid status:', next);
        return;
    }
    if (appState.status === next) return;
    const prev = appState.status;
    appState.status = next;
    document.body.dataset.state = next;
    _emit({ type: 'status', prev, next });
}

export function patch(changes) {
    Object.assign(appState, changes);
    _emit({ type: 'patch', changes });
}

export function subscribe(fn) {
    _listeners.push(fn);
    return () => { _listeners = _listeners.filter((f) => f !== fn); };
}

function _emit(detail) {
    document.dispatchEvent(new CustomEvent('appstatechange', { detail }));
    for (const fn of _listeners) {
        try { fn(detail, appState); } catch (e) { console.error('[state] listener error', e); }
    }
}

export function isBusy() {
    return appState.status === 'streaming' || appState.status === 'stopping' || appState.status === 'uploading';
}

export function newStreamId() {
    // crypto.randomUUID is available in modern browsers; fallback for old.
    if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
    return 's_' + Math.random().toString(36).slice(2) + Date.now().toString(36);
}
