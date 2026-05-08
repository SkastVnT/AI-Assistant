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
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init, { once: true });
} else {
    init();
}

export { isDesktop };
