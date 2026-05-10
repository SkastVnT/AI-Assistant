/**
 * Image Generation Legacy Bindings Module
 * SD window function wrappers, tag display, tag toggle,
 * and generated-image overlay close.
 *
 * Extracted from main.js — no behavior change.
 */

// ── Tag display for Img2Img feature extraction ─────────────────────

function displayExtractedTags(tags, categories) {
    const container = document.getElementById('extractedTags');
    const list = document.getElementById('tagsList');

    if (!container || !list) {
        console.error('[Display Tags] Container or list not found');
        return;
    }

    // Category icons
    const categoryIcons = {
        hair: '💇', eyes: '👀', face: '😊', clothing: '👗',
        accessories: '💍', body: '🧘', pose: '🤸', background: '🌄',
        character: '👤', style: '🎨', quality: '⭐', other: '🏷️'
    };

    // Initialize selectedTags if not exists (all selected by default)
    if (!window.selectedImageTags) {
        window.selectedImageTags = new Set(tags.map(t => t.name));
    }

    // Build HTML by category
    let html = '';
    Object.keys(categories).forEach(catName => {
        const catTags = categories[catName];
        if (!catTags || catTags.length === 0) return;

        const icon = categoryIcons[catName] || '🏷️';
        const catTitle = catName.charAt(0).toUpperCase() + catName.slice(1);

        html += `
            <div class="tag-category">
                <div class="category-header" onclick="toggleCategory('${catName}')">
                    ${icon} <strong>${catTitle}</strong> (${catTags.length})
                    <span class="category-toggle">▼</span>
                </div>
                <div class="category-tags" id="cat-${catName}">
                    ${catTags.map(tag => {
                        const isSelected = window.selectedImageTags.has(tag.name);
                        return `
                        <span class="tag-item ${isSelected ? 'tag-selected' : 'tag-unselected'}" 
                              onclick="toggleImageTag('${tag.name.replace(/'/g, "\\'")}', this)" 
                              title="${isSelected ? 'Click để bỏ chọn' : 'Click để chọn'} (Confidence: ${(tag.confidence * 100).toFixed(1)}%)">
                            ${tag.name} <small>(${(tag.confidence * 100).toFixed(0)}%)</small>
                        </span>
                    `}).join('')}
                </div>
            </div>
        `;
    });

    list.innerHTML = html;
    container.style.display = 'block';

    // Enable generate button
    const generateBtn = document.getElementById('generateImg2ImgBtn');
    if (generateBtn) {
        generateBtn.disabled = false;
    }

    console.log('[Display Tags] Displayed', tags.length, 'tags in', Object.keys(categories).length, 'categories');
}

/**
 * Initialize image-gen window bindings and tag toggle globals.
 * @param {object} app - ChatBotApp instance (needs app.imageGen, app.uiUtils)
 * Call from DOMContentLoaded.
 */
export function initImageGenBindings(app) {
    // ── SD modal function wrappers ──────────────────────────────────
    window.closeImageModal = () => app.imageGen.closeModal();
    window.switchImageGenTab = (tab) => app.imageGen.switchTab(tab);
    window.randomPrompt = () => app.imageGen.randomPrompt();
    window.randomNegativePrompt = () => app.imageGen.randomNegativePrompt();
    window.randomImg2ImgPrompt = () => app.imageGen.randomImg2ImgPrompt();
    window.randomImg2ImgNegativePrompt = () => app.imageGen.randomImg2ImgNegativePrompt();
    window.addLoraSelection = () => app.imageGen.addLoraSelection();
    window.addImg2imgLoraSelection = () => app.imageGen.addImg2imgLoraSelection();
    window.removeLoraSelection = (id) => app.imageGen.removeLoraSelection(id);
    window.removeImg2imgLoraSelection = (id) => app.imageGen.removeImg2imgLoraSelection(id);

    window.generateImage = async () => {
        const btn = document.getElementById('generateImageBtn');
        if (!btn) return;

        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ Đang tạo ảnh...';

        try {
            await app.imageGen.generateText2Img();
        } catch (error) {
            console.error('[Generate Image] Error:', error);
            app.uiUtils.showAlert('❌ Lỗi: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };

    window.generateImg2Img = async () => {
        const btn = document.getElementById('generateImg2ImgBtn');
        if (!btn) return;

        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ Đang tạo ảnh...';

        try {
            await app.imageGen.generateImg2Img();
        } catch (error) {
            console.error('[Generate Img2Img] Error:', error);
            app.uiUtils.showAlert('❌ Lỗi: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };

    window.extractFeatures = async () => {
        const btn = event.target;
        if (!btn) return;

        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '⏳ Đang trích xuất...';

        try {
            const data = await app.imageGen.extractFeatures();

            if (data && data.tags) {
                // Display tags in UI
                displayExtractedTags(data.tags, data.categories || {});
                alert(`✅ Đã trích xuất ${data.tags.length} tags!`);
            }
        } catch (error) {
            console.error('[Extract Features] Error:', error);
            alert('❌ Lỗi: ' + error.message);
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };

    window.autoGeneratePromptFromTags = async () => {
        const btn = event.target;
        if (!btn) return;

        const originalText = btn.textContent;
        btn.disabled = true;
        btn.textContent = '🤖 Đang tạo prompt & chọn best options...';

        try {
            const result = await app.imageGen.generatePromptFromTags();

            if (result && result.prompt) {
                const promptTextarea = document.getElementById('img2imgPrompt');
                const negativeTextarea = document.getElementById('img2imgNegativePrompt');

                if (promptTextarea) {
                    promptTextarea.value = result.prompt;
                    promptTextarea.style.transition = 'all 0.3s';
                    promptTextarea.style.boxShadow = '0 0 20px rgba(102, 126, 234, 0.6)';
                    setTimeout(() => { promptTextarea.style.boxShadow = ''; }, 1500);
                }

                if (negativeTextarea && result.negative_prompt) {
                    negativeTextarea.value = result.negative_prompt;
                    negativeTextarea.style.transition = 'all 0.3s';
                    negativeTextarea.style.boxShadow = '0 0 20px rgba(255, 87, 34, 0.6)';
                    setTimeout(() => { negativeTextarea.style.boxShadow = ''; }, 1500);
                }

                // Auto-pick best Model, LoRA, VAE, Sampler
                app.imageGen.autoPickBestOptions();

                // Scroll to prompt and show summary
                if (promptTextarea) {
                    promptTextarea.scrollIntoView({ behavior: 'smooth', block: 'center' });
                }

                const modelVal = document.getElementById('img2imgModelSelect')?.value || '—';
                const vaeVal = document.getElementById('img2imgVaeSelect')?.value || 'Default';
                const promptPreview = result.prompt.substring(0, 60);
                alert(`✅ Auto-configured!\n\n📝 Prompt: ${promptPreview}...\n🎨 Model: ${modelVal}\n🔧 VAE: ${vaeVal}\n🎯 LoRA + params đã tự động chọn`);
            }
        } catch (error) {
            console.error('[Auto-Generate Prompt] Error:', error);
            alert('❌ Lỗi: ' + error.message + '\n\n💡 Kiểm tra GROK_API_KEY trong file .env');
        } finally {
            btn.disabled = false;
            btn.textContent = originalText;
        }
    };

    window.toggleTag = (tag) => app.imageGen.toggleTag(tag);
    window.toggleCategory = (category) => app.imageGen.toggleCategory(category);
    window.copyImageToChat = () => app.imageGen.sendImageToChat();
    window.downloadGeneratedImage = () => app.imageGen.downloadGeneratedImage();
    window.shareImageToImgBB = () => app.imageGen.shareImageToImgBB();
    window.handleSourceImageUpload = (event) => app.imageGen.handleSourceImageUpload(event);

    // Advanced image gen features
    window.applyNegativePreset = (v) => app.imageGen.applyNegativePreset(v);
    window.showPromptHistory = () => app.imageGen.showPromptHistory();
    window.handleInpaintSourceUpload = (event) => app.imageGen.handleInpaintSourceUpload(event);
    window.clearInpaintMask = () => app.imageGen.clearInpaintMask();
    window.generateInpaint = () => app.imageGen.generateInpaint();
    window.handleControlnetSourceUpload = (event) => app.imageGen.handleControlnetSourceUpload(event);
    window.generateControlNet = () => app.imageGen.generateControlNet();
    window.handleUpscaleSourceUpload = (event) => app.imageGen.handleUpscaleSourceUpload(event);
    window.generateUpscale = () => app.imageGen.generateUpscale();
    window.generateBatch = () => app.imageGen.generateBatch();
    window._showBatchImage = (idx) => {
        const results = app.imageGen._batchResults;
        if (results && results[idx]) {
            app.imageGen._showGeneratedImage(results[idx].image, 'batch');
        }
    };

    // Load negative presets on modal open
    app.imageGen.loadNegativePresets();

    window.closeGeneratedImageOverlay = (event) => {
        const container = document.getElementById('generatedImageContainer');
        if (container) {
            // If event is provided and clicked element is the overlay (not modal content), close it
            if (!event || event.target === container) {
                container.classList.remove('open');
            }
        }
    };

    // ── Tag toggle ──────────────────────────────────────────────────

    window.toggleImageTag = (tagName, element) => {
        if (!window.selectedImageTags) {
            window.selectedImageTags = new Set();
        }

        if (window.selectedImageTags.has(tagName)) {
            // Deselect
            window.selectedImageTags.delete(tagName);
            element.classList.remove('tag-selected');
            element.classList.add('tag-unselected');
            element.title = `Click để chọn (${element.querySelector('small').textContent})`;
        } else {
            // Select
            window.selectedImageTags.add(tagName);
            element.classList.remove('tag-unselected');
            element.classList.add('tag-selected');
            element.title = `Click để bỏ chọn (${element.querySelector('small').textContent})`;
        }

        console.log('[Tag Toggle]', tagName, window.selectedImageTags.has(tagName) ? 'SELECTED' : 'UNSELECTED');
        console.log('[Tag Toggle] Total selected:', window.selectedImageTags.size);
    };

    // Get selected tags for prompt generation
    window.getSelectedImageTags = () => {
        return Array.from(window.selectedImageTags || []);
    };
}
