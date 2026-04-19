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
    { key: 'critique',         icon: '🔍',  label: 'Critique' },
    { key: 'upscale',          icon: '📐',  label: 'Upscale' },
];

export class AnimePipeline {
    constructor() {
        /** @type {AbortController|null} */
        this._abort = null;
        this._running = false;
        this._debug = false;
        this._available = null;  // cached availability
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
     */
    openModalWithPrompt(prompt) {
        // Prefer inline chat mode so the result lands directly in the conversation.
        const chatContainer = document.getElementById('chatContainer');
        if (chatContainer) {
            this._runInlineChat(prompt, chatContainer);
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
     */
    async _runInlineChat(prompt, chatContainer) {
        if (this._running) return;
        this._running = true;

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
        };

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

    /** Build the initial inline pipeline message bubble. */
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
        div.innerHTML = `
            <div class="message__avatar message__avatar--agent">
                <img src="/static/icons/favicon.svg" class="avatar-img" alt="" draggable="false">
            </div>
            <div class="message__body">
                <div class="message-content">
                    <details class="ap-inline-progress" open>
                        <summary class="ap-inline-summary">
                            <div class="thinking-pill__dots">
                                <span></span><span></span><span></span>
                            </div>
                            <span class="ap-inline-label">Đang tạo ảnh anime…</span>
                            <span class="ap-inline-timer" id="ap-timer-${uid}">0.0s</span>
                        </summary>
                        <div class="ap-inline-stages" id="ap-stages-${uid}">${stagesHtml}</div>
                        <div class="ap-inline-current" id="ap-current-${uid}">Khởi động…</div>
                    </details>
                </div>
            </div>`;
        return div;
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
                this._inlineSetCurrent(uid, data.message || '');
                break;
            case 'ap_layer_plan':
                this._inlineShowLayerChips(uid, data);
                break;
            case 'ap_stage_start': {
                this._inlineSetStage(uid, data.stage, 'active');
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
                summary.innerHTML = `
                    <span class="ap-inline-done-icon">🎨</span>
                    <span class="ap-inline-label">✅ Anime Pipeline · ${elapsed}s</span>`;
            }
        }

        if (imgSrc) {
            // Append the result image after the details block
            const msgContent = bubble.querySelector('.message-content');
            const resultDiv = document.createElement('div');
            resultDiv.innerHTML = `
                <div class="igv2-chat-image" data-prompt="${promptAttr}">
                    <img src="${imgSrc}" alt="Anime Pipeline result" data-igv2-open="${imgSrc}">
                    <div class="igv2-chat-meta">🎨 Anime Pipeline · ${elapsed}s${data.local_url ? ' · 💾 saved' : ''}</div>
                    <div class="ap-inline-result-btns">
                        <button class="ap-inline-btn" data-action="download" data-job="${jobId}" data-prompt="${promptAttr}">📥 Tải ảnh</button>
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

            // Tạo lại: re-run inline with same prompt
            resultDiv.querySelector('[data-action="regenerate"]')?.addEventListener('click', () => {
                this._runInlineChat(prompt, chatContainer);
            });

            // Chỉnh sửa: toggle edit box
            const editBox = resultDiv.querySelector('.ap-inline-edit-box');
            resultDiv.querySelector('[data-action="edit"]')?.addEventListener('click', () => {
                editBox.style.display = editBox.style.display === 'none' ? 'block' : 'none';
                if (editBox.style.display === 'block') {
                    editBox.querySelector('textarea')?.focus();
                }
            });

            // Run with edited prompt
            resultDiv.querySelector('[data-action="edit-run"]')?.addEventListener('click', () => {
                const newPrompt = editBox.querySelector('textarea')?.value?.trim();
                if (newPrompt) {
                    editBox.style.display = 'none';
                    this._runInlineChat(newPrompt, chatContainer);
                }
            });

            // Cancel edit
            resultDiv.querySelector('[data-action="edit-cancel"]')?.addEventListener('click', () => {
                editBox.style.display = 'none';
            });

            // Wire image click-to-open if igv2 handler is available
            const img = resultDiv.querySelector('img');
            if (img) {
                img.addEventListener('click', () => {
                    window.chatApp?.imageGenV2?.openImageModal?.(imgSrc);
                });
            }

            msgContent?.appendChild(resultDiv.firstElementChild);
            chatContainer.scrollTop = chatContainer.scrollHeight;

            // Save to session
            window.chatApp?.saveCurrentSession?.(true);
        }
    }

    /** Show a fatal error state in the inline bubble. */
    _setInlineError(bubble, uid, message) {
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
                        this._handleEvent(currentEvent, data);
                    } catch { /* ignore malformed */ }
                }
            }
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
        // Reset beauty_pass and critique stages in the modal stage list
        this._setStageState('beauty_pass', 'pending');
        this._setStageState('critique', 'pending');
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
        if (imgEl && data.image_b64) {
            imgEl.src = 'data:image/png;base64,' + data.image_b64;
            imgEl.style.display = '';
        } else if (imgEl) {
            imgEl.style.display = 'none';
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
        if (!this._lastResult?.image_b64) return;
        const app = window.chatApp;
        if (!app) return;

        const chatContainer = document.getElementById('chat-container');
        if (!chatContainer) return;

        const prompt = (document.getElementById('apPrompt')?.value || '').trim();
        const latency = this._lastResult.total_latency_ms
            ? `${(this._lastResult.total_latency_ms / 1000).toFixed(1)}s` : '';
        const meta = `🎨 Anime Pipeline${latency ? ' · ' + latency : ''}`;
        const imgSrc = 'data:image/png;base64,' + this._lastResult.image_b64;
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
        if (!this._lastResult?.image_b64) return;

        const a = document.createElement('a');
        a.href = 'data:image/png;base64,' + this._lastResult.image_b64;
        a.download = `anime_pipeline_${this._lastResult.job_id || 'result'}.png`;
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
}
