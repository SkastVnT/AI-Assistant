/**
 * job-queue-panel.js — Local image job queue panel.
 *
 * Polls /api/jobs every POLL_INTERVAL_MS and renders a compact list with
 * state chip, progress, character, preset, and cancel/manifest actions.
 *
 * Public API:
 *   window.openJobQueuePanel()
 *   window.closeJobQueuePanel()
 *   window.refreshJobQueue()
 */
(function () {
  'use strict';

  const API_BASE = '/api/jobs';
  const POLL_INTERVAL_MS = 3500;

  const STATE = { open: false, pollHandle: null, lastCount: 0 };

  async function fetchJobs() {
    const res = await fetch(`${API_BASE}?limit=50`, { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`${API_BASE} -> ${res.status}`);
    return res.json();
  }

  function escapeHTML(str) {
    return String(str || '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function stateChip(state) {
    const map = {
      queued: { c: 'jq-chip jq-queued', t: 'queued' },
      running: { c: 'jq-chip jq-running', t: 'running' },
      completed: { c: 'jq-chip jq-completed', t: 'done' },
      failed: { c: 'jq-chip jq-failed', t: 'failed' },
      cancelled: { c: 'jq-chip jq-cancelled', t: 'cancelled' },
    };
    const m = map[state] || { c: 'jq-chip', t: state };
    return `<span class="${m.c}">${escapeHTML(m.t)}</span>`;
  }

  function formatTs(ts) {
    if (!ts) return '';
    try { return new Date(ts * 1000).toLocaleTimeString(); } catch { return ''; }
  }

  function buildPanel() {
    let panel = document.getElementById('jobQueuePanel');
    if (panel) return panel;
    panel = document.createElement('div');
    panel.id = 'jobQueuePanel';
    panel.className = 'job-queue-panel';
    panel.style.display = 'none';
    panel.innerHTML = `
      <div class="jq-header">
        <h3>Hàng đợi tác vụ ảnh</h3>
        <div class="jq-header-actions">
          <button type="button" id="jqRefreshBtn" class="jq-icon-btn" title="Refresh">⟳</button>
          <button type="button" id="jqCloseBtn" class="jq-icon-btn" aria-label="Close">×</button>
        </div>
      </div>
      <div class="jq-stats" id="jqStats"></div>
      <div class="jq-list" id="jqList" aria-live="polite"></div>
    `;
    document.body.appendChild(panel);
    return panel;
  }

  function renderStats(stats) {
    const node = document.getElementById('jqStats');
    if (!node) return;
    const by = stats.by_state || {};
    node.innerHTML = `
      <span>Tổng: <strong>${stats.total ?? 0}</strong></span>
      <span>Chạy: <strong>${by.running ?? 0}</strong></span>
      <span>Chờ: <strong>${by.queued ?? 0}</strong></span>
      <span>Xong: <strong>${by.completed ?? 0}</strong></span>
      <span>Lỗi: <strong>${by.failed ?? 0}</strong></span>
    `;
  }

  function renderJobs(jobs) {
    const list = document.getElementById('jqList');
    if (!list) return;
    if (!jobs || jobs.length === 0) {
      list.innerHTML = '<div class="jq-empty">Chưa có job nào.</div>';
      return;
    }
    list.innerHTML = jobs.map(j => {
      const pct = Math.max(0, Math.min(100, Number(j.progress_pct || 0)));
      const stage = j.progress_stage ? ` · ${escapeHTML(j.progress_stage)}` : '';
      const charLine = j.character_display
        ? `<div class="jq-char">👤 ${escapeHTML(j.character_display)}${j.series_key ? ` · ${escapeHTML(j.series_key)}` : ''}</div>`
        : '';
      const presetLine = j.preset ? `<div class="jq-preset">⚙ ${escapeHTML(j.preset)}</div>` : '';
      const errLine = j.error ? `<div class="jq-error" title="${escapeHTML(j.error)}">${escapeHTML(j.error.slice(0, 80))}</div>` : '';
      const canCancel = j.state === 'queued' || j.state === 'running';
      const cancelBtn = canCancel ? `<button type="button" class="jq-action" data-act="cancel" data-id="${escapeHTML(j.job_id)}">Hủy</button>` : '';
      const manifestBtn = `<button type="button" class="jq-action" data-act="manifest" data-id="${escapeHTML(j.job_id)}">Manifest</button>`;
      return `
        <div class="jq-item">
          <div class="jq-row1">
            ${stateChip(j.state)}
            <code class="jq-id">${escapeHTML(j.job_id.slice(0, 12))}</code>
            <span class="jq-ts">${escapeHTML(formatTs(j.created_at))}</span>
          </div>
          ${charLine}${presetLine}
          <div class="jq-prompt">${escapeHTML((j.prompt || '').slice(0, 140))}</div>
          <div class="jq-progress" title="${pct.toFixed(0)}%${stage}">
            <div class="jq-progress-bar" style="width:${pct.toFixed(1)}%"></div>
          </div>
          ${errLine}
          <div class="jq-actions">
            ${cancelBtn}
            ${manifestBtn}
          </div>
        </div>
      `;
    }).join('');

    list.querySelectorAll('.jq-action').forEach(btn => {
      btn.addEventListener('click', async () => {
        const act = btn.getAttribute('data-act');
        const id = btn.getAttribute('data-id');
        if (!id) return;
        if (act === 'cancel') {
          try {
            await fetch(`${API_BASE}/${encodeURIComponent(id)}/cancel`, {
              method: 'POST', credentials: 'same-origin',
            });
            await refresh();
          } catch (e) { console.error('[job-queue] cancel failed', e); }
        } else if (act === 'manifest') {
          window.open(`${API_BASE}/${encodeURIComponent(id)}/manifest`, '_blank');
        }
      });
    });
  }

  async function refresh() {
    try {
      const data = await fetchJobs();
      renderStats(data.stats || {});
      renderJobs(data.jobs || []);
      STATE.lastCount = (data.jobs || []).length;
    } catch (e) {
      console.error('[job-queue] refresh failed', e);
      const list = document.getElementById('jqList');
      if (list) list.innerHTML = `<div class="jq-error-block">Lỗi tải hàng đợi: ${escapeHTML(e.message)}</div>`;
    }
  }

  function startPoll() {
    stopPoll();
    STATE.pollHandle = setInterval(refresh, POLL_INTERVAL_MS);
  }
  function stopPoll() {
    if (STATE.pollHandle) { clearInterval(STATE.pollHandle); STATE.pollHandle = null; }
  }

  function bindControls() {
    const close = document.getElementById('jqCloseBtn');
    const reload = document.getElementById('jqRefreshBtn');
    if (close && !close._jqBound) { close.addEventListener('click', closePanel); close._jqBound = true; }
    if (reload && !reload._jqBound) { reload.addEventListener('click', refresh); reload._jqBound = true; }
  }

  function openPanel() {
    const panel = buildPanel();
    panel.style.display = 'flex';
    STATE.open = true;
    bindControls();
    refresh();
    startPoll();
  }
  function closePanel() {
    const panel = document.getElementById('jobQueuePanel');
    if (panel) panel.style.display = 'none';
    STATE.open = false;
    stopPoll();
  }

  window.openJobQueuePanel = openPanel;
  window.closeJobQueuePanel = closePanel;
  window.refreshJobQueue = refresh;
})();
