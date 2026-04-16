/**
 * Image Generation V2 ΓÇö Multi-Provider System
 * Uses the new /api/image-gen/* endpoints backed by:
 * fal.ai, Replicate, BFL, OpenAI, Together.ai, StepFun, ComfyUI (local)
 * 
 * Features:
 * - Smart provider auto-selection
 * - LLM prompt enhancement
 * - Style presets (15+)
 * - Conversational editing (iterative refinement)
 * - Gallery with history
 * - Cost/latency tracking
 */

export class ImageGenV2 {
    constructor(apiService) {
        this.apiService = apiService;
        this.providers = [];
        this.styles = [];
        this.isGenerating = false;
        this.currentImage = null;
        this.conversationId = '';
        this.gallery = [];
        this.stats = null;
    }

    // ΓöÇΓöÇ Initialization ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    async init() {
        try {
            await Promise.all([
                this.loadProviders(),
                this.loadStyles(),
            ]);
            console.log('[ImageGenV2] Initialized with', this.providers.length, 'providers,', this.styles.length, 'styles');
        } catch (e) {
            console.warn('[ImageGenV2] Init partial:', e);
        }
    }

    async loadProviders() {
        try {
            const resp = await fetch('/api/image-gen/providers');
            const data = await resp.json();
            this.providers = data.providers || [];
            this._renderProviderSelect();
        } catch (e) {
            console.warn('[ImageGenV2] Failed to load providers:', e);
        }
    }

    async loadStyles() {
        try {
            const resp = await fetch('/api/image-gen/styles');
            const data = await resp.json();
            this.styles = data.styles || [];
            this._renderStyleGrid();
        } catch (e) {
            console.warn('[ImageGenV2] Failed to load styles:', e);
        }
    }

    // ΓöÇΓöÇ Modal Control ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    openModal() {
        const modal = document.getElementById('imageGenV2Modal');
        if (modal) {
            modal.classList.add('active', 'open');
            this.init();
        }
    }

    closeModal() {
        const modal = document.getElementById('imageGenV2Modal');
        if (modal) {
            modal.classList.remove('active', 'open');
        }
    }

    switchTab(tab) {
        // Update tab buttons
        document.querySelectorAll('#imageGenV2Modal .igv2-tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        // Update tab panels
        document.querySelectorAll('#imageGenV2Modal .igv2-tab-panel').forEach(panel => {
            panel.style.display = panel.id === `igv2-${tab}` ? 'block' : 'none';
        });
    }

    // ΓöÇΓöÇ Generate ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    async generate() {
        if (this.isGenerating) return;

        const prompt = document.getElementById('igv2Prompt')?.value?.trim();
        if (!prompt) {
            this._showStatus('Nhß║¡p m├┤ tß║ú ß║únh!', 'error');
            return;
        }

        this.isGenerating = true;
        const btn = document.getElementById('igv2GenerateBtn');
        const statusEl = document.getElementById('igv2Status');
        const resultArea = document.getElementById('igv2Result');

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="animate-spin">ΓÅ│</span> ─Éang tß║ío ß║únh...';
        }
        if (statusEl) statusEl.textContent = '≡ƒñû ─Éang enhance prompt vß╗¢i AI...';

        try {
            const quality = document.getElementById('igv2Quality')?.value || 'auto';
            const style = document.getElementById('igv2Style')?.value || '';
            const provider = document.getElementById('igv2Provider')?.value || '';
            const width = parseInt(document.getElementById('igv2Width')?.value || '1024');
            const height = parseInt(document.getElementById('igv2Height')?.value || '1024');
            const enhance = document.getElementById('igv2Enhance')?.checked !== false;
            const steps = parseInt(document.getElementById('igv2Steps')?.value || '28');
            const guidance = parseFloat(document.getElementById('igv2Guidance')?.value || '3.5');

            if (statusEl) statusEl.textContent = '≡ƒÄ¿ ─Éang tß║ío ß║únh...';

            const resp = await fetch('/api/image-gen/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt,
                    quality,
                    style: style || null,
                    width,
                    height,
                    provider: provider || null,
                    enhance,
                    steps,
                    guidance,
                    conversation_id: this.conversationId,
                    num_images: 1,
                }),
            });

            const data = await resp.json();

            if (data.success) {
                this.currentImage = data;
                this._renderResult(data);
                this._showStatus(
                    `Γ£à Tß║ío th├ánh c├┤ng! Provider: ${data.provider} | Model: ${data.model} | ${data.latency_ms}ms | $${data.cost_usd}`,
                    'success'
                );

                // Also inject into chat
                this._addImageToChat(data, prompt);

                // Refresh gallery
                this.loadGallery();
            } else {
                this._showStatus(`Γ¥î Lß╗ùi: ${data.error}`, 'error');
                if (resultArea) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'igv2-error';
                    const errorP = document.createElement('p');
                    errorP.textContent = 'Γ¥î ' + (data.error || 'Unknown error');
                    errorDiv.appendChild(errorP);
                    const promptP = document.createElement('p');
                    promptP.className = 'text-sm mt-2';
                    promptP.textContent = 'Prompt used: ' + (data.prompt_used || prompt);
                    errorDiv.appendChild(promptP);
                    resultArea.innerHTML = '';
                    resultArea.appendChild(errorDiv);
                }
            }
        } catch (e) {
            console.error('[ImageGenV2] Generate error:', e);
            this._showStatus(`Γ¥î Lß╗ùi: ${e.message}`, 'error');
        } finally {
            this.isGenerating = false;
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '≡ƒÄ¿ Tß║ío ß║únh';
            }
        }
    }

    // ΓöÇΓöÇ Edit (iterative) ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    async editImage() {
        if (this.isGenerating) return;

        const prompt = document.getElementById('igv2EditPrompt')?.value?.trim();
        if (!prompt) {
            this._showStatus('Nhß║¡p lß╗çnh chß╗ënh sß╗¡a!', 'error');
            return;
        }

        this.isGenerating = true;
        const btn = document.getElementById('igv2EditBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="animate-spin">ΓÅ│</span> ─Éang chß╗ënh sß╗¡a...';
        }

        try {
            const strength = parseFloat(document.getElementById('igv2EditStrength')?.value || '0.75');
            const provider = document.getElementById('igv2EditProvider')?.value || '';

            const resp = await fetch('/api/image-gen/edit', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt,
                    conversation_id: this.conversationId,
                    strength,
                    provider: provider || null,
                }),
            });

            const data = await resp.json();

            if (data.success) {
                this.currentImage = data;
                this._renderResult(data);
                this._showStatus(`Γ£à Chß╗ënh sß╗¡a th├ánh c├┤ng! ${data.provider} | ${data.latency_ms}ms`, 'success');
                this._addImageToChat(data, `Γ£Å∩╕Å Edit: ${prompt}`);
                this.loadGallery();
            } else {
                this._showStatus(`Γ¥î ${data.error}`, 'error');
            }
        } catch (e) {
            this._showStatus(`Γ¥î ${e.message}`, 'error');
        } finally {
            this.isGenerating = false;
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = 'Γ£Å∩╕Å Chß╗ënh sß╗¡a';
            }
        }
    }

    // ΓöÇΓöÇ Gallery ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    async loadGallery() {
        try {
            const resp = await fetch(`/api/image-gen/gallery?limit=20&conversation_id=${this.conversationId}`);
            const data = await resp.json();
            this.gallery = data.images || [];
            this._renderGallery();
        } catch (e) {
            console.warn('[ImageGenV2] Gallery load failed:', e);
        }
    }

    async loadStats() {
        try {
            const resp = await fetch('/api/image-gen/stats');
            this.stats = await resp.json();
            this._renderStats();
        } catch (e) {
            console.warn('[ImageGenV2] Stats load failed:', e);
        }
    }

    async deleteImage(imageId) {
        try {
            await fetch(`/api/image-gen/images/${imageId}`, { method: 'DELETE' });
            this.loadGallery();
        } catch (e) {
            console.warn('[ImageGenV2] Delete failed:', e);
        }
    }

    // ΓöÇΓöÇ Chat Integration ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    /**
     * Called from the chat flow when image generation intent is detected.
     * Generates image inline in chat without opening modal.
     */
    async generateFromChat(message, conversationId) {
        this.conversationId = conversationId || this.conversationId;
        
        try {
            const resp = await fetch('/api/image-gen/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: message,
                    quality: 'auto',
                    enhance: true,
                    conversation_id: this.conversationId,
                    num_images: 1,
                }),
            });

            const data = await resp.json();
            return data;
        } catch (e) {
            return { success: false, error: e.message };
        }
    }

    /**
     * Streaming version of generateFromChat.
     * Uses SSE to show real-time status (thinking, provider switching, etc.)
     * 
     * @param {string} message - User prompt
     * @param {string} conversationId - Session ID
     * @param {AbortSignal} [abortSignal] - Optional abort signal
     * @param {Object} callbacks - Event callbacks:
     *   onStatus({step, phase, ...})
     *   onProviderTry({provider, priority, attempt, total_providers})
     *   onProviderFail({provider, error, attempt})
     *   onProviderSuccess({provider, model, latency_ms})
     *   onResult({success, provider, model, images_url, ...})
     *   onSaved({images: [{url, image_id, local_path}]})
     *   onError({error})
     * @returns {Promise<Object>} Final result data
     */
    async generateFromChatStream(message, conversationId, abortSignal = null, callbacks = {}, options = {}) {
        this.conversationId = conversationId || this.conversationId;

        try {
            const resp = await fetch('/api/image-gen/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt: message,
                    quality: options.quality || 'auto',
                    provider: options.provider || undefined,
                    enhance: true,
                    conversation_id: this.conversationId,
                    num_images: 1,
                }),
                signal: abortSignal,
            });

            if (!resp.ok) {
                const errText = await resp.text();
                return { success: false, error: `HTTP ${resp.status}: ${errText}` };
            }

            const reader = resp.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let finalResult = null;
            let savedData = null;
            let currentEvent = 'message';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop(); // Keep incomplete line
                for (const line of lines) {
                    if (line.startsWith('event: ')) {
                        currentEvent = line.slice(7).trim();
                    } else if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            switch (currentEvent) {
                                case 'status':
                                    if (callbacks.onStatus) callbacks.onStatus(data);
                                    break;
                                case 'provider_try':
                                    if (callbacks.onProviderTry) callbacks.onProviderTry(data);
                                    break;
                                case 'provider_fail':
                                    if (callbacks.onProviderFail) callbacks.onProviderFail(data);
                                    break;
                                case 'provider_success':
                                    if (callbacks.onProviderSuccess) callbacks.onProviderSuccess(data);
                                    break;
                                case 'result':
                                    finalResult = data;
                                    if (callbacks.onResult) callbacks.onResult(data);
                                    break;
                                case 'saved':
                                    savedData = data;
                                    if (callbacks.onSaved) callbacks.onSaved(data);
                                    break;
                                case 'error':
                                    if (callbacks.onError) callbacks.onError(data);
                                    return { success: false, error: data.error };
                            }
                        } catch (e) {
                            // Skip invalid JSON
                        }
                    } else if (line === '') {
                        // Empty line = end of SSE message, reset event type
                        currentEvent = 'message';
                    }
                }
            }

            // Merge saved image info into result
            if (finalResult && savedData) {
                finalResult.images = savedData.images;
            }
            return finalResult || { success: false, error: 'No result received' };
        } catch (e) {
            if (e.name === 'AbortError') throw e;
            return { success: false, error: e.message };
        }
    }

    /**
     * Detect if a message is an image generation request.
     * Enhanced detection with better accuracy ΓÇö avoids false positives.
     */
    static isImageRequest(message) {
        const lower = message.toLowerCase().trim();
        
        // Command triggers (highest confidence ΓÇö always match)
        const commandTriggers = ['/img ', '/image ', '/draw ', '/gen ', '/paint '];
        if (commandTriggers.some(t => lower.startsWith(t))) return true;
        
        // Vietnamese triggers (start-of-sentence)
        const viStartTriggers = [
            'vß║╜ ', 'vß║╜ cho', 'vß║╜ gi├║p', 'h├úy vß║╜', 'tß║ío ß║únh', 'tß║ío h├¼nh',
            'sinh ß║únh', 'tß║ío mß╗Öt bß╗⌐c', 'vß║╜ mß╗Öt', 'tß║ío mß╗Öt ß║únh',
            'tß║ío h├¼nh ß║únh', 'h├úy tß║ío', 'gi├║p t├┤i vß║╜', 'gi├║p m├¼nh vß║╜',
        ];
        if (viStartTriggers.some(t => lower.startsWith(t))) return true;
        
        // English triggers (start-of-sentence)
        const enStartTriggers = [
            'draw ', 'draw me', 'create image', 'create an image',
            'generate image', 'generate an image', 'generate a ',
            'make an image', 'make me an image', 'paint ', 'paint me',
            'illustrate ', 'design an image', 'render ',
            'create a picture', 'make a picture',
        ];
        if (enStartTriggers.some(t => lower.startsWith(t))) return true;
        
        // Contextual patterns (require keyword + image-related word)
        const imageWords = ['ß║únh', 'h├¼nh', 'image', 'picture', 'photo', 'illustration', 'artwork'];
        const actionWords = ['tß║ío', 'vß║╜', 'create', 'generate', 'make', 'draw'];
        
        const hasImage = imageWords.some(w => lower.includes(w));
        const hasAction = actionWords.some(w => lower.includes(w));
        
        // Only match if BOTH action AND image word are present
        if (hasImage && hasAction) return true;
        
        return false;
    }

    /**
     * Detect if a message is an image edit request (needs previous image).
     * More precise to avoid triggering on regular text editing questions.
     */
    static isEditRequest(message) {
        const lower = message.toLowerCase().trim();
        
        // Must reference a previous image
        const imageRef = [
            'ß║únh tr╞░ß╗¢c', 'ß║únh vß╗½a', 'c├íi ß║únh', 'bß╗⌐c ß║únh',
            'previous image', 'last image', 'that image', 'the image',
        ];
        const hasImageRef = imageRef.some(t => lower.includes(t));
        
        if (!hasImageRef) return false;
        
        // And must have an edit action
        const editActions = [
            'th├¬m', 'bß╗Å', 'x├│a', '─æß╗òi', 'thay ─æß╗òi', 'sß╗¡a', 'chß╗ënh',
            'add', 'remove', 'change', 'edit', 'modify', 'replace',
        ];
        return editActions.some(t => lower.includes(t));
    }

    // ΓöÇΓöÇ Private: Rendering ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    _renderResult(data) {
        const resultArea = document.getElementById('igv2Result');
        if (!resultArea) return;

        // Get display URL
        let imgSrc = '';
        if (data.images?.length > 0 && data.images[0].url) {
            imgSrc = data.images[0].url;
        } else if (data.images_url?.length > 0) {
            imgSrc = data.images_url[0];
        }

        resultArea.innerHTML = `
            <div class="igv2-image-result">
                <img src="${imgSrc}" alt="Generated" class="igv2-result-img" 
                     onclick="window.open('${imgSrc}', '_blank')" title="Click to open full size">
                <div class="igv2-result-meta">
                    <div class="igv2-meta-row">
                        <span class="igv2-meta-label">Provider:</span>
                        <span class="igv2-meta-value">${data.provider}</span>
                    </div>
                    <div class="igv2-meta-row">
                        <span class="igv2-meta-label">Model:</span>
                        <span class="igv2-meta-value">${data.model}</span>
                    </div>
                    <div class="igv2-meta-row">
                        <span class="igv2-meta-label">Prompt:</span>
                        <span class="igv2-meta-value igv2-prompt-text">${data.prompt_used || ''}</span>
                    </div>
                    <div class="igv2-meta-row">
                        <span class="igv2-meta-label">Latency:</span>
                        <span class="igv2-meta-value">${Math.round(data.latency_ms)}ms</span>
                    </div>
                    <div class="igv2-meta-row">
                        <span class="igv2-meta-label">Cost:</span>
                        <span class="igv2-meta-value">$${data.cost_usd}</span>
                    </div>
                </div>
                <div class="igv2-result-actions">
                    <button onclick="window.imageGenV2?.downloadImage('${imgSrc}')" class="igv2-action-btn">≡ƒÆ╛ Download</button>
                    <button onclick="window.imageGenV2?.copyToChat('${imgSrc}')" class="igv2-action-btn">≡ƒôï Copy to Chat</button>
                    <button onclick="document.getElementById('igv2EditPrompt')?.focus(); window.imageGenV2?.switchTab('edit')" class="igv2-action-btn">Γ£Å∩╕Å Edit</button>
                </div>
            </div>
        `;
    }

    _renderProviderSelect() {
        const select = document.getElementById('igv2Provider');
        const editSelect = document.getElementById('igv2EditProvider');
        if (!select) return;

        const options = '<option value="">≡ƒñû Auto (Best available)</option>' +
            this.providers
                .filter(p => p.available)
                .map(p => `<option value="${p.name}">${this._providerIcon(p.name)} ${p.name} (${p.tier}${p.cost_per_image > 0 ? ' ~$' + p.cost_per_image : ' FREE'})</option>`)
                .join('');

        select.innerHTML = options;
        if (editSelect) editSelect.innerHTML = options;
    }

    _renderStyleGrid() {
        const container = document.getElementById('igv2StyleGrid');
        const select = document.getElementById('igv2Style');
        if (!container && !select) return;

        if (select) {
            select.innerHTML = '<option value="">None (auto)</option>' +
                this.styles.map(s => `<option value="${s.name}">${this._styleIcon(s.name)} ${s.name}</option>`).join('');
        }

        if (container) {
            container.innerHTML = this.styles.map(s => `
                <button class="igv2-style-chip" data-style="${s.name}" 
                        onclick="window.imageGenV2?._selectStyle('${s.name}')"
                        title="${s.description}">
                    ${this._styleIcon(s.name)} ${s.name}
                </button>
            `).join('');
        }
    }

    _selectStyle(name) {
        // Update select
        const select = document.getElementById('igv2Style');
        if (select) select.value = name;

        // Update chips
        document.querySelectorAll('.igv2-style-chip').forEach(chip => {
            chip.classList.toggle('active', chip.dataset.style === name);
        });
    }

    _renderGallery() {
        const container = document.getElementById('igv2Gallery');
        if (!container) return;

        if (this.gallery.length === 0) {
            container.innerHTML = '<p class="igv2-gallery-empty">No images yet. Generate your first image!</p>';
            return;
        }

        container.innerHTML = this.gallery.map(img => `
            <div class="igv2-gallery-item" onclick="window.open('/api/image-gen/images/${img.image_id}', '_blank')">
                <img src="/api/image-gen/images/${img.image_id}" alt="${img.prompt?.substring(0, 30)}" loading="lazy">
                <div class="igv2-gallery-meta">
                    <span class="igv2-gallery-prompt">${img.prompt?.substring(0, 40)}...</span>
                    <span class="igv2-gallery-info">${img.provider} | ${img.model}</span>
                </div>
                <button class="igv2-gallery-delete" onclick="event.stopPropagation(); window.imageGenV2?.deleteImage('${img.image_id}')" title="Delete">≡ƒùæ∩╕Å</button>
            </div>
        `).join('');
    }

    _renderStats() {
        const container = document.getElementById('igv2Stats');
        if (!container || !this.stats) return;

        const gen = this.stats.generation || {};
        const storage = this.stats.storage || {};

        container.innerHTML = `
            <div class="igv2-stats-grid">
                <div class="igv2-stat-card">
                    <span class="igv2-stat-label">Total Generated</span>
                    <span class="igv2-stat-value">${gen.total_generations || 0}</span>
                </div>
                <div class="igv2-stat-card">
                    <span class="igv2-stat-label">Total Spent</span>
                    <span class="igv2-stat-value">$${gen.total_cost_usd || 0}</span>
                </div>
                <div class="igv2-stat-card">
                    <span class="igv2-stat-label">Stored Images</span>
                    <span class="igv2-stat-value">${storage.total_files || 0}</span>
                </div>
                <div class="igv2-stat-card">
                    <span class="igv2-stat-label">Storage Used</span>
                    <span class="igv2-stat-value">${storage.total_mb || 0} MB</span>
                </div>
            </div>
        `;
    }

    _addImageToChat(data, prompt) {
        // Get the chat container from the main app
        const chatContainer = document.getElementById('chatContainer');
        if (!chatContainer) return;

        let imgSrc = '';
        if (data.images?.length > 0 && data.images[0].url) {
            imgSrc = data.images[0].url;
        } else if (data.images_url?.length > 0) {
            imgSrc = data.images_url[0];
        }

        if (!imgSrc) return;

        const msgDiv = document.createElement('div');
        msgDiv.className = 'message assistant-message';
        msgDiv.innerHTML = `
            <div class="message-content">
                <div class="igv2-chat-image">
                    <img src="${imgSrc}" alt="Generated" style="max-width: 100%; border-radius: 12px; cursor: pointer;" 
                         onclick="window.open('${imgSrc}', '_blank')">
                    <div class="igv2-chat-meta">
                        ≡ƒÄ¿ <strong>${data.provider}</strong> / ${data.model} | ${Math.round(data.latency_ms)}ms | $${data.cost_usd}
                        ${data.prompt_used ? `<br>≡ƒô¥ ${data.prompt_used.substring(0, 120)}...` : ''}
                    </div>
                </div>
            </div>
        `;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    _showStatus(msg, type = 'info') {
        const el = document.getElementById('igv2Status');
        if (!el) return;
        el.textContent = msg;
        el.className = `igv2-status igv2-status-${type}`;
    }

    // ΓöÇΓöÇ Utility ΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇΓöÇ

    downloadImage(url) {
        const a = document.createElement('a');
        a.href = url;
        a.download = `generated_${Date.now()}.png`;
        a.click();
    }

    copyToChat(url) {
        // Create a message in chat with the image
        const chatContainer = document.getElementById('chatContainer');
        if (!chatContainer) return;
        const msgDiv = document.createElement('div');
        msgDiv.className = 'message user-message';
        msgDiv.innerHTML = `<div class="message-content"><img src="${url}" style="max-width: 100%; border-radius: 8px;"></div>`;
        chatContainer.appendChild(msgDiv);
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }

    _providerIcon(name) {
        const icons = {
            fal: 'ΓÜí', replicate: '≡ƒöä', bfl: '≡ƒîè', openai: '≡ƒñû',
            comfyui: '≡ƒûÑ∩╕Å', together: '≡ƒñ¥', stepfun: '≡ƒÜÇ',
        };
        return icons[name] || '≡ƒÄ»';
    }

    _styleIcon(name) {
        const icons = {
            photorealistic: '≡ƒô╖', anime: '≡ƒÄî', cinematic: '≡ƒÄ¼',
            watercolor: '≡ƒÄ¿', digital_art: '≡ƒÆ╗', oil_painting: '≡ƒû╝∩╕Å',
            pixel_art: '≡ƒæ╛', '3d_render': '≡ƒºè', sketch: 'Γ£Å∩╕Å',
            pop_art: '≡ƒÄ¬', minimalist: 'Γ¼£', fantasy: '≡ƒºÖ',
            noir: '≡ƒîæ', vaporwave: '≡ƒî┤', studio_photo: '≡ƒô╕',
        };
        return icons[name] || '≡ƒÄ¿';
    }
}
