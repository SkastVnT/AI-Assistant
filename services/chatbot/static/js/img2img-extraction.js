// Img2Img Feature Extraction - Simple & Working
console.log('[IMG2IMG] Script loaded');

let img2imgSourceImage = null;
let img2imgExtractedTags = [];

// Upload image handler
window.handleSourceImageUpload = function(event) {
    console.log('[IMG2IMG] Upload handler called');
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        img2imgSourceImage = e.target.result;
        
        // Show preview
        const preview = document.getElementById('sourceImagePreview');
        const placeholder = document.getElementById('uploadPlaceholder');
        if (preview && placeholder) {
            preview.src = img2imgSourceImage;
            preview.style.display = 'block';
            placeholder.style.display = 'none';
        }
        
        // Show extraction section
        const section = document.getElementById('featureExtractionSection');
        if (section) section.style.display = 'block';
        
        console.log('[IMG2IMG] Image loaded');
    };
    reader.readAsDataURL(file);
};

// Extract features
window.extractFeatures = async function() {
    console.log('[IMG2IMG] Extract features called');
    
    if (!img2imgSourceImage) {
        alert('Vui lòng upload ảnh trước!');
        return;
    }
    
    const btn = event.target;
    btn.disabled = true;
    btn.textContent = '⏳ Đang trích xuất...';
    
    try {
        // Remove base64 prefix
        const base64Data = img2imgSourceImage.split(',')[1];
        
        console.log('[IMG2IMG] Calling /sd-api/interrogate...');
        const response = await fetch('/sd-api/interrogate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: base64Data,
                model: 'deepdanbooru'
            })
        });
        
        const data = await response.json();
        console.log('[IMG2IMG] Response:', data);
        
        if (data.success && data.tags) {
            img2imgExtractedTags = data.tags;
            displayTags(data.tags, data.categories || {});
            alert(`✅ Đã trích xuất ${data.tags.length} tags!`);
        } else {
            throw new Error(data.error || 'Extraction failed');
        }
    } catch (error) {
        console.error('[IMG2IMG] Error:', error);
        alert('❌ Lỗi: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '🔬 Trích xuất đặc trưng';
    }
};

// Display tags
function displayTags(tags, categories) {
    const container = document.getElementById('extractedTags');
    const list = document.getElementById('tagsList');
    
    if (!container || !list) return;
    
    // Group by category
    const grouped = {};
    tags.forEach(tag => {
        const cat = tag.category || 'other';
        if (!grouped[cat]) grouped[cat] = [];
        grouped[cat].push(tag);
    });
    
    // Build HTML
    let html = '';
    const categoryIcons = {
        hair: '💇', eyes: '👁️', face: '😊', clothing: '👔',
        accessories: '👑', body: '🧍', pose: '🤸', background: '🏞️',
        other: '🏷️'
    };
    
    for (const [cat, catTags] of Object.entries(grouped)) {
        const icon = categoryIcons[cat] || '🏷️';
        const catName = categories[cat] || cat;
        
        html += `<div style="margin-bottom: 12px;">
            <div style="font-weight: 600; margin-bottom: 6px; color: #667eea;">${icon} ${catName}</div>
            <div style="display: flex; flex-wrap: wrap; gap: 6px;">`;
        
        catTags.forEach((tag, idx) => {
            const tagName = tag.name || tag;
            const conf = tag.confidence ? ` (${Math.round(tag.confidence * 100)}%)` : '';
            html += `<span onclick="removeTag('${tagName}')" style="display: inline-block; background: linear-gradient(135deg, #667eea, #764ba2); color: white; padding: 6px 12px; border-radius: 20px; font-size: 12px; cursor: pointer; transition: all 0.3s;">${tagName}${conf} ×</span>`;
        });
        
        html += `</div></div>`;
    }
    
    list.innerHTML = html;
    container.style.display = 'block';
    
    // Enable generate button
    const genBtn = document.getElementById('generateImg2ImgBtn');
    if (genBtn) genBtn.disabled = false;
}

// Remove tag
window.removeTag = function(tagName) {
    img2imgExtractedTags = img2imgExtractedTags.filter(t => {
        const name = t.name || t;
        return name !== tagName;
    });
    
    // Re-display
    const container = document.getElementById('tagsList');
    if (container) {
        const spans = container.querySelectorAll('span');
        spans.forEach(span => {
            if (span.textContent.includes(tagName)) {
                span.remove();
            }
        });
    }
};

// Random prompts
window.randomImg2ImgPrompt = function() {
    const prompts = [
        "high quality, masterpiece, detailed, best quality",
        "vibrant colors, anime style, beautiful lighting",
        "photorealistic, 4k, ultra detailed, sharp focus",
        "fantasy art, magical atmosphere, glowing effects"
    ];
    const input = document.getElementById('img2imgPrompt');
    if (input) input.value = prompts[Math.floor(Math.random() * prompts.length)];
};

window.randomImg2ImgNegativePrompt = function() {
    const prompts = [
        "bad quality, blurry, distorted, ugly, worst quality",
        "lowres, bad anatomy, bad hands, text, error",
        "watermark, signature, low quality, jpeg artifacts"
    ];
    const input = document.getElementById('img2imgNegativePrompt');
    if (input) input.value = prompts[Math.floor(Math.random() * prompts.length)];
};

console.log('[IMG2IMG] Ready');
