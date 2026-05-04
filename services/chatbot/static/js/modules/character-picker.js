/**
 * character-picker.js — Searchable character picker modal.
 *
 * Public API (exposed on window):
 *   window.openCharacterPicker(onSelect)
 *     onSelect(record): callback fired when user picks a character
 *     record shape:    { key, display_name, series, series_key, character_tag,
 *                        series_tag, aliases, thumbnail, solo_recommended }
 *
 * The picker fetches /api/characters and /api/characters/series and renders
 * a search box + series filter + grid of character cards.
 */
(function () {
  'use strict';

  const API_BASE = '/api/characters';
  const STATE = {
    open: false,
    series: '',
    query: '',
    cache: { chars: null, series: null, ts: 0 },
    onSelect: null,
  };

  const TTL_MS = 60_000;

  async function fetchJSON(url) {
    const res = await fetch(url, { credentials: 'same-origin' });
    if (!res.ok) throw new Error(`${url} -> ${res.status}`);
    return res.json();
  }

  async function loadSeries() {
    if (STATE.cache.series && (Date.now() - STATE.cache.ts) < TTL_MS) {
      return STATE.cache.series;
    }
    const data = await fetchJSON(`${API_BASE}/series`);
    STATE.cache.series = data.series || [];
    return STATE.cache.series;
  }

  async function loadCharacters(query, series) {
    const params = new URLSearchParams();
    if (query) params.set('q', query);
    if (series) params.set('series', series);
    params.set('limit', '120');
    const data = await fetchJSON(`${API_BASE}?${params.toString()}`);
    STATE.cache.ts = Date.now();
    return data.characters || [];
  }

  function escapeHTML(str) {
    return String(str || '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function buildModal() {
    let modal = document.getElementById('characterPickerModal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'characterPickerModal';
    modal.className = 'modal-overlay character-picker-modal';
    modal.style.display = 'none';
    modal.innerHTML = `
      <div class="modal-content character-picker-content" role="dialog" aria-modal="true" aria-label="Character picker">
        <div class="character-picker-header">
          <h3>Chọn nhân vật</h3>
          <button type="button" class="cp-close-btn" id="cpCloseBtn" aria-label="Close">×</button>
        </div>
        <div class="character-picker-controls">
          <input type="search" id="cpSearchInput" placeholder="Tìm theo tên, tag, alias…" autocomplete="off"/>
          <select id="cpSeriesFilter">
            <option value="">Tất cả series</option>
          </select>
          <button type="button" id="cpReloadBtn" class="cp-reload-btn" title="Reload registry">⟳</button>
        </div>
        <div class="character-picker-grid" id="cpGrid" aria-live="polite"></div>
        <div class="character-picker-footer">
          <span id="cpCount" class="cp-count">0 nhân vật</span>
          <button type="button" id="cpCancelBtn" class="cp-cancel-btn">Hủy</button>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    return modal;
  }

  function renderSeries(seriesList) {
    const sel = document.getElementById('cpSeriesFilter');
    if (!sel) return;
    const current = sel.value;
    sel.innerHTML = '<option value="">Tất cả series</option>' +
      seriesList.map(s => `<option value="${escapeHTML(s.key)}">${escapeHTML(s.name)}</option>`).join('');
    sel.value = current;
  }

  function renderGrid(chars) {
    const grid = document.getElementById('cpGrid');
    const count = document.getElementById('cpCount');
    if (!grid) return;
    if (count) count.textContent = `${chars.length} nhân vật`;
    if (chars.length === 0) {
      grid.innerHTML = '<div class="cp-empty">Không tìm thấy nhân vật phù hợp.</div>';
      return;
    }
    grid.innerHTML = chars.map(c => {
      const thumbUrl = `${API_BASE}/${encodeURIComponent(c.key)}/thumbnail`;
      const aliasText = (c.aliases && c.aliases.length)
        ? `<small class="cp-alias">${escapeHTML(c.aliases.slice(0, 3).join(', '))}</small>` : '';
      // SAA-augmented entries (5149-char WAI fallback) get a small badge
      // so users can tell them apart from the hand-curated local registry.
      const sourceBadge = (c.source === 'saa')
        ? `<span class="cp-source-badge" title="From SAA WAI database (5149 characters)">SAA</span>`
        : '';
      return `
        <button type="button" class="cp-card" data-key="${escapeHTML(c.key)}" title="${escapeHTML(c.display_name)} — ${escapeHTML(c.series)}">
          <div class="cp-thumb">
            <img loading="lazy" src="${thumbUrl}" alt="${escapeHTML(c.display_name)}"
                 onerror="this.style.display='none';this.parentNode.classList.add('cp-no-thumb');this.parentNode.textContent='${escapeHTML(c.display_name.charAt(0))}';"/>
            ${sourceBadge}
          </div>
          <div class="cp-meta">
            <strong>${escapeHTML(c.display_name)}</strong>
            <span class="cp-series">${escapeHTML(c.series)}</span>
            ${aliasText}
          </div>
        </button>
      `;
    }).join('');
    grid.querySelectorAll('.cp-card').forEach(btn => {
      btn.addEventListener('click', () => {
        const key = btn.getAttribute('data-key');
        const rec = chars.find(c => c.key === key);
        if (rec) selectCharacter(rec);
      });
    });
  }

  function selectCharacter(record) {
    closePicker();
    if (typeof STATE.onSelect === 'function') {
      try { STATE.onSelect(record); } catch (e) { console.error('[character-picker] onSelect error', e); }
    }
    document.dispatchEvent(new CustomEvent('character:selected', { detail: record }));
  }

  let _refreshTimer = null;
  async function refresh() {
    try {
      const chars = await loadCharacters(STATE.query, STATE.series);
      renderGrid(chars);
    } catch (e) {
      console.error('[character-picker] refresh failed', e);
      const grid = document.getElementById('cpGrid');
      if (grid) grid.innerHTML = `<div class="cp-error">Lỗi tải dữ liệu: ${escapeHTML(e.message)}</div>`;
    }
  }

  function debouncedRefresh() {
    if (_refreshTimer) clearTimeout(_refreshTimer);
    _refreshTimer = setTimeout(refresh, 200);
  }

  async function openPicker(onSelect) {
    STATE.onSelect = typeof onSelect === 'function' ? onSelect : null;
    const modal = buildModal();
    if (!STATE.cache.series) {
      try { await loadSeries(); } catch (e) { console.warn('[character-picker] series load failed', e); }
    }
    renderSeries(STATE.cache.series || []);
    modal.style.display = 'flex';
    STATE.open = true;
    const input = document.getElementById('cpSearchInput');
    if (input) { input.value = STATE.query; setTimeout(() => input.focus(), 50); }
    bindControls();
    refresh();
  }

  function closePicker() {
    const modal = document.getElementById('characterPickerModal');
    if (modal) modal.style.display = 'none';
    STATE.open = false;
  }

  function bindControls() {
    const closeBtn = document.getElementById('cpCloseBtn');
    const cancelBtn = document.getElementById('cpCancelBtn');
    const reloadBtn = document.getElementById('cpReloadBtn');
    const search = document.getElementById('cpSearchInput');
    const series = document.getElementById('cpSeriesFilter');
    if (closeBtn && !closeBtn._cpBound) { closeBtn.addEventListener('click', closePicker); closeBtn._cpBound = true; }
    if (cancelBtn && !cancelBtn._cpBound) { cancelBtn.addEventListener('click', closePicker); cancelBtn._cpBound = true; }
    if (reloadBtn && !reloadBtn._cpBound) {
      reloadBtn.addEventListener('click', async () => {
        try {
          await fetch(`${API_BASE}/reload`, { method: 'POST', credentials: 'same-origin' });
          STATE.cache.series = null;
          await loadSeries();
          renderSeries(STATE.cache.series || []);
          refresh();
        } catch (e) { console.error('[character-picker] reload failed', e); }
      });
      reloadBtn._cpBound = true;
    }
    if (search && !search._cpBound) {
      search.addEventListener('input', (ev) => { STATE.query = ev.target.value; debouncedRefresh(); });
      search._cpBound = true;
    }
    if (series && !series._cpBound) {
      series.addEventListener('change', (ev) => { STATE.series = ev.target.value; refresh(); });
      series._cpBound = true;
    }
    if (!document._cpEscBound) {
      document.addEventListener('keydown', (ev) => {
        if (ev.key === 'Escape' && STATE.open) closePicker();
      });
      document._cpEscBound = true;
    }
  }

  // Public API
  window.openCharacterPicker = openPicker;
  window.closeCharacterPicker = closePicker;
})();
