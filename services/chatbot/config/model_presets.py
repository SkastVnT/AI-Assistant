"""
Model Presets Configuration
Defines presets for different image generation styles
"""

# Model presets for different styles
MODEL_PRESETS = {
    # === ANIME STYLES ===
    "anime_xl": {
        "name": "Anime XL",
        "description": "High quality anime art (SDXL)",
        "model": "animagine-xl-3.1.safetensors",
        "negative_prompt": "bad quality, worst quality, low quality, blurry, distorted, deformed, ugly, bad anatomy, bad hands, missing fingers, extra fingers, fused fingers, too many fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, disfigured, watermark, text, signature",
        "cfg_scale": 7.0,
        "steps": 25,
        "sampler": "euler_ancestral",
        "width": 1024,
        "height": 1024,
        "category": "anime"
    },
    "anime_counterfeit": {
        "name": "Anime Classic",
        "description": "Classic anime style (SD 1.5)",
        "model": "counterfeit_v30.safetensors",
        "negative_prompt": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, username, blurry",
        "cfg_scale": 7.0,
        "steps": 28,
        "sampler": "euler_ancestral",
        "width": 512,
        "height": 768,
        "category": "anime"
    },
    "anime_dreamshaper": {
        "name": "Anime Fantasy",
        "description": "Fantasy anime style (SDXL)",
        "model": "dreamshaper_xl.safetensors",
        "negative_prompt": "bad quality, worst quality, low quality, blurry, distorted, deformed, ugly, bad anatomy, poorly drawn face, watermark, signature",
        "cfg_scale": 6.5,
        "steps": 20,
        "sampler": "dpmpp_2m",
        "width": 1024,
        "height": 1024,
        "category": "anime"
    },
    
    # === REALISTIC STYLES ===
    "realistic_xl": {
        "name": "Realistic XL",
        "description": "Photorealistic people (SDXL Lightning)",
        "model": "realvisxlV50_v50LightningBakedvae.safetensors",
        "negative_prompt": "cartoon, anime, illustration, drawing, painting, sketch, bad quality, worst quality, blurry, distorted, deformed, ugly, bad anatomy, bad proportions, watermark, signature",
        "cfg_scale": 2.0,
        "steps": 6,
        "sampler": "euler",
        "width": 1024,
        "height": 1024,
        "category": "realistic"
    },
    "realistic_juggernaut": {
        "name": "Realistic Pro",
        "description": "Professional photorealistic (SDXL)",
        "model": "juggernautXL_v9.safetensors",
        "negative_prompt": "cartoon, anime, illustration, drawing, painting, bad quality, worst quality, blurry, distorted, deformed, ugly, bad anatomy, extra limbs, missing limbs, watermark, signature, text",
        "cfg_scale": 4.5,
        "steps": 25,
        "sampler": "dpmpp_2m_sde",
        "width": 1024,
        "height": 1344,
        "category": "realistic"
    },
    "realistic_vision": {
        "name": "Realistic Vision",
        "description": "Portrait realistic (SD 1.5)",
        "model": "realisticVision_v60.safetensors",
        "negative_prompt": "(deformed iris, deformed pupils, semi-realistic, cgi, 3d, render, sketch, cartoon, drawing, anime:1.4), text, close up, cropped, out of frame, worst quality, low quality, jpeg artifacts, ugly, duplicate, morbid, mutilated, extra fingers, mutated hands, poorly drawn hands, poorly drawn face, mutation, deformed, blurry, dehydrated, bad anatomy, bad proportions, extra limbs, cloned face, disfigured, gross proportions, malformed limbs, missing arms, missing legs, extra arms, extra legs, fused fingers, too many fingers, long neck",
        "cfg_scale": 7.0,
        "steps": 28,
        "sampler": "dpmpp_sde",
        "width": 512,
        "height": 768,
        "category": "realistic"
    },
    
    # === VERSATILE STYLES ===
    "sdxl_base": {
        "name": "SDXL Base",
        "description": "Official Stability AI base model",
        "model": "sd_xl_base_1.0.safetensors",
        "negative_prompt": "bad quality, worst quality, low quality, blurry",
        "cfg_scale": 7.0,
        "steps": 30,
        "sampler": "euler",
        "width": 1024,
        "height": 1024,
        "category": "versatile"
    }
}

# Category descriptions
CATEGORIES = {
    "anime": {
        "name": "🎨 Anime",
        "description": "Anime & illustration styles",
        "icon": "🎨"
    },
    "realistic": {
        "name": "📷 Realistic",
        "description": "Photorealistic human portraits",
        "icon": "📷"
    },
    "versatile": {
        "name": "✨ Versatile",
        "description": "General purpose models",
        "icon": "✨"
    }
}

# Quick presets for UI buttons
QUICK_PRESETS = [
    {
        "id": "anime_xl",
        "name": "🎨 Anime XL",
        "description": "High quality anime"
    },
    {
        "id": "realistic_xl",
        "name": "📷 Realistic (Fast)",
        "description": "Photorealistic Lightning"
    },
    {
        "id": "realistic_juggernaut",
        "name": "📷 Realistic Pro",
        "description": "Professional photos"
    },
    {
        "id": "anime_counterfeit",
        "name": "🎨 Anime Classic",
        "description": "Classic anime style"
    }
]


def get_preset(preset_id: str) -> dict:
    """Get a preset by ID"""
    return MODEL_PRESETS.get(preset_id, MODEL_PRESETS.get("anime_xl"))


def get_presets_by_category(category: str) -> list:
    """Get all presets for a category"""
    return [
        {"id": k, **v} 
        for k, v in MODEL_PRESETS.items() 
        if v.get("category") == category
    ]


def get_all_presets() -> dict:
    """Get all presets grouped by category"""
    result = {}
    for cat_id, cat_info in CATEGORIES.items():
        result[cat_id] = {
            "info": cat_info,
            "presets": get_presets_by_category(cat_id)
        }
    return result
