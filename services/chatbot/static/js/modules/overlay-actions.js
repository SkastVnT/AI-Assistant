/**
 * Overlay Actions Module
 * Image overlay handlers (download/info/save), click delegation,
 * lightbox zoom/pinch/swipe, and image preview wrappers.
 *
 * Extracted from main.js — no behavior change.
 */

// ── Image overlay button handlers ──────────────────────────────────

function _igv2Download(imgSrc, imageId) {
    const a = document.createElement('a');
    // Prefer the local serve URL for clean filename
    a.href = imageId ? `/api/image-gen/images/${imageId}` : imgSrc;
    a.download = imageId ? `${imageId}.png` : 'generated.png';
    document.body.appendChild(a);
    a.click();
    a.remove();
}

async function _igv2Info(imageId, triggerEl) {
    // Remove any existing popup first
    document.querySelectorAll('.igv2-info-popup').forEach(p => p.remove());
    if (!imageId) return;

    const popup = document.createElement('div');
    popup.className = 'igv2-info-popup';
    popup.textContent = 'Đang tải…';
    triggerEl.closest('.igv2-chat-image').appendChild(popup);

    try {
        const resp = await fetch(`/api/image-gen/meta/${imageId}`);
        if (!resp.ok) throw new Error('Not found');
        const m = await resp.json();
        const _esc = (s) => { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; };
        const rawHtml = [
            m.provider ? `<b>Provider:</b> ${_esc(m.provider)}` : '',
            m.model    ? `<b>Model:</b> ${_esc(m.model)}` : '',
            m.prompt   ? `<b>Prompt:</b> ${_esc(m.prompt.substring(0,200))}` : '',
            m.created_at ? `<b>Created:</b> ${_esc(new Date(m.created_at).toLocaleString())}` : '',
            m.image_id ? `<b>ID:</b> ${_esc(m.image_id)}` : '',
        ].filter(Boolean).join('<br>');
        popup.innerHTML = typeof DOMPurify !== 'undefined' ? DOMPurify.sanitize(rawHtml) : rawHtml;
    } catch {
        popup.textContent = 'Không tải được thông tin.';
    }

    // Close on outside click
    const close = (e) => { if (!popup.contains(e.target) && e.target !== triggerEl) { popup.remove(); document.removeEventListener('click', close, true); } };
    setTimeout(() => document.addEventListener('click', close, true), 50);
}

async function _igv2Save(imageId, triggerEl) {
    if (!imageId) return;
    triggerEl.disabled = true;
    triggerEl.textContent = '⏳';
    try {
        const resp = await fetch(`/api/image-gen/save/${imageId}`, { method: 'POST' });
        const data = await resp.json();
        if (data.success) {
            triggerEl.textContent = '✅';
            triggerEl.title = data.drive_url ? `Drive: ${data.drive_url}` : 'Đã lưu!';
        } else {
            triggerEl.textContent = '❌';
            triggerEl.title = data.error || 'Lỗi khi lưu';
            setTimeout(() => { triggerEl.textContent = '☁'; triggerEl.disabled = false; }, 3000);
        }
    } catch (e) {
        triggerEl.textContent = '❌';
        triggerEl.title = String(e);
        setTimeout(() => { triggerEl.textContent = '☁'; triggerEl.disabled = false; }, 3000);
    }
}

/**
 * Register igv2 overlay delegation.
 * Call once at module scope (before DOMContentLoaded).
 */
export function initOverlayActions() {
    if (!window.__igv2OverlayDelegationBound) {
        window.__igv2OverlayDelegationBound = true;
        document.addEventListener('click', (event) => {
            // Handle igv2 overlay action buttons (download / info / save)
            const actionBtn = event.target.closest('.igv2-img-btn[data-igv2-action]');
            if (!actionBtn) return;

            event.preventDefault();
            event.stopPropagation();

            const action  = actionBtn.getAttribute('data-igv2-action');
            const imageId = actionBtn.getAttribute('data-image-id') || '';
            const imgSrc  = actionBtn.getAttribute('data-img-src') || '';

            if (action === 'download') {
                _igv2Download(imgSrc, imageId);
            } else if (action === 'info') {
                _igv2Info(imageId, actionBtn);
            } else if (action === 'save') {
                _igv2Save(imageId, actionBtn);
            }
        });
    }
}

// initLightbox removed — lightbox is now fully managed by global-image-viewer.js
