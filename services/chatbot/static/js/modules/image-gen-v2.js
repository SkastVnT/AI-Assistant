/**
 * Image Generation V2 — Multi-Provider System
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

    // ── Initialization ─────────────────────────────────────────────

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

    // ── Modal Control ──────────────────────────────────────────────

    openModal() {
        const modal = document.getElementById('imageGenV2Modal');
        if (modal) {
            modal.classList.add('active', 'open');
            modal.style.display = 'flex';
            this.init();
        }
    }

    closeModal() {
        const modal = document.getElementById('imageGenV2Modal');
        if (modal) {
            modal.classList.remove('active');
            modal.style.display = 'none';
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

    // ── Generate ───────────────────────────────────────────────────

    async generate() {
        if (this.isGenerating) return;

        const prompt = document.getElementById('igv2Prompt')?.value?.trim();
        if (!prompt) {
            this._showStatus('Nhập mô tả ảnh!', 'error');
            return;
        }

        this.isGenerating = true;
        const btn = document.getElementById('igv2GenerateBtn');
        const statusEl = document.getElementById('igv2Status');
        const resultArea = document.getElementById('igv2Result');

        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="animate-spin">⏳</span> Đang tạo ảnh...';
        }
        if (statusEl) statusEl.textContent = '🤖 Đang enhance prompt với AI...';

        try {
            const quality = document.getElementById('igv2Quality')?.value || 'auto';
            const style = document.getElementById('igv2Style')?.value || '';
            const provider = document.getElementById('igv2Provider')?.value || '';
            const width = parseInt(document.getElementById('igv2Width')?.value || '1024');
            const height = parseInt(document.getElementById('igv2Height')?.value || '1024');
            const enhance = document.getElementById('igv2Enhance')?.checked !== false;
            const steps = parseInt(document.getElementById('igv2Steps')?.value || '28');
            const guidance = parseFloat(document.getElementById('igv2Guidance')?.value || '3.5');

            if (statusEl) statusEl.textContent = '🎨 Đang tạo ảnh...';

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
                    `✅ Tạo thành công! Provider: ${data.provider} | Model: ${data.model} | ${data.latency_ms}ms | $${data.cost_usd}`,
                    'success'
                );

                // Also inject into chat
                this._addImageToChat(data, prompt);

                // Refresh gallery
                this.loadGallery();
            } else {
                this._showStatus(`❌ Lỗi: ${data.error}`, 'error');
                if (resultArea) {
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'igv2-error';
                    const errorP = document.createElement('p');
                    errorP.textContent = '❌ ' + (data.error || 'Unknown error');
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
            this._showStatus(`❌ Lỗi: ${e.message}`, 'error');
        } finally {
            this.isGenerating = false;
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '🎨 Tạo ảnh';
            }
        }
    }

    // ── Edit (iterative) ───────────────────────────────────────────

    async editImage() {
        if (this.isGenerating) return;

        const prompt = document.getElementById('igv2EditPrompt')?.value?.trim();
        if (!prompt) {
            this._showStatus('Nhập lệnh chỉnh sửa!', 'error');
            return;
        }

        this.isGenerating = true;
        const btn = document.getElementById('igv2EditBtn');
        if (btn) {
            btn.disabled = true;
            btn.innerHTML = '<span class="animate-spin">⏳</span> Đang chỉnh sửa...';
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
                this._showStatus(`✅ Chỉnh sửa thành công! ${data.provider} | ${data.latency_ms}ms`, 'success');
                this._addImageToChat(data, `✏️ Edit: ${prompt}`);
                this.loadGallery();
            } else {
                this._showStatus(`❌ ${data.error}`, 'error');
            }
        } catch (e) {
            this._showStatus(`❌ ${e.message}`, 'error');
        } finally {
            this.isGenerating = false;
            if (btn) {
                btn.disabled = false;
                btn.innerHTML = '✏️ Chỉnh sửa';
            }
        }
    }

    // ── Gallery ────────────────────────────────────────────────────

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

    // ── Chat Integration ───────────────────────────────────────────

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
     * Detect if a message is an image generation request.
     * Enhanced detection with better accuracy — avoids false positives.
     */
    static isImageRequest(message) {
        const lower = message.toLowerCase().trim();
        
        // Command triggers (highest confidence — always match)
        const commandTriggers = ['/img ', '/image ', '/draw ', '/gen ', '/paint '];
        if (commandTriggers.some(t => lower.startsWith(t))) return true;
        
        // Vietnamese triggers (start-of-sentence)
        const viStartTriggers = [
            'vẽ ', 'vẽ cho', 'vẽ giúp', 'hãy vẽ', 'tạo ảnh', 'tạo hình',
            'sinh ảnh', 'tạo một bức', 'vẽ một', 'tạo một ảnh',
            'tạo hình ảnh', 'hãy tạo', 'giúp tôi vẽ', 'giúp mình vẽ',
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
        const imageWords = ['ảnh', 'hình', 'image', 'picture', 'photo', 'illustration', 'artwork'];
        const actionWords = ['tạo', 'vẽ', 'create', 'generate', 'make', 'draw'];
        
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
            'ảnh trước', 'ảnh vừa', 'cái ảnh', 'bức ảnh',
            'previous image', 'last image', 'that image', 'the image',
        ];
        const hasImageRef = imageRef.some(t => lower.includes(t));
        
        if (!hasImageRef) return false;
        
        // And must have an edit action
        const editActions = [
            'thêm', 'bỏ', 'xóa', 'đổi', 'thay đổi', 'sửa', 'chỉnh',
            'add', 'remove', 'change', 'edit', 'modify', 'replace',
        ];
        return editActions.some(t => lower.includes(t));
    }

    // ── Private: Rendering ─────────────────────────────────────────

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
                    <button onclick="window.imageGenV2?.downloadImage('${imgSrc}')" class="igv2-action-btn">💾 Download</button>
                    <button onclick="window.imageGenV2?.copyToChat('${imgSrc}')" class="igv2-action-btn">📋 Copy to Chat</button>
                    <button onclick="document.getElementById('igv2EditPrompt')?.focus(); window.imageGenV2?.switchTab('edit')" class="igv2-action-btn">✏️ Edit</button>
                </div>
            </div>
        `;
    }

    _renderProviderSelect() {
        const select = document.getElementById('igv2Provider');
        const editSelect = document.getElementById('igv2EditProvider');
        if (!select) return;

        const options = '<option value="">🤖 Auto (Best available)</option>' +
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
                <button class="igv2-gallery-delete" onclick="event.stopPropagation(); window.imageGenV2?.deleteImage('${img.image_id}')" title="Delete">🗑️</button>
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
                        🎨 <strong>${data.provider}</strong> / ${data.model} | ${Math.round(data.latency_ms)}ms | $${data.cost_usd}
                        ${data.prompt_used ? `<br>📝 ${data.prompt_used.substring(0, 120)}...` : ''}
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

    // ── Utility ────────────────────────────────────────────────────

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
            fal: '⚡', replicate: '🔄', bfl: '🌊', openai: '🤖',
            comfyui: '🖥️', together: '🤝', stepfun: '🚀',
        };
        return icons[name] || '🎯';
    }

    _styleIcon(name) {
        const icons = {
            photorealistic: '📷', anime: '🎌', cinematic: '🎬',
            watercolor: '🎨', digital_art: '💻', oil_painting: '🖼️',
            pixel_art: '👾', '3d_render': '🧊', sketch: '✏️',
            pop_art: '🎪', minimalist: '⬜', fantasy: '🧙',
            noir: '🌑', vaporwave: '🌴', studio_photo: '📸',
        };
        return icons[name] || '🎨';
    }
}
