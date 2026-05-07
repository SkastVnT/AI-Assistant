/**
 * tools-controller.js — minimal tool toggles.
 *
 * Locked: only "web-search" and "deep-research".
 * UI value "web-search" maps to backend tool name "google-search".
 */

import { dom } from './dom.js';
import { appState } from './state.js';

const TOOLS = [
    { id: 'web-search', label: 'Web search', backend: 'google-search' },
    { id: 'deep-research', label: 'Deep research', backend: 'deep-research' },
];

function _backendName(id) {
    const t = TOOLS.find((x) => x.id === id);
    return t ? t.backend : id;
}

export function initTools() {
    const bar = dom('toolsBar');
    if (!bar) return;
    bar.innerHTML = '';
    for (const t of TOOLS) {
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'tool-toggle';
        btn.dataset.tool = t.id;
        btn.textContent = t.label;
        btn.setAttribute('aria-pressed', 'false');
        btn.addEventListener('click', () => {
            const backend = _backendName(t.id);
            const isActive = appState.activeTools.has(backend);
            if (isActive) appState.activeTools.delete(backend);
            else appState.activeTools.add(backend);
            btn.classList.toggle('is-active', !isActive);
            btn.setAttribute('aria-pressed', String(!isActive));
        });
        bar.appendChild(btn);
    }
}
