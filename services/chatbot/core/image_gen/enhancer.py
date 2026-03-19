"""
PromptEnhancer â€” uses an LLM to transform user's casual request into 
an optimized image generation prompt.

This is the key differentiator: ChatGPT/Gemini/Grok all use their LLM 
to rewrite prompts internally before sending to the image model.
We do the same thing explicitly.
"""

from __future__ import annotations

import os
import json
import logging
import httpx
from typing import Optional

logger = logging.getLogger(__name__)

# â”€â”€ System prompt for the enhancer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
ENHANCER_SYSTEM = """You are an expert AI image prompt engineer. Your job is to take a user's casual image request and transform it into an optimized prompt for a text-to-image diffusion model (like FLUX, DALL-E, or Stable Diffusion).

RULES:
1. Keep the user's core intent intact â€” do NOT change what they want
2. Add technical quality boosters: lighting, composition, detail level, camera angle
3. Add style descriptors when not specified: photorealistic, cinematic, illustration, etc.
4. Keep prompt under 200 words â€” models work best with concise prompts
5. If the user writes in Vietnamese, translate the visual description to English for the model
6. Output ONLY the enhanced prompt â€” no explanations, no markdown, no quotes
7. For editing requests ("thÃªm...", "bá»...", "Ä‘á»•i...") on an existing image, output an img2img-focused prompt

EXAMPLES:
User: "váº½ con mÃ¨o"
Enhanced: A fluffy white cat sitting gracefully on a sunlit windowsill, golden hour lighting streaming through lace curtains, photorealistic, shallow depth of field, 4K, warm color palette

User: "cyberpunk city at night"  
Enhanced: Sprawling cyberpunk metropolis at night, neon signs reflecting on rain-soaked streets, towering holographic billboards, flying vehicles between skyscrapers, blade runner atmosphere, dramatic rain, volumetric fog, cinematic wide angle, ultra detailed, 8K

User: "logo for a coffee shop called Bean & Brew"
Enhanced: Minimalist logo design for "Bean & Brew" coffee shop, steaming coffee cup icon integrated with stylized coffee bean, warm brown and cream color scheme, clean vector style, professional branding, white background

User: "thÃªm cáº§u vá»“ng vÃ o báº§u trá»i"
Enhanced: Add a vibrant double rainbow arching across the sky, natural atmospheric lighting, soft prismatic colors blending into the existing scene"""


STYLE_PRESETS = {
    "photorealistic": "photorealistic, DSLR quality, natural lighting, 8K resolution, detailed textures",
    "anime": "anime art style, vibrant colors, clean linework, studio Ghibli inspired, manga shading",
    "cinematic": "cinematic composition, dramatic lighting, film grain, anamorphic lens, movie still, 35mm",
    "watercolor": "watercolor painting, soft washes, paper texture, artistic brushstrokes, muted palette",
    "digital_art": "digital art, vibrant, artstation trending, concept art, highly detailed illustration",
    "oil_painting": "oil painting on canvas, rich impasto texture, classical composition, museum quality",
    "pixel_art": "pixel art, retro 16-bit style, limited color palette, crisp pixels, nostalgic",
    "3d_render": "3D render, octane render, ray tracing, subsurface scattering, physically based materials",
    "sketch": "pencil sketch, detailed cross-hatching, graphite on paper, artistic study",
    "pop_art": "pop art style, bold colors, halftone dots, comic book aesthetic, Andy Warhol inspired",
    "minimalist": "minimalist design, clean lines, simple shapes, negative space, modern aesthetic",
    "fantasy": "fantasy art, magical atmosphere, ethereal glow, mythical, epic composition, detailed",
    "noir": "film noir style, black and white, dramatic shadows, high contrast, moody atmosphere",
    "vaporwave": "vaporwave aesthetic, pink and blue neon, retro 80s, glitch art, geometric shapes",
    "studio_photo": "professional studio photography, softbox lighting, clean background, commercial quality",
}


class PromptEnhancer:
    """Enhance user prompts using any OpenAI-compatible LLM."""

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "https://api.x.ai/v1",  # default to Grok
        model: str = "grok-3-mini",
        fallback_api_key: str = "",
        fallback_base_url: str = "https://api.deepseek.com",
        fallback_model: str = "deepseek-chat",
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.fallback_api_key = fallback_api_key
        self.fallback_base_url = fallback_base_url
        self.fallback_model = fallback_model
        self._enabled = bool(api_key)

    def enhance(
        self,
        user_prompt: str,
        style_preset: Optional[str] = None,
        context: Optional[str] = None,
    ) -> str:
        """
        Enhance a user prompt. Returns enhanced prompt string.
        Falls back to original if LLM call fails.
        """
        if not self._enabled:
            return self._manual_enhance(user_prompt, style_preset)

        try:
            return self._llm_enhance(user_prompt, style_preset, context)
        except Exception as e:
            logger.warning(f"[PromptEnhancer] LLM failed ({e}), trying fallback...")
            try:
                if self.fallback_api_key:
                    return self._llm_enhance(
                        user_prompt, style_preset, context,
                        api_key=self.fallback_api_key,
                        base_url=self.fallback_base_url,
                        model=self.fallback_model,
                    )
            except Exception as e2:
                logger.warning(f"[PromptEnhancer] Fallback also failed ({e2}), using manual enhance")
            return self._manual_enhance(user_prompt, style_preset)

    def _llm_enhance(
        self,
        user_prompt: str,
        style_preset: Optional[str] = None,
        context: Optional[str] = None,
        api_key: str = "",
        base_url: str = "",
        model: str = "",
    ) -> str:
        api_key = api_key or self.api_key
        base_url = base_url or self.base_url
        model = model or self.model

        messages = [{"role": "system", "content": ENHANCER_SYSTEM}]

        user_msg = user_prompt
        if style_preset and style_preset in STYLE_PRESETS:
            user_msg += f"\n\n[Style: {style_preset}]"
        if context:
            user_msg += f"\n\n[Context: {context}]"

        messages.append({"role": "user", "content": user_msg})

        with httpx.Client(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=15.0,
        ) as client:
            resp = client.post("/chat/completions", json={
                "model": model,
                "messages": messages,
                "max_tokens": 300,
                "temperature": 0.7,
            })
            resp.raise_for_status()
            data = resp.json()
            enhanced = data["choices"][0]["message"]["content"].strip()

            # Clean up any wrapping the LLM might add
            for wrapper in ['```', '"', "'"]:
                enhanced = enhanced.strip(wrapper)

            return enhanced

    def _manual_enhance(self, user_prompt: str, style_preset: Optional[str] = None) -> str:
        """Rule-based enhancement when LLM is unavailable."""
        parts = [user_prompt]

        if style_preset and style_preset in STYLE_PRESETS:
            parts.append(STYLE_PRESETS[style_preset])

        # Add generic quality boosters if prompt is short
        if len(user_prompt.split()) < 15:
            parts.append("highly detailed, professional quality, 4K resolution")

        return ", ".join(parts)

    def detect_edit_intent(self, user_message: str) -> dict:
        """
        Detect if the user wants to edit a previous image vs. generate new.
        Returns: {"is_edit": bool, "edit_type": str, "description": str}
        """
        edit_keywords_vi = ["thÃªm", "bá»", "xÃ³a", "Ä‘á»•i", "thay", "sá»­a", "chá»‰nh", "lÃ m", "biáº¿n"]
        edit_keywords_en = ["add", "remove", "change", "replace", "fix", "adjust", "make", "turn"]

        lower = user_message.lower().strip()
        
        for kw in edit_keywords_vi + edit_keywords_en:
            if lower.startswith(kw) or f" {kw} " in f" {lower} ":
                return {
                    "is_edit": True,
                    "edit_type": "modify",
                    "description": user_message,
                }

        # Check for referencing previous image
        ref_patterns = ["áº£nh trÆ°á»›c", "áº£nh vá»«a", "cÃ¡i áº£nh", "last image", "previous image", "that image"]
        for pat in ref_patterns:
            if pat in lower:
                return {
                    "is_edit": True,
                    "edit_type": "reference_edit",
                    "description": user_message,
                }

        return {"is_edit": False, "edit_type": "new", "description": user_message}


# Convenience factory
def create_enhancer() -> PromptEnhancer:
    """Create a PromptEnhancer from environment variables."""
    return PromptEnhancer(
        api_key=os.getenv("GROK_API_KEY", ""),
        base_url="https://api.x.ai/v1",
        model="grok-3-mini",
        fallback_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        fallback_base_url="https://api.deepseek.com",
        fallback_model="deepseek-chat",
    )
