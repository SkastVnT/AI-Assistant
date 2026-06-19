/* eslint-disable no-console */
/**
 * Nano Banana — Gemini 2.5 Flash Image surface.
 *
 * Public API (window.nanoBanana):
 *   openModal()      — open & sync prompt from chat
 *   closeModal()
 *   useChatPrompt()  — re-pull current chat textarea value
 *   generate()       — POST /api/nano-banana/generate
 *
 * Backend contract (mirrors routes/nano_banana.py):
 *   POST /api/nano-banana/generate
 *     { prompt, num_images, aspect_ratio, image_size,
 *       reference_images_b64: [b64], reference_mime_types: [mime],
 *       conversation_id }
 *   → { success, images:[{url,image_id}], provider, model,
 *       requested_num_images, delivered_num_images, latency_ms, cost_usd }
 */
(function () {
  'use strict';

  const MAX_REF_DEFAULT = 6;
  const state = {
    refs: [],            // [{name, mime, b64, dataUrl}]
    config: null,        // /status payload
    busy: false,
  };

  // ── DOM helpers ────────────────────────────────────────────────
  const $  = (id) => document.getElementById(id);
  const on = (el, ev, fn) => el && el.addEventListener(ev, fn);

  function el(tag, attrs = {}, children = []) {
    const node = document.createElement(tag);
    Object.entries(attrs).forEach(([k, v]) => {
      if (k === 'style' && typeof v === 'object') Object.assign(node.style, v);
      else if (k === 'class') node.className = v;
      else if (k.startsWith('on') && typeof v === 'function') node.addEventListener(k.slice(2), v);
      else node.setAttribute(k, v);
    });
    children.forEach(c => node.appendChild(typeof c === 'string' ? document.createTextNode(c) : c));
    return node;
  }

  function setStatus(msg, level = 'info') {
    const s = $('nbStatus'); if (!s) return;
    s.textContent = msg;
    s.classList.remove('is-ok', 'is-warn');
    if (level === 'ok')    s.classList.add('is-ok');
    if (level === 'error') s.classList.add('is-warn');
  }

  function setProgress(msg, busy = false) {
    const p = $('nbProgress'); if (!p) return;
    p.textContent = msg || '';
    p.classList.toggle('is-busy', !!busy);
  }

  function showError(msg) {
    const e = $('nbError'); if (!e) return;
    if (!msg) { e.style.display = 'none'; e.textContent = ''; return; }
    e.style.display = '';
    e.textContent = msg;
  }

  // ── Status / config probe ──────────────────────────────────────
  async function probeStatus() {
    try {
      const r = await fetch('/api/nano-banana/status', { credentials: 'same-origin' });
      const j = await r.json();
      state.config = j;
      const maxRefsEl = $('nbMaxRefs');
      if (maxRefsEl) maxRefsEl.textContent = String(j.max_reference_images || MAX_REF_DEFAULT);

      // Populate the model dropdown from the server-side whitelist.
      const sel = $('nbModel');
      if (sel) {
        sel.innerHTML = '';
        const models = Array.isArray(j.models) && j.models.length
          ? j.models
          : [{ alias: '', id: j.model || '', label: j.model || 'default' }];
        models.forEach(m => {
          const opt = document.createElement('option');
          opt.value = m.alias || m.id;
          opt.textContent = m.label || m.id;
          if ((j.default_model_alias && m.alias === j.default_model_alias)
              || (!j.default_model_alias && m.id === j.model)) {
            opt.selected = true;
          }
          sel.appendChild(opt);
        });
      }

      const btn = $('nbGenerateBtn');
      if (!j.available) {
        setStatus('Chưa cấu hình GEMINI_API_KEY_1 trong env.', 'error');
        if (btn) btn.disabled = true;
      } else {
        setStatus(`✓ Sẵn sàng • ${j.default_model_alias || j.model} • ${j.default_image_size}`, 'ok');
        if (btn) btn.disabled = false;
      }
    } catch (e) {
      setStatus('Không kiểm tra được trạng thái: ' + e.message, 'error');
    }
  }

  // ── File handling ──────────────────────────────────────────────
  function readFileAsB64(file) {
    return new Promise((resolve, reject) => {
      const fr = new FileReader();
      fr.onload  = () => {
        const dataUrl = fr.result;             // "data:image/png;base64,XXX"
        const comma   = dataUrl.indexOf(',');
        const b64     = comma >= 0 ? dataUrl.slice(comma + 1) : dataUrl;
        resolve({ b64, dataUrl, mime: file.type || 'image/png', name: file.name });
      };
      fr.onerror = () => reject(fr.error || new Error('read failed'));
      fr.readAsDataURL(file);
    });
  }

  async function addFiles(fileList) {
    const max = (state.config?.max_reference_images) || MAX_REF_DEFAULT;
    const files = Array.from(fileList || []);
    for (const f of files) {
      if (state.refs.length >= max) {
        setProgress(`Tối đa ${max} ảnh tham chiếu.`);
        break;
      }
      if (!/^image\//.test(f.type || '')) continue;
      if (f.size > 10 * 1024 * 1024) {
        setProgress(`"${f.name}" vượt 10 MB, bỏ qua.`);
        continue;
      }
      try {
        const item = await readFileAsB64(f);
        state.refs.push(item);
      } catch (e) {
        console.warn('[nano-banana] failed to read', f.name, e);
      }
    }
    renderThumbs();
    setProgress(state.refs.length ? `${state.refs.length} ảnh tham chiếu` : '');
  }

  function renderThumbs() {
    const wrap = $('nbThumbs'); if (!wrap) return;
    wrap.innerHTML = '';
    state.refs.forEach((r, idx) => {
      const card = el('div', { class: 'nb-thumb' });
      const img = el('img', { src: r.dataUrl, alt: r.name });
      const close = el('button', {
        class: 'nb-thumb__del', title: 'Xoá',
        onclick: () => { state.refs.splice(idx, 1); renderThumbs();
          setProgress(state.refs.length ? `${state.refs.length} ảnh tham chiếu` : ''); },
      }, ['×']);
      card.appendChild(img);
      card.appendChild(close);
      wrap.appendChild(card);
    });
  }

  // ── Modal ──────────────────────────────────────────────────────
  function openModal() {
    // Use overlay manager when available (tracks in _stack for outside-click close).
    if (window.openOverlay) {
      window.openOverlay('nanoBananaModal');
      // onOpen callback in main.js calls onOverlayOpen()
    } else {
      _showModal();
    }
  }

  function _showModal() {
    const m = $('nanoBananaModal'); if (!m) return;
    m.classList.add('open');
    showError('');
    useChatPrompt();
    if (!state.config) probeStatus();
    if (window.lucide?.createIcons) try { window.lucide.createIcons(); } catch (_) {}
  }

  function onOverlayOpen() {
    // Called by overlay manager's onOpen callback (registered in main.js).
    _showModal();
  }

  function closeModal() {
    if (window.closeOverlay) {
      window.closeOverlay('nanoBananaModal');
    } else {
      const m = $('nanoBananaModal'); if (!m) return;
      m.classList.remove('open');
    }
  }

  function useChatPrompt() {
    const ta = $('nbPrompt'); if (!ta) return;
    const userInput = $('userInput') || $('chatInput') || $('messageInput');
    const text = (userInput && (userInput.value || userInput.textContent) || '').trim();
    if (text && !ta.value.trim()) ta.value = text;
  }

  // ── Generate ───────────────────────────────────────────────────
  async function generate() {
    if (state.busy) return;
    showError('');
    const prompt = ($('nbPrompt')?.value || '').trim();
    if (!prompt) { showError('Vui lòng nhập prompt.'); return; }
    const num   = parseInt($('nbCount')?.value || '1', 10);
    const aspect= $('nbAspect')?.value || '1:1';
    const size  = $('nbSize')?.value || '2K';
    const model = $('nbModel')?.value || '';

    const body = {
      prompt,
      num_images: num,
      aspect_ratio: aspect,
      image_size: size,
      model,
      reference_images_b64: state.refs.map(r => r.b64),
      reference_mime_types: state.refs.map(r => r.mime),
      conversation_id: window.currentConversationId || '',
    };

    const btn = $('nbGenerateBtn');
    state.busy = true;
    if (btn) { btn.disabled = true; btn.dataset.label = btn.innerHTML;
      btn.innerHTML = '<span>Đang tạo…</span>'; }
    $('nbResults').innerHTML = '';

    // Animated queue attempt counter — updates every ~3 s while waiting.
    const MAX_ATTEMPTS = 5;
    let displayAttempt = 1;
    setProgress(`Đang tạo ${num} ảnh • ${aspect} • ${size} • lần thử ${displayAttempt}/${MAX_ATTEMPTS}`, true);
    const attemptTicker = setInterval(() => {
      if (displayAttempt < MAX_ATTEMPTS) {
        displayAttempt++;
        setProgress(`Đang tạo ${num} ảnh • ${aspect} • ${size} • lần thử ${displayAttempt}/${MAX_ATTEMPTS}`, true);
      }
    }, 3000);

    const t0 = performance.now();
    try {
      const r = await fetch('/api/nano-banana/generate', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });
      const j = await r.json().catch(() => ({}));
      clearInterval(attemptTicker);
      if (!r.ok || !j.success) {
        const attemptTxt = (j.attempt_count > 1) ? ` (thử ${j.attempt_count}/${MAX_ATTEMPTS} lần)` : '';
        showError((j.error || `HTTP ${r.status}`) + attemptTxt);
        setProgress('Thất bại.', false);
        return;
      }
      renderResults(j);
      const dt = ((performance.now() - t0) / 1000).toFixed(1);
      const actualAttempt = j.attempt_count || 1;
      const attemptNote = actualAttempt > 1 ? ` • thử ${actualAttempt}/${MAX_ATTEMPTS} lần` : '';
      setProgress(
        `${j.delivered_num_images}/${j.requested_num_images} ảnh • ${dt}s • ` +
        `cost ≈ $${(j.cost_usd || 0).toFixed(3)}${attemptNote}`,
        false
      );
      if ((j.errors || []).length) {
        showError('Một số ảnh thất bại: ' + j.errors.slice(0, 3).join('; '));
      }
    } catch (e) {
      clearInterval(attemptTicker);
      showError('Network error: ' + e.message);
      setProgress('Thất bại.', false);
    } finally {
      clearInterval(attemptTicker);
      state.busy = false;
      if (btn) { btn.disabled = false; if (btn.dataset.label) btn.innerHTML = btn.dataset.label; }
    }
  }

  function renderResults(payload) {
    const grid = $('nbResults'); if (!grid) return;
    grid.innerHTML = '';
    (payload.images || []).forEach((im, idx) => {
      const card = el('div', { class: 'nb-result' });
      const img = el('img', {
        src: im.url, alt: `Nano Banana #${idx + 1}`, loading: 'lazy',
        onclick: () => { try { if (window.openImagePreview) window.openImagePreview(img); } catch (_) {} },
      });
      const bar = el('div', { class: 'nb-result__bar' });
      bar.appendChild(document.createTextNode(`#${idx + 1}`));
      const dl = el('a', {
        href: im.url, download: `nano-banana-${im.image_id || idx + 1}.png`,
        title: 'Tải xuống',
      }, ['⬇ Tải']);
      bar.appendChild(dl);
      card.appendChild(img);
      card.appendChild(bar);
      grid.appendChild(card);
    });
  }

  // ── Wiring ─────────────────────────────────────────────────────
  function wire() {
    const btn = $('nanoBananaBtn');
    on(btn, 'click', (e) => {
      e.preventDefault();
      e.stopPropagation(); // prevent same-click from triggering outside-close
      // Close the Tools dropdown if open.
      const dd = $('topbarToolsDropdown');
      if (dd) dd.classList.add('hidden');
      openModal();
    });

    const dz = $('nbDropzone');
    const fi = $('nbFileInput');
    on(dz, 'click', () => fi && fi.click());
    on(fi, 'change', (e) => addFiles(e.target.files).then(() => { fi.value = ''; }));
    on(dz, 'dragover', (e) => { e.preventDefault(); dz.classList.add('is-dragover'); });
    on(dz, 'dragleave', () => dz.classList.remove('is-dragover'));
    on(dz, 'drop', (e) => {
      e.preventDefault();
      dz.classList.remove('is-dragover');
      addFiles(e.dataTransfer?.files);
    });

    // Close on overlay backdrop click (fallback when overlay manager not ready)
    const modal = $('nanoBananaModal');
    on(modal, 'click', (e) => { if (e.target === modal) closeModal(); });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && modal && modal.classList.contains('open')) closeModal();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', wire);
  } else {
    wire();
  }

  window.nanoBanana = { openModal, closeModal, useChatPrompt, generate, onOverlayOpen };
})();
