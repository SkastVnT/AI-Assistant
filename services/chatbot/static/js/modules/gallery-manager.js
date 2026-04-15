/**
 * Gallery Manager Module
 * Gallery modal, image CRUD, info display, long-press actions.
 *
 * Extracted from main.js — no behavior change.
 */

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
}

// ── Gallery CRUD ────────────────────────────────────────────────────

async function openGallery() {
    const modal = document.getElementById('galleryModal');
    const grid = document.getElementById('galleryGrid');
    const stats = document.getElementById('galleryStats');

    if (!modal) return;

    modal.classList.add('active', 'open');
    grid.innerHTML = '<div style="text-align: center; padding: 50px; color: #999;">⏳ Đang tải ảnh...</div>';

    try {
        const url = '/api/gallery/images?all=true';
        const response = await fetch(url);
        const data = await response.json();

        if (data.success && data.images.length > 0) {
            const sourceText = data.source === 'mongodb' ? ' ☁️' : ' 💾';
            stats.textContent = `📊 Tổng số: ${data.total} ảnh (Tất cả)${sourceText}`;

            grid.innerHTML = data.images.map(img => {
                const metadataStr = JSON.stringify(img.metadata).replace(/"/g, '&quot;');
                const rawFilename = img.filename || (img.path || '').split('/').pop() || '';
                const filename = escapeHtml(rawFilename);
                // JS-safe: escape single quotes and backslashes for onclick contexts
                const jsFilename = rawFilename.replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                // Prefer cloud URL (ImgBB CDN) for display, fallback to local path
                const displayUrl = escapeHtml(img.cloud_url || img.path || img.url || '');
                const isCloud = !!img.cloud_url;
                const hasDrive = !!img.drive_url;
                const imageDataStr = encodeURIComponent(JSON.stringify({
                    id: img.id || '',
                    filename: rawFilename,
                    path: img.cloud_url || img.path || img.url || '',
                    cloud_url: img.cloud_url || '',
                    drive_url: img.drive_url || '',
                    share_url: img.share_url || img.drive_url || img.cloud_url || img.path || img.url || '',
                    created: img.created || img.created_at || '',
                    creator: img.creator || '',
                    db_status: img.db_status || {},
                    metadata: img.metadata || {}
                }));
                const jsImgId = (img.id || '').replace(/\\/g, '\\\\').replace(/'/g, "\\'");
                const safePrompt = escapeHtml(img.prompt || '');
                const safeCreated = escapeHtml(img.created || '');
                const safeFallback = escapeHtml(img.local_path || img.path || '');
                return `
                    <div class="gallery-item" data-path="${displayUrl}" data-filename="${filename}" data-metadata="${metadataStr}">
                        <img src="${displayUrl}" alt="${filename}" loading="lazy" onerror="this.src='${safeFallback}'">
                        ${isCloud ? '<span class="gallery-cloud-badge" title="Stored in cloud">☁️</span>' : ''}
                        ${hasDrive ? '<span class="gallery-drive-badge" title="Saved to Drive">📁</span>' : ''}
                        <div class="gallery-item-info">
                            <div style="font-size:10px;opacity:0.7;">📅 ${safeCreated}</div>
                            <div class="gallery-item-prompt" title="${safePrompt}">
                                ${escapeHtml((img.prompt || '').substring(0, 60))}${(img.prompt || '').length > 60 ? '…' : ''}
                            </div>
                        </div>
                        <button class="gallery-info-btn" data-action="gallery:info" data-action-stop data-filename="${filename}" data-image-id="${escapeHtml(img.id || '')}" data-image-data="${imageDataStr}" title="Thông tin ảnh">
                            ℹ️
                        </button>
                        <button class="gallery-upload-btn" data-action="gallery:upload" data-action-stop data-filename="${filename}" title="Upload metadata + ảnh lên MongoDB/Firebase/Drive">
                            ⬆️
                        </button>
                        <button class="gallery-delete-btn" data-action="gallery:delete" data-action-stop data-filename="${filename}" title="Xóa ảnh">
                            🗑️
                        </button>
                    </div>
                `;
            }).join('');

            // Add click event listeners to gallery items
            document.querySelectorAll('.gallery-item').forEach(item => {
                item.addEventListener('click', () => {
                    const path = item.getAttribute('data-path');
                    const metadataStr = item.getAttribute('data-metadata');
                    try {
                        const metadata = JSON.parse(metadataStr);
                        viewGalleryImage(path, metadata);
                    } catch (e) {
                        console.error('[Gallery] Failed to parse metadata:', e);
                        viewGalleryImage(path, {});
                    }
                });
            });
        } else {
            grid.innerHTML = '<div class="gallery-empty">🖼️ No pictures yet</div>';
            stats.textContent = '📊 Total: 0 Pictures';
        }
    } catch (error) {
        console.error('[Gallery] Error:', error);
        grid.innerHTML = '<div class="gallery-empty">❌ Error while loading images</div>';
    }
}

function closeGallery() {
    const modal = document.getElementById('galleryModal');
    if (modal) modal.classList.remove('active', 'open');
}

async function refreshGallery() {
    console.log('[Gallery] Refreshing...');
    await openGallery();
}

async function showGalleryImageInfo(filename, imageId = '', encodedImageData = '') {
    const modal = document.getElementById('galleryInfoModal');
    const body = document.getElementById('galleryInfoBody');
    if (!modal || !body) return;

    modal.classList.add('active', 'open');
    body.innerHTML = '<div style="padding:12px 0; color: var(--text-tertiary);">⏳ Đang tải thông tin ảnh...</div>';

    let fromCard = {};
    if (encodedImageData) {
        try {
            fromCard = JSON.parse(decodeURIComponent(encodedImageData));
        } catch (_) {}
    }

    const toSafeText = (value) => {
        if (value === null || value === undefined || value === '') return 'Khong co';
        if (typeof value === 'boolean') return value ? 'Co' : 'Khong';
        if (typeof value === 'object') return JSON.stringify(value);
        return String(value);
    };

    const toSafeLink = (value) => {
        const raw = String(value || '').trim();
        if (!raw || !/^https?:\/\//i.test(raw)) return '';
        return raw;
    };

    const dateText = (value) => {
        const raw = String(value || '').trim();
        if (!raw) return 'Khong ro';
        const d = new Date(raw);
        if (Number.isNaN(d.getTime())) return raw;
        return d.toLocaleString('vi-VN');
    };

    const renderRow = (label, value, options = {}) => {
        const full = options.full ? ' gallery-info-row--full' : '';
        const statusClass = options.statusClass ? ` ${options.statusClass}` : '';
        if (options.link) {
            const safeHref = escapeHtml(options.link);
            return `
                <div class="gallery-info-row${full}">
                    <span class="gallery-info-label">${escapeHtml(label)}</span>
                    <a class="gallery-info-value gallery-info-value--link" href="${safeHref}" target="_blank" rel="noopener noreferrer">${escapeHtml(value)}</a>
                </div>
            `;
        }
        if (options.status) {
            return `
                <div class="gallery-info-row${full}">
                    <span class="gallery-info-label">${escapeHtml(label)}</span>
                    <span class="gallery-info-value gallery-info-status${statusClass}">${escapeHtml(value)}</span>
                </div>
            `;
        }
        return `
            <div class="gallery-info-row${full}">
                <span class="gallery-info-label">${escapeHtml(label)}</span>
                <span class="gallery-info-value">${escapeHtml(value)}</span>
            </div>
        `;
    };

    const renderInfoBody = (payload = {}) => {
        const metadata = payload.metadata || fromCard.metadata || {};
        const db = payload.db_status || fromCard.db_status || {};
        const links = payload.links || {
            share_url: fromCard.share_url || fromCard.drive_url || fromCard.cloud_url || fromCard.path || '',
            drive_folder_url: 'https://drive.google.com/drive/folders/11MN5m72gl84LsP1NMfBjeX9YAzsIlRxz?usp=sharing'
        };

        const creator = toSafeText(payload.creator || fromCard.creator || 'unknown');
        const createdAt = dateText(payload.created_at || fromCard.created || '');
        const shareLink = toSafeLink(links.share_url || fromCard.share_url || '');
        const driveFolder = toSafeLink(links.drive_folder_url || '');
        const mongoText = db.mongodb ? 'Da dong bo' : 'Chua dong bo';
        const firebaseText = db.firebase ? 'Da dong bo' : 'Chua dong bo';

        const allMeta = Object.entries(metadata)
            .filter(([_, v]) => v !== null && v !== undefined && String(v).trim() !== '')
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([k, v]) => renderRow(k, toSafeText(v)))
            .join('');

        body.innerHTML = `
            <div class="gallery-info-card">
                <div class="gallery-info-card__title">Tong quan</div>
                <div class="gallery-info-grid">
                    ${renderRow('Nguoi tao', creator)}
                    ${renderRow('Thoi gian tao', createdAt)}
                    ${renderRow('MongoDB', mongoText, { status: true, statusClass: db.mongodb ? 'gallery-info-status--ok' : '' })}
                    ${renderRow('Firebase', firebaseText, { status: true, statusClass: db.firebase ? 'gallery-info-status--ok' : '' })}
                    ${shareLink ? renderRow('Share link', shareLink, { full: true, link: shareLink }) : ''}
                    ${driveFolder ? renderRow('Drive folder', driveFolder, { full: true, link: driveFolder }) : ''}
                </div>
            </div>

            <div class="gallery-info-card">
                <div class="gallery-info-card__title">Thong so anh</div>
                <div class="gallery-info-grid">${allMeta || renderRow('Metadata', 'Khong co metadata', { full: true })}</div>
            </div>

            <div class="gallery-info-actions">
                <button class="btn btn--sm btn--primary" data-action="gallery:upload" data-filename="${escapeHtml(filename)}">⬆️ Upload len DB</button>
                ${(links.share_url || fromCard.share_url) ? `<button class="btn btn--sm btn--ghost" data-action="gallery:copy-link" data-url="${escapeHtml(links.share_url || fromCard.share_url)}">🔗 Copy Share Link</button>` : ''}
            </div>
        `;
    };

    try {
        const response = await fetch(`/api/gallery/image-info?filename=${encodeURIComponent(filename)}`);
        if (response.status === 404) {
            renderInfoBody({});
            return;
        }
        const data = await response.json();
        if (!data.success) throw new Error(data.error || 'Cannot load image info');
        renderInfoBody(data);
    } catch (error) {
        console.error('[Gallery] image-info error:', error);
        // Graceful fallback: still show what we currently know from gallery card
        renderInfoBody({});
    }
}

function closeGalleryInfo() {
    const modal = document.getElementById('galleryInfoModal');
    if (modal) modal.classList.remove('active', 'open');
}

async function copyGalleryShareLink(url) {
    try {
        await navigator.clipboard.writeText(url || '');
        alert('✅ Đã copy share link');
    } catch (_) {
        prompt('Copy link:', url || '');
    }
}

async function uploadGalleryImageToDB(filename) {
    if (!filename) return;
    try {
        let response = await fetch('/api/gallery/upload-db', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filename })
        });

        // Fallback for older backend versions that do not have /api/gallery/upload-db
        if (response.status === 404) {
            const item = document.querySelector(`.gallery-item[data-filename="${CSS.escape(filename)}"]`);
            const imagePath = item?.getAttribute('data-path') || `/storage/images/${filename}`;
            const metadataRaw = item?.getAttribute('data-metadata') || '{}';
            let metadata = {};
            try { metadata = JSON.parse(metadataRaw); } catch (_) {}
            metadata.filename = filename;

            const imgResp = await fetch(imagePath);
            if (!imgResp.ok) throw new Error('Cannot fetch local image for fallback upload');
            const blob = await imgResp.blob();
            const b64 = await new Promise((resolve, reject) => {
                const reader = new FileReader();
                reader.onload = () => resolve((reader.result || '').toString());
                reader.onerror = () => reject(new Error('Cannot convert image to base64'));
                reader.readAsDataURL(blob);
            });

            response = await fetch('/api/save-generated-image', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: b64, metadata })
            });
            if (response.status === 404) {
                response = await fetch('/api/save-image', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ image: b64, metadata })
                });
            }
        }

        const data = await response.json().catch(() => ({}));
        if (!response.ok || (data.success === false)) {
            throw new Error(data.error || `Upload failed (${response.status})`);
        }
        alert('✅ Đã upload lên MongoDB/Firebase/Drive (nếu cấu hình Drive endpoint hợp lệ).');
        await refreshGallery();
    } catch (error) {
        console.error('[Gallery] upload-db error:', error);
        alert('❌ Upload DB lỗi: ' + (error.message || 'Unknown error'));
    }
}

async function deleteGalleryImage(filename) {
    if (!confirm(`Bạn có chắc muốn xóa ảnh "${filename}"?`)) return;

    try {
        const response = await fetch(`/api/delete-image/${filename}`, {
            method: 'DELETE'
        });
        const data = await response.json();

        if (data.success) {
            console.log('[Gallery] Image deleted:', filename);
            // Refresh gallery
            await refreshGallery();
        } else {
            alert('Lỗi: ' + (data.error || 'Không thể xóa ảnh'));
        }
    } catch (error) {
        console.error('[Gallery] Delete error:', error);
        alert('Lỗi khi xóa ảnh');
    }
}

function viewGalleryImage(imagePath, metadata) {
    console.log('[Gallery] Opening image:', imagePath);

    const modal = document.getElementById('imagePreviewModal');
    const img = document.getElementById('imagePreviewContent');
    const info = document.getElementById('imagePreviewInfo');

    if (modal && img) {
        // Reset zoom
        if (window.resetPreviewZoom) window.resetPreviewZoom();
        img.src = imagePath;
        // Store path for download
        img.dataset.downloadUrl = imagePath;
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';

        if (info && metadata) {
            const m = metadata;
            const metaItems = [
                m.model && { label: 'Model', value: m.model },
                m.sampler && { label: 'Sampler', value: m.sampler },
                m.steps && { label: 'Steps', value: m.steps },
                m.cfg_scale && { label: 'CFG', value: m.cfg_scale },
                (m.width && m.height) && { label: 'Size', value: `${m.width}×${m.height}` },
                m.denoising_strength && { label: 'Denoise', value: m.denoising_strength },
                m.vae && { label: 'VAE', value: m.vae },
                m.seed && { label: 'Seed', value: m.seed },
            ].filter(Boolean);

            const loraStr = m.lora_models
                ? (typeof m.lora_models === 'string' ? m.lora_models : JSON.stringify(m.lora_models))
                : '';

            info.innerHTML = `
                ${m.prompt ? `<div class="lightbox__prompt"><span class="lightbox__meta-label">Prompt</span><br>${m.prompt}</div>` : ''}
                ${m.negative_prompt ? `<div class="lightbox__prompt" style="opacity:0.7;font-size:11px;"><span class="lightbox__meta-label">Negative</span><br>${m.negative_prompt}</div>` : ''}
                <div class="lightbox__meta-grid">
                    ${metaItems.map(i => `
                        <div class="lightbox__meta-item">
                            <span class="lightbox__meta-label">${i.label}</span>
                            <span class="lightbox__meta-value">${i.value}</span>
                        </div>
                    `).join('')}
                    ${loraStr ? `<div class="lightbox__meta-item" style="grid-column:1/-1"><span class="lightbox__meta-label">LoRA</span><span class="lightbox__meta-value">${loraStr}</span></div>` : ''}
                </div>
            `;
        } else if (info) {
            info.innerHTML = '';
        }
    }
}

// ── Long-press on gallery items (mobile) ────────────────────────────
function initGalleryLongPress() {
    let pressTimer = null;
    let activeItem = null;

    document.addEventListener('touchstart', (e) => {
        const item = e.target.closest('.gallery-item');
        if (!item) return;
        pressTimer = setTimeout(() => {
            // Dismiss any previously active item
            if (activeItem && activeItem !== item) {
                activeItem.classList.remove('show-actions');
            }
            item.classList.toggle('show-actions');
            activeItem = item.classList.contains('show-actions') ? item : null;
        }, 500);
    }, { passive: true });

    document.addEventListener('touchend', () => { clearTimeout(pressTimer); });
    document.addEventListener('touchmove', () => { clearTimeout(pressTimer); });

    // Dismiss actions when tapping elsewhere
    document.addEventListener('click', (e) => {
        if (activeItem && !e.target.closest('.gallery-item')) {
            activeItem.classList.remove('show-actions');
            activeItem = null;
        }
    });
}

/**
 * Initialize gallery: bind modal close, gallery button, long-press,
 * and expose all gallery functions as window globals.
 * Call from DOMContentLoaded.
 */
export function initGallery() {
    // Gallery modal: click overlay to close
    const galleryModal = document.getElementById('galleryModal');
    if (galleryModal) {
        galleryModal.addEventListener('click', (e) => {
            if (e.target === galleryModal) {
                closeGallery();
            }
        });
    }

    // Gallery button
    const galleryBtn = document.getElementById('galleryBtn');
    if (galleryBtn) {
        galleryBtn.addEventListener('click', openGallery);
    }

    // Long-press (mobile)
    initGalleryLongPress();
}

// Export gallery functions for delegation registration
export {
    openGallery,
    closeGallery,
    refreshGallery,
    showGalleryImageInfo,
    closeGalleryInfo,
    copyGalleryShareLink,
    uploadGalleryImageToDB,
    deleteGalleryImage,
    viewGalleryImage,
};
