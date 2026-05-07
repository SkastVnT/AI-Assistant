/**
 * gallery-controller.js — right panel image gallery for the active conversation.
 */

import { dom } from './dom.js';
import { appState } from './state.js';

function _imageUrl(img) {
    if (!img) return '';
    if (typeof img === 'string') return img;
    return img.url || img.src || img.data || '';
}

function _openLightbox(url) {
    const root = dom('modalRoot');
    if (!root) return;
    const back = document.createElement('div');
    back.className = 'modal-backdrop';
    back.innerHTML = `<div class="modal__dialog modal__dialog--lightbox"><img alt=""></div>`;
    back.querySelector('img').src = url;
    const close = () => back.remove();
    back.addEventListener('click', close);
    document.addEventListener('keydown', function onKey(e) {
        if (e.key === 'Escape') { close(); document.removeEventListener('keydown', onKey); }
    });
    root.appendChild(back);
}

export function refreshGallery() {
    const grid = dom('galleryGrid');
    const count = dom('galleryCount');
    if (!grid) return;
    const urls = (appState.messages || [])
        .flatMap((m) => m.images || [])
        .map(_imageUrl)
        .filter(Boolean);
    grid.innerHTML = '';
    if (count) count.textContent = String(urls.length);
    if (!urls.length) {
        const empty = document.createElement('div');
        empty.className = 'gallery__empty';
        empty.textContent = 'No images yet.';
        grid.appendChild(empty);
        return;
    }
    for (const u of urls) {
        const tile = document.createElement('button');
        tile.type = 'button';
        tile.className = 'gallery__tile';
        tile.innerHTML = `<img loading="lazy" alt="">`;
        tile.querySelector('img').src = u;
        tile.addEventListener('click', () => _openLightbox(u));
        grid.appendChild(tile);
    }
}

export function initGallery() {
    document.addEventListener('appstatechange', refreshGallery);
    document.addEventListener('chat:complete', refreshGallery);
    refreshGallery();
}
