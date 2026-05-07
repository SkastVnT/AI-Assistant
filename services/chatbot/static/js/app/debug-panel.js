/**
 * debug-panel.js — captures errors, fetch issues, live state. Toggle Ctrl+Shift+D.
 *
 * Registered FIRST in boot so it can catch boot-time errors.
 */

import { dom } from './dom.js';
import { appState } from './state.js';
import { setFetchHook } from './api.js';
import { toast } from './toast.js';

const MAX_ENTRIES = 200;
const entries = [];
let panelEl = null;
let logEl = null;
let stateEl = null;
let visible = false;

function _ts() {
    const d = new Date();
    return d.toISOString().slice(11, 23);
}

function _addEntry(level, msg, extra) {
    const entry = { t: _ts(), level, msg: String(msg), extra };
    entries.push(entry);
    if (entries.length > MAX_ENTRIES) entries.shift();
    if (logEl) {
        const div = document.createElement('div');
        div.className = `debug__entry debug__entry--${level}`;
        div.textContent = `[${entry.t}] ${level.toUpperCase()} ${entry.msg}` + (extra ? ' ' + JSON.stringify(extra) : '');
        logEl.appendChild(div);
        while (logEl.children.length > MAX_ENTRIES) logEl.firstChild.remove();
        logEl.scrollTop = logEl.scrollHeight;
    }
}

function _renderState() {
    if (!stateEl) return;
    const s = {
        status: appState.status,
        currentConversationId: appState.currentConversationId,
        currentStreamId: appState.currentStreamId,
        activeTools: Array.from(appState.activeTools),
        stagedFiles: appState.stagedFiles.length,
        backendOk: appState.backendOk,
        theme: appState.theme,
        messages: appState.messages.length,
        conversations: appState.conversations.length,
    };
    stateEl.innerHTML = '';
    for (const [k, v] of Object.entries(s)) {
        const row = document.createElement('div');
        row.className = 'debug__state-row';
        row.innerHTML = `<span class="debug__state-key"></span><span class="debug__state-val"></span>`;
        row.querySelector('.debug__state-key').textContent = k;
        row.querySelector('.debug__state-val').textContent = JSON.stringify(v);
        stateEl.appendChild(row);
    }
}

function _toggle(force) {
    visible = typeof force === 'boolean' ? force : !visible;
    if (panelEl) panelEl.classList.toggle('is-open', visible);
}

export function initDebugPanel() {
    panelEl = dom('debugPanel');
    if (!panelEl) return;
    panelEl.innerHTML = `
        <div class="debug__header">
            <span class="debug__title">Debug</span>
            <button class="debug__close" type="button" aria-label="Close">×</button>
        </div>
        <div class="debug__state"></div>
        <div class="debug__log"></div>
    `;
    stateEl = panelEl.querySelector('.debug__state');
    logEl = panelEl.querySelector('.debug__log');
    panelEl.querySelector('.debug__close').addEventListener('click', () => _toggle(false));

    const btn = dom('debugToggleBtn');
    if (btn) btn.addEventListener('click', () => _toggle());

    document.addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.shiftKey && (e.key === 'D' || e.key === 'd')) {
            e.preventDefault();
            _toggle();
        }
    });

    window.addEventListener('error', (e) => {
        _addEntry('error', e.message || 'window.error', { src: e.filename, line: e.lineno });
        toast.error(e.message || 'Script error');
    });
    window.addEventListener('unhandledrejection', (e) => {
        const m = e.reason?.message || String(e.reason);
        _addEntry('error', 'unhandledrejection: ' + m);
        toast.error(m);
    });

    setFetchHook((info) => {
        const status = info.status ?? 0;
        const lvl = info.error ? 'error' : (status >= 400 ? 'warn' : 'info');
        _addEntry(lvl, `${info.method} ${info.url} → ${info.error ? 'ERR' : status} (${Math.round(info.ms || 0)}ms)`);
    });

    document.addEventListener('appstatechange', _renderState);
    _renderState();
    _addEntry('info', 'debug panel ready');
}
