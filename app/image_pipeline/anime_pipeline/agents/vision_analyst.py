"""
VisionAnalystAgent — Stage 1: Analyze input/reference images with vision AI.

Returns structured VisionAnalysis JSON. No hidden reasoning text.
Uses Gemini 2.0 Flash (primary) → GPT-4o-mini → GPT-4o fallback chain.
"""

from __future__ import annotations

import base64
import json
import logging
import os
import re
import time
from typing import Optional

from ..config import AnimePipelineConfig
from ..schemas import AnimePipelineJob, AnimePipelineStatus, VisionAnalysis
from ..runtime_policy import RuntimePolicy

logger = logging.getLogger(__name__)

# Vision analysis system prompt — returns structured JSON only
_VISION_SYSTEM_PROMPT = """\
You are a vision analyst for an anime image generation pipeline.
Analyze the provided image(s) and user prompt. Return ONLY a JSON object with these fields:

{
  "caption_short": "One-sentence description",
  "caption_detailed": "Detailed multi-sentence description",
  "subject_description": "Main subject appearance details",
  "pose_description": "Pose and body language",
  "clothing_description": "Clothing and accessories",
  "background_description": "Background and environment",
  "art_style": "anime|realistic|digital_art|watercolor|sketch",
  "color_palette": ["primary colors as list"],
  "composition_notes": "Framing, perspective, focal point",
  "identity_anchors": ["key visual identifiers to preserve"],
  "missing_details": ["details the user prompt mentions but image lacks"],
  "suggested_negative": "things to avoid in generation",
  "layer_analysis": {
    "eyes": {"color": "exact eye color(s)", "shape": "shape description", "special": "heterochromia/pattern/glow"},
    "hair": {"color": "exact color", "length": "short/medium/long/very_long", "style": "twintails/ponytail/straight/etc", "accessories": "ribbons/clips/etc"},
    "face": {"shape": "round/oval/heart/etc", "expression": "smile/neutral/serious", "markings": "any marks/scars/tattoos"},
    "outfit": {"description": "detailed outfit", "colors": ["primary colors"], "style": "gothic_lolita/school_uniform/etc"},
    "accessories": ["list of accessories, weapons, items"],
    "body": {"type": "slim/petite/athletic/curvy", "skin_tone": "fair/medium/dark", "notable": "any notable body features"}
  }
}

Rules:
- Return ONLY valid JSON, no markdown, no explanation
- Focus on anime/illustration-relevant details
- Identity anchors are critical for consistency across passes
- Keep descriptions concrete and visual, not abstract
- The layer_analysis is CRITICAL for character identity - be extremely precise about eye colors, hair details, and outfit specifics
- For heterochromia characters, specify EACH eye's color and which side (left/right)
"""

_USER_PROMPT_TEMPLATE = """\
User request: {user_prompt}

Analyze the {image_context} and return structured JSON analysis \
focused on anime image generation parameters.
"""

_PROMPT_TRANSLATION_TEMPLATE = """\
Convert the following image generation request into English danbooru-style tags.
Return ONLY a JSON object with TWO arrays:
{{
  "character_tags": ["character_name_tag", "series_tag", "identity_tags..."],
  "scene_tags": ["background", "setting", "pose", "action", "atmosphere", "lighting"]
}}

Rules:
- "character_tags": If a specific anime character is mentioned, include their danbooru tag + series tag + core identity (hair color, eye color, outfit). Max 6 tags.
- "scene_tags": MUST include ALL background, setting, pose, action, weather, time-of-day, and atmosphere details from the request. These are CRITICAL — never omit scenery the user described. Min 4, max 12 tags.
- Use underscored danbooru format: "blue_sky", "flower_field", "looking_up".
- NEVER drop scene/background details. If the user says "on a flower highland under blue sky", the scene_tags MUST include "flower_field", "blue_sky", "highland", "scenery".

Request: {user_prompt}

Example (character + scene): {{
  "character_tags": ["tokisaki_kurumi", "date_a_live", "1girl", "twintails", "heterochromia"],
  "scene_tags": ["flower_field", "blue_sky", "looking_up", "highland", "scenery", "sunlight", "wind", "vibrant_colors"]
}}
Example (no character): {{
  "character_tags": [],
  "scene_tags": ["1girl", "white_sweater", "winter", "snowflakes", "warm_lighting", "cozy", "outdoors", "soft_smile"]
}}
"""

# ── Known anime character → danbooru appearance tags ─────────────────
# Key: lowercase search alias(es), Value: (danbooru_tag, series_tag, appearance_tags[])
# appearance_tags are prepended to the prompt so the model knows the look.
_KNOWN_CHARACTERS: dict[str, tuple[str, str, list[str]]] = {
    # Date a Live
    "kurumi": (
        "tokisaki_kurumi",
        "date_a_live",
        [
            "1girl",
            "black_hair",
            "very_long_hair",
            "twintails",
            "heterochromia",
            "(yellow_left_eye:1.2)",
            "(red_right_eye:1.2)",
            "gothic_lolita",
        ],
    ),
    "tokisaki kurumi": (
        "tokisaki_kurumi",
        "date_a_live",
        [
            "1girl",
            "black_hair",
            "very_long_hair",
            "twintails",
            "heterochromia",
            "(yellow_left_eye:1.2)",
            "(red_right_eye:1.2)",
            "gothic_lolita",
        ],
    ),
    "tohka": (
        "yatogami_tohka",
        "date_a_live",
        [
            "1girl",
            "long_hair",
            "purple_hair",
            "dark_blue_hair",
            "blue_eyes",
            "princess_dress",
            "white_dress",
        ],
    ),
    "kotori": (
        "itsuka_kotori",
        "date_a_live",
        [
            "1girl",
            "long_hair",
            "pink_hair",
            "red_eyes",
            "uniform",
            "commander",
        ],
    ),
    # Sword Art Online
    "asuna": (
        "yuuki_asuna",
        "sword_art_online",
        [
            "1girl",
            "long_hair",
            "orange_hair",
            "brown_eyes",
            "armor",
            "white_uniform",
            "knight",
        ],
    ),
    "kirito": (
        "kirigaya_kazuto",
        "sword_art_online",
        [
            "1boy",
            "short_black_hair",
            "black_eyes",
            "black_coat",
            "dual_blades",
        ],
    ),
    # Re:Zero
    "rem": (
        "rem_(re:zero)",
        "re:zero",
        [
            "1girl",
            "short_hair",
            "blue_hair",
            "blue_eyes",
            "maid",
            "maid_headdress",
            "maid_uniform",
        ],
    ),
    "emilia": (
        "emilia_(re:zero)",
        "re:zero",
        [
            "1girl",
            "long_hair",
            "silver_hair",
            "purple_eyes",
            "elf_ears",
            "white_dress",
        ],
    ),
    # Demon Slayer
    "nezuko": (
        "kamado_nezuko",
        "kimetsu_no_yaiba",
        [
            "1girl",
            "long_hair",
            "black_hair",
            "pink_gradient_hair",
            "pink_eyes",
            "bamboo_muzzle",
            "kimono",
            "pink_kimono",
        ],
    ),
    "tanjiro": (
        "kamado_tanjiro",
        "kimetsu_no_yaiba",
        [
            "1boy",
            "short_hair",
            "black_hair",
            "red_eyes",
            "scar",
            "checkered_haori",
            "nichirin_sword",
        ],
    ),
    # Honkai: Star Rail / Genshin
    "hu tao": (
        "hu_tao_(genshin_impact)",
        "genshin_impact",
        [
            "1girl",
            "long_hair",
            "brown_hair",
            "twintails",
            "(red_eyes:1.2)",
            "flower_hair_ornament",
            "hair_ribbon",
            "chinese_clothes",
            "dark_red_jacket",
            "black_gloves",
            "white_floral_pattern",
        ],
    ),
    "hutao": (
        "hu_tao_(genshin_impact)",
        "genshin_impact",
        [
            "1girl",
            "long_hair",
            "brown_hair",
            "twintails",
            "(red_eyes:1.2)",
            "flower_hair_ornament",
            "hair_ribbon",
            "chinese_clothes",
            "dark_red_jacket",
            "black_gloves",
            "white_floral_pattern",
        ],
    ),
    "raiden shogun": (
        "raiden_shogun",
        "genshin_impact",
        [
            "1girl",
            "long_hair",
            "purple_hair",
            "(purple_eyes:1.2)",
            "kimono",
            "elegant",
        ],
    ),
    "fischl": (
        "fischl_(genshin_impact)",
        "genshin_impact",
        [
            "1girl",
            "long_hair",
            "blonde_hair",
            "heterochromia",
            "eyepatch",
            "thighhighs",
            "gothic",
        ],
    ),
    # Fate series
    "saber": (
        "artoria_pendragon",
        "fate/stay_night",
        [
            "1girl",
            "short_hair",
            "blonde_hair",
            "green_eyes",
            "armor",
            "blue_dress",
            "ahoge",
        ],
    ),
    "rin": (
        "tohsaka_rin",
        "fate/stay_night",
        [
            "1girl",
            "long_hair",
            "black_hair",
            "twintails",
            "red_eyes",
            "red_turtleneck",
            "skirt",
        ],
    ),
    # Naruto
    "hinata": (
        "hyuuga_hinata",
        "naruto",
        [
            "1girl",
            "short_hair",
            "dark_blue_hair",
            "white_eyes",
            "byakugan",
            "ninja",
            "lavender_hoodie",
        ],
    ),
    # Attack on Titan
    "mikasa": (
        "mikasa_ackerman",
        "shingeki_no_kyojin",
        [
            "1girl",
            "short_hair",
            "black_hair",
            "gray_eyes",
            "scarf",
            "red_scarf",
            "military_uniform",
        ],
    ),
    # Hololive
    "fubuki": (
        "shirakami_fubuki",
        "hololive",
        [
            "1girl",
            "long_hair",
            "white_hair",
            "blue_eyes",
            "fox_ears",
            "fox_tail",
            "virtual_youtuber",
        ],
    ),
    # Zenless Zone Zero
    "ellen": (
        "ellen_joe",
        "zenless_zone_zero",
        [
            "1girl",
            "long_hair",
            "silver_hair",
            "blue_eyes",
            "shark_tail",
            "school_uniform",
        ],
    ),
    "ellen joe": (
        "ellen_joe",
        "zenless_zone_zero",
        [
            "1girl",
            "long_hair",
            "silver_hair",
            "blue_eyes",
            "shark_tail",
            "school_uniform",
        ],
    ),
    "miyabi": (
        "miyabi_(zenless_zone_zero)",
        "zenless_zone_zero",
        [
            "1girl",
            "long_hair",
            "pink_hair",
            "red_eyes",
            "japanese_clothes",
            "kimono",
        ],
    ),
    "anby": (
        "anby_demara",
        "zenless_zone_zero",
        [
            "1girl",
            "short_hair",
            "purple_hair",
            "yellow_eyes",
            "jacket",
            "combat_outfit",
        ],
    ),
    "nicole demara": (
        "nicole_demara",
        "zenless_zone_zero",
        [
            "1girl",
            "long_hair",
            "blonde_hair",
            "green_eyes",
            "business_suit",
            "hat",
        ],
    ),
    "jane doe": (
        "jane_doe_(zenless_zone_zero)",
        "zenless_zone_zero",
        [
            "1girl",
            "medium_hair",
            "red_hair",
            "red_eyes",
            "combat_outfit",
            "mask",
        ],
    ),
    "zhu yuan": (
        "zhu_yuan",
        "zenless_zone_zero",
        [
            "1girl",
            "long_hair",
            "white_hair",
            "yellow_eyes",
            "police_uniform",
            "gloves",
        ],
    ),
    # NIKKE
    "rapi": (
        "rapi_(nikke)",
        "goddess_of_victory:_nikke",
        [
            "1girl",
            "long_hair",
            "blonde_hair",
            "red_eyes",
            "military_uniform",
            "beret",
        ],
    ),
    # To Love-Ru
    "lala": (
        "lala_satalin_deviluke",
        "to_love-ru",
        [
            "1girl",
            "long_hair",
            "pink_hair",
            "green_eyes",
            "tail",
            "hair_ornament",
        ],
    ),
    "yami": (
        "konjiki_no_yami",
        "to_love-ru",
        [
            "1girl",
            "long_hair",
            "blonde_hair",
            "red_eyes",
            "black_dress",
            "emotionless",
        ],
    ),
    # Oshi no Ko
    "ai hoshino": (
        "hoshino_ai",
        "oshi_no_ko",
        [
            "1girl",
            "long_hair",
            "purple_hair",
            "star_eyes",
            "idol",
            "star_hair_ornament",
        ],
    ),
    "ruby hoshino": (
        "hoshino_ruby",
        "oshi_no_ko",
        [
            "1girl",
            "long_hair",
            "blonde_hair",
            "star_eyes",
            "idol",
        ],
    ),
    # Fire Emblem
    "edelgard": (
        "edelgard_von_hresvelg",
        "fire_emblem",
        [
            "1girl",
            "long_hair",
            "white_hair",
            "purple_eyes",
            "armor",
            "cape",
            "crown",
        ],
    ),
    "camilla": (
        "camilla_(fire_emblem)",
        "fire_emblem",
        [
            "1girl",
            "very_long_hair",
            "purple_hair",
            "purple_eyes",
            "armor",
            "tiara",
        ],
    ),
    # KanColle
    "shimakaze": (
        "shimakaze_(kancolle)",
        "kantai_collection",
        [
            "1girl",
            "long_hair",
            "blonde_hair",
            "blue_eyes",
            "thighhighs",
            "sailor_collar",
            "miniskirt",
        ],
    ),
    # Touhou
    "reimu": (
        "hakurei_reimu",
        "touhou",
        [
            "1girl",
            "long_hair",
            "black_hair",
            "brown_eyes",
            "red_hakama",
            "detached_sleeves",
            "hair_ribbon",
            "bow",
        ],
    ),
    "marisa": (
        "kirisame_marisa",
        "touhou",
        [
            "1girl",
            "long_hair",
            "blonde_hair",
            "yellow_eyes",
            "witch_hat",
            "apron",
            "braid",
        ],
    ),
    "remilia": (
        "remilia_scarlet",
        "touhou",
        [
            "1girl",
            "short_hair",
            "blue_hair",
            "red_eyes",
            "wings",
            "bat_wings",
            "mob_cap",
            "pink_dress",
        ],
    ),
    "flandre": (
        "flandre_scarlet",
        "touhou",
        [
            "1girl",
            "blonde_hair",
            "red_eyes",
            "side_ponytail",
            "wings",
            "crystal_wings",
            "mob_cap",
            "red_dress",
        ],
    ),
    "sakuya": (
        "izayoi_sakuya",
        "touhou",
        [
            "1girl",
            "short_hair",
            "silver_hair",
            "blue_eyes",
            "maid",
            "maid_headdress",
            "knives",
        ],
    ),
    # Fate/Grand Order
    "ishtar": (
        "ishtar_(fate)",
        "fate/grand_order",
        [
            "1girl",
            "long_hair",
            "black_hair",
            "red_eyes",
            "two-side_up",
            "tiara",
            "red_outfit",
        ],
    ),
    "ereshkigal": (
        "ereshkigal_(fate)",
        "fate/grand_order",
        [
            "1girl",
            "long_hair",
            "blonde_hair",
            "red_eyes",
            "tiara",
            "cage",
            "red_outfit",
        ],
    ),
}


class VisionAnalystAgent:
    """Analyzes input/reference images with vision AI models."""

    def __init__(self, config: AnimePipelineConfig):
        self._config = config
        self._policy = RuntimePolicy.from_config(config)

    def execute(self, job: AnimePipelineJob) -> AnimePipelineJob:
        """Run vision analysis on reference/source images."""
        job.status = AnimePipelineStatus.VISION_ANALYZING
        t0 = time.time()

        # Determine what images to analyze
        images_b64 = self._gather_images(job)

        if not images_b64 and not job.user_prompt:
            logger.warning("[VisionAnalyst] No images or prompt to analyze")
            job.vision_analysis = VisionAnalysis(
                caption_short=job.user_prompt or "No input provided",
                confidence=0.0,
            )
            job.mark_stage("vision_analysis", 0.0)
            return job

        # Skip vision API when there are no reference images — calling the
        # vision LLM with only text causes hallucinated tags (wrong outfits,
        # backgrounds etc.) that overwrite the user's actual prompt.
        if not images_b64:
            logger.info(
                "[VisionAnalyst] No reference images — skipping vision API, using prompt-only analysis"
            )
            analysis = self._prompt_only_analysis(job.user_prompt)
        else:
            # Try each vision model in priority order
            analysis = None
            for model_name in self._config.vision_model_priority:
                if not self._policy.allows_provider(
                    model_name, purpose="local_vision_analysis"
                ):
                    logger.debug(
                        "[VisionAnalyst] Provider blocked by runtime policy: %s",
                        model_name,
                    )
                    continue
                try:
                    analysis = self._analyze_with_model(
                        model_name, job.user_prompt, images_b64, job.language
                    )
                    if analysis:
                        analysis.model_used = model_name
                        break
                except Exception as e:
                    logger.warning(
                        "[VisionAnalyst] %s failed: %s, trying next", model_name, e
                    )

            if not analysis:
                logger.warning(
                    "[VisionAnalyst] All models failed, using prompt-only analysis"
                )
                analysis = self._prompt_only_analysis(job.user_prompt)

        latency = (time.time() - t0) * 1000
        analysis.latency_ms = latency
        job.vision_analysis = analysis
        job.mark_stage("vision_analysis", latency)

        logger.info(
            "[VisionAnalyst] Done in %.0fms via %s (confidence=%.2f)",
            latency,
            analysis.model_used,
            analysis.confidence,
        )
        return job

    def _gather_images(self, job: AnimePipelineJob) -> list[str]:
        """Collect all available images as base64 strings."""
        images = []
        if job.source_image_b64:
            images.append(job.source_image_b64)
        images.extend(job.reference_images_b64)
        return images[:4]  # Cap at 4 images for API limits

    def _analyze_with_model(
        self,
        model_name: str,
        user_prompt: str,
        images_b64: list[str],
        language: str,
    ) -> Optional[VisionAnalysis]:
        """Dispatch to the appropriate vision API.

        2026-04-29: Grok and StepFun added (NSFW-friendly, OpenAI-compat
        chat-completions schema) so the priority list in vision_service
        config is honoured end-to-end. Without these branches the agent
        silently fell through to Gemini/GPT, defeating the NSFW chain.
        """
        name = model_name.lower()
        if name.startswith("local"):
            return self._analyze_openai_compat(
                self._config.local_vlm_model or model_name,
                user_prompt,
                images_b64,
                language,
                base_url=f"{self._config.local_vlm_url.rstrip('/')}/chat/completions",
                api_key=os.getenv("ANIME_PIPELINE_LOCAL_VLM_API_KEY", "local"),
                key_label="ANIME_PIPELINE_LOCAL_VLM_API_KEY",
            )
        if name.startswith("gemini"):
            return self._analyze_gemini(model_name, user_prompt, images_b64, language)
        if name.startswith("gpt"):
            return self._analyze_openai(model_name, user_prompt, images_b64, language)
        if name.startswith("grok"):
            return self._analyze_openai_compat(
                model_name,
                user_prompt,
                images_b64,
                language,
                base_url="https://api.x.ai/v1/chat/completions",
                api_key=os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY"),
                key_label="GROK_API_KEY",
            )
        if name.startswith("step-") or name.startswith("stepfun"):
            return self._analyze_openai_compat(
                model_name,
                user_prompt,
                images_b64,
                language,
                base_url="https://api.stepfun.com/v1/chat/completions",
                api_key=os.getenv("STEPFUN_API_KEY"),
                key_label="STEPFUN_API_KEY",
            )
        logger.warning("[VisionAnalyst] Unknown model: %s", model_name)
        return None

    def _analyze_gemini(
        self,
        model_name: str,
        user_prompt: str,
        images_b64: list[str],
        language: str,
    ) -> Optional[VisionAnalysis]:
        """Analyze using Google Gemini vision API."""
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError("No GEMINI_API_KEY set")

        import httpx

        image_context = (
            f"{len(images_b64)} reference image(s)"
            if images_b64
            else "user prompt (no images)"
        )
        user_msg = _USER_PROMPT_TEMPLATE.format(
            user_prompt=user_prompt, image_context=image_context
        )

        # Build parts
        parts = [{"text": _VISION_SYSTEM_PROMPT + "\n\n" + user_msg}]
        for img_b64 in images_b64:
            # Strip data URI prefix if present
            raw = img_b64.split(",", 1)[-1] if "," in img_b64 else img_b64
            parts.append(
                {
                    "inline_data": {
                        "mime_type": "image/png",
                        "data": raw,
                    }
                }
            )

        api_model = (
            model_name.replace(".", "-") if "." not in model_name else model_name
        )
        # Map friendly names to API model names
        model_map = {
            "gemini-2.0-flash": "gemini-2.0-flash",
            "gemini-2-0-flash": "gemini-2.0-flash",
        }
        api_model = model_map.get(model_name, model_name)

        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{api_model}:generateContent"
        )

        payload = {
            "contents": [{"parts": parts}],
            "generationConfig": {
                "temperature": self._config.vision_temperature,
                "maxOutputTokens": self._config.vision_max_tokens,
                "responseMimeType": "application/json",
            },
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers={"X-goog-api-key": api_key}, json=payload)
            resp.raise_for_status()

        data = resp.json()
        text = (
            data.get("candidates", [{}])[0]
            .get("content", {})
            .get("parts", [{}])[0]
            .get("text", "{}")
        )
        return self._parse_analysis(text)

    def _analyze_openai(
        self,
        model_name: str,
        user_prompt: str,
        images_b64: list[str],
        language: str,
    ) -> Optional[VisionAnalysis]:
        """Analyze using OpenAI vision API."""
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("No OPENAI_API_KEY set")

        import httpx

        image_context = (
            f"{len(images_b64)} reference image(s)"
            if images_b64
            else "user prompt (no images)"
        )
        user_msg = _USER_PROMPT_TEMPLATE.format(
            user_prompt=user_prompt, image_context=image_context
        )

        messages_content: list[dict] = [{"type": "text", "text": user_msg}]
        for img_b64 in images_b64:
            raw = img_b64.split(",", 1)[-1] if "," in img_b64 else img_b64
            messages_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{raw}",
                        "detail": "low",
                    },
                }
            )

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": _VISION_SYSTEM_PROMPT},
                {"role": "user", "content": messages_content},
            ],
            "max_tokens": self._config.vision_max_tokens,
            "temperature": self._config.vision_temperature,
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()

        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return self._parse_analysis(text)

    def _analyze_openai_compat(
        self,
        model_name: str,
        user_prompt: str,
        images_b64: list[str],
        language: str,
        *,
        base_url: str,
        api_key: Optional[str],
        key_label: str,
    ) -> Optional[VisionAnalysis]:
        """Analyze using any OpenAI-compatible chat-completions endpoint.

        Used by Grok (api.x.ai) and StepFun (api.stepfun.com) which both
        speak the same JSON schema as OpenAI but live on different hosts
        and have NSFW-friendlier moderation. Mirrors :meth:`_analyze_openai`
        with a configurable URL + API key source so the NSFW priority chain
        in vision_service config is honoured end-to-end.
        """
        if not api_key:
            raise RuntimeError(f"No {key_label} set")
        self._policy.assert_url(base_url, purpose="local_vision_analysis")

        import httpx

        image_context = (
            f"{len(images_b64)} reference image(s)"
            if images_b64
            else "user prompt (no images)"
        )
        user_msg = _USER_PROMPT_TEMPLATE.format(
            user_prompt=user_prompt, image_context=image_context
        )

        messages_content: list[dict] = [{"type": "text", "text": user_msg}]
        for img_b64 in images_b64:
            raw = img_b64.split(",", 1)[-1] if "," in img_b64 else img_b64
            messages_content.append(
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{raw}",
                        "detail": "low",
                    },
                }
            )

        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": _VISION_SYSTEM_PROMPT},
                {"role": "user", "content": messages_content},
            ],
            "max_tokens": self._config.vision_max_tokens,
            "temperature": self._config.vision_temperature,
            "response_format": {"type": "json_object"},
        }

        with httpx.Client(timeout=30) as client:
            resp = client.post(
                base_url,
                json=payload,
                headers={"Authorization": f"Bearer {api_key}"},
            )
            resp.raise_for_status()

        data = resp.json()
        text = data["choices"][0]["message"]["content"]
        return self._parse_analysis(text)

    def _parse_analysis(self, raw_text: str) -> Optional[VisionAnalysis]:
        """Parse JSON response into VisionAnalysis."""
        try:
            # Clean up potential markdown code fences
            text = raw_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[-1]
            if text.endswith("```"):
                text = text.rsplit("```", 1)[0]
            text = text.strip()

            obj = json.loads(text)
            # Map old field names to new schema fields for backward compat
            subjects = obj.get("subjects", [])
            if not subjects and obj.get("subject_description"):
                subjects = [obj["subject_description"]]

            bg_elements = obj.get("background_elements", [])
            if not bg_elements and obj.get("background_description"):
                bg_elements = [obj["background_description"]]

            return VisionAnalysis(
                caption_short=obj.get("caption_short", ""),
                caption_detailed=obj.get("caption_detailed", ""),
                subjects=subjects,
                pose=obj.get("pose", obj.get("pose_description", "")),
                camera_angle=obj.get("camera_angle", ""),
                framing=obj.get("framing", ""),
                background_elements=bg_elements,
                dominant_colors=obj.get(
                    "dominant_colors", obj.get("color_palette", [])
                ),
                anime_tags=obj.get("anime_tags", []),
                quality_risks=obj.get("quality_risks", []),
                identity_anchors=obj.get("identity_anchors", []),
                missing_details=obj.get("missing_details", []),
                suggested_negative=obj.get("suggested_negative", ""),
                layer_analysis=obj.get("layer_analysis", {}),
                confidence=0.85,
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("[VisionAnalyst] Failed to parse response: %s", e)
            return None

    def _resolve_character_tags(self, user_prompt: str) -> list[str]:
        """Detect known anime character names in the prompt and return their danbooru tags.

        Handles patterns like:
          - "Kurumi trong anime: Date a live"
          - "vẽ Rem từ Re:Zero"
          - "draw Asuna from SAO"
        Returns character_tag + series_tag + appearance_tags, or [] if no match.

        Matching uses word boundaries so short aliases like "rem", "rin",
        "saber" don't match inside unrelated words (e.g. "extreme",
        "drinking", "scabbard"). Aliases are checked longest-first so
        multi-word aliases win over single-word prefixes.
        """
        lower = user_prompt.lower()
        # Longest alias first so "tokisaki kurumi" wins over "kurumi",
        # "ellen joe" wins over "ellen", etc.
        for alias in sorted(_KNOWN_CHARACTERS.keys(), key=len, reverse=True):
            # Build a word-boundary regex. re.escape handles colons/spaces in
            # aliases. \b works with ASCII aliases and the surrounding
            # Vietnamese/Japanese/English text we support here.
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, lower):
                char_tag, series_tag, appearance = _KNOWN_CHARACTERS[alias]
                tags = [char_tag, series_tag] + appearance
                logger.info(
                    "[VisionAnalyst] Character detected: %s → %s", alias, char_tag
                )
                return tags
        return []

    def _prompt_only_analysis(self, user_prompt: str) -> VisionAnalysis:
        """Fallback: derive analysis from prompt text alone.

        When the prompt contains non-ASCII characters (Vietnamese, Japanese,
        Chinese, Korean, etc.) the raw text is unintelligible to SD models.
        In that case we call an LLM to translate it into English danbooru tags
        and return them with sufficient confidence to be used by the planner.

        Character detection runs first - if a known character is found, their
        visual tags are prepended so the model generates the correct appearance
        even without reference images.

        Scene/background tags are stored separately in background_elements so
        the planner can ensure they reach the final prompt without being
        truncated by character identity tags.
        """
        is_ascii = all(ord(c) < 128 for c in user_prompt)

        # ── Step 1: detect known character and pre-fill appearance tags ──
        character_tags = self._resolve_character_tags(user_prompt)

        translated_char_tags: list[str] = []
        translated_scene_tags: list[str] = []
        confidence = 0.3
        model_used = "prompt_fallback"

        if not is_ascii or character_tags:
            if not is_ascii:
                logger.info(
                    "[VisionAnalyst] Non-ASCII prompt detected, translating to English tags"
                )
            translated_char_tags, translated_scene_tags = (
                self._translate_prompt_to_tags(user_prompt)
            )
            if translated_char_tags or translated_scene_tags:
                confidence = 0.65
                model_used = "prompt_translation"
                logger.info(
                    "[VisionAnalyst] Translated char=%s scene=%s",
                    translated_char_tags,
                    translated_scene_tags,
                )
            else:
                logger.warning(
                    "[VisionAnalyst] Translation failed, prompt will be used raw"
                )

        # ── Step 2: merge character identity tags (hardcoded + LLM) ──
        # Deduplicate preserving order (hardcoded character tags first)
        merged_identity: list[str] = []
        seen: set[str] = set()
        for tag in character_tags + translated_char_tags:
            if tag and tag not in seen:
                merged_identity.append(tag)
                seen.add(tag)

        # ── Step 3: scene tags stay separate — not mixed with identity ──
        scene_tags: list[str] = []
        for tag in translated_scene_tags:
            if tag and tag not in seen:
                scene_tags.append(tag)
                seen.add(tag)

        # Combine all for anime_tags but ensure scene tags follow identity
        all_tags = merged_identity + scene_tags

        if all_tags:
            confidence = max(confidence, 0.75)
            if character_tags:
                model_used = model_used + "+character_detect"

        return VisionAnalysis(
            caption_short=user_prompt[:200],
            caption_detailed=user_prompt,
            subjects=[user_prompt.split(",")[0].strip()] if user_prompt else [],
            anime_tags=all_tags,
            background_elements=scene_tags,  # scene tags preserved separately
            confidence=confidence,
            model_used=model_used,
        )

    def _translate_prompt_to_tags(
        self, user_prompt: str
    ) -> tuple[list[str], list[str]]:
        """Use an LLM to convert a non-English prompt to English ComfyUI tags.

        Returns (character_tags, scene_tags) - two separate lists.
        """
        import httpx

        msg = _PROMPT_TRANSLATION_TEMPLATE.format(user_prompt=user_prompt)

        def _parse_tags(text: str) -> tuple[list[str], list[str]]:
            """Parse tags from JSON response. Handles both old flat format and new split format."""
            try:
                text = text.strip()
                if text.startswith("```"):
                    text = text.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
                obj = json.loads(text)
                if isinstance(obj, dict):
                    # New split format: {"character_tags": [...], "scene_tags": [...]}
                    char_tags = obj.get("character_tags", [])
                    scene_tags = obj.get("scene_tags", [])
                    if char_tags or scene_tags:
                        c = [str(t).strip() for t in char_tags[:8] if t]
                        s = [str(t).strip() for t in scene_tags[:12] if t]
                        return c, s
                    # Fallback: old flat format {"tags": [...]}
                    flat = obj.get("tags", obj.get("tag_list", []))
                    if isinstance(flat, list):
                        return [], [str(t).strip() for t in flat[:15] if t]
                if isinstance(obj, list):
                    return [], [str(t).strip() for t in obj[:15] if t]
            except (json.JSONDecodeError, KeyError):
                pass
            return [], []

        # Prompt translation is a runtime concern, so it is local-only. A
        # missing VLM degrades to deterministic prompt parsing below.
        local_url = f"{self._config.local_vlm_url.rstrip('/')}/chat/completions"
        try:
            self._policy.assert_url(local_url, purpose="local_prompt_translation")
            with httpx.Client(timeout=15) as client:
                resp = client.post(
                    local_url,
                    json={
                        "model": self._config.local_vlm_model or "local-vlm",
                        "messages": [{"role": "user", "content": msg}],
                        "max_tokens": 200,
                        "temperature": 0.1,
                        "response_format": {"type": "json_object"},
                    },
                    headers={
                        "Authorization": "Bearer "
                        + os.getenv("ANIME_PIPELINE_LOCAL_VLM_API_KEY", "local")
                    },
                )
                resp.raise_for_status()
            text = resp.json()["choices"][0]["message"]["content"]
            return _parse_tags(text)
        except Exception as e:
            logger.debug("[VisionAnalyst] Local translation unavailable: %s", e)
            return [], []

        # Try Gemini first (rotate through key pool, skip exhausted keys).
        from .._gemini_pool import get_active_key, mark_exhausted, is_quota_error

        while True:
            gemini_key = get_active_key()
            if not gemini_key:
                break
            try:
                url = (
                    "https://generativelanguage.googleapis.com/v1beta/models/"
                    "gemini-2.0-flash:generateContent"
                )
                with httpx.Client(timeout=15) as client:
                    resp = client.post(
                        url,
                        headers={"X-goog-api-key": gemini_key},
                        json={
                            "contents": [{"parts": [{"text": msg}]}],
                            "generationConfig": {
                                "temperature": 0.1,
                                "maxOutputTokens": 200,
                                "responseMimeType": "application/json",
                            },
                        },
                    )
                    resp.raise_for_status()
                data = resp.json()
                text = (
                    data.get("candidates", [{}])[0]
                    .get("content", {})
                    .get("parts", [{}])[0]
                    .get("text", "{}")
                )
                char_t, scene_t = _parse_tags(text)
                if char_t or scene_t:
                    return char_t, scene_t
                break  # Empty response — give up on Gemini, fall through to OpenAI.
            except Exception as e:
                if is_quota_error(e):
                    mark_exhausted(gemini_key, "429 in vision_analyst")
                    continue  # Try next key in pool.
                logger.warning("[VisionAnalyst] Gemini translation failed: %s", e)
                break

        # Fallback: OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            try:
                with httpx.Client(timeout=15) as client:
                    resp = client.post(
                        "https://api.openai.com/v1/chat/completions",
                        json={
                            "model": "gpt-4o-mini",
                            "messages": [{"role": "user", "content": msg}],
                            "max_tokens": 200,
                            "temperature": 0.1,
                            "response_format": {"type": "json_object"},
                        },
                        headers={"Authorization": f"Bearer {openai_key}"},
                    )
                    resp.raise_for_status()
                data = resp.json()
                text = data["choices"][0]["message"]["content"]
                char_t, scene_t = _parse_tags(text)
                if char_t or scene_t:
                    return char_t, scene_t
            except Exception as e:
                logger.warning("[VisionAnalyst] OpenAI translation failed: %s", e)

        return [], []
