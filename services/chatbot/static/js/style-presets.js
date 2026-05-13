    // STYLE PRESETS (for V1 Image Gen)
    // ════════════════════════════════════════════════════════════
    const stylePresets = {
        anime_xl: { name: "Anime XL", description: "High quality anime art (SDXL)", model: "animagine-xl-4.0-opt.safetensors", negative_prompt: "bad quality, worst quality, low quality, blurry, distorted, deformed, ugly, bad anatomy, bad hands, missing fingers, extra fingers, watermark, text, signature", cfg_scale: 7.0, steps: 25, width: 1024, height: 1024 },
        realistic_xl: { name: "Realistic Fast", description: "Photorealistic Lightning (SDXL)", model: "realvisxlV50_v50LightningBakedvae.safetensors", negative_prompt: "cartoon, anime, illustration, drawing, painting, sketch, bad quality, blurry, distorted, deformed, ugly, watermark, signature", cfg_scale: 2.0, steps: 6, width: 1024, height: 1024 },
        realistic_juggernaut: { name: "Realistic Pro", description: "Professional photorealistic (SDXL)", model: "juggernautXL_v9.safetensors", negative_prompt: "cartoon, anime, illustration, drawing, painting, bad quality, worst quality, blurry, distorted, deformed, ugly, extra limbs, missing limbs, watermark, signature, text", cfg_scale: 4.5, steps: 25, width: 1024, height: 1344 },
        anime_counterfeit: { name: "Anime Classic", description: "Classic anime style (SD 1.5)", model: "counterfeit_v30.safetensors", negative_prompt: "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, blurry", cfg_scale: 7.0, steps: 28, width: 512, height: 768 }
    };
    let currentStyle = 'anime_xl';

    function selectStyle(id) {
        currentStyle = id;
        const p = stylePresets[id];
        if (!p) return;
        document.querySelectorAll('.style-btn').forEach(b => {
            b.className = b.dataset.style === id ? 'btn btn--sm btn--primary style-btn active' : 'btn btn--sm btn--secondary style-btn';
        });
        const d = document.getElementById('styleDescription');
        if (d) d.textContent = p.description;
        const np = document.getElementById('negativePrompt');
        if (np) np.value = p.negative_prompt;
    }

    window.getCurrentStyle = () => currentStyle;
    window.getStylePreset = (id) => stylePresets[id || currentStyle];

    // ════════════════════════════════════════════════════════════


window.selectStyle = selectStyle;

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => selectStyle('anime_xl'));
} else {
    selectStyle('anime_xl');
}
