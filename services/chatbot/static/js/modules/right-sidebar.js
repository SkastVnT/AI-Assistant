/**
 * right-sidebar.js — Collapsible right status panel.
 *
 * Mirrors a read-only summary of:
 *   • Active character (from `character:state-changed`)
 *   • Active skill (from #activeSkillBadge — observed via MutationObserver)
 *   • Job queue stats (poll /api/jobs every 8s WHEN sidebar is open).
 *
 * Toggle: #rightSidebarToggleBtn (topbar) / #rightSidebarCloseBtn (header).
 * "Mở chi tiết hàng đợi" delegates to window.openJobQueuePanel().
 *
 * Polling is suspended when the sidebar is closed to avoid network noise.
 */
(function () {
    'use strict';

    const SIDEBAR_ID = 'rightSidebar';
    const TOGGLE_ID = 'rightSidebarToggleBtn';
    const CLOSE_ID = 'rightSidebarCloseBtn';
    const POLL_MS = 8000;

    let pollTimer = null;

    function escapeHTML(s) {
        return String(s == null ? '' : s)
            .replace(/&/g, '&amp;').replace(/</g, '&lt;')
            .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function setOpen(open) {
        const sidebar = document.getElementById(SIDEBAR_ID);
        if (!sidebar) return;
        sidebar.classList.toggle('collapsed', !open);
        document.body.classList.toggle('right-sidebar-open', open);
        if (open) startPolling(); else stopPolling();
    }

    function isOpen() {
        const sidebar = document.getElementById(SIDEBAR_ID);
        return !!(sidebar && !sidebar.classList.contains('collapsed'));
    }

    // ── Character mirror ──────────────────────────────────────────────

    function renderCharacter(character) {
        const body = document.getElementById('rightSidebarCharacterBody');
        if (!body) return;
        if (!character) {
            body.className = 'right-sidebar__character right-sidebar__placeholder';
            body.innerHTML = 'Chưa chọn nhân vật. Mở <em>Tools → Chọn nhân vật</em> để chọn.';
            return;
        }
        const name = character.display_name || character.canonical_id || 'character';
        const series = character.series_name || '';
        const thumb = character.preview_url
            || (character.key ? '/api/characters/' + encodeURIComponent(character.key) + '/thumbnail' : '');
        const flags = [];
        if (character.safe_to_attach_lora === false) flags.push('LoRA off');
        if (character.needs_review) flags.push('needs review');
        body.className = 'right-sidebar__character';
        body.innerHTML =
            (thumb
                ? '<img src="' + escapeHTML(thumb) + '" alt="" class="right-sidebar__thumb" loading="lazy" />'
                : '<div class="right-sidebar__thumb right-sidebar__thumb--placeholder">?</div>') +
            '<div class="right-sidebar__char-meta">' +
                '<div class="right-sidebar__char-name">' + escapeHTML(name) + '</div>' +
                (series ? '<div class="right-sidebar__char-series">' + escapeHTML(series) + '</div>' : '') +
                (flags.length
                    ? '<div class="right-sidebar__char-flags">' + flags.map(escapeHTML).join(' · ') + '</div>'
                    : '') +
            '</div>';
    }

    document.addEventListener('character:state-changed', (ev) => {
        renderCharacter(ev && ev.detail ? ev.detail.character : null);
    });

    // ── Skill mirror (observe the existing badge — single source of truth) ──

    function syncSkillFromBadge() {
        const badge = document.getElementById('activeSkillBadge');
        const out = document.getElementById('rightSidebarSkillBody');
        if (!badge || !out) return;
        const text = (badge.textContent || '').trim();
        if (!text) {
            out.className = 'right-sidebar__placeholder';
            out.textContent = 'Không có skill nào đang bật.';
            return;
        }
        out.className = '';
        out.innerHTML = '<div class="right-sidebar__skill-pill">'
            + escapeHTML(text.replace(/×$/, '').trim())
            + '</div>';
    }

    function watchSkillBadge() {
        const badge = document.getElementById('activeSkillBadge');
        if (!badge || typeof MutationObserver === 'undefined') return;
        const obs = new MutationObserver(syncSkillFromBadge);
        obs.observe(badge, { childList: true, subtree: true, characterData: true });
        syncSkillFromBadge();
    }

    // ── Jobs poll ─────────────────────────────────────────────────────

    async function pollJobs() {
        const out = document.getElementById('rightSidebarJobsSummary');
        if (!out) return;
        try {
            const res = await fetch('/api/jobs?limit=20', { credentials: 'same-origin' });
            if (!res.ok) throw new Error('HTTP ' + res.status);
            const data = await res.json();
            const stats = data.stats || {};
            const by = stats.by_state || {};
            const total = stats.total || 0;
            if (total === 0) {
                out.innerHTML = '<div class="right-sidebar__placeholder">Chưa có tác vụ nào.</div>';
                return;
            }
            out.innerHTML =
                '<div class="right-sidebar__jobs-grid">' +
                    cell('Tổng', total) +
                    cell('Chạy', by.running || 0, 'running') +
                    cell('Chờ', by.queued || 0, 'queued') +
                    cell('Xong', by.completed || 0, 'completed') +
                    cell('Lỗi', by.failed || 0, 'failed') +
                '</div>';
        } catch (err) {
            out.innerHTML = '<div class="right-sidebar__placeholder">Lỗi tải hàng đợi: '
                + escapeHTML(err.message || String(err)) + '</div>';
        }
    }

    function cell(label, value, kind) {
        const cls = kind ? ' right-sidebar__jobs-cell--' + kind : '';
        return '<div class="right-sidebar__jobs-cell' + cls + '">'
            + '<div class="right-sidebar__jobs-value">' + escapeHTML(String(value)) + '</div>'
            + '<div class="right-sidebar__jobs-label">' + escapeHTML(label) + '</div>'
            + '</div>';
    }

    function startPolling() {
        if (pollTimer) return;
        pollJobs();
        pollTimer = setInterval(pollJobs, POLL_MS);
    }

    function stopPolling() {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    }

    // ── Wire up ───────────────────────────────────────────────────────

    function init() {
        const toggle = document.getElementById(TOGGLE_ID);
        if (toggle) toggle.addEventListener('click', () => setOpen(!isOpen()));
        const closeBtn = document.getElementById(CLOSE_ID);
        if (closeBtn) closeBtn.addEventListener('click', () => setOpen(false));
        const openJobs = document.getElementById('rightSidebarOpenJobs');
        if (openJobs) {
            openJobs.addEventListener('click', () => {
                if (typeof window.openJobQueuePanel === 'function') {
                    window.openJobQueuePanel();
                }
            });
        }
        watchSkillBadge();
        renderCharacter(window.selectedCharacter || null);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Expose for debugging / external triggers.
    window.openRightSidebar = () => setOpen(true);
    window.closeRightSidebar = () => setOpen(false);
})();
