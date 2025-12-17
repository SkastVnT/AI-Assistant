// Img2Img functionality - Simplified Ver_1.5 style
let sourceImageBase64 = null;
let sourceImageFile = null;
let extractedTags = [];

alert('IMG2IMG SCRIPT LOADED! Check console.');
console.log('[IMG2IMG] Script loaded!');

// Hidden NSFW filter toggle (Ctrl+Shift+N to toggle)
let nsfwFilterEnabled = localStorage.getItem('_nsfw_filter') !== 'off';

// Keyboard shortcut listener for NSFW filter toggle
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.shiftKey && e.key === 'N') {
        e.preventDefault();
        nsfwFilterEnabled = !nsfwFilterEnabled;
        localStorage.setItem('_nsfw_filter', nsfwFilterEnabled ? 'on' : 'off';
        
        // Subtle visual feedback - change page title briefly
        const originalTitle = document.title;
        document.title = nsfwFilterEnabled ? '🛡️ Filter ON' : '🔓 Filter OFF';
        setTimeout(() => { document.title = originalTitle; }, 1000);
    }
});

// Handle source image upload
function handleSourceImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    sourceImageFile = file;
    const reader = new FileReader();
    
    reader.onload = function(e) {
        sourceImageBase64 = e.target.result.split(',')[1]; // Remove data:image/...;base64, prefix
        
        // Show preview
        const preview = document.getElementById('sourceImagePreview');
        const placeholder = document.getElementById('uploadPlaceholder');
        
        if (preview && placeholder) {
            preview.src = e.target.result;
            preview.style.display = 'block';
            placeholder.style.display = 'none';
        }
        
        // Enable feature extraction
        const featureSection = document.getElementById('featureExtractionSection');
        if (featureSection) {
            featureSection.style.display = 'block';
        }
        
        // Enable generate button
        const generateBtn = document.getElementById('generateImg2ImgBtn');
        if (generateBtn) {
            generateBtn.disabled = false;
        }
    };
    
    reader.readAsDataURL(file);
}

// Extract features from uploaded image
async function extractFeatures() {
    console.log('[IMG2IMG] extractFeatures() called');
    console.log('[IMG2IMG] sourceImageBase64:', sourceImageBase64 ? 'exists' : 'null');
    
    if (!sourceImageBase64) {
        alert('Vui lòng upload ảnh trước!');
        return;
    }
    
    console.log('[IMG2IMG] Sending request to /sd-api/interrogate...');
    
    try {
        const response = await fetch('/sd-api/interrogate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: sourceImageBase64,
                model: 'deepdanbooru'
            })
        });
        
        console.log('[IMG2IMG] Response status:', response.status);
        const data = await response.json();
        console.log('[IMG2IMG] Response data:', data);
        
        if (data.success && data.tags) {
            // Extract tag names from response
            extractedTags = data.tags.map(tag => tag.name);
            console.log('[IMG2IMG] Extracted tags count:', extractedTags.length);
            displayExtractedTags();
        } else {
            alert('Lỗi khi trích xuất: ' + (data.error || 'Unknown error'));
        }
    } caole.log('[IMG2IMG] displayExtractedTags() called, tags:', extractedTags.length);
    
    const tagsContainer = document.getElementById('extractedTags');
    const tagsList = document.getElementById('tagsList');
    
    console.log('[IMG2IMG] Elements found:', {
        tagsContainer: !!tagsContainer,
        tagsList: !!tagsList
    });
    
    if (!tagsContainer || !tagsList) {
        console.error('[IMG2IMG] Required elements not found!');
        return;
    }
    
    tagsContainer.style.display = 'block';
    
    // Simple tag display with remove button
    const html = extractedTags.map((tag, index) => 
        `<span class="tag" style="display: inline-block; background: #4CAF50; color: white; padding: 4px 8px; margin: 4px; border-radius: 4px; cursor: pointer;" onclick="removeTag(${index})">${tag} ×</span>`
    ).join('');
    
    tagsList.innerHTML = html || '<p style="color: #999;">No tags extracted</p>';
    console.log('[IMG2IMG] Tags displayed!')
    tagsContainer.style.display = 'block';
    
    // Simple tag display with remove button
    const html = extractedTags.map((tag, index) => 
        `<span class="tag" style="display: inline-block; background: #4CAF50; color: white; padding: 4px 8px; margin: 4px; border-radius: 4px; cursor: pointer;" onclick="removeTag(${index})">${tag} ×</span>`
    ).join('');
    
    tagsList.innerHTML = html || '<p style="color: #999;">No tags extracted</p>';
}

// Remove tag from extracted list
function removeTag(index) {
    extractedTags.splice(index, 1);
    displayExtractedTags();
}

// Generate Img2Img
async function generateImg2Img() {
    if (!sourceImageBase64) {
        alert('Vui lòng upload ảnh nguồn!');
        return;
    }
    
    const prompt = document.getElementById('img2imgPrompt').value.trim();
    let negativePrompt = document.getElementById('img2imgNegativePrompt').value.trim();
    const denoisingStrength = parseFloat(document.getElementById('denoisingStrength').value);
    const steps = parseInt(document.getElementById('img2imgSteps').value);
    const cfgScale = parseFloat(document.getElementById('img2imgCfgScale').value);
    
    // NSFW filter
    if (nsfwFilterEnabled) {
        const nsfwFilters = 'nsfw, r18, nude, naked, explicit, sexual, porn, hentai, underwear, panties, bra, bikini, revealing clothes, suggestive, lewd, ecchi, inappropriate content';
        if (!negativePrompt.toLowerCase().includes('nsfw')) {
            negativePrompt = negativePrompt ? `${negativePrompt}, ${nsfwFilters}` : nsfwFilters;
        }
    }
    
    // Combine extracted tags with user prompt
    let finalPrompt = prompt;
    if (extractedTags.length > 0) {
        const featureWeight = parseInt(document.getElementById('featureWeight').value) / 100;
        if (featureWeight > 0) {
            finalPrompt = extractedTags.join(', ') + (prompt ? ', ' + prompt : '');
        }
    }
    
    if (!finalPrompt) {
        alert('Vui lòng nhập prompt hoặc trích xuất features!');
        return;
    }
    
    const generateBtn = document.getElementById('generateImg2ImgBtn');
    const originalText = generateBtn.textContent;
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Đang tạo...';
    
    try {
        const response = await fetch('/sd-api/img2img', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                init_images: [sourceImageBase64],
                prompt: finalPrompt,
                negative_prompt: negativePrompt,
                denoising_strength: denoisingStrength,
                steps: steps,
                cfg_scale: cfgScale,
                width: 512,
                height: 512
            })
        });
        
        const data = await response.json();
        
        if (data.images && data.images.length > 0) {
            // Display generated image
            const resultImg = document.getElementById('img2imgResultImage');
            const resultContainer = document.getElementById('img2imgResult');
            
            if (resultImg && resultContainer) {
                resultImg.src = 'data:image/png;base64,' + data.images[0];
                resultContainer.style.display = 'block';
            }
        } else {
            alert('Lỗi: Không nhận được ảnh từ server');
        }
    } catch (error) {
        console.error('Error generating image:', error);
        alert('Lỗi khi tạo ảnh: ' + error.message);
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = originalText;
    }
}

// Random prompt generators
function randomPrompt() {
    const prompts = [
        'anime girl, long hair, beautiful eyes, detailed face, soft lighting',
        'anime boy, cool pose, dynamic angle, vibrant colors',
        'fantasy character, magical atmosphere, glowing effects',
        'cute chibi, kawaii style, pastel colors, happy expression',
        'detailed portrait, close-up, beautiful lighting, high quality'
    ];
    document.getElementById('img2imgPrompt').value = prompts[Math.floor(Math.random() * prompts.length)];
}

function randomNegative() {
    const negatives = [
        'bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality',
        'lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, cropped, worst quality',
        'ugly, tiling, poorly drawn hands, poorly drawn feet, poorly drawn face, out of frame, mutation, mutated',
        'bad proportions, deformed, ugly, bad anatomy, disfigured, malformed limbs, watermark'
    ];
    document.getElementById('img2imgNegativePrompt').value = negatives[Math.floor(Math.random() * negatives.length)];
}

// Expose functions to global scope for onclick handlers
window.handleSourceImageUpload = handleSourceImageUpload;
window.extractFeatures = extractFeatures;
window.generateImg2Img = generateImg2Img;
window.removeTag = removeTag;
window.randomPrompt = randomPrompt;
window.randomNegative = randomNegative;

console.log('[IMG2IMG] Functions exposed to window:', {
    handleSourceImageUpload: typeof window.handleSourceImageUpload,
    extractFeatures: typeof window.extractFeatures,
    generateImg2Img: typeof window.generateImg2Img,
    removeTag: typeof window.removeTag,
    randomPrompt: typeof window.randomPrompt,
    randomNegative: typeof window.randomNegative
});
