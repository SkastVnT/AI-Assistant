/**
 * Global Image Viewer — complete self-contained lightbox
 *
 * Replaces the fragmented global-image-viewer + overlay-actions#initLightbox.
 * - Single delegated click listener for ALL chat images (no makeImagesClickable needed)
 * - Creates modal DOM on first use; also works if #imagePreviewModal already in page
 * - Built-in zoom (wheel + buttons), keyboard (Escape), swipe-to-close
 * - Sets window.openImagePreview / closeImagePreview / downloadPreviewImage /
 *   zoomPreviewImage / resetPreviewZoom for callers in rendered HTML
 */

// ── Selectors ──────────────────────────────────────────────────────────
const INCLUDE = [
  '.message-content img',
  '.message-text img',
  '.message img',
  '.ap-inline-msg img',
  '.ap-stage-preview img',
  '.ap-debug-preview img',
  '.igv2-chat-image img',
  '.igv2-gallery-item img',
  '.igv2-result-img',
  '.generated-preview',
  'img[alt="Generated Image"]',
].join(', ');

const EXCLUDE = '.avatar, .emoji, .icon, .lucide, [data-no-preview]';
const MIN_PX  = 64;

// ── State ──────────────────────────────────────────────────────────────
let _zoom   = 1.0;
let _modal  = null; // cached overlay element

// ── DOM creation ───────────────────────────────────────────────────────
function _buildModal() {
  const el = document.createElement('div');
  el.id        = 'imagePreviewModal';
  el.className = 'image-preview-overlay';
  el.innerHTML = `
    <div class="lightbox-controls" id="lightboxControls">
      <button class="lightbox-btn" id="lbDownload" title="Tải xuống">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
      </button>
      <button class="lightbox-btn" id="lbZoomOut" title="Thu nhỏ">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
      </button>
      <button class="lightbox-btn" id="lbZoomIn" title="Phóng to">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/><line x1="11" y1="8" x2="11" y2="14"/><line x1="8" y1="11" x2="14" y2="11"/></svg>
      </button>
      <button class="lightbox-btn" id="lbReset" title="Đặt lại">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="1 4 1 10 7 10"/><path d="M3.51 15a9 9 0 1 0 .49-3.45"/></svg>
      </button>
      <button class="lightbox-btn lightbox-btn--close" id="lbClose" title="Đóng">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
    <div class="lightbox-wrap" id="lightboxImageWrap">
      <img id="imagePreviewContent" alt="Preview">
    </div>
    <div class="lightbox-meta" id="imagePreviewInfo"></div>`;
  document.body.appendChild(el);
  return el;
}

function _getModal() {
  if (_modal) return _modal;
  _modal = document.getElementById('imagePreviewModal') || _buildModal();
  _bindModalEvents(_modal);
  return _modal;
}

// ── Core API ───────────────────────────────────────────────────────────
function openImagePreview(imgEl) {
  const modal     = _getModal();
  const previewImg = document.getElementById('imagePreviewContent');
  if (!previewImg) return;

  resetPreviewZoom();

  const src = imgEl.src || imgEl.getAttribute('data-igv2-open') || '';
  if (previewImg.src !== src) previewImg.src = src;
  previewImg.dataset.downloadUrl = src;

  modal.classList.add('open');
  document.body.style.overflow = 'hidden';

  // Show dimensions
  const infoEl = document.getElementById('imagePreviewInfo');
  if (infoEl) {
    const show = (w, h) => { infoEl.textContent = w && h ? `${w} × ${h}` : ''; };
    if (previewImg.complete && previewImg.naturalWidth > 0) {
      show(previewImg.naturalWidth, previewImg.naturalHeight);
    } else {
      infoEl.textContent = '';
      previewImg.addEventListener('load', () => show(previewImg.naturalWidth, previewImg.naturalHeight), { once: true });
    }
  }
}

function closeImagePreview() {
  const modal = document.getElementById('imagePreviewModal');
  if (!modal) return;
  modal.classList.remove('open');
  document.body.style.overflow = '';

  // Reset wrap transform (from swipe drag)
  const wrap = document.getElementById('lightboxImageWrap');
  if (wrap) { wrap.style.transform = ''; wrap.style.opacity = ''; }
}

function downloadPreviewImage() {
  const img = document.getElementById('imagePreviewContent');
  if (!img?.src) return;
  const a = document.createElement('a');
  a.href     = img.dataset.downloadUrl || img.src;
  a.download = `image_${Date.now()}.png`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

function zoomPreviewImage(delta) {
  _zoom = Math.max(0.2, Math.min(8, _zoom + delta));
  const img = document.getElementById('imagePreviewContent');
  if (img) img.style.transform = `scale(${_zoom})`;
}

function resetPreviewZoom() {
  _zoom = 1.0;
  const img = document.getElementById('imagePreviewContent');
  if (img) img.style.transform = 'scale(1)';
}

// ── Modal event binding ────────────────────────────────────────────────
function _bindModalEvents(modal) {
  // Control buttons
  const get = (id) => document.getElementById(id);
  get('lbClose')?.addEventListener('click', (e) => { e.stopPropagation(); closeImagePreview(); });
  get('lbDownload')?.addEventListener('click', (e) => { e.stopPropagation(); downloadPreviewImage(); });
  get('lbZoomIn')?.addEventListener('click', (e) => { e.stopPropagation(); zoomPreviewImage(0.25); });
  get('lbZoomOut')?.addEventListener('click', (e) => { e.stopPropagation(); zoomPreviewImage(-0.25); });
  get('lbReset')?.addEventListener('click', (e) => { e.stopPropagation(); resetPreviewZoom(); });

  // Click backdrop (the overlay itself, not children) to close
  modal.addEventListener('click', (e) => {
    if (e.target === modal) closeImagePreview();
  });

  // Wrap-level interactions
  const wrap = document.getElementById('lightboxImageWrap');
  if (!wrap) return;

  // Mouse wheel zoom
  wrap.addEventListener('wheel', (e) => {
    e.preventDefault();
    zoomPreviewImage(e.deltaY < 0 ? 0.2 : -0.2);
  }, { passive: false });

  // Click image wrap backdrop (not the img) to close
  wrap.addEventListener('click', (e) => {
    if (e.target === wrap) closeImagePreview();
  });

  // Swipe-to-close (touch)
  let _swipeY = 0, _swipeDy = 0, _swiping = false;
  wrap.addEventListener('touchstart', (e) => {
    if (e.touches.length === 1 && _zoom <= 1.05) {
      _swipeY = e.touches[0].clientY;
      _swiping = true;
      _swipeDy = 0;
    }
  }, { passive: true });

  wrap.addEventListener('touchmove', (e) => {
    if (!_swiping || e.touches.length !== 1) return;
    _swipeDy = e.touches[0].clientY - _swipeY;
    if (_swipeDy > 0) {
      wrap.style.transform = `translateY(${_swipeDy}px)`;
      wrap.style.opacity   = String(1 - Math.min(_swipeDy / 250, 1) * 0.6);
    }
  }, { passive: true });

  wrap.addEventListener('touchend', () => {
    if (!_swiping) return;
    _swiping = false;
    if (_swipeDy > 120) {
      closeImagePreview();
    } else {
      wrap.style.transition = 'transform 0.2s, opacity 0.2s';
      wrap.style.transform  = '';
      wrap.style.opacity    = '';
      setTimeout(() => { wrap.style.transition = ''; }, 220);
    }
    _swipeDy = 0;
  });

  // Pinch-to-zoom
  let _pinchDist = 0, _pinchZoom = 1;
  wrap.addEventListener('touchstart', (e) => {
    if (e.touches.length === 2) {
      _pinchDist = Math.hypot(
        e.touches[0].clientX - e.touches[1].clientX,
        e.touches[0].clientY - e.touches[1].clientY,
      );
      _pinchZoom = _zoom;
    }
  }, { passive: true });

  wrap.addEventListener('touchmove', (e) => {
    if (e.touches.length !== 2) return;
    const d = Math.hypot(
      e.touches[0].clientX - e.touches[1].clientX,
      e.touches[0].clientY - e.touches[1].clientY,
    );
    _zoom = Math.max(0.5, Math.min(8, _pinchZoom * (d / _pinchDist)));
    const img = document.getElementById('imagePreviewContent');
    if (img) img.style.transform = `scale(${_zoom})`;
  }, { passive: true });

  // Double-tap to toggle zoom
  let _lastTap = 0;
  wrap.addEventListener('touchend', (e) => {
    if (e.touches.length > 0) return;
    const now = Date.now();
    if (now - _lastTap < 300) {
      if (_zoom > 1.1) resetPreviewZoom(); else zoomPreviewImage(1.5);
    }
    _lastTap = now;
  });
}

// ── Click delegation ───────────────────────────────────────────────────
function _shouldOpen(img) {
  if (!img || img.tagName !== 'IMG') return false;
  if (img.matches(EXCLUDE) || img.closest(EXCLUDE)) return false;
  if (img.dataset.noPreview === 'true') return false;
  const w = img.naturalWidth  || img.width  || 0;
  const h = img.naturalHeight || img.height || 0;
  if (w && h && (w < MIN_PX || h < MIN_PX)) return false;
  return img.matches(INCLUDE);
}

// ── Init ───────────────────────────────────────────────────────────────
let _inited = false;

export function initGlobalImageViewer() {
  if (_inited) return;
  _inited = true;

  // Ensure modal exists and globals are set before first click
  _getModal();

  // Wire globals — called from onclick="" in HTML and from other modules
  window.openImagePreview    = openImagePreview;
  window.closeImagePreview   = closeImagePreview;
  window.downloadPreviewImage = downloadPreviewImage;
  window.zoomPreviewImage    = zoomPreviewImage;
  window.resetPreviewZoom    = resetPreviewZoom;

  // Single delegated click for all chat images
  document.addEventListener('click', (e) => {
    // Let igv2 overlay action buttons (.igv2-img-btn) handle themselves
    if (e.target.closest('[data-igv2-action]')) return;

    const img = e.target.closest('img');
    if (!img || !_shouldOpen(img)) return;

    e.preventDefault();
    e.stopPropagation();
    openImagePreview(img);
  });

  // Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const m = document.getElementById('imagePreviewModal');
    if (m?.classList.contains('open')) closeImagePreview();
  });
}

// Auto-init — works whether this module loads before or after DOMContentLoaded
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initGlobalImageViewer, { once: true });
} else {
  initGlobalImageViewer();
}

// Manual re-init hook (debugging)
window.initGlobalImageViewer = initGlobalImageViewer;
