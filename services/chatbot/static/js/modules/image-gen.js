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
            modal.classList.add('active');
            
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
     * Close image generation modal
     */
    closeModal() {
        const modal = document.getElementById('imageGenModal');
        if (modal) {
            modal.classList.remove('active');
        }
    }

    /**
     * Switch between text2img and img2img tabs
     */
    switchTab(tabName) {
        const text2imgTab = document.getElementById('text2imgTab');
        const img2imgTab = document.getElementById('img2imgTab');
        
        // Hide all tabs
        if (text2imgTab) {
            text2imgTab.style.display = 'none';
            text2imgTab.classList.remove('active');
        }
        if (img2imgTab) {
            img2imgTab.style.display = 'none';
            img2imgTab.classList.remove('active');
        }
        
        // Remove active from all tab buttons
        document.querySelectorAll('.image-gen-tabs .tab-btn').forEach(btn => {
            btn.classList.remove('active');
        });
        
        // Show selected tab
        if (tabName === 'text2img' && text2imgTab) {
            text2imgTab.style.display = 'block';
            text2imgTab.classList.add('active');
            document.querySelectorAll('.image-gen-tabs .tab-btn')[0]?.classList.add('active');
        } else if (tabName === 'img2img' && img2imgTab) {
            img2imgTab.style.display = 'block';
            img2imgTab.classList.add('active');
            document.querySelectorAll('.image-gen-tabs .tab-btn')[1]?.classList.add('active');
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
        }
    }

    /**
     * Populate model select dropdown
     */
    populateModelSelect() {
        const selects = document.querySelectorAll('#modelCheckpoint, #img2imgModelSelect');
        selects.forEach(select => {
            if (select && this.sdModels.length > 0) {
                select.innerHTML = this.sdModels.map(model => 
                    `<option value="${model}">${model}</option>`
                ).join('');
            }
        });
    }

    /**
     * Populate sampler select dropdown
     */
    populateSamplerSelect() {
        const selects = document.querySelectorAll('#samplerSelect, #img2imgSamplerSelect');
        selects.forEach(select => {
            if (select && this.samplers.length > 0) {
                select.innerHTML = this.samplers.map(sampler => 
                    `<option value="${sampler}">${sampler}</option>`
                ).join('');
            }
        });
    }

    /**
     * Populate LoRA list
     */
    populateLoraList() {
        const containers = document.querySelectorAll('#loraList, #img2imgLoraList');
        containers.forEach(container => {
            if (container && this.loras.length > 0) {
                container.innerHTML = this.loras.map(lora => `
                    <div class="lora-item">
                        <input type="checkbox" id="lora-${lora}" value="${lora}">
                        <label for="lora-${lora}">${lora}</label>
                    </div>
                `).join('');
                
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
                    this.vaes.map(vae => `<option value="${vae}">${vae}</option>`).join('');
                
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
     * Get selected LoRAs
     */
    getSelectedLoras(containerId = 'loraList') {
        const container = document.getElementById(containerId);
        if (!container) return [];
        
        const selectedLoras = [];
        container.querySelectorAll('input[type="checkbox"]:checked').forEach(checkbox => {
            selectedLoras.push({
                name: checkbox.value,
                weight: 1.0 // Default weight
            });
        });
        
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
                    lora_models: this.getSelectedLoras('loraList'),
                    vae: document.getElementById('vaeSelect')?.value || ''
                };
            }
            
            const data = await this.apiService.generateImage(params);
            if (data.image) {
                this.currentGeneratedImage = data;
                this.displayGeneratedImage(data.image);
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
                    steps: parseInt(document.getElementById('img2imgSteps')?.value) || 30,
                    cfg_scale: parseFloat(document.getElementById('img2imgCfgScale')?.value) || 7.0,
                    width: parseInt(document.getElementById('img2imgWidth')?.value) || 512,
                    height: parseInt(document.getElementById('img2imgHeight')?.value) || 512,
                    denoising_strength: parseFloat(document.getElementById('denoisingStrength')?.value) || 0.75,
                    sampler_name: document.getElementById('img2imgSampler')?.value || 'DPM++ 2M Karras',
                    seed: -1,
                    lora_models: this.getSelectedLoras('img2imgLoraList'),
                    vae: document.getElementById('img2imgVaeSelect')?.value || ''
                };
            }
            
            const data = await this.apiService.generateImg2Img(params);
            if (data.image) {
                this.currentGeneratedImage = data;
                this.displayGeneratedImage(data.image);
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
     * Display generated image
     */
    displayGeneratedImage(base64Image) {
        const imgElement = document.getElementById('generatedImage');
        const container = document.getElementById('generatedImageContainer');
        
        if (imgElement && container) {
            imgElement.src = 'data:image/png;base64,' + base64Image;
            container.style.display = 'block';
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
            // Get active tags (exclude filtered ones)
            const activeTags = this.getActiveTags();
            
            if (activeTags.length === 0) {
                throw new Error('All tags are filtered. Please keep some tags active.');
            }
            
            // Prepare context for Grok
            const tagsByCategory = {};
            for (const [category, tags] of Object.entries(this.extractedCategories)) {
                if (!this.filteredCategories.has(category)) {
                    tagsByCategory[category] = tags
                        .filter(tag => !this.filteredTags.has(tag.name))
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
            
            // Call API
            const response = await fetch('/api/generate-prompt-grok', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    context: context,
                    tags: activeTags
                })
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.error || `HTTP ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.prompt) {
                console.log(`[Grok Prompt] Generated prompt (${data.tags_used} tags)`);
                console.log(`[Grok Prompt] Generated negative prompt`);
                return {
                    prompt: data.prompt,
                    negative_prompt: data.negative_prompt || ''
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
                sampler: document.getElementById('samplerSelect')?.value || document.getElementById('img2imgSampler')?.value || 'N/A',
                steps: document.getElementById('imageSteps')?.value || document.getElementById('img2imgSteps')?.value || 'N/A',
                cfg_scale: document.getElementById('cfgScale')?.value || document.getElementById('img2imgCfgScale')?.value || 'N/A',
                size: `${document.getElementById('imageWidth')?.value || document.getElementById('img2imgWidth')?.value}x${document.getElementById('imageHeight')?.value || document.getElementById('img2imgHeight')?.value}`,
                denoising_strength: document.getElementById('denoisingStrength')?.value || 'N/A',
                lora_models: this.getSelectedLoras('loraList').concat(this.getSelectedLoras('img2imgLoraList')).map(l => l.name).join(', ') || 'None',
                vae: document.getElementById('vaeSelect')?.value || document.getElementById('img2imgVaeSelect')?.value || 'Auto'
            };
            
            // Create message HTML with image and metadata
            const timestamp = new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' });
            const messageHtml = `
                <div class="message ai">
                    <div class="message-content">
                        <div class="message-header">
                            <span class="message-role">🎨 AI Image Generation</span>
                            <span class="message-timestamp">${timestamp}</span>
                        </div>
                        <div class="message-body">
                            <img src="data:image/png;base64,${this.currentGeneratedImage.image}" 
                                 style="max-width: 100%; border-radius: 8px; margin-bottom: 10px; cursor: pointer;"
                                 onclick="openImagePreview(this)" />
                            <div style="background: rgba(0,0,0,0.05); padding: 12px; border-radius: 8px; font-size: 13px; margin-top: 10px;">
                                <div style="margin-bottom: 8px;"><strong>📝 Prompt:</strong> ${metadata.prompt}</div>
                                <div style="margin-bottom: 8px;"><strong>🚫 Negative:</strong> ${metadata.negative_prompt}</div>
                                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 10px;">
                                    <div><strong>🤖 Model:</strong> ${metadata.model}</div>
                                    <div><strong>⚙️ Sampler:</strong> ${metadata.sampler}</div>
                                    <div><strong>🔢 Steps:</strong> ${metadata.steps}</div>
                                    <div><strong>🎚️ CFG:</strong> ${metadata.cfg_scale}</div>
                                    <div><strong>📐 Size:</strong> ${metadata.size}</div>
                                    ${metadata.denoising_strength !== 'N/A' ? `<div><strong>🔧 Denoising:</strong> ${metadata.denoising_strength}</div>` : ''}
                                    <div><strong>🎨 LoRA:</strong> ${metadata.lora_models}</div>
                                    <div><strong>🔧 VAE:</strong> ${metadata.vae}</div>
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
            
            // Show success feedback
            alert('✅ Đã gửi ảnh vào chat với đầy đủ thông tin!');
            
        } catch (error) {
            console.error('[Image Gen] Error sending to chat:', error);
            alert('❌ Lỗi khi gửi ảnh vào chat: ' + error.message);
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
            "1girl, beautiful, detailed face, long hair, cherry blossoms, sunset, masterpiece, best quality",
            "cyberpunk city, neon lights, rain, futuristic, detailed, 8k, photorealistic",
            "fantasy landscape, mountains, magic, ethereal, glowing, epic, cinematic lighting",
            "portrait, anime style, cute, colorful, detailed eyes, soft lighting, high quality"
        ];
        const promptEl = document.getElementById('imagePrompt');
        if (promptEl) {
            promptEl.value = prompts[Math.floor(Math.random() * prompts.length)];
        }
    }
    
    randomNegativePrompt() {
        const negativePrompts = [
            "bad quality, blurry, distorted, ugly, worst quality, low resolution",
            "nsfw, lowres, bad anatomy, bad hands, text, error, missing fingers",
            "watermark, signature, username, low quality, worst quality"
        ];
        const negPromptEl = document.getElementById('negativePrompt');
        if (negPromptEl) {
            negPromptEl.value = negativePrompts[Math.floor(Math.random() * negativePrompts.length)];
        }
    }
    
    randomImg2ImgPrompt() {
        const prompts = [
            "improve quality, enhance details, masterpiece",
            "anime style, vibrant colors, high quality",
            "photorealistic, 8k, detailed, professional"
        ];
        const promptEl = document.getElementById('img2imgPrompt');
        if (promptEl) {
            promptEl.value = prompts[Math.floor(Math.random() * prompts.length)];
        }
    }
    
    randomImg2ImgNegativePrompt() {
        const negativePrompts = [
            "bad quality, blurry, worst quality",
            "low resolution, artifacts, distorted",
            "nsfw, watermark, signature"
        ];
        const negPromptEl = document.getElementById('img2imgNegativePrompt');
        if (negPromptEl) {
            negPromptEl.value = negativePrompts[Math.floor(Math.random() * negativePrompts.length)];
        }
    }
    
    /**
     * Lora management
     */
    addLoraSelection() {
        // Implementation for adding Lora selection
        console.log('[Image Gen] Add Lora selection');
    }
    
    addImg2imgLoraSelection() {
        // Implementation for adding Img2Img Lora selection
        console.log('[Image Gen] Add Img2Img Lora selection');
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
}
