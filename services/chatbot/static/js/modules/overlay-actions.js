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
            if (data.drive_url) {
                const a = document.createElement('a');
                a.href = data.drive_url;
                a.target = '_blank';
                a.style.cssText = 'position:absolute;opacity:0;pointer-events:none';
                // Don't auto-open; just update tooltip
            }
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
            const actionBtn = event.target.closest('.igv2-img-btn[data-igv2-action]');
            if (actionBtn) {
                event.preventDefault();
                event.stopPropagation();

                const action = actionBtn.getAttribute('data-igv2-action');
                const imageId = actionBtn.getAttribute('data-image-id') || '';
                const imgSrc = actionBtn.getAttribute('data-img-src') || '';

                if (action === 'download') {
                    _igv2Download(imgSrc, imageId);
                } else if (action === 'info') {
                    _igv2Info(imageId, actionBtn);
                } else if (action === 'save') {
                    _igv2Save(imageId, actionBtn);
                }
                return;
            }

            const imageEl = event.target.closest('.igv2-chat-image img[data-igv2-open]');
            if (imageEl) {
                const targetUrl = imageEl.getAttribute('data-igv2-open');
                if (targetUrl) {
                    window.open(targetUrl, '_blank', 'noopener');
                }
            }
        });
    }
}

/**
 * Initialize lightbox zoom, pinch-to-zoom, swipe-to-close,
 * and image preview window globals.
 * Call from DOMContentLoaded after modules are ready.
 */
export function initLightbox(messageRenderer) {
    // Image preview wrappers
    const openImagePreview = (img) => messageRenderer.openImagePreview(img);
    const closeImagePreview = () => messageRenderer.closeImagePreview();
    const downloadPreviewImage = () => messageRenderer.downloadPreviewImage();

    // Keep openImagePreview global — called dynamically from rendered messages
    window.openImagePreview = openImagePreview;

    // Image preview zoom state
    let currentZoom = 1.0;

    const zoomPreviewImage = (delta) => {
        const previewImg = document.getElementById('imagePreviewContent');
        if (previewImg) {
            currentZoom = Math.max(0.5, Math.min(5.0, currentZoom + delta));
            previewImg.style.transform = `scale(${currentZoom})`;
        }
    };

    const resetPreviewZoom = () => {
        const previewImg = document.getElementById('imagePreviewContent');
        if (previewImg) {
            currentZoom = 1.0;
            previewImg.style.transform = 'scale(1)';
        }
    };

    // Keep resetPreviewZoom global — called from gallery viewGalleryImage
    window.resetPreviewZoom = resetPreviewZoom;

    // Pinch-to-zoom on mobile for lightbox
    const wrap = document.getElementById('lightboxImageWrap');
    if (wrap) {
        let startDist = 0;
        let startZoom = 1;
        wrap.addEventListener('touchstart', (e) => {
            if (e.touches.length === 2) {
                startDist = Math.hypot(
                    e.touches[0].clientX - e.touches[1].clientX,
                    e.touches[0].clientY - e.touches[1].clientY
                );
                startZoom = currentZoom;
            }
        }, { passive: true });
        wrap.addEventListener('touchmove', (e) => {
            if (e.touches.length === 2) {
                const dist = Math.hypot(
                    e.touches[0].clientX - e.touches[1].clientX,
                    e.touches[0].clientY - e.touches[1].clientY
                );
                const scale = dist / startDist;
                currentZoom = Math.max(0.5, Math.min(5.0, startZoom * scale));
                const img = document.getElementById('imagePreviewContent');
                if (img) img.style.transform = `scale(${currentZoom})`;
            }
        }, { passive: true });
        // Double-tap to toggle zoom
        let lastTap = 0;
        wrap.addEventListener('touchend', (e) => {
            if (e.touches.length > 0) return;
            const now = Date.now();
            if (now - lastTap < 300) {
                // Double tap
                if (currentZoom > 1.1) {
                    resetPreviewZoom();
                } else {
                    zoomPreviewImage(1.5);
                }
            }
            lastTap = now;
        });
        // Mouse wheel zoom
        wrap.addEventListener('wheel', (e) => {
            e.preventDefault();
            zoomPreviewImage(e.deltaY < 0 ? 0.2 : -0.2);
        }, { passive: false });

        // === Swipe-down to close lightbox ===
        let swipeStartY = 0;
        let swipeDeltaY = 0;
        let isSwiping = false;
        const modal = document.getElementById('imagePreviewModal');
        const lightboxEl = modal ? modal.querySelector('.lightbox') : null;

        wrap.addEventListener('touchstart', (e) => {
            if (e.touches.length === 1 && currentZoom <= 1.05) {
                swipeStartY = e.touches[0].clientY;
                isSwiping = true;
                swipeDeltaY = 0;
            }
        }, { passive: true });

        wrap.addEventListener('touchmove', (e) => {
            if (!isSwiping || e.touches.length !== 1) return;
            swipeDeltaY = e.touches[0].clientY - swipeStartY;
            if (swipeDeltaY > 0 && lightboxEl) {
                const progress = Math.min(swipeDeltaY / 200, 1);
                lightboxEl.style.transform = `translateY(${swipeDeltaY}px)`;
                lightboxEl.style.opacity = 1 - progress * 0.5;
            }
        }, { passive: true });

        wrap.addEventListener('touchend', () => {
            if (!isSwiping) return;
            isSwiping = false;
            if (swipeDeltaY > 120) {
                // Swipe far enough → close
                if (lightboxEl) {
                    lightboxEl.style.transition = 'transform 0.2s, opacity 0.2s';
                    lightboxEl.style.transform = 'translateY(100%)';
                    lightboxEl.style.opacity = '0';
                }
                setTimeout(() => {
                    closeImagePreview();
                    if (lightboxEl) {
                        lightboxEl.style.transition = '';
                        lightboxEl.style.transform = '';
                        lightboxEl.style.opacity = '';
                    }
                }, 200);
            } else if (lightboxEl) {
                // Snap back
                lightboxEl.style.transition = 'transform 0.2s, opacity 0.2s';
                lightboxEl.style.transform = '';
                lightboxEl.style.opacity = '';
                setTimeout(() => { lightboxEl.style.transition = ''; }, 200);
            }
            swipeDeltaY = 0;
        });

        // === Tap background (outside image) to close ===
        wrap.addEventListener('click', (e) => {
            if (e.target === wrap && currentZoom <= 1.05) {
                closeImagePreview();
            }
        });
    }

    // Return functions for delegation registration
    return { openImagePreview, closeImagePreview, downloadPreviewImage, zoomPreviewImage, resetPreviewZoom };
}
