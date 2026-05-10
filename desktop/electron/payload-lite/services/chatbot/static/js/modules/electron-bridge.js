/* electron-bridge.js — frontend ↔ Electron desktopAPI integration.
 *
 * Responsibilities:
 *   1. Detect Electron (window.desktopAPI) and tag <body> with `is-desktop`.
 *   2. Wire the custom titlebar buttons (minimize/maximize/close).
 *   3. Sync max/unmax state → swap the maximize icon.
 *   4. Mirror the local job-queue running count to the system tray badge.
 *   5. Optionally show a native notification when an image-gen job completes.
 *
 * Pure browser fallback: when window.desktopAPI is missing, this module
 * tags <body class="is-browser"> and does nothing else.
 */

const isDesktop = !!(window.desktopAPI && window.desktopAPI.isDesktop);

function tagBody() {
    if (!document.body) return;
    document.body.classList.toggle('is-desktop', isDesktop);
    document.body.classList.toggle('is-browser', !isDesktop);
}

function wireTitlebar() {
    if (!isDesktop) return;
    const min  = document.getElementById('titlebarMinBtn');
    const max  = document.getElementById('titlebarMaxBtn');
    const close = document.getElementById('titlebarCloseBtn');
    if (min)  min.addEventListener('click',  () => window.desktopAPI.window.minimize());
    if (max)  max.addEventListener('click',  () => window.desktopAPI.window.maximize());
    if (close) close.addEventListener('click', () => window.desktopAPI.window.close());

    // Swap the max/restore icon when state changes.
    const setIcon = (isMax) => {
        if (!max) return;
        const icon = max.querySelector('[data-lucide]');
        if (icon) {
            icon.setAttribute('data-lucide', isMax ? 'minimize-2' : 'square');
            try { window.lucide && window.lucide.createIcons({ icons: window.lucide.icons }); } catch (_) {}
        }
        max.title = isMax ? 'Restore' : 'Maximize';
    };
    window.desktopAPI.window.isMaximized().then(setIcon).catch(() => {});
    window.desktopAPI.window.onMaximizedChanged(setIcon);
}

// ── Job-queue badge bridge ────────────────────────────────────────
let _badgeTimer = null;
function startJobBadgePoller() {
    if (!isDesktop) return;
    const tick = async () => {
        try {
            const res = await fetch('/api/jobs/stats', { cache: 'no-store' });
            if (!res.ok) return;
            const data = await res.json();
            const by = (data && data.by_state) || {};
            const active = (by.running || 0) + (by.queued || 0);
            window.desktopAPI.tray.setBadge(active).catch(() => {});
        } catch (_) { /* offline / route absent */ }
    };
    tick();
    if (_badgeTimer) clearInterval(_badgeTimer);
    _badgeTimer = setInterval(tick, 5000);
}

// Optional helper: any module can call window.desktopNotify({title, body}).
function exposeNotifyHelper() {
    window.desktopNotify = (payload) => {
        if (!isDesktop) return Promise.resolve(false);
        return window.desktopAPI.notify.show(payload || {});
    };
}

function init() {
    tagBody();
    wireTitlebar();
    exposeNotifyHelper();
    startJobBadgePoller();
    wireKeyboardShortcuts();
    // Force a final lucide pass so titlebar SVGs render even if main.js init
    // ran before the titlebar was visible.
    setTimeout(() => {
        try { window.lucide && window.lucide.createIcons(); } catch (_) {}
    }, 50);
}

// ── Application keyboard shortcuts (in-window, all modes) ─────────
function wireKeyboardShortcuts() {
    const click = (id) => {
        const el = document.getElementById(id);
        if (el) { el.click(); return true; }
        return false;
    };
    const togglePanel = (panelKey) => {
        // overlay-manager exposes window.overlayManager.toggle for floating panels
        if (window.overlayManager && typeof window.overlayManager.toggle === 'function') {
            try { window.overlayManager.toggle(panelKey); return true; } catch (_) {}
        }
        return false;
    };

    document.addEventListener('keydown', (e) => {
        // Skip if user is typing in an input/textarea, *unless* it's a global
        // (Ctrl/Cmd combined) shortcut that should always work.
        const tag = (e.target?.tagName || '').toLowerCase();
        const inEditable = (tag === 'input' || tag === 'textarea' || e.target?.isContentEditable);
        const ctrl = e.ctrlKey || e.metaKey;

        // Ctrl+Shift+N — New chat
        if (ctrl && e.shiftKey && e.key.toLowerCase() === 'n') {
            e.preventDefault(); click('newChatBtn'); return;
        }
        // Ctrl+K — Quick search (focus chat list filter or composer if absent)
        if (ctrl && !e.shiftKey && e.key.toLowerCase() === 'k') {
            e.preventDefault();
            const filter = document.getElementById('chatListFilter');
            if (filter) { filter.focus(); filter.select?.(); }
            else { document.getElementById('messageInput')?.focus(); }
            return;
        }
        // Ctrl+/ — Focus composer
        if (ctrl && !e.shiftKey && e.key === '/') {
            e.preventDefault();
            document.getElementById('messageInput')?.focus();
            return;
        }
        // Ctrl+B — Toggle sidebar
        if (ctrl && !e.shiftKey && e.key.toLowerCase() === 'b') {
            e.preventDefault();
            const btn = document.getElementById('sidebarToggleBtn');
            if (btn) btn.click();
            return;
        }
        // Ctrl+Shift+I — Toggle Image-Gen panel
        if (ctrl && e.shiftKey && e.key.toLowerCase() === 'i') {
            e.preventDefault();
            if (!togglePanel('imageGenV2')) click('imageGenBtn') || click('imageGenV2Btn');
            return;
        }
        // Ctrl+Shift+J — Toggle Job Queue panel
        if (ctrl && e.shiftKey && e.key.toLowerCase() === 'j') {
            e.preventDefault();
            if (typeof window.openJobQueuePanel === 'function') window.openJobQueuePanel();
            else if (!togglePanel('jobQueue')) click('jobQueueBtn');
            return;
        }
    }, true);
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
    init();
}

export { isDesktop };
