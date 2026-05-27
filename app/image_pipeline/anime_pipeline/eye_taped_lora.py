"""Eye-taped LoRA stack — Layer 4 sub-effect.

User spec (2026-04-23):
  "Chinh workflow cho 3 cai nay:
     - eyetaped_v0.safetensors
     - klee eye taped.safetensors
     - taped_eyesV01.safetensors
   strenght dua theo lora do CUC CAO
   ket hop voi cac text tu nhien lien quan den ngu mo mat co bloodshot"

Behaviour:
  * Detect intent from the user prompt (Vietnamese + English keyword
    set covering "eyes taped open", "eye tape", "bang dinh mat",
    "sleep open eye", "ngu mo mat", "forced open eyes", etc.).
  * When triggered, return a high-strength LoRA stack:
      - eyetaped_v0            @ 1.00 / 0.90
      - taped_eyesV01          @ 1.00 / 0.90
      - klee_eye_taped         @ 1.00 / 0.90  (only when character is Klee)
  * Pair the stack with a natural-language prompt fragment describing
    a sleep-deprived gaze with eyes pried open by tape and visible
    bloodshot veins.
  * Negative prompt clears closed-eye / sleeping-with-eyes-shut
    contradictions that would fight the LoRA at high weight.

The module is OPT-IN and PURE — no I/O, no global state — so it is
safe to call from inpaint passes, layer painters, and tests.
"""

from __future__ import annotations

import re
from typing import Any, Optional

# ── LoRA stack (strength values come straight from the user spec
#    "strenght dua theo lora do CUC CAO" — these LoRAs were trained at
#    full weight by their authors, so we honour that) ──────────────────

# Generic "eye taped open" pair — applies to ANY character.
_GENERIC_LORAS: tuple[dict[str, Any], ...] = (
    {
        "name": "effects/eyetaped_v0.safetensors",
        "strength_model": 1.00,
        "strength_clip": 0.90,
    },
    {
        "name": "effects/taped_eyesV01.safetensors",
        "strength_model": 1.00,
        "strength_clip": 0.90,
    },
)

# Character-locked LoRA — only loaded when the character matches.
_KLEE_LORA: dict[str, Any] = {
    "name": "effects/klee_eye_taped.safetensors",
    "strength_model": 1.00,
    "strength_clip": 0.90,
}

_KLEE_TOKENS: frozenset[str] = frozenset(
    {
        "klee",
        "klee (genshin impact)",
        "klee_(genshin_impact)",
    }
)


# ── Intent detection ────────────────────────────────────────────────

_EYE_TAPED_PATTERNS: tuple[re.Pattern[str], ...] = tuple(
    re.compile(p, re.IGNORECASE)
    for p in (
        # English
        r"\beye(?:s)?\s*tap(?:e|ed|ing)\b",
        r"\btap(?:e|ed|ing)\s+eye(?:s)?\b",
        r"\beye(?:lid)?s?\s+tap(?:e|ed)\s+(?:open|shut)\b",
        # "forced (eyes|eyelids) open" OR "forced open eyes"
        r"\bforc(?:e|ed|ing)\s+(?:eye(?:lid)?s?|open)\s+\w*\s*(?:open|eye(?:lid)?s?)\b",
        r"\bsleep(?:ing)?\s+with\s+eye(?:s)?\s+(?:open|taped)\b",
        r"\beye(?:s)?\s+(?:held|pried|propped)\s+open\b",
        # "eyelids pried open with medical tape" — combine pried+tape anywhere
        r"\bmedical\s+tape\b.*\beye",
        r"\beye.*\bmedical\s+tape\b",
        r"\b(?:pried|propped|held)\s+open\b.*\btape\b",
        # Vietnamese (no diacritics; users frequently type without them)
        r"\bb(?:a|ă)ng\s*d(?:i|í)nh\s*m(?:a|ắ)t\b",
        r"\bd(?:a|á)n\s*b(?:a|ă)ng\s*m(?:a|ắ)t\b",
        r"\bd(?:a|á)n\s*m(?:a|ắ)t\s*m(?:o|ở)\b",
        r"\bng(?:u|ủ)\s*m(?:o|ở)\s*m(?:a|ắ)t\b",
        r"\bm(?:a|ắ)t\s*b(?:i|ị)\s*tape\b",
        r"\bm(?:a|ắ)t\s*tape\s*m(?:o|ở)\b",
    )
)


def detect_eye_taped_intent(user_prompt: Optional[str]) -> bool:
    """Return True when the prompt asks for the eye-taped/sleep-open
    look. Pure substring/regex match — no network, safe for hot path."""
    if not user_prompt:
        return False
    text = str(user_prompt).strip()
    if not text:
        return False
    return any(p.search(text) for p in _EYE_TAPED_PATTERNS)


# ── LoRA stack builder ──────────────────────────────────────────────


def _is_klee(character_name: str = "", character_tag: str = "") -> bool:
    haystack = f"{character_name} {character_tag}".strip().lower()
    if not haystack:
        return False
    return any(token in haystack for token in _KLEE_TOKENS)


def build_eye_taped_lora_stack(
    *,
    character_name: str = "",
    character_tag: str = "",
) -> list[dict[str, Any]]:
    """Return the LoRA stack for the eye-taped look.

    Always includes the two generic LoRAs at full strength.  Adds the
    Klee-specific LoRA only when the character matches — loading a
    character-locked LoRA on the wrong subject biases facial features.
    Caller is responsible for filtering against on-disk presence.
    """
    stack: list[dict[str, Any]] = [dict(l) for l in _GENERIC_LORAS]
    if _is_klee(character_name, character_tag):
        stack.append(dict(_KLEE_LORA))
    return stack


# ── Prompt fragments ────────────────────────────────────────────────

# Natural-language fragment describing the look. Phrased as
# comma-separated booru-style tags so it merges cleanly with the
# existing region prompts via DetectionInpaintAgent._merge_prompt().
EYE_TAPED_POSITIVE: str = (
    "eyes taped open, medical tape over eyelids, eyelids pried open with tape, "
    "forced wakefulness, sleep deprived expression, exhausted half-asleep gaze, "
    "drowsy unfocused stare, tired heavy eyebags, "
    "bloodshot eyes, prominent red veins on sclera, irritated red eyes, "
    "watery glassy eyes, dilated pupils, "
    "thousand-yard stare, slumped posture, pale tired skin"
)

# Negative cleanup — at full LoRA strength the model still sometimes
# falls back to closed-eye sleeping; explicitly reject those.
EYE_TAPED_NEGATIVE: str = (
    "closed eyes, eyes closed, sleeping with eyes shut, "
    "eyelids closed, peaceful sleep, restful expression, "
    "clean white sclera, no eye redness"
)
