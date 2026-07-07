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

        /** Inline-generation queue — max 3 pending slots. */
        this._queue = [];
        /** True when the active generation is a multi-image batch (no queueing). */
        this._batchMode = false;
        /** True while _runContinuous is looping (no queueing between iterations). */
        this._continuousMode = false;
        /** UID of the generation currently being streamed. */
        this._runningUid = null;

        /**
         * Per-uid run state for bubbles driven by the CHAT SSE stream
         * (the "Thinking with Images" bridge), keyed by uid:
         *   { bubble, prompt, startTime, chatContainer, timerInterval, savedImage }
         * Separate from _runningUid so a chat-bridged image turn never
         * collides with this module's own /api/anime-pipeline/stream runs.
         */
        this._chatBridgeRuns = new Map();

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
            const ask = (window.appPrompt
                ? window.appPrompt('Mô tả anime scene bạn muốn tạo:', '')
                : Promise.resolve(''));
            ask.then((prompt) => {
                if (prompt && String(prompt).trim()) {
                    this._runInlineChat(String(prompt).trim(), chatContainer);
                }
            }).catch(() => {});
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
        // #chatContainer is always present — no fallback needed.
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
        const imageOnly = !!opts.imageOnly;
        const batchSize = Math.max(1, Math.min(parseInt(opts.batchSize, 10) || 1, 6));

        // ── Queue guard ──────────────────────────────────────────────────
        // Internal calls (_isInternal: true) bypass the guard so queued
        // items and continuous-loop iterations are never re-queued.
        if ((this._running || this._continuousMode) && !opts._isInternal) {
            if (this._batchMode || this._continuousMode) {
                this._appendQueueMessage(chatContainer,
                    '⚠️ Pipeline đang tạo ảnh hàng loạt / liên tục — vui lòng chờ hoàn tất');
            } else if (this._queue.length >= 3) {
                this._appendQueueMessage(chatContainer,
                    '⚠️ Hàng đợi đầy (tối đa 3) — vui lòng chờ pipeline hiện tại hoàn thành');
            } else {
                this._enqueueRequest(prompt, chatContainer, opts);
            }
            return;
        }
        // ────────────────────────────────────────────────────────────────

        this._running = true;
        this._batchMode = imageOnly && batchSize > 1;

        const uid = opts._holdingUid || Date.now().toString(36);
        this._runningUid = uid;
        const startTime = Date.now();

        // Reuse the queued holding bubble when available; create a fresh one otherwise.
        let bubble;
        if (opts._holdingBubble) {
            bubble = opts._holdingBubble;
            this._activateQueuedBubble(bubble, uid);
            if (bubble.isConnected) chatContainer.scrollTop = chatContainer.scrollHeight;
        } else {
            bubble = this._createInlineBubble(uid, prompt);
            chatContainer.appendChild(bubble);
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }

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
        // Use `bubble` directly — it may be detached (queued background run)
        // so getElementById would return null.
        bubble.dataset.apImageOnly = imageOnly ? '1' : '0';
        bubble.dataset.apBatchSize = String(body.batch_size);

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
            this._batchMode = false;
            this._runningUid = null;
            this._abort = null;
            this._processQueue();
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
        const baseOpts = { imageOnly: !!opts.imageOnly, batchSize: opts.batchSize || 1, _isInternal: true };

        // Reset cancel flag and exclude-list at loop start.
        this._continuousCancelled = false;
        this._continuousExcludes = [];
        this._continuousMode = true;

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
        this._continuousMode = false;
        this._processQueue();
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
                <span class="ap-stage-dot"></span>
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
                <img src="/static/icons/app-icon.png" class="avatar-img" alt="" width="36" height="36" draggable="false">
            </div>
            <div class="message__body">
                <div class="message-content">
                    <div class="ap-pipeline-card" data-open>
                        <div class="ap-pipeline-header">
                            <div class="thinking-pill__dots">
                                <span></span><span></span><span></span>
                            </div>
                            <span class="ap-inline-label" id="ap-headline-${uid}">Khởi động…</span>
                            <span class="ap-inline-timer" id="ap-timer-${uid}">0.0s</span>
                            <button type="button"
                                    class="ap-inline-stop-btn"
                                    id="ap-stop-${uid}"
                                    title="Ngưng pipeline và xuất ảnh hiện tại">⏹ Ngưng &amp; xuất ảnh</button>
                        </div>
                        <div class="ap-pipeline-body">
                            <div class="ap-pipeline-status ap-inline-current" id="ap-current-${uid}">Khởi động…</div>
                            <div class="ap-inline-stages" id="ap-stages-${uid}">${stagesHtml}</div>
                        </div>
                    </div>
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

    // ── Thinking-with-Images bridge (chat-stream driven) ─────────────────
    //
    // These two public methods let the CHAT SSE stream (api-service.js)
    // drive the inline bubble instead of this module's own
    // /api/anime-pipeline/stream consumer. The backend bridge in
    // routes/stream.py forwards the pipeline's ap_* frames verbatim into
    // /chat/stream; send-message-helpers.js calls beginInlineFromChat()
    // once, then injectSSEEvent() for every ap_* frame. No new renderer is
    // built — we reuse _createInlineBubble + _handleInlineEvent wholesale.

    /**
     * Create + mount an inline image bubble that will be fed by the chat
     * SSE stream. Returns the bubble element (so the caller can reposition
     * it, e.g. above the caption message div). Does NOT fetch anything.
     *
     * @param {string} uid   stable id for this chat-bridged image turn
     * @param {string} prompt original user prompt (for result metadata)
     * @param {object} opts   { chatContainer?, parentEl? }
     *                        parentEl reserved for Phase 1b (nest under a
     *                        thinking-section); defaults to chatContainer.
     */
    beginInlineFromChat(uid, prompt, opts = {}) {
        const chatContainer = opts.chatContainer
            || document.getElementById('chatContainer')
            || document.querySelector('.chat-container');
        if (!chatContainer) return null;
        const parentEl = opts.parentEl || chatContainer;

        const bubble = this._createInlineBubble(uid, prompt || '');
        parentEl.appendChild(bubble);
        try { chatContainer.scrollTop = chatContainer.scrollHeight; } catch (_) { /* noop */ }

        const startTime = Date.now();
        const timerEl = document.getElementById(`ap-timer-${uid}`);
        const timerInterval = setInterval(() => {
            if (!timerEl || !timerEl.isConnected) { clearInterval(timerInterval); return; }
            timerEl.textContent = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
        }, 200);

        this._chatBridgeRuns.set(uid, {
            bubble,
            prompt: prompt || '',
            startTime,
            chatContainer,
            timerInterval,
            savedImage: false,
        });
        return bubble;
    }

    /**
     * Push a single pre-parsed SSE event (forwarded from the chat stream)
     * into the inline bubble renderer. Drives the full _handleInlineEvent
     * dispatch so a chat-bridged bubble behaves exactly like a native run
     * (ap_status job_id capture, ap_queued, ap_preview, ap_refine,
     * ap_result, ap_error, …).
     *
     * Duplicate-save guard: only the FIRST ap_result registers the image
     * asset (addGeneratedImage) / finalizes; the chat `complete` event also
     * persists the turn, so a re-entrant ap_result must not double-add.
     */
    injectSSEEvent(uid, name, data) {
        const run = this._chatBridgeRuns.get(uid);
        if (!run) { console.warn('[bridge] injectSSEEvent: no run for uid', uid, name); return; }
        const bubble = document.getElementById(`ap-inline-${uid}`) || run.bubble;
        if (!bubble) { console.warn('[bridge] injectSSEEvent: no bubble for uid', uid); return; }
        if (name === 'ap_result') {
            console.log('[bridge] ap_result: connected=', bubble.isConnected,
                'local_url=', !!(data && data.local_url),
                'image_b64=', !!(data && data.image_b64),
                'images=', Array.isArray(data && data.images) ? data.images.length : 0);
        }

        if (name === 'ap_result') {
            if (run.savedImage) return;  // guard: finalize/persist once
            run.savedImage = true;
        }

        try {
            this._handleInlineEvent(
                name, data, bubble, uid, run.prompt, run.startTime, run.chatContainer,
            );
        } catch (e) {
            // eslint-disable-next-line no-console
            console.error('[anime-pipeline] injectSSEEvent failed:', e?.message || e);
        }

        // Terminal pipeline events: stop the timer; release run state on
        // ap_done / ap_error (ap_done always trails ap_result from the bridge).
        if (name === 'ap_result' || name === 'ap_error' || name === 'ap_done') {
            clearInterval(run.timerInterval);
        }
        if (name === 'ap_done' || name === 'ap_error') {
            this._chatBridgeRuns.delete(uid);
        }
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

        const card = bubble.querySelector('.ap-pipeline-card');
        if (card) {
            card.removeAttribute('data-open');
            const header = card.querySelector('.ap-pipeline-header');
            if (header) {
                header.querySelector('.thinking-pill__dots')?.remove();
                const stop = header.querySelector('.ap-inline-stop-btn');
                if (stop) stop.style.display = 'none';
                const label = header.querySelector('.ap-inline-label');
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
    /**
     * Phase 3 (opt-in): update the single live denoise-preview frame for a run.
     * Reuses one <img> slot at the top of the gallery, swapping its data URL as
     * ComfyUI streams preview JPEGs over /ws. Cheap DOM update (src only).
     */
    _inlineSetLivePreview(uid, fmt, b64) {
        const gallery = document.getElementById(`ap-layers-${uid}`);
        if (!gallery || !b64) return;
        gallery.style.display = '';
        const src = `data:image/${fmt === 'png' ? 'png' : 'jpeg'};base64,${b64}`;
        let card = document.getElementById(`ap-live-${uid}`);
        if (!card) {
            card = document.createElement('div');
            card.id = `ap-live-${uid}`;
            card.className = 'ap-live-preview';
            card.style.cssText = (
                'margin-bottom:8px; border:1px solid var(--accent-soft,var(--border)); ' +
                'border-radius:10px; overflow:hidden; position:relative;'
            );
            card.innerHTML = `
                <img class="ap-live-img" alt="Live preview"
                     style="width:100%; max-height:320px; object-fit:contain; display:block; background:var(--bg-secondary,var(--bg));">
                <span class="ap-live-badge"
                      style="position:absolute; top:6px; left:6px; font-size:10px; font-weight:600;
                             padding:2px 7px; border-radius:999px; background:rgba(0,0,0,.55); color:#fff;">
                    ● LIVE</span>`;
            gallery.insertBefore(card, gallery.firstChild);
        }
        const img = card.querySelector('.ap-live-img');
        if (img) img.src = src;
    }

    /**
     * Remove the live-preview slot once the final image is in (called from the
     * result handler); the finished layers/result replace it.
     */
    _inlineClearLivePreview(uid) {
        const card = document.getElementById(`ap-live-${uid}`);
        if (card) card.remove();
    }

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
        let gotResult = false;
        let lastDataMs = Date.now();
        let gotFirstEvent = false;

        // Show "connecting" immediately so user sees SSE is open (fetch resolved).
        this._inlineSetCurrent(uid, '⏳ Đang kết nối pipeline…');

        // Update the counter every 4s while waiting for the first real event.
        // Stops once gotFirstEvent is true so it never clobbers stage text.
        const silenceInterval = setInterval(() => {
            if (gotFirstEvent) return;
            const silentSec = Math.round((Date.now() - lastDataMs) / 1000);
            this._inlineSetCurrent(uid, `⏳ Đang kết nối pipeline… (${silentSec}s)`);
        }, 4000);

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                lastDataMs = Date.now();
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        currentEvent = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (currentEvent === 'ap_result' || currentEvent === 'ap_done') gotResult = true;
                            // Mark first real event received (not keepalive comments)
                            if (currentEvent && !gotFirstEvent) gotFirstEvent = true;
                            this._handleInlineEvent(currentEvent, data, bubble, uid, prompt, startTime, chatContainer);
                        } catch { /* ignore malformed */ }
                    }
                }
            }
        } finally {
            clearInterval(silenceInterval);
            reader.cancel().catch(() => {});
        }

        // Stream ended without ap_result — backend job may still be running
        if (!gotResult) {
            const jobId = bubble.dataset.jobId;
            if (jobId) {
                this._pollForResult(bubble, uid, prompt, startTime, chatContainer, jobId);
            } else {
                this._setInlineError(bubble, uid, 'Stream kết thúc bất ngờ — không nhận được kết quả');
            }
        }
    }

    /**
     * Reflect a `progress_stage` key (from job-queue poll) into the stage cells.
     * Marks every stage before curStage as done, curStage as active.
     * Called when SSE has dropped and we're polling /api/jobs/{id} for progress.
     */
    _syncStagesFromPoll(uid, curStage) {
        const curIdx = STAGES.findIndex(s => s.key === curStage);
        if (curIdx < 0) return;
        STAGES.forEach((s, i) => {
            if (i < curIdx)      this._inlineSetStage(uid, s.key, 'done');
            else if (i === curIdx) this._inlineSetStage(uid, s.key, 'active');
        });
    }

    /** Poll /api/jobs/<jobId> until completed/failed, then show result. */
    async _pollForResult(bubble, uid, prompt, startTime, chatContainer, jobId) {
        this._inlineSetCurrent(uid, '⏳ Kết nối bị ngắt — đang kiểm tra kết quả...');
        const POLL_INTERVAL = 2000;
        const POLL_TIMEOUT = 5 * 60 * 1000; // 5 minutes
        const deadline = Date.now() + POLL_TIMEOUT;

        while (Date.now() < deadline) {
            await new Promise(r => setTimeout(r, POLL_INTERVAL));

            // Stop only on explicit user abort; keep polling even if bubble is
            // detached from DOM (user switched chat tab) — result goes to localStorage.
            if (this._abort?.signal.aborted) return;

            try {
                const res = await fetch(`/api/jobs/${encodeURIComponent(jobId)}`);
                if (!res.ok) continue;
                const { job } = await res.json();

                if (job.state === 'completed') {
                    // Fetch manifest for local_url
                    let local_url = null;
                    try {
                        const mRes = await fetch(`/api/jobs/${encodeURIComponent(jobId)}/manifest`);
                        if (mRes.ok) {
                            const { manifest } = await mRes.json();
                            local_url = manifest?.local_url || manifest?.share_url || null;
                        }
                    } catch { /* manifest optional */ }

                    this._inlineShowResult(bubble, uid, {
                        job_id: jobId,
                        local_url,
                        image_b64: null,
                        prompt_used: prompt,
                    }, prompt, startTime, chatContainer);
                    return;
                }

                if (job.state === 'failed' || job.state === 'cancelled') {
                    this._setInlineError(bubble, uid, job.error || `Job ${job.state}`);
                    return;
                }

                // Still running — update status text AND stage cells
                if (job.progress_stage) {
                    const pct = typeof job.progress_pct === 'number' ? Math.round(job.progress_pct) : 0;
                    this._inlineSetCurrent(uid, `⏳ ${job.progress_stage} · ${pct}%`);
                    this._syncStagesFromPoll(uid, job.progress_stage);
                }
            } catch { /* network error — retry next interval */ }
        }

        this._setInlineError(bubble, uid, 'Hết thời gian chờ kết quả');
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
                // Track stage label so heartbeats can append elapsed time.
                bubble.dataset.apCurrentStageLabel = data.label || data.stage;
                break;
            }
            case 'ap_stage_heartbeat': {
                // Emitted every ~1.5 s while the backend blocks on ComfyUI
                // sampling. Shows elapsed time so the pill feels alive.
                // Phase 3 (opt-in): may also carry a live progress % and a
                // denoise preview frame from the ComfyUI /ws socket.
                const stageLabel = bubble.dataset.apCurrentStageLabel || data.stage || '';
                const pctText = (typeof data.progress_pct === 'number')
                    ? ` · ${Math.round(data.progress_pct)}%` : '';
                this._inlineSetCurrent(uid, `${stageLabel} · ${data.elapsed_s}s${pctText}`);
                if (data.preview_b64) {
                    this._inlineSetLivePreview(uid, data.preview_fmt || 'jpeg', data.preview_b64);
                }
                // If ap_stage_start was missed (e.g. SSE buffering), the cell
                // may still be pending. Promote it to active so the UI reflects
                // the stage that's actually running.
                if (data.stage) {
                    const hbRow = document.getElementById(`ap-stage-${uid}-${data.stage}`);
                    if (hbRow && hbRow.classList.contains('pending')) {
                        this._inlineSetStage(uid, data.stage, 'active');
                        if (!bubble.dataset.apCurrentStageLabel) {
                            bubble.dataset.apCurrentStageLabel = stageLabel;
                        }
                    }
                }
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
            case 'ap_vision_status': {
                // 2026-04-29: surface which vision provider answered
                // (NSFW chain may have routed through grok/step before
                // gemini/gpt — the user deserves to know).
                const model = data.model_used || 'unknown';
                const isNsfwChain = /^(grok|step)/i.test(model);
                const isPromptOnly = /^prompt_/i.test(model);
                const tag = isPromptOnly ? '⚠️ prompt-only fallback' :
                            isNsfwChain  ? '🔞 NSFW vision' :
                                           '👁️ vision';
                const conf = (data.confidence || 0).toFixed(2);
                const charBit = data.character_detected
                    ? ` · 🎭 ${data.character_name || 'character detected'}`
                    : '';
                this._inlineSetCurrent(
                    uid,
                    `${tag}: ${model} · conf ${conf} · ${data.tag_count} tags${charBit}`,
                );
                // Persist a small pill on the vision_analysis stage row.
                const row = document.getElementById(`ap-stage-${uid}-vision_analysis`);
                if (row) {
                    let pill = row.querySelector('.ap-vision-model-pill');
                    if (!pill) {
                        pill = document.createElement('span');
                        pill.className = 'ap-vision-model-pill';
                        pill.style.cssText = 'margin-left:6px;padding:1px 6px;border-radius:8px;font-size:.7em;';
                        const timeEl = row.querySelector('.ap-stage-time');
                        if (timeEl) row.insertBefore(pill, timeEl); else row.appendChild(pill);
                    }
                    pill.textContent = model.length > 22 ? model.slice(0, 22) + '…' : model;
                    pill.style.background = isPromptOnly
                        ? 'rgba(251,191,36,.18)' :
                          isNsfwChain ? 'rgba(244,114,182,.18)' :
                                        'rgba(34,197,94,.18)';
                    pill.style.color = isPromptOnly ? '#fbbf24' :
                                       isNsfwChain ? '#f472b6' :
                                                     '#22c55e';
                    pill.title = `model=${model}, conf=${conf}, tags=${data.tag_count}`;
                }
                break;
            }
            case 'ap_research_status': {
                // 2026-04-29: surface where reference images came from.
                // Backend (orchestrator → anime_pipeline_service) emits
                // this once character_research finishes — local cache
                // hits, web downloads, NSFW chain, etc.
                const local = data.local_refs || 0;
                const web = data.web_refs || 0;
                const skipped = !!data.web_search_skipped;
                const cachedTag = data.cached ? ' (cache)' : '';
                const nsfwTag = data.nsfw_intent ? ' · 🔞 NSFW chain' : '';
                let msg;
                if (skipped) {
                    msg = `📚 Đã có đủ ${local} ảnh local, bỏ qua web search${cachedTag}${nsfwTag}`;
                } else if (web > 0 && local > 0) {
                    msg = `📚 Dùng ${local} local + ${web} web mới${cachedTag}${nsfwTag}`;
                } else if (web > 0) {
                    msg = `🌐 Tải ${web} ảnh tham chiếu từ web${cachedTag}${nsfwTag}`;
                } else if (local > 0) {
                    msg = `📚 Dùng ${local} ảnh local${cachedTag}${nsfwTag}`;
                } else {
                    msg = `🔍 Hoàn tất research${cachedTag}${nsfwTag}`;
                }
                this._inlineSetCurrent(uid, msg);
                // Also annotate the character_research stage row with a
                // tiny ref-source pill so the badge persists after the
                // headline rolls over to the next stage.
                const row = document.getElementById(`ap-stage-${uid}-character_research`);
                if (row) {
                    let pill = row.querySelector('.ap-ref-source-pill');
                    if (!pill) {
                        pill = document.createElement('span');
                        pill.className = 'ap-ref-source-pill';
                        pill.style.cssText = 'margin-left:6px;padding:1px 6px;border-radius:8px;background:rgba(99,102,241,.15);color:#818cf8;font-size:.7em;';
                        const timeEl = row.querySelector('.ap-stage-time');
                        if (timeEl) row.insertBefore(pill, timeEl); else row.appendChild(pill);
                    }
                    pill.textContent = skipped
                        ? `📚 ${local} local`
                        : `${local}📚 + ${web}🌐`;
                    pill.title = `local=${local}, web=${web}, skipped=${skipped}, nsfw=${!!data.nsfw_intent}, conf=${(data.confidence||0).toFixed(2)}`;
                }
                break;
            }
            case 'ap_queued': {
                const pos = data.position || 1;
                this._inlineSetCurrent(uid, `⏳ Đang chờ GPU — vị trí ${pos}…`);
                break;
            }
            case 'ap_result':
                this._inlineShowResult(bubble, uid, data, prompt, startTime, chatContainer);
                break;
            case 'ap_error': {
                // 3-class UX hint (retryable / resource / config_or_workflow).
                const _hintByClass = {
                    resource: ' · GPU hết VRAM — thử giảm profile VRAM hoặc đóng bớt ứng dụng dùng GPU rồi chạy lại.',
                    retryable: ' · Lỗi tạm thời (kết nối ComfyUI) — hãy thử lại sau ít phút.',
                };
                const _hint = _hintByClass[data.error_class] || '';
                if (!data.recoverable) {
                    this._setInlineError(bubble, uid, (data.error || 'Pipeline thất bại') + _hint);
                } else {
                    if (data.stage) {
                        this._inlineSetStage(uid, data.stage, 'error');
                    }
                    this._inlineSetCurrent(uid, `⚠️ ${data.stage || ''}: ${data.error}${_hint}`);
                }
                break;
            }
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
        // Phase 3: drop the transient live-denoise frame; the final image replaces it.
        this._inlineClearLivePreview(uid);

        // ── Background-tab support ──────────────────────────────────────
        // If the bubble was removed from the DOM because the user switched chat,
        // persist the result to localStorage so recoverInlineBubbles can restore
        // it when they return.  Also try to forward directly to a re-inserted
        // bubble with the same id (user already switched back mid-generation).
        if (!bubble.isConnected) {
            const bgKey = `ap_bg_result_${uid}`;
            try {
                localStorage.setItem(bgKey, JSON.stringify({
                    local_url:   data.local_url   || null,
                    image_b64:   data.image_b64   || null,
                    job_id:      data.job_id      || uid,
                    prompt_used: data.prompt_used || prompt,
                    elapsed,
                }));
            } catch { /* storage quota — ignore */ }

            const liveBubble = document.getElementById(`ap-inline-${uid}`);
            if (liveBubble && liveBubble !== bubble) {
                // User already switched back; the bubble is live again — render there.
                localStorage.removeItem(bgKey);
                this._inlineShowResult(liveBubble, uid, data, prompt, startTime, null);
                return;
            }
            // User is still on a different chat — show a toast.
            window.appAlert?.('✅ Anime Pipeline hoàn tất! Quay lại chat để xem ảnh.', 'success');
            return;
        }
        // ── end background-tab support ──────────────────────────────────

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

        // Collapse the card and update the header to "done"
        const card = bubble.querySelector('.ap-pipeline-card');
        if (card) {
            card.removeAttribute('data-open');
            const header = card.querySelector('.ap-pipeline-header');
            if (header) {
                header.querySelector('.thinking-pill__dots')?.remove();
                header.querySelector('.ap-inline-timer')?.remove();
                header.querySelector('.ap-inline-stop-btn')?.remove();
                const label = header.querySelector('.ap-inline-label');
                const icon = document.createElement('span');
                icon.className = 'ap-inline-done-icon';
                if (wasCancelled) {
                    const stageLabel = cancelStage ? ` (ngưng tại ${cancelStage})` : '';
                    icon.textContent = '⏸';
                    header.prepend(icon);
                    if (label) label.textContent = `Đã ngưng — ảnh hiện tại · ${elapsed}s${stageLabel}`;
                } else {
                    icon.textContent = '🎨';
                    header.prepend(icon);
                    if (label) label.textContent = `✅ Anime Pipeline · ${elapsed}s`;
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
                        <img src="${src}" alt="Anime Pipeline candidate ${i + 1}" style="width:100%;height:auto;display:block;border-radius:8px;cursor:zoom-in;">
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
            if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight;

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
        const card = bubble?.querySelector('.ap-pipeline-card');
        if (card) {
            card.setAttribute('data-open', '');
            const label = card.querySelector('.ap-inline-label');
            if (label) label.textContent = '❌ ' + message;
            const current = document.getElementById(`ap-current-${uid}`);
            if (current) current.textContent = message;
        }
        // Mark every stage that is still "pending" with a dim cancelled style
        // so the user can see the pipeline never reached them.
        STAGES.forEach(s => {
            const row = document.getElementById(`ap-stage-${uid}-${s.key}`);
            if (row && row.classList.contains('pending')) {
                row.style.opacity = '0.12';
            }
        });
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
            const card = bubble.querySelector('.ap-pipeline-card');
            const hasResult = bubble.querySelector('.igv2-chat-image img');

            if (hasResult) {
                // Image exists — collapse progress, re-wire buttons
                if (card) {
                    card.removeAttribute('data-open');
                    const header = card.querySelector('.ap-pipeline-header');
                    if (header) {
                        header.querySelector('.thinking-pill__dots')?.remove();
                        const label = header.querySelector('.ap-inline-label');
                        if (label && !label.textContent.includes('✅')) {
                            const timer = header.querySelector('.ap-inline-timer');
                            const elapsed = timer?.textContent || '';
                            label.textContent = `✅ Anime Pipeline · ${elapsed}`;
                            timer?.remove();
                        }
                    }
                }
                this._rewireInlineButtons(bubble);
            } else if (card) {
                // No image yet — three possible reasons:
                // A) Result arrived while bubble was detached → localStorage has it
                // B) Generation still running in background (user switched tab mid-run)
                // C) Real network drop / F5

                const uid = bubble.id?.replace('ap-inline-', '') || '';

                // ── Case A: background result already saved ───────────────
                const bgKey = `ap_bg_result_${uid}`;
                const stored = localStorage.getItem(bgKey);
                if (stored) {
                    try {
                        const res = JSON.parse(stored);
                        localStorage.removeItem(bgKey);
                        const fakeStart = Date.now() - (parseFloat(res.elapsed || '0') * 1000);
                        this._inlineShowResult(bubble, uid, res, res.prompt_used || '', fakeStart, null);
                        return;
                    } catch { /* bad data — fall through */ }
                }

                // ── Case Q: bubble is sitting in the in-memory queue ─────────
                const queueIdx = this._queue.findIndex(item => item.uid === uid);
                if (queueIdx >= 0) {
                    card.setAttribute('data-open', '');
                    const label = card.querySelector('.ap-inline-label');
                    if (label) label.textContent = `⏳ Holding ${queueIdx + 1} — chờ pipeline sẵn sàng`;
                    return;
                }

                // ── Case B: still generating in background ────────────────
                if (this._running) {
                    card.setAttribute('data-open', '');
                    const label = card.querySelector('.ap-inline-label');
                    if (label) label.textContent = '⏳ Đang tạo ảnh nền — sẽ tự cập nhật khi xong';
                    return;
                }

                // ── Case C: real interruption (F5 / network drop) ─────────
                const orphanJobId = bubble.dataset.jobId || '';
                if (orphanJobId) {
                    fetch('/api/anime-pipeline/cancel', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ job_id: orphanJobId }),
                        keepalive: true,
                    }).catch(() => {});
                }
                card.setAttribute('data-open', '');
                const label = card.querySelector('.ap-inline-label');
                if (label) label.textContent = '⚠️ Pipeline bị gián đoạn (F5/mất kết nối)';
                card.querySelector('.thinking-pill__dots')?.remove();
                card.querySelector('.ap-inline-timer')?.remove();
                // Disable any leftover Stop button — its job is dead.
                const stopBtn = card.querySelector('.ap-inline-stop-btn');
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

    // ── Queue management ────────────────────────────────────────────

    /**
     * Enqueue a pending request. Creates a "holding" bubble immediately so
     * the user sees their queue position. Max 3 entries.
     */
    _enqueueRequest(prompt, chatContainer, opts) {
        const uid = Date.now().toString(36) + Math.random().toString(36).slice(2, 5);
        const position = this._queue.length + 1;

        const bubble = this._createInlineBubble(uid, prompt);
        bubble.dataset.apState = 'holding';

        // Override label to show holding position, hide body
        const card = bubble.querySelector('.ap-pipeline-card');
        const label = card?.querySelector('.ap-inline-label');
        if (label) label.textContent = `⏳ Holding ${position} — chờ pipeline sẵn sàng`;
        if (card) card.removeAttribute('data-open');

        // Stop button is meaningless while holding; keep it hidden
        const stopBtn = bubble.querySelector('.ap-inline-stop-btn');
        if (stopBtn) stopBtn.style.display = 'none';

        chatContainer.appendChild(bubble);
        chatContainer.scrollTop = chatContainer.scrollHeight;

        this._queue.push({ uid, prompt, opts, bubble, chatContainer });
    }

    /**
     * Start the next queued request when the pipeline is idle.
     * Called from _runInlineChat finally and _runContinuous end.
     */
    _processQueue() {
        if (this._running || this._continuousMode || this._queue.length === 0) return;
        const item = this._queue.shift();
        this._updateQueueLabels();
        this._runInlineChat(item.prompt, item.chatContainer, {
            ...item.opts,
            _isInternal: true,
            _holdingUid: item.uid,
            _holdingBubble: item.bubble,
        });
    }

    /**
     * Refresh "Holding N" labels after a queue position changes.
     */
    _updateQueueLabels() {
        this._queue.forEach((item, i) => {
            const liveBubble = document.getElementById(`ap-inline-${item.uid}`) || item.bubble;
            const lbl = liveBubble?.querySelector('.ap-inline-label');
            if (lbl) lbl.textContent = `⏳ Holding ${i + 1} — chờ pipeline sẵn sàng`;
        });
    }

    /**
     * Transition a holding bubble from "Holding N" state to live progress.
     * Called right before the SSE stream starts for a dequeued request.
     */
    _activateQueuedBubble(bubble) {
        bubble.dataset.apState = 'active';
        const card = bubble?.querySelector('.ap-pipeline-card');
        if (card) card.setAttribute('data-open', '');
        const lbl = card?.querySelector('.ap-inline-label');
        if (lbl) lbl.textContent = '⚡ Đang khởi động pipeline...';
        // Stop button stays hidden until job_id arrives via ap_status event
    }

    /**
     * Append a transient notice message (auto-dismisses after 5 s).
     * Used for queue-full and batch-mode rejection notices.
     */
    _appendQueueMessage(chatContainer, text) {
        const el = document.createElement('div');
        el.className = 'message assistant ap-queue-notice';
        el.innerHTML = `<div class="message__body"><div class="message-content" style="font-size:13px;color:var(--text-secondary,#aaa);padding:4px 0;opacity:0.85;">${text}</div></div>`;
        chatContainer.appendChild(el);
        chatContainer.scrollTop = chatContainer.scrollHeight;
        setTimeout(() => { if (el.isConnected) el.remove(); }, 5000);
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
