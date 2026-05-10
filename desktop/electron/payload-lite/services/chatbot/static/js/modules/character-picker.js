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
    // Hidden by default; openPicker() switches to .open class.
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
      const aliasText = (c.aliases && c.aliases.length)
        ? `<small class="cp-alias">${escapeHTML(c.aliases.slice(0, 3).join(', '))}</small>` : '';
      // SAA-augmented entries (5149-char WAI fallback) get a small badge
      // so users can tell them apart from the hand-curated local registry.
      const sourceBadge = (c.source === 'saa')
        ? `<span class="cp-source-badge" title="From SAA WAI database (5149 characters)">SAA</span>`
        : '';
      // Skip the <img> entirely when the backend told us no thumbnail is
      // resolvable — avoids a guaranteed 404 + log noise. Render the letter
      // avatar directly. ``has_thumbnail`` may be undefined on legacy
      // responses; in that case fall back to the original onerror flow.
      const letter = escapeHTML(c.display_name.charAt(0));
      const thumbInner = (c.has_thumbnail === false)
        ? `<span class="cp-letter">${letter}</span>`
        : `<img loading="lazy" src="${API_BASE}/${encodeURIComponent(c.key)}/thumbnail" alt="${escapeHTML(c.display_name)}"
                 onerror="this.style.display='none';this.parentNode.classList.add('cp-no-thumb');this.parentNode.textContent='${letter}';"/>`;
      return `
        <button type="button" class="cp-card" data-key="${escapeHTML(c.key)}" title="${escapeHTML(c.display_name)} — ${escapeHTML(c.series)}">
          <div class="cp-thumb${c.has_thumbnail === false ? ' cp-no-thumb' : ''}">
            ${thumbInner}
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
    modal.style.display = '';
    modal.classList.add('open');
    STATE.open = true;
    const input = document.getElementById('cpSearchInput');
    if (input) { input.value = STATE.query; setTimeout(() => input.focus(), 50); }
    bindControls();
    refresh();
  }

  function closePicker() {
    const modal = document.getElementById('characterPickerModal');
    if (modal) {
      modal.classList.remove('open');
      modal.style.display = 'none';
    }
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

  // ── Inline-card mode (preferred) ──────────────────────────────────────
  // Renders the picker as a chat message bubble using the same
  // `igv2-provider-choice` aesthetic so it lives *inside* the conversation
  // instead of as a centred modal. One inline picker at a time; opening a
  // second one removes the previous.

  const INLINE_ID = 'characterPickerInline';

  function buildInlineCard() {
    const existing = document.getElementById(INLINE_ID);
    if (existing && existing.parentNode) existing.parentNode.removeChild(existing);
    const wrap = document.createElement('div');
    wrap.id = INLINE_ID;
    wrap.className = 'message assistant';
    wrap.innerHTML = `
      <div class="message__avatar message__avatar--agent"><img src="/static/icons/app-icon.png" class="avatar-img" alt="" width="36" height="36" draggable="false"></div>
      <div class="message__body">
        <div class="message-content">
          <div class="igv2-provider-choice character-picker-inline">
            <div class="igv2-choice-header">
              <span class="igv2-choice-icon">🎭</span>
              <span class="igv2-choice-title">Chọn nhân vật</span>
              <button type="button" class="cp-inline-close" aria-label="Close" style="margin-left:auto;background:transparent;border:0;font-size:18px;cursor:pointer;color:var(--text);">×</button>
            </div>
            <div class="igv2-choice-options">
              <div class="igv2-choice-option-group igv2-choice-option-full" style="display:flex;gap:8px;flex-wrap:wrap;align-items:center;">
                <input type="search" id="cpInlineSearch" placeholder="Tìm tên / tag / alias…" autocomplete="off" style="flex:1 1 200px;min-width:160px;padding:6px 10px;border-radius:6px;border:1px solid var(--border,#ddd);background:var(--bg,#fff);color:var(--text);"/>
                <select id="cpInlineSeries" style="padding:6px 10px;border-radius:6px;border:1px solid var(--border,#ddd);background:var(--bg,#fff);color:var(--text);">
                  <option value="">Tất cả series</option>
                </select>
                <button type="button" id="cpInlineReload" title="Reload registry" style="padding:6px 10px;border-radius:6px;border:1px solid var(--border,#ddd);background:var(--bg,#fff);color:var(--text);cursor:pointer;">⟳</button>
                <button type="button" id="cpInlineClear" title="Clear selection" style="padding:6px 10px;border-radius:6px;border:1px solid var(--border,#ddd);background:var(--bg,#fff);color:var(--text);cursor:pointer;">Bỏ chọn</button>
              </div>
            </div>
            <div id="cpInlineGrid" class="character-picker-grid character-picker-grid--inline" aria-live="polite" style="margin-top:8px;max-height:340px;overflow:auto;"></div>
            <div class="igv2-choice-header" style="border-top:1px solid var(--border,#eee);margin-top:8px;padding-top:6px;">
              <span id="cpInlineCount" class="cp-count" style="font-size:12px;opacity:0.75;">0 nhân vật</span>
            </div>
          </div>
        </div>
      </div>
    `;
    return wrap;
  }

  async function refreshInline() {
    const grid = document.getElementById('cpInlineGrid');
    const count = document.getElementById('cpInlineCount');
    if (!grid) return;
    grid.innerHTML = '<div style="padding:14px;text-align:center;opacity:0.7;">Đang tải…</div>';
    try {
      const chars = await loadCharacters(STATE.query, STATE.series);
      if (!chars.length) {
        grid.innerHTML = '<div style="padding:14px;text-align:center;opacity:0.7;">Không có kết quả</div>';
        if (count) count.textContent = '0 nhân vật';
        return;
      }
      grid.innerHTML = chars.map((c) => {
        const hasThumb = c.has_thumbnail !== false && c.thumbnail;
        const thumb = hasThumb
          ? `<img src="${escapeHTML(c.thumbnail)}" alt="" loading="lazy" onerror="this.replaceWith(Object.assign(document.createElement('div'),{className:'cp-no-thumb',textContent:(this.dataset.letter||'?')}));" data-letter="${escapeHTML((c.display_name||'?')[0])}"/>`
          : `<div class="cp-no-thumb">${escapeHTML((c.display_name || '?')[0])}</div>`;
        return `
          <button type="button" class="character-card" data-key="${escapeHTML(c.key)}" title="${escapeHTML(c.display_name)} — ${escapeHTML(c.series || '')}">
            ${thumb}
            <div class="cp-name">${escapeHTML(c.display_name)}</div>
            <div class="cp-series">${escapeHTML(c.series || '')}</div>
          </button>`;
      }).join('');
      if (count) count.textContent = `${chars.length} nhân vật`;
      // Bind click on cards.
      grid.querySelectorAll('.character-card').forEach((btn) => {
        btn.addEventListener('click', () => {
          const key = btn.getAttribute('data-key');
          const rec = chars.find((x) => x.key === key);
          if (!rec) return;
          if (typeof STATE.onSelect === 'function') STATE.onSelect(rec);
          document.dispatchEvent(new CustomEvent('character:selected', { detail: rec }));
          closeInline();
        });
      });
    } catch (e) {
      grid.innerHTML = `<div style="padding:14px;color:#c00;">Lỗi: ${escapeHTML(e.message || e)}</div>`;
    }
  }

  let inlineDebounceTimer = null;
  function debouncedInline() {
    clearTimeout(inlineDebounceTimer);
    inlineDebounceTimer = setTimeout(refreshInline, 200);
  }

  function closeInline() {
    const el = document.getElementById(INLINE_ID);
    if (el && el.parentNode) el.parentNode.removeChild(el);
  }

  async function openInline(onSelect) {
    STATE.onSelect = typeof onSelect === 'function' ? onSelect : null;
    const container = document.getElementById('chatContainer');
    if (!container) {
      // Fallback to modal if chat container is missing.
      return openPicker(onSelect);
    }
    const card = buildInlineCard();
    container.appendChild(card);
    container.scrollTop = container.scrollHeight;

    if (!STATE.cache.series) {
      try { await loadSeries(); } catch (e) { console.warn('[character-picker] series load failed', e); }
    }
    const sel = document.getElementById('cpInlineSeries');
    if (sel) {
      const list = STATE.cache.series || [];
      sel.innerHTML = '<option value="">Tất cả series</option>' +
        list.map((s) => `<option value="${escapeHTML(s.key)}">${escapeHTML(s.name)}</option>`).join('');
      sel.value = STATE.series || '';
      sel.addEventListener('change', (ev) => { STATE.series = ev.target.value; refreshInline(); });
    }
    const search = document.getElementById('cpInlineSearch');
    if (search) {
      search.value = STATE.query || '';
      search.addEventListener('input', (ev) => { STATE.query = ev.target.value; debouncedInline(); });
      setTimeout(() => search.focus(), 50);
    }
    const reload = document.getElementById('cpInlineReload');
    if (reload) {
      reload.addEventListener('click', async () => {
        try {
          await fetch(`${API_BASE}/reload`, { method: 'POST', credentials: 'same-origin' });
          STATE.cache.series = null;
          await loadSeries();
          if (sel) {
            const list = STATE.cache.series || [];
            sel.innerHTML = '<option value="">Tất cả series</option>' +
              list.map((s) => `<option value="${escapeHTML(s.key)}">${escapeHTML(s.name)}</option>`).join('');
          }
          refreshInline();
        } catch (e) { console.error('[character-picker] reload failed', e); }
      });
    }
    const closeBtn = card.querySelector('.cp-inline-close');
    if (closeBtn) closeBtn.addEventListener('click', closeInline);
    const clearBtn = document.getElementById('cpInlineClear');
    if (clearBtn) clearBtn.addEventListener('click', () => {
      if (typeof STATE.onSelect === 'function') STATE.onSelect(null);
      document.dispatchEvent(new CustomEvent('character:selected', { detail: null }));
      closeInline();
    });

    refreshInline();
  }

  window.openCharacterPickerInline = openInline;
  window.closeCharacterPickerInline = closeInline;
})();
