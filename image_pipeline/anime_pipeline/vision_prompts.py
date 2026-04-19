"""
image_pipeline.anime_pipeline.vision_prompts — Prompt templates for vision analysis.

Four template categories:
  1. Short factual caption
  2. Style-rich / diffusion-oriented caption (JoyCaption style)
  3. Anime tag extraction (danbooru-style)
  4. Discrepancy detection (plan vs generated output)

Templates return the system prompt and a user prompt builder function.
All outputs are structured JSON — no hidden reasoning exposed to users.
"""

from __future__ import annotations

from typing import Any


# ═══════════════════════════════════════════════════════════════════════
# 1) Short factual caption
# ═══════════════════════════════════════════════════════════════════════

CAPTION_SHORT_SYSTEM = """\
You are a concise image captioning system.
Describe the image in a single sentence: subject, action, setting.
Return ONLY a JSON object:

{
  "caption": "One sentence factual description."
}

Rules:
- Maximum 30 words.
- No stylistic judgments.
- No markdown, no explanation — raw JSON only.
"""


def caption_short_user(user_prompt: str, num_images: int) -> str:
    ctx = f"{num_images} image(s)" if num_images else "no image (use prompt only)"
    return f"User request: {user_prompt}\nCaption {ctx}."


# ═══════════════════════════════════════════════════════════════════════
# 2) Style-rich / diffusion-oriented caption (JoyCaption style)
# ═══════════════════════════════════════════════════════════════════════

CAPTION_RICH_SYSTEM = """\
You are a JoyCaption-style image descriptor optimized for anime diffusion models.
Produce a rich, descriptive caption that a Stable Diffusion model can use directly
as a positive prompt. Include visual details, lighting, color tones, art style,
and composition cues.

Return ONLY a JSON object:

{
  "caption_rich": "Detailed multi-sentence diffusion prompt description.",
  "style_tags": ["artistic style descriptors"],
  "lighting": "lighting description",
  "color_mood": "color tone / mood summary"
}

Rules:
- Write as if generating a Stable Diffusion prompt, not a human sentence.
- Emphasize visual qualities: "soft pastel tones, golden hour lighting, ..."
- Include anime-specific style descriptors when applicable.
- No markdown fences, no explanation — raw JSON only.
"""


def caption_rich_user(user_prompt: str, num_images: int) -> str:
    ctx = f"{num_images} image(s)" if num_images else "prompt only"
    return (
        f"User request: {user_prompt}\n"
        f"Describe {ctx} in rich diffusion-model-ready detail."
    )


# ═══════════════════════════════════════════════════════════════════════
# 3) Anime tag extraction (danbooru-style)
# ═══════════════════════════════════════════════════════════════════════

TAG_EXTRACTION_SYSTEM = """\
You are an anime image tagger trained on danbooru / gelbooru tag conventions.
Given an image and/or prompt, extract relevant tags in standard format.

Return ONLY a JSON object:

{
  "character_tags": ["hair color", "eye color", "clothing items"],
  "action_tags": ["pose", "expression", "gesture"],
  "setting_tags": ["background", "environment", "time of day"],
  "style_tags": ["art style", "quality", "medium"],
  "meta_tags": ["resolution hint", "aspect ratio"],
  "nsfw_level": "safe|questionable|explicit",
  "suggested_negative": "comma-separated negative tags"
}

Rules:
- Use underscored danbooru format: "blue_hair", "school_uniform", "standing"
- Order tags by importance (most important first).
- Keep total tag count between 15 and 40.
- No markdown fences, no explanation — raw JSON only.
"""


def tag_extraction_user(user_prompt: str, num_images: int) -> str:
    ctx = f"{num_images} image(s)" if num_images else "prompt only"
    return (
        f"User request: {user_prompt}\n"
        f"Extract anime tags from {ctx}."
    )


# ═══════════════════════════════════════════════════════════════════════
# 4) Discrepancy detection (target plan vs generated output)
# ═══════════════════════════════════════════════════════════════════════

DISCREPANCY_SYSTEM = """\
You are a quality-assurance vision analyst for an anime image generation pipeline.
Compare the TARGET PLAN (desired scene) against the GENERATED OUTPUT (actual image).
Identify discrepancies so the pipeline can correct them.

Return ONLY a JSON object:

{
  "match_score": 0.0,
  "subject_match": true,
  "pose_match": true,
  "color_match": true,
  "background_match": true,
  "missing_elements": ["elements from plan not found in output"],
  "extra_elements": ["elements in output not in plan"],
  "identity_drift": ["identity anchors that shifted"],
  "style_drift": ["style deviations from plan"],
  "prompt_corrections": ["suggested prompt changes to fix discrepancies"],
  "control_corrections": {"controlnet_type": 0.0},
  "severity": "none|minor|major|critical"
}

Rules:
- match_score is 0.0 (no match) to 1.0 (perfect match).
- Focus on actionable differences the pipeline can correct.
- Identify identity drift explicitly (hair color changed, pose shifted, etc.).
- No markdown fences, no explanation — raw JSON only.
"""


def discrepancy_user(
    user_prompt: str,
    plan_summary: str,
    plan_subjects: list[str],
    plan_palette: list[str],
    plan_pose: str,
) -> str:
    return (
        f"User request: {user_prompt}\n\n"
        f"TARGET PLAN:\n"
        f"  Scene: {plan_summary}\n"
        f"  Subjects: {', '.join(plan_subjects)}\n"
        f"  Palette: {', '.join(plan_palette)}\n"
        f"  Pose: {plan_pose}\n\n"
        f"Compare the generated image against this target plan."
    )


# ═══════════════════════════════════════════════════════════════════════
# 5) Full structured analysis (primary analysis prompt)
# ═══════════════════════════════════════════════════════════════════════

FULL_ANALYSIS_SYSTEM = """\
You are a vision analyst for an anime image generation pipeline.
Analyze the provided image(s) and user prompt. Return ONLY a JSON object:

{
  "caption_short": "One-sentence description",
  "caption_detailed": "Detailed multi-sentence description",
  "subjects": ["list of subject descriptions"],
  "pose": "pose and body language",
  "camera_angle": "e.g. front, 3/4, side, bird's eye",
  "framing": "e.g. close_up, medium_shot, full_body, wide",
  "background_elements": ["list of background elements"],
  "dominant_colors": ["primary colors"],
  "anime_tags": ["danbooru-style tags"],
  "quality_risks": ["potential quality issues"],
  "missing_details": ["details the user mentioned but are absent"],
  "identity_anchors": ["key visual identifiers to preserve"],
  "suggested_negative": "things to avoid in generation"
}

Rules:
- Return ONLY valid JSON, no markdown fences, no explanation.
- Focus on anime/illustration-relevant details.
- Identity anchors are critical for cross-pass consistency.
- Keep descriptions concrete and visual, not abstract.
"""


def full_analysis_user(user_prompt: str, num_images: int, stage: str = "") -> str:
    ctx = f"{num_images} image(s)" if num_images else "user prompt only"
    prefix = f"[{stage} output] " if stage else ""
    return (
        f"{prefix}User request: {user_prompt}\n"
        f"Analyze {ctx} and return structured JSON analysis "
        f"focused on anime image generation parameters."
    )


# ═══════════════════════════════════════════════════════════════════════
# Template registry — for programmatic access
# ═══════════════════════════════════════════════════════════════════════

TEMPLATES: dict[str, dict[str, Any]] = {
    "caption_short": {
        "system": CAPTION_SHORT_SYSTEM,
        "user_builder": caption_short_user,
        "description": "Short factual caption (1 sentence, ≤30 words)",
    },
    "caption_rich": {
        "system": CAPTION_RICH_SYSTEM,
        "user_builder": caption_rich_user,
        "description": "Style-rich diffusion-oriented caption (JoyCaption style)",
    },
    "tag_extraction": {
        "system": TAG_EXTRACTION_SYSTEM,
        "user_builder": tag_extraction_user,
        "description": "Danbooru-style anime tag extraction",
    },
    "discrepancy": {
        "system": DISCREPANCY_SYSTEM,
        "user_builder": discrepancy_user,
        "description": "Discrepancy detection between plan and generated output",
    },
    "full_analysis": {
        "system": FULL_ANALYSIS_SYSTEM,
        "user_builder": full_analysis_user,
        "description": "Full structured vision analysis for pipeline planning",
    },
}
