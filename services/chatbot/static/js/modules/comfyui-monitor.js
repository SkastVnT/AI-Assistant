/**
 * comfyui-monitor.js — floating terminal panel for ComfyUI logs.
 * Only activates when running inside the Electron desktop app
 * (window.desktopAPI.isDesktop + window.desktopAPI.comfyui).
 */
(function () {
    'use strict';

    const api = window.desktopAPI;
    if (!api || !api.isDesktop || !api.comfyui) return;

    // ── State ──────────────────────────────────────────────────────
    const STRIP_ANSI = /\x1b\[[0-9;]*[mGKHFJA-Z]/g;
    const MAX_LINES = 600;

    let panel = null;
    let logEl = null;
    let statusDot = null;
    let statusLabel = null;
    let autoScroll = true;
    let historyFetched = false;
    let lines = [];

    // ── Helpers ────────────────────────────────────────────────────
    function stripAnsi(t) { return t.replace(STRIP_ANSI, ''); }

    function escHtml(t) {
        return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    function appendLines(stream, text) {
        const raw = stripAnsi(text);
        raw.split('\n').forEach(line => {
            if (!line) return;
            lines.push({ s: stream, t: line });
        });
        while (lines.length > MAX_LINES) lines.shift();
    }

    function renderLog() {
        if (!logEl) return;
        logEl.innerHTML = lines.map(({ s, t }) =>
            `<div class="cui-line${s === 'err' ? ' cui-line--err' : ''}">${escHtml(t)}</div>`
        ).join('');
        if (autoScroll) logEl.scrollTop = logEl.scrollHeight;
    }

    function updateStatus(status) {
        if (!statusDot || !statusLabel) return;
        const MAP = {
            running:  { color: '#4ade80', text: 'running' },
            starting: { color: '#fbbf24', text: 'starting…' },
            failed:   { color: '#f87171', text: 'failed' },
            stopped:  { color: '#6b7280', text: 'stopped' },
        };
        const s = MAP[status] || MAP.stopped;
        statusDot.style.background = s.color;
        statusLabel.textContent = s.text;
    }

    // ── CSS injection ───────────────────────────────────────────────
    function injectStyles() {
        if (document.getElementById('cui-monitor-style')) return;
        const el = document.createElement('style');
        el.id = 'cui-monitor-style';
        el.textContent = `
#cuiMonitorPanel {
    position: fixed;
    bottom: 16px;
    right: 16px;
    width: 460px;
    height: 300px;
    min-height: 120px;
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: 8px;
    display: flex;
    flex-direction: column;
    z-index: 9000;
    box-shadow: 0 8px 32px rgba(0,0,0,0.65);
    font-family: 'Consolas','Menlo','Courier New',monospace;
    font-size: 12px;
    resize: vertical;
    overflow: hidden;
}
#cuiMonitorPanel .cui-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 6px 10px;
    background: #161b22;
    border-bottom: 1px solid #30363d;
    border-radius: 8px 8px 0 0;
    flex-shrink: 0;
    user-select: none;
    cursor: move;
}
#cuiMonitorPanel .cui-dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #6b7280;
    flex-shrink: 0;
    transition: background 0.3s;
}
#cuiMonitorPanel .cui-title { color: #e6edf3; font-weight: 600; font-size: 12px; flex: 1; }
#cuiMonitorPanel .cui-status { color: #8b949e; font-size: 11px; }
#cuiMonitorPanel .cui-btn-icon {
    background: none; border: none; color: #8b949e;
    cursor: pointer; padding: 2px 5px; border-radius: 4px;
    line-height: 1; font-size: 14px;
}
#cuiMonitorPanel .cui-btn-icon:hover { color: #e6edf3; background: #21262d; }
#cuiMonitorPanel .cui-log {
    flex: 1;
    overflow-y: auto;
    overflow-x: hidden;
    padding: 8px 10px;
    color: #c9d1d9;
    line-height: 1.5;
}
#cuiMonitorPanel .cui-log::-webkit-scrollbar { width: 6px; }
#cuiMonitorPanel .cui-log::-webkit-scrollbar-track { background: transparent; }
#cuiMonitorPanel .cui-log::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
#cuiMonitorPanel .cui-line { white-space: pre-wrap; word-break: break-all; }
#cuiMonitorPanel .cui-line--err { color: #ffa198; }
#cuiMonitorPanel .cui-footer {
    padding: 4px 10px;
    border-top: 1px solid #30363d;
    display: flex;
    align-items: center;
    gap: 8px;
    flex-shrink: 0;
}
#cuiMonitorPanel .cui-autoscroll-label {
    display: flex; align-items: center; gap: 4px;
    color: #8b949e; font-size: 11px; cursor: pointer;
}
#cuiMonitorPanel .cui-btn-text {
    margin-left: auto; background: none;
    border: 1px solid #30363d; color: #8b949e;
    cursor: pointer; padding: 2px 8px; border-radius: 4px; font-size: 11px;
}
#cuiMonitorPanel .cui-btn-text:hover { color: #e6edf3; border-color: #6e7681; }
        `;
        document.head.appendChild(el);
    }

    // ── Panel DOM ──────────────────────────────────────────────────
    function buildPanel() {
        injectStyles();
        const p = document.createElement('div');
        p.id = 'cuiMonitorPanel';
        p.innerHTML = `
            <div class="cui-header" id="cuiDragHandle">
                <span class="cui-dot" id="cuiStatusDot"></span>
                <span class="cui-title">ComfyUI Terminal</span>
                <span class="cui-status" id="cuiStatusLabel">…</span>
                <button class="cui-btn-icon" id="cuiOpenBrowserBtn" title="Open ComfyUI in browser">↗</button>
                <button class="cui-btn-icon" id="cuiCloseBtn" title="Close">✕</button>
            </div>
            <div class="cui-log" id="cuiLog"></div>
            <div class="cui-footer">
                <label class="cui-autoscroll-label">
                    <input type="checkbox" id="cuiAutoScrollCb" checked> Auto-scroll
                </label>
                <button class="cui-btn-text" id="cuiClearBtn">Clear</button>
            </div>
        `;
        document.body.appendChild(p);

        logEl      = p.querySelector('#cuiLog');
        statusDot  = p.querySelector('#cuiStatusDot');
        statusLabel= p.querySelector('#cuiStatusLabel');

        // Close
        p.querySelector('#cuiCloseBtn').addEventListener('click', closePanel);

        // Open ComfyUI in browser
        p.querySelector('#cuiOpenBrowserBtn').addEventListener('click', () => {
            const url = 'http://127.0.0.1:' + (window.__COMFYUI_PORT || '8188');
            window.open(url, '_blank');
        });

        // Auto-scroll checkbox
        p.querySelector('#cuiAutoScrollCb').addEventListener('change', (e) => {
            autoScroll = e.target.checked;
            if (autoScroll && logEl) logEl.scrollTop = logEl.scrollHeight;
        });

        // Scroll → disable auto-scroll when user scrolls up
        logEl.addEventListener('scroll', () => {
            const atBottom = logEl.scrollHeight - logEl.scrollTop - logEl.clientHeight < 30;
            autoScroll = atBottom;
            const cb = p.querySelector('#cuiAutoScrollCb');
            if (cb) cb.checked = autoScroll;
        });

        // Clear
        p.querySelector('#cuiClearBtn').addEventListener('click', () => {
            lines = [];
            logEl.innerHTML = '';
        });

        // Drag to reposition
        setupDrag(p.querySelector('#cuiDragHandle'), p);

        return p;
    }

    // ── Drag ───────────────────────────────────────────────────────
    function setupDrag(handle, target) {
        let ox = 0, oy = 0;
        handle.addEventListener('mousedown', (e) => {
            if (e.target.closest('button')) return;
            ox = e.clientX - target.getBoundingClientRect().left;
            oy = e.clientY - target.getBoundingClientRect().top;
            const onMove = (ev) => {
                target.style.right   = 'auto';
                target.style.bottom  = 'auto';
                target.style.left    = (ev.clientX - ox) + 'px';
                target.style.top     = (ev.clientY - oy) + 'px';
            };
            const onUp = () => {
                document.removeEventListener('mousemove', onMove);
                document.removeEventListener('mouseup', onUp);
            };
            document.addEventListener('mousemove', onMove);
            document.addEventListener('mouseup', onUp);
            e.preventDefault();
        });
    }

    // ── Open / close ───────────────────────────────────────────────
    function openPanel() {
        if (!panel) panel = buildPanel();
        panel.style.display = 'flex';

        // Fetch history once
        if (!historyFetched) {
            historyFetched = true;
            api.comfyui.getHistory().then(history => {
                if (!history) return;
                // Replace lines with history (live subscription already buffered ongoing logs)
                const oldLines = lines.slice();
                lines = [];
                history.split('\n').forEach(line => {
                    const m = line.match(/^\[(out|err)\] (.*)$/);
                    if (m) appendLines(m[1], m[2]);
                });
                // Re-append any live lines that may not yet be in history
                oldLines.forEach(l => lines.push(l));
                while (lines.length > MAX_LINES) lines.shift();
                renderLog();
            }).catch(() => {});
        } else {
            renderLog();
        }

        api.comfyui.getStatus().then(updateStatus).catch(() => {});
    }

    function closePanel() {
        if (panel) panel.style.display = 'none';
    }

    function togglePanel() {
        if (!panel || panel.style.display === 'none' || panel.style.display === '') {
            openPanel();
        } else {
            closePanel();
        }
    }

    // ── Live subscription (always-on so logs buffer while panel is closed) ──
    api.comfyui.onLog((data) => {
        appendLines(data.stream, data.text);
        if (panel && panel.style.display === 'flex' && logEl) renderLog();
    });

    // ── Periodic status refresh ────────────────────────────────────
    setInterval(() => {
        if (!panel || panel.style.display !== 'flex') return;
        api.comfyui.getStatus().then(updateStatus).catch(() => {});
    }, 3000);

    // ── Expose button ──────────────────────────────────────────────
    const btn = document.getElementById('comfyuiMonitorBtn');
    if (btn) {
        btn.style.display = '';   // un-hide
        btn.addEventListener('click', togglePanel);
        // Re-init lucide icon since it was hidden on first pass
        if (window.lucide) lucide.createIcons({ nodes: [btn] });
    }
})();
