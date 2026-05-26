"""Tests for eye-taped Layer-4 LoRA stack and intent detection.

Spec verbatim (2026-04-23):
  "Chinh workflow cho 3 cai nay
   strenght dua theo lora do CUC CAO
   ket hop voi cac text tu nhien lien quan den ngu mo mat co bloodshot"
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from image_pipeline.anime_pipeline.eye_taped_lora import (  # noqa: E402
    EYE_TAPED_NEGATIVE,
    EYE_TAPED_POSITIVE,
    build_eye_taped_lora_stack,
    detect_eye_taped_intent,
)

# ── Intent detection ────────────────────────────────────────────────


@pytest.mark.parametrize(
    "prompt",
    [
        "Klee with eyes taped open",
        "girl, eye tape, sleep deprived",
        "eyelids pried open with medical tape",
        "forced open eyes, exhausted",
        "sleeping with eyes taped",
        "Klee, eyes held open",
        # Vietnamese forms with and without diacritics
        "Klee bang dinh mat",
        "co gai dan bang mat",
        "ngu mo mat",
        "ngủ mở mắt, bloodshot",
        "Klee mắt bị tape",
        "băng dính mắt mở",
    ],
)
def test_detect_intent_positive(prompt):
    assert detect_eye_taped_intent(prompt) is True


@pytest.mark.parametrize(
    "prompt",
    [
        "",
        None,
        "Klee Genshin Impact happy",
        "anime girl smiling",
        "closed eyes peaceful sleep",
        "Klee with eyepatch",  # eyepatch != eye tape
        "tape recorder in background",
        "scotch tape on a box",
    ],
)
def test_detect_intent_negative(prompt):
    assert detect_eye_taped_intent(prompt) is False


# ── Stack builder ───────────────────────────────────────────────────


def test_stack_generic_only_when_not_klee():
    stack = build_eye_taped_lora_stack(
        character_name="Hu Tao", character_tag="hu_tao_(genshin_impact)"
    )
    names = [l["name"] for l in stack]
    assert "effects/eyetaped_v0.safetensors" in names
    assert "effects/taped_eyesV01.safetensors" in names
    assert "effects/klee_eye_taped.safetensors" not in names
    assert len(stack) == 2


def test_stack_includes_klee_lora_for_klee():
    stack = build_eye_taped_lora_stack(
        character_name="Klee", character_tag="klee_(genshin_impact)"
    )
    names = [l["name"] for l in stack]
    assert "effects/klee_eye_taped.safetensors" in names
    assert len(stack) == 3


def test_stack_klee_match_is_case_insensitive():
    stack = build_eye_taped_lora_stack(character_name="KLEE")
    names = [l["name"] for l in stack]
    assert "effects/klee_eye_taped.safetensors" in names


def test_stack_strengths_are_full_high():
    """User spec: 'strenght dua theo lora do CUC CAO'.

    Generic LoRAs must be at >=0.95 model and >=0.85 clip — anything
    lower defeats the point of the eye-tape effect."""
    stack = build_eye_taped_lora_stack(character_name="Klee")
    for lora in stack:
        assert lora["strength_model"] >= 0.95, lora
        assert lora["strength_clip"] >= 0.85, lora


def test_stack_returns_independent_dicts():
    """Caller must be able to mutate the returned stack without
    poisoning the module-level templates."""
    a = build_eye_taped_lora_stack(character_name="Klee")
    a[0]["strength_model"] = 0.0
    b = build_eye_taped_lora_stack(character_name="Klee")
    assert b[0]["strength_model"] >= 0.95


# ── Prompt fragments ────────────────────────────────────────────────


def test_positive_prompt_covers_all_required_themes():
    p = EYE_TAPED_POSITIVE.lower()
    # The user explicitly listed: "ngu mo mat co bloodshot".
    assert "tape" in p
    assert "bloodshot" in p
    assert "sleep" in p or "drowsy" in p or "exhausted" in p
    assert "open" in p


def test_negative_prompt_blocks_closed_eyes():
    n = EYE_TAPED_NEGATIVE.lower()
    assert "closed eyes" in n or "eyes closed" in n
    assert "sleeping with eyes shut" in n or "eyelids closed" in n
