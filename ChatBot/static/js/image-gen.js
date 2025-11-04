// Image generation functionality
let isGeneratingImage = false;

// Handle image generation tool detection in chat
async function handleImageGenerationTool(message, model, context, deepThinking) {
    if (isGeneratingImage) {
        addMessage('⚠️ Đang tạo ảnh... Vui lòng đợi!', false, model, context, formatTimestamp(new Date()));
        return;
    }
    
    isGeneratingImage = true;
    
    try {
        // Build memory context if AI Learning is enabled
        let memoryContext = '';
        if (aiLearningCheckbox.checked && selectedMemories.size > 0) {
            const selectedMemoryData = allMemories.filter(m => selectedMemories.has(m.id));
            memoryContext = '\n\n📚 **Kiến thức từ các bài học đã chọn:**\n\n';
            memoryContext += selectedMemoryData.map(m => 
                `**${m.title}**:\n${m.content.substring(0, 300)}...`
            ).join('\n\n');
        }
        
        // Step 1: Generate prompt with AI
        addMessage('✨ Đang tạo prompt với AI...', false, model, context, formatTimestamp(new Date()));
        
        const promptInstruction = `You are an expert at creating Stable Diffusion prompts. Based on this request, create a detailed prompt:

User request: "${message}"
${memoryContext}

Generate an optimized Stable Diffusion prompt following these rules:
1. Write in English, comma-separated tags
2. Include quality tags: masterpiece, best quality, highly detailed
3. Be descriptive about: subject, style, lighting, composition, colors
4. Keep it concise but detailed (max 100 words)
5. Focus on visual elements only
${memoryContext ? '6. Use knowledge from the lessons above to create more accurate and detailed prompt' : ''}

${deepThinking ? 'Use deep thinking to create the most creative and detailed prompt possible.' : ''}

Return ONLY the prompt, nothing else.`;
        
        const promptResponse = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: promptInstruction,
                model: model,
                context: 'creative',
                deep_thinking: deepThinking,
                ai_learning: false,
                memory_ids: Array.from(selectedMemories)
            })
        });
        
        const promptData = await promptResponse.json();
        const generatedPrompt = promptData.response.trim();
        
        addMessage(`✨ **Prompt được tạo:**\n\`\`\`\n${generatedPrompt}\n\`\`\``, false, model, context, formatTimestamp(new Date()));
        
        // Step 2: Generate negative prompt
        addMessage('🚫 Đang tạo negative prompt...', false, model, context, formatTimestamp(new Date()));
        
        const negativeInstruction = `Based on this positive prompt, generate a detailed negative prompt to avoid common issues:

Positive prompt: "${generatedPrompt}"

Create a negative prompt that includes:
1. Common quality issues (bad quality, blurry, distorted, ugly, worst quality)
2. Anatomy issues (bad anatomy, bad hands, missing fingers, extra digit, fewer digits)
3. Unwanted content (r18, nsfw, nude, explicit, sexual, porn)
4. Technical issues (lowres, jpeg artifacts, cropped, out of frame)
5. Other common problems relevant to this image

Return ONLY the negative prompt (comma-separated keywords), nothing else.`;
        
        const negativeResponse = await fetch('/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: negativeInstruction,
                model: model,
                context: 'precise',
                deep_thinking: false,
                ai_learning: false
            })
        });
        
        const negativeData = await negativeResponse.json();
        const negativePrompt = negativeData.response.trim();
        
        addMessage(`🚫 **Negative prompt được tạo:**\n\`\`\`\n${negativePrompt}\n\`\`\``, false, model, context, formatTimestamp(new Date()));
        
        // Step 3: Check/change to AnythingV4 model
        addMessage('⚙️ Đang chuẩn bị model AnythingV4...', false, model, context, formatTimestamp(new Date()));
        
        try {
            await fetch('/api/sd/change-model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_name: 'anythingv4_0.safetensors' })
            });
        } catch (e) {
            console.log('Model change error (may already be loaded):', e);
        }
        
        // Step 4: Generate image
        addMessage('🎨 Đang tạo ảnh... (có thể mất 10-30 giây)', false, model, context, formatTimestamp(new Date()));
        
        const imageParams = {
            prompt: generatedPrompt,
            negative_prompt: negativePrompt,
            steps: 30,
            cfg_scale: 7,
            width: 512,
            height: 512,
            sampler_name: 'DPM++ 2M Karras',
            seed: -1,
            save_to_storage: true
        };
        
        console.log('Generating image with params:', imageParams);
        
        const imageResponse = await fetch('/api/generate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(imageParams)
        });
        
        const imageData = await imageResponse.json();
        console.log('Image response:', imageData);
        
        if (imageData.success && imageData.images && imageData.images.length > 0) {
            // Check if images are filenames (saved to storage) or base64
            const firstImage = imageData.images[0];
            let imageUrl;
            
            if (firstImage.startsWith('generated_')) {
                // Saved to storage - construct URL
                imageUrl = `/storage/images/${firstImage}`;
            } else if (firstImage.startsWith('data:image')) {
                // Already data URL
                imageUrl = firstImage;
            } else {
                // Base64 string - convert to data URL
                imageUrl = `data:image/png;base64,${firstImage}`;
            }
            
            // Display image with metadata
            const metadata = `
📝 **Prompt:** ${generatedPrompt.substring(0, 100)}...
❌ **Negative:** ${negativePrompt.substring(0, 100)}...
🖼️ **Size:** ${imageParams.width}x${imageParams.height}
🎲 **Steps:** ${imageParams.steps} | **CFG:** ${imageParams.cfg_scale}
⚙️ **Sampler:** ${imageParams.sampler_name}`;
            
            addMessage(
                `🖼️ **Ảnh đã được tạo thành công!**\n\n<img src="${imageUrl}" alt="Generated Image" style="max-width: 100%; border-radius: 8px; margin: 10px 0;">\n\n<div style="background: rgba(76, 175, 80, 0.1); padding: 10px; border-radius: 8px; margin-top: 10px; font-size: 0.9em;">${metadata}</div>`,
                false,
                model,
                context,
                formatTimestamp(new Date())
            );
        } else {
            addMessage(`❌ **Lỗi:** ${imageData.error || 'Không thể tạo ảnh'}`, false, model, context, formatTimestamp(new Date()));
        }
        
    } catch (error) {
        console.error('Image generation error:', error);
        addMessage(`❌ **Lỗi:** ${error.message}`, false, model, context, formatTimestamp(new Date()));
    } finally {
        isGeneratingImage = false;
    }
}

// Manual image generation modal
const imageGenModal = document.getElementById('imageGenModal');
const imageGenBtn = document.getElementById('imageGenBtn');
const closeModalBtn = document.getElementById('closeModal');
const generateImageBtn = document.getElementById('generateImageBtn');

if (imageGenBtn) {
    imageGenBtn.addEventListener('click', openImageModal);
}

if (closeModalBtn) {
    closeModalBtn.addEventListener('click', closeImageModal);
}

if (generateImageBtn) {
    generateImageBtn.addEventListener('click', generateImage);
}

// Close modal when clicking outside
if (imageGenModal) {
    imageGenModal.addEventListener('click', (e) => {
        if (e.target === imageGenModal) {
            closeImageModal();
        }
    });
}

function openImageModal() {
    if (imageGenModal) {
        imageGenModal.style.display = 'flex';
        loadSamplers();
    }
}

function closeImageModal() {
    if (imageGenModal) {
        imageGenModal.style.display = 'none';
    }
}

async function loadSamplers() {
    try {
        const response = await fetch('/api/sd/samplers');
        const data = await response.json();
        
        const samplerSelect = document.getElementById('samplerName');
        if (samplerSelect && data.success) {
            samplerSelect.innerHTML = data.samplers.map(s => 
                `<option value="${s.name}">${s.name}</option>`
            ).join('');
        }
    } catch (error) {
        console.error('Error loading samplers:', error);
    }
}

function adjustStepsAndCFG() {
    const width = parseInt(document.getElementById('imageWidth').value);
    const height = parseInt(document.getElementById('imageHeight').value);
    const stepsInput = document.getElementById('steps');
    const cfgInput = document.getElementById('cfgScale');
    
    const totalPixels = width * height;
    
    if (totalPixels <= 512 * 512) {
        stepsInput.value = 30;
        cfgInput.value = 7;
    } else if (totalPixels <= 768 * 768) {
        stepsInput.value = 25;
        cfgInput.value = 6.5;
    } else {
        stepsInput.value = 20;
        cfgInput.value = 6;
    }
}

async function generateImage() {
    const prompt = document.getElementById('prompt').value.trim();
    const negativePrompt = document.getElementById('negativePrompt').value.trim();
    const width = parseInt(document.getElementById('imageWidth').value);
    const height = parseInt(document.getElementById('imageHeight').value);
    const steps = parseInt(document.getElementById('steps').value);
    const cfgScale = parseFloat(document.getElementById('cfgScale').value);
    const samplerName = document.getElementById('samplerName').value;
    const seed = parseInt(document.getElementById('seed').value);
    
    if (!prompt) {
        alert('Vui lòng nhập prompt!');
        return;
    }
    
    const generateBtn = document.getElementById('generateImageBtn');
    generateBtn.disabled = true;
    generateBtn.textContent = '⏳ Đang tạo...';
    
    try {
        const response = await fetch('/api/generate-image', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt,
                negative_prompt: negativePrompt,
                width,
                height,
                steps,
                cfg_scale: cfgScale,
                sampler_name: samplerName,
                seed,
                save_to_storage: true
            })
        });
        
        const data = await response.json();
        
        if (data.success && data.images && data.images.length > 0) {
            // Check if images are filenames or base64
            const firstImage = data.images[0];
            let imageUrl;
            
            if (firstImage.startsWith('generated_')) {
                // Saved to storage - construct URL
                imageUrl = `/storage/images/${firstImage}`;
            } else if (firstImage.startsWith('data:image')) {
                // Already data URL
                imageUrl = firstImage;
            } else {
                // Base64 string - convert to data URL
                imageUrl = `data:image/png;base64,${firstImage}`;
            }
            
            // Display in result area
            const resultDiv = document.getElementById('generatedImageResult');
            resultDiv.innerHTML = `
                <img src="${imageUrl}" alt="Generated Image" style="max-width: 100%; border-radius: 8px;">
                <div style="margin-top: 10px;">
                    <button onclick="copyImageToChat()" class="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded">
                        📋 Copy to Chat
                    </button>
                    <button onclick="downloadGeneratedImage()" class="px-4 py-2 bg-green-500 hover:bg-green-600 text-white rounded ml-2">
                        💾 Download
                    </button>
                </div>
            `;
            
            // Store current image
            window.currentGeneratedImage = imageUrl;
            
        } else {
            alert('❌ Lỗi: ' + (data.error || 'Không thể tạo ảnh'));
        }
        
    } catch (error) {
        console.error('Error generating image:', error);
        alert('❌ Lỗi: ' + error.message);
    } finally {
        generateBtn.disabled = false;
        generateBtn.textContent = '🎨 Tạo ảnh';
    }
}

function copyImageToChat() {
    if (window.currentGeneratedImage) {
        const metadata = `
🖼️ Image: ${window.currentGeneratedImage}
📝 Prompt: ${document.getElementById('prompt').value.substring(0, 100)}...`;
        
        addMessage(
            `<img src="${window.currentGeneratedImage}" alt="Generated" style="max-width: 100%; border-radius: 8px;"><br>${metadata}`,
            false,
            modelSelect.value,
            contextSelect.value,
            formatTimestamp(new Date())
        );
        
        closeImageModal();
    }
}

function downloadGeneratedImage() {
    if (window.currentGeneratedImage) {
        const link = document.createElement('a');
        link.href = window.currentGeneratedImage;
        link.download = `generated_${Date.now()}.png`;
        link.click();
    }
}

// Auto-adjust on size change
document.getElementById('imageWidth')?.addEventListener('change', adjustStepsAndCFG);
document.getElementById('imageHeight')?.addEventListener('change', adjustStepsAndCFG);
