/**
 * chat-renderer.js — pure render functions, no state mutation.
 *
 * Tiny markdown helper: code fences (```...```) and line breaks only.
 * Anything richer can be added later without changing the call sites.
 */

import { dom } from './dom.js';

function escapeHtml(s) {
    return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#39;');
}

/** Tiny markdown: fenced code blocks + paragraph breaks. */
export function tinyMarkdown(text) {
    if (!text) return '';
    const parts = String(text).split(/```/);
    let html = '';
    for (let i = 0; i < parts.length; i++) {
        if (i % 2 === 1) {
            // code fence
            const seg = parts[i];
            const nl = seg.indexOf('\n');
            const lang = nl >= 0 ? seg.slice(0, nl).trim() : '';
            const body = nl >= 0 ? seg.slice(nl + 1) : seg;
            html += `<pre><code${lang ? ` data-lang="${escapeHtml(lang)}"` : ''}>${escapeHtml(body)}</code></pre>`;
        } else {
            html += escapeHtml(parts[i]).replace(/\n/g, '<br>');
        }
    }
    return html;
}

function _imageUrl(img) {
    if (!img) return '';
    if (typeof img === 'string') return img;
    return img.url || img.src || img.data || '';
}

function _renderImages(images) {
    if (!images || !images.length) return '';
    const tiles = images
        .map(_imageUrl)
        .filter((u) => u && !u.startsWith('data:image/svg'))
        .map((u) => `<img class="message__image" src="${escapeHtml(u)}" loading="lazy" alt="">`);
    return tiles.length ? `<div class="message__images">${tiles.join('')}</div>` : '';
}

export function renderMessage(msg) {
    const el = document.createElement('div');
    el.className = 'message';
    el.dataset.role = msg.role || 'assistant';
    el.dataset.messageId = msg.id || '';
    if (msg.status === 'streaming') el.dataset.status = 'streaming';

    const bubble = document.createElement('div');
    bubble.className = 'message__bubble';
    bubble.innerHTML = tinyMarkdown(msg.content || '');
    el.appendChild(bubble);

    const imgs = _renderImages(msg.images);
    if (imgs) el.insertAdjacentHTML('beforeend', imgs);

    return el;
}

export function renderMessageList(messages) {
    const list = dom('messageList');
    if (!list) return;
    list.innerHTML = '';
    if (!messages || !messages.length) {
        const empty = document.createElement('div');
        empty.className = 'chat__empty';
        empty.textContent = 'Start typing to begin a new chat.';
        list.appendChild(empty);
        return;
    }
    const frag = document.createDocumentFragment();
    for (const m of messages) frag.appendChild(renderMessage(m));
    list.appendChild(frag);
    list.scrollTop = list.scrollHeight;
}

/** Append text to the streaming assistant bubble; create one if missing. */
export function appendChunk(text) {
    if (!text) return;
    const list = dom('messageList');
    if (!list) return;
    let el = list.querySelector('.message[data-status="streaming"]');
    if (!el) {
        el = renderMessage({ role: 'assistant', content: '', status: 'streaming' });
        list.appendChild(el);
    }
    const bubble = el.querySelector('.message__bubble');
    const prev = bubble.dataset.raw || '';
    const next = prev + text;
    bubble.dataset.raw = next;
    bubble.innerHTML = tinyMarkdown(next);
    list.scrollTop = list.scrollHeight;
}

export function finalizeStreaming(finalText, extras = {}) {
    const list = dom('messageList');
    if (!list) return;
    const el = list.querySelector('.message[data-status="streaming"]');
    if (!el) return;
    const bubble = el.querySelector('.message__bubble');
    if (typeof finalText === 'string' && finalText.length) {
        bubble.dataset.raw = finalText;
        bubble.innerHTML = tinyMarkdown(finalText);
    }
    if (extras.images && extras.images.length) {
        const html = _renderImages(extras.images);
        if (html) el.insertAdjacentHTML('beforeend', html);
    }
    delete el.dataset.status;
}

export function setTitle(title) {
    const t = dom('conversationTitle');
    if (t) t.textContent = title || '';
}
