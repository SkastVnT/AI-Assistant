/**
 * composer-controller.js — input box, attach, send/stop.
 */

import { dom } from './dom.js';
import { appState, setStatus } from './state.js';
import { streamController } from './stream-controller.js';
import { toast } from './toast.js';

const MAX_FILE_BYTES = 8 * 1024 * 1024;

function _renderChips() {
    const chips = dom('composerChips');
    if (!chips) return;
    chips.innerHTML = '';
    appState.stagedFiles.forEach((f, i) => {
        const chip = document.createElement('span');
        chip.className = 'chip';
        chip.innerHTML = `<span class="chip__name"></span><button class="chip__remove" type="button" aria-label="Remove">×</button>`;
        chip.querySelector('.chip__name').textContent = f.name;
        chip.querySelector('.chip__remove').addEventListener('click', () => {
            appState.stagedFiles.splice(i, 1);
            _renderChips();
        });
        chips.appendChild(chip);
    });
}

function _autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 240) + 'px';
}

async function _filesToImagesPayload(files) {
    const out = [];
    for (const f of files) {
        if (!f.type.startsWith('image/')) continue;
        const data = await new Promise((resolve, reject) => {
            const r = new FileReader();
            r.onload = () => resolve(r.result);
            r.onerror = reject;
            r.readAsDataURL(f);
        });
        out.push(data);
    }
    return out;
}

async function _doSend() {
    const inp = dom('composerInput');
    const text = (inp.value || '').trim();
    if (!text && !appState.stagedFiles.length) return;
    if (streamController.isStreaming()) return;

    let images = [];
    if (appState.stagedFiles.length) {
        setStatus('uploading');
        try { images = await _filesToImagesPayload(appState.stagedFiles); }
        catch (e) { toast.error('Failed to read attachment'); setStatus('idle'); return; }
        appState.stagedFiles = [];
        _renderChips();
    }
    const tools = Array.from(appState.activeTools);
    streamController.send({
        message: text,
        images,
        tools,
        conversationId: appState.currentConversationId,
    });
}

export function initComposer() {
    const input = dom('composerInput');
    const sendBtn = dom('sendBtn');
    const stopBtn = dom('stopBtn');
    const attachBtn = dom('attachFilesBtn');
    const fileInput = dom('fileInput');

    input.addEventListener('input', () => {
        _autoResize(input);
        if (appState.status === 'idle' && input.value) setStatus('composing');
        if (appState.status === 'composing' && !input.value && !appState.stagedFiles.length) setStatus('idle');
    });

    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
            e.preventDefault();
            _doSend();
        }
    });

    sendBtn.addEventListener('click', _doSend);
    stopBtn.addEventListener('click', () => streamController.stop());

    attachBtn.addEventListener('click', () => fileInput.click());
    fileInput.addEventListener('change', () => {
        const files = Array.from(fileInput.files || []);
        for (const f of files) {
            if (f.size > MAX_FILE_BYTES) { toast.warn(`${f.name} is too large (>8MB) and was skipped.`); continue; }
            appState.stagedFiles.push(f);
        }
        fileInput.value = '';
        _renderChips();
    });

    document.addEventListener('appstatechange', () => {
        const busy = streamController.isStreaming();
        sendBtn.disabled = busy;
        input.disabled = appState.status === 'uploading';
    });
}
