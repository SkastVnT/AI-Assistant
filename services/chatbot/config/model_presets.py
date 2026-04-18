"""
Model Presets Configuration
Defines presets for different image generation styles,
LoRA combinations, and workflow recipes.
"""

# ─── LoRA Catalog ────────────────────────────────────────────────────────
# Each entry maps a short key to its filename and metadata.
# Paths are resolved by ComfyUI via extra_model_paths.yaml.

LORA_CATALOG = {
    # ── Character LoRAs (Honkai Star Rail) ───────────────────────────────
    "firefly":        {"file": "Firefly-1024-v1.safetensors",           "trigger": ["firefly"],           "category": "character", "base": "sdxl"},
    "kafka":          {"file": "kafka-v2-naivae-final-6ep.safetensors", "trigger": ["kafka"],             "category": "character", "base": "sdxl"},
    "jingliu":        {"file": "JingliuV4-09.safetensors",              "trigger": ["jingliu"],           "category": "character", "base": "sdxl"},
    "seele":          {"file": "Seele.safetensors",                     "trigger": ["seele"],             "category": "character", "base": "sd15"},
    "clara":          {"file": "Clara.safetensors",                     "trigger": ["clara"],             "category": "character", "base": "sd15"},
    "march7th":       {"file": "March 7th.safetensors",                 "trigger": ["march 7th"],         "category": "character", "base": "sd15"},
    "bronya":         {"file": "Bronya Rand.safetensors",               "trigger": ["bronya rand"],       "category": "character", "base": "sd15"},
    "trailblazer":    {"file": "TrailblazerHonkaiStarRail4.safetensors","trigger": ["trailblazer"],       "category": "character", "base": "sd15"},

    # ── Character LoRAs (Genshin Impact) ─────────────────────────────────
    "nahida":         {"file": "Nahida3.safetensors",                   "trigger": ["nahida"],            "category": "character", "base": "sd15"},
    "furina":         {"file": "furina-lora-nochekaiser.safetensors",   "trigger": ["furina"],            "category": "character", "base": "sdxl"},
    "eula":           {"file": "Eula-1.0.safetensors",                  "trigger": ["eula"],              "category": "character", "base": "sd15"},
    "raiden":         {"file": "raiden shogun_LoRA.safetensors",        "trigger": ["raiden shogun"],     "category": "character", "base": "sd15"},
    "yae_miko":       {"file": "yaemiko1.safetensors",                  "trigger": ["yae miko"],          "category": "character", "base": "sd15"},

    # ── Character LoRAs (Other) ──────────────────────────────────────────
    "tatsumaki":      {"file": "tatsumaki.safetensors",                 "trigger": ["tatsumaki"],         "category": "character", "base": "sd15"},
    "atri":           {"file": "atri.safetensors",                      "trigger": ["atri"],              "category": "character", "base": "sd15"},

    # ── Style LoRAs ──────────────────────────────────────────────────────
    "outline":        {"file": "SIC_outline_v1.01.safetensors",         "trigger": [],                    "category": "style",     "base": "sdxl"},
    "dilation_tape":  {"file": "dilationTapeLora-05.safetensors",       "trigger": [],                    "category": "style",     "base": "sd15"},

    # ── Anatomy / Quality LoRAs ──────────────────────────────────────────
    "detail_tweaker": {"file": "add_detail.safetensors",                "trigger": [],                    "category": "anatomy",   "base": "sd15"},

    # ── Custom trained ───────────────────────────────────────────────────
    "maki_custom":    {"file": "maki_lora.safetensors",                 "trigger": ["maki"],              "category": "character", "base": "sd15"},

    # ── NSFW LoRAs — Illustrious XL base (compatible with ChenkinNoob-XL) ──
    # These LoRAs are confirmed ILXL/Illustrious — use ChenkinNoob-XL-V0.2.safetensors
    "xray_ilxl":              {"file": "x-ray_ilxl_v1.safetensors",                                              "trigger": ["xray view", "x-ray view", "internal view", "see through body"],  "category": "nsfw", "base": "ilxl"},
    "speculum_ilxl":          {"file": "speculum_illustrious_V1.0.safetensors",                                   "trigger": ["speculum"],                                                       "category": "nsfw", "base": "ilxl"},
    "speculum_insertion_ilxl":{"file": "LoraILXL10_speculum_insertion_v1.safetensors",                            "trigger": ["speculum insertion"],                                             "category": "nsfw", "base": "ilxl"},
    "vibrator_clit_ilxl":     {"file": "LoraILXL10_vibrator_on_clitoris_v1.safetensors",                         "trigger": ["vibrator on clitoris"],                                           "category": "nsfw", "base": "ilxl"},
    "vibrator_panties_ilxl":  {"file": "vibrator-under-panties-illustriousxl-lora-nochekaiser.safetensors",       "trigger": ["vibrator under panties", "vibrator panties"],                    "category": "nsfw", "base": "ilxl"},
    "spread_anal_il":         {"file": "ExtremeSpreadPussyAnal_Anime_IL_V1.safetensors",                          "trigger": ["spread pussy", "extreme spread"],                                 "category": "nsfw", "base": "ilxl"},
    "ifl_il":                 {"file": "IFL_v1.0_IL.safetensors",                                                 "trigger": [],                                                                 "category": "nsfw", "base": "ilxl"},
    "cameltoe_ilxl":          {"file": "Cameltoe_THICK_-_Anime-000009.safetensors",                               "trigger": ["cameltoe", "camel toe"],                                          "category": "nsfw", "base": "ilxl"},
    "eyes_ilxl":              {"file": "Eyes_for_Illustrious_Lora_Perfect_anime_eyes.safetensors",                "trigger": [],                                                                 "category": "quality", "base": "ilxl"},

    # ── NSFW LoRAs — likely SDXL/anime base (ambiguous, attempt with ChenkinNoob) ──
    "xray_v2":                {"file": "xray2.5.safetensors",                                                     "trigger": [],                                                                 "category": "nsfw", "base": "sdxl"},
    "xray_window":            {"file": "Johns_X-Ray_Window_LORA.safetensors",                                     "trigger": ["x-ray window", "xray window"],                                    "category": "nsfw", "base": "sdxl"},
    "xray_creampie":          {"file": "X-ray_creampie_high.safetensors",                                         "trigger": ["xray creampie", "x-ray creampie"],                                "category": "nsfw", "base": "sdxl"},
    "xray_cum":               {"file": "X-ray_cum_inflation.safetensors",                                         "trigger": ["cum inflation", "xray inflation"],                                "category": "nsfw", "base": "sdxl"},
    "tape_gape":              {"file": "TapeGape-000037.safetensors",                                             "trigger": ["tape gape"],                                                      "category": "nsfw", "base": "sdxl"},
    "tape_spread":            {"file": "Tape_Spread-000023.safetensors",                                          "trigger": ["tape spread"],                                                    "category": "nsfw", "base": "sdxl"},
    "vibrator_thigh":         {"file": "vibrator_in_thighhighs.safetensors",                                      "trigger": ["vibrator thighhighs", "vibrator thigh highs"],                   "category": "nsfw", "base": "sdxl"},
    "vibrator_underwear":     {"file": "Vibrator in underwear and legs spread.safetensors",                       "trigger": ["vibrator in underwear"],                                          "category": "nsfw", "base": "sdxl"},
    "cervix":                 {"file": "cervix.safetensors",                                                      "trigger": ["cervix view", "cervix"],                                          "category": "nsfw", "base": "sdxl"},
    "armpit_hair":            {"file": "my_girls_armpit_hair_anime_style.safetensors",                            "trigger": ["armpit hair", "hairy armpit"],                                    "category": "nsfw", "base": "sdxl"},
    "expressive_h":           {"file": "Expressive_H-000001.safetensors",                                         "trigger": [],                                                                 "category": "nsfw", "base": "sdxl"},
    "dasv3":                  {"file": "DASV3.safetensors",                                                       "trigger": [],                                                                 "category": "nsfw", "base": "sdxl"},
}


# ─── Workflow Presets ────────────────────────────────────────────────────
# Pre-configured combos of checkpoint + LoRAs + settings.
# Users pick a preset_id and get optimized generation settings.

WORKFLOW_PRESETS = {
    # ── Local ComfyUI bulk LoRA (auto live list) ──────────────────────────
    "lora_bulk_auto_chat": {
        "name": "Local LoRA Bulk (Auto)",
        "description": "ComfyUI local preset for chat flow: auto-attach a batch of available LoRAs without manual filename selection.",
        "checkpoint": "animagine-xl-4.0-opt.safetensors",
        "default_loras": [],
        "use_live_loras": True,
        "live_lora_limit": 2,
        "live_lora_weight": 0.55,
        "live_lora_include_keywords": [
            "il", "ilxl", "illustrious", "xl", "xray", "x-ray", "eye", "speculum",
            "vibrator", "tape", "cervix", "cameltoe", "armpit", "uncensored", "das", "dskb",
        ],
        "live_lora_exclude_keywords": ["pony", "flux"],
        "negative_prompt": "worst quality, low quality, blurry, bad anatomy, watermark, text, signature",
        "cfg_scale": 6.0,
        "steps": 26,
        "sampler": "euler_ancestral",
        "width": 832,
        "height": 1216,
        "category": "anime",
        "hires_fix": False,
    },

    # ── NSFW Illustrious XL preset (ChenkinNoob + ILXL LoRAs) ───────────
    "anime_nsfw_ilxl": {
        "name": "NSFW Illustrious XL",
        "description": "NSFW anime generation using ChenkinNoob-XL (NoobAI/Illustrious base). "
                       "Compatible with ILXL LoRAs. Pass lora_models: [{name: 'xray_ilxl', weight: 0.8}] etc.",
        "checkpoint": "ChenkinNoob-XL-V0.2.safetensors",
        "default_loras": [],
        "negative_prompt": "worst quality, low quality, blurry, bad anatomy, bad hands, watermark, text, signature, "
                           "deformed, ugly, poorly drawn",
        "cfg_scale": 5.0,
        "steps": 28,
        "sampler": "euler_ancestral",
        "width": 832,
        "height": 1216,
        "category": "nsfw",
        "hires_fix": False,
    },

    # ── Anime character generation (SDXL) ────────────────────────────────
    "anime_character_xl": {
        "name": "Anime Character (XL)",
        "description": "Anime characters with SDXL — high quality, supports character LoRAs",
        "checkpoint": "animagine-xl-3.1.safetensors",
        "default_loras": [],
        "negative_prompt": "bad quality, worst quality, low quality, blurry, distorted, deformed, ugly, bad anatomy, bad hands, missing fingers, extra fingers, watermark, text, signature",
        "cfg_scale": 7.0,
        "steps": 25,
        "sampler": "euler_ancestral",
        "width": 1024,
        "height": 1024,
        "category": "anime",
        "hires_fix": False,
    },
    "anime_character_15": {
        "name": "Anime Character (Classic)",
        "description": "Anime characters with SD 1.5 — compatible with most character LoRAs",
        "checkpoint": "counterfeit_v30.safetensors",
        "default_loras": [],
        "negative_prompt": "lowres, bad anatomy, bad hands, text, error, missing fingers, extra digit, fewer digits, cropped, worst quality, low quality, normal quality, jpeg artifacts, signature, watermark, blurry",
        "cfg_scale": 7.0,
        "steps": 28,
        "sampler": "euler_ancestral",
        "width": 512,
        "height": 768,
        "category": "anime",
        "hires_fix": True,
        "hires_scale": 1.5,
        "hires_denoise": 0.45,
        "hires_steps": 15,
    },
    "anime_hsr_jingliu": {
        "name": "Jingliu (HSR)",
        "description": "Jingliu from Honkai Star Rail — optimized preset",
        "checkpoint": "animagine-xl-3.1.safetensors",
        "default_loras": [
            {"key": "jingliu", "weight": 0.85},
        ],
        "negative_prompt": "bad quality, worst quality, low quality, blurry, deformed, ugly, bad anatomy, watermark, text",
        "cfg_scale": 7.0,
        "steps": 28,
        "sampler": "euler_ancestral",
        "width": 1024,
        "height": 1024,
        "category": "anime",
        "hires_fix": False,
    },
    "anime_hsr_firefly": {
        "name": "Firefly (HSR)",
        "description": "Firefly from Honkai Star Rail — character preset",
        "checkpoint": "animagine-xl-3.1.safetensors",
        "default_loras": [
            {"key": "firefly", "weight": 0.85},
        ],
        "negative_prompt": "bad quality, worst quality, low quality, blurry, deformed, ugly, bad anatomy, watermark, text",
        "cfg_scale": 7.0,
        "steps": 28,
        "sampler": "euler_ancestral",
        "width": 1024,
        "height": 1024,
        "category": "anime",
        "hires_fix": False,
    },
    "anime_genshin_furina": {
        "name": "Furina (Genshin)",
        "description": "Furina from Genshin Impact — character preset",
        "checkpoint": "animagine-xl-3.1.safetensors",
        "default_loras": [
            {"key": "furina", "weight": 0.8},
        ],
        "negative_prompt": "bad quality, worst quality, low quality, blurry, deformed, ugly, bad anatomy, watermark, text",
        "cfg_scale": 7.0,
        "steps": 28,
        "sampler": "euler_ancestral",
        "width": 1024,
        "height": 1024,
        "category": "anime",
        "hires_fix": False,
    },

    # ── Realistic presets ────────────────────────────────────────────────
    "realistic_portrait": {
        "name": "Realistic Portrait",
        "description": "Photorealistic portraits — SDXL Lightning fast",
        "checkpoint": "realvisxlV50_v50LightningBakedvae.safetensors",
        "default_loras": [],
        "negative_prompt": "cartoon, anime, illustration, drawing, painting, sketch, bad quality, worst quality, blurry, distorted, deformed, ugly, bad anatomy, watermark, signature",
        "cfg_scale": 2.0,
        "steps": 6,
        "sampler": "euler",
        "width": 1024,
        "height": 1024,
        "category": "realistic",
        "hires_fix": False,
    },
    "realistic_pro": {
        "name": "Realistic Pro",
        "description": "Professional photorealistic — slower but higher quality",
        "checkpoint": "juggernautXL_v9.safetensors",
        "default_loras": [],
        "negative_prompt": "cartoon, anime, illustration, drawing, painting, bad quality, worst quality, blurry, distorted, deformed, ugly, bad anatomy, extra limbs, watermark, signature, text",
        "cfg_scale": 4.5,
        "steps": 25,
        "sampler": "dpmpp_2m_sde",
        "width": 1024,
        "height": 1344,
        "category": "realistic",
        "hires_fix": False,
    },

    # ── Fantasy / artistic ───────────────────────────────────────────────
    "fantasy_anime": {
        "name": "Fantasy Anime",
        "description": "Fantasy anime art — great for environments and characters",
        "checkpoint": "dreamshaper_xl.safetensors",
        "default_loras": [],
        "negative_prompt": "bad quality, worst quality, low quality, blurry, distorted, deformed, ugly, bad anatomy, watermark, signature",
        "cfg_scale": 6.5,
        "steps": 20,
        "sampler": "dpmpp_2m",
        "width": 1024,
        "height": 1024,
        "category": "anime",
        "hires_fix": False,
    },
}


def get_lora_by_key(key: str) -> dict | None:
    """Look up a LoRA entry from the catalog."""
    return LORA_CATALOG.get(key)


def resolve_loras_for_preset(preset_id: str) -> list[dict]:
    """
    Return resolved LoRA specs for a workflow preset.
    Each entry: {"file": "...", "weight": 0.8, "trigger": [...]}
    """
    preset = WORKFLOW_PRESETS.get(preset_id, {})
    result = []
    for lora_ref in preset.get("default_loras", []):
        key = lora_ref.get("key", "")
        weight = lora_ref.get("weight", 0.8)
        entry = LORA_CATALOG.get(key)
        if entry:
            result.append({
                "file": entry["file"],
                "weight": weight,
                "trigger": entry.get("trigger", []),
            })
    return result


def get_workflow_preset(preset_id: str) -> dict | None:
    """Get a workflow preset by ID."""
    return WORKFLOW_PRESETS.get(preset_id)


def get_workflow_presets_by_category(category: str) -> list[dict]:
    """Get all workflow presets for a category."""
    return [
        {"id": k, **v}
        for k, v in WORKFLOW_PRESETS.items()
        if v.get("category") == category
    ]


def get_all_workflow_presets() -> dict:
    """Get all workflow presets grouped by category."""
    cats = {}
    for pid, preset in WORKFLOW_PRESETS.items():
        cat = preset.get("category", "other")
        if cat not in cats:
            cats[cat] = []
        cats[cat].append({"id": pid, **preset})
    return cats


# ─── Legacy Model Presets (backward-compatible) ─────────────────────────
# These are used by the old UI and stable_diffusion.py routes.

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
        "name": "ðŸŽ¨ Anime",
        "description": "Anime & illustration styles",
        "icon": "ðŸŽ¨"
    },
    "realistic": {
        "name": "ðŸ“· Realistic",
        "description": "Photorealistic human portraits",
        "icon": "ðŸ“·"
    },
    "versatile": {
        "name": "âœ¨ Versatile",
        "description": "General purpose models",
        "icon": "âœ¨"
    }
}

# Quick presets for UI buttons
QUICK_PRESETS = [
    {
        "id": "anime_xl",
        "name": "ðŸŽ¨ Anime XL",
        "description": "High quality anime"
    },
    {
        "id": "realistic_xl",
        "name": "ðŸ“· Realistic (Fast)",
        "description": "Photorealistic Lightning"
    },
    {
        "id": "realistic_juggernaut",
        "name": "ðŸ“· Realistic Pro",
        "description": "Professional photos"
    },
    {
        "id": "anime_counterfeit",
        "name": "ðŸŽ¨ Anime Classic",
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
