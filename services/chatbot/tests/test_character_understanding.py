"""Tests for core.character_understanding (phase 1).

These tests exercise the resolver in isolation. The local
``CharacterRegistry`` is monkey-patched per-test so we don't depend on
the seeded ``storage/character_db/`` JSON content. SAA is exercised
both as "missing" and as a stub.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure chatbot root is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import character_understanding as cu  # noqa: E402


# ── Helpers ──────────────────────────────────────────────────────────────────

def _empty_registry(monkeypatch):
    """Patch get_registry to return a stub with no hits and no collisions."""
    stub = MagicMock()
    stub.resolve_query.return_value = None
    stub.detect_collisions.return_value = []
    monkeypatch.setattr("core.character_registry.get_registry", lambda: stub)
    return stub


def _disable_saa(monkeypatch):
    """Force the SAA lazy import to fail."""
    # Insert a sentinel that raises on attribute access.
    fake = types.ModuleType("image_pipeline.anime_pipeline.saa_character_db")
    def _boom(*a, **kw):
        raise RuntimeError("SAA not installed in this test")
    fake.lookup_character = _boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "image_pipeline.anime_pipeline.saa_character_db", fake)


# ── Canonical ID stability ───────────────────────────────────────────────────

class TestCanonicalId:
    def test_basic(self):
        assert cu.make_canonical_id("hu_tao", "genshin_impact") == "hu_tao@genshin_impact"

    def test_slugifies_inputs(self):
        assert cu.make_canonical_id("Hu Tao", "Genshin Impact") == "hu_tao@genshin_impact"

    def test_strips_diacritics(self):
        assert cu.make_canonical_id("Élise", "café") == "elise@cafe"

    def test_empty_series(self):
        assert cu.make_canonical_id("rem", "") == "rem@"

    def test_stable_across_calls(self):
        a = cu.make_canonical_id("Hu Tao", "Genshin Impact")
        b = cu.make_canonical_id("hu  tao", "genshin-impact")
        assert a == b == "hu_tao@genshin_impact"


# ── selected_character priority ──────────────────────────────────────────────

class TestSelectedCharacterWins:
    def test_selected_wins_over_alias_table(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        # "rem" is ambiguous in alias table — but selected_character must win.
        result = cu.resolve_character(
            "rem",
            selected_character={
                "character_slug": "Some Custom OC",
                "series_slug": "private_universe",
                "display_name": "Custom OC",
                "series_name": "Private Universe",
            },
        )
        assert result.resolved is True
        assert result.ambiguous is False
        assert result.best is not None
        assert result.best.canonical_id == "some_custom_oc@private_universe"
        assert result.best.source == "selected"
        assert result.best.confidence == 1.0

    def test_selected_without_query(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        result = cu.resolve_character(
            "",
            selected_character={"character_slug": "kafka", "series_slug": "honkai_star_rail"},
        )
        assert result.resolved is True
        assert result.best.canonical_id == "kafka@honkai_star_rail"


# ── Alias table ──────────────────────────────────────────────────────────────

class TestAliasTable:
    def test_unique_alias_resolves(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        result = cu.resolve_character("hutao")
        assert result.resolved is True
        assert result.ambiguous is False
        assert result.best.canonical_id == "hu_tao@genshin_impact"
        assert result.best.source == "alias_table"

    def test_yae_resolves_to_yae_miko(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        result = cu.resolve_character("yae")
        assert result.resolved is True
        assert result.best.canonical_id == "yae_miko@genshin_impact"

    def test_ambiguous_miko_returns_candidates(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        result = cu.resolve_character("Miko")  # case-insensitive
        assert result.ambiguous is True
        assert result.resolved is False
        ids = {c.canonical_id for c in result.candidates}
        assert "yae_miko@genshin_impact" in ids
        assert "shrine_miko@generic" in ids
        assert result.best is None  # ambiguous → no auto-attach

    def test_ambiguous_rem(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        result = cu.resolve_character("Rem")
        assert result.ambiguous is True
        ids = {c.canonical_id for c in result.candidates}
        assert "rem@rezero" in ids
        assert "rem_sleep@generic" in ids

    def test_ambiguous_sparkle(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        result = cu.resolve_character("sparkle")
        assert result.ambiguous is True


# ── Registry path ────────────────────────────────────────────────────────────

class TestRegistryPath:
    def test_registry_hit_short_circuits(self, monkeypatch):
        rec = MagicMock()
        rec.key = "hu_tao_genshin_impact"
        rec.character_tag = "hu_tao"
        rec.series_key = "genshin_impact"
        rec.display_name = "Hu Tao"
        rec.series = "Genshin Impact"
        rec.aliases = ["HuTao"]
        rec.lora_hint = None

        stub = MagicMock()
        stub.resolve_query.return_value = rec
        stub.detect_collisions.return_value = []
        monkeypatch.setattr("core.character_registry.get_registry", lambda: stub)
        _disable_saa(monkeypatch)

        result = cu.resolve_character("Hu Tao")
        assert result.resolved is True
        assert result.best.source == "registry"
        assert result.best.canonical_id == "hu_tao@genshin_impact"

    def test_registry_collision_marks_ambiguous(self, monkeypatch):
        def make_rec(key, char_tag, series_key, display, series):
            r = MagicMock()
            r.key, r.character_tag, r.series_key = key, char_tag, series_key
            r.display_name, r.series = display, series
            r.aliases, r.lora_hint = [], None
            return r

        rec_a = make_rec("rem_rezero", "rem", "rezero", "Rem", "Re:Zero")
        rec_b = make_rec("rem_pokemon", "rem", "pokemon", "Rem", "Pokemon")

        stub = MagicMock()
        stub.resolve_query.return_value = rec_a
        stub.detect_collisions.return_value = [rec_a, rec_b]
        monkeypatch.setattr("core.character_registry.get_registry", lambda: stub)
        _disable_saa(monkeypatch)

        result = cu.resolve_character("Rem")
        assert result.ambiguous is True
        ids = {c.canonical_id for c in result.candidates}
        assert "rem@rezero" in ids
        assert "rem@pokemon" in ids


# ── SAA fail-safe ────────────────────────────────────────────────────────────

class TestSaaFailSafe:
    def test_missing_saa_does_not_crash(self, monkeypatch):
        _empty_registry(monkeypatch)
        # Remove SAA module entirely if present, and block re-import.
        monkeypatch.setitem(
            sys.modules,
            "image_pipeline.anime_pipeline.saa_character_db",
            None,  # importlib treats this as ImportError
        )
        result = cu.resolve_character("totally_unknown_character_xyz")
        assert result.resolved is False
        assert result.ambiguous is False
        assert result.best is None

    def test_saa_exception_falls_through(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)  # SAA raises on call
        # Should still be able to hit alias table.
        result = cu.resolve_character("hutao")
        assert result.resolved is True
        assert result.best.canonical_id == "hu_tao@genshin_impact"


# ── Empty / no-op ────────────────────────────────────────────────────────────

class TestEmpty:
    def test_empty_query_no_selection(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        result = cu.resolve_character("")
        assert result.resolved is False
        assert result.ambiguous is False
        assert result.candidates == []

    def test_unknown_query(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        result = cu.resolve_character("zzzzz_not_a_character")
        assert result.resolved is False
        assert result.best is None


# ── Prompt entity extraction ─────────────────────────────────────────────────

class TestExtractPromptEntities:
    def test_iroha_kaguya_phrase(self):
        ents = cu.extract_prompt_entities(
            "Iroha trong Kaguya Cosmic Princess mặc váy trắng đứng trong vườn hoa"
        )
        assert ents["candidate_name_slug"] == "iroha"
        assert ents["candidate_name"] == "Iroha"
        assert ents["series_hint"] == "cosmic_princess_kaguya"
        # Residual must include the outfit/scene tail (now original-cased).
        assert "váy" in ents["residual_prompt"] or "trắng" in ents["residual_prompt"]
        assert "hoa" in ents["residual_prompt"]
        assert ents["is_named"] is True

    def test_english_from_phrase(self):
        ents = cu.extract_prompt_entities("draw Sparkle from Honkai Star Rail")
        assert ents["candidate_name_slug"] == "sparkle"
        assert ents["series_hint"] == "honkai_star_rail"
        assert ents["is_named"] is True

    def test_generic_scene_is_not_named(self):
        ents = cu.extract_prompt_entities("a cat sitting in a sunny window")
        assert ents["series_hint"] == ""
        # "cat" is lowercase in the prompt → not treated as a proper name.
        assert ents["is_named"] is False

    def test_empty_prompt(self):
        ents = cu.extract_prompt_entities("")
        assert ents["candidate_name"] == ""
        assert ents["series_hint"] == ""
        assert ents["is_named"] is False


# ── Unknown / low-data fallback ──────────────────────────────────────────────

class TestUnknownCharacterFallback:
    """Behavior when no known source recognises the character."""

    def test_unknown_with_series_hint_yields_unresolved_unknown(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        # Force overrides to be empty.
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])

        result = cu.resolve_character(
            "Iroha trong Kaguya Cosmic Princess mặc váy trắng trong vườn hoa"
        )
        # Must NOT pick a known character.
        assert result.resolved is False
        assert result.ambiguous is False
        assert result.best is None
        assert result.mode == "unresolved_unknown"
        assert result.safe_to_attach_lora is False
        # Provisional id is stable & namespaced.
        assert result.unknown_profile is not None
        assert result.unknown_profile.provisional_id == "unknown:iroha@cosmic_princess_kaguya"
        assert result.unknown_profile.possible_series == "cosmic_princess_kaguya"
        assert result.unknown_profile.needs_user_confirmation is True
        # Identity block tells downstream not to attach LoRA.
        assert "Do not attach LoRA" in result.character_identity_block
        assert "do not substitute" in result.character_identity_block.lower()

    def test_unknown_does_not_attach_lora(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])
        result = cu.resolve_character("Iroha trong Kaguya Cosmic Princess")
        assert result.safe_to_attach_lora is False
        # No candidate carrying a LoRA hint.
        assert all(c.lora_hint is None for c in result.candidates)

    def test_collision_prone_name_without_series_hint(self, monkeypatch):
        """A bare unknown name with no series stays unresolved_unknown
        — never auto-resolves to a popular character."""
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])
        # "Aria" is a name shared by many characters; no series hint here.
        result = cu.resolve_character("Aria mặc váy trắng đứng trong vườn hoa")
        assert result.resolved is False
        assert result.safe_to_attach_lora is False
        assert result.mode == "unresolved_unknown"
        assert result.unknown_profile.needs_user_confirmation is True
        assert result.unknown_profile.possible_series == ""

    def test_missing_overrides_file_does_not_crash(self, monkeypatch, tmp_path):
        # Point loader at a non-existent file.
        bogus = tmp_path / "does_not_exist.json"
        assert not bogus.exists()
        loaded = cu._load_manual_overrides(bogus)
        assert loaded == []

    def test_known_character_unaffected_by_unknown_path(self, monkeypatch):
        """Sanity: existing alias resolution still wins over unknown."""
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])
        result = cu.resolve_character("hutao")
        assert result.resolved is True
        assert result.mode == "resolved_known"
        assert result.safe_to_attach_lora is True
        assert result.unknown_profile is None

    def test_result_is_json_serializable(self, monkeypatch):
        import json
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])
        result = cu.resolve_character("Iroha trong Kaguya Cosmic Princess")
        # to_dict() must round-trip through JSON without errors.
        encoded = json.dumps(result.to_dict())
        decoded = json.loads(encoded)
        assert decoded["mode"] == "unresolved_unknown"
        assert decoded["unknown_profile"]["provisional_id"].startswith("unknown:iroha@")


# ── Manual override → low_data_profile ───────────────────────────────────────

class TestManualOverride:
    def _make_override(self):
        return [
            {
                "canonical_id": "iroha_sakayori@cosmic_princess_kaguya",
                "display_name": "Iroha Sakayori",
                "aliases": ["iroha", "iroha sakayori"],
                "series": "Cosmic Princess Kaguya",
                "series_slug": "cosmic_princess_kaguya",
                "visual_traits": ["long silver hair", "blue eyes"],
                "negative_identity_guard": [
                    "do not make her Kaguya",
                    "do not make her Hatsune Miku",
                ],
            }
        ]

    def test_override_resolves_to_low_data_profile(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(
            cu, "_load_manual_overrides", lambda path=None: self._make_override()
        )
        result = cu.resolve_character(
            "Iroha trong Kaguya Cosmic Princess mặc váy trắng"
        )
        assert result.resolved is True
        assert result.mode == "low_data_profile"
        assert result.safe_to_attach_lora is False  # NEVER attach LoRA from override
        assert result.best is not None
        assert result.best.canonical_id == "iroha_sakayori@cosmic_princess_kaguya"
        assert result.best.source == "manual_override"
        # Visual traits from override propagate to identity block.
        assert "long silver hair" in result.character_identity_block
        # Negative guard included.
        assert "do not make her Kaguya" in result.character_identity_block
        assert result.unknown_profile is not None
        assert result.unknown_profile.profile_source == "manual_override"

    def test_override_not_matched_when_series_differs(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        # Override is locked to Cosmic Princess Kaguya. Prompt mentions a
        # different series → must NOT match.
        monkeypatch.setattr(
            cu, "_load_manual_overrides", lambda path=None: self._make_override()
        )
        result = cu.resolve_character("Iroha trong Genshin Impact")
        # Falls back to unresolved_unknown for that other series.
        assert result.mode == "unresolved_unknown"
        assert result.safe_to_attach_lora is False
        assert result.unknown_profile.possible_series == "genshin_impact"


# ── Phase 4: override priority + collision safety ────────────────────────────

class TestOverridePriority:
    """Manual override must beat registry/SAA/alias for the same name."""

    def test_override_beats_registry_hit(self, monkeypatch):
        # Registry would normally resolve "newchar" to a fake record;
        # override for the same slug must win.
        rec = MagicMock()
        rec.character_tag = "newchar_registry"
        rec.key = "newchar_registry"
        rec.series_key = "wrong_series"
        rec.display_name = "Newchar Registry"
        rec.series = "Wrong Series"
        rec.aliases = ["newchar"]
        rec.lora_hint = "registry_lora.safetensors"
        stub = MagicMock()
        stub.resolve_query.return_value = rec
        stub.detect_collisions.return_value = []
        monkeypatch.setattr("core.character_registry.get_registry", lambda: stub)
        _disable_saa(monkeypatch)

        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [{
            "canonical_id": "newchar@correct_series",
            "display_name": "Newchar",
            "aliases": ["newchar"],
            "series_slug": "correct_series",
            "visual_traits": ["short blue hair"],
        }])
        result = cu.resolve_character("Newchar")
        assert result.mode == "low_data_profile"
        assert result.best.canonical_id == "newchar@correct_series"
        assert result.best.source == "manual_override"
        assert result.safe_to_attach_lora is False

    def test_override_with_explicit_lora_attaches(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [{
            "canonical_id": "verified_char@verified_series",
            "display_name": "Verified Char",
            "aliases": ["verified"],
            "series_slug": "verified_series",
            "lora_hint": "verified_char_v1.safetensors",
            "safe_to_attach_lora": True,
        }])
        result = cu.resolve_character("Verified")
        assert result.mode == "low_data_profile"
        assert result.safe_to_attach_lora is True
        assert result.best.lora_hint == "verified_char_v1.safetensors"

    def test_override_with_lora_but_not_marked_safe_stays_unsafe(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [{
            "canonical_id": "untrusted@series",
            "display_name": "Untrusted",
            "aliases": ["untrusted"],
            "series_slug": "series",
            "lora_hint": "untrusted.safetensors",
            # safe_to_attach_lora omitted (defaults to False)
        }])
        result = cu.resolve_character("Untrusted")
        assert result.mode == "low_data_profile"
        assert result.safe_to_attach_lora is False
        assert result.best.lora_hint is None  # stripped


class TestCollisionSafety:
    """Collision-prone names must never auto-resolve to a popular character."""

    def test_firefly_without_series_hint_is_safe(self, monkeypatch):
        # No HSR alias for "firefly" in the alias table → unknown profile.
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])
        result = cu.resolve_character("Firefly trên bầu trời pháo hoa")
        assert result.safe_to_attach_lora is False
        assert result.mode in {"unresolved_unknown", "ambiguous"}
        # Must NOT silently pick e.g. firefly_effect / a generic firefly.
        if result.best is not None:
            assert "effect" not in result.best.canonical_id.lower()

    def test_firefly_with_hsr_hint_pins_series(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])
        result = cu.resolve_character("Firefly HSR trên bầu trời pháo hoa")
        # No "firefly" alias entry → must fall to unknown:firefly@hsr,
        # NOT to firefly_effect / similar.
        assert result.safe_to_attach_lora is False
        if result.mode == "unresolved_unknown":
            assert result.unknown_profile.possible_series == "honkai_star_rail"
            assert result.unknown_profile.provisional_id == "unknown:firefly@honkai_star_rail"
        else:
            # If a future alias is added, it MUST be the HSR firefly.
            assert result.best is not None
            assert result.best.series_slug == "honkai_star_rail"

    def test_main_female_protagonist_phrase(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])
        result = cu.resolve_character(
            "nhân vật main nữ trong zzz đứng bên tường uống nước"
        )
        # No alias → unknown profile, but the series hint MUST resolve.
        assert result.safe_to_attach_lora is False
        if result.unknown_profile is not None:
            assert result.unknown_profile.possible_series == "zenless_zone_zero"


class TestProfileSchema:
    """Phase 4 schema additions on UnknownCharacterProfile."""

    def test_profile_has_data_status_and_needs_review(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])
        result = cu.resolve_character("Brandnewchar trong Brandnewseries")
        assert result.unknown_profile is not None
        d = result.unknown_profile.to_dict()
        assert d["data_status"] == "unknown"
        assert d["needs_review"] is True

    def test_override_profile_data_status(self, monkeypatch):
        _empty_registry(monkeypatch)
        _disable_saa(monkeypatch)
        monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [{
            "canonical_id": "x@y",
            "display_name": "X",
            "aliases": ["x"],
            "series_slug": "y",
            "data_status": "manual_override",
        }])
        result = cu.resolve_character("X")
        assert result.unknown_profile is not None
        assert result.unknown_profile.to_dict()["data_status"] == "manual_override"


class TestInvalidOverrideFile:
    """Loader must never crash on missing / invalid override files."""

    def test_missing_file(self, tmp_path):
        assert cu._load_manual_overrides(tmp_path / "no.json") == []

    def test_invalid_json(self, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{ this is not valid json", encoding="utf-8")
        assert cu._load_manual_overrides(bad) == []

    def test_non_dict_root(self, tmp_path):
        not_obj = tmp_path / "list.json"
        not_obj.write_text('["this is a list, not an object"]', encoding="utf-8")
        assert cu._load_manual_overrides(not_obj) == []
