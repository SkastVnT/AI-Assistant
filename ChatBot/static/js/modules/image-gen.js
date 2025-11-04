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
            }
        });
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
            }
        });
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
    handleSourceImageUpload(file) {
        if (!file || !file.type.startsWith('image/')) {
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
     * Send generated image to chat
     */
    sendImageToChat(onSendToChat) {
        if (!this.currentGeneratedImage || !onSendToChat) return;
        
        onSendToChat(this.currentGeneratedImage);
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
