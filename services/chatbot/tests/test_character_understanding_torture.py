"""Torture tests for character identity collision, unknown characters,
low-data profiles, and LoRA-safety after Phase 4.6.

Each test holds the resolver to one invariant: it must NEVER silently
substitute a different character, attach a wrong LoRA, or collapse
multi-character prompts into one mistaken identity. Where exact future
behavior depends on data that may be added later (alias entries, registry
seeds, manual overrides), the tests assert *safety properties* rather
than specific resolved ids.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import character_understanding as cu  # noqa: E402


# ── Helpers (duplicated locally so this file is self-contained) ──────────────

def _empty_registry(monkeypatch):
    stub = MagicMock()
    stub.resolve_query.return_value = None
    stub.detect_collisions.return_value = []
    stub.list_all.return_value = []
    stub.list_series.return_value = []
    monkeypatch.setattr("core.character_registry.get_registry", lambda: stub)
    return stub


def _disable_saa(monkeypatch):
    fake = types.ModuleType("image_pipeline.anime_pipeline.saa_character_db")
    def _boom(*a, **kw):
        raise RuntimeError("SAA not installed in this test")
    fake.lookup_character = _boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules,
                        "image_pipeline.anime_pipeline.saa_character_db", fake)


def _no_overrides(monkeypatch):
    monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    """Default isolation for every test: empty registry, no SAA, no overrides."""
    _empty_registry(monkeypatch)
    _disable_saa(monkeypatch)
    _no_overrides(monkeypatch)


# ── 1. Common-word character names (collision torture) ───────────────────────

class TestCommonWordNames:
    def test_firefly_without_series_hint(self):
        r = cu.resolve_character("firefly trên bầu trời pháo hoa")
        assert r.safe_to_attach_lora is False
        # Must NOT silently resolve to firefly@honkai_star_rail.
        if r.best is not None:
            assert r.best.canonical_id != "firefly@honkai_star_rail"

    def test_firefly_with_hsr_pins_series(self):
        r = cu.resolve_character("firefly hsr trên bầu trời pháo hoa")
        # Must either resolve as firefly@honkai_star_rail OR mark the
        # provisional id with the HSR series — never silently other-series.
        if r.best is not None:
            assert r.best.series_slug == "honkai_star_rail"
        elif r.unknown_profile is not None:
            assert r.unknown_profile.possible_series == "honkai_star_rail"
            assert r.unknown_profile.provisional_id.startswith("unknown:firefly@")

    def test_sparkle_glitter_phrase_does_not_auto_resolve(self):
        # "sparkle lấp lánh trên váy" — the word "sparkle" appears as
        # adjective/decoration. Must NOT auto-resolve to Sparkle HSR.
        r = cu.resolve_character("sparkle lấp lánh trên váy")
        assert r.safe_to_attach_lora is False

    def test_sparkle_with_hsr_hint_resolves(self):
        r = cu.resolve_character("sparkle hsr mặc váy đỏ")
        # Sparkle is in the built-in alias table with both HSR + generic
        # entries; HSR series hint must filter to the HSR entry.
        if r.resolved and r.best is not None:
            assert r.best.series_slug == "honkai_star_rail"
            assert r.best.canonical_id == "sparkle@honkai_star_rail"


# ── 2. Same-name / niche character ───────────────────────────────────────────

class TestNicheCharacter:
    def test_iroha_kaguya_no_override_yields_unknown(self):
        r = cu.resolve_character(
            "Iroha trong Kaguya Cosmic Princess mặc váy trắng"
        )
        assert r.mode == "unresolved_unknown"
        assert r.safe_to_attach_lora is False
        assert r.unknown_profile is not None
        assert r.unknown_profile.provisional_id == "unknown:iroha@cosmic_princess_kaguya"

    def test_iroha_must_not_substitute_known_iroha(self):
        # Even when a different-series Iroha is in the alias table,
        # the series hint must prevent substitution.
        r = cu.resolve_character(
            "Iroha trong Kaguya Cosmic Princess mặc váy trắng"
        )
        if r.best is not None:
            # If anything resolved, it must be in the same series.
            assert r.best.series_slug == "cosmic_princess_kaguya"

    def test_negation_phrase_appended_to_guard(self):
        r = cu.resolve_character(
            "Iroha trong Kaguya Cosmic Princess, không phải Kaguya"
        )
        assert r.unknown_profile is not None
        guard_text = " ; ".join(r.unknown_profile.negative_identity_guard).lower()
        assert "kaguya" in guard_text
        # And Kaguya is never the candidate.
        if r.best is not None:
            assert "kaguya" not in r.best.character_slug


# ── 3. Known-ish game cases ──────────────────────────────────────────────────

class TestKnownGameCases:
    def test_shorekeeper_wuwa_pins_series(self):
        r = cu.resolve_character(
            "shorekeeper wuwa mặc váy trắng trong vườn hoa"
        )
        # Either resolves to shorekeeper@wuthering_waves, or unknown
        # form with that series — never another series.
        if r.best is not None:
            assert r.best.series_slug == "wuthering_waves"
        elif r.unknown_profile is not None:
            assert r.unknown_profile.possible_series == "wuthering_waves"
            assert r.unknown_profile.provisional_id.startswith("unknown:shorekeeper@")

    def test_klee_action_phrase_safe(self):
        # "klee câu cá bằng bom" — lowercase "klee", no series hint,
        # no built-in alias entry for klee. Must remain safe (no LoRA,
        # no other-character substitution).
        r = cu.resolve_character("klee câu cá bằng bom")
        assert r.safe_to_attach_lora is False
        if r.best is not None:
            # If somehow resolved, it must be klee@genshin_impact only.
            assert r.best.character_slug == "klee"

    def test_main_female_protagonist_zzz_phrase(self):
        r = cu.resolve_character(
            "nhân vật main nữ trong zzz đứng bên tường uống nước"
        )
        assert r.safe_to_attach_lora is False
        # Series hint must resolve.
        if r.unknown_profile is not None:
            assert r.unknown_profile.possible_series == "zenless_zone_zero"
            # Protagonist phrase normalizes to a stable canonical form.
            assert r.unknown_profile.provisional_id == (
                "unknown:main_female_protagonist@zenless_zone_zero"
            )


# ── 4. Style vs character ────────────────────────────────────────────────────

class TestStyleVsCharacter:
    def test_style_phrase_does_not_resolve_real_character(self):
        # "vẽ cô gái phong cách Bocchi the Rock" — Bocchi is a STYLE
        # reference, not the character. Must not auto-attach LoRA.
        r = cu.resolve_character("vẽ cô gái phong cách Bocchi the Rock")
        assert r.safe_to_attach_lora is False
        # If anything resolves, it must NOT be a known real character
        # from another franchise being substituted in.
        if r.best is not None:
            assert r.best.source != "saa" or r.best.series_slug == "bocchi_the_rock"

    def test_bocchi_in_bocchi_pins_series(self):
        r = cu.resolve_character("bocchi trong bocchi the rock chơi đàn rock")
        # Either resolves to a Bocchi-the-Rock character OR unknown
        # within that series. Must not be another franchise.
        if r.best is not None:
            assert r.best.series_slug == "bocchi_the_rock"
        elif r.unknown_profile is not None:
            assert r.unknown_profile.possible_series == "bocchi_the_rock"


# ── 5. Original characters ───────────────────────────────────────────────────

class TestOriginalCharacter:
    def test_oc_luna_is_safe(self):
        r = cu.resolve_character("OC tên Luna mặc áo giáp")
        assert r.safe_to_attach_lora is False
        # Luna is shared by many series — must NOT silently pick one.
        if r.best is not None:
            assert "luna" in r.best.character_slug
            # And no LoRA hint.
            assert r.best.lora_hint is None
        elif r.unknown_profile is not None:
            assert r.unknown_profile.provisional_id.startswith("unknown:")


# ── 6. Multi-character ───────────────────────────────────────────────────────

class TestMultiCharacter:
    def test_multi_character_does_not_collapse(self):
        # "Furina và Nahida" — two characters. Resolver must not
        # confidently lock onto one popular character + LoRA.
        r = cu.resolve_character("Furina và Nahida đi chơi trong vườn")
        assert r.safe_to_attach_lora is False
        # And whatever is returned must not be a third unrelated identity.
        if r.best is not None:
            assert r.best.character_slug in {
                "furina", "nahida", "furina_va_nahida_di",
            } or r.best.canonical_id.startswith("unknown:")


# ── 7. LoRA safety invariants (apply across all unsafe modes) ────────────────

class TestLoraSafetyInvariants:
    @pytest.mark.parametrize("query", [
        "firefly trên bầu trời pháo hoa",
        "sparkle lấp lánh trên váy",
        "Iroha trong Kaguya Cosmic Princess",
        "OC tên Luna mặc áo giáp",
        "Furina và Nahida đi chơi trong vườn",
        "vẽ cô gái phong cách Bocchi the Rock",
    ])
    def test_unsafe_modes_never_attach_lora(self, query):
        r = cu.resolve_character(query)
        assert r.safe_to_attach_lora is False
        for cand in r.candidates:
            assert cand.lora_hint is None, (
                f"unsafe candidate {cand.canonical_id} carries lora_hint"
            )


# ── 8. Serialization invariants ──────────────────────────────────────────────

class TestSerializationTorture:
    @pytest.mark.parametrize("query", [
        "firefly hsr trên bầu trời pháo hoa",
        "sparkle hsr mặc váy đỏ",
        "Iroha trong Kaguya Cosmic Princess, không phải Kaguya",
        "shorekeeper wuwa mặc váy trắng trong vườn hoa",
        "nhân vật main nữ trong zzz đứng bên tường uống nước",
        "vẽ cô gái phong cách Bocchi the Rock",
        "bocchi trong bocchi the rock chơi đàn rock",
        "OC tên Luna mặc áo giáp",
        "Furina và Nahida đi chơi trong vườn",
        "klee câu cá bằng bom",
        "",
    ])
    def test_result_round_trips_json(self, query):
        r = cu.resolve_character(query)
        encoded = json.dumps(r.to_dict())
        # Round-trip must preserve the safety flag.
        decoded = json.loads(encoded)
        assert decoded["safe_to_attach_lora"] == r.safe_to_attach_lora
        # Mode must be one of the documented values.
        assert decoded["mode"] in {
            "", "resolved_known", "ambiguous",
            "low_data_profile", "unresolved_unknown",
        }
