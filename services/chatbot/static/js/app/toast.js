/**
 * toast.js — minimal transient notifications.
 */

import { dom } from './dom.js';

const DEFAULT_TIMEOUT = 5000;

function _push(kind, msg, opts = {}) {
    const root = dom('toastRoot');
    if (!root) { console[kind === 'error' ? 'error' : 'log']('[toast]', msg); return; }
    const el = document.createElement('div');
    el.className = `toast toast--${kind}`;
    el.textContent = String(msg);
    el.title = 'Click to dismiss';
    const timeout = opts.timeout ?? DEFAULT_TIMEOUT;
    let timer = null;
    const close = () => {
        if (timer) { clearTimeout(timer); timer = null; }
        if (!el.isConnected) return;
        el.classList.add('is-leaving');
        el.addEventListener('animationend', () => el.remove(), { once: true });
    };
    el.addEventListener('click', close);
    if (timeout > 0) timer = setTimeout(close, timeout);
    root.appendChild(el);
    return close;
}

export const toast = {
    info:    (m, o) => _push('info', m, o),
    success: (m, o) => _push('success', m, o),
    warn:    (m, o) => _push('warn', m, o),
    error:   (m, o) => _push('error', m, o ?? { timeout: 8000 }),
};
