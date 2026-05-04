/**
 * character-chip.js — Compact character chip + Check-first / Mode toggles.
 *
 * Renders inside #characterChipMount (a small inline slot in the topbar).
 * Listens for the `character:selected` event dispatched by character-picker.js,
 * fetches `/api/characters/preview?key=<key>` for authoritative metadata, and
 * exposes the selection on `window.selectedCharacter` plus
 * `window.imageGenOptions = { preflightOnly, budgetMode }` for downstream
 * image-gen modules to consume.
 *
 * Default UI is intentionally tiny:
 *   No selection : Character: Auto-detect [Select]
 *   Selected     : [thumb] Name · Series  [×]
 *   Unknown      : ⚠ Unknown: Name · Series  [Review]
 *
 * Tooltip details (canonical_id, source, safe_to_attach_lora, needs_review)
 * appear on hover only.
 */
(function () {
  'use strict';

  const MOUNT_ID = 'characterChipMount';
  const STATE = {
    record: null,        // last selection from the picker
    preview: null,       // last fetched CharacterPreview
    options: { preflightOnly: false, budgetMode: 'normal' },
  };
  // Public option object — read by reasoning-image-gen.js.
  window.imageGenOptions = STATE.options;

  function escapeHTML(s) {
    return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function ensureMount() {
    let mount = document.getElementById(MOUNT_ID);
    if (mount) return mount;
    // Insert immediately after the existing character picker button so the
    // chip lives in the same compact topbar row without redesigning the UI.
    const anchor = document.getElementById('characterPickerBtn');
    if (!anchor || !anchor.parentNode) return null;
    mount = document.createElement('span');
    mount.id = MOUNT_ID;
    mount.className = 'character-chip-mount';
    anchor.parentNode.insertBefore(mount, anchor.nextSibling);
    return mount;
  }

  async function fetchPreview(key) {
    if (!key) return null;
    try {
      const res = await fetch(`/api/characters/preview?key=${encodeURIComponent(key)}`, {
        credentials: 'same-origin',
      });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      console.warn('[character-chip] preview fetch failed', e);
      return null;
    }
  }

  function tooltipText(preview) {
    if (!preview || !preview.tooltip_lines) return '';
    return preview.tooltip_lines.join('\n');
  }

  function render() {
    const mount = ensureMount();
    if (!mount) return;
    const p = STATE.preview;
    const rec = STATE.record;

    // Toggle controls (always visible, compact).
    const controls = `
      <label class="chip-toggle" title="Run preflight risk check before ComfyUI">
        <input type="checkbox" id="chipPreflight" ${STATE.options.preflightOnly ? 'checked' : ''}/>
        <span>Check first</span>
      </label>
      <label class="chip-mode" title="Cost budget hint for the pipeline">
        Mode:
        <select id="chipMode">
          <option value="normal" ${STATE.options.budgetMode === 'normal' ? 'selected' : ''}>Normal</option>
          <option value="fast" ${STATE.options.budgetMode === 'fast' ? 'selected' : ''}>Fast</option>
        </select>
      </label>
    `;

    let body;
    if (!rec) {
      body = `
        <span class="character-chip character-chip--empty">
          <span class="chip-label">Character:</span>
          <span class="chip-value">Auto-detect</span>
          <button type="button" class="chip-action" id="chipSelectBtn">Select</button>
        </span>
      `;
    } else {
      const needsReview = !!(p && p.needs_review);
      const tip = tooltipText(p);
      const thumb = (p && p.preview_url) || `/api/characters/${encodeURIComponent(rec.key)}/thumbnail`;
      const name = (p && p.display_name) || rec.display_name || rec.key;
      const series = (p && p.series_name) || rec.series || '';
      const cls = needsReview ? 'character-chip character-chip--warn' : 'character-chip character-chip--ok';
      const reviewBtn = needsReview
        ? `<button type="button" class="chip-action chip-action--warn" id="chipReviewBtn">Review</button>`
        : '';
      body = `
        <span class="${cls}" title="${escapeHTML(tip)}">
          ${needsReview ? '<span class="chip-warn">⚠</span>' : ''}
          <img class="chip-thumb" src="${escapeHTML(thumb)}" alt=""
               onerror="this.style.visibility='hidden';"/>
          <span class="chip-name">${escapeHTML(name)}</span>
          ${series ? `<span class="chip-sep">·</span><span class="chip-series">${escapeHTML(series)}</span>` : ''}
          ${reviewBtn}
          <button type="button" class="chip-clear" id="chipClearBtn" aria-label="Clear selection">×</button>
        </span>
      `;
    }

    mount.innerHTML = body + controls;
    bindEvents();
  }

  function bindEvents() {
    const selectBtn = document.getElementById('chipSelectBtn');
    if (selectBtn) selectBtn.onclick = () => triggerPicker('');
    const reviewBtn = document.getElementById('chipReviewBtn');
    if (reviewBtn) reviewBtn.onclick = () => triggerPicker(STATE.record ? (STATE.record.display_name || '') : '');
    const clearBtn = document.getElementById('chipClearBtn');
    if (clearBtn) clearBtn.onclick = clearSelection;
    const preflight = document.getElementById('chipPreflight');
    if (preflight) preflight.onchange = (ev) => { STATE.options.preflightOnly = !!ev.target.checked; };
    const mode = document.getElementById('chipMode');
    if (mode) mode.onchange = (ev) => { STATE.options.budgetMode = ev.target.value || 'normal'; };
  }

  function triggerPicker(prefill) {
    if (typeof window.openCharacterPicker !== 'function') {
      console.warn('[character-chip] picker not loaded');
      return;
    }
    window.openCharacterPicker((rec) => onSelected(rec));
    // The picker sets its own search input; pre-filling is best-effort.
    setTimeout(() => {
      const input = document.getElementById('cpSearchInput');
      if (input && prefill) {
        input.value = prefill;
        input.dispatchEvent(new Event('input', { bubbles: true }));
      }
    }, 60);
  }

  function clearSelection() {
    STATE.record = null;
    STATE.preview = null;
    window.selectedCharacter = null;
    document.body.removeAttribute('data-character-key');
    document.body.removeAttribute('data-series-key');
    render();
  }

  async function onSelected(rec) {
    if (!rec) return;
    STATE.record = rec;
    window.selectedCharacter = rec;
    document.body.setAttribute('data-character-key', rec.key || '');
    document.body.setAttribute('data-series-key', rec.series_key || '');
    // Render synchronously with what we have so the chip appears instantly.
    render();
    // Then fetch authoritative preview (safe_to_attach_lora, needs_review, ...).
    const p = await fetchPreview(rec.key);
    if (p) {
      STATE.preview = p;
      render();
    }
  }

  function init() {
    ensureMount();
    render();
    document.addEventListener('character:selected', (ev) => onSelected(ev.detail));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
