/**
 * character-chip.js — Headless character-state holder + inline-picker glue.
 *
 * No DOM is injected into the topbar. The chip used to live there but the
 * inline card-style picker (see character-picker.js openCharacterPickerInline)
 * replaces it. This file only:
 *
 *   1. Wires #characterPickerBtn → opens the inline picker card in chat.
 *   2. Wires #manualProfileBtn (in the More menu) → opens the manual-profile
 *      modal (built lazily in DOM on first open).
 *   3. Listens for `character:selected` events from the picker, fetches
 *      `/api/characters/preview` for canonical metadata, and exposes the
 *      result on `window.selectedCharacter` for downstream image-gen flows.
 *   4. Tracks `window.imageGenOptions` (preflightOnly, budgetMode, …) so the
 *      provider-choice card and reasoning-image-gen.js can read user prefs.
 *      Toggles for these now live inside the provider-choice card itself.
 */
(function () {
  'use strict';

  const STATE = {
    record: null,
    preview: null,
    manualProfile: null,
  };

  // Public hooks consumed by reasoning-image-gen.js + send-message-helpers.js.
  window.imageGenOptions = window.imageGenOptions || {
    preflightOnly: false,
    budgetMode: 'normal',
    requirePreflightPass: false,
    maxCostLevel: '',
  };
  window.selectedCharacter = null;
  window.manualProfile = null;

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
      lora_hint: rec.lora_hint || p.lora_hint || null,
      safe_to_attach_lora: typeof p.safe_to_attach_lora === 'boolean' ? p.safe_to_attach_lora : true,
      needs_review: !!p.needs_review,
      key: rec.key || null,
    };
    Object.keys(out).forEach((k) => { if (out[k] === null || out[k] === '') delete out[k]; });
    return out;
  }

  async function fetchPreview(key) {
    if (!key) return null;
    try {
      const res = await fetch(`/api/characters/preview?key=${encodeURIComponent(key)}`,
        { credentials: 'same-origin' });
      if (!res.ok) return null;
      return await res.json();
    } catch (e) {
      console.warn('[character-chip] preview fetch failed', e);
      return null;
    }
  }

  async function onSelected(rec) {
    STATE.record = rec || null;
    STATE.preview = rec ? await fetchPreview(rec.key) : null;
    window.selectedCharacter = buildSelectedCharacter(rec, STATE.preview);
    document.dispatchEvent(new CustomEvent('character:state-changed', {
      detail: { character: window.selectedCharacter },
    }));
  }

  // ── Manual profile modal (lazy-built, opened from More menu) ──────────

  function ensureProfileModal() {
    let modal = document.getElementById('manualProfileModal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'manualProfileModal';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
      <div class="modal-content" role="dialog" aria-modal="true" aria-label="Manual character profile" style="max-width:560px;">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
          <h3 style="margin:0;">Manual character profile</h3>
          <button type="button" id="mpModalClose" aria-label="Close" style="background:transparent;border:0;font-size:22px;cursor:pointer;color:var(--text);">×</button>
        </div>
        <p style="margin:0 0 12px;color:var(--text-muted,#888);font-size:13px;">
          Chỉ điền khi muốn ghi đè thủ công. Bỏ trống = dùng dữ liệu picker / SAA.
        </p>
        <div style="display:grid;gap:8px;">
          <input id="mpDisplayName" placeholder="Display name"/>
          <input id="mpSeriesName" placeholder="Series name"/>
          <input id="mpSeriesSlug" placeholder="series_slug"/>
          <textarea id="mpVisual" rows="2" placeholder="visual_traits — one per line"></textarea>
          <textarea id="mpOutfit" rows="2" placeholder="outfit_traits — one per line"></textarea>
          <textarea id="mpPersonality" rows="2" placeholder="personality_traits — one per line"></textarea>
          <textarea id="mpGuard" rows="2" placeholder="negative_identity_guard — one per line"></textarea>
          <textarea id="mpRefs" rows="2" placeholder="reference_images — one URL per line"></textarea>
        </div>
        <div style="display:flex;gap:8px;flex-wrap:wrap;margin-top:12px;">
          <button type="button" id="mpApplyBtn" class="btn btn--primary">Apply</button>
          <button type="button" id="mpPreviewBtn" class="btn">Preview</button>
          <button type="button" id="mpSaveBtn" class="btn">Save</button>
          <button type="button" id="mpClearBtn" class="btn btn--danger">Clear</button>
        </div>
        <div id="mpResult" hidden style="margin-top:12px;padding:8px;background:var(--bg-secondary,#f5f5f5);border-radius:6px;font-size:12px;font-family:monospace;white-space:pre-wrap;max-height:160px;overflow:auto;"></div>
      </div>
    `;
    document.body.appendChild(modal);
    modal.addEventListener('click', (ev) => { if (ev.target === modal) closeProfileModal(); });
    modal.querySelector('#mpModalClose').addEventListener('click', closeProfileModal);
    modal.querySelector('#mpApplyBtn').addEventListener('click', () => submitProfile('apply'));
    modal.querySelector('#mpPreviewBtn').addEventListener('click', () => submitProfile('preview'));
    modal.querySelector('#mpSaveBtn').addEventListener('click', () => submitProfile('save'));
    modal.querySelector('#mpClearBtn').addEventListener('click', clearProfile);
    return modal;
  }

  function openProfileModal() {
    const modal = ensureProfileModal();
    // Repopulate from current state.
    const m = STATE.manualProfile || {};
    const set = (id, v) => { const el = modal.querySelector('#' + id); if (el) el.value = v || ''; };
    set('mpDisplayName', m.display_name);
    set('mpSeriesName', m.series_name);
    set('mpSeriesSlug', m.series_slug);
    set('mpVisual', (m.visual_traits || []).join('\n'));
    set('mpOutfit', (m.outfit_traits || []).join('\n'));
    set('mpPersonality', (m.personality_traits || []).join('\n'));
    set('mpGuard', (m.negative_identity_guard || []).join('\n'));
    set('mpRefs', (m.reference_images || []).join('\n'));
    modal.classList.add('open');
  }

  function closeProfileModal() {
    const modal = document.getElementById('manualProfileModal');
    if (modal) modal.classList.remove('open');
  }

  function splitLines(txt) {
    return String(txt || '').split(/\r?\n/).map((s) => s.trim()).filter(Boolean);
  }

  function collectProfileFromForm() {
    const get = (id) => (document.getElementById(id) || {}).value || '';
    const out = {
      display_name: get('mpDisplayName').trim(),
      series_name: get('mpSeriesName').trim(),
      series_slug: get('mpSeriesSlug').trim(),
      visual_traits: splitLines(get('mpVisual')),
      outfit_traits: splitLines(get('mpOutfit')),
      personality_traits: splitLines(get('mpPersonality')),
      negative_identity_guard: splitLines(get('mpGuard')),
      reference_images: splitLines(get('mpRefs')),
    };
    Object.keys(out).forEach((k) => {
      if (Array.isArray(out[k]) ? !out[k].length : !out[k]) delete out[k];
    });
    return out;
  }

  function showResult(data) {
    const box = document.getElementById('mpResult');
    if (!box) return;
    box.hidden = false;
    try { box.textContent = JSON.stringify(data, null, 2); }
    catch (e) { box.textContent = String(data); }
  }

  async function submitProfile(action) {
    const profile = collectProfileFromForm();
    if (!Object.keys(profile).length) {
      showResult({ ok: false, error: 'profile is empty' });
      return;
    }
    if (action === 'apply') {
      STATE.manualProfile = profile;
      window.manualProfile = profile;
      showResult({ ok: true, applied: profile });
      return;
    }
    const path = action === 'save' ? '/api/characters/profile/save' : '/api/characters/profile/preview';
    try {
      const res = await fetch(path, {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile }),
      });
      const data = await res.json().catch(() => ({}));
      if (action === 'save' && res.ok) {
        STATE.manualProfile = profile;
        window.manualProfile = profile;
      }
      showResult(data);
    } catch (e) {
      showResult({ ok: false, error: String(e) });
    }
  }

  function clearProfile() {
    STATE.manualProfile = null;
    window.manualProfile = null;
    const ids = ['mpDisplayName', 'mpSeriesName', 'mpSeriesSlug',
      'mpVisual', 'mpOutfit', 'mpPersonality', 'mpGuard', 'mpRefs'];
    ids.forEach((id) => { const el = document.getElementById(id); if (el) el.value = ''; });
    showResult({ ok: true, cleared: true });
  }

  // ── Wire-up ───────────────────────────────────────────────────────────

  function init() {
    document.addEventListener('character:selected', (ev) => onSelected(ev.detail));
    const pickerBtn = document.getElementById('characterPickerBtn');
    if (pickerBtn) {
      pickerBtn.addEventListener('click', () => {
        if (typeof window.openCharacterPickerInline === 'function') {
          window.openCharacterPickerInline((rec) => onSelected(rec));
        } else if (typeof window.openCharacterPicker === 'function') {
          window.openCharacterPicker((rec) => onSelected(rec));
        }
      });
    }
    const profileBtn = document.getElementById('manualProfileBtn');
    if (profileBtn) {
      profileBtn.addEventListener('click', openProfileModal);
    }
  }

  // Public API for legacy callers.
  window.openManualProfileModal = openProfileModal;
  window.clearCharacterSelection = () => onSelected(null);

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
