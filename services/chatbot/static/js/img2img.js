// Img2Img functionality
let sourceImageBase64 = null;
let sourceImageFile = null;
let extractedTags = [];

// Hidden NSFW filter toggle (Ctrl+Shift+N to toggle)
let nsfwFilterEnabled = localStorage.getItem('_nsfw_filter') !== 'off';

// Keyboard shortcut listener for NSFW filter toggle
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.shiftKey && e.key === 'N') {
        e.preventDefault();
        nsfwFilterEnabled = !nsfwFilterEnabled;
        localStorage.setItem('_nsfw_filter', nsfwFilterEnabled ? 'on' : 'off');
        
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
    if (!sourceImageBase64) {
        alert('Vui lòng upload ảnh trước!');
        return;
    }
    
    // Get selected models
    const selectedModels = [];
    if (document.getElementById('modelDeepDanbooru')?.checked) selectedModels.push('deepdanbooru');
    if (document.getElementById('modelCLIP')?.checked) selectedModels.push('clip');
    if (document.getElementById('modelWD14')?.checked) selectedModels.push('wd14');
    
    if (selectedModels.length === 0) {
        alert('Vui lòng chọn ít nhất 1 extraction model!');
        return;
    }
    
    try {
        const response = await fetch('/api/sd/interrogate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: sourceImageBase64,
                models: selectedModels
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.caption) {
            extractedTags = data.caption.split(',').map(tag => tag.trim());
            displayExtractedTags();
        } else {
            alert('Lỗi khi trích xuất: ' + (data.error || 'Unknown error'));
        }
    } catch (error) {
        console.error('Error extracting features:', error);
        alert('Lỗi: ' + error.message);
    }
}

// Display extracted tags
function displayExtractedTags() {
    const tagsContainer = document.getElementById('extractedTags');
    const tagsList = document.getElementById('tagsList');
    
    if (!tagsContainer || !tagsList) return;
    
    tagsContainer.style.display = 'block';
    
    // Group tags by category (simple grouping)
    const html = extractedTags.map((tag, index) => 
        `<span class="tag" style="display: inline-block; background: #4CAF50; color: white; padding: 4px 8px; margin: 4px; border-radius: 4px; cursor: pointer;" onclick="removeTag(${index})">${tag} ×</span>`
    ).join('');
    
    tagsList.innerHTML = html || '<p style="color: #999;">No tags extracted</p>';
}

// Remove a tag
function removeTag(index) {
    extractedTags.splice(index, 1);
    displayExtractedTags();
}

// Generate Img2Img
async function generateImg2Img() {
    if (!sourceImageBase64) {
        alert('Vui lòng upload ảnh nguồn trước!');
        return;
    }
    
    const prompt = document.getElementById('img2imgPrompt').value.trim();
    let negativePrompt = document.getElementById('img2imgNegativePrompt').value.trim();
    const width = parseInt(document.getElementById('img2imgWidth').value);
    const height = parseInt(document.getElementById('img2imgHeight').value);
    const denoisingStrength = parseFloat(document.getElementById('denoisingStrength').value);
    const steps = parseInt(document.getElementById('img2imgSteps').value);
    const cfgScale = parseFloat(document.getElementById('img2imgCfgScale').value);
    
    // Auto-append NSFW filters (respects hidden toggle)
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
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Đang tạo...';
    
    try {
        const response = await fetch('/api/img2img', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: 'data:image/png;base64,' + sourceImageBase64,
                prompt: finalPrompt,
                negative_prompt: negativePrompt,
                width,
                height,
                denoising_strength: denoisingStrength,
                steps,
                cfg_scale: cfgScale,
                sampler_name: 'DPM++ 2M Karras',
                seed: -1,
                save_to_storage: true
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.images && data.images.length > 0) {
            const firstImage = data.images[0];
            let imageUrl;
            
            if (firstImage.startsWith('img2img_')) {
                imageUrl = `/storage/images/${firstImage}`;
            } else if (firstImage.startsWith('data:image')) {
                imageUrl = firstImage;
            } else {
                imageUrl = `data:image/png;base64,${firstImage}`;
            }
            
            // Display result
            const resultDiv = document.getElementById('generatedImageResult');
            if (resultDiv) {
                resultDiv.innerHTML = `
                    <img src="${imageUrl}" alt="Generated Img2Img" style="max-width: 100%; border-radius: 8px;">
                    <div style="margin-top: 10px;">
                        <button onclick="copyImg2ImgToChat()" class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded">
                            📋 Copy to Chat
                        </button>
                        <button onclick="downloadGeneratedImage()" class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded ml-2">
                            💾 Download
                        </button>
                    </div>
                `;
                window.currentGeneratedImage = imageUrl;
            }
            
            alert('✅ Ảnh được tạo thành công!');
        } else {
            alert('❌ Lỗi: ' + (data.error || 'Không thể tạo ảnh'));
        }
    } catch (error) {
        console.error('Error generating img2img:', error);
        alert('❌ Lỗi: ' + error.message);
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = '🎨 Tạo ảnh từ hình ảnh';
    }
}

// Copy Img2Img result to chat
function copyImg2ImgToChat() {
    if (window.currentGeneratedImage) {
        const metadata = `
🖼️ Img2Img Result
📝 Prompt: ${document.getElementById('img2imgPrompt').value.substring(0, 100)}...`;
        
        addMessage(
            `<img src="${window.currentGeneratedImage}" alt="Img2Img" style="max-width: 100%; border-radius: 8px;"><br>${metadata}`,
            false,
            modelSelect.value,
            contextSelect.value,
            formatTimestamp(new Date())
        );
        
        closeImageModal();
    }
}

// Random prompts for Img2Img
function randomImg2ImgPrompt() {
    const prompts = [
        "high quality, detailed, masterpiece, best quality",
        "anime style, vibrant colors, detailed background",
        "photorealistic, 4k, ultra detailed, sharp focus",
        "fantasy art, magical lighting, ethereal atmosphere"
    ];
    
    const promptInput = document.getElementById('img2imgPrompt');
    if (promptInput) {
        promptInput.value = prompts[Math.floor(Math.random() * prompts.length)];
    }
}

function randomImg2ImgNegativePrompt() {
    const baseNegatives = [
        "bad quality, blurry, distorted, ugly, worst quality, low resolution",
        "bad anatomy, bad hands, missing fingers, extra digit, fewer digits",
        "text, watermark, signature, lowres, jpeg artifacts",
        "cropped, out of frame, mutation, deformed, poorly drawn"
    ];
    
    let chosen = baseNegatives[Math.floor(Math.random() * baseNegatives.length)];
    
    // Add NSFW filter if enabled
    if (nsfwFilterEnabled) {
        const nsfwFilter = "nsfw, r18, nude, naked, explicit, sexual, underwear, revealing, suggestive, inappropriate";
        chosen = `${chosen}, ${nsfwFilter}`;
    }
    
    const negativeInput = document.getElementById('img2imgNegativePrompt');
    if (negativeInput) {
        negativeInput.value = negatives[Math.floor(Math.random() * negatives.length)];
    }
}

// Random prompts for Text2Img
function randomPrompt() {
    const prompts = [
        "1girl, beautiful, detailed face, long hair, cherry blossoms, sunset, masterpiece, best quality",
        "cyberpunk city, neon lights, rain, futuristic, detailed, 8k, photorealistic",
        "fantasy landscape, mountains, magic, ethereal, glowing, epic, cinematic lighting",
        "portrait, anime style, cute, colorful, detailed eyes, soft lighting, high quality"
    ];
    
    const promptInput = document.getElementById('imagePrompt');
    if (promptInput) {
        promptInput.value = prompts[Math.floor(Math.random() * prompts.length)];
    }
}

function randomNegativePrompt() {
    const baseNegatives = [
        "bad quality, blurry, distorted, ugly, worst quality, lowres, bad anatomy",
        "bad hands, text, error, missing fingers, extra digit, fewer digits, cropped",
        "worst quality, low quality, normal quality, jpeg artifacts, signature, watermark",
        "disfigured, deformed, cross-eye, body out of frame, grainy, amateur"
    ];
    
    let chosen = baseNegatives[Math.floor(Math.random() * baseNegatives.length)];
    
    // Add NSFW filter if enabled
    if (nsfwFilterEnabled) {
        const nsfwFilter = "nsfw, r18, nude, naked, explicit, sexual, underwear, revealing, suggestive, inappropriate";
        chosen = `${chosen}, ${nsfwFilter}`;
    }
    
    const negativeInput = document.getElementById('negativePrompt');
    if (negativeInput) {
        negativeInput.value = negatives[Math.floor(Math.random() * negatives.length)];
    }
}

// Tab switching
function switchImageGenTab(tabName) {
    // Hide all tabs
    const text2imgTab = document.getElementById('text2imgTab');
    const img2imgTab = document.getElementById('img2imgTab');
    
    if (text2imgTab) text2imgTab.style.display = 'none';
    if (img2imgTab) img2imgTab.style.display = 'none';
    
    // Show selected tab
    if (tabName === 'text2img' && text2imgTab) {
        text2imgTab.style.display = 'block';
    } else if (tabName === 'img2img' && img2imgTab) {
        img2imgTab.style.display = 'block';
    }
    
    // Update tab buttons
    const tabButtons = document.querySelectorAll('.tab-btn');
    tabButtons.forEach(btn => btn.classList.remove('active'));
    
    if (tabName === 'text2img') {
        tabButtons[0]?.classList.add('active');
    } else {
        tabButtons[1]?.classList.add('active');
    }
}

// Lora/VAE management placeholders (can be expanded)
function addLoraSelection() {
    alert('Lora selection feature - to be implemented');
}

function addImg2imgLoraSelection() {
    alert('Img2Img Lora selection feature - to be implemented');
}
