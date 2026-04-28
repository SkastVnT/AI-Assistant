/**
 * Image Generation Module
 * Handles Stable Diffusion image generation (Text2Img and Img2Img)
 */

export class ImageGeneration {
    constructor(apiService) {
        this.apiService = apiService;
        this.currentGeneratedImage = null;
        this.sdModels = [];
        this.samplers = [];
        this.loras = [];
        this.vaes = [];
        
        // Img2Img specific
        this.sourceImageFile = null;
        this.sourceImageBase64 = null;
        this.extractedTags = [];
        this.extractedCategories = {};
        this.filteredTags = new Set();
        this.filteredCategories = new Set();
    }

    /**
     * Open image generation modal
     */
    async openModal() {
        console.log('[Image Modal] Opening modal...');
        const modal = document.getElementById('imageGenModal');
        if (modal) {
            modal.classList.add('active', 'open');
            modal.style.display = 'flex';
            
            // Check SD status and load resources
            await this.checkSDStatus();
            await this.loadSDModels();
            await this.loadSamplers();
            await this.loadLoras();
            await this.loadVaes();
            
            // Initialize tabs
            this.switchTab('text2img');
        }
    }

    /**
     * Close image generation modal with animation
     */
    closeModal() {
        const modal = document.getElementById('imageGenModal');
        if (modal) {
            modal.classList.remove('active', 'open');
            modal.style.display = 'none';
        }
    }

    /**
     * Switch between tabs
     */
    switchTab(tabName) {
        const allTabs = ['text2img', 'img2img', 'inpaint', 'controlnet', 'upscale', 'batch'];
        
        // Hide all tab contents
        allTabs.forEach(t => {
            const el = document.getElementById(t + 'Tab');
            if (el) { el.style.display = 'none'; el.classList.remove('active'); }
        });
        
        // Remove active from all tab buttons
        document.querySelectorAll('#imageGenModal .tab-btn').forEach(btn => {
            btn.classList.remove('btn--primary');
            btn.classList.add('btn--ghost');
        });
        
        // Show selected tab
        const selectedTab = document.getElementById(tabName + 'Tab');
        if (selectedTab) {
            selectedTab.style.display = 'block';
            selectedTab.classList.add('active');
        }
        
        // Highlight correct button
        const tabBtns = document.querySelectorAll('#imageGenModal .tab-btn');
        const idx = allTabs.indexOf(tabName);
        if (idx >= 0 && tabBtns[idx]) {
            tabBtns[idx].classList.remove('btn--ghost');
            tabBtns[idx].classList.add('btn--primary');
        }
        
        console.log(`[Tab Switch] Switched to ${tabName}`);
    }

    /**
     * Check Stable Diffusion API status
     */
    async checkSDStatus() {
        try {
            const data = await this.apiService.checkSDStatus();
            const statusEl = document.getElementById('sdStatus');
            
            if (statusEl) {
                if (data.status === 'online') {
                    statusEl.textContent = '✅ Stable Diffusion API: Online';
                    statusEl.style.color = '#4CAF50';
                } else {
                    statusEl.textContent = '❌ Stable Diffusion API: Offline';
                    statusEl.style.color = '#f44336';
                }
            }
            
            return data.status === 'online';
        } catch (error) {
            console.error('SD status check failed:', error);
            return false;
        }
    }

    /**
     * Load SD models
     */
    async loadSDModels() {
        try {
            this.sdModels = await this.apiService.loadSDModels();
            this.populateModelSelect();
        } catch (error) {
            console.error('Failed to load models:', error);
        }
    }

    /**
     * Load samplers
     */
    async loadSamplers() {
        try {
            this.samplers = await this.apiService.loadSamplers();
            this.populateSamplerSelect();
        } catch (error) {
            console.error('Failed to load samplers:', error);
        }
    }

    /**
     * Load LoRAs
     */
    async loadLoras() {
        try {
            this.loras = await this.apiService.loadLoras();
            this.populateLoraList();
        } catch (error) {
            console.error('Failed to load LoRAs:', error);
            try {
                await new Promise(r => setTimeout(r, 2000));
                this.loras = await this.apiService.loadLoras();
                this.populateLoraList();
            } catch (retryErr) {
                console.error('LoRA retry also failed:', retryErr);
            }
        }
    }

    /**
     * Load VAEs
     */
    async loadVaes() {
        try {
            this.vaes = await this.apiService.loadVaes();
            this.populateVaeSelect();
        } catch (error) {
            console.error('Failed to load VAEs:', error);
            // Retry once after a short delay (tunnel may be slow)
            try {
                await new Promise(r => setTimeout(r, 2000));
                this.vaes = await this.apiService.loadVaes();
                this.populateVaeSelect();
            } catch (retryErr) {
                console.error('VAE retry also failed:', retryErr);
            }
        }
    }

    /**
     * Populate model select dropdown
     */
    populateModelSelect() {
        const selects = document.querySelectorAll('#modelCheckpoint, #img2imgModelSelect');
        selects.forEach(select => {
            if (!select) return;
            if (this.sdModels.length > 0) {
                select.innerHTML = this.sdModels.map(model =>
                    `<option value="${model}">${model}</option>`
                ).join('');
            } else {
                select.innerHTML = '<option value="">⚠️ No models found — place .safetensors in ComfyUI/models/checkpoints/</option>';
            }
        });
    }

    /**
     * Populate sampler select dropdown
     */
    populateSamplerSelect() {
        const selects = document.querySelectorAll('#samplerSelect, #img2imgSampler');
        selects.forEach(select => {
            if (select && this.samplers.length > 0) {
                select.innerHTML = this.samplers.map(sampler => 
                    `<option value="${sampler}">${sampler}</option>`
                ).join('');
            }
        });
    }

    /**
     * Normalize a lora or vae item to its name string
     */
    _itemName(item) {
        if (typeof item === 'object' && item !== null) return item.name || item.alias || String(item);
        return String(item);
    }

    /**
     * Populate LoRA checkbox lists in both Text2Img and Img2Img tabs
     */
    populateLoraList() {
        const containers = document.querySelectorAll('#loraSelectionContainer, #img2imgLoraSelectionContainer');
        containers.forEach(container => {
            if (!container) return;
            if (this.loras.length > 0) {
                container.innerHTML = this.loras.map(lora => {
                    const name = this._itemName(lora);
                    const safeId = name.replace(/[^a-zA-Z0-9_-]/g, '_');
                    const uniqueId = `lora-${container.id}-${safeId}`;
                    return `
                    <label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; padding: 2px 0;">
                        <input type="checkbox" value="${this._escapeAttr(name)}" style="accent-color: var(--accent);">
                        <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this._escapeAttr(name)}">${this._escapeHtml(name)}</span>
                    </label>`;
                }).join('');
                this.autoSelectRecommendedLoras(container);
            } else {
                container.innerHTML = '<p style="font-size: 12px; color: var(--text-tertiary); margin: 0;">No LoRAs found</p>';
            }
        });
    }
    
    /**
     * Auto-select recommended LoRA models
     */
    autoSelectRecommendedLoras(container) {
        // Tier 1 — Anime style & character detail (always prefer these)
        const tier1Patterns = [
            /anime/i,
            /illustri/i,
            /illustration/i,
            /manga/i,
            /2d.*style/i,
            /style.*2d/i,
            /add[_\-\s]*detail/i,
            /detail[_\-\s]*(?:enhancer|booster|plus)/i,
            /more[_\-\s]*detail/i,
            /character[_\-\s]*detail/i,
            /face[_\-\s]*detail/i,
            /skin[_\-\s]*detail/i,
            /eye[_\-\s]*detail/i,
            /expressive/i,
            /pony.*xl/i,
            /xl.*pony/i,
        ];

        // Tier 2 — General quality / enhancement (fallback)
        const tier2Patterns = [
            /detail/i,
            /quality/i,
            /enhance/i,
            /improve/i,
        ];

        let selectedCount = 0;
        const maxAutoSelect = 3;

        const checkboxes = Array.from(container.querySelectorAll('input[type="checkbox"]'));

        // Pass 1: tier 1 — anime / character detail
        for (const checkbox of checkboxes) {
            if (selectedCount >= maxAutoSelect) break;
            if (tier1Patterns.some(p => p.test(checkbox.value))) {
                checkbox.checked = true;
                selectedCount++;
                console.log(`[Auto-Select LoRA T1] ${checkbox.value}`);
            }
        }

        // Pass 2: tier 2 — general quality (only if still under limit)
        for (const checkbox of checkboxes) {
            if (selectedCount >= maxAutoSelect) break;
            if (!checkbox.checked && tier2Patterns.some(p => p.test(checkbox.value))) {
                checkbox.checked = true;
                selectedCount++;
                console.log(`[Auto-Select LoRA T2] ${checkbox.value}`);
            }
        }

        // Fallback: select the first LoRA if nothing matched
        if (selectedCount === 0 && checkboxes.length > 0) {
            checkboxes[0].checked = true;
            console.log(`[Auto-Select LoRA fallback] ${checkboxes[0].value}`);
        }
    }

    /**
     * Populate VAE radio button lists
     */
    populateVaeSelect() {
        const mappings = [
            { containerId: 'vaeSelectionContainer', radioName: 'vaeChoice' },
            { containerId: 'img2imgVaeSelectionContainer', radioName: 'img2imgVaeChoice' },
        ];
        mappings.forEach(({ containerId, radioName }) => {
            const container = document.getElementById(containerId);
            if (!container) return;
            if (this.vaes.length > 0) {
                let html = `<label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; padding: 2px 0;">
                        <input type="radio" name="${radioName}" value="" checked style="accent-color: var(--accent);"> Automatic
                    </label>`;
                html += this.vaes.map(vae => {
                    const name = this._itemName(vae);
                    return `<label style="display: flex; align-items: center; gap: 6px; font-size: 13px; cursor: pointer; padding: 2px 0;">
                        <input type="radio" name="${radioName}" value="${this._escapeAttr(name)}" style="accent-color: var(--accent);">
                        <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${this._escapeAttr(name)}">${this._escapeHtml(name)}</span>
                    </label>`;
                }).join('');
                container.innerHTML = html;
                // Auto-select recommended VAE
                this.autoSelectRecommendedVae(container, radioName);
            }
        });
    }
    
    /**
     * Auto-select recommended VAE (radio button version)
     */
    autoSelectRecommendedVae(container, radioName) {
        const recommendedPatterns = [
            /anime.*vae/i,
            /anything.*vae/i,
            /vae.*ft.*mse/i,
            /blessed2/i,
            /orangemix/i
        ];
        
        const radios = container.querySelectorAll(`input[name="${radioName}"]`);
        for (const radio of radios) {
            if (radio.value && recommendedPatterns.some(p => p.test(radio.value))) {
                radio.checked = true;
                console.log(`[Auto-Select] Selected VAE: ${radio.value}`);
                return;
            }
        }
        // If no recommended VAE found, select first non-default
        if (this.vaes.length > 0 && radios.length > 1) {
            radios[1].checked = true;
            console.log(`[Auto-Select] Selected first VAE: ${radios[1].value}`);
        }
    }

    /**
     * Auto-pick best Model, LoRA, VAE for Img2Img based on extracted tags/prompt
     */
    autoPickBestOptions() {
        // ── Best Model ──
        const modelSelect = document.getElementById('img2imgModelSelect');
        if (modelSelect && modelSelect.options.length > 1) {
            // Preference order for anime/illustration
            const modelPriority = [
                /abyssorangemix3/i,
                /anythingv5/i,
                /anything/i,
                /orangemix/i,
                /aom3/i,
                /illustri/i,
                /soushiki/i,
            ];
            let picked = false;
            for (const pattern of modelPriority) {
                for (let i = 0; i < modelSelect.options.length; i++) {
                    if (pattern.test(modelSelect.options[i].value)) {
                        modelSelect.selectedIndex = i;
                        console.log(`[Auto-Pick] Model: ${modelSelect.options[i].value}`);
                        picked = true;
                        break;
                    }
                }
                if (picked) break;
            }
        }

        // ── Best VAE ──
        const img2imgVaeContainer = document.getElementById('img2imgVaeSelectionContainer');
        if (img2imgVaeContainer) {
            const vaePriority = [
                /kl-f8-anime/i,
                /orangemix\.vae/i,
                /anime.*vae/i,
                /vae.*ft.*mse/i,
            ];
            const radios = img2imgVaeContainer.querySelectorAll('input[name="img2imgVaeChoice"]');
            let picked = false;
            for (const pattern of vaePriority) {
                for (const radio of radios) {
                    if (radio.value && pattern.test(radio.value)) {
                        radio.checked = true;
                        console.log(`[Auto-Pick] VAE: ${radio.value}`);
                        picked = true;
                        break;
                    }
                }
                if (picked) break;
            }
        }

        // ── Best LoRA ──
        const loraContainer = document.getElementById('img2imgLoraSelectionContainer');
        if (loraContainer && this.loras.length > 0) {
            // Quality/detail LoRAs to auto-add
            const loraTargets = [
                /^add_detail/i,
                /^more_details/i,
                /^add-detail/i,
            ];
            // Remove existing lora rows (except the Add button)
            loraContainer.querySelectorAll('.lora-row').forEach(r => r.remove());

            const matched = [];
            for (const pattern of loraTargets) {
                const found = this.loras.find(l => pattern.test(this._itemName(l)));
                if (found) matched.push(this._itemName(found));
                if (matched.length >= 2) break;
            }
            // If no quality LoRA found, skip — don't force
            for (const loraName of matched) {
                // Trigger addImg2imgLoraSelection and set value
                if (window.addImg2imgLoraSelection) {
                    window.addImg2imgLoraSelection();
                    // Get the last added row's select
                    const rows = loraContainer.querySelectorAll('.lora-row');
                    const lastRow = rows[rows.length - 1];
                    if (lastRow) {
                        const sel = lastRow.querySelector('.lora-select');
                        if (sel) {
                            sel.value = loraName;
                            console.log(`[Auto-Pick] LoRA: ${loraName}`);
                        }
                        const weightInput = lastRow.querySelector('.lora-weight');
                        if (weightInput) weightInput.value = '0.7';
                    }
                }
            }
        }

        // ── Optimal params ──
        const stepsInput = document.getElementById('img2imgSteps');
        if (stepsInput) stepsInput.value = '28';
        const cfgInput = document.getElementById('img2imgCfgScale');
        if (cfgInput) cfgInput.value = '7';
        const denoisingInput = document.getElementById('denoisingStrength');
        if (denoisingInput) denoisingInput.value = '0.6';
        const samplerSelect = document.getElementById('img2imgSampler');
        if (samplerSelect) {
            // Prefer euler_ancestral or dpmpp_2m
            const samplerPriority = [/euler_ancestral/i, /dpmpp_2m/i, /euler/i];
            for (const pattern of samplerPriority) {
                for (let i = 0; i < samplerSelect.options.length; i++) {
                    if (pattern.test(samplerSelect.options[i].value)) {
                        samplerSelect.selectedIndex = i;
                        console.log(`[Auto-Pick] Sampler: ${samplerSelect.options[i].value}`);
                        break;
                    }
                }
                if (samplerSelect.value.match(samplerPriority[0])) break;
            }
        }

        console.log('[Auto-Pick] Best options applied');
    }

    /**
     * Get selected LoRAs from checkbox list
     */
    getSelectedLoras(containerId = 'loraSelectionContainer') {
        const container = document.getElementById(containerId);
        if (!container) return [];

        const selectedLoras = [];
        container.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
            selectedLoras.push({ name: checkbox.value, weight: 1.0 });
        });

        return selectedLoras;
    }

    /**
     * Get selected VAE from radio buttons
     */
    getSelectedVae(radioName = 'vaeChoice') {
        const checked = document.querySelector(`input[name="${radioName}"]:checked`);
        return checked ? checked.value : '';
    }

    /**
     * Generate image (Text2Img)
     */
    async generateText2Img(params) {
        try {
            // If params not provided, collect from UI
            if (!params) {
                params = {
                    prompt: document.getElementById('imagePrompt')?.value || '',
                    negative_prompt: document.getElementById('negativePrompt')?.value || '',
                    steps: parseInt(document.getElementById('steps')?.value) || 20,
                    cfg_scale: parseFloat(document.getElementById('cfgScale')?.value) || 7.0,
                    width: parseInt(document.getElementById('width')?.value) || 512,
                    height: parseInt(document.getElementById('height')?.value) || 512,
                    sampler_name: document.getElementById('sampler')?.value || 'DPM++ 2M Karras',
                    seed: -1,
                    batch_size: 1,
                    lora_models: this.getSelectedLoras('loraSelectionContainer'),
                    vae: this.getSelectedVae('vaeChoice')
                };
            }
            
            const data = await this.apiService.generateImage(params);
            if (data.image || data.base64_images) {
                this.currentGeneratedImage = data;
                // Use base64_images if available (when save_to_storage=true), otherwise use image
                const imageToDisplay = (data.base64_images && data.base64_images[0]) || data.image;
                this.displayGeneratedImage(imageToDisplay);
                // Save prompt to history
                this.savePromptToHistory(params.prompt, params.negative_prompt);
                return data;
            } else {
                throw new Error(data.error || 'Failed to generate image');
            }
        } catch (error) {
            console.error('Text2Img error:', error);
            throw error;
        }
    }

    /**
     * Generate image (Img2Img)
     */
    async generateImg2Img(params) {
        try {
            // If params not provided, collect from UI
            if (!params) {
                if (!this.sourceImageBase64) {
                    throw new Error('Please upload a source image first');
                }
                
                params = {
                    image: this.sourceImageBase64.split(',')[1], // Remove data:image/... prefix
                    prompt: document.getElementById('img2imgPrompt')?.value || '',
                    negative_prompt: document.getElementById('img2imgNegativePrompt')?.value || '',
                    model: document.getElementById('img2imgModelSelect')?.value || document.getElementById('modelCheckpoint')?.value || '',
                    steps: parseInt(document.getElementById('img2imgSteps')?.value) || 30,
                    cfg_scale: parseFloat(document.getElementById('img2imgCfgScale')?.value) || 7.0,
                    width: parseInt(document.getElementById('img2imgWidth')?.value) || 512,
                    height: parseInt(document.getElementById('img2imgHeight')?.value) || 512,
                    denoising_strength: parseFloat(document.getElementById('denoisingStrength')?.value) || 0.75,
                    sampler_name: document.getElementById('img2imgSampler')?.value || 'euler',
                    seed: parseInt(document.getElementById('img2imgSeed')?.value) || -1,
                    lora_models: this.getSelectedLoras('img2imgLoraSelectionContainer'),
                    vae: this.getSelectedVae('img2imgVaeChoice')
                };
            }
            
            const data = await this.apiService.generateImg2Img(params);
            if (data.image || data.base64_images) {
                this.currentGeneratedImage = data;
                // Use base64_images if available (when save_to_storage=true), otherwise use image
                const imageToDisplay = (data.base64_images && data.base64_images[0]) || data.image;
                this.displayGeneratedImage(imageToDisplay);
                // Save prompt to history
                this.savePromptToHistory(params.prompt, params.negative_prompt);
                return data;
            } else {
                throw new Error(data.error || 'Failed to generate image');
            }
        } catch (error) {
            console.error('Img2Img error:', error);
            throw error;
        }
    }

    /**
     * Display generated image - Send directly to chat
     */
    displayGeneratedImage(base64Image) {
        console.log('[Display Image] Received base64 image, length:', base64Image?.length || 0);
        
        // Lưu ảnh vào storage và metadata (không có prefix)
        this.currentGeneratedImage = { image: base64Image };
        
        // Auto-save image to storage
        this.autoSaveImage(base64Image);
        
        // Gửi ảnh thẳng vào chat (không dùng overlay)
        console.log('[Display Image] Scheduling sendImageToChat in 300ms...');
        setTimeout(() => {
            console.log('[Display Image] Calling sendImageToChat now!');
            this.sendImageToChat();
        }, 300);
    }
    
    /**
     * Auto-save generated image to storage and chat history
     */
    async autoSaveImage(base64Image) {
        try {
            // Skip if not valid base64 data (e.g., if it's a filename or URL)
            if (!base64Image || 
                base64Image.startsWith('http') || 
                base64Image.startsWith('/') ||
                base64Image.length < 100) {
                console.log('[Auto-Save] Skipping - image already saved by server or not base64');
                return;
            }
            
            // Collect metadata
            const metadata = {
                prompt: document.getElementById('img2imgPrompt')?.value || document.getElementById('imagePrompt')?.value || 'N/A',
                negative_prompt: document.getElementById('img2imgNegativePrompt')?.value || document.getElementById('negativePrompt')?.value || 'N/A',
                model: document.getElementById('modelCheckpoint')?.value || 'N/A',
                sampler: document.getElementById('img2imgSampler')?.value || document.getElementById('samplerSelect')?.value || 'N/A',
                steps: document.getElementById('img2imgSteps')?.value || document.getElementById('imageSteps')?.value || 'N/A',
                cfg_scale: document.getElementById('img2imgCfgScale')?.value || document.getElementById('cfgScale')?.value || 'N/A',
                width: document.getElementById('img2imgWidth')?.value || document.getElementById('imageWidth')?.value || 'N/A',
                height: document.getElementById('img2imgHeight')?.value || document.getElementById('imageHeight')?.value || 'N/A',
                denoising_strength: document.getElementById('denoisingStrength')?.value || 'N/A',
                lora_models: this.getSelectedLoras('loraSelectionContainer').concat(this.getSelectedLoras('img2imgLoraSelectionContainer')).map(l => l.name).join(', ') || 'None',
                vae: this.getSelectedVae('img2imgVaeChoice') || this.getSelectedVae('vaeChoice') || 'Auto',
                seed: document.getElementById('img2imgSeed')?.value || document.getElementById('imageSeed')?.value || '-1'
            };
            
            console.log('[Auto-Save] Saving image with metadata:', metadata);
            
            const response = await fetch('/api/save-generated-image', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image: base64Image,
                    metadata: metadata
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success) {
                console.log('[Auto-Save] ✅ Saved:', data.filename);
                if (data.cloud_url) {
                    console.log('[Auto-Save] ☁️ ImgBB:', data.cloud_url);
                    
                    // Log to Firebase (async)
                    if (window.logImageToFirebase && this.currentGeneratedImage) {
                        window.logImageToFirebase(
                            this.currentGeneratedImage.prompt || '',
                            this.currentGeneratedImage.negativePrompt || '',
                            this.currentGeneratedImage.image || '',
                            data.cloud_url
                        );
                    }
                }
            }
            
        } catch (error) {
            console.error('[Auto-Save] Error:', error);
            // Don't show alert, just log error
        }
    }
    
    /**
     * Share image to ImgBB
     */
    async shareImageToImgBB() {
        if (!this.currentGeneratedImage) {
            alert('❌ Không có ảnh để share!');
            return;
        }
        
        try {
            const prompt = document.getElementById('img2imgPrompt')?.value || document.getElementById('imagePrompt')?.value || 'AI Generated';
            const title = prompt.substring(0, 50).replace(/[^a-zA-Z0-9 ]/g, '_');
            
            console.log('[ImgBB Share] Uploading...');
            
            const response = await fetch('/api/share-image-imgbb', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    image: this.currentGeneratedImage.image,
                    title: title
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.url) {
                console.log('[ImgBB Share] ✅ Success:', data.url);
                
                // Copy to clipboard
                try {
                    await navigator.clipboard.writeText(data.url);
                    alert(`✅ Link đã được copy vào clipboard!\n\n🔗 ${data.url}`);
                } catch (clipError) {
                    // Fallback: Show prompt to copy
                    prompt(`✅ ImgBB Link (Ctrl+C to copy):\n\n`, data.url);
                }
            } else {
                throw new Error(data.error || 'Share failed');
            }
            
        } catch (error) {
            console.error('[ImgBB Share] Error:', error);
            alert('❌ Lỗi khi share lên ImgBB: ' + error.message);
        }
    }

    /**
     * Handle source image upload for Img2Img
     */
    handleSourceImageUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.type.startsWith('image/')) {
            alert('⚠️ Vui lòng chọn file hình ảnh!');
            return;
        }
        
        this.sourceImageFile = file;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            this.sourceImageBase64 = e.target.result;
            
            // Preview image
            const preview = document.getElementById('sourceImagePreview');
            const placeholder = document.getElementById('uploadPlaceholder');
            
            if (preview && placeholder) {
                preview.src = this.sourceImageBase64;
                preview.style.display = 'block';
                placeholder.style.display = 'none';
            }
            
            // Show feature extraction section
            const extractSection = document.getElementById('featureExtractionSection');
            if (extractSection) {
                extractSection.style.display = 'block';
            }
            
            // Reset extracted tags
            this.extractedTags = [];
            this.filteredTags.clear();
            this.filteredCategories.clear();
            
            const extractedTagsEl = document.getElementById('extractedTags');
            if (extractedTagsEl) {
                extractedTagsEl.style.display = 'none';
            }
            
            // Auto-detect image size
            const img = new Image();
            img.onload = () => {
                console.log(`[Img2Img] Detected image size: ${img.width}x${img.height}`);
                const widthInput = document.getElementById('img2imgWidth');
                const heightInput = document.getElementById('img2imgHeight');
                if (widthInput) widthInput.value = img.width;
                if (heightInput) heightInput.value = img.height;
            };
            img.src = this.sourceImageBase64;
        };
        reader.readAsDataURL(file);
    }

    /**
     * Extract features from image
     */
    async extractFeatures(models = ['deepdanbooru']) {
        if (!this.sourceImageBase64) {
            throw new Error('No source image uploaded');
        }
        
        try {
            const data = await this.apiService.interrogateImage(
                this.sourceImageBase64.split(',')[1],
                models[0]
            );
            
            if (data.tags && data.categories) {
                this.extractedTags = data.tags;
                this.extractedCategories = data.categories;
                
                // Enable auto-generate prompt button
                const autoGenBtn = document.getElementById('autoGeneratePromptBtn');
                if (autoGenBtn) {
                    autoGenBtn.style.display = 'block';
                }
                
                return data;
            } else {
                throw new Error(data.error || 'Failed to extract features');
            }
        } catch (error) {
            console.error('Feature extraction error:', error);
            throw error;
        }
    }
    
    /**
     * Auto-generate prompt from extracted tags using Grok AI
     */
    async generatePromptFromTags() {
        if (!this.extractedTags || this.extractedTags.length === 0) {
            throw new Error('No tags extracted. Please extract features first.');
        }
        
        try {
            // Get selected tags from global state (user-selected tags)
            const selectedTags = window.getSelectedImageTags ? window.getSelectedImageTags() : this.extractedTags.map(t => t.name);
            
            if (selectedTags.length === 0) {
                throw new Error('No tags selected. Please select at least one tag.');
            }
            
            // Filter extracted tags to only include selected ones
            const activeTags = this.extractedTags.filter(tag => selectedTags.includes(tag.name));
            
            // Prepare context for Grok - group by category
            const tagsByCategory = {};
            for (const [category, tags] of Object.entries(this.extractedCategories)) {
                const selectedInCategory = tags.filter(tag => selectedTags.includes(tag.name));
                if (selectedInCategory.length > 0) {
                    tagsByCategory[category] = selectedInCategory
                        .map(tag => `${tag.name} (${(tag.confidence * 100).toFixed(1)}%)`);
                }
            }
            
            const context = `Generate a natural, high-quality Stable Diffusion prompt for anime/illustration image generation based on these extracted features:

${Object.entries(tagsByCategory).map(([cat, tags]) => `${cat}: ${tags.join(', ')}`).join('\n')}

Requirements:
1. Create a flowing, natural prompt that combines these features
2. Add quality boosters like "masterpiece", "best quality", "highly detailed"
3. Keep anime/illustration style consistent
4. Focus on visual details and composition
5. Make it concise but descriptive (max 150 words)
6. DO NOT include negative prompts
7. DO NOT explain, just output the prompt text

Prompt:`;
            
            console.log('[Grok Prompt] Using', selectedTags.length, 'selected tags out of', this.extractedTags.length, 'total tags');
            
            // Call API
            const response = await fetch('/api/generate-prompt-grok', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    context: context,
                    tags: selectedTags
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            console.log('[Grok Prompt] Response data:', data);
            
            if (data.success && data.prompt) {
                console.log(`[Grok Prompt] Generated prompt (${selectedTags.length} tags):`, data.prompt);
                console.log(`[Grok Prompt] Generated negative prompt:`, data.negative_prompt);
                return {
                    prompt: data.prompt,
                    negative_prompt: data.negative_prompt || 'nsfw, nude, sexual, explicit, adult content, bad quality, blurry, worst quality'
                };
            } else {
                throw new Error(data.error || 'Failed to generate prompt');
            }
            
        } catch (error) {
            console.error('[Grok Prompt] Error:', error);
            throw error;
        }
    }

    /**
     * Toggle tag filtering
     */
    toggleTag(tagName) {
        if (this.filteredTags.has(tagName)) {
            this.filteredTags.delete(tagName);
        } else {
            this.filteredTags.add(tagName);
        }
    }

    /**
     * Toggle category filtering
     */
    toggleCategory(category) {
        if (this.filteredCategories.has(category)) {
            this.filteredCategories.delete(category);
            // Remove all tags in this category
            if (this.extractedCategories[category]) {
                this.extractedCategories[category].forEach(tag => {
                    this.filteredTags.delete(tag.name);
                });
            }
        } else {
            this.filteredCategories.add(category);
            // Add all tags in this category
            if (this.extractedCategories[category]) {
                this.extractedCategories[category].forEach(tag => {
                    this.filteredTags.add(tag.name);
                });
            }
        }
    }

    /**
     * Get active tags (non-filtered)
     */
    getActiveTags() {
        return this.extractedTags
            .filter(tag => !this.filteredTags.has(tag.name))
            .map(tag => tag.name);
    }

    /**
     * Send generated image to chat with metadata
     */
    sendImageToChat() {
        if (!this.currentGeneratedImage) {
            console.error('[Image Gen] No image to send');
            return;
        }
        
        try {
            const chatContainer = document.getElementById('chatContainer');
            if (!chatContainer) {
                console.error('[Image Gen] Chat container not found');
                return;
            }
            
            // Collect metadata from current generation
            const metadata = {
                prompt: document.getElementById('img2imgPrompt')?.value || document.getElementById('imagePrompt')?.value || 'N/A',
                negative_prompt: document.getElementById('img2imgNegativePrompt')?.value || document.getElementById('negativePrompt')?.value || 'N/A',
                model: document.getElementById('modelCheckpoint')?.value || 'N/A',
                sampler: document.getElementById('img2imgSampler')?.value || document.getElementById('samplerSelect')?.value || 'N/A',
                steps: document.getElementById('img2imgSteps')?.value || document.getElementById('imageSteps')?.value || 'N/A',
                cfg_scale: document.getElementById('img2imgCfgScale')?.value || document.getElementById('cfgScale')?.value || 'N/A',
                size: `${document.getElementById('img2imgWidth')?.value || document.getElementById('imageWidth')?.value}x${document.getElementById('img2imgHeight')?.value || document.getElementById('imageHeight')?.value}`,
                denoising_strength: document.getElementById('denoisingStrength')?.value || 'N/A',
                lora_models: this.getSelectedLoras('loraSelectionContainer').concat(this.getSelectedLoras('img2imgLoraSelectionContainer')).map(l => l.name).join(', ') || 'None',
                vae: this.getSelectedVae('img2imgVaeChoice') || this.getSelectedVae('vaeChoice') || 'Auto',
                seed: document.getElementById('img2imgSeed')?.value || document.getElementById('imageSeed')?.value || '-1'
            };
            
            // Create message HTML with image and metadata
            const timestamp = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
            const messageHtml = `
                <div class="message ai">
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-role">🎨 AI Image Generation</span>
                            <span class="message-timestamp">${this._escapeHtml(timestamp)}</span>
                        </div>
                        <div class="message-body">
                            <img src="data:image/png;base64,${this.currentGeneratedImage.image}" 
                                 style="max-width: 100%; border-radius: 8px; margin-bottom: 10px; cursor: pointer;"
                                 onclick="openImagePreview(this)" />
                            <div style="background: rgba(0,0,0,0.05); padding: 12px; border-radius: 8px; font-size: 13px; margin-top: 10px;">
                                <div style="margin-bottom: 8px;"><strong>📝 Prompt:</strong> ${this._escapeHtml(metadata.prompt)}</div>
                                <div style="margin-bottom: 8px;"><strong>🚫 Negative:</strong> ${this._escapeHtml(metadata.negative_prompt)}</div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px;">
                                    <div><strong>🤖 Model:</strong> ${this._escapeHtml(metadata.model)}</div>
                                    <div><strong>⚙️ Sampler:</strong> ${this._escapeHtml(metadata.sampler)}</div>
                                    <div><strong>🔢 Steps:</strong> ${this._escapeHtml(metadata.steps)}</div>
                                    <div><strong>🎚️ CFG:</strong> ${this._escapeHtml(metadata.cfg_scale)}</div>
                                    <div><strong>📐 Size:</strong> ${this._escapeHtml(metadata.size)}</div>
                                    ${metadata.denoising_strength !== 'N/A' ? `<div><strong>🔧 Denoising:</strong> ${this._escapeHtml(metadata.denoising_strength)}</div>` : ''}
                                    <div><strong>🎨 LoRA:</strong> ${this._escapeHtml(metadata.lora_models)}</div>
                                    <div><strong>🔧 VAE:</strong> ${this._escapeHtml(metadata.vae)}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            // Append to chat
            chatContainer.insertAdjacentHTML('beforeend', messageHtml);
            chatContainer.scrollTop = chatContainer.scrollHeight;
            
            console.log('[Image Gen] Image sent to chat with metadata');
            
            // Silent success - no alert popup
            
        } catch (error) {
            console.error('[Image Gen] Error sending to chat:', error);
            // Silent error - just log, no alert
        }
    }

    /**
     * Download generated image
     */
    downloadImage() {
        if (!this.currentGeneratedImage) return;
        
        const link = document.createElement('a');
        link.href = 'data:image/png;base64,' + this.currentGeneratedImage.image;
        link.download = `generated_${Date.now()}.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
    
    /**
     * Random prompt generators
     */
    randomPrompt() {
        const prompts = [
            "masterpiece, best quality, highly detailed, 1girl, beautiful detailed face, long flowing hair, cherry blossoms, golden hour lighting, soft focus, depth of field, professional photography, 8k uhd",
            "anime style, masterpiece, 1girl, cute face, sparkling eyes, colorful outfit, dynamic pose, vibrant colors, soft lighting, detailed background, high quality illustration",
            "cyberpunk cityscape, neon lights, rain reflections, futuristic architecture, night scene, cinematic lighting, highly detailed, photorealistic, 8k, ultra sharp",
            "fantasy landscape, majestic mountains, magical atmosphere, ethereal glow, epic scenery, volumetric lighting, cinematic composition, masterpiece, best quality",
            "portrait photography, beautiful woman, professional lighting, soft bokeh, shallow depth of field, detailed skin texture, natural makeup, 8k uhd, photorealistic",
            "anime aesthetic, 1girl, school uniform, cherry blossom petals, spring atmosphere, warm colors, detailed eyes, soft smile, high quality digital art",
            "sunset beach scene, golden hour, ocean waves, dramatic sky, professional landscape photography, vivid colors, high dynamic range, 8k resolution",
            "1girl, elegant dress, ballroom setting, ornate architecture, chandelier lighting, romantic atmosphere, detailed fabric texture, cinematic composition, masterpiece"
        ];
        const promptEl = document.getElementById('imagePrompt');
        if (promptEl) {
            promptEl.value = prompts[Math.floor(Math.random() * prompts.length)];
        }
    }
    
    randomNegativePrompt() {
        const negativePrompts = [
            "nsfw, nude, sexual content, low quality, worst quality, bad anatomy, bad hands, bad proportions, blurry, ugly, deformed, mutated, distorted",
            "nsfw, explicit, low resolution, poorly drawn, bad quality, watermark, signature, text, username, jpeg artifacts, bad anatomy",
            "nsfw, lowres, bad quality, worst quality, bad hands, missing fingers, extra fingers, bad anatomy, mutated, poorly drawn face, out of focus",
            "nsfw, nude, adult content, low quality, blurry, distorted, ugly, worst quality, bad proportions, extra limbs, disfigured, grainy"
        ];
        const negPromptEl = document.getElementById('negativePrompt');
        if (negPromptEl) {
            negPromptEl.value = negativePrompts[Math.floor(Math.random() * negativePrompts.length)];
        }
    }
    
    randomImg2ImgPrompt() {
        const prompts = [
            "masterpiece, best quality, highly detailed, enhanced, improved quality, professional, 8k uhd, sharp focus",
            "anime style, vibrant colors, high quality illustration, detailed, soft lighting, beautiful composition",
            "photorealistic, 8k resolution, detailed textures, professional photography, cinematic lighting, ultra sharp",
            "improve details, enhance quality, fix imperfections, upscale, masterpiece, best quality",
            "artistic style, beautiful colors, high quality digital art, detailed rendering, professional illustration"
        ];
        const promptEl = document.getElementById('img2imgPrompt');
        if (promptEl) {
            promptEl.value = prompts[Math.floor(Math.random() * prompts.length)];
        }
    }
    
    randomImg2ImgNegativePrompt() {
        const negativePrompts = [
            "nsfw, nude, low quality, bad quality, blurry, worst quality, bad anatomy, distorted",
            "nsfw, explicit, low resolution, artifacts, jpeg artifacts, distorted, ugly, deformed",
            "nsfw, adult content, watermark, signature, text, bad proportions, poorly drawn, bad quality",
            "nsfw, nude, blurry, grainy, noisy, worst quality, low quality, bad anatomy, out of focus"
        ];
        const negPromptEl = document.getElementById('img2imgNegativePrompt');
        if (negPromptEl) {
            negPromptEl.value = negativePrompts[Math.floor(Math.random() * negativePrompts.length)];
        }
    }
    
    /**
     * Lora management
     */
    _buildLoraRow(id, containerId) {
        const loraOptions = this.loras.length > 0
            ? this.loras.map(lora => {
                const name = this._itemName(lora);
                return `<option value="${name}">${name}</option>`;
              }).join('')
            : '<option value="">No LoRAs found</option>';
        const row = document.createElement('div');
        row.id = `loraSelection_${id}`;
        row.className = 'lora-row';
        row.innerHTML = `
            <select class="form-select lora-select">${loraOptions}</select>
            <input type="number" class="form-input lora-weight" value="1.0" min="0" max="2" step="0.1"
                   title="Weight">
            <button type="button" class="btn btn--sm btn--ghost lora-remove-btn"
                    onclick="removeLoraSelection(${id})">✕</button>`;
        return row;
    }

    addLoraSelection() {
        const container = document.getElementById('loraSelectionContainer');
        if (!container) return;
        const addBtn = document.getElementById('addLoraBtn');
        const row = this._buildLoraRow(Date.now(), 'loraSelectionContainer');
        addBtn ? container.insertBefore(row, addBtn) : container.appendChild(row);
    }

    addImg2imgLoraSelection() {
        const container = document.getElementById('img2imgLoraSelectionContainer');
        if (!container) return;
        const id = Date.now();
        const loraOptions = this.loras.length > 0
            ? this.loras.map(lora => {
                const name = this._itemName(lora);
                return `<option value="${name}">${name}</option>`;
              }).join('')
            : '<option value="">No LoRAs found</option>';
        const row = document.createElement('div');
        row.id = `img2imgLoraSelection_${id}`;
        row.className = 'lora-row';
        row.innerHTML = `
            <select class="form-select lora-select">${loraOptions}</select>
            <input type="number" class="form-input lora-weight" value="1.0" min="0" max="2" step="0.1"
                   title="Weight">
            <button type="button" class="btn btn--sm btn--ghost lora-remove-btn"
                    onclick="removeImg2imgLoraSelection(${id})">✕</button>`;
        container.appendChild(row);
    }
    
    removeLoraSelection(id) {
        // Implementation for removing Lora selection
        console.log('[Image Gen] Remove Lora selection:', id);
        const element = document.getElementById(`loraSelection_${id}`);
        if (element) {
            element.remove();
        }
    }
    
    removeImg2imgLoraSelection(id) {
        // Implementation for removing Img2Img Lora selection
        console.log('[Image Gen] Remove Img2Img Lora selection:', id);
        const element = document.getElementById(`img2imgLoraSelection_${id}`);
        if (element) {
            element.remove();
        }
    }
    
    /**
     * Copy generated image to chat
     */
    copyImageToChat() {
        if (this.currentGeneratedImage) {
            console.log('[Image Gen] Copy to chat:', this.currentGeneratedImage);
            // Implementation to send image to chat
        }
    }
    
    /**
     * Alias for downloadImage
     */
    downloadGeneratedImage() {
        this.downloadImage();
    }
    
    /**
     * Handle source image upload for img2img
     */
    handleSourceImageUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.type.startsWith('image/')) {
            alert('⚠️ Please select an image file!');
            return;
        }
        
        this.sourceImageFile = file;
        
        // Preview image
        const reader = new FileReader();
        reader.onload = (e) => {
            this.sourceImageBase64 = e.target.result;
            const preview = document.getElementById('sourceImagePreview');
            const placeholder = document.getElementById('uploadPlaceholder');
            
            if (preview && placeholder) {
                preview.src = this.sourceImageBase64;
                preview.style.display = 'block';
                placeholder.style.display = 'none';
            }
            
            // Show feature extraction section
            const extractSection = document.getElementById('featureExtractionSection');
            if (extractSection) {
                extractSection.style.display = 'block';
            }
            
            // Reset extracted tags
            this.extractedTags = [];
            this.filteredTags.clear();
            this.filteredCategories.clear();
            
            const extractedTagsEl = document.getElementById('extractedTags');
            if (extractedTagsEl) {
                extractedTagsEl.style.display = 'none';
            }
            
            // Disable generate button until features extracted
            const generateBtn = document.getElementById('generateImg2ImgBtn');
            if (generateBtn) {
                generateBtn.disabled = true;
            }
        };
        reader.readAsDataURL(file);
    }

    // =========================================================================
    // NEGATIVE PROMPT PRESETS
    // =========================================================================

    async loadNegativePresets() {
        try {
            const resp = await fetch('/api/sd-negative-presets');
            const data = await resp.json();
            const select = document.getElementById('negativePresetSelect');
            if (!select || !data.presets) return;
            select.innerHTML = '<option value="">📋 Preset...</option>';
            data.presets.forEach(p => {
                const opt = document.createElement('option');
                opt.value = p.prompt;
                opt.textContent = p.label;
                select.appendChild(opt);
            });
        } catch (e) {
            console.warn('[NegPresets] Load failed:', e);
        }
    }

    applyNegativePreset(prompt) {
        if (!prompt) return;
        const el = document.getElementById('negativePrompt');
        if (el) el.value = prompt;
    }

    // =========================================================================
    // PROMPT HISTORY
    // =========================================================================

    async loadPromptHistory() {
        try {
            const resp = await fetch('/api/prompt-history');
            const data = await resp.json();
            this._promptHistory = data.history || [];
        } catch (e) { this._promptHistory = []; }
    }

    async savePromptToHistory(prompt, negativePrompt) {
        if (!prompt) return;
        try {
            await fetch('/api/prompt-history', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt, negative_prompt: negativePrompt || '' }),
            });
        } catch (e) { /* silent */ }
    }

    showPromptHistory() {
        const dropdown = document.getElementById('promptHistoryDropdown');
        if (!dropdown) return;

        if (dropdown.style.display === 'block') {
            dropdown.style.display = 'none';
            return;
        }

        this.loadPromptHistory().then(() => {
            const history = this._promptHistory || [];
            if (!history.length) {
                dropdown.innerHTML = '<div style="padding:8px;color:var(--text-tertiary);font-size:12px;">No history yet</div>';
            } else {
                dropdown.innerHTML = history.slice(-20).reverse().map(h =>
                    `<div class="prompt-history-item" style="padding:6px 10px;cursor:pointer;font-size:12px;border-bottom:1px solid var(--border-secondary);overflow:hidden;text-overflow:ellipsis;white-space:nowrap;" onclick="document.getElementById('imagePrompt').value='${h.prompt.replace(/'/g, "\\'")}';document.getElementById('promptHistoryDropdown').style.display='none';" title="${h.prompt}">${h.prompt.substring(0, 80)}</div>`
                ).join('');
            }
            dropdown.style.display = 'block';
        });
    }

    // =========================================================================
    // INPAINT
    // =========================================================================

    _inpaintImageB64 = null;
    _inpaintCanvas = null;
    _inpaintCtx = null;
    _inpaintPainting = false;

    handleInpaintSourceUpload(event) {
        const file = event.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            this._inpaintImageB64 = e.target.result;
            const preview = document.getElementById('inpaintPreview');
            if (preview) { preview.src = e.target.result; preview.style.display = 'block'; }

            // Setup canvas
            const wrapper = document.getElementById('inpaintCanvasWrapper');
            if (wrapper) wrapper.style.display = 'block';
            const canvas = document.getElementById('inpaintCanvas');
            if (!canvas) return;
            const img = new Image();
            img.onload = () => {
                const maxW = 512;
                const scale = Math.min(maxW / img.width, maxW / img.height, 1);
                canvas.width = Math.round(img.width * scale);
                canvas.height = Math.round(img.height * scale);
                const ctx = canvas.getContext('2d');
                ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
                this._inpaintCanvas = canvas;
                this._inpaintCtx = ctx;
                this._inpaintOrigImg = img;
                this._inpaintScale = scale;
                this._setupInpaintDrawing(canvas, ctx, img, scale);
            };
            img.src = e.target.result;

            document.getElementById('inpaintBtn').disabled = false;
        };
        reader.readAsDataURL(file);
    }

    _setupInpaintDrawing(canvas, ctx, bgImg, scale) {
        // Mask layer
        this._maskCanvas = document.createElement('canvas');
        this._maskCanvas.width = canvas.width;
        this._maskCanvas.height = canvas.height;
        this._maskCtx = this._maskCanvas.getContext('2d');
        this._maskCtx.fillStyle = 'black';
        this._maskCtx.fillRect(0, 0, canvas.width, canvas.height);

        const getPos = (e) => {
            const rect = canvas.getBoundingClientRect();
            const scaleX = canvas.width / rect.width;
            const scaleY = canvas.height / rect.height;
            if (e.touches) { return { x: (e.touches[0].clientX - rect.left) * scaleX, y: (e.touches[0].clientY - rect.top) * scaleY }; }
            return { x: (e.clientX - rect.left) * scaleX, y: (e.clientY - rect.top) * scaleY };
        };

        const brush = () => parseInt(document.getElementById('inpaintBrushSize')?.value || 30);

        const draw = (e) => {
            if (!this._inpaintPainting) return;
            e.preventDefault();
            const p = getPos(e);
            // Draw on mask
            this._maskCtx.fillStyle = 'white';
            this._maskCtx.beginPath();
            this._maskCtx.arc(p.x, p.y, brush() / 2, 0, Math.PI * 2);
            this._maskCtx.fill();
            // Redraw canvas
            ctx.drawImage(bgImg, 0, 0, canvas.width, canvas.height);
            ctx.globalAlpha = 0.45;
            ctx.drawImage(this._maskCanvas, 0, 0);
            ctx.globalAlpha = 1.0;
        };

        canvas.onmousedown = canvas.ontouchstart = (e) => { this._inpaintPainting = true; draw(e); };
        canvas.onmousemove = canvas.ontouchmove = draw;
        canvas.onmouseup = canvas.ontouchend = canvas.onmouseleave = () => { this._inpaintPainting = false; };
    }

    clearInpaintMask() {
        if (!this._maskCtx || !this._inpaintCtx || !this._inpaintOrigImg) return;
        this._maskCtx.fillStyle = 'black';
        this._maskCtx.fillRect(0, 0, this._maskCanvas.width, this._maskCanvas.height);
        this._inpaintCtx.drawImage(this._inpaintOrigImg, 0, 0, this._inpaintCanvas.width, this._inpaintCanvas.height);
    }

    async generateInpaint() {
        if (!this._inpaintImageB64 || !this._maskCanvas) return;
        const btn = document.getElementById('inpaintBtn');
        const origText = btn.textContent;
        btn.disabled = true; btn.textContent = '⏳ Inpainting...';

        try {
            const maskB64 = this._maskCanvas.toDataURL('image/png');
            const prompt = document.getElementById('inpaintPrompt')?.value || '';
            const resp = await fetch('/api/sd-inpaint', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: this._inpaintImageB64,
                    mask: maskB64,
                    prompt,
                    negative_prompt: document.getElementById('inpaintNegativePrompt')?.value || '',
                    denoising_strength: parseFloat(document.getElementById('inpaintDenoising')?.value || 0.75),
                    steps: parseInt(document.getElementById('inpaintSteps')?.value || 30),
                    save_to_storage: true,
                }),
            });
            const data = await resp.json();
            if (data.success && data.image) {
                this._showGeneratedImage(data.image, 'inpaint');
            } else {
                throw new Error(data.error || 'Inpaint failed');
            }
        } catch (e) {
            console.error('[Inpaint]', e);
            alert('❌ Inpaint error: ' + e.message);
        } finally { btn.disabled = false; btn.textContent = origText; }
    }

    // =========================================================================
    // CONTROLNET
    // =========================================================================

    _controlnetImageB64 = null;

    handleControlnetSourceUpload(event) {
        const file = event.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            this._controlnetImageB64 = e.target.result;
            const preview = document.getElementById('controlnetPreview');
            if (preview) { preview.src = e.target.result; preview.style.display = 'block'; }
            document.getElementById('controlnetBtn').disabled = false;
        };
        reader.readAsDataURL(file);
    }

    async generateControlNet() {
        if (!this._controlnetImageB64) return;
        const btn = document.getElementById('controlnetBtn');
        const origText = btn.textContent;
        btn.disabled = true; btn.textContent = '⏳ Generating...';

        try {
            const resp = await fetch('/api/sd-controlnet', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    control_image: this._controlnetImageB64,
                    controlnet_type: document.getElementById('controlnetType')?.value || 'canny',
                    controlnet_weight: parseFloat(document.getElementById('controlnetWeight')?.value || 1.0),
                    prompt: document.getElementById('controlnetPrompt')?.value || '',
                    negative_prompt: document.getElementById('controlnetNegativePrompt')?.value || '',
                    width: parseInt(document.getElementById('controlnetWidth')?.value || 512),
                    height: parseInt(document.getElementById('controlnetHeight')?.value || 512),
                    steps: parseInt(document.getElementById('controlnetSteps')?.value || 30),
                    save_to_storage: true,
                }),
            });
            const data = await resp.json();
            if (data.success && data.images?.length) {
                this._showGeneratedImage(data.images[0], 'controlnet');
            } else {
                throw new Error(data.error || 'ControlNet generation failed');
            }
        } catch (e) {
            console.error('[ControlNet]', e);
            alert('❌ ControlNet error: ' + e.message);
        } finally { btn.disabled = false; btn.textContent = origText; }
    }

    // =========================================================================
    // UPSCALE
    // =========================================================================

    _upscaleImageB64 = null;

    handleUpscaleSourceUpload(event) {
        const file = event.target.files?.[0];
        if (!file) return;
        const reader = new FileReader();
        reader.onload = (e) => {
            this._upscaleImageB64 = e.target.result;
            const preview = document.getElementById('upscalePreview');
            if (preview) { preview.src = e.target.result; preview.style.display = 'block'; }
            document.getElementById('upscaleBtn').disabled = false;
        };
        reader.readAsDataURL(file);
    }

    async generateUpscale() {
        if (!this._upscaleImageB64) return;
        const btn = document.getElementById('upscaleBtn');
        const origText = btn.textContent;
        btn.disabled = true; btn.textContent = '⏳ Upscaling...';

        try {
            const resp = await fetch('/api/sd-upscale', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    image: this._upscaleImageB64,
                    upscaler: document.getElementById('upscalerSelect')?.value || 'R-ESRGAN 4x+',
                    scale_factor: parseFloat(document.getElementById('upscaleFactor')?.value || 4),
                    restore_faces: document.getElementById('upscaleRestoreFaces')?.checked || false,
                    save_to_storage: true,
                }),
            });
            const data = await resp.json();
            if (data.success && data.image) {
                this._showGeneratedImage(data.image, 'upscale');
                const info = `Upscaled: ${data.original_size?.join?.('x') || '?'} → ${data.upscaled_size?.join?.('x') || '?'}`;
                console.log('[Upscale]', info);
            } else {
                throw new Error(data.error || 'Upscale failed');
            }
        } catch (e) {
            console.error('[Upscale]', e);
            alert('❌ Upscale error: ' + e.message);
        } finally { btn.disabled = false; btn.textContent = origText; }
    }

    // =========================================================================
    // BATCH GENERATION
    // =========================================================================

    async generateBatch() {
        const btn = document.getElementById('batchBtn');
        const origText = btn.textContent;
        btn.disabled = true; btn.textContent = '⏳ Generating...';

        try {
            const prompt = document.getElementById('batchPrompt')?.value || '';
            if (!prompt) { alert('Please enter a prompt'); return; }
            const resp = await fetch('/api/sd-batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    prompt,
                    negative_prompt: document.getElementById('batchNegativePrompt')?.value || '',
                    count: parseInt(document.getElementById('batchCount')?.value || 4),
                    width: parseInt(document.getElementById('batchWidth')?.value || 1024),
                    height: parseInt(document.getElementById('batchHeight')?.value || 1024),
                    steps: parseInt(document.getElementById('batchSteps')?.value || 20),
                    cfg_scale: parseFloat(document.getElementById('batchCfgScale')?.value || 7),
                    save_to_storage: true,
                }),
            });
            const data = await resp.json();
            if (data.success && data.results?.length) {
                const grid = document.getElementById('batchGrid');
                const container = document.getElementById('batchResults');
                if (grid && container) {
                    grid.innerHTML = data.results.map((r, i) =>
                        `<div style="position:relative;cursor:pointer;" onclick="window._showBatchImage('${i}')">
                            <img src="data:image/png;base64,${r.image}" style="width:100%;border-radius:var(--radius-sm);" alt="Variation ${i+1}">
                            <span style="position:absolute;bottom:4px;left:4px;background:rgba(0,0,0,0.6);color:#fff;padding:2px 6px;border-radius:4px;font-size:11px;">seed: ${r.seed}</span>
                        </div>`
                    ).join('');
                    container.style.display = 'block';
                    this._batchResults = data.results;
                }
                // Save prompt to history
                this.savePromptToHistory(prompt, document.getElementById('batchNegativePrompt')?.value);
            } else {
                throw new Error(data.error || 'Batch generation failed');
            }
        } catch (e) {
            console.error('[Batch]', e);
            alert('❌ Batch error: ' + e.message);
        } finally { btn.disabled = false; btn.textContent = origText; }
    }

    // =========================================================================
    // SHARED HELPERS
    // =========================================================================

    _showGeneratedImage(b64, type) {
        const container = document.getElementById('generatedImageContainer');
        const img = document.getElementById('generatedImage');
        if (container && img) {
            img.src = 'data:image/png;base64,' + b64;
            container.classList.add('open');
            this.currentGeneratedImage = { image: b64, type };
        }
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }

    _escapeAttr(text) {
        return (text || '').replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/'/g, '&#39;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }
}
