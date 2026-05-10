"""
Image Intent Detection — classifies user messages to determine if image generation
is needed, what kind (new vs edit vs followup), and what generation parameters to use.

Designed to be fast (no LLM calls), battle-tested with Vietnamese + English.
Called by ImageOrchestrator.handle() before every chat request.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class ImageIntent(str, Enum):
    GENERATE      = "generate"   # Fresh image generation
    EDIT          = "edit"       # Explicit edit of the last image ("sửa ảnh", "edit image")
    FOLLOWUP_EDIT = "followup"   # Short follow-up that modifies last image ("thêm cầu vồng")
    NONE          = "none"       # Not an image request → pass to LLM


@dataclass
class IntentResult:
    intent:        ImageIntent    = ImageIntent.NONE
    quality_hint:  str            = "auto"    # auto|fast|quality|free|cheap
    width:         int            = 1024
    height:        int            = 1024
    style_hint:    Optional[str]  = None
    provider_hint: Optional[str]  = None
    edit_verb:     str            = ""        # "add", "remove", "change", "make", …
    confidence:    float          = 0.0       # 0–1
    debug:         dict           = field(default_factory=dict)


# ── Keyword banks ─────────────────────────────────────────────────────

_GEN_VI = [
    "vẽ", "tạo ảnh", "tạo hình", "sinh ảnh", "gen ảnh", "tạo một",
    "vẽ cho", "tạo logo", "thiết kế", "minh họa", "vẽ tranh",
    "ảnh anime", "hình ảnh", "bức ảnh", "bức tranh", "ảnh nền",
    "avatar", "icon", "tạo ra", "làm ảnh", "tạo hình ảnh",
    "một bức", "hình nền", "wallpaper", "render",
]

_GEN_EN = [
    "draw", "paint", "generate image", "create image", "make image",
    "gen image", "image of", "design", "illustrate", "render",
    "visualize", "photo of", "picture of", "artwork", "wallpaper",
    "logo", "portrait", "landscape painting", "a picture", "a photo",
    "create a", "draw a", "make a", "generate a", "paint a",
    "generate me", "create me", "draw me", "show me a",
    "create an image", "make an image",
]

_EDIT_VI = [
    "thêm vào ảnh", "bỏ khỏi ảnh", "xóa trong ảnh", "chỉnh ảnh",
    "sửa ảnh", "edit ảnh", "thay đổi ảnh", "đổi màu",
    "thêm hiệu ứng", "làm sáng hơn", "làm tối hơn", "làm mờ",
    "xóa nền", "đổi nền", "thêm người", "xóa người",
    "làm nét hơn", "cắt ảnh", "thêm text", "thêm chữ",
    "vào ảnh trên", "vào ảnh vừa", "trong ảnh đó", "ảnh trên",
    "ảnh đó",
]

_EDIT_EN = [
    "edit image", "modify image", "img2img", "inpaint",
    "add to the image", "remove from image", "change the image",
    "make it", "to that image", "to the last image",
    "to the previous image", "that image", "the image above",
    "add some", "change color",
]

# Short follow-up patterns — require has_previous_image=True
_FOLLOWUP_VI = [
    "thêm", "bỏ", "xóa", "đổi", "thay", "sửa lại", "chỉnh lại",
    "làm cho", "biến thành", "đổi thành", "hãy thêm", "hãy bỏ",
    "tươi hơn", "tối hơn", "sáng hơn", "mờ hơn", "sắc nét hơn",
    "khác màu", "to hơn", "nhỏ hơn", "nền trắng", "nền đen",
    "thêm bầu trời", "thêm cây", "thêm người", "bỏ nền", "đổi nền",
]

_FOLLOWUP_EN = [
    "add", "remove", "change", "make it", "make the",
    "brighter", "darker", "sharper", "blurrier", "more colorful",
    "new background", "white background", "black background",
    "add sky", "add trees", "add person",
    "no background", "remove background",
]

_CHAT_ONLY = [
    "giải thích", "explain", "dịch", "translate", "tóm tắt", "summarize",
    "code", "lập trình", "debug", "fix bug", "sửa lỗi", "viết hàm",
    "algorithm", "so sánh", "compare", "phân tích", "analyze",
    "review", "tư vấn", "hỏi đáp", "question", "what is", "how to",
    "tell me", "why", "tại sao", "vì sao", "như thế nào",
    "cách nào", "what does", "who is", "where is", "when did",
    "list of", "help me with", "write a", "write me",
    "định nghĩa", "ý nghĩa",
    # Programming / scripting — prevent IMAGE_FIRST_MODE false triggers
    "function", "script", "viết", "python", "javascript", "typescript",
    "java", "golang", "rust", "c++", "c#", "php", "ruby",
    "sort", "implement", "mảng", "array", "class", "method",
    "module", "import", "library", "framework", "api",
    "database", "sql", "query", "loop", "recursion",
]

# Quality mapping
_QUALITY_MAP: dict[str, tuple[str, list[str]]] = {
    "quality": ("quality", ["chất lượng cao", "hd", "4k", "8k", "ultra", "detailed", "best", "pro", "high quality"]),
    "fast":    ("fast",    ["nhanh", "quick", "fast", "draft", "sketch", "rough", "nháp"]),
    "free":    ("free",    ["comfyui", "local", "miễn phí", "free", "offline"]),
    "cheap":   ("cheap",   ["rẻ nhất", "cheapest", "budget", "cheap"]),
}

# Style mapping
_STYLE_MAP: dict[str, list[str]] = {
    "anime":         ["anime", "manga", "chibi", "ghibli", "hoạt hình nhật", "phong cách anime"],
    "photorealistic":["thực tế", "realistic", "photorealistic", "real", "photo", "ảnh thật"],
    "digital_art":   ["digital art", "digital", "artstation", "concept art"],
    "oil_painting":  ["oil painting", "tranh sơn dầu", "classical painting"],
    "watercolor":    ["watercolor", "màu nước", "tranh màu nước"],
    "cinematic":     ["cinematic", "điện ảnh", "movie", "film", "dramatic"],
    "3d_render":     ["3d", "render", "3d render", "blender", "cgi"],
    "pixel_art":     ["pixel art", "pixel", "retro", "8-bit", "16-bit"],
    "sketch":        ["sketch", "phác thảo", "pencil", "bút chì"],
    "minimalist":    ["minimal", "minimalist", "tối giản", "clean", "simple"],
}

# Dimension hints
_PORTRAIT_HINTS  = ["portrait", "dọc", "vertical", "tall", "9:16", "phone wallpaper", "mobile"]
_LANDSCAPE_HINTS = ["landscape", "ngang", "horizontal", "wide", "16:9", "desktop wallpaper", "banner"]
_SQUARE_HINTS    = ["square", "vuông", "1:1", "instagram", "profile", "avatar", "icon"]

# Question starters (used to avoid false IMAGE_FIRST_MODE triggers)
_QUESTION_STARTERS = [
    "là", "có", "tại sao", "vì sao", "bao nhiêu", "khi nào", "ở đâu",
    "what", "why", "how", "when", "where", "who", "can you", "will you",
    "do you", "is ", "are ", "was ", "were ", "did ", "does ",
]


# ─────────────────────────────────────────────────────────────────────

def detect_intent(message: str, has_previous_image: bool = False) -> IntentResult:
    """
    Classify a user message into an image intent.

    Returns IntentResult — if intent == NONE, the caller should fall through
    to the normal LLM chat flow.
    """
    msg_lower = message.lower().strip()
    result = IntentResult()
    debug: dict = {}

    # ── 1. Strong negative: chat-only keywords ────────────────────────
    chat_only_matches = [kw for kw in _CHAT_ONLY if kw in msg_lower]
    if chat_only_matches:
        image_keywords = _GEN_VI + _GEN_EN
        image_matches = [kw for kw in image_keywords if kw in msg_lower]
        if not image_matches:
            debug["chat_only_matches"] = chat_only_matches[:3]
            result.debug = debug
            return result  # NONE

    # ── 2. Explicit edit intent (only when a previous image exists) ───
    if has_previous_image:
        edit_matches = [kw for kw in _EDIT_VI + _EDIT_EN if kw in msg_lower]
        if edit_matches:
            result.intent    = ImageIntent.EDIT
            result.confidence = min(1.0, 0.6 + len(edit_matches) * 0.1)
            result.edit_verb  = _extract_edit_verb(msg_lower)
            debug["edit_matches"] = edit_matches[:5]
            result = _extract_hints(msg_lower, result)
            result.debug = debug
            return result

        # Short follow-up: word starts/contains followup keyword AND ≤10 words
        followup_padded = f" {msg_lower} "
        followup_matches = [
            kw for kw in _FOLLOWUP_VI + _FOLLOWUP_EN
            if msg_lower.startswith(kw) or f" {kw} " in followup_padded
        ]
        if followup_matches and len(msg_lower.split()) <= 12:
            result.intent    = ImageIntent.FOLLOWUP_EDIT
            result.confidence = min(1.0, 0.5 + len(followup_matches) * 0.1)
            result.edit_verb  = _extract_edit_verb(msg_lower)
            debug["followup_matches"] = followup_matches[:5]
            result = _extract_hints(msg_lower, result)
            result.debug = debug
            return result

    # ── 3. Generation intent ──────────────────────────────────────────
    gen_matches = [kw for kw in _GEN_VI + _GEN_EN if kw in msg_lower]
    if gen_matches:
        result.intent    = ImageIntent.GENERATE
        result.confidence = min(1.0, 0.5 + len(gen_matches) * 0.15)
        debug["gen_matches"] = gen_matches[:5]
        result = _extract_hints(msg_lower, result)
        result.debug = debug
        return result

    # ── 4. IMAGE_FIRST_MODE inference ────────────────────────────────
    image_first = os.getenv("IMAGE_FIRST_MODE", "1").lower() in ("1", "true", "yes", "on")
    if image_first and not chat_only_matches:
        words = msg_lower.split()
        is_question = msg_lower.endswith("?") or any(
            msg_lower.startswith(q) for q in _QUESTION_STARTERS
        )
        if len(words) >= 3 and not is_question:
            result.intent    = ImageIntent.GENERATE
            result.confidence = 0.3  # low — IMAGE_FIRST_MODE heuristic
            debug["image_first_mode"] = True
            result = _extract_hints(msg_lower, result)
            result.debug = debug

    return result


def _extract_edit_verb(msg_lower: str) -> str:
    """Identify the primary edit action from the message."""
    verbs = {
        "add":     ["add", "thêm", "thêm vào", "hãy thêm"],
        "remove":  ["remove", "xóa", "bỏ", "loại bỏ", "delete"],
        "change":  ["change", "đổi", "thay đổi", "modify", "alter", "thay"],
        "make":    ["make it", "make the", "làm cho", "biến thành", "làm"],
        "replace": ["replace", "thay thế"],
    }
    for verb, patterns in verbs.items():
        if any(p in msg_lower for p in patterns):
            return verb
    return "edit"


def _extract_hints(msg_lower: str, result: IntentResult) -> IntentResult:
    """Extract quality, dimension, and style hints from the message."""
    # Style
    for style_name, keywords in _STYLE_MAP.items():
        if any(kw in msg_lower for kw in keywords):
            result.style_hint = style_name
            break

    # Quality
    for _key, (mode, keywords) in _QUALITY_MAP.items():
        if any(kw in msg_lower for kw in keywords):
            result.quality_hint = mode
            break

    # Dimensions
    if any(h in msg_lower for h in _PORTRAIT_HINTS):
        result.width  = 768
        result.height = 1344
    elif any(h in msg_lower for h in _LANDSCAPE_HINTS):
        result.width  = 1344
        result.height = 768
    # Square or single-word hints default stays 1024×1024

    return result
