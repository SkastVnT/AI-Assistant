"""
ScenePlanner (v2)
=================
Deterministic, rule-based scene planner for image generation requests.
Zero LLM calls. Fully unit-testable. Supports Vietnamese + English (or mixed).

Classification (PlanClassification):
  GENERATE       — new image from scratch
  EDIT_FOLLOWUP  — edit / refine the previous image
  UNCERTAIN      — ambiguous; caller may ask for clarification

Fields extracted → SceneSpec:
  subject, subject_attributes, action
  background (= environment), lighting, mood
  style, quality_preset, aspect_ratio
  composition, camera
  wants_text_in_image, wants_consistency_with_previous, wants_real_world_accuracy
  negative_hints, extra_tags, seed, edit_operations

Vietnamese edit follow-up patterns detected:
  "làm trời tối hơn"               → EDIT_FOLLOWUP + EditOp(modify, sky, darker)
  "thêm kính"                      → EDIT_FOLLOWUP + EditOp(add, glasses)
  "đổi tóc thành màu trắng"        → EDIT_FOLLOWUP + EditOp(change, hair, white)
  "giữ nhân vật cũ nhưng đổi nền"  → EDIT_FOLLOWUP + wants_consistency + EditOp(change, background)
  "bỏ cái mũ"                      → EDIT_FOLLOWUP + EditOp(remove, hat)
  "thêm chữ sale 50%"              → EDIT_FOLLOWUP + wants_text_in_image + EditOp(add_text, sale 50%)
"""

from __future__ import annotations

import re
from dataclasses import replace as dc_replace
from typing import Optional

from .schemas import (
    ImageIntent,
    PlanClassification,
    EditOperation,
    PlanResult,
    SceneSpec,
)



# ─────────────────────────────────────────────────────────────────────
# 1. Aspect-ratio / dimension tables
# ─────────────────────────────────────────────────────────────────────

_PORTRAIT_HINTS    = ["dọc", "thẳng đứng", "chân dung", "9:16", "4:3 dọc",
                      "portrait", "vertical", "tall", "phone wallpaper"]
_LANDSCAPE_HINTS   = ["ngang", "rộng", "phong cảnh ngang", "16:9", "panorama",
                      "landscape", "horizontal", "16:9", "banner", "thumbnail"]
_WIDE_HINTS        = ["ultra wide", "21:9", "anamorphic", "siêu rộng"]

_DIMS: dict[str, tuple[int, int]] = {
    "square":    (1024, 1024),
    "portrait":  (768,  1024),
    "landscape": (1024, 768),
    "wide":      (1216, 832),
}

# ─────────────────────────────────────────────────────────────────────
# 2. Style detection
# ─────────────────────────────────────────────────────────────────────

_STYLE_KEYWORDS: dict[str, list[str]] = {
    "anime":          ["anime", "manga", "ghibli", "chibi", "waifu", "nhật bản",
                       "nhân vật anime", "hoạt hình nhật", "2d anime"],
    "photorealistic": ["realistic", "thực tế", "photo", "ảnh thật", "chụp ảnh",
                       "photography", "photoreal", "hyperrealistic", "siêu thực"],
    "cinematic":      ["cinematic", "điện ảnh", "movie", "film", "phim", "trailer",
                       "movie still", "film grain"],
    "watercolor":     ["watercolor", "màu nước", "acrylic painting"],
    "digital_art":    ["digital art", "concept art", "artstation", "illustration",
                       "digital painting"],
    "oil_painting":   ["oil paint", "sơn dầu", "canvas", "oil on canvas"],
    "pixel_art":      ["pixel", "8-bit", "16-bit", "retro game", "sprite", "pixel art"],
    "3d_render":      ["3d render", "octane", "blender", "cgi", "3d model",
                       "c4d", "unreal engine", "ray tracing"],
    "sketch":         ["sketch", "phác thảo", "pencil", "bút chì", "lineart",
                       "line drawing", "ink sketch"],
    "minimalist":     ["minimal", "tối giản", "flat design", "simple vector"],
    "fantasy":        ["fantasy", "kỳ ảo", "magic", "phép thuật", "rồng",
                       "elf", "wizard", "thần tiên", "huyền ảo"],
    "noir":           ["noir", "đen trắng", "black and white", "shadow play",
                       "dark moody", "monochrome"],
    "vaporwave":      ["vaporwave", "neon aesthetic", "synthwave", "retrowave", "80s aesthetic"],
    "studio_photo":   ["studio", "nền trắng", "white background",
                       "product photo", "studio portrait"],
}

# ─────────────────────────────────────────────────────────────────────
# 3. Quality presets
# ─────────────────────────────────────────────────────────────────────

_QUALITY_MAP: dict[str, list[str]] = {
    "fast":    ["nhanh", "fast", "quick", "draft", "thử nhanh", "tốc độ"],
    "quality": ["chất lượng cao", "hd", " 4k", " 8k", "ultra", "best quality",
                "chi tiết cao", "masterpiece", "highest"],
    "free":    ["free", "miễn phí", "local", "offline", "comfyui"],
    "cheap":   ["cheap", "rẻ", "economy", "tiết kiệm"],
}

# ─────────────────────────────────────────────────────────────────────
# 4. Lighting patterns
# ─────────────────────────────────────────────────────────────────────

_LIGHTING: list[tuple[str, str]] = [
    (r"golden hour|ánh vàng buổi chiều",     "golden hour lighting, warm amber glow"),
    (r"hoàng hôn|sunset(?! gradient)",        "sunset, orange-red sky, warm light"),
    (r"bình minh|sunrise",                    "sunrise, soft pink-gold gradient sky"),
    (r"giữa trưa|midday|noon",                "harsh midday sun, strong overhead shadows"),
    (r"ban đêm|đêm khuya|late night",         "nighttime, dark sky, ambient street glow"),
    (r"ánh trăng|moonlight",                  "soft moonlight, cool blue-silver tones"),
    (r"neon(?! aesthetic)",                   "neon lights, colorful reflections, wet pavement"),
    (r"nến|candlelight",                      "candlelight, warm amber flickering glow"),
    (r"studio light|đèn studio",              "professional softbox studio lighting, even shadows"),
    (r"backlight|ngược sáng|rim light",       "dramatic backlight, rim lighting, silhouette"),
    (r"cloudy|nhiều mây|overcast",            "overcast sky, soft diffused light, no harsh shadows"),
    (r"tối hơn|darker sky|trời tối",          "darker atmosphere, low-key lighting, dramatic shadows"),
    (r"sáng hơn|brighter|ánh sáng mạnh",     "bright natural light, high-key, well-lit"),
]

# ─────────────────────────────────────────────────────────────────────
# 5. Mood patterns
# ─────────────────────────────────────────────────────────────────────

_MOOD: list[tuple[str, str]] = [
    (r"bình yên|peaceful|calm|yên tĩnh|tranquil",  "peaceful, serene, tranquil"),
    (r"hùng tráng|epic|majestic|hoành tráng",      "epic, grand, majestic, awe-inspiring"),
    (r"kinh dị|horror|đáng sợ|scary|creepy",       "eerie, ominous, unsettling, horror"),
    (r"vui vẻ|happy|cheerful|rực rỡ|joyful",       "cheerful, vibrant, joyful, uplifting"),
    (r"buồn bã|melancholic|sad|ảm đạm",            "melancholic, somber, bittersweet"),
    (r"lãng mạn|romantic|tình cảm|love",           "romantic, dreamy, soft and warm"),
    (r"bí ẩn|mysterious|mystical|huyền bí",        "mysterious, mystical, ethereal"),
    (r"mạnh mẽ|powerful|intense|dramatic|badass",  "powerful, intense, action-oriented"),
    (r"dễ thương|cute|kawaii|adorable|ngộ nghĩnh",  "cute, adorable, charming, playful"),
    (r"cô đơn|lonely|solitary|một mình",           "lonely, solitary, contemplative"),
    (r"hy vọng|hopeful|optimistic|tươi sáng",      "hopeful, optimistic, uplifting light"),
]

# ─────────────────────────────────────────────────────────────────────
# 6. Environment / background patterns
# ─────────────────────────────────────────────────────────────────────

_ENVIRONMENT: list[tuple[str, str]] = [
    (r"bãi biển|beach|seaside",                 "sandy beach, ocean waves, coastal scenery"),
    (r"biển|ocean|sea(?!\s*of)",                "open ocean, water reflections"),
    (r"rừng nhiệt đới|tropical forest|jungle",  "tropical jungle, dense canopy, lush vegetation"),
    (r"rừng|forest(?! fire)|woodland",          "dense forest, ancient trees, dappled light"),
    (r"núi tuyết|snowy mountain",               "snow-capped mountains, alpine landscape"),
    (r"núi|mountain|highland|đồi",              "mountain landscape, rocky peaks, dramatic sky"),
    (r"sa mạc|desert|sand dune|cát",            "desert landscape, rolling sand dunes, dry heat shimmer"),
    (r"tuyết|snow|snowfield|blizzard",          "snowy winter landscape, frost, white ground"),
    (r"thành phố|city|urban|đường phố",         "urban cityscape, busy streets, architecture"),
    (r"cyberpunk|tương lai|futuristic|sci-fi",  "futuristic sci-fi city, neon signs, high-tech"),
    (r"vũ trụ|space|galaxy|cosmos|thiên hà",    "outer space, star field, nebula, cosmic scale"),
    (r"đại dương sâu|deep ocean|underwater",    "underwater scene, bioluminescent light, coral"),
    (r"đồng bằng|plains|meadow|cánh đồng",     "open meadow, green fields, gentle hills"),
    (r"hang động|cave|grotto|hầm",              "cave interior, stalactites, filtered light"),
    (r"lâu đài|castle|palace",                  "grand castle, stone walls, medieval architecture"),
    (r"làng|village|thôn quê|countryside",      "rural village, countryside, quaint houses"),
    (r"cửa sổ|window",                          "by the window, soft filtered daylight"),
    (r"nền trắng|white background|clean bg",    "pure white background, studio setting"),
    (r"nền đen|black background",               "pure black background, isolated subject"),
]

# ─────────────────────────────────────────────────────────────────────
# 7. Composition patterns
# ─────────────────────────────────────────────────────────────────────

_COMPOSITION: list[tuple[str, str]] = [
    (r"cận cảnh (?:khuôn )?mặt|extreme close.?up face",  "extreme close-up, facial details"),
    (r"cận cảnh|close.?up|macro shot",                   "close-up shot, detailed framing"),
    (r"toàn thân|full body|head to toe",                  "full body shot, head to toe"),
    (r"nửa người|half body|waist up|upper body",          "upper body shot, waist up"),
    (r"nhìn từ trên|bird.?s eye|aerial view|từ trên cao", "bird's eye view, top-down perspective"),
    (r"góc thấp|low angle|nhìn từ dưới lên",              "low angle shot, dramatic perspective from below"),
    (r"góc nhìn người thứ nhất|first.?person|pov shot",   "first-person POV, immersive perspective"),
    (r"nhìn ngang|side profile|side view",                "side profile view, lateral composition"),
    (r"dutch angle|nghiêng camera",                       "dutch angle, tilted frame, dynamic tension"),
    (r"over the shoulder|qua vai",                        "over-the-shoulder composition"),
    (r"wide shot|cảnh rộng|toàn cảnh",                   "wide establishing shot, full environment"),
    (r"medium shot|tầm trung",                            "medium shot, waist-level framing"),
]

# ─────────────────────────────────────────────────────────────────────
# 8. Camera / lens patterns
# ─────────────────────────────────────────────────────────────────────

_CAMERA: list[tuple[str, str]] = [
    (r"85mm",                                "85mm portrait lens, shallow depth of field, creamy bokeh"),
    (r"50mm",                                "50mm standard lens, natural perspective"),
    (r"24mm|wide angle|góc rộng",           "24mm wide angle lens, expansive view"),
    (r"macro|cực cận|ultra close",          "macro photography lens, extreme close-up detail"),
    (r"fisheye|mắt cá",                     "fisheye lens, barrel distortion, wide perspective"),
    (r"telephoto|tele|200mm|zoom lens",     "telephoto compression, 200mm, compressed depth"),
    (r"tilt.?shift",                         "tilt-shift lens, selective focus, miniature effect"),
    (r"anamorphic|letterbox|cinemascope",   "anamorphic lens, horizontal lens flares, cinematic"),
    (r"bokeh|xóa phông|nền mờ",             "portrait lens, strong bokeh, blurred background"),
    (r"chụp phim|film camera|analog",       "analog film camera, film grain, film photography"),
    (r"drone|flycam|aerial",               "drone photography, aerial shot, aerial perspective"),
]

# ─────────────────────────────────────────────────────────────────────
# 9. Subject attribute patterns (VI + EN → English attribute string)
# ─────────────────────────────────────────────────────────────────────

_ATTRIBUTE_PATTERNS: list[tuple[str, str]] = [
    # ── Hair color ────────────────────────────────────────────────────
    (r"tóc hồng|pink hair",                    "pink hair"),
    (r"tóc vàng|blonde|golden hair",           "blonde hair"),
    (r"tóc đen|black hair",                    "black hair"),
    (r"tóc trắng|white hair",                  "white hair"),
    (r"tóc xanh dương|blue hair",              "blue hair"),
    (r"tóc xanh lá|green hair",               "green hair"),
    (r"tóc xanh(?! lá| dương)|teal hair",     "teal hair"),
    (r"tóc đỏ|red hair",                       "red hair"),
    (r"tóc nâu|brown hair",                    "brown hair"),
    (r"tóc bạc|silver hair|tóc xám",          "silver hair"),
    (r"tóc tím|purple hair",                   "purple hair"),
    (r"tóc cam|orange hair",                   "orange hair"),
    # ── Hair style ────────────────────────────────────────────────────
    (r"tóc ngắn|short hair",                   "short hair"),
    (r"tóc dài|long hair",                     "long hair"),
    (r"tóc xoăn|curly hair",                   "curly hair"),
    (r"tóc thẳng|straight hair",               "straight hair"),
    (r"tóc buộc|đuôi ngựa|ponytail",           "ponytail"),
    (r"tóc tết|braided hair|braid",            "braided hair"),
    (r"tóc hai bên|twin tails|twintails",      "twintails"),
    # ── Eye color ─────────────────────────────────────────────────────
    (r"mắt xanh dương|blue eyes",              "blue eyes"),
    (r"mắt xanh lá|green eyes",               "green eyes"),
    (r"mắt nâu|brown eyes",                    "brown eyes"),
    (r"mắt đen|dark eyes",                     "dark eyes"),
    (r"mắt đỏ|red eyes",                       "red eyes"),
    (r"mắt vàng|golden eyes|amber eyes",      "amber eyes"),
    (r"mắt tím|purple eyes|violet eyes",       "violet eyes"),
    (r"mắt mèo|cat eyes|cat-like eyes",       "cat-like eyes"),
    (r"mắt chói|glowing eyes",                 "glowing eyes"),
    (r"dị sắc|heterochromia",                  "heterochromia eyes"),
    # ── Skin / features ───────────────────────────────────────────────
    (r"da trắng|pale skin|fair skin",          "fair skin"),
    (r"da ngăm|dark skin|tanned skin",         "tanned skin"),
    (r"tàn nhang|freckles",                    "freckles"),
    (r"hình xăm|tattoo",                       "tattoos"),
    (r"sẹo|scar",                              "scar"),
    # ── Clothing / uniform ────────────────────────────────────────────
    (r"áo giáp(?! đen)|armor",                 "wearing armor"),
    (r"áo giáp đen|black armor",              "wearing black armor"),
    (r"kimono",                                "wearing kimono"),
    (r"áo dài",                                "wearing áo dài (Vietnamese traditional dress)"),
    (r"đồng phục học sinh|school uniform",    "school uniform"),
    (r"áo khoác da|leather jacket",            "leather jacket"),
    (r"áo choàng|cloak|cape|áo cape",         "wearing cape/cloak"),
    (r"trang phục phù thủy|wizard robe",       "wizard robe"),
    (r"váy trắng|white dress",                 "white dress"),
    (r"váy đỏ|red dress",                      "red dress"),
    (r"váy đen|black dress",                   "black dress"),
    # ── Accessories ───────────────────────────────────────────────────
    (r"\bkính cận\b|reading glasses",          "wearing glasses"),
    (r"\bkính mát\b|sunglasses",              "wearing sunglasses"),
    (r"\bkính\b(?! mát|cận)",                  "wearing glasses"),
    (r"mũ phù thủy|wizard hat",               "wizard hat"),
    (r"vương miện|crown|tiara",               "crown"),
    (r"\bmũ\b(?! phù thủy)|cap\b|baseball cap","wearing cap"),
    (r"khăn quàng|scarf",                      "wearing scarf"),
    (r"tai nghe|headphones",                   "wearing headphones"),
    # ── Special features ─────────────────────────────────────────────
    (r"cánh thiên thần|angel wings",          "angel wings"),
    (r"cánh quỷ|demon wings",                 "demon wings"),
    (r"cánh(?! thiên| quỷ)|wings",            "wings"),
    (r"đuôi mèo|cat tail",                    "cat tail"),
    (r"tai mèo|cat ears|neko",                "cat ears"),
    (r"tai thỏ|bunny ears",                   "bunny ears"),
    (r"đuôi cáo|fox tail",                    "fox tail"),
    (r"sừng ác quỷ|demon horns",             "demon horns"),
    (r"hào quang|halo|vầng hào quang",        "halo"),
    # ── Species / race ────────────────────────────────────────────────
    (r"elf|thần tiên tai nhọn",               "elf"),
    (r"vampire|ma cà rồng",                   "vampire"),
    (r"robot|cyborg|người máy",               "robot/cyborg"),
    (r"half.?dragon|nửa rồng",               "half-dragon"),
    (r"tiên|fairy(?! tale)",                  "fairy"),
    # ── Expression ───────────────────────────────────────────────────
    (r"mỉm cười|nụ cười|smiling|smile",       "smiling"),
    (r"cười lớn|laughing|grinning",           "laughing"),
    (r"khóc|crying|tears",                    "crying"),
    (r"nghiêm túc|serious expression",        "serious expression"),
    (r"ngạc nhiên|surprised",                 "surprised expression"),
    (r"tức giận|angry|angry face",            "angry expression"),
    # ── Build ─────────────────────────────────────────────────────────
    (r"cơ bắp|muscular|buff|strong build",    "muscular build"),
    (r"nhỏ bé|petite|slim figure",            "petite figure"),
    (r"cao lớn|tall(?! build)",               "tall figure"),
    # ── Weapons ───────────────────────────────────────────────────────
    (r"kiếm rồng|dragon sword",               "dragon sword"),
    (r"kiếm ma(?:\s|$)|magic sword|enchanted sword", "enchanted sword"),
    (r"\bkiếm\b(?! rồng| ma)|katana|sword",  "sword"),
    (r"súng|gun|pistol|rifle",               "gun"),
    (r"cung tên|bow and arrow",              "bow and arrow"),
    (r"giáo|spear|lance",                    "spear"),
    (r"búa|axe|hammer",                      "axe"),
]

# ─────────────────────────────────────────────────────────────────────
# 10. Vietnamese → English target/value translation tables
# ─────────────────────────────────────────────────────────────────────

# Targets (what element is being edited)
_VI_TARGET_EN: list[tuple[str, str]] = [
    (r"tóc",       "hair"),
    (r"mắt",       "eyes"),
    (r"kính mát",  "sunglasses"),
    (r"kính",      "glasses"),
    (r"mũ phù thủy","wizard hat"),
    (r"mũ",        "hat"),
    (r"áo giáp",   "armor"),
    (r"áo",        "clothing"),
    (r"váy",       "dress/skirt"),
    (r"da",        "skin"),
    (r"cánh",      "wings"),
    (r"đuôi",      "tail"),
    (r"kiếm",      "sword"),
    (r"súng",      "gun"),
    (r"nền",       "background"),
    (r"phông",     "background"),
    (r"bầu trời|trời(?!\s+tối|\s+sáng)", "sky"),
    (r"trời tối",  "sky/lighting"),
    (r"ánh sáng",  "lighting"),
    (r"đèn",       "lighting"),
    (r"bóng",      "shadow"),
    (r"mặt trời",  "sun"),
    (r"mây",       "clouds"),
    (r"nhân vật|người|character|subject", "character"),
    (r"hoa",       "flowers"),
    (r"cây",       "tree"),
    (r"cửa sổ",   "window"),
    (r"mặt",       "face"),
    (r"tay",       "hands"),
    (r"chân",      "legs"),
    (r"hình xăm",  "tattoo"),
    (r"vết sẹo|sẹo", "scar"),
    (r"chữ\b|text\b", "text"),
]

# Values (new value after change)
_VI_VALUE_EN: list[tuple[str, str]] = [
    (r"trắng|white",    "white"),
    (r"đen|black",      "black"),
    (r"đỏ|red",         "red"),
    (r"xanh dương|blue","blue"),
    (r"xanh lá|green",  "green"),
    (r"xanh\b",         "blue"),
    (r"vàng|yellow|golden", "golden"),
    (r"hồng|pink",      "pink"),
    (r"tím|purple|violet", "purple"),
    (r"nâu|brown",      "brown"),
    (r"bạc|silver",     "silver"),
    (r"cam|orange",     "orange"),
    (r"xám|gray",       "gray"),
    (r"ngắn|short",     "short"),
    (r"dài|long",       "long"),
    (r"xoăn|curly",     "curly"),
    (r"thẳng|straight", "straight"),
    # Background values
    (r"rừng|forest|woodland",     "dense forest, lush vegetation"),
    (r"sa mạc|desert",            "desert landscape, sand dunes"),
    (r"thành phố|city",           "urban cityscape"),
    (r"biển|beach|ocean",         "seaside, ocean waves"),
    (r"núi|mountain",             "mountain landscape"),
    (r"vũ trụ|space|cosmos",      "outer space, cosmos"),
    (r"công viên|park",           "park, green scenery"),
    (r"phòng|room|interior",      "indoor room, interior"),
    (r"tuyết|snow",               "snowy landscape"),
]

# ─────────────────────────────────────────────────────────────────────
# 11. Generate verb patterns (triggers GENERATE)
# ─────────────────────────────────────────────────────────────────────

_VI_GENERATE_VERBS = [
    r"^vẽ\b", r"^tạo ảnh\b", r"^tạo hình\b", r"^sinh ảnh\b",
    r"^gen ảnh\b", r"^tạo (một |bức )?", r"^minh họa\b", r"^thiết kế\b",
    r"^làm ảnh\b", r"^render\b", r"^chụp\b", r"^tưởng tượng\b",
    r"^tạo ra\b", r"^phác thảo\b",
]
_EN_GENERATE_VERBS = [
    r"^draw\b", r"^paint\b", r"^generate\b", r"^create\b", r"^make\b(?!.+\bhơn\b)",
    r"^design\b", r"^illustrate\b", r"^render\b", r"^visualize\b",
    r"^show me\b", r"^imagine\b", r"^sketch\b",
]

# ─────────────────────────────────────────────────────────────────────
# 12. Edit verb patterns (triggers EDIT_FOLLOWUP)
# ─────────────────────────────────────────────────────────────────────

# (regex pattern for the edit verb/structure, operation type)
_VI_EDIT_VERBS: list[tuple[str, str]] = [
    # ADD TEXT
    (r"(?:thêm|chèn|viết)\s+chữ\b",                 "add_text"),
    (r"add text\b",                                   "add_text"),
    # ADD
    (r"(?:thêm|bổ sung|cho thêm|vẽ thêm|đặt|gắn)\s+(?!chữ)", "add"),
    (r"^add\s+(?!text)",                              "add"),
    (r"^put\s+.+\s+(?:in|on)\b",                     "add"),
    # REMOVE
    (r"(?:bỏ|xóa|loại bỏ|loại|cắt bỏ|gỡ bỏ|xóa bỏ)\s+(?:cái\s+|con\s+|chiếc\s+)?", "remove"),
    (r"^(?:remove|delete|erase)\s+(?:the\s+)?",      "remove"),
    # CHANGE (with new value)
    (r"(?:đổi|thay|sửa thành|đổi sang)\s+(?:.+?)\s+(?:thành|sang)\s+", "change"),
    (r"(?:thay|replace)\s+(?:.+?)\s+(?:bằng|with)\s+", "replace"),
    (r"(?:change|make)\s+(?:the\s+)?(?:.+?)\s+(?:to|into)\s+", "change"),
    # MODIFY (intensity / comparative)
    (r"làm\s+(?:.+?)\s+(?:tối|sáng|lớn|nhỏ|mờ|rõ|to|bé)\s+hơn", "modify"),
    (r"(?:tối hơn|sáng hơn|to hơn|nhỏ hơn|mờ hơn|rõ hơn|brighter|darker|bigger|smaller)\s*$", "modify_general"),
    (r"(?:make (?:it |)?(?:darker|lighter|brighter|bigger|smaller|softer))", "modify_general"),
    # KEEP (consistency with change)
    (r"giữ\s+(?:nhân vật|người|character|subject).+(?:nhưng|but)", "keep_then_change"),
    (r"(?:keep|maintain)\s+(?:the\s+)?(?:character|subject|person).+(?:but|however)", "keep_then_change"),
]

_EN_EDIT_VERBS = _VI_EDIT_VERBS  # already mixed in the list above

# ─────────────────────────────────────────────────────────────────────
# 13. Consistency / accuracy flags
# ─────────────────────────────────────────────────────────────────────

_CONSISTENCY_PATTERNS = [
    r"giữ (?:nhân vật|người|character|subject)\s*(?:cũ|như cũ|giống cũ)?",
    r"giữ nguyên (?:nhân vật|người|subject|character)",
    r"nhân vật (?:cũ|giống|như cũ|như trước)",
    r"vẫn giữ (?:nhân vật|người)",
    r"y như cũ",
    r"(?:keep|maintain|preserve)\s+(?:the\s+)?(?:same\s+)?(?:character|subject|person|protagonist)",
    r"same character",
    r"consistent .+(?:character|subject)",
]

_REAL_ACCURACY_PATTERNS = [
    r"trông như thật",
    r"như ảnh thật",
    r"trông giống thật",
    r"chân thực",
    r"hyper.?realistic",
    r"photo.?realistic",
    r"như chụp",
    r"realistic photo",
    r"real.?world",
]

# ─────────────────────────────────────────────────────────────────────
# 14. Text-in-image patterns
# ─────────────────────────────────────────────────────────────────────

_TEXT_IN_IMAGE_PATTERNS = [
    r"(?:thêm|vẽ|chèn|viết|đặt)\s+chữ\b",
    r"add\s+text\b",
    r"typography",
    r"text overlay",
    r"dòng chữ",
    r"banner\s+chữ",
    r"watermark",
]

# ─────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────

def _translate_target(raw: str) -> str:
    """Map a raw Vietnamese target word to English."""
    lower = raw.lower().strip()
    for pattern, en in _VI_TARGET_EN:
        if re.search(pattern, lower):
            return re.sub(pattern, en, lower, count=1).strip()
    return lower   # unchanged (may already be English)


def _translate_value(raw: str) -> str:
    """Map a raw Vietnamese new-value phrase to English."""
    lower = raw.lower().strip()
    for pattern, en in _VI_VALUE_EN:
        if re.search(pattern, lower):
            return en
    return lower


def _resolve_environment_from_value(raw: str) -> str:
    """Convert a background change value to a full environment string."""
    return _translate_value(raw)


# ─────────────────────────────────────────────────────────────────────
# ScenePlanner
# ─────────────────────────────────────────────────────────────────────

class ScenePlanner:
    """
    Deterministic, rule-based scene planner.

    Primary entry points::

        plan_result = planner.classify_and_plan(message, language="vi")
        # plan_result.scene      → SceneSpec
        # plan_result.classification → PlanClassification
        # plan_result.edit_ops   → list[EditOperation]

        # Backward-compatible convenience wrapper:
        scene = planner.plan(message, intent, language)
    """

    # ── Public: classify only ─────────────────────────────────────────

    def classify(
        self,
        message:           str,
        has_previous_image: bool = False,
        language:          str  = "vi",
    ) -> PlanClassification:
        """
        Classify the user message as GENERATE, EDIT_FOLLOWUP, or UNCERTAIN.

        Algorithm (in priority order):
        1. Any VI/EN edit verb pattern → EDIT_FOLLOWUP
        2. Any VI/EN generate verb → GENERATE
        3. Long message (>8 words), no edit signal → GENERATE
        4. Short message (≤6 words) + has_previous_image → EDIT_FOLLOWUP
        5. Otherwise → UNCERTAIN
        """
        lower = message.lower().strip()

        # Priority 1: edit verb present
        for pattern, _ in _VI_EDIT_VERBS:
            if re.search(pattern, lower, re.IGNORECASE):
                return PlanClassification.EDIT_FOLLOWUP

        # Priority 2: generate verb present
        for p in _VI_GENERATE_VERBS + _EN_GENERATE_VERBS:
            if re.search(p, lower, re.IGNORECASE):
                return PlanClassification.GENERATE

        # Priority 3: long descriptive message → likely GENERATE
        if len(lower.split()) > 8:
            return PlanClassification.GENERATE

        # Priority 4: short + context (previous image exists) → likely edit
        if has_previous_image and len(lower.split()) <= 6:
            return PlanClassification.EDIT_FOLLOWUP

        # Priority 5: medium-length phrase with no verb → GENERATE (default)
        if len(lower.split()) >= 3:
            return PlanClassification.GENERATE

        return PlanClassification.UNCERTAIN

    # ── Public: combined classify + plan ──────────────────────────────

    def classify_and_plan(
        self,
        message:            str,
        language:           str        = "vi",
        has_previous_image: bool       = False,
        previous_scene:     Optional[SceneSpec] = None,
        style_override:     Optional[str] = None,
        quality_override:   Optional[str] = None,
    ) -> PlanResult:
        """
        Classify the message and produce a fully structured SceneSpec.

        Returns PlanResult with .classification, .scene, .edit_ops, .confidence.
        """
        classification = self.classify(message, has_previous_image, language)
        lower          = message.lower().strip()

        is_edit = classification == PlanClassification.EDIT_FOLLOWUP

        # Parse edit operations first (needed to mutate scene for edits)
        edit_ops = self._detect_edit_ops(message, lower) if is_edit else []

        # Build base scene
        if is_edit and previous_scene is not None:
            # Delegate to the standalone merge function
            scene = merge_scene_delta(
                base_scene = previous_scene,
                message    = message,
                edit_ops   = edit_ops,
                language   = language,
            )
            # Apply style/quality overrides that merge_scene_delta doesn't handle
            if style_override:
                scene = dc_replace(scene, style=style_override)
            if quality_override:
                scene = dc_replace(scene, quality_preset=quality_override)
        else:
            scene = SceneSpec(edit_operations=edit_ops)
            # Extract all fields
            scene = self._fill_scene(scene, message, lower, language, is_edit,
                                      style_override, quality_override)

        # Confidence heuristic
        confidence = self._estimate_confidence(message, classification, edit_ops)

        return PlanResult(
            classification = classification,
            scene          = scene,
            edit_ops       = edit_ops,
            confidence     = confidence,
            debug_info     = {"lower": lower, "word_count": len(lower.split())},
        )

    # ── Public: backward-compatible plan() ───────────────────────────

    def plan(
        self,
        message:          str,
        intent:           ImageIntent,
        language:         str = "vi",
        previous_scene:   Optional[SceneSpec] = None,
        style_override:   Optional[str] = None,
        quality_override: Optional[str] = None,
    ) -> SceneSpec:
        """
        Original API — delegates to classify_and_plan().
        Intent is used to decide 'is this an edit?' when the message is ambiguous.
        """
        is_edit_intent = intent in (ImageIntent.EDIT, ImageIntent.FOLLOWUP_EDIT)
        result = self.classify_and_plan(
            message            = message,
            language           = language,
            has_previous_image = is_edit_intent or (previous_scene is not None),
            previous_scene     = previous_scene,
            style_override     = style_override,
            quality_override   = quality_override,
        )
        return result.scene

    # ── Internal: fill all SceneSpec fields from message ─────────────

    def _fill_scene(
        self,
        scene:           SceneSpec,
        message:         str,
        lower:           str,
        language:        str,
        is_edit:         bool,
        style_override:  Optional[str],
        quality_override: Optional[str],
    ) -> SceneSpec:
        """Fill all extractable fields from the raw message."""

        # Subject (skip for pure edit follow-ups like "tối hơn")
        subj = self._extract_subject(message, lower, language, is_edit)
        if subj:
            scene = dc_replace(scene, subject=subj)

        # Subject attributes (additive for edits)
        attrs = self._extract_subject_attributes(lower)
        if attrs:
            merged = list(dict.fromkeys(list(scene.subject_attributes) + attrs))
            scene = dc_replace(scene, subject_attributes=merged)

        # Action
        action = self._extract_action(lower)
        if action and not scene.action:
            scene = dc_replace(scene, action=action)

        # Background / environment
        bg = self._extract_environment(lower)
        if bg:
            scene = dc_replace(scene, background=bg)

        # Lighting (override only if message explicitly mentions lighting)
        lt = self._extract_lighting(lower)
        if lt:
            scene = dc_replace(scene, lighting=lt)

        # Mood
        md = self._extract_mood(lower)
        if md:
            scene = dc_replace(scene, mood=md)

        # Style
        style = style_override or self._extract_style(lower)
        if style:
            scene = dc_replace(scene, style=style)

        # Quality
        quality = quality_override or self._extract_quality(lower)
        if quality:
            scene = dc_replace(scene, quality_preset=quality)

        # Aspect / dimensions
        aspect = self._extract_aspect(lower)
        w, h   = _DIMS[aspect]
        scene  = dc_replace(scene, aspect_ratio=aspect, width=w, height=h)

        # Composition
        comp = self._extract_composition(lower)
        if comp:
            scene = dc_replace(scene, composition=comp)

        # Camera
        cam = self._extract_camera(lower)
        if cam:
            scene = dc_replace(scene, camera=cam)

        # Seed
        seed = self._extract_seed(lower)
        if seed is not None:
            scene = dc_replace(scene, seed=seed)

        # Boolean flags
        wants_text    = self._check_wants_text(lower)
        wants_consist = self._check_wants_consistency(lower)
        wants_real    = self._check_wants_real_accuracy(lower)
        scene = dc_replace(
            scene,
            wants_text_in_image             = wants_text  or scene.wants_text_in_image,
            wants_consistency_with_previous = wants_consist or scene.wants_consistency_with_previous,
            wants_real_world_accuracy       = wants_real   or scene.wants_real_world_accuracy,
        )

        # Style override for real-accuracy requests
        if scene.wants_real_world_accuracy and not scene.style:
            scene = dc_replace(scene, style="photorealistic")

        # Negative hints from style conflicts
        neg = self._extract_negative_hints(lower, scene.style)
        if neg:
            merged_neg = list(dict.fromkeys(list(scene.negative_hints) + neg))
            scene = dc_replace(scene, negative_hints=merged_neg)

        return scene

    # ── Internal: edit operation detection ───────────────────────────

    def _detect_edit_ops(self, message: str, lower: str) -> list[EditOperation]:
        """
        Parse edit verbs in the message into a list of EditOperation objects.
        Returns an empty list if none found.
        """
        ops: list[EditOperation] = []

        # ── Keep + change (consistency): "giữ nhân vật cũ nhưng đổi nền" ──
        keep_change = re.search(
            r"(?:giữ|keep|maintain)\s+(nhân vật|người|character|subject)[^,\n]*?"
            r"(?:nhưng|but|tuy nhiên|however)\s+(?:đổi|change|thay đổi|replace)?\s*(?P<target>[^,\n]{1,40})",
            lower, re.IGNORECASE,
        )
        if keep_change:
            ops.append(EditOperation("keep", "character", raw_target="character"))
            raw_t = keep_change.group("target").strip()
            t_en  = _translate_target(raw_t)
            new_v = _resolve_environment_from_value(raw_t)
            ops.append(EditOperation("change", t_en, new_value=new_v, raw_target=raw_t))
            return ops  # enough context; don't double-parse

        # ── Add text: "thêm chữ SALE 50%" ──────────────────────────────
        add_text = re.search(
            r"(?:thêm|chèn|viết|add)\s+chữ\s+(?P<text>.{1,80})$",
            lower, re.IGNORECASE,
        )
        if add_text:
            text_val = message[add_text.start("text"):add_text.end("text")].strip()
            ops.append(EditOperation("add_text", text_val, raw_target=text_val))
            return ops

        # ── Change with new value: "đổi tóc thành trắng" ─────────────
        change_m = re.search(
            r"(?:đổi|thay|sửa|change|make)\s+(?P<target>[^,\n]{1,30}?)\s+"
            r"(?:thành|sang|to|into)\s+(?:màu\s+)?(?P<value>[^,\n]{1,40})$",
            lower, re.IGNORECASE,
        )
        if change_m:
            t_en  = _translate_target(change_m.group("target"))
            v_en  = _translate_value(change_m.group("value"))
            ops.append(EditOperation(
                "change", t_en, new_value=v_en,
                raw_target=change_m.group("target"),
            ))
            return ops

        # ── Replace: "thay X bằng Y" ──────────────────────────────────
        replace_m = re.search(
            r"(?:thay|replace)\s+(?P<target>[^,\n]{1,30}?)\s+(?:bằng|with)\s+(?P<value>[^,\n]{1,40})$",
            lower, re.IGNORECASE,
        )
        if replace_m:
            t_en = _translate_target(replace_m.group("target"))
            v_en = _translate_value(replace_m.group("value"))
            ops.append(EditOperation("replace", t_en, new_value=v_en, raw_target=replace_m.group("target")))
            return ops

        # ── Modify intensity: "làm trời tối hơn" ──────────────────────
        modify_m = re.search(
            r"l[àa]m\s+(?P<target>[^,\n]{1,30}?)\s+(?P<mod>tối|sáng|lớn|nhỏ|to|bé|mờ|rõ|nhanh|chậm)\s+hơn",
            lower, re.IGNORECASE,
        )
        if modify_m:
            t_en = _translate_target(modify_m.group("target"))
            mod  = modify_m.group("mod")
            modifier_en = {
                "tối": "darker", "sáng": "brighter", "lớn": "larger",
                "nhỏ": "smaller", "to": "larger", "bé": "smaller",
                "mờ": "softer/blurrier", "rõ": "sharper",
                "nhanh": "faster", "chậm": "slower",
            }.get(mod, mod)
            ops.append(EditOperation("modify", t_en, modifier=modifier_en, raw_target=modify_m.group("target")))
            return ops

        # ── Standalone modifier: "tối hơn", "sáng hơn" ────────────────
        standalone = re.search(
            r"^(?P<mod>tối hơn|sáng hơn|to hơn|nhỏ hơn|mờ hơn|rõ hơn|"
            r"brighter|darker|bigger|smaller|softer|sharper)\s*$",
            lower, re.IGNORECASE,
        )
        if standalone:
            mod = standalone.group("mod").lower()
            modifier_en = {
                "tối hơn": "darker", "sáng hơn": "brighter", "to hơn": "larger",
                "nhỏ hơn": "smaller", "mờ hơn": "softer", "rõ hơn": "sharper",
            }.get(mod, mod)
            ops.append(EditOperation("modify_general", "lighting/atmosphere", modifier=modifier_en))
            return ops

        # ── Remove: "bỏ cái mũ" ────────────────────────────────────────
        remove_m = re.search(
            r"(?:bỏ|xóa|loại bỏ|loại|cắt bỏ|gỡ|remove|delete|erase)\s+"
            r"(?:cái\s+|con\s+|chiếc\s+|những\s+)?(?P<target>[^,\n]{1,40}?)(?:\s+đi\s*)?$",
            lower, re.IGNORECASE,
        )
        if remove_m:
            raw_t = remove_m.group("target").strip()
            t_en  = _translate_target(raw_t)
            ops.append(EditOperation("remove", t_en, raw_target=raw_t))
            return ops

        # ── Add item: "thêm kính" ──────────────────────────────────────
        add_m = re.search(
            r"(?:thêm|bổ sung|cho thêm|vẽ thêm|đặt|add|put)\s+"
            r"(?P<target>[^,\n]{1,40})$",
            lower, re.IGNORECASE,
        )
        if add_m:
            raw_t = add_m.group("target").strip()
            # Strip common trailing Vietnamese filler phrases
            raw_t = re.sub(
                r"\s+(?:cho\s+(?:nhân vật|nó|cô|anh|người)|vào|lên|xuống|ra)\s*$",
                "", raw_t, flags=re.IGNORECASE,
            ).strip()
            t_en  = _translate_target(raw_t)
            ops.append(EditOperation("add", t_en, raw_target=raw_t))
            return ops

        return ops

    # ── Internal: apply edit ops to mutate scene fields ───────────────

    def _apply_edit_ops(self, scene: SceneSpec, ops: list[EditOperation]) -> SceneSpec:
        """
        Apply parsed edit operations to the scene, overriding fields appropriately.
        """
        attrs  = list(scene.subject_attributes)
        extra  = list(scene.extra_tags)
        neg    = list(scene.negative_hints)
        fields: dict = {}

        for op in ops:
            # ── add_text ──────────────────────────────────────────────
            if op.operation == "add_text":
                fields["wants_text_in_image"] = True
                if op.target:
                    extra.append(f"text overlay: '{op.target}'")

            # ── add ───────────────────────────────────────────────────
            elif op.operation == "add":
                t = op.target or ""
                if _is_appearance(t):
                    attrs.append(t)
                else:
                    extra.append(t)
                # Remove from negative if previously blocked
                neg = [n for n in neg if t.lower() not in n.lower()]

            # ── remove ────────────────────────────────────────────────
            elif op.operation == "remove":
                t = op.target or ""
                attrs  = [a for a in attrs  if t.lower() not in a.lower()]
                extra  = [e for e in extra  if t.lower() not in e.lower()]
                neg.append(f"no {t}, without {t}")

            # ── change / replace ──────────────────────────────────────
            elif op.operation in ("change", "replace"):
                t     = op.target or ""
                v     = op.new_value or ""
                raw_t = op.raw_target or t

                if _is_hair_target(raw_t):
                    # Remove all existing hair-color attributes, add new one
                    attrs = [a for a in attrs if "hair" not in a.lower() or
                             any(c in a.lower() for c in ["ears", "style"])]
                    if v:
                        attrs.append(f"{v} hair" if "hair" not in v else v)

                elif _is_background_target(raw_t):
                    fields["background"] = v or t

                elif _is_eye_target(raw_t):
                    attrs = [a for a in attrs if "eyes" not in a.lower()]
                    if v:
                        attrs.append(f"{v} eyes" if "eyes" not in v else v)

                else:
                    # Generic attribute change
                    attrs = [a for a in attrs if raw_t.lower() not in a.lower()
                             and t.lower() not in a.lower()]
                    if v:
                        attrs.append(v)

            # ── modify ────────────────────────────────────────────────
            elif op.operation == "modify":
                t        = op.target or ""
                modifier = op.modifier or ""

                if _is_lighting_target(t) or _is_sky_target(t):
                    existing = scene.lighting or ""
                    if "darker" in modifier or "lower" in modifier:
                        fields["lighting"] = (existing + ", dramatic shadows, low-key" if existing
                                              else "darker atmosphere, dramatic shadows, low-key lighting")
                    elif "brighter" in modifier or "lighter" in modifier:
                        fields["lighting"] = (existing + ", bright natural light" if existing
                                              else "bright natural light, high-key lighting")
                    elif "softer" in modifier:
                        fields["lighting"] = (existing + ", soft diffused light" if existing
                                              else "soft diffused lighting")
                    else:
                        fields["lighting"] = f"{existing}, {modifier}".strip(", ")
                else:
                    extra.append(f"{t} {modifier}".strip())

            # ── modify_general ────────────────────────────────────────
            elif op.operation == "modify_general":
                modifier = op.modifier or ""
                existing = scene.lighting or ""
                if "darker" in modifier:
                    fields["lighting"] = (existing + ", darker atmosphere, low-key" if existing
                                          else "darker atmosphere, dramatic shadows")
                elif "brighter" in modifier or "lighter" in modifier:
                    fields["lighting"] = (existing + ", brighter" if existing
                                          else "bright natural light")
                else:
                    extra.append(modifier)

        return dc_replace(
            scene,
            subject_attributes = list(dict.fromkeys(attrs)),
            extra_tags         = list(dict.fromkeys(extra)),
            negative_hints     = neg,
            **fields,
        )

    # ── Internal: individual field extractors ─────────────────────────

    def _extract_subject(self, message: str, lower: str, language: str, is_edit: bool) -> str:
        """Strip generation verbs; return empty string for pure edit commands."""
        if is_edit:
            # Only meaningful for "keep X but change Y" type messages
            keep_m = re.search(
                r"giữ\s+(?P<subj>nhân vật\S*|người\S*|character\S*)", lower
            )
            return keep_m.group("subj").strip() if keep_m else ""

        vi_verbs = [
            r"^vẽ\s+(?:một |một bức |bức )?", r"^tạo ảnh\s+", r"^tạo hình\s+",
            r"^sinh ảnh\s+", r"^gen ảnh\s+", r"^tạo (?:một |bức )?",
            r"^minh họa\s+", r"^thiết kế\s+", r"^làm ảnh\s+", r"^chụp\s+",
            r"^phác thảo\s+", r"^tưởng tượng\s+", r"^render\s+",
        ]
        en_verbs = [
            r"^draw\s+(?:me\s+)?(?:a\s+|an\s+)?", r"^paint\s+(?:me\s+)?(?:a\s+|an\s+)?",
            r"^generate\s+(?:me\s+)?(?:an?\s+)?(?:image\s+(?:of\s+)?)?",
            r"^create\s+(?:me\s+)?(?:an?\s+)?(?:image\s+of\s+)?",
            r"^make\s+(?:me\s+)?(?:an?\s+)?(?:image\s+of\s+)?",
            r"^design\s+", r"^illustrate\s+", r"^render\s+",
            r"^visualize\s+", r"^show\s+me\s+(?:a\s+|an\s+)?", r"^sketch\s+",
        ]
        patterns = vi_verbs if language.startswith("vi") else en_verbs
        subject = message
        for p in patterns:
            reduced = re.sub(p, "", subject, flags=re.IGNORECASE).strip()
            if reduced != subject:
                subject = reduced
                break
        return subject[:140]

    def _extract_subject_attributes(self, lower: str) -> list[str]:
        """Return a list of English visual attribute strings detected in the message."""
        found: list[str] = []
        for pattern, en_attr in _ATTRIBUTE_PATTERNS:
            if re.search(pattern, lower, re.IGNORECASE):
                found.append(en_attr)
        return list(dict.fromkeys(found))  # dedupe while preserving order

    def _extract_action(self, lower: str) -> str:
        actions = [
            (r"ngồi\s+(?:trên|cạnh|dưới|bên|ở)",  "sitting"),
            (r"đứng\s+(?:trên|cạnh|bên|ở|trong)",  "standing"),
            (r"\bchạy\b",                           "running"),
            (r"\bbay\b",                            "flying"),
            (r"chiến đấu|đang đánh",               "fighting"),
            (r"nhảy\b|leap",                       "jumping"),
            (r"nhìn ra|gazing|staring",            "gazing into the distance"),
            (r"cưỡi|riding",                       "riding"),
            (r"bơi|swimming",                      "swimming"),
            (r"leo\b|climbing",                    "climbing"),
        ]
        for pattern, value in actions:
            if re.search(pattern, lower, re.IGNORECASE):
                return value
        return ""

    def _extract_environment(self, lower: str) -> str:
        for pattern, value in _ENVIRONMENT:
            if re.search(pattern, lower, re.IGNORECASE):
                return value
        return ""

    def _extract_lighting(self, lower: str) -> str:
        for pattern, value in _LIGHTING:
            if re.search(pattern, lower, re.IGNORECASE):
                return value
        return ""

    def _extract_mood(self, lower: str) -> str:
        for pattern, value in _MOOD:
            if re.search(pattern, lower, re.IGNORECASE):
                return value
        return ""

    def _extract_style(self, lower: str) -> Optional[str]:
        for style_name, keywords in _STYLE_KEYWORDS.items():
            if any(kw in lower for kw in keywords):
                return style_name
        return None

    def _extract_quality(self, lower: str) -> str:
        for preset, keywords in _QUALITY_MAP.items():
            if any(kw in lower for kw in keywords):
                return preset
        return "auto"

    def _extract_aspect(self, lower: str) -> str:
        if any(h in lower for h in _WIDE_HINTS):
            return "wide"
        if any(h in lower for h in _LANDSCAPE_HINTS):
            return "landscape"
        if any(h in lower for h in _PORTRAIT_HINTS):
            return "portrait"
        return "square"

    def _extract_composition(self, lower: str) -> str:
        for pattern, value in _COMPOSITION:
            if re.search(pattern, lower, re.IGNORECASE):
                return value
        return ""

    def _extract_camera(self, lower: str) -> str:
        for pattern, value in _CAMERA:
            if re.search(pattern, lower, re.IGNORECASE):
                return value
        return ""

    def _extract_seed(self, lower: str) -> Optional[int]:
        m = re.search(r"seed\s*[=:]\s*(\d+)", lower)
        return int(m.group(1)) if m else None

    def _check_wants_text(self, lower: str) -> bool:
        return any(re.search(p, lower, re.IGNORECASE) for p in _TEXT_IN_IMAGE_PATTERNS)

    def _check_wants_consistency(self, lower: str) -> bool:
        return any(re.search(p, lower, re.IGNORECASE) for p in _CONSISTENCY_PATTERNS)

    def _check_wants_real_accuracy(self, lower: str) -> bool:
        return any(re.search(p, lower, re.IGNORECASE) for p in _REAL_ACCURACY_PATTERNS)

    def _extract_negative_hints(self, lower: str, style: Optional[str]) -> list[str]:
        hints: list[str] = []
        if style == "anime":
            hints.extend(["realistic photography", "photorealistic", "3d render"])
        elif style == "photorealistic":
            hints.extend(["cartoon", "anime", "painting", "illustration", "sketch"])
        elif style == "sketch":
            hints.extend(["color", "painted", "photorealistic"])
        return hints

    def _estimate_confidence(
        self,
        message:        str,
        classification: PlanClassification,
        edit_ops:       list[EditOperation],
    ) -> float:
        """Rough confidence score for the classification decision."""
        lower = message.lower().strip()
        words = len(lower.split())

        if classification == PlanClassification.EDIT_FOLLOWUP and edit_ops:
            return 0.95
        if classification == PlanClassification.GENERATE and words > 6:
            return 0.90
        if classification == PlanClassification.UNCERTAIN:
            return 0.40
        return 0.75


# ─────────────────────────────────────────────────────────────────────
# Target classification helpers (used in _apply_edit_ops)
# ─────────────────────────────────────────────────────────────────────

def _is_hair_target(raw: str) -> bool:
    return bool(re.search(r"tóc|hair", raw, re.IGNORECASE))

def _is_eye_target(raw: str) -> bool:
    return bool(re.search(r"mắt|eyes?", raw, re.IGNORECASE))

def _is_background_target(raw: str) -> bool:
    return bool(re.search(r"nền|phông|background|bầu trời|sky(?:\s+not)?\b", raw, re.IGNORECASE))

def _is_lighting_target(raw: str) -> bool:
    return bool(re.search(r"ánh sáng|đèn|lighting|light(?:ing)?", raw, re.IGNORECASE))

def _is_sky_target(raw: str) -> bool:
    return bool(re.search(r"trời|bầu trời|sky|clouds?|mây", raw, re.IGNORECASE))

def _is_appearance(attr: str) -> bool:
    """Return True if attr is a visual property of the subject (va. location/prop)."""
    return bool(re.search(
        r"hair|eyes?|skin|dress|armor|jacket|glasses|hat|wings|tail|ears|"
        r"expression|smiling|crying|uniform|crown|scarf|sword|gun",
        attr, re.IGNORECASE,
    ))


# ─────────────────────────────────────────────────────────────────────
# Public: merge_scene_delta
# ─────────────────────────────────────────────────────────────────────

def merge_scene_delta(
    base_scene:     SceneSpec,
    message:        str,
    edit_ops:       list[EditOperation],
    language:       str = "vi",
) -> SceneSpec:
    """
    Merge an edit request into an existing scene, returning the updated scene.

    The *base_scene* is copied (immutable input), then:
      1. Deep-copy mutable list fields to prevent aliasing.
      2. Extract any new field values from *message* (additive only).
      3. Apply each *edit_op* (change, add, remove, modify, etc.).

    This is the authoritative "delta merge" function.  The orchestrator
    calls it on every follow-up turn so the previous image context is
    never lost.

    Parameters
    ----------
    base_scene : SceneSpec
        The scene from the previous turn (stored in session memory).
    message : str
        The current user message (raw Vietnamese or English).
    edit_ops : list[EditOperation]
        Parsed edit commands from ScenePlanner._detect_edit_ops().
    language : str
        "vi" or "en".

    Returns
    -------
    SceneSpec
        A new SceneSpec with the delta applied.
    """
    planner = ScenePlanner()
    lower   = message.lower().strip()

    # 1. Deep-copy base scene with edit defaults
    merged = dc_replace(
        base_scene,
        strength                        = 0.65,
        wants_consistency_with_previous = any(
            op.operation == "keep" for op in edit_ops
        ) or base_scene.wants_consistency_with_previous,
        extra_tags         = list(base_scene.extra_tags),
        negative_hints     = list(base_scene.negative_hints),
        subject_attributes = list(base_scene.subject_attributes),
        edit_operations    = list(edit_ops),
    )

    # 2. Additive fill from message (only overrides fields the message mentions)
    merged = planner._fill_scene(
        merged, message, lower, language,
        is_edit=True, style_override=None, quality_override=None,
    )

    # 3. Apply edit operations (change hair, background, lighting, etc.)
    if edit_ops:
        merged = planner._apply_edit_ops(merged, edit_ops)

    return merged
