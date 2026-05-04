"""Focused tests for the rule-based ``extract_prompt_entities`` contract
defined in Prompt 4.7. Exercises the new spec fields:
``raw_character_query``, ``series_slug``, ``residual_prompt``,
``style_hint``, ``negative_identity_guard``, ``multiple_characters``,
``extraction_confidence``, ``extraction_reason``.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import character_understanding as cu  # noqa: E402


# ── 1. Action-tail extraction (the headline case) ────────────────────────────

class TestActionTailExtraction:
    def test_klee_fishing_with_bombs(self):
        """``"klee câu cá bằng bom"`` must NOT pass the whole sentence as
        the character name. ``raw_character_query`` is ``"klee"``,
        ``residual_prompt`` is the Vietnamese tail."""
        ents = cu.extract_prompt_entities("klee câu cá bằng bom")
        assert ents["raw_character_query"] == "klee"
        assert ents["candidate_name_slug"] == "klee"
        assert ents["residual_prompt"] == "câu cá bằng bom"
        assert ents["series_hint"] == ""
        assert ents["series_slug"] == ""
        assert ents["multiple_characters"] is False
        assert ents["style_hint"] == ""

    def test_english_action_tail(self):
        ents = cu.extract_prompt_entities("Klee holding a bomb in a sunny field")
        assert ents["raw_character_query"] == "Klee"
        assert ents["residual_prompt"].startswith("holding")
        assert ents["is_named"] is True


# ── 2. Vietnamese / English connector phrases ────────────────────────────────

class TestConnectorPhrases:
    @pytest.mark.parametrize("prompt,expected_slug,expected_series", [
        ("Iroha trong Kaguya Cosmic Princess mặc váy trắng",
         "iroha", "cosmic_princess_kaguya"),
        ("Hu Tao của Genshin Impact cầm hoa cúc",
         "hu_tao", "genshin_impact"),
        ("nhân vật Sparkle trong Honkai Star Rail",
         "sparkle", "honkai_star_rail"),
        ("Klee from Genshin Impact wearing a red hat",
         "klee", "genshin_impact"),
        ("Sparkle in Honkai Star Rail standing on a rooftop",
         "sparkle", "honkai_star_rail"),
    ])
    def test_connector_pins_series(self, prompt, expected_slug, expected_series):
        ents = cu.extract_prompt_entities(prompt)
        assert ents["candidate_name_slug"] == expected_slug
        assert ents["series_hint"] == expected_series
        assert ents["series_slug"] == expected_series
        assert ents["extraction_confidence"] >= 0.7


# ── 3. Series alias coverage ─────────────────────────────────────────────────

class TestSeriesAliases:
    @pytest.mark.parametrize("phrase,canonical", [
        ("genshin", "genshin_impact"),
        ("genshin impact", "genshin_impact"),
        ("gi", "genshin_impact"),
        ("hsr", "honkai_star_rail"),
        ("honkai star rail", "honkai_star_rail"),
        ("wuwa", "wuthering_waves"),
        ("wuthering waves", "wuthering_waves"),
        ("zzz", "zenless_zone_zero"),
        ("zenless zone zero", "zenless_zone_zero"),
        ("bocchi the rock", "bocchi_the_rock"),
        ("kaguya cosmic princess", "cosmic_princess_kaguya"),
        ("cosmic princess kaguya", "cosmic_princess_kaguya"),
    ])
    def test_series_alias_canonicalizes(self, phrase, canonical):
        ents = cu.extract_prompt_entities(f"Iroha trong {phrase} mặc váy")
        assert ents["series_slug"] == canonical


# ── 4. Protagonist phrases ───────────────────────────────────────────────────

class TestProtagonistPhrases:
    def test_main_nu_zzz(self):
        ents = cu.extract_prompt_entities("nhân vật main nữ trong zzz")
        assert ents["candidate_name_slug"] == "main_female_protagonist"
        assert ents["series_slug"] == "zenless_zone_zero"

    def test_main_nam_genshin(self):
        ents = cu.extract_prompt_entities("nhân vật main nam trong genshin impact")
        assert ents["candidate_name_slug"] == "main_male_protagonist"
        assert ents["series_slug"] == "genshin_impact"

    def test_female_protagonist_english(self):
        ents = cu.extract_prompt_entities("female protagonist from honkai star rail")
        assert ents["candidate_name_slug"] == "main_female_protagonist"
        assert ents["series_slug"] == "honkai_star_rail"


# ── 5. Style hint ────────────────────────────────────────────────────────────

class TestStyleHint:
    def test_phong_cach_demotes_series_to_style(self):
        ents = cu.extract_prompt_entities("vẽ cô gái phong cách Bocchi the Rock")
        assert ents["style_hint"] == "bocchi_the_rock"
        # Series slug is cleared — the prompt is asking for a style, not
        # a character from that franchise.
        assert ents["series_slug"] == ""
        assert ents["candidate_name_slug"] == ""

    def test_kieu_marker(self):
        ents = cu.extract_prompt_entities("một cô gái kiểu Genshin Impact")
        assert ents["style_hint"] == "genshin_impact"
        assert ents["series_slug"] == ""

    def test_english_style_marker(self):
        ents = cu.extract_prompt_entities(
            "a girl in the style of Honkai Star Rail"
        )
        assert ents["style_hint"] == "honkai_star_rail"
        assert ents["series_slug"] == ""

    def test_explicit_alias_character_keeps_series(self):
        # If an explicit known character (alias-table hit) is present
        # AND the prompt mentions style, the character/series stay —
        # only ambiguous "style + no character" prompts get demoted.
        ents = cu.extract_prompt_entities("hutao kiểu watercolor")
        assert ents["candidate_name_slug"] == "hutao"


# ── 6. Negative identity guard ───────────────────────────────────────────────

class TestNegativeIdentityGuard:
    def test_khong_phai_appended(self):
        ents = cu.extract_prompt_entities(
            "Iroha trong Kaguya Cosmic Princess, không phải Kaguya"
        )
        guard_str = " ".join(ents["negative_identity_guard"]).lower()
        assert "kaguya" in guard_str
        # The negation target must NOT become the character.
        assert "kaguya" not in ents["candidate_name_slug"]

    def test_english_not_target(self):
        ents = cu.extract_prompt_entities("not Sparkle, just a fairy")
        guard_str = " ".join(ents["negative_identity_guard"]).lower()
        assert "sparkle" in guard_str

    def test_giong_nhung_khong_phai(self):
        ents = cu.extract_prompt_entities(
            "giống Hu Tao nhưng không phải Hu Tao"
        )
        guard_str = " ".join(ents["negative_identity_guard"]).lower()
        assert "hu tao" in guard_str or "hu" in guard_str


# ── 7. OC marker ─────────────────────────────────────────────────────────────

class TestOriginalCharacterMarker:
    def test_oc_does_not_resolve_known(self):
        ents = cu.extract_prompt_entities("OC tên Luna mặc áo giáp")
        assert ents["is_named"] is False
        assert "OC" in ents["extraction_reason"] or "marker" in ents["extraction_reason"].lower()

    def test_original_character_phrase(self):
        ents = cu.extract_prompt_entities("an original character named Vex wearing armor")
        assert ents["is_named"] is False

    def test_nhan_vat_tu_tao(self):
        ents = cu.extract_prompt_entities("nhân vật tự tạo tên Mira mặc váy đỏ")
        assert ents["is_named"] is False


# ── 8. Multi-character ───────────────────────────────────────────────────────

class TestMultipleCharacters:
    def test_furina_va_nahida(self):
        ents = cu.extract_prompt_entities("Furina và Nahida đi chơi trong vườn")
        assert ents["multiple_characters"] is True
        # Candidate must be ONE of the two, never a merged slug.
        assert ents["candidate_name_slug"] in {"furina", "nahida"}

    def test_english_and_connector(self):
        ents = cu.extract_prompt_entities("Hu Tao and Klee playing in a field")
        assert ents["multiple_characters"] is True

    def test_single_character_is_not_multi(self):
        ents = cu.extract_prompt_entities("Iroha mặc váy trắng")
        assert ents["multiple_characters"] is False


# ── 9. Confidence + reason invariants ────────────────────────────────────────

class TestConfidenceAndReason:
    def test_empty_prompt(self):
        ents = cu.extract_prompt_entities("")
        assert ents["extraction_confidence"] == 0.0
        assert ents["extraction_reason"] == "empty prompt"

    def test_named_with_series(self):
        ents = cu.extract_prompt_entities("Iroha trong Kaguya Cosmic Princess")
        assert ents["extraction_confidence"] >= 0.8

    def test_lowercase_name_low_confidence(self):
        # "klee" is lowercase in the prompt — without a series hint,
        # it must NOT score as a high-confidence proper-noun match.
        ents = cu.extract_prompt_entities("klee câu cá bằng bom")
        assert ents["extraction_confidence"] < 0.7

    def test_generic_scene(self):
        ents = cu.extract_prompt_entities("a cat sitting in a sunny window")
        assert ents["extraction_confidence"] < 0.6
        assert ents["multiple_characters"] is False


# ── 10. Serialization invariant ──────────────────────────────────────────────

class TestSerialization:
    @pytest.mark.parametrize("prompt", [
        "klee câu cá bằng bom",
        "Iroha trong Kaguya Cosmic Princess, không phải Kaguya",
        "vẽ cô gái phong cách Bocchi the Rock",
        "Furina và Nahida đi chơi trong vườn",
        "OC tên Luna mặc áo giáp",
        "nhân vật main nữ trong zzz",
        "",
    ])
    def test_round_trips_json(self, prompt):
        ents = cu.extract_prompt_entities(prompt)
        encoded = json.dumps(ents)
        decoded = json.loads(encoded)
        # All required spec keys present.
        for k in (
            "raw_character_query", "series_hint", "series_slug",
            "residual_prompt", "style_hint", "negative_identity_guard",
            "multiple_characters", "extraction_confidence",
            "extraction_reason",
        ):
            assert k in decoded, f"missing key: {k}"
