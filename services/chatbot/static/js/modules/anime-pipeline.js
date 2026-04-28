/**
 * anime-pipeline.js — Layered Anime Pipeline frontend module.
 *
 * Manages the pipeline modal, SSE progress display, intermediate
 * debug previews, and final result rendering.
 *
 * SSE events consumed:
 *   ap_status       — pipeline initialised
 *   ap_stage_start  — stage begun
 *   ap_stage_done   — stage completed
 *   ap_preview      — intermediate image (debug only)
 *   ap_refine       — refine loop iteration
 *   ap_result       — final image + manifest
 *   ap_error        — error (recoverable or fatal)
 *   ap_done         — stream complete sentinel
 */

const STAGES = [
    { key: 'vision_analysis',  icon: '👁️',  label: 'Vision Analysis' },
    { key: 'layer_planning',   icon: '📋',  label: 'Layer Planning' },
    { key: 'composition_pass', icon: '🎨',  label: 'Composition' },
    { key: 'structure_lock',   icon: '🔒',  label: 'Structure Lock' },
    { key: 'beauty_pass',      icon: '✨',  label: 'Beauty Pass' },
    { key: 'detection_inpaint',icon: '🎯',  label: 'YOLO Detail Fix' },
    { key: 'critique',         icon: '🔍',  label: 'Critique' },
    { key: 'upscale',          icon: '📐',  label: 'Upscale' },
];

// Off-DOM full-resolution image cache for layer cards.
//
// Earlier versions stored the full-res src directly on
// ``card.dataset.fullSrc``. When the src was a base64 PNG (composition
// pass with no /storage URL yet) that meant injecting a 2–4 MB string
// into a DOM attribute. Five layer cards × 3 MB = ~15 MB of HTML, which
// pushed the browser into "very heavy" territory and stalled the image
// viewer (every Lightbox open re-cloned the attribute).
//
// A WeakMap keyed by the card element keeps the heavy strings outside
// the serialized DOM and lets the GC drop them when the bubble is
// removed — no manual cleanup needed on Stop / new chat.
const _layerFullSrcMap = new WeakMap();

export class AnimePipeline {
    constructor() {
        /** @type {AbortController|null} */
        this._abort = null;
        this._running = false;
        this._debug = false;
        this._available = null;  // cached availability

        // F5 / tab-close orphan-job cleanup. Without this the backend
        // pipeline keeps running (and eats GPU + the 60s queue slot)
        // long after the user navigated away. We POST cancel beacons
        // for every live bubble that has a job_id but no final image.
        // Use 'pagehide' (Safari-friendly) + 'beforeunload' for parity.
        const fireOrphanCancels = () => {
            try {
                document.querySelectorAll('.ap-inline-msg').forEach(el => {
                    const jobId = el.dataset?.jobId || '';
                    const hasResult = el.querySelector('.igv2-chat-image img');
                    if (jobId && !hasResult) {
                        // sendBeacon survives page teardown; fetch with
                        // keepalive is the fallback for older browsers.
                        const payload = JSON.stringify({ job_id: jobId });
                        if (navigator.sendBeacon) {
                            navigator.sendBeacon(
                                '/api/anime-pipeline/cancel',
                                new Blob([payload], { type: 'application/json' }),
                            );
                        } else {
                            fetch('/api/anime-pipeline/cancel', {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: payload,
                                keepalive: true,
                            }).catch(() => {});
                        }
                    }
                });
            } catch (_) { /* never block unload */ }
        };
        window.addEventListener('pagehide', fireOrphanCancels);
        window.addEventListener('beforeunload', fireOrphanCancels);
    }

    // ── Modal lifecycle ─────────────────────────────────────────────

    openModal() {
        // Modal removed — redirect toolbar button to inline chat mode.
        const chatContainer = document.getElementById('chatContainer');
        if (chatContainer) {
            const prompt = window.prompt('Mô tả anime scene bạn muốn tạo:');
            if (prompt && prompt.trim()) {
                this._runInlineChat(prompt.trim(), chatContainer);
            }
            return;
        }
        // If no chat container (edge case), do nothing gracefully.
    }

    /**
     * Open the modal and auto-start generation with the given prompt.
     * Called when the user picks LOCAL from the chat image-gen dialog.
     * Runs inline in the chat (like a thinking box) — no modal popup.
     * Falls back to modal if chat container is not found.
     * @param {string} prompt
     * @param {{imageOnly?: boolean, batchSize?: number, negativePrompt?: string,
     *         continuous?: {enabled: boolean, count: number, sleepSeconds: number}}} [opts]
     */
    openModalWithPrompt(prompt, opts = {}) {
        // Prefer inline chat mode so the result lands directly in the conversation.
        const chatContainer = document.getElementById('chatContainer');
        if (chatContainer) {
            const cont = opts && opts.continuous;
            if (cont && cont.enabled && (cont.count || 0) > 1) {
                // Fire-and-forget; the loop manages its own bubbles.
                this._runContinuous(prompt, chatContainer, opts);
            } else {
                this._runInlineChat(prompt, chatContainer, opts);
            }
            return;
        }
        // Fallback: open modal
        const el = document.getElementById('animePipelineModal');
        if (!el) return;
        el.classList.add('active', 'open');
        this._resetUI();
        const promptEl = document.getElementById('apPrompt');
        if (promptEl && prompt) promptEl.value = prompt;
        const statusEl = document.getElementById('apStatus');
        if (statusEl) statusEl.textContent = '🎨 Đang khởi động pipeline…';
        this._showSection('progress');
        setTimeout(() => this.generate(), 30);
    }

    /**
     * Run the anime pipeline inline inside the chat conversation.
     * Creates an assistant message bubble with a live progress block,
     * then replaces it with the final image on completion.
     * @param {string} prompt
     * @param {HTMLElement} chatContainer
     * @param {{imageOnly?: boolean, batchSize?: number, negativePrompt?: string}} [opts]
     *   imageOnly  — when true the backend stops after composition_pass
     *                and returns N candidates (skips beauty / yolo / etc.).
     *   batchSize  — number of candidates to emit (1-6, clamped server-side).
     *                Only meaningful when imageOnly is true.
     *   negativePrompt — optional; not yet wired into the backend request
     *                schema but reserved so the choice-card payload survives
     *                the regenerate round-trip.
     */
    async _runInlineChat(prompt, chatContainer, opts = {}) {
        if (this._running) return;
        this._running = true;
        const imageOnly = !!opts.imageOnly;
        const batchSize = Math.max(1, Math.min(parseInt(opts.batchSize, 10) || 1, 6));

        const uid = Date.now().toString(36);
        const startTime = Date.now();

        // Build the inline bubble
        const bubble = this._createInlineBubble(uid, prompt);
        chatContainer.appendChild(bubble);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        // Live timer
        const timerEl = document.getElementById(`ap-timer-${uid}`);
        const timerInterval = setInterval(() => {
            if (!timerEl || !timerEl.isConnected) { clearInterval(timerInterval); return; }
            timerEl.textContent = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
        }, 200);

        const body = {
            prompt,
            preset: 'anime_quality',
            quality_mode: 'quality',
            debug: false,
            image_only: imageOnly,
            batch_size: imageOnly ? batchSize : 1,
        };

        // Pipe the character picker selection (if any) into the request.
        // Backend ``_enrich_with_character`` resolves this against the local
        // registry first, then falls back to the SAA WAI database (5149
        // entries) so long-tail characters still get fully-qualified prompts.
        try {
            const sel = window.selectedCharacter || null;
            if (sel && sel.key) {
                body.character_key = sel.key;
                if (sel.series_key) body.series_key = sel.series_key;
            } else {
                const dsKey = document.body.getAttribute('data-character-key');
                const dsSeries = document.body.getAttribute('data-series-key');
                if (dsKey) body.character_key = dsKey;
                if (dsSeries) body.series_key = dsSeries;
            }
        } catch (_) { /* picker not loaded — ignore */ }

        // Stash the run options on the bubble so the regenerate /
        // edit-and-rerun buttons in _inlineShowResult can preserve
        // image-only mode and batch size on the next round-trip
        // without the user re-opening the choice card.
        const bubbleEl = document.getElementById(`ap-inline-${uid}`);
        if (bubbleEl) {
            bubbleEl.dataset.apImageOnly = imageOnly ? '1' : '0';
            bubbleEl.dataset.apBatchSize = String(body.batch_size);
        }

        this._abort = new AbortController();
        try {
            const resp = await fetch('/api/anime-pipeline/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: this._abort.signal,
            });

            if (!resp.ok && !resp.headers.get('content-type')?.includes('text/event-stream')) {
                const err = await resp.json().catch(() => ({ error: 'Request failed' }));
                this._setInlineError(bubble, uid, err.error || `HTTP ${resp.status}`);
                return;
            }

            await this._consumeInlineSSE(resp, bubble, uid, prompt, startTime, chatContainer);

        } catch (e) {
            if (e.name === 'AbortError') return;
            this._setInlineError(bubble, uid, e.message || 'Connection lost');
        } finally {
            clearInterval(timerInterval);
            this._running = false;
            this._abort = null;
        }
    }

    /**
     * Continuous-generation loop. Runs `_runInlineChat` repeatedly with
     * a fresh random WAI character swapped into the prompt on every
     * iteration. Sleeps between iterations. Stops early when the user
     * clicks the Stop button on the most recent bubble (which sets
     * this._continuousCancelled via the Stop handler below).
     *
     * @param {string} prompt
     * @param {HTMLElement} chatContainer
     * @param {{imageOnly?: boolean, batchSize?: number,
     *          continuous: {enabled: boolean, count: number,
     *                       sleepSeconds: number}}} opts
     */
    async _runContinuous(prompt, chatContainer, opts) {
        const cont = opts.continuous || {};
        const total = Math.max(2, Math.min(parseInt(cont.count, 10) || 2, 50));
        const sleepMs = Math.max(0, (parseFloat(cont.sleepSeconds) || 0) * 1000);
        const baseOpts = { imageOnly: !!opts.imageOnly, batchSize: opts.batchSize || 1 };

        // Reset cancel flag and exclude-list at loop start.
        this._continuousCancelled = false;
        this._continuousExcludes = [];

        // Render a small banner so the user sees the loop is active.
        const banner = document.createElement('div');
        banner.className = 'message assistant ap-continuous-banner';
        banner.style.cssText = 'padding:6px 10px; font-size:12px; color:var(--text-muted,#888);';
        banner.innerHTML = `<div class="message__body"><div class="message-content">🔁 Tạo liên tục: <strong class="ap-cont-progress">1</strong>/${total} · nghỉ ${cont.sleepSeconds || 0}s · đổi nhân vật mỗi lượt</div></div>`;
        chatContainer.appendChild(banner);
        const progressEl = banner.querySelector('.ap-cont-progress');

        let currentPrompt = prompt;

        for (let i = 0; i < total; i++) {
            if (this._continuousCancelled) break;
            if (progressEl) progressEl.textContent = String(i + 1);

            // After the first iteration, swap the character in the prompt.
            if (i > 0) {
                try {
                    const swapResp = await fetch('/api/characters/swap-in-prompt', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            prompt: prompt,
                            exclude: this._continuousExcludes,
                        }),
                    });
                    const swapData = await swapResp.json().catch(() => ({}));
                    if (swapData && swapData.ok && swapData.prompt) {
                        currentPrompt = swapData.prompt;
                        const newTag = swapData.character && swapData.character.tag;
                        if (newTag) this._continuousExcludes.push(newTag);
                        const display = (swapData.character && swapData.character.display_name) || newTag || '';
                        const note = document.createElement('div');
                        note.className = 'message assistant ap-continuous-swap';
                        note.style.cssText = 'padding:4px 10px; font-size:12px; color:var(--text-muted,#888);';
                        note.innerHTML = `<div class="message__body"><div class="message-content">↳ Lượt ${i + 1}: nhân vật mới · <strong>${display}</strong> <code style="font-size:11px;">${newTag || ''}</code></div></div>`;
                        chatContainer.appendChild(note);
                        chatContainer.scrollTop = chatContainer.scrollHeight;
                    }
                } catch (err) {
                    // Swap failed — keep the original prompt and continue.
                    // eslint-disable-next-line no-console
                    console.warn('[anime-pipeline] swap-in-prompt failed:', err);
                }
            }

            if (this._continuousCancelled) break;

            // Run one full pipeline. _runInlineChat resolves when SSE EOF.
            try {
                await this._runInlineChat(currentPrompt, chatContainer, baseOpts);
            } catch (err) {
                // eslint-disable-next-line no-console
                console.warn('[anime-pipeline] continuous iteration error:', err);
            }

            if (this._continuousCancelled) break;

            // Sleep between iterations (skipped after the last one).
            if (i < total - 1 && sleepMs > 0) {
                if (progressEl) progressEl.textContent = `${i + 1} (nghỉ ${cont.sleepSeconds}s)`;
                await new Promise((r) => setTimeout(r, sleepMs));
            }
        }

        // Final banner update.
        if (banner.isConnected) {
            const tail = this._continuousCancelled ? '⏹ đã ngưng' : '✅ hoàn thành';
            const body = banner.querySelector('.message-content');
            if (body) body.innerHTML = `🔁 Tạo liên tục: ${tail}`;
        }
        this._continuousCancelled = false;
    }

    /** Build the initial inline pipeline message bubble.
     *
     * Layout (ChatGPT-style):
     *   ┌─────────────────────────────────────────┐
     *   │ 🎨 Finalizing image adjustments  ›      │  ← reasoning pill
     *   │   (expanded text · stage chips inside)  │
     *   ├─────────────────────────────────────────┤
     *   │ Đang tạo · Layer 1 · Bố cục   [thumb]  │  ← layer gallery
     *   │ Đang tạo · Layer 2 · Khoá nét [thumb]  │     (grows as
     *   │ Đang tạo · Layer 3 · Tô màu   [thumb]  │      previews
     *   │ Đang tạo · Layer 4 · Tinh chỉnh [thumb] │      arrive)
     *   └─────────────────────────────────────────┘
     */
    _createInlineBubble(uid, prompt) {
        const stagesHtml = STAGES.map(s => `
            <div class="ap-stage-item pending" data-ap-stage="${s.key}" id="ap-stage-${uid}-${s.key}">
                <span class="ap-stage-icon">${s.icon}</span>
                <span class="ap-stage-label">${s.label}</span>
                <span class="ap-stage-time"></span>
            </div>`).join('');

        const div = document.createElement('div');
        div.className = 'message assistant ap-inline-msg';
        div.id = `ap-inline-${uid}`;
        div.setAttribute('data-ap-prompt', prompt);
        div.innerHTML = `
            <div class="message__avatar message__avatar--agent">
                <img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false">
            </div>
            <div class="message__body">
                <div class="message-content">
                    <details class="ap-inline-progress ap-reasoning-pill" open>
                        <summary class="ap-inline-summary ap-reasoning-summary">
                            <span class="ap-reasoning-chevron">›</span>
                            <div class="thinking-pill__dots">
                                <span></span><span></span><span></span>
                            </div>
                            <span class="ap-inline-label" id="ap-headline-${uid}">Finalizing image adjustments</span>
                            <span class="ap-inline-timer" id="ap-timer-${uid}">0.0s</span>
                            <button type="button"
                                    class="ap-inline-stop-btn"
                                    id="ap-stop-${uid}"
                                    style="margin-left:8px; padding:2px 10px; font-size:12px; border:1px solid var(--border); background:var(--bg-secondary,var(--bg)); color:var(--text); border-radius:6px; cursor:pointer;"
                                    title="Ngưng pipeline và xuất ảnh hiện tại">⏹ Ngưng & xuất ảnh</button>
                        </summary>
                        <div class="ap-reasoning-body">
                            <div class="ap-inline-current ap-reasoning-text" id="ap-current-${uid}">Khởi động…</div>
                            <div class="ap-inline-stages" id="ap-stages-${uid}">${stagesHtml}</div>
                        </div>
                    </details>
                    <div class="ap-layers-gallery" id="ap-layers-${uid}" style="display:none; margin-top:10px;"></div>
                </div>
            </div>`;

        // Wire the Stop button. The Stop button must feel decisive:
        //   1. POST /cancel so the backend bails at the next checkpoint.
        //   2. Mark the bubble as "user-cancelled" via dataset.apHardStop.
        //   3. Schedule an 8-second hard fallback: if neither ap_cancelled
        //      nor ap_result has arrived by then (e.g. critique stuck on a
        //      blocked vision API call, or SSE socket dropped), force the
        //      bubble into a finalized "Đã ngưng" state using the most
        //      recent layer thumbnail. This guarantees the UI never sits
        //      on "⏳ Đang ngưng…" forever — which is the exact symptom
        //      the user reported.
        const stopBtn = div.querySelector(`#ap-stop-${uid}`);
        if (stopBtn) {
            stopBtn.addEventListener('click', (ev) => {
                ev.preventDefault();
                ev.stopPropagation();
                const jobId = div.dataset.jobId || '';
                stopBtn.disabled = true;
                stopBtn.textContent = '⏳ Đang ngưng…';
                div.dataset.apHardStop = '1';

                // Also break out of any active continuous-generation loop
                // so the next iteration does not start. The flag is
                // checked between iterations and around the sleep.
                this._continuousCancelled = true;

                // Log so the console makes it obvious whether Stop
                // actually fired the cancel requests. Users previously
                // reported "ComfyUI kept running after Stop" and the
                // only way to tell whether /cancel ever hit the server
                // was via uvicorn access logs.
                try {
                    // eslint-disable-next-line no-console
                    console.log('[anime-pipeline] Stop clicked, job_id=%s', jobId || '(unknown)');
                } catch (_) { /* noop */ }

                // 1. Abort the SSE reader so the browser stops listening
                //    to more server frames. Without this, even after the
                //    server cancels, stale SSE frames keep updating the UI.
                try { this._abort?.abort?.(); } catch (_) { /* noop */ }

                // 2. POST /cancel with the specific job_id when we have one.
                //    Fire-and-forget; the nuclear /cancel-all below is the
                //    belt-and-suspenders that guarantees the server halts.
                if (jobId) {
                    fetch('/api/anime-pipeline/cancel', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ job_id: jobId }),
                        keepalive: true,
                    }).catch(() => { /* noop */ });
                }

                // 3. Nuclear cancel-all — always fires, regardless of
                //    whether we captured a job_id. This was added after
                //    users observed the pipeline keep running because
                //    the Stop handler silently returned when jobId was
                //    missing from dataset. Now the server ALWAYS gets
                //    a kill signal for every in-flight pipeline job.
                fetch('/api/anime-pipeline/cancel-all', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: '{}',
                    keepalive: true,
                }).catch(() => { /* noop */ });

                // Hard fallback. The handler is no-op if the bubble has
                // already been swapped to a result by the normal SSE path.
                setTimeout(() => {
                    if (!document.body.contains(div)) return;
                    if (div.dataset.apFinalized === '1') return;
                    this._forceFinalizeAsCancelled(div, uid);
                }, 8000);
            });
        }
        return div;
    }

    /** Forcefully finalize the bubble as "stopped + exported best layer"
     *  when the backend stops responding after Stop is pressed. Uses the
     *  most recent layer thumbnail (gallery card) as the export.
     */
    _forceFinalizeAsCancelled(bubble, uid) {
        // Pick the freshest layer card and prefer its FULL-resolution
        // source over the 64x64 thumbnail. Earlier versions used
        // ``lastThumb.src`` which is only the cropped preview, so the
        // "Đã ngưng" output came out pixelated. ``card.dataset.fullSrc``
        // is set by ``_inlineAddLayerPreview`` to the local /storage URL
        // when available, falling back to the full-res base64.
        const gallery = document.getElementById(`ap-layers-${uid}`);
        const cards = gallery ? gallery.querySelectorAll('.ap-layer-card') : [];
        const lastCard = cards.length ? cards[cards.length - 1] : null;
        const lastThumb = lastCard ? lastCard.querySelector('.ap-layer-thumb') : null;
        const imgSrc = (lastCard && (_layerFullSrcMap.get(lastCard) || lastCard.dataset.fullSrc)) || lastThumb?.src || '';

        const details = bubble.querySelector('.ap-inline-progress');
        if (details) {
            details.open = false;
            const summary = details.querySelector('.ap-inline-summary');
            if (summary) {
                const dots = summary.querySelector('.thinking-pill__dots');
                if (dots) dots.remove();
                const stop = summary.querySelector('.ap-inline-stop-btn');
                if (stop) stop.style.display = 'none';
                const label = summary.querySelector('.ap-inline-label');
                if (label) label.textContent = '⏸ Đã ngưng — đang dùng layer cuối làm output';
            }
        }
        bubble.dataset.apFinalized = '1';
        bubble.dataset.apCancelled = '1';

        // Surface the freshest preview as the "result" image so the user
        // sees what they got.
        if (imgSrc && !bubble.querySelector('.igv2-chat-image img')) {
            const msgContent = bubble.querySelector('.message-content');
            if (msgContent) {
                const wrap = document.createElement('div');
                wrap.className = 'igv2-chat-image';
                wrap.style.cssText = 'margin-top:10px;';
                wrap.innerHTML = `
                    <img src="${imgSrc}" data-igv2-open="${imgSrc}"
                         style="max-width:100%; border-radius:10px; cursor:pointer;"
                         alt="Layer cuối — đã ngưng">
                    <div style="margin-top:6px; font-size:11px; opacity:.6;">
                        Output từ layer cuối cùng được tạo trước khi ngưng.
                    </div>`;
                wrap.querySelector('img').addEventListener('click', () => {
                    // window.openImagePreview expects an <img> element. Pass
                    // the element itself so the lightbox can read .src and
                    // any data attributes (download filename, etc.).
                    const el = wrap.querySelector('img');
                    if (window.openImagePreview && el) {
                        window.openImagePreview(el);
                    }
                });
                msgContent.appendChild(wrap);
            }
        }
    }

    /** Append a new layer card to the gallery, or update the existing one
     *  for the same layer slot. Cards show "Đang tạo · Layer N · {label}"
     *  while the stage is running and animate to "✓ Đã xong" once a
     *  non-pending preview arrives for the same slot or a later layer
     *  starts.
     *
     *  Backend emits two ap_preview frames per layer stage:
     *    1. on stage_start — { pending: true, local_url: <prev layer> }
     *    2. on stage_done  — { local_url: <new image for this stage> }
     *  The same slotId is reused so the card refreshes in place.
     */
    _inlineAddLayerPreview(uid, data) {
        const gallery = document.getElementById(`ap-layers-${uid}`);
        if (!gallery) return;
        gallery.style.display = '';

        const layerNum = data.layer_num || (gallery.children.length + 1);
        const layerLabel = data.layer_label || data.label || data.stage || `Layer ${layerNum}`;
        const slotId = `ap-layer-${uid}-${data.stage || layerNum}`;
        const isPending = data.pending === true;
        // Prefer inline thumb b64 — the /storage/images route stalls
        // while the SSE worker is busy serving the pipeline stream, so
        // a normal <img src="/storage/..."> would never load.
        // local_url is still kept as the click-to-enlarge target.
        const thumbSrc = data.thumb_b64
            ? 'data:image/jpeg;base64,' + data.thumb_b64
            : (data.image_b64 ? 'data:image/png;base64,' + data.image_b64 : data.local_url || '');
        const fullSrc = data.local_url
            || (data.image_b64 ? 'data:image/png;base64,' + data.image_b64 : thumbSrc);

        let card = document.getElementById(slotId);
        if (!card) {
            card = document.createElement('div');
            card.id = slotId;
            card.className = 'ap-layer-card';
            card.style.cssText = (
                'display:flex; align-items:center; gap:10px; padding:8px 10px; ' +
                'margin-bottom:6px; border:1px solid var(--border); border-radius:10px; ' +
                'background:var(--bg-secondary,var(--bg)); cursor:pointer; ' +
                'transition:background .15s ease;'
            );
            card.innerHTML = `
                <div class="ap-layer-thumb-wrap" style="position:relative; width:64px; height:64px; flex:none;">
                    <img class="ap-layer-thumb" alt="Layer ${layerNum}"
                         style="width:64px; height:64px; object-fit:cover; border-radius:6px; display:block;">
                    <div class="ap-layer-spinner" style="position:absolute; inset:0; display:flex; align-items:center; justify-content:center; background:rgba(0,0,0,.25); border-radius:6px; pointer-events:none;">
                        <div class="thinking-pill__dots" style="--dot-color:#fff;">
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                </div>
                <div class="ap-layer-meta" style="flex:1; min-width:0;">
                    <div class="ap-layer-headline" style="font-size:13px; font-weight:600; color:var(--text);">
                        <span class="ap-layer-status" style="opacity:.85;">Đang tạo</span>
                        <span style="opacity:.45; margin:0 4px;">·</span>
                        <span class="ap-layer-name">Layer ${layerNum} · ${layerLabel}</span>
                    </div>
                    <div class="ap-layer-sub" style="font-size:11px; opacity:.55; margin-top:2px;">
                        ${data.stage || ''}
                    </div>
                </div>`;
            card.addEventListener('click', () => {
                // Use the stored full-resolution URL when available; fall
                // back to the current thumb src otherwise.
                const thumb = card.querySelector('.ap-layer-thumb');
                const full = _layerFullSrcMap.get(card) || card.dataset.fullSrc || thumb?.src;
                if (!full) return;
                // window.openImagePreview wants an <img> element. Build a
                // detached one that points at the full-res source so the
                // lightbox does not get the 64x64 cropped thumbnail.
                const tmp = document.createElement('img');
                tmp.src = full;
                tmp.alt = thumb?.alt || 'Layer';
                if (window.openImagePreview) {
                    window.openImagePreview(tmp);
                }
            });
            gallery.appendChild(card);
        }
        // Refresh thumbnail and click-target when an image is supplied.
        // A pending frame may arrive without any image (b64 + persist
        // both failed) — in that case keep whatever thumb is already
        // there.
        if (thumbSrc) {
            const thumb = card.querySelector('.ap-layer-thumb');
            if (thumb) thumb.src = thumbSrc;
        }
        if (fullSrc) {
            // Heavy base64 strings live in the WeakMap, NOT the DOM.
            // Light /storage URLs can also live there — uniform access.
            _layerFullSrcMap.set(card, fullSrc);
            // Keep dataset only when src is a short URL (not base64),
            // so devtools / right-click "copy URL" still works without
            // bloating the HTML attribute when the src is multi-MB.
            if (!fullSrc.startsWith('data:')) {
                card.dataset.fullSrc = fullSrc;
            } else if (card.dataset.fullSrc) {
                delete card.dataset.fullSrc;
            }
        }
        // Promote the previous layer card to ✓ Đã xong as soon as we
        // start drawing the next one. Also flip THIS card to done when
        // the non-pending preview arrives.
        const status = card.querySelector('.ap-layer-status');
        const spinner = card.querySelector('.ap-layer-spinner');
        if (isPending) {
            // Mark every prior card as done.
            let prev = card.previousElementSibling;
            while (prev) {
                const ps = prev.querySelector('.ap-layer-status');
                const psp = prev.querySelector('.ap-layer-spinner');
                if (ps && ps.textContent === 'Đang tạo') {
                    ps.textContent = '✓ Đã xong';
                    ps.style.color = 'var(--accent, #4ade80)';
                }
                if (psp) psp.style.display = 'none';
                prev = prev.previousElementSibling;
            }
            if (status) {
                status.textContent = 'Đang tạo';
                status.style.color = '';
            }
            if (spinner) spinner.style.display = '';
        } else {
            // Final preview for this slot: stop the spinner, mark done.
            if (status) {
                status.textContent = '✓ Đã xong';
                status.style.color = 'var(--accent, #4ade80)';
            }
            if (spinner) spinner.style.display = 'none';
        }
    }

    /** Consume SSE stream for inline mode, updating the bubble DOM. */
    async _consumeInlineSSE(resp, bubble, uid, prompt, startTime, chatContainer) {
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentEvent = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';

            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    currentEvent = line.slice(7).trim();
                } else if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        this._handleInlineEvent(currentEvent, data, bubble, uid, prompt, startTime, chatContainer);
                    } catch { /* ignore malformed */ }
                }
            }
        }
    }

    /** Dispatch an SSE event to the inline bubble updaters. */
    _handleInlineEvent(event, data, bubble, uid, prompt, startTime, chatContainer) {
        switch (event) {
            case 'ap_status':
                // Capture job_id from the first status frame so the
                // Stop button knows what to cancel. Reveal the button
                // only after the backend has assigned an id.
                if (data && data.job_id && !bubble.dataset.jobId) {
                    bubble.dataset.jobId = data.job_id;
                    const stopBtn = document.getElementById(`ap-stop-${uid}`);
                    if (stopBtn) stopBtn.style.display = '';
                }
                this._inlineSetCurrent(uid, data.message || '');
                break;
            case 'ap_cancelled': {
                // Server acknowledged Stop & Export. Mark the bubble
                // as cancelled; the partial image will arrive in the
                // following ap_result frame and _inlineShowResult will
                // pick up the cancelled flag from the dataset.
                bubble.dataset.apCancelled = '1';
                bubble.dataset.apCancelStage = data.stage || '';
                this._inlineSetCurrent(uid, `⏸ Đã ngưng tại ${data.stage || 'pipeline'} — đang xuất ảnh hiện tại…`);
                const stopBtn = document.getElementById(`ap-stop-${uid}`);
                if (stopBtn) stopBtn.style.display = 'none';
                break;
            }
            case 'ap_layer_plan':
                this._inlineShowLayerChips(uid, data);
                break;
            case 'ap_preview':
                // ChatGPT-style: live "Layer N" thumbnail card. Backend
                // emits this for composition_pass / structure_lock /
                // beauty_pass / detection_inpaint with a local_url.
                this._inlineAddLayerPreview(uid, data);
                break;
            case 'ap_stage_start': {
                this._inlineSetStage(uid, data.stage, 'active');
                // _inlineSetCurrent updates both the reasoning body text
                // and the ChatGPT-style headline pill (.ap-inline-label).
                this._inlineSetCurrent(uid, data.label || data.stage);
                break;
            }
            case 'ap_stage_done': {
                this._inlineSetStage(uid, data.stage, 'done');
                if (data.latency_ms) {
                    const row = document.getElementById(`ap-stage-${uid}-${data.stage}`);
                    if (row) row.querySelector('.ap-stage-time').textContent =
                        `${(data.latency_ms / 1000).toFixed(1)}s`;
                }
                // Show rich character card when character_research completes.
                if (data.stage === 'character_research') {
                    this._inlineShowCharacterCard(uid, data);
                }
                break;
            }
            case 'ap_critique_result': {
                const row = document.getElementById(`ap-stage-${uid}-critique`);
                if (!row) break;
                const passed = data.passed;
                const scoreText = `${data.score}/10 ${passed ? '\u2705' : '\u21a9\ufe0f'}`;
                let badge = row.querySelector('.ap-score-badge');
                if (!badge) {
                    badge = document.createElement('span');
                    badge.className = 'ap-score-badge';
                    const timeEl = row.querySelector('.ap-stage-time');
                    if (timeEl) row.insertBefore(badge, timeEl);
                    else row.appendChild(badge);
                }
                badge.textContent = scoreText;
                badge.className = `ap-score-badge ${passed ? 'ap-score-pass' : 'ap-score-fail'}`;
                const issues = data.issues || [];
                if (issues.length) badge.title = issues.slice(0, 3).join(' \u00b7 ');
                break;
            }
            case 'ap_refine': {
                const round = data.round || 1;
                // Reset beauty_pass row for the new round
                const bpRow = document.getElementById(`ap-stage-${uid}-beauty_pass`);
                if (bpRow) {
                    bpRow.classList.remove('done', 'error', 'active');
                    bpRow.classList.add('pending');
                    const lbl = bpRow.querySelector('.ap-stage-label');
                    if (lbl) lbl.textContent = `Beauty Pass (Round ${round + 1})`;
                    const tEl = bpRow.querySelector('.ap-stage-time');
                    if (tEl) tEl.textContent = '';
                }
                // Reset critique row
                const crRow = document.getElementById(`ap-stage-${uid}-critique`);
                if (crRow) {
                    crRow.classList.remove('done', 'error', 'active');
                    crRow.classList.add('pending');
                    crRow.querySelector('.ap-score-badge')?.remove();
                }
                this._inlineSetCurrent(uid, `\uD83D\uDD04 Refinement round ${round + 1}/${(data.max_rounds || 1) + 1}\u2026`);
                break;
            }
            case 'ap_refine_reasoning': {
                // Show reasoning for why refine/restart happened
                const reason = data.reason || '';
                const worst = (data.worst_dimensions || []).map(d => `${d.name}:${d.score}`).join(', ');
                const detail = worst ? `${reason} [${worst}]` : reason;
                this._inlineSetCurrent(uid, `🧠 ${detail}`);
                break;
            }
            case 'ap_full_restart': {
                // Full restart — reset all beauty/critique rows
                const bpR = document.getElementById(`ap-stage-${uid}-beauty_pass`);
                if (bpR) {
                    bpR.classList.remove('done', 'error', 'active');
                    bpR.classList.add('pending');
                    const lbl = bpR.querySelector('.ap-stage-label');
                    if (lbl) lbl.textContent = `Beauty Pass (Restart #${data.restart_num || 1})`;
                    const tEl = bpR.querySelector('.ap-stage-time');
                    if (tEl) tEl.textContent = '';
                }
                const crR = document.getElementById(`ap-stage-${uid}-critique`);
                if (crR) {
                    crR.classList.remove('done', 'error', 'active');
                    crR.classList.add('pending');
                    crR.querySelector('.ap-score-badge')?.remove();
                }
                this._inlineSetCurrent(uid, `🔁 Full restart #${data.restart_num || 1}: ${data.reason || 'score stagnant'}`);
                break;
            }
            case 'ap_result':
                this._inlineShowResult(bubble, uid, data, prompt, startTime, chatContainer);
                break;
            case 'ap_error':
                if (!data.recoverable) {
                    this._setInlineError(bubble, uid, data.error || 'Pipeline thất bại');
                } else {
                    if (data.stage) {
                        this._inlineSetStage(uid, data.stage, 'error');
                    }
                    this._inlineSetCurrent(uid, `⚠️ ${data.stage || ''}: ${data.error}`);
                }
                break;
        }
    }

    _inlineSetStage(uid, stageKey, state) {
        const row = document.getElementById(`ap-stage-${uid}-${stageKey}`);
        if (!row) return;
        row.classList.remove('pending', 'active', 'done', 'error');
        row.classList.add(state);
    }

    /** Inject pass chips into the layer_planning stage row. */
    _inlineShowLayerChips(uid, data) {
        const row = document.getElementById(`ap-stage-${uid}-layer_planning`);
        if (!row) return;
        // Remove any existing chips
        row.querySelector('.ap-layer-chips')?.remove();

        const passes = data.passes || [];
        if (!passes.length) return;

        const chips = passes.map(p => {
            const denoiseLabel = p.denoise < 1.0 ? ` ·${p.denoise}` : '';
            return `<span class="ap-layer-chip" title="${p.name}: ${p.steps} steps${denoiseLabel}">${p.icon} ${p.name}</span>`;
        });

        const extra = data.total_passes > passes.length
            ? `<span class="ap-layer-chip ap-layer-chip--dim">+${data.total_passes - passes.length}</span>`
            : '';

        const resChip = data.resolution
            ? `<span class="ap-layer-chip ap-layer-chip--res">${data.resolution}</span>`
            : '';

        const wrapper = document.createElement('div');
        wrapper.className = 'ap-layer-chips';
        wrapper.innerHTML = chips.join('') + extra + resChip;

        // Insert before the time span
        const timeEl = row.querySelector('.ap-stage-time');
        if (timeEl) {
            row.insertBefore(wrapper, timeEl);
        } else {
            row.appendChild(wrapper);
        }
    }

    /**
     * Render a "cực xịn" character research card right under the
     * character_research stage row.
     *
     * Shows:
     *   • 48×48 thumbnail (from SAA wai_character_thumbs.json when available)
     *   • display_name + series
     *   • provenance badge — "SAA DB", "alias table", "web", etc
     *   • confidence bar (0–1) with a colored gradient
     *
     * This method is idempotent — calling twice replaces the previous card.
     */
    _inlineShowCharacterCard(uid, data) {
        const row = document.getElementById(`ap-stage-${uid}-character_research`);
        if (!row) return;

        // Nothing to show when no character was detected.
        if (data.skipped || !data.character) return;

        const cardId = `ap-char-card-${uid}`;
        document.getElementById(cardId)?.remove();

        const card = document.createElement('div');
        card.className = 'ap-character-card';
        card.id = cardId;

        const aliasSource = data.alias_source || 'unknown';
        const sourceLabel = {
            alias_table: 'Alias Table',
            saa_wai_db:  'SAA DB (5149)',
            civitai:     'CivitAI',
            web:         'Web',
            unknown:     'Auto',
        }[aliasSource] || aliasSource;
        const sourceColor = {
            alias_table: '#68d391',
            saa_wai_db:  '#8ab4ff',
            civitai:     '#b794f4',
            web:         '#f6e05e',
        }[aliasSource] || '#999';

        const conf = Math.max(0, Math.min(1, Number(data.confidence) || 0));
        const confPct = Math.round(conf * 100);
        const confColor = conf >= 0.8 ? '#68d391' : conf >= 0.5 ? '#f6e05e' : '#ff6b6b';

        // Thumbnail: prefer SAA DB data URL; hide element when none.
        const thumbHtml = data.saa_thumbnail
            ? `<img class="ap-char-thumb" src="${data.saa_thumbnail}" alt="${data.character}">`
            : `<div class="ap-char-thumb ap-char-thumb--placeholder">👤</div>`;

        const charTag = data.character_tag || '';
        const tagHtml = charTag
            ? `<code class="ap-char-tag" title="Danbooru tag">${charTag}</code>`
            : '';

        const refsHtml = data.ref_images_count
            ? `<span class="ap-char-meta-item" title="Reference images">🖼 ${data.ref_images_count}</span>`
            : '';
        const idTagsHtml = data.identity_tags_count
            ? `<span class="ap-char-meta-item" title="Identity tags">🏷 ${data.identity_tags_count}</span>`
            : '';
        const cachedHtml = data.cached
            ? `<span class="ap-char-meta-item" title="Loaded from local cache">⚡ cached</span>`
            : '';

        card.innerHTML = `
            <div class="ap-char-card__left">${thumbHtml}</div>
            <div class="ap-char-card__body">
                <div class="ap-char-card__head">
                    <span class="ap-char-name">${data.character}</span>
                    <span class="ap-char-source-badge" style="background:${sourceColor}22;color:${sourceColor};border:1px solid ${sourceColor}55;">${sourceLabel}</span>
                </div>
                <div class="ap-char-card__sub">
                    ${data.series ? `<span class="ap-char-series">${data.series}</span>` : ''}
                    ${tagHtml}
                </div>
                <div class="ap-char-confbar" title="Confidence ${confPct}%">
                    <div class="ap-char-confbar__fill" style="width:${confPct}%;background:${confColor};"></div>
                    <span class="ap-char-confbar__label">${confPct}%</span>
                </div>
                <div class="ap-char-card__meta">${refsHtml}${idTagsHtml}${cachedHtml}</div>
            </div>
        `;

        // Insert after the character_research stage row.
        row.insertAdjacentElement('afterend', card);

        // Lazy-inject card styles only once.
        if (!document.getElementById('ap-character-card-styles')) {
            const style = document.createElement('style');
            style.id = 'ap-character-card-styles';
            style.textContent = `
.ap-character-card {
  display: flex; gap: 10px; align-items: stretch;
  margin: 6px 0 8px 22px; padding: 8px 10px;
  background: linear-gradient(135deg, rgba(138,180,255,0.08), rgba(183,148,244,0.08));
  border: 1px solid rgba(138,180,255,0.25);
  border-radius: 10px;
  font-size: 12px;
}
.ap-char-card__left { flex: 0 0 auto; display: flex; align-items: center; }
.ap-char-thumb {
  width: 48px; height: 48px; border-radius: 8px; object-fit: cover;
  border: 1px solid rgba(255,255,255,0.15);
  background: rgba(0,0,0,0.3);
}
.ap-char-thumb--placeholder {
  display: flex; align-items: center; justify-content: center;
  font-size: 24px; color: #888;
}
.ap-char-card__body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.ap-char-card__head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.ap-char-name { font-weight: 600; color: var(--text, #eee); }
.ap-char-source-badge {
  font-size: 10px; font-weight: 600; padding: 1px 6px;
  border-radius: 10px; letter-spacing: 0.3px;
}
.ap-char-card__sub { display: flex; gap: 8px; align-items: center; font-size: 11px; color: var(--text-muted, #aaa); }
.ap-char-series { font-style: italic; }
.ap-char-tag {
  font-family: ui-monospace, monospace; font-size: 10px;
  padding: 1px 5px; border-radius: 3px;
  background: rgba(0,0,0,0.35); color: #8ab4ff;
}
.ap-char-confbar {
  position: relative; height: 6px; border-radius: 3px;
  background: rgba(255,255,255,0.08); overflow: hidden; margin-top: 2px;
}
.ap-char-confbar__fill { height: 100%; transition: width 250ms ease; }
.ap-char-confbar__label {
  position: absolute; right: 4px; top: -14px;
  font-size: 10px; color: var(--text-muted, #aaa);
  font-variant-numeric: tabular-nums;
}
.ap-char-card__meta { display: flex; gap: 10px; font-size: 10px; color: var(--text-muted, #888); }
.ap-char-meta-item { display: inline-flex; align-items: center; gap: 2px; }
`;
            document.head.appendChild(style);
        }
    }

    _inlineSetCurrent(uid, text) {
        const el = document.getElementById(`ap-current-${uid}`);
        if (el) el.textContent = text;
        const bubble = document.getElementById(`ap-inline-${uid}`);
        const label = bubble?.querySelector('.ap-inline-label');
        if (label) label.textContent = text;
    }

    /** Replace progress block with the final image result. */
    _inlineShowResult(bubble, uid, data, prompt, startTime, chatContainer) {
        const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
        const wasCancelled = bubble.dataset.apCancelled === '1';
        const cancelStage = bubble.dataset.apCancelStage || '';
        // Disarm the Stop hard-fallback timer set in _createInlineBubble.
        bubble.dataset.apFinalized = '1';
        bubble.dataset.apState = wasCancelled ? 'cancelled' : 'done';

        // Mark every still-pending layer card as done (final stage emitted
        // before the bubble swap; nothing else will refresh them).
        const gallery = document.getElementById(`ap-layers-${uid}`);
        if (gallery) {
            gallery.querySelectorAll('.ap-layer-status').forEach(el => {
                if (el.textContent === 'Đang tạo') {
                    el.textContent = '✓ Đã xong';
                    el.style.color = 'var(--accent, #4ade80)';
                }
            });
        }
        // Prefer the saved local URL (lighter than base64 in DOM); fall back to base64
        const imgSrc = data.local_url
            ? data.local_url
            : (data.image_b64 ? 'data:image/png;base64,' + data.image_b64 : null);
        const downloadSrc = data.image_b64
            ? 'data:image/png;base64,' + data.image_b64
            : imgSrc;
        const jobId = data.job_id || uid;
        const promptAttr = prompt.replace(/"/g, '&quot;');

        // Close the details and update the summary label to "done"
        const details = bubble.querySelector('.ap-inline-progress');
        if (details) {
            details.open = false;
            const summary = details.querySelector('.ap-inline-summary');
            if (summary) {
                if (wasCancelled) {
                    const stageLabel = cancelStage
                        ? ` (ngưng tại ${cancelStage})`
                        : '';
                    summary.innerHTML = `
                        <span class="ap-inline-done-icon">⏸</span>
                        <span class="ap-inline-label">Đã ngưng — ảnh hiện tại · ${elapsed}s${stageLabel}</span>`;
                } else {
                    summary.innerHTML = `
                        <span class="ap-inline-done-icon">🎨</span>
                        <span class="ap-inline-label">✅ Anime Pipeline · ${elapsed}s</span>`;
                }
            }
        }

        if (imgSrc) {
            // Append the result image after the details block
            const msgContent = bubble.querySelector('.message-content');
            const resultDiv = document.createElement('div');
            const headerLabel = wasCancelled
                ? `⏸ Anime Pipeline (đã ngưng) · ${elapsed}s`
                : `🎨 Anime Pipeline · ${elapsed}s`;

            // Recover the run options so regenerate can stay in the
            // same mode (image-only + batch size). Fallback to defaults
            // when the dataset was lost (older bubbles, edge cases).
            const wasImageOnly = bubble.dataset.apImageOnly === '1' || !!data.image_only;
            const replayBatchSize = parseInt(bubble.dataset.apBatchSize, 10)
                || data.batch_count || 1;

            // Image-only batch mode: render every candidate as a
            // clickable thumb in a responsive grid. Each opens the
            // existing lightbox (window.openImagePreview) at full
            // resolution. Falls back to the single-image layout when
            // ``data.images`` is missing (regular pipeline result).
            const galleryItems = Array.isArray(data.images) ? data.images : [];
            const hasGallery = wasImageOnly && galleryItems.length > 1;

            let mediaHtml;
            if (hasGallery) {
                const tiles = galleryItems.map((g, i) => {
                    const src = g.local_url
                        ? g.local_url
                        : (g.image_b64 ? 'data:image/png;base64,' + g.image_b64 : '');
                    if (!src) return '';
                    return `<div class="ap-batch-tile" style="position:relative;">
                        <img src="${src}" alt="Anime Pipeline candidate ${i + 1}" data-igv2-open="${src}" style="width:100%;height:auto;display:block;border-radius:8px;cursor:zoom-in;">
                        <span class="ap-batch-tile-num" style="position:absolute;top:6px;left:6px;background:rgba(0,0,0,0.6);color:#fff;font-size:11px;padding:2px 6px;border-radius:4px;">#${i + 1}</span>
                    </div>`;
                }).join('');
                mediaHtml = `<div class="ap-batch-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:8px;">${tiles}</div>`;
            } else {
                mediaHtml = `<img src="${imgSrc}" alt="Anime Pipeline result" data-igv2-open="${imgSrc}">`;
            }

            const metaSuffix = hasGallery
                ? ` · ${galleryItems.length} ảnh`
                : (data.local_url ? ' · 💾 saved' : '');

            resultDiv.innerHTML = `
                <div class="igv2-chat-image" data-prompt="${promptAttr}">
                    ${mediaHtml}
                    <div class="igv2-chat-meta">${headerLabel}${metaSuffix}</div>
                    <div class="ap-inline-result-btns">
                        <button class="ap-inline-btn" data-action="download" data-job="${jobId}" data-prompt="${promptAttr}" data-download-url="${data.local_url || ''}">📥 Tải ảnh</button>
                        <button class="ap-inline-btn" data-action="regenerate" data-prompt="${promptAttr}">🔄 Tạo lại</button>
                        <button class="ap-inline-btn" data-action="edit" data-prompt="${promptAttr}">✏️ Chỉnh sửa</button>
                    </div>
                    <div class="ap-inline-edit-box" style="display:none; margin-top:8px;">
                        <textarea class="ap-inline-edit-textarea" rows="3" style="width:100%;box-sizing:border-box;padding:6px 8px;font-size:13px;border-radius:6px;border:1px solid var(--border);background:var(--bg-secondary,var(--bg));color:var(--text);resize:vertical;">${prompt}</textarea>
                        <div style="display:flex;gap:6px;margin-top:6px;">
                            <button class="ap-inline-btn ap-inline-btn--primary" data-action="edit-run">🎨 Tạo với prompt mới</button>
                            <button class="ap-inline-btn" data-action="edit-cancel">✕ Hủy</button>
                        </div>
                    </div>
                </div>`;

            const dlBtn = resultDiv.querySelector('[data-action="download"]');
            dlBtn?.addEventListener('click', () => {
                const a = document.createElement('a');
                a.href = downloadSrc;
                a.download = `anime_pipeline_${jobId}.png`;
                a.click();
            });

            // Remember the result against the active chat session so
            // follow-up turns ("crop tighter", "what color is the dress",
            // "regenerate same character") see it as context. The backend
            // back-fills manifest_path / character_key / preset from the
            // JobQueue using job_id alone, so we do not need to forward
            // them from here.
            try {
                window.chatManager?.addGeneratedImage?.({
                    job_id: jobId,
                    url: data.local_url || undefined,
                    prompt: prompt,
                    provider: 'local',
                    model: 'anime_pipeline',
                });
            } catch (_e) { /* non-fatal */ }

            // Tạo lại: re-run inline with same prompt — preserve the
            // image-only / batch-size mode so a regenerate from a
            // 4-image batch produces another 4-image batch (with new
            // random seeds) instead of dropping back to the full
            // beauty pipeline.
            resultDiv.querySelector('[data-action="regenerate"]')?.addEventListener('click', () => {
                this._runInlineChat(prompt, chatContainer, {
                    imageOnly: wasImageOnly,
                    batchSize: replayBatchSize,
                });
            });

            // Chỉnh sửa: toggle edit box
            const editBox = resultDiv.querySelector('.ap-inline-edit-box');
            resultDiv.querySelector('[data-action="edit"]')?.addEventListener('click', () => {
                editBox.style.display = editBox.style.display === 'none' ? 'block' : 'none';
                if (editBox.style.display === 'block') {
                    editBox.querySelector('textarea')?.focus();
                }
            });

            // Run with edited prompt — also preserve the run mode.
            resultDiv.querySelector('[data-action="edit-run"]')?.addEventListener('click', () => {
                const newPrompt = editBox.querySelector('textarea')?.value?.trim();
                if (newPrompt) {
                    editBox.style.display = 'none';
                    this._runInlineChat(newPrompt, chatContainer, {
                        imageOnly: wasImageOnly,
                        batchSize: replayBatchSize,
                    });
                }
            });

            // Cancel edit
            resultDiv.querySelector('[data-action="edit-cancel"]')?.addEventListener('click', () => {
                editBox.style.display = 'none';
            });

            // Wire image click-to-open via the real lightbox. Covers
            // both the single-image layout and every tile in the
            // image-only batch grid.
            resultDiv.querySelectorAll('img[data-igv2-open]').forEach(img => {
                img.addEventListener('click', () => {
                    if (window.openImagePreview) {
                        window.openImagePreview(img);
                    }
                });
            });

            // 2026-04-28: per-tile "📐 Upscale" overlay button removed by
            // user request — the new orientation presets generate at
            // native 2048×2048 (or 1536×2048 / 2048×1536) so a
            // post-hoc upscale pass is no longer needed in the common
            // case. The /api/anime-pipeline/upscale endpoint still
            // exists for power users / CLI consumers.

            msgContent?.appendChild(resultDiv.firstElementChild);
            chatContainer.scrollTop = chatContainer.scrollHeight;

            // Save to session
            window.chatApp?.saveCurrentSession?.(true);
        }
    }

    /** Show a fatal error state in the inline bubble. */
    _setInlineError(bubble, uid, message) {
        // If the user already pressed Stop, treat any subsequent stream
        // error as the cancel taking effect: surface the freshest layer
        // as the output instead of an angry red error.
        if (bubble?.dataset?.apHardStop === '1' && bubble?.dataset?.apFinalized !== '1') {
            this._forceFinalizeAsCancelled(bubble, uid);
            return;
        }
        bubble.dataset.apFinalized = '1';
        bubble.dataset.apState = 'error';
        const details = bubble?.querySelector('.ap-inline-progress');
        if (details) {
            details.open = true;
            const label = details.querySelector('.ap-inline-label');
            if (label) label.textContent = '❌ ' + message;
            const current = document.getElementById(`ap-current-${uid}`);
            if (current) current.textContent = message;
        }
    }

    closeModal() {
        const el = document.getElementById('animePipelineModal');
        if (!el) return;
        el.classList.remove('active', 'open');
        this.cancel();
    }

    cancel() {
        if (this._abort) {
            this._abort.abort();
            this._abort = null;
        }
        this._running = false;
        this._setGenerateEnabled(true);
    }

    // ── Health check ────────────────────────────────────────────────

    async _checkHealth() {
        const statusEl = document.getElementById('apStatus');
        try {
            const resp = await fetch('/api/anime-pipeline/health');
            const data = await resp.json();
            this._available = data;
            if (data.available) {
                if (statusEl) statusEl.textContent = '✅ Pipeline ready';
            } else {
                // Show warning but keep button enabled — user gets a real error on generate.
                const msg = (data.errors || []).join('; ') || 'Pipeline unavailable';
                if (statusEl) statusEl.textContent = '⚠️ ' + msg;
            }
        } catch (e) {
            if (statusEl) statusEl.textContent = '⚠️ Health check failed — try generating anyway';
        }
        // Always enable the button; failure is surfaced when the stream starts.
        this._setGenerateEnabled(true);
    }

    // ── Generate (SSE) ──────────────────────────────────────────────

    async generate() {
        if (this._running) return;

        const prompt = (document.getElementById('apPrompt')?.value || '').trim();
        if (!prompt) {
            this._showError('Please enter a prompt.');
            return;
        }

        this._running = true;
        this._setGenerateEnabled(false);
        this._resetProgress();
        this._showSection('progress');

        const preset = document.getElementById('apPreset')?.value || 'anime_quality';
        const quality = document.getElementById('apQuality')?.value || 'quality';
        this._debug = document.getElementById('apDebug')?.checked || false;

        const body = {
            prompt,
            preset,
            quality_mode: quality,
            debug: this._debug,
            model_base:    document.getElementById('apModelBase')?.value || '',
            model_cleanup: document.getElementById('apModelCleanup')?.value || '',
            model_final:   document.getElementById('apModelFinal')?.value || '',
        };

        // Collect reference images
        const refInput = document.getElementById('apReferenceInput');
        if (refInput?.files?.length) {
            body.reference_images = await this._filesToB64(refInput.files);
        }

        this._abort = new AbortController();

        // Abort on F5 / page unload to avoid stuck connections
        const onUnload = () => this._abort?.abort();
        window.addEventListener('beforeunload', onUnload);

        try {
            const resp = await fetch('/api/anime-pipeline/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(body),
                signal: this._abort.signal,
            });

            if (!resp.ok && !resp.headers.get('content-type')?.includes('text/event-stream')) {
                const err = await resp.json().catch(() => ({ error: 'Request failed' }));
                this._showError(err.error || `HTTP ${resp.status}`);
                return;
            }

            await this._consumeSSE(resp);

        } catch (e) {
            if (e.name === 'AbortError') return;
            this._showError(e.message || 'Connection lost');
        } finally {
            window.removeEventListener('beforeunload', onUnload);
            this._running = false;
            this._setGenerateEnabled(true);
        }
    }

    // ── SSE consumer ────────────────────────────────────────────────

    async _consumeSSE(resp) {
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let currentEvent = '';
        let gotResult = false;

        // Timeout: if no event received for 120s, treat as connection lost
        const SSE_TIMEOUT_MS = 120_000;
        let timeoutId = setTimeout(() => {
            if (!gotResult) {
                reader.cancel();
                this._onError({ error: 'Mất kết nối (timeout 120s)', recoverable: false });
            }
        }, SSE_TIMEOUT_MS);

        const resetTimeout = () => {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                if (!gotResult) {
                    reader.cancel();
                    this._onError({ error: 'Mất kết nối (timeout 120s)', recoverable: false });
                }
            }, SSE_TIMEOUT_MS);
        };

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                resetTimeout();
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        currentEvent = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (currentEvent === 'ap_result' || currentEvent === 'ap_done') {
                                gotResult = true;
                            }
                            this._handleEvent(currentEvent, data);
                        } catch { /* ignore malformed */ }
                    }
                }
            }
        } finally {
            clearTimeout(timeoutId);
        }

        // If stream ended without ap_result, show error
        if (!gotResult) {
            this._onError({ error: 'Stream kết thúc bất ngờ — không nhận được kết quả', recoverable: false });
        }
    }

    _handleEvent(event, data) {
        switch (event) {
            case 'ap_status':
                this._onStatus(data);
                break;
            case 'ap_stage_start':
                this._onStageStart(data);
                break;
            case 'ap_stage_done':
                this._onStageDone(data);
                break;
            case 'ap_preview':
                this._onPreview(data);
                break;
            case 'ap_critique_result':
                this._onCritiqueResult(data);
                break;
            case 'ap_refine':
                this._onRefine(data);
                break;
            case 'ap_refine_reasoning':
                this._onRefineReasoning(data);
                break;
            case 'ap_full_restart':
                this._onFullRestart(data);
                break;
            case 'ap_result':
                this._onResult(data);
                break;
            case 'ap_error':
                this._onError(data);
                break;
            case 'ap_done':
                // stream complete — nothing more to do
                break;
        }
    }

    // ── Event handlers ──────────────────────────────────────────────

    _onStatus(data) {
        const el = document.getElementById('apCurrentAction');
        if (el) el.textContent = data.message || 'Initialising…';
    }

    _onStageStart(data) {
        const { stage, label, stage_num, total_stages } = data;
        this._setStageState(stage, 'active');

        const el = document.getElementById('apCurrentAction');
        if (el) el.textContent = label || stage;

        const pct = Math.round(((stage_num - 1) / total_stages) * 100);
        this._setProgressPercent(pct);
    }

    _onStageDone(data) {
        const { stage, stage_num, total_stages, latency_ms } = data;
        this._setStageState(stage, 'done');

        const pct = Math.round((stage_num / (total_stages || 7)) * 100);
        this._setProgressPercent(pct);

        // Update latency display
        const row = document.querySelector(`[data-ap-stage="${stage}"] .ap-stage-time`);
        if (row && latency_ms) {
            row.textContent = `${(latency_ms / 1000).toFixed(1)}s`;
        }
    }

    _onPreview(data) {
        if (!this._debug || !data.image_b64) return;

        const container = document.getElementById('apDebugPreviews');
        if (!container) return;

        container.style.display = '';

        const wrap = document.createElement('div');
        wrap.className = 'ap-debug-preview';
        wrap.innerHTML = `
            <div class="ap-debug-preview__label">${data.stage}</div>
            <img src="data:image/png;base64,${data.image_b64}" alt="${data.stage}">
        `;
        container.querySelector('.ap-debug-preview__grid')?.appendChild(wrap);
    }

    _onRefine(data) {
        const el = document.getElementById('apCurrentAction');
        if (el) {
            el.textContent = `Refining (round ${data.round}/${data.max_rounds}, score: ${(data.previous_score || 0).toFixed(1)})…`;
        }
        // Reset loop stages: beauty → YOLO → critique
        this._setStageState('beauty_pass', 'pending');
        this._setStageState('detection_inpaint', 'pending');
        this._setStageState('critique', 'pending');
    }

    _onRefineReasoning(data) {
        // Show reasoning details in progress view
        const el = document.getElementById('apCurrentAction');
        if (el) {
            const dims = (data.worst_dimensions || []).slice(0, 3).join(', ');
            const actionCount = (data.actions || []).length;
            el.textContent = `🧠 Reasoning: ${dims || 'general'} — applying ${actionCount} fix(es)`;
        }
    }

    _onFullRestart(data) {
        const el = document.getElementById('apCurrentAction');
        if (el) {
            el.textContent = `🔄 Full restart #${data.restart_num} (best score: ${(data.best_score || 0).toFixed(1)}) — regenerating from scratch`;
        }
        // Reset all stages
        STAGES.forEach(s => this._setStageState(s.key, 'pending'));
    }

    _onCritiqueResult(data) {
        // Show score chip on the critique stage row in the modal
        const row = document.querySelector('[data-ap-stage="critique"]');
        if (!row) return;
        const passed = data.passed;
        const scoreText = `${data.score}/10 ${passed ? '\u2705' : '\u21a9\ufe0f'}`;
        let badge = row.querySelector('.ap-score-badge');
        if (!badge) {
            badge = document.createElement('span');
            badge.className = 'ap-score-badge';
            const timeEl = row.querySelector('.ap-stage-time');
            if (timeEl) row.insertBefore(badge, timeEl);
            else row.appendChild(badge);
        }
        badge.textContent = scoreText;
        badge.className = `ap-score-badge ${passed ? 'ap-score-pass' : 'ap-score-fail'}`;
        const issues = data.issues || [];
        if (issues.length) badge.title = issues.slice(0, 3).join(' \u00b7 ');
    }

    _onResult(data) {
        this._setProgressPercent(100);
        this._showSection('result');

        const statusEl = document.getElementById('apStatus');
        if (statusEl) statusEl.textContent = '✅ Hoàn thành!';

        const imgEl = document.getElementById('apResultImage');
        if (imgEl) {
            // Prefer local_url (survives localStorage quota stripping)
            // then cloud_url, then base64 as last resort
            const src = data.local_url || data.cloud_url || (data.image_b64 ? 'data:image/png;base64,' + data.image_b64 : '');
            if (src) {
                imgEl.src = src;
                imgEl.style.display = '';
            } else {
                imgEl.style.display = 'none';
            }
        }

        // Populate manifest summary
        const metaEl = document.getElementById('apResultMeta');
        if (metaEl) {
            const lines = [];
            if (data.total_latency_ms) lines.push(`⏱️ ${(data.total_latency_ms / 1000).toFixed(1)}s`);
            if (data.refine_rounds) lines.push(`🔄 ${data.refine_rounds} vòng tinh chỉnh`);
            if (data.models_used?.length) lines.push(`🧠 ${data.models_used.join(', ')}`);
            if (data.stages_executed?.length) lines.push(`📋 ${data.stages_executed.length} stages`);
            metaEl.innerHTML = lines.join(' &nbsp;·&nbsp; ');
        }

        // Store result for download / send-to-chat
        this._lastResult = data;
    }

    _onError(data) {
        if (data.recoverable) {
            // Non-fatal: show inline warning in progress view
            const el = document.getElementById('apCurrentAction');
            if (el) el.textContent = `⚠️ ${data.stage || ''}: ${data.error}`;
        } else {
            // Fatal: show error without jumping to form
            const statusEl = document.getElementById('apStatus');
            if (statusEl) statusEl.textContent = '❌ Thất bại';
            const errEl = document.getElementById('apErrorBox');
            if (errEl) {
                errEl.textContent = data.error || 'Pipeline thất bại';
                errEl.style.display = '';
            }
            const actionEl = document.getElementById('apCurrentAction');
            if (actionEl) actionEl.textContent = '❌ ' + (data.error || 'Pipeline thất bại');
        }
    }

    /**
     * Insert the generated image into the chat conversation.
     * Uses window.chatApp (set by main.js) to access messageRenderer.
     */
    sendToChat() {
        const result = this._lastResult;
        if (!result) return;
        const app = window.chatApp;
        if (!app) return;

        const chatContainer = document.getElementById('chat-container');
        if (!chatContainer) return;

        const prompt = (document.getElementById('apPrompt')?.value || '').trim();
        const latency = result.total_latency_ms
            ? `${(result.total_latency_ms / 1000).toFixed(1)}s` : '';
        const meta = `🎨 Anime Pipeline${latency ? ' · ' + latency : ''}`;
        // Prefer local_url / cloud_url to avoid localStorage quota issues
        const imgSrc = result.local_url || result.cloud_url || (result.image_b64 ? 'data:image/png;base64,' + result.image_b64 : '');
        if (!imgSrc) return;
        const promptAttr = prompt.replace(/"/g, '&quot;');

        app.messageRenderer.addMessage(
            chatContainer,
            `<div class="igv2-chat-image" data-prompt="${promptAttr}">
                <img src="${imgSrc}" alt="Anime Pipeline result" data-igv2-open="${imgSrc}">
                <div class="igv2-chat-meta">${meta}</div>
            </div>`,
            false,
            app.currentModel || '',
            '',
            app.uiUtils?.formatTimestamp(new Date()) || ''
        );
        chatContainer.scrollTop = chatContainer.scrollHeight;
        app.saveCurrentSession?.(true);
        this.closeModal();
    }

    // ── UI helpers ──────────────────────────────────────────────────

    _resetUI() {
        this._resetProgress();
        this._showSection('form');
        const err = document.getElementById('apErrorBox');
        if (err) err.style.display = 'none';
        const dbg = document.getElementById('apDebugPreviews');
        if (dbg) {
            dbg.style.display = 'none';
            const grid = dbg.querySelector('.ap-debug-preview__grid');
            if (grid) grid.innerHTML = '';
        }
    }

    _resetProgress() {
        STAGES.forEach(s => this._setStageState(s.key, 'pending'));
        this._setProgressPercent(0);
        const el = document.getElementById('apCurrentAction');
        if (el) el.textContent = 'Starting…';
    }

    _showSection(which) {
        ['form', 'progress', 'result'].forEach(s => {
            const el = document.getElementById(`apSection_${s}`);
            if (el) el.style.display = s === which ? '' : 'none';
        });
    }

    _setStageState(stageKey, state) {
        const row = document.querySelector(`[data-ap-stage="${stageKey}"]`);
        if (!row) return;
        row.classList.remove('pending', 'active', 'done', 'error');
        row.classList.add(state);
    }

    _setProgressPercent(pct) {
        const bar = document.getElementById('apProgressBar');
        if (bar) bar.style.width = pct + '%';
        const lbl = document.getElementById('apProgressLabel');
        if (lbl) lbl.textContent = pct + '%';
    }

    _setGenerateEnabled(enabled) {
        const btn = document.getElementById('apGenerateBtn');
        if (btn) btn.disabled = !enabled;
    }

    _showError(msg) {
        const el = document.getElementById('apErrorBox');
        if (el) {
            el.textContent = msg;
            el.style.display = '';
        }
        this._showSection('form');
    }

    // ── Download result ─────────────────────────────────────────────

    downloadResult() {
        const result = this._lastResult;
        if (!result) return;
        const src = result.local_url || result.cloud_url || (result.image_b64 ? 'data:image/png;base64,' + result.image_b64 : '');
        if (!src) return;

        const a = document.createElement('a');
        a.href = src;
        a.download = `anime_pipeline_${result.job_id || 'result'}.png`;
        a.click();
    }

    newGeneration() {
        this._resetUI();
    }

    // ── File helpers ────────────────────────────────────────────────

    async _filesToB64(files) {
        const results = [];
        for (const file of Array.from(files).slice(0, 4)) {
            const b64 = await new Promise((resolve) => {
                const reader = new FileReader();
                reader.onload = () => resolve(reader.result.split(',')[1]);
                reader.readAsDataURL(file);
            });
            results.push(b64);
        }
        return results;
    }

    // ── F5 / Page-load recovery ─────────────────────────────────────

    /**
     * Called on page load to recover stuck pipeline bubbles and re-wire
     * inline button handlers that were lost when the DOM was restored
     * from localStorage.
     */
    recoverInlineBubbles() {
        const bubbles = document.querySelectorAll('.ap-inline-msg');
        if (!bubbles.length) return;

        bubbles.forEach(bubble => {
            const details = bubble.querySelector('.ap-inline-progress');
            const hasResult = bubble.querySelector('.igv2-chat-image img');

            if (hasResult) {
                // Image exists — collapse progress, re-wire buttons
                if (details) {
                    details.open = false;
                    const summary = details.querySelector('.ap-inline-summary');
                    if (summary) {
                        const dots = summary.querySelector('.thinking-pill__dots');
                        if (dots) dots.remove();
                        const label = summary.querySelector('.ap-inline-label');
                        if (label && !label.textContent.includes('✅')) {
                            const timer = summary.querySelector('.ap-inline-timer');
                            const elapsed = timer?.textContent || '';
                            label.textContent = `✅ Anime Pipeline · ${elapsed}`;
                            if (timer) timer.remove();
                        }
                    }
                }
                this._rewireInlineButtons(bubble);
            } else if (details) {
                // No image — pipeline was interrupted mid-stream (network drop / F5).
                // Treat as broken: backend job (if any) is unreachable from here, so
                // immediately fire-and-forget cancel (orphan cleanup) and switch the
                // bubble into "retry" mode. The Stop button — if any — gets neutered
                // because there is no live stream to stop.
                const orphanJobId = bubble.dataset.jobId || '';
                if (orphanJobId) {
                    fetch('/api/anime-pipeline/cancel', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ job_id: orphanJobId }),
                        keepalive: true,
                    }).catch(() => {});
                }
                details.open = true;
                const label = details.querySelector('.ap-inline-label');
                if (label) label.textContent = '⚠️ Pipeline bị gián đoạn (F5/mất kết nối)';
                const dots = details.querySelector('.thinking-pill__dots');
                if (dots) dots.remove();
                const timer = details.querySelector('.ap-inline-timer');
                if (timer) timer.remove();
                // Disable any leftover Stop button — its job is dead.
                const stopBtn = details.querySelector('.ap-inline-stop-btn');
                if (stopBtn) {
                    stopBtn.disabled = true;
                    stopBtn.style.display = 'none';
                }
                const current = bubble.querySelector('[id^="ap-current-"]');
                if (current) current.textContent = 'Bấm "Tạo lại" để chạy lại pipeline';

                // Recovery button. We ALWAYS re-bind the click handler even if
                // the .ap-recovery-btn element was restored from localStorage
                // (in which case the original addEventListener is gone). Without
                // this re-bind the button looks alive but does nothing — the
                // exact "phế vật" symptom users hit after F5.
                const msgContent = bubble.querySelector('.message-content');
                let retryBtn = bubble.querySelector('.ap-recovery-btn');
                if (!retryBtn && msgContent) {
                    const retryDiv = document.createElement('div');
                    retryDiv.style.cssText = 'margin-top:8px;';
                    retryDiv.innerHTML = `<button class="ap-inline-btn ap-recovery-btn" style="padding:6px 14px;">🔄 Tạo lại</button>`;
                    msgContent.appendChild(retryDiv);
                    retryBtn = retryDiv.querySelector('button');
                }
                if (retryBtn) {
                    // Clone-replace removes any stale listeners from a previous session.
                    const fresh = retryBtn.cloneNode(true);
                    retryBtn.replaceWith(fresh);
                    fresh.addEventListener('click', () => {
                        const prompt = bubble.getAttribute('data-ap-prompt')
                            || bubble.querySelector('[data-prompt]')?.getAttribute('data-prompt')
                            || '';
                        if (prompt) {
                            bubble.remove();
                            const chatContainer = document.getElementById('chatContainer');
                            if (chatContainer) this._runInlineChat(prompt, chatContainer);
                        }
                    });
                }

                // Mark all active/pending stages as interrupted
                bubble.querySelectorAll('.ap-stage-item.active, .ap-stage-item.pending').forEach(row => {
                    row.classList.remove('active', 'pending');
                    row.classList.add('error');
                });
            }
        });
    }

    /**
     * Re-wire event listeners on inline result buttons after DOM restore.
     * @param {HTMLElement} bubble
     */
    _rewireInlineButtons(bubble) {
        const chatContainer = document.getElementById('chatContainer');

        // Check if image is broken/placeholder (base64 stripped by storage cleanup)
        const img = bubble.querySelector('.igv2-chat-image img');
        const imgSrc = img?.getAttribute('src') || '';
        const isPlaceholder = !imgSrc || imgSrc.includes('R0lGODlhAQABAI') || imgSrc === '#' || imgSrc === '[image removed to save space]';

        // If image is a placeholder, try to recover from data-igv2-open or data-download-url
        if (img && isPlaceholder) {
            const serverUrl = img.getAttribute('data-igv2-open') || '';
            const dlUrl = bubble.querySelector('[data-download-url]')?.getAttribute('data-download-url') || '';
            const recoveryUrl = (serverUrl && !serverUrl.startsWith('data:')) ? serverUrl
                : (dlUrl && !dlUrl.startsWith('data:')) ? dlUrl : '';
            if (recoveryUrl) {
                img.src = recoveryUrl;
                img.setAttribute('data-igv2-open', recoveryUrl);
            }
        }

        // Download button
        bubble.querySelectorAll('[data-action="download"]').forEach(btn => {
            const jobId = btn.getAttribute('data-job') || 'result';
            const downloadUrl = btn.getAttribute('data-download-url') || '';
            const imgEl = bubble.querySelector('.igv2-chat-image img');
            const src = downloadUrl || imgEl?.getAttribute('src') || '';
            btn.replaceWith(btn.cloneNode(true));  // remove old listeners
            const newBtn = bubble.querySelector('[data-action="download"]');
            newBtn?.addEventListener('click', () => {
                if (!src || src.includes('R0lGODlhAQABAI')) {
                    alert('Ảnh không còn khả dụng. Hãy tạo lại.');
                    return;
                }
                const a = document.createElement('a');
                a.href = src;
                a.download = `anime_pipeline_${jobId}.png`;
                a.click();
            });
        });

        // Regenerate button
        bubble.querySelectorAll('[data-action="regenerate"]').forEach(btn => {
            const prompt = btn.getAttribute('data-prompt') || '';
            btn.replaceWith(btn.cloneNode(true));
            const newBtn = bubble.querySelector('[data-action="regenerate"]');
            newBtn?.addEventListener('click', () => {
                if (prompt && chatContainer) this._runInlineChat(prompt, chatContainer);
            });
        });

        // Edit button + edit box
        const editBox = bubble.querySelector('.ap-inline-edit-box');
        bubble.querySelectorAll('[data-action="edit"]').forEach(btn => {
            btn.replaceWith(btn.cloneNode(true));
            const newBtn = bubble.querySelector('[data-action="edit"]');
            newBtn?.addEventListener('click', () => {
                if (editBox) {
                    editBox.style.display = editBox.style.display === 'none' ? 'block' : 'none';
                    if (editBox.style.display === 'block') editBox.querySelector('textarea')?.focus();
                }
            });
        });

        bubble.querySelectorAll('[data-action="edit-run"]').forEach(btn => {
            btn.replaceWith(btn.cloneNode(true));
            const newBtn = bubble.querySelector('[data-action="edit-run"]');
            newBtn?.addEventListener('click', () => {
                const newPrompt = editBox?.querySelector('textarea')?.value?.trim();
                if (newPrompt && chatContainer) {
                    if (editBox) editBox.style.display = 'none';
                    this._runInlineChat(newPrompt, chatContainer);
                }
            });
        });

        bubble.querySelectorAll('[data-action="edit-cancel"]').forEach(btn => {
            btn.replaceWith(btn.cloneNode(true));
            const newBtn = bubble.querySelector('[data-action="edit-cancel"]');
            newBtn?.addEventListener('click', () => {
                if (editBox) editBox.style.display = 'none';
            });
        });

        // Image click-to-open via the real lightbox.
        bubble.querySelectorAll('.igv2-chat-image img').forEach(img => {
            img.style.cursor = 'pointer';
            img.addEventListener('click', () => {
                if (window.openImagePreview) {
                    window.openImagePreview(img);
                }
            });
        });
    }
}
