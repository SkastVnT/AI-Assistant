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
                    statusEl.textContent = 'Γ£à Stable Diffusion API: Online';
                    statusEl.style.color = '#4CAF50';
                } else {
                    statusEl.textContent = 'Γ¥î Stable Diffusion API: Offline';
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
                select.innerHTML = '<option value="">ΓÜá∩╕Å No models found ΓÇö place .safetensors in ComfyUI/models/checkpoints/</option>';
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
     * Populate LoRA list
     */
    populateLoraList() {
        const containers = document.querySelectorAll('#loraList, #img2imgLoraList');
        containers.forEach(container => {
            if (container && this.loras.length > 0) {
                container.innerHTML = this.loras.map(lora => {
                    const name = this._itemName(lora);
                    return `
                    <div class="lora-item">
                        <input type="checkbox" id="lora-${name}" value="${name}">
                        <label for="lora-${name}">${name}</label>
                    </div>`;
                }).join('');
                
                // Auto-select recommended LoRAs
                this.autoSelectRecommendedLoras(container);
            }
        });
    }
    
    /**
     * Auto-select recommended LoRA models
     */
    autoSelectRecommendedLoras(container) {
        // Define recommended LoRA patterns (case-insensitive)
        const recommendedPatterns = [
            /detail/i,
            /quality/i,
            /enhance/i,
            /add.*detail/i,
            /realistic/i,
            /improvement/i
        ];
        
        let selectedCount = 0;
        const maxAutoSelect = 2; // Auto-select max 2 LoRAs
        
        container.querySelectorAll('input[type="checkbox"]').forEach(checkbox => {
            if (selectedCount >= maxAutoSelect) return;
            
            const loraName = checkbox.value;
            const shouldSelect = recommendedPatterns.some(pattern => pattern.test(loraName));
            
            if (shouldSelect) {
                checkbox.checked = true;
                selectedCount++;
                console.log(`[Auto-Select] Selected LoRA: ${loraName}`);
            }
        });
        
        // If no recommended LoRAs found, select the first one
        if (selectedCount === 0 && this.loras.length > 0) {
            const firstCheckbox = container.querySelector('input[type="checkbox"]');
            if (firstCheckbox) {
                firstCheckbox.checked = true;
                console.log(`[Auto-Select] Selected first LoRA: ${firstCheckbox.value}`);
            }
        }
    }

    /**
     * Populate VAE select dropdown
     */
    populateVaeSelect() {
        const selects = document.querySelectorAll('#vaeSelect, #img2imgVaeSelect');
        selects.forEach(select => {
            if (select && this.vaes.length > 0) {
                select.innerHTML = '<option value="">Default</option>' +
                    this.vaes.map(vae => {
                        const name = this._itemName(vae);
                        return `<option value="${name}">${name}</option>`;
                    }).join('');
                
                // Auto-select recommended VAE
                this.autoSelectRecommendedVae(select);
            }
        });
    }
    
    /**
     * Auto-select recommended VAE
     */
    autoSelectRecommendedVae(select) {
        // Define recommended VAE patterns (case-insensitive)
        const recommendedPatterns = [
            /anime.*vae/i,
            /anything.*vae/i,
            /vae.*ft.*mse/i,
            /blessed2/i,
            /orangemix/i
        ];
        
        // Try to find and select a recommended VAE
        for (let i = 0; i < select.options.length; i++) {
            const option = select.options[i];
            const vaeName = option.value;
            
            if (vaeName && recommendedPatterns.some(pattern => pattern.test(vaeName))) {
                select.selectedIndex = i;
                console.log(`[Auto-Select] Selected VAE: ${vaeName}`);
                return;
            }
        }
        
        // If no recommended VAE found but VAEs exist, select the first non-default one
        if (this.vaes.length > 0 && select.options.length > 1) {
            select.selectedIndex = 1; // Select first VAE (skip "Default" option)
            console.log(`[Auto-Select] Selected first VAE: ${select.options[1].value}`);
        }
    }

    /**
     * Auto-pick best Model, LoRA, VAE for Img2Img based on extracted tags/prompt
     */
    autoPickBestOptions() {
        // ΓöÇΓöÇ Best Model ΓöÇΓöÇ
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

        // ΓöÇΓöÇ Best VAE ΓöÇΓöÇ
        const vaeSelect = document.getElementById('img2imgVaeSelect');
        if (vaeSelect && vaeSelect.options.length > 1) {
            const vaePriority = [
                /kl-f8-anime/i,
                /orangemix\.vae/i,
                /anime.*vae/i,
                /vae.*ft.*mse/i,
            ];
            let picked = false;
            for (const pattern of vaePriority) {
                for (let i = 0; i < vaeSelect.options.length; i++) {
                    if (pattern.test(vaeSelect.options[i].value)) {
                        vaeSelect.selectedIndex = i;
                        console.log(`[Auto-Pick] VAE: ${vaeSelect.options[i].value}`);
                        picked = true;
                        break;
                    }
                }
                if (picked) break;
            }
        }

        // ΓöÇΓöÇ Best LoRA ΓöÇΓöÇ
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
            // If no quality LoRA found, skip ΓÇö don't force
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

        // ΓöÇΓöÇ Optimal params ΓöÇΓöÇ
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
     * Get selected LoRAs from dynamic rows (loraSelectionContainer) or checkbox list (loraList)
     */
    getSelectedLoras(containerId = 'loraSelectionContainer') {
        const container = document.getElementById(containerId);
        if (!container) return [];

        const selectedLoras = [];

        // Dynamic rows: each row has a .lora-select and optional .lora-weight
        container.querySelectorAll('.lora-select').forEach(sel => {
            if (sel.value) {
                const weightEl = sel.closest('div')?.querySelector('.lora-weight');
                selectedLoras.push({
                    name: sel.value,
                    weight: weightEl ? parseFloat(weightEl.value) || 1.0 : 1.0
                });
            }
        });

        // Fallback: checkbox list (legacy loraList)
        if (selectedLoras.length === 0) {
            container.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
                selectedLoras.push({ name: checkbox.value, weight: 1.0 });
            });
        }

        return selectedLoras;
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
                    vae: document.getElementById('vaeSelect')?.value || ''
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
                    vae: document.getElementById('img2imgVaeSelect')?.value || ''
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
        
        // L╞░u ß║únh v├áo storage v├á metadata (kh├┤ng c├│ prefix)
        this.currentGeneratedImage = { image: base64Image };
        
        // Auto-save image to storage
        this.autoSaveImage(base64Image);
        
        // Gß╗¡i ß║únh thß║│ng v├áo chat (kh├┤ng d├╣ng overlay)
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
                vae: document.getElementById('img2imgVaeSelect')?.value || document.getElementById('vaeSelect')?.value || 'Auto',
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
                console.log('[Auto-Save] Γ£à Saved:', data.filename);
                if (data.cloud_url) {
                    console.log('[Auto-Save] Γÿü∩╕Å ImgBB:', data.cloud_url);
                    
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
            alert('Γ¥î Kh├┤ng c├│ ß║únh ─æß╗â share!');
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
                console.log('[ImgBB Share] Γ£à Success:', data.url);
                
                // Copy to clipboard
                try {
                    await navigator.clipboard.writeText(data.url);
                    alert(`Γ£à Link ─æ├ú ─æ╞░ß╗úc copy v├áo clipboard!\n\n≡ƒöù ${data.url}`);
                } catch (clipError) {
                    // Fallback: Show prompt to copy
                    prompt(`Γ£à ImgBB Link (Ctrl+C to copy):\n\n`, data.url);
                }
            } else {
                throw new Error(data.error || 'Share failed');
            }
            
        } catch (error) {
            console.error('[ImgBB Share] Error:', error);
            alert('Γ¥î Lß╗ùi khi share l├¬n ImgBB: ' + error.message);
        }
    }

    /**
     * Handle source image upload for Img2Img
     */
    handleSourceImageUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        if (!file.type.startsWith('image/')) {
            alert('ΓÜá∩╕Å Vui l├▓ng chß╗ìn file h├¼nh ß║únh!');
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
                vae: document.getElementById('img2imgVaeSelect')?.value || document.getElementById('vaeSelect')?.value || 'Auto',
                seed: document.getElementById('img2imgSeed')?.value || document.getElementById('imageSeed')?.value || '-1'
            };
            
            // Create message HTML with image and metadata
            const timestamp = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
            const messageHtml = `
                <div class="message ai">
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-role">≡ƒÄ¿ AI Image Generation</span>
                            <span class="message-timestamp">${this._escapeHtml(timestamp)}</span>
                        </div>
                        <div class="message-body">
                            <img src="data:image/png;base64,${this.currentGeneratedImage.image}" 
                                 style="max-width: 100%; border-radius: 8px; margin-bottom: 10px; cursor: pointer;"
                                 onclick="openImagePreview(this)" />
                            <div style="background: rgba(0,0,0,0.05); padding: 12px; border-radius: 8px; font-size: 13px; margin-top: 10px;">
                                <div style="margin-bottom: 8px;"><strong>≡ƒô¥ Prompt:</strong> ${this._escapeHtml(metadata.prompt)}</div>
                                <div style="margin-bottom: 8px;"><strong>≡ƒÜ½ Negative:</strong> ${this._escapeHtml(metadata.negative_prompt)}</div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px;">
                                    <div><strong>≡ƒñû Model:</strong> ${this._escapeHtml(metadata.model)}</div>
                                    <div><strong>ΓÜÖ∩╕Å Sampler:</strong> ${this._escapeHtml(metadata.sampler)}</div>
                                    <div><strong>≡ƒöó Steps:</strong> ${this._escapeHtml(metadata.steps)}</div>
                                    <div><strong>≡ƒÄÜ∩╕Å CFG:</strong> ${this._escapeHtml(metadata.cfg_scale)}</div>
                                    <div><strong>≡ƒôÉ Size:</strong> ${this._escapeHtml(metadata.size)}</div>
                                    ${metadata.denoising_strength !== 'N/A' ? `<div><strong>≡ƒöº Denoising:</strong> ${this._escapeHtml(metadata.denoising_strength)}</div>` : ''}
                                    <div><strong>≡ƒÄ¿ LoRA:</strong> ${this._escapeHtml(metadata.lora_models)}</div>
                                    <div><strong>≡ƒöº VAE:</strong> ${this._escapeHtml(metadata.vae)}</div>
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
                    onclick="removeLoraSelection(${id})">Γ£ò</button>`;
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
                    onclick="removeImg2imgLoraSelection(${id})">Γ£ò</button>`;
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
            alert('ΓÜá∩╕Å Please select an image file!');
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
            select.innerHTML = '<option value="">≡ƒôï Preset...</option>';
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
        btn.disabled = true; btn.textContent = 'ΓÅ│ Inpainting...';

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
            alert('Γ¥î Inpaint error: ' + e.message);
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
        btn.disabled = true; btn.textContent = 'ΓÅ│ Generating...';

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
            alert('Γ¥î ControlNet error: ' + e.message);
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
        btn.disabled = true; btn.textContent = 'ΓÅ│ Upscaling...';

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
                const info = `Upscaled: ${data.original_size?.join?.('x') || '?'} ΓåÆ ${data.upscaled_size?.join?.('x') || '?'}`;
                console.log('[Upscale]', info);
            } else {
                throw new Error(data.error || 'Upscale failed');
            }
        } catch (e) {
            console.error('[Upscale]', e);
            alert('Γ¥î Upscale error: ' + e.message);
        } finally { btn.disabled = false; btn.textContent = origText; }
    }

    // =========================================================================
    // BATCH GENERATION
    // =========================================================================

    async generateBatch() {
        const btn = document.getElementById('batchBtn');
        const origText = btn.textContent;
        btn.disabled = true; btn.textContent = 'ΓÅ│ Generating...';

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
            alert('Γ¥î Batch error: ' + e.message);
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
}
