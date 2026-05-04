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
    manualProfile: null, // last applied manual profile (or null)
    panelOpen: false,    // Details panel toggled by [⋮]
    options: {
      preflightOnly: false,
      budgetMode: 'normal',         // "normal" | "fast"
      requirePreflightPass: false,
      maxCostLevel: '',             // "" (off) | "low" | "medium" | "high"
    },
  };
  // Public hooks — read by reasoning-image-gen.js / future image-gen flows.
  window.imageGenOptions = STATE.options;
  window.selectedCharacter = null;
  window.manualProfile = null;

  /**
   * Build the documented selected_character schema from a picker record
   * + (optional) preview metadata. Fields with no real data are dropped
   * so the payload never carries fake / placeholder values.
   */
  function buildSelectedCharacter(rec, preview) {
    if (!rec) return null;
    const p = preview || {};
    const slug = rec.character_tag || rec.key || '';
    const sname = rec.series || p.series_name || '';
    const sslug = rec.series_key || rec.series_tag || p.series_slug || '';
    const out = {
      source: p.source || rec.source || 'picker',
      display_name: rec.display_name || p.display_name || '',
      canonical_id: p.canonical_id || (slug && sslug ? `${slug}@${sslug}` : null),
      character_slug: slug || null,
      series_name: sname || '',
      series_slug: sslug || '',
      tag: rec.character_tag || null,
      thumbnail: rec.thumbnail || null,
      preview_url: p.preview_url || null,
      preview_source: p.preview_source || null,
    };
    Object.keys(out).forEach((k) => {
      if (out[k] === null || out[k] === '') delete out[k];
    });
    return out;
  }
  // Exported for unit / smoke tests and other modules that want the same shape.
  window.__characterChip = { buildSelectedCharacter };

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
      <button type="button" class="chip-details-btn" id="chipDetailsBtn"
              title="Manual profile / advanced limits"
              aria-expanded="${STATE.panelOpen ? 'true' : 'false'}">⋮</button>
    `;
    const panel = renderPanel();

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

    mount.innerHTML = body + controls + panel;
    bindEvents();
  }

  function renderPanel() {
    const mp = STATE.manualProfile || {};
    const o = STATE.options;
    return `
      <div class="character-chip-panel" id="chipPanel" ${STATE.panelOpen ? '' : 'hidden'}>
        <div class="chip-panel-section">
          <strong>Manual profile</strong>
          <small> (only sent when fields are filled)</small>
          <div class="chip-row">
            <input id="mpDisplayName" placeholder="Display name" value="${escapeHTML(mp.display_name || '')}"/>
            <input id="mpSeriesName" placeholder="Series name" value="${escapeHTML(mp.series_name || '')}"/>
            <input id="mpSeriesSlug" placeholder="series_slug" value="${escapeHTML(mp.series_slug || '')}"/>
          </div>
          <textarea id="mpVisual" rows="2"
            placeholder="visual_traits — one per line">${escapeHTML((mp.visual_traits || []).join('\n'))}</textarea>
          <textarea id="mpOutfit" rows="2"
            placeholder="outfit_traits — one per line">${escapeHTML((mp.outfit_traits || []).join('\n'))}</textarea>
          <textarea id="mpPersonality" rows="2"
            placeholder="personality_traits — one per line">${escapeHTML((mp.personality_traits || []).join('\n'))}</textarea>
          <textarea id="mpGuard" rows="2"
            placeholder="negative_identity_guard — one per line">${escapeHTML((mp.negative_identity_guard || []).join('\n'))}</textarea>
          <textarea id="mpRefs" rows="2"
            placeholder="reference_images — one URL per line">${escapeHTML((mp.reference_images || []).join('\n'))}</textarea>
        </div>
        <div class="chip-panel-section">
          <label class="chip-toggle">
            <input type="checkbox" id="chipRequirePass" ${o.requirePreflightPass ? 'checked' : ''}/>
            <span>Block on high risk (require_preflight_pass)</span>
          </label>
          <label class="chip-mode">
            Cap (max_cost_level):
            <select id="chipMaxCost">
              <option value=""        ${o.maxCostLevel === ''       ? 'selected' : ''}>off</option>
              <option value="low"     ${o.maxCostLevel === 'low'    ? 'selected' : ''}>low</option>
              <option value="medium"  ${o.maxCostLevel === 'medium' ? 'selected' : ''}>medium</option>
              <option value="high"    ${o.maxCostLevel === 'high'   ? 'selected' : ''}>high</option>
            </select>
          </label>
        </div>
        <div class="chip-panel-actions">
          <button type="button" id="mpApplyBtn" class="chip-action">Apply</button>
          <button type="button" id="mpClearBtn" class="chip-action chip-action--warn">Clear profile</button>
        </div>
      </div>
    `;
  }

  function splitLines(txt) {
    return String(txt || '').split('\n').map((s) => s.trim()).filter(Boolean);
  }

  function applyManualProfile() {
    const $ = (id) => document.getElementById(id);
    const profile = {};
    const dn = $('mpDisplayName') ? $('mpDisplayName').value.trim() : '';
    const sn = $('mpSeriesName')  ? $('mpSeriesName').value.trim()  : '';
    const ss = $('mpSeriesSlug')  ? $('mpSeriesSlug').value.trim()  : '';
    if (dn) profile.display_name = dn;
    if (sn) profile.series_name = sn;
    if (ss) profile.series_slug = ss;
    const v  = splitLines($('mpVisual')      ? $('mpVisual').value      : '');
    const ou = splitLines($('mpOutfit')      ? $('mpOutfit').value      : '');
    const pn = splitLines($('mpPersonality') ? $('mpPersonality').value : '');
    const g  = splitLines($('mpGuard')       ? $('mpGuard').value       : '');
    const r  = splitLines($('mpRefs')        ? $('mpRefs').value        : '');
    if (v.length)  profile.visual_traits = v;
    if (ou.length) profile.outfit_traits = ou;
    if (pn.length) profile.personality_traits = pn;
    if (g.length)  profile.negative_identity_guard = g;
    if (r.length)  profile.reference_images = r;
    if (Object.keys(profile).length === 0) {
      STATE.manualProfile = null;
      window.manualProfile = null;
    } else {
      STATE.manualProfile = profile;
      window.manualProfile = profile;
    }
  }

  function clearManualProfile() {
    STATE.manualProfile = null;
    window.manualProfile = null;
    render();
  }

  function bindEvents() {
    const $ = (id) => document.getElementById(id);
    if ($('chipSelectBtn'))   $('chipSelectBtn').onclick   = () => triggerPicker('');
    if ($('chipReviewBtn'))   $('chipReviewBtn').onclick   = () => { STATE.panelOpen = true; render(); };
    if ($('chipClearBtn'))    $('chipClearBtn').onclick    = clearSelection;
    if ($('chipPreflight'))   $('chipPreflight').onchange  = (ev) => { STATE.options.preflightOnly = !!ev.target.checked; };
    if ($('chipMode'))        $('chipMode').onchange       = (ev) => { STATE.options.budgetMode = ev.target.value || 'normal'; };
    if ($('chipDetailsBtn'))  $('chipDetailsBtn').onclick  = () => { STATE.panelOpen = !STATE.panelOpen; render(); };
    if ($('chipRequirePass')) $('chipRequirePass').onchange = (ev) => { STATE.options.requirePreflightPass = !!ev.target.checked; };
    if ($('chipMaxCost'))     $('chipMaxCost').onchange    = (ev) => { STATE.options.maxCostLevel = ev.target.value || ''; };
    if ($('mpApplyBtn'))      $('mpApplyBtn').onclick      = applyManualProfile;
    if ($('mpClearBtn'))      $('mpClearBtn').onclick      = clearManualProfile;
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
    // Publish structured payload immediately so a fast user can fire a
    // request before the preview fetch returns.
    window.selectedCharacter = buildSelectedCharacter(rec, null);
    document.body.setAttribute('data-character-key', rec.key || '');
    document.body.setAttribute('data-series-key', rec.series_key || '');
    render();
    // Then enrich with the authoritative preview (safe_to_attach_lora, ...).
    const p = await fetchPreview(rec.key);
    if (p) {
      STATE.preview = p;
      window.selectedCharacter = buildSelectedCharacter(rec, p);
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
