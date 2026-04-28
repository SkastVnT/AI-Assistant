/**
 * Global Image Viewer
 * ────────────────────────────────────────────────────────────────
 * Refinement, no markup change.
 *
 * Goals:
 *  1. ANY image in chat (message bubble, AP-inline result,
 *     debug preview, gallery thumb, generated preview…) opens
 *     the existing #imagePreviewModal lightbox on click.
 *  2. Clicking the dark backdrop (the rim around the image)
 *     closes the lightbox.
 *  3. Pressing Escape closes the lightbox.
 *
 * Re-uses the existing `window.openImagePreview` /
 * `window.closeImagePreview` wrappers wired by overlay-actions.js
 * → no behavior duplication.
 */

const SELECTOR =
  '.message-content img,' +
  ' .message-text img,' +
  ' .message img,' +
  ' .generated-preview,' +
  ' .gallery-thumb img,' +
  ' .ap-inline-msg img,' +
  ' .ap-debug-preview img,' +
  ' img[alt="Generated Image"]';

// Things we never want to "preview"
const EXCLUDE_SELECTOR =
  '.avatar,' +
  ' .emoji,' +
  ' .icon,' +
  ' .lucide,' +
  ' [data-no-preview]';

const MIN_PREVIEW_PX = 64; // skip tiny inline icons

function shouldOpen(img) {
  if (!img || img.tagName !== 'IMG') return false;
  if (img.matches(EXCLUDE_SELECTOR)) return false;
  if (img.closest(EXCLUDE_SELECTOR)) return false;

  // Skip images already wired to a custom click handler
  // (e.g. character picker thumbnails that swap an input value).
  if (img.dataset.noPreview === 'true') return false;

  // Allow if we matched the inclusion selector
  if (!img.matches(SELECTOR)) return false;

  // Skip tiny icons/avatars by intrinsic size when known
  const w = img.naturalWidth || img.width || 0;
  const h = img.naturalHeight || img.height || 0;
  if (w && h && (w < MIN_PREVIEW_PX || h < MIN_PREVIEW_PX)) return false;

  return true;
}

function openPreview(img) {
  if (typeof window.openImagePreview === 'function') {
    window.openImagePreview(img);
    return;
  }
  // Fallback: directly drive the modal element if the wrapper
  // hasn't been registered yet (very early click).
  const modal = document.getElementById('imagePreviewModal');
  const previewImg = document.getElementById('imagePreviewContent');
  if (modal && previewImg) {
    if (previewImg.src !== img.src) previewImg.src = img.src;
    modal.classList.add('open');
    document.body.style.overflow = 'hidden';
  }
}

function closePreview() {
  if (typeof window.closeImagePreview === 'function') {
    window.closeImagePreview();
    return;
  }
  const modal = document.getElementById('imagePreviewModal');
  if (modal) {
    modal.classList.remove('open');
    document.body.style.overflow = '';
  }
}

let inited = false;
export function initGlobalImageViewer() {
  if (inited) return;
  inited = true;

  // 1) Delegated click: open any qualifying <img>
  document.addEventListener(
    'click',
    (e) => {
      // Don't hijack image-gen overlay action buttons
      if (e.target.closest('.igv2-action-btn, [data-igv2-action]')) return;

      const img = e.target.closest('img');
      if (!img) return;
      if (!shouldOpen(img)) return;

      // Some flows (e.g. igv2-chat-image with [data-igv2-open])
      // prefer opening in a new tab — let those keep their behavior.
      if (img.hasAttribute('data-igv2-open')) return;

      e.stopPropagation();
      e.preventDefault();
      openPreview(img);
    },
    { capture: false },
  );

  // 2) Click on backdrop closes (rim outside the image, controls,
  //    and close button).
  const modal = document.getElementById('imagePreviewModal');
  if (modal) {
    modal.addEventListener('click', (e) => {
      // Ignore clicks on the image itself, on any control button,
      // on the close × span, the upscale dropdown, the meta caption.
      const t = e.target;
      if (!t || t === modal) {
        // Click directly on the dark backdrop
        closePreview();
        return;
      }
      // Allow clicks on controls / image without closing
      const isImg     = t.id === 'imagePreviewContent' || t.tagName === 'IMG';
      const isControl = !!t.closest(
        '.image-preview-controls, button, select, option, [onclick]'
      );
      const isInfo    = !!t.closest('#imagePreviewInfo');
      if (isImg || isControl || isInfo) return;

      // Anything else inside the overlay = treat as backdrop
      closePreview();
    });
  }

  // 3) Escape key closes
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'Escape') return;
    const modal = document.getElementById('imagePreviewModal');
    if (modal && modal.classList.contains('open')) {
      e.stopPropagation();
      closePreview();
    }
  });
}

// Auto-init: works whether loaded as a module before or after main.js
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', initGlobalImageViewer, { once: true });
} else {
  initGlobalImageViewer();
}

// Expose a manual hook for debugging / re-init after dynamic injection
window.initGlobalImageViewer = initGlobalImageViewer;
