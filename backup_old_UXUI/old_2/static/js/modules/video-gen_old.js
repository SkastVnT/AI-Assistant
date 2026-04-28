/**
 * Video Generation ΓÇö Sora 2 (Full Feature)
 * Uses /api/video/* endpoints (OpenAI Videos API)
 *
 * Features:
 *  - Text-to-Video & Image-to-Video (up to 5 reference images)
 *  - Models: sora-2 ($0.10/s), sora-2-pro ($0.30/s)
 *  - Sizes: 1280x720, 720x1280, 1792x1024, 1024x1792
 *  - Durations: 4, 8, 12 seconds
 *  - Cancel/Stop in-progress jobs
 *  - Full-quality video download
 */

export class VideoGen {
    constructor() {
        this.isGenerating = false;
        this.pollTimer = null;
        this.currentJobId = null;
        this.selectedImages = [];   // Array of File objects (max 5)
        this.mode = 'text';         // 'text' or 'image'
        this.MAX_IMAGES = 5;
        this.COST_PER_SEC = { 'sora-2': 0.10, 'sora-2-pro': 0.30 };
    }

    // ΓöÇΓöÇ Modal Control ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    openModal() {
        const modal = document.getElementById('videoGenModal');
        if (modal) {
            modal.classList.add('active', 'open');
            this._updateCostEstimate();
            this._bindCostListeners();
            this._setupDragDrop();
        }
    }

    closeModal() {
        const modal = document.getElementById('videoGenModal');
        if (modal) {
            modal.classList.remove('active', 'open');
        }
        this._stopPolling();
    }

    switchTab(tab) {
        document.querySelectorAll('#videoGenModal .vg-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
            btn.classList.toggle('btn--primary', btn.dataset.tab === tab);
            btn.classList.toggle('btn--ghost', btn.dataset.tab !== tab);
        });
        document.querySelectorAll('#videoGenModal .vg-tab-panel').forEach(panel => {
            panel.style.display = panel.id === `vg-${tab}` ? 'block' : 'none';
        });
    }

    // ΓöÇΓöÇ Mode Toggle (text / image) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    switchMode(mode) {
        this.mode = mode;
        document.querySelectorAll('.vg-mode-btn').forEach(btn => {
            btn.classList.toggle('btn--primary', btn.dataset.mode === mode);
            btn.classList.toggle('btn--ghost', btn.dataset.mode !== mode);
        });
        const uploadZone = document.getElementById('vgImageUploadZone');
        if (uploadZone) uploadZone.style.display = mode === 'image' ? 'block' : 'none';
        const prompt = document.getElementById('vgPrompt');
        if (prompt) {
            prompt.placeholder = mode === 'image'
                ? 'Describe how to animate these images...'
                : 'Describe the video you want to create...';
        }
    }

    // ΓöÇΓöÇ Multi-Image Upload (max 5) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    _setupDragDrop() {
        if (this._dragBound) return;
        this._dragBound = true;
        const zone = document.getElementById('vgDropZone');
        if (!zone) return;

        zone.addEventListener('dragover', (e) => {
            e.preventDefault();
            zone.style.borderColor = 'var(--accent)';
            zone.style.background = 'var(--accent-soft, rgba(99,102,241,0.08))';
        });
        zone.addEventListener('dragleave', () => {
            zone.style.borderColor = 'var(--border-primary)';
            zone.style.background = 'var(--bg-tertiary)';
        });
        zone.addEventListener('drop', (e) => {
            e.preventDefault();
            zone.style.borderColor = 'var(--border-primary)';
            zone.style.background = 'var(--bg-tertiary)';
            const files = Array.from(e.dataTransfer?.files || []).filter(f => f.type.startsWith('image/'));
            this._addImages(files);
        });
    }

    handleImageSelect(input) {
        const files = Array.from(input?.files || []);
        if (files.length) this._addImages(files);
        if (input) input.value = '';
    }

    _addImages(files) {
        const remaining = this.MAX_IMAGES - this.selectedImages.length;
        if (remaining <= 0) {
            this._showStatus(`Maximum ${this.MAX_IMAGES} images allowed`, 'error');
            return;
        }
        const toAdd = files.slice(0, remaining);
        const maxSize = 20 * 1024 * 1024;

        for (const file of toAdd) {
            if (file.size > maxSize) {
                this._showStatus(`${file.name} too large (max 20 MB)`, 'error');
                continue;
            }
            this.selectedImages.push(file);
        }

        if (files.length > remaining) {
            this._showStatus(`Only ${remaining} more image(s) can be added (max ${this.MAX_IMAGES})`, 'error');
        }

        this._renderImagePreviews();
    }

    removeImage(index) {
        this.selectedImages.splice(index, 1);
        this._renderImagePreviews();
    }

    clearAllImages() {
        this.selectedImages = [];
        this._renderImagePreviews();
        const input = document.getElementById('vgImageInput');
        if (input) input.value = '';
    }

    _renderImagePreviews() {
        const grid = document.getElementById('vgImageGrid');
        const counter = document.getElementById('vgImageCounter');
        const dropContent = document.getElementById('vgDropContent');

        if (counter) {
            counter.textContent = `${this.selectedImages.length}/${this.MAX_IMAGES} images`;
            counter.style.color = this.selectedImages.length >= this.MAX_IMAGES ? 'var(--error, #ef4444)' : 'var(--text-tertiary)';
        }

        if (!grid) return;

        if (this.selectedImages.length === 0) {
            grid.style.display = 'none';
            if (dropContent) dropContent.style.display = 'block';
            return;
        }

        if (dropContent) dropContent.style.display = this.selectedImages.length >= this.MAX_IMAGES ? 'none' : 'block';
        grid.style.display = 'grid';
        grid.innerHTML = '';

        this.selectedImages.forEach((file, i) => {
            const item = document.createElement('div');
            item.className = 'vg-img-item';
            item.style.cssText = 'position:relative; border-radius:var(--radius-sm); overflow:hidden; background:var(--bg-secondary); aspect-ratio:1; border:1px solid var(--border-primary);';

            const img = document.createElement('img');
            img.style.cssText = 'width:100%; height:100%; object-fit:cover;';
            img.alt = file.name;

            const reader = new FileReader();
            reader.onload = (e) => { img.src = e.target.result; };
            reader.readAsDataURL(file);

            const removeBtn = document.createElement('button');
            removeBtn.innerHTML = 'Γ£ò';
            removeBtn.style.cssText = 'position:absolute; top:2px; right:2px; width:22px; height:22px; border-radius:50%; background:rgba(0,0,0,0.7); color:white; border:none; cursor:pointer; font-size:12px; display:flex; align-items:center; justify-content:center; line-height:1;';
            removeBtn.onclick = (e) => { e.stopPropagation(); this.removeImage(i); };

            const label = document.createElement('div');
            label.style.cssText = 'position:absolute; bottom:0; left:0; right:0; padding:2px 4px; background:rgba(0,0,0,0.6); color:white; font-size:10px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;';
            label.textContent = `${file.name} (${(file.size / 1024 / 1024).toFixed(1)}MB)`;

            item.appendChild(img);
            item.appendChild(removeBtn);
            item.appendChild(label);
            grid.appendChild(item);
        });
    }

    // ΓöÇΓöÇ Cost Estimate ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    _bindCostListeners() {
        if (this._costBound) return;
        this._costBound = true;
        ['vgDuration', 'vgModel'].forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('change', () => this._updateCostEstimate());
        });
    }

    _updateCostEstimate() {
        const duration = parseInt(document.getElementById('vgDuration')?.value || '8');
        const model = document.getElementById('vgModel')?.value || 'sora-2';
        const rate = this.COST_PER_SEC[model] || 0.10;
        const cost = (duration * rate).toFixed(2);
        const el = document.getElementById('vgCostEstimate');
        if (el) el.innerHTML = `≡ƒÆ░ Estimated cost: <strong>$${cost}</strong> (${duration}s ├ù $${rate}/s)`;
    }

    // ΓöÇΓöÇ Generate ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    async generate() {
        if (this.isGenerating) return;

        const prompt = document.getElementById('vgPrompt')?.value?.trim();
        if (!prompt) {
            this._showStatus('Please enter a prompt!', 'error');
            return;
        }

        const size = document.getElementById('vgResolution')?.value || '1280x720';
        const seconds = document.getElementById('vgDuration')?.value || '8';
        const model = document.getElementById('vgModel')?.value || 'sora-2';

        if (this.mode === 'image' && this.selectedImages.length === 0) {
            this._showStatus('Please upload at least one image!', 'error');
            return;
        }

        this.isGenerating = true;
        const btn = document.getElementById('vgGenerateBtn');
        if (btn) { btn.disabled = true; btn.innerHTML = 'ΓÅ│ Submitting...'; }

        this._hideResult();
        const imgCount = this.selectedImages.length;
        const modeLabel = this.mode === 'image' ? `Image-to-Video (${imgCount} image${imgCount > 1 ? 's' : ''})` : 'Text-to-Video';
        this._showProgress(`Submitting ${modeLabel} to OpenAI...`, 0);

        try {
            let resp;
            if (this.mode === 'image' && this.selectedImages.length > 0) {
                const formData = new FormData();
                formData.append('prompt', prompt);
                formData.append('size', size);
                formData.append('seconds', seconds);
                formData.append('model', model);
                this.selectedImages.forEach(file => formData.append('images', file));
                resp = await fetch('/api/video/generate', {
                    method: 'POST',
                    body: formData,
                });
            } else {
                resp = await fetch('/api/video/generate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt, size, seconds, model }),
                });
            }
            const data = await resp.json();

            if (!resp.ok) {
                throw new Error(data.error || `HTTP ${resp.status}`);
            }

            this.currentJobId = data.id;
            this._showStatus(`Job submitted: ${data.id}`, 'info');
            this._showProgress('Queued ΓÇö waiting for OpenAI...', 0);
            this._showCancelBtn(true);
            this._startPolling(data.id);
        } catch (e) {
            this._showStatus(`Error: ${e.message}`, 'error');
            this._hideProgress();
        } finally {
            this.isGenerating = false;
            if (btn) { btn.disabled = false; btn.innerHTML = '≡ƒÄ¼ Generate Video'; }
        }
    }

    // ΓöÇΓöÇ Cancel / Stop Job ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    async cancelJob() {
        if (!this.currentJobId) return;

        const cancelBtn = document.getElementById('vgCancelBtn');
        if (cancelBtn) { cancelBtn.disabled = true; cancelBtn.innerHTML = 'ΓÅ│ Cancelling...'; }

        try {
            const resp = await fetch(`/api/video/cancel/${this.currentJobId}`, { method: 'POST' });
            const data = await resp.json();

            this._stopPolling();
            this._hideProgress();
            this._showCancelBtn(false);

            if (resp.ok) {
                this._showStatus(`Γ¢ö Job cancelled: ${this.currentJobId}`, 'info');
            } else {
                this._showStatus(`Cancel failed: ${data.error || 'Unknown error'}`, 'error');
            }
        } catch (e) {
            this._showStatus(`Cancel error: ${e.message}`, 'error');
        } finally {
            this.currentJobId = null;
            if (cancelBtn) { cancelBtn.disabled = false; cancelBtn.innerHTML = 'Γ¢ö Stop / Cancel'; }
        }
    }

    _showCancelBtn(show) {
        const btn = document.getElementById('vgCancelBtn');
        if (btn) btn.style.display = show ? 'block' : 'none';
    }

    // ΓöÇΓöÇ Polling ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    _startPolling(jobId) {
        this._stopPolling();
        let interval = 2000;
        let elapsed = 0;

        const poll = async () => {
            try {
                const resp = await fetch(`/api/video/status/${jobId}`);
                const data = await resp.json();

                if (!resp.ok) throw new Error(data.error || 'Poll failed');

                const status = data.status;
                const progress = data.progress || 0;

                // Update progress meta info
                const meta = document.getElementById('vgProgressMeta');
                if (meta) {
                    const parts = [];
                    if (data.model) parts.push(data.model);
                    if (data.size) parts.push(data.size);
                    if (data.seconds) parts.push(`${data.seconds}s`);
                    if (data.cost_estimate) parts.push(data.cost_estimate);
                    meta.textContent = parts.join(' ΓÇó ');
                }

                if (status === 'completed') {
                    this._stopPolling();
                    this._showProgress('Completed!', 100);
                    this._showCancelBtn(false);
                    this._showVideo(jobId, data);
                    this._showStatus('Video ready!', 'success');
                    return;
                }

                if (status === 'failed') {
                    this._stopPolling();
                    this._showCancelBtn(false);
                    this._showStatus(`Failed: ${data.error || 'Unknown error'}`, 'error');
                    this._hideProgress();
                    return;
                }

                const label = status === 'queued' ? 'Queued ΓÇö waiting...' : `Generating... ${progress}%`;
                this._showProgress(label, progress);

                elapsed += interval;
                if (elapsed > 30000 && interval < 5000) interval = 5000;

                this.pollTimer = setTimeout(poll, interval);
            } catch (e) {
                console.error('[VideoGen] Poll error:', e);
                this.pollTimer = setTimeout(poll, 5000);
            }
        };

        this.pollTimer = setTimeout(poll, interval);
    }

    _stopPolling() {
        if (this.pollTimer) { clearTimeout(this.pollTimer); this.pollTimer = null; }
    }

    // ΓöÇΓöÇ UI Helpers ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    _showStatus(msg, type = 'info') {
        const el = document.getElementById('vgStatus');
        if (!el) return;
        const colors = { error: 'var(--error, #ef4444)', success: 'var(--success, #22c55e)', info: 'var(--text-tertiary)' };
        el.style.color = colors[type] || colors.info;
        el.textContent = msg;
    }

    _showProgress(label, pct) {
        const wrap = document.getElementById('vgProgress');
        if (wrap) wrap.style.display = 'block';
        const lbl = document.getElementById('vgProgressLabel');
        if (lbl) lbl.textContent = label;
        const pctEl = document.getElementById('vgProgressPct');
        if (pctEl) pctEl.textContent = pct > 0 ? `${pct}%` : '';
        const bar = document.getElementById('vgProgressBar');
        if (bar) bar.style.width = `${pct}%`;
    }

    _hideProgress() {
        const wrap = document.getElementById('vgProgress');
        if (wrap) wrap.style.display = 'none';
        this._showCancelBtn(false);
    }

    _showVideo(jobId, meta) {
        const wrap = document.getElementById('vgResult');
        if (wrap) wrap.style.display = 'block';
        const video = document.getElementById('vgVideo');
        if (video) {
            // Use stream endpoint for in-browser playback (full quality)
            video.src = `/api/video/stream/${jobId}`;
            video.load();
        }
        const metaEl = document.getElementById('vgResultMeta');
        if (metaEl) {
            const parts = [];
            if (meta.model) parts.push(`Model: ${meta.model}`);
            if (meta.aspect_ratio) parts.push(`Aspect: ${meta.aspect_ratio}`);
            else if (meta.size) parts.push(`Size: ${meta.size}`);
            if (meta.seconds) parts.push(`Duration: ${meta.seconds}s`);
            if (meta.cost_estimate) parts.push(`Cost: ${meta.cost_estimate}`);
            metaEl.textContent = parts.join(' ΓÇó ');
        }
    }

    _hideResult() {
        const wrap = document.getElementById('vgResult');
        if (wrap) wrap.style.display = 'none';
    }

    downloadCurrent() {
        if (!this.currentJobId) return;
        // Use the download endpoint (as_attachment=True) for full quality file
        const a = document.createElement('a');
        a.href = `/api/video/download/${this.currentJobId}`;
        a.download = `sora2_${this.currentJobId}.mp4`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
    }

    generateAnother() {
        this._hideResult();
        this._hideProgress();
        this._showStatus('Ready', 'info');
        this.currentJobId = null;
        this.clearAllImages();
    }

    // ΓöÇΓöÇ Jobs List ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    async loadJobs() {
        const container = document.getElementById('vgJobsList');
        if (!container) return;
        container.innerHTML = '<p style="color: var(--text-tertiary); text-align: center; padding: 16px;">Loading...</p>';

        try {
            const resp = await fetch('/api/video/list?limit=20');
            const data = await resp.json();
            const jobs = data.videos || [];

            if (jobs.length === 0) {
                container.innerHTML = '<p style="color: var(--text-tertiary); text-align: center; padding: 24px;">No videos yet. Generate your first video!</p>';
                return;
            }

            container.innerHTML = jobs.map(job => {
                const statusIcon = { completed: '≡ƒƒó', failed: '≡ƒö┤', in_progress: '≡ƒƒí', queued: 'ΓÜ¬', cancelled: 'Γ¢ö' }[job.status] || 'ΓÜ¬';
                const date = job.created_at ? new Date(job.created_at).toLocaleString() : '';
                const prompt = (job.prompt || '').slice(0, 80) + ((job.prompt || '').length > 80 ? '...' : '');
                const isReady = job.status === 'completed';
                const isActive = job.status === 'in_progress' || job.status === 'queued';
                const isImg2Vid = Array.isArray(job.source_images) && job.source_images.length > 0;
                const modeTag = isImg2Vid
                    ? `<span class="vg-tag vg-tag--img">≡ƒû╝∩╕Å ImageΓåÆVideo</span>`
                    : `<span class="vg-tag vg-tag--txt">≡ƒô¥ TextΓåÆVideo</span>`;
                return `
                    <div class="vg-job-card">
                        <div class="vg-job-header">
                            <div class="vg-job-status">${statusIcon} ${this._escapeHtml(job.status)} ${modeTag}</div>
                            <span class="vg-job-date">${this._escapeHtml(date)}</span>
                        </div>
                        <p class="vg-job-prompt">${this._escapeHtml(prompt)}</p>
                        <div class="vg-job-meta">
                            <span>${this._escapeHtml(job.model || '')}</span>
                            <span>${this._escapeHtml(job.aspect_ratio || job.size || '')}</span>
                            <span>${this._escapeHtml(String(job.seconds || ''))}s</span>
                            <span>${this._escapeHtml(job.cost_estimate || '')}</span>
                        </div>
                        <div class="vg-job-actions">
                            ${isReady ? `<button class="btn btn--sm btn--primary vg-job-action-btn" onclick="window.videoGen?.playJobVideo('${this._escapeHtml(job.id)}')" title="Watch video">Γû╢∩╕Å Watch</button>` : ''}
                            ${isReady ? `<a href="/api/video/download/${this._escapeHtml(job.id)}" download class="btn btn--sm btn--ghost vg-job-action-btn" title="Download">≡ƒôÑ Download</a>` : ''}
                            ${isActive ? `<button class="btn btn--sm vg-job-action-btn" onclick="window.videoGen?._cancelFromList('${this._escapeHtml(job.id)}')" style="color: var(--error, #ef4444);">Γ¢ö Cancel</button>` : ''}
                        </div>
                    </div>`;
            }).join('');
        } catch (e) {
            container.innerHTML = `<p style="color: var(--error, #ef4444); text-align: center; padding: 16px;">Error: ${this._escapeHtml(e.message)}</p>`;
        }
    }

    playJobVideo(jobId) {
        // Switch to Generate tab and show the video
        this.switchTab('generate');
        this._showVideo(jobId, {});
        this._showStatus('Video ready!', 'success');
        this.currentJobId = jobId;
        // Load meta from status endpoint for display
        fetch(`/api/video/status/${jobId}`).then(r => r.json()).then(data => {
            if (data && !data.error) this._showVideo(jobId, data);
        }).catch(() => {});
    }

    async _cancelFromList(jobId) {
        try {
            await fetch(`/api/video/cancel/${jobId}`, { method: 'POST' });
            this._showStatus(`Job ${jobId} cancelled`, 'info');
            this.loadJobs();
        } catch (e) {
            this._showStatus(`Cancel failed: ${e.message}`, 'error');
        }
    }

    _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }
}
