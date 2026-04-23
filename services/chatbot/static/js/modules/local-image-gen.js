/**
 * local-image-gen.js — Embeds the Character Select SAA web UI in a modal
 * and pipes any newly-generated ComfyUI output image back into the active
 * chatbot conversation.
 *
 * Public API:
 *   window.openLocalImageGen()  — open modal, start polling
 *   window.closeLocalImageGen() — close modal, stop polling
 *
 * Backend contract:
 *   GET /api/character-select/url       → { enabled, url }
 *   GET /api/local-image-gen/recent?since=<epoch> → { ok, now, files: [{name, mtime, url, size}] }
 *   GET /api/local-image-gen/file/<name>          → image bytes
 */
(function () {
  'use strict';

  const POLL_MS = 2500;
  const STATE = {
    open: false,
    timer: null,
    sinceEpoch: 0,
    seen: new Set(),
    iframeUrl: '',
    autoSend: true,
  };

  function $(id) { return document.getElementById(id); }

  function escapeHTML(str) {
    return String(str || '').replace(/[&<>"']/g, (c) => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
  }

  function toast(msg, type) {
    if (window.showToast) window.showToast(msg, type || 'info');
    else console.info('[local-image-gen]', msg);
  }

  function buildModal() {
    let modal = $('localImageGenModal');
    if (modal) return modal;
    modal = document.createElement('div');
    modal.id = 'localImageGenModal';
    modal.className = 'modal-overlay local-imggen-modal';
    modal.style.display = 'none';
    modal.innerHTML = `
      <div class="modal-panel local-imggen-panel" role="dialog" aria-modal="true" aria-label="Local Image Gen (SAA)">
        <div class="modal-panel__header local-imggen-header">
          <h2 class="modal-panel__title">
            <i data-lucide="palette" class="lucide"></i> Local Image Gen — Character Select SAA
          </h2>
          <div class="local-imggen-toolbar">
            <label class="local-imggen-autosend" title="Tự đẩy ảnh mới vào khung chat">
              <input type="checkbox" id="ligAutoSend" checked />
              <span>Auto → Chat</span>
            </label>
            <button type="button" class="btn btn--sm btn--ghost" id="ligOpenInTab" title="Mở SAA trong tab mới">
              <i data-lucide="external-link" class="lucide"></i>
            </button>
            <button type="button" class="btn btn--sm btn--ghost" id="ligReloadFrame" title="Tải lại UI SAA">
              <i data-lucide="rotate-ccw" class="lucide"></i>
            </button>
            <button type="button" class="modal-panel__close" id="ligCloseBtn" aria-label="Đóng">×</button>
          </div>
        </div>
        <div class="modal-panel__body local-imggen-body">
          <div class="local-imggen-status" id="ligStatus">
            <span class="lig-status-dot" data-state="idle"></span>
            <span id="ligStatusText">Đang kết nối SAA…</span>
          </div>
          <div class="local-imggen-frame-wrap">
            <iframe id="ligFrame" referrerpolicy="no-referrer" allow="clipboard-read; clipboard-write" loading="lazy"></iframe>
          </div>
          <div class="local-imggen-results" id="ligResults">
            <div class="lig-results-header">
              <strong>Ảnh vừa tạo</strong>
              <span class="lig-results-hint">Tự cập nhật mỗi ${(POLL_MS / 1000).toFixed(1)}s</span>
            </div>
            <div class="lig-results-grid" id="ligResultsGrid">
              <div class="lig-empty">Chưa có ảnh mới. Hãy bấm <em>Create Image</em> trong SAA.</div>
            </div>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(modal);
    if (window.lucide?.createIcons) window.lucide.createIcons();

    modal.addEventListener('click', (e) => {
      if (e.target === modal) closeModal();
    });
    $('ligCloseBtn').addEventListener('click', closeModal);
    $('ligReloadFrame').addEventListener('click', () => {
      const f = $('ligFrame');
      if (f && STATE.iframeUrl) f.src = STATE.iframeUrl + (STATE.iframeUrl.includes('?') ? '&' : '?') + 'r=' + Date.now();
    });
    $('ligOpenInTab').addEventListener('click', () => {
      if (STATE.iframeUrl) window.open(STATE.iframeUrl, '_blank', 'noopener');
    });
    $('ligAutoSend').addEventListener('change', (e) => {
      STATE.autoSend = !!e.target.checked;
    });

    return modal;
  }

  function setStatus(state, text) {
    const dot = document.querySelector('#ligStatus .lig-status-dot');
    const label = $('ligStatusText');
    if (dot) dot.dataset.state = state;
    if (label) label.textContent = text;
  }

  async function fetchSidecarUrl() {
    try {
      const res = await fetch('/api/character-select/url', { credentials: 'same-origin' });
      const data = await res.json();
      if (!data.enabled) {
        return { enabled: false, url: data.url || 'http://localhost:51028' };
      }
      return { enabled: true, url: data.url };
    } catch (err) {
      console.warn('[local-image-gen] sidecar url fetch failed', err);
      return { enabled: false, url: 'http://localhost:51028' };
    }
  }

  function pushImageToChat(file) {
    // Prefer the rich MessageRenderer when available, else fall back to a
    // minimal markdown injection through the chat input.
    const url = file.url;
    const mdImage = `![SAA ${escapeHTML(file.name)}](${url})`;
    const note = `🎨 **Local SD (SAA)** — \`${escapeHTML(file.name)}\`\n\n${mdImage}`;

    const renderer = window.chatApp?.messageRenderer;
    const container = document.getElementById('chatContainer');
    if (renderer && container && typeof renderer.addMessage === 'function') {
      try {
        renderer.addMessage(container, note, false, 'local-sd', '', new Date().toISOString());
        return true;
      } catch (err) {
        console.warn('[local-image-gen] renderer.addMessage failed', err);
      }
    }

    // Fallback: drop into the message input so user can hit Enter.
    const input = document.getElementById('messageInput');
    if (input) {
      input.value = (input.value ? input.value + '\n\n' : '') + note;
      input.dispatchEvent(new Event('input', { bubbles: true }));
      input.focus();
      return true;
    }
    return false;
  }

  function renderResultsGrid(files) {
    const grid = $('ligResultsGrid');
    if (!grid) return;
    if (!files.length && !STATE.seen.size) {
      grid.innerHTML = '<div class="lig-empty">Chưa có ảnh mới. Hãy bấm <em>Create Image</em> trong SAA.</div>';
      return;
    }
    // Keep last 12 in chronological order (newest first).
    const cards = files.map(f => `
      <figure class="lig-card" data-name="${escapeHTML(f.name)}">
        <img loading="lazy" src="${escapeHTML(f.url)}" alt="${escapeHTML(f.name)}" />
        <figcaption>
          <span class="lig-card-name" title="${escapeHTML(f.name)}">${escapeHTML(f.name)}</span>
          <button type="button" class="btn btn--sm btn--ghost lig-send-btn" data-url="${escapeHTML(f.url)}" data-name="${escapeHTML(f.name)}">
            ↗ Chat
          </button>
        </figcaption>
      </figure>
    `).join('');
    grid.innerHTML = cards;
    grid.querySelectorAll('.lig-send-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        pushImageToChat({ name: btn.dataset.name, url: btn.dataset.url });
        toast('Đã đẩy ảnh sang khung chat', 'success');
      });
    });
  }

  async function pollOnce() {
    if (!STATE.open) return;
    try {
      const since = STATE.sinceEpoch || 0;
      const res = await fetch(`/api/local-image-gen/recent?since=${encodeURIComponent(since)}&limit=12`, {
        credentials: 'same-origin',
      });
      const data = await res.json();
      if (!data.ok) {
        setStatus('error', data.error || 'Không đọc được output ComfyUI');
        return;
      }
      // First successful poll seeds the watermark — only files appearing AFTER
      // the modal opens count as "new".
      if (STATE.sinceEpoch === 0) {
        STATE.sinceEpoch = data.now;
        setStatus('ok', `Đang theo dõi ${data.root}`);
        return;
      }

      const fresh = (data.files || []).filter(f => !STATE.seen.has(f.name));
      if (fresh.length === 0) return;

      // Mark seen first so re-entry doesn't double-fire.
      fresh.forEach(f => STATE.seen.add(f.name));
      // Advance the watermark to the newest mtime we just observed.
      STATE.sinceEpoch = Math.max(STATE.sinceEpoch, ...fresh.map(f => f.mtime));

      // Render strip (newest first; merge with previously-shown small set).
      const grid = $('ligResultsGrid');
      const previous = grid ? Array.from(grid.querySelectorAll('.lig-card')).map(el => ({
        name: el.dataset.name,
        url: el.querySelector('img')?.getAttribute('src') || '',
      })).filter(f => f.url) : [];
      const merged = [...fresh, ...previous].slice(0, 12);
      renderResultsGrid(merged);

      if (STATE.autoSend) {
        // Push only the newest single image to chat to avoid spam.
        pushImageToChat(fresh[0]);
        toast(`Ảnh mới: ${fresh[0].name}`, 'success');
      }
    } catch (err) {
      console.warn('[local-image-gen] poll failed', err);
      setStatus('error', 'Mất kết nối backend');
    }
  }

  function startPolling() {
    stopPolling();
    pollOnce();
    STATE.timer = setInterval(pollOnce, POLL_MS);
  }

  function stopPolling() {
    if (STATE.timer) {
      clearInterval(STATE.timer);
      STATE.timer = null;
    }
  }

  async function openModal() {
    const modal = buildModal();
    STATE.open = true;
    STATE.sinceEpoch = 0;
    STATE.seen = new Set();
    setStatus('idle', 'Đang kết nối SAA…');
    renderResultsGrid([]);

    const cfg = await fetchSidecarUrl();
    STATE.iframeUrl = cfg.url || 'http://localhost:51028';
    const frame = $('ligFrame');
    if (frame) frame.src = STATE.iframeUrl;
    if (!cfg.enabled) {
      setStatus('warn', `SAA disabled — vẫn thử kết nối ${STATE.iframeUrl}. Bật CHARACTER_SELECT_ENABLED=1 trong .env.`);
    } else {
      setStatus('ok', 'Đang kết nối ComfyUI output…');
    }

    modal.style.display = 'flex';
    requestAnimationFrame(() => modal.classList.add('is-open'));
    document.body.classList.add('modal-open');
    startPolling();
  }

  function closeModal() {
    const modal = $('localImageGenModal');
    STATE.open = false;
    stopPolling();
    if (modal) {
      modal.classList.remove('is-open');
      modal.style.display = 'none';
    }
    document.body.classList.remove('modal-open');
  }

  window.openLocalImageGen = openModal;
  window.closeLocalImageGen = closeModal;
})();
