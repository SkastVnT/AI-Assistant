"""Focused tests for ``can_attach_character_lora`` — the single safety
gate that prevents wrong-LoRA attachment for ambiguous, unknown,
low-data, OC, style-only, and collision-prone characters.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import character_understanding as cu  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    stub = MagicMock()
    stub.resolve_query.return_value = None
    stub.detect_collisions.return_value = []
    stub.list_all.return_value = []
    stub.list_series.return_value = []
    monkeypatch.setattr("core.character_registry.get_registry", lambda: stub)

    fake = types.ModuleType("image_pipeline.anime_pipeline.saa_character_db")
    def _boom(*a, **kw):
        raise RuntimeError("SAA off in tests")
    fake.lookup_character = _boom  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules,
                        "image_pipeline.anime_pipeline.saa_character_db", fake)
    monkeypatch.setattr(cu, "_load_manual_overrides", lambda path=None: [])


# ── Block cases ──────────────────────────────────────────────────────────────

class TestBlockedCases:
    def test_none_input(self):
        safe, reason = cu.can_attach_character_lora(None)
        assert safe is False
        assert reason == "no_character_result"

    def test_unresolved_unknown_iroha_kaguya(self):
        r = cu.resolve_character(
            "Iroha trong Kaguya Cosmic Princess mặc váy trắng"
        )
        assert r.mode == "unresolved_unknown"
        safe, reason = cu.can_attach_character_lora(r)
        assert safe is False
        assert reason == "unresolved_unknown"

    def test_unresolved_unknown_blocks_same_name_other_series_lora(self):
        r = cu.resolve_character(
            "Iroha trong Kaguya Cosmic Princess mặc váy trắng"
        )
        # Even if a same-named LoRA from another series is offered,
        # the gate must refuse — the character is unresolved/unknown.
        safe, reason = cu.can_attach_character_lora(
            r,
            lora_candidate={
                "canonical_id": "iroha@samurai_champloo",
                "character_slug": "iroha",
                "series_slug": "samurai_champloo",
            },
        )
        assert safe is False
        assert reason == "unresolved_unknown"

    def test_firefly_without_hsr_hint_is_blocked(self):
        r = cu.resolve_character("firefly trên bầu trời pháo hoa")
        safe, reason = cu.can_attach_character_lora(r)
        assert safe is False
        # Either unresolved_unknown or safe_to_attach_lora_false.
        assert reason in {
            "unresolved_unknown",
            "safe_to_attach_lora_false",
            "not_resolved",
        }

    def test_oc_luna_is_blocked(self):
        r = cu.resolve_character("OC tên Luna mặc áo giáp")
        safe, reason = cu.can_attach_character_lora(r)
        assert safe is False
        assert reason != "ok"

    def test_style_bocchi_is_blocked(self):
        r = cu.resolve_character("vẽ cô gái phong cách Bocchi the Rock")
        safe, reason = cu.can_attach_character_lora(r)
        assert safe is False
        assert reason != "ok"

    def test_low_data_profile_without_lora_hint(self, monkeypatch):
        # Manual override that has NO lora_hint — must block.
        monkeypatch.setattr(
            cu, "_load_manual_overrides",
            lambda path=None: [{
                "canonical_id": "iroha@cosmic_princess_kaguya",
                "display_name": "Iroha",
                "series_slug": "cosmic_princess_kaguya",
                "series_name": "Cosmic Princess Kaguya",
                "aliases": ["iroha"],
                "confidence": 0.7,
                # no lora_hint, no safe_to_attach_lora
            }],
        )
        r = cu.resolve_character(
            "Iroha trong Kaguya Cosmic Princess mặc váy trắng"
        )
        assert r.mode == "low_data_profile"
        safe, reason = cu.can_attach_character_lora(r)
        assert safe is False
        assert reason in {
            "safe_to_attach_lora_false",
            "low_data_profile_no_lora_hint",
        }


# ── Allow cases ──────────────────────────────────────────────────────────────

class TestAllowedCases:
    def test_resolved_known_alias_table_hit(self):
        r = cu.resolve_character("hutao")
        assert r.mode == "resolved_known"
        safe, reason = cu.can_attach_character_lora(r)
        assert safe is True
        assert reason == "ok"

    def test_resolved_known_with_matching_lora_candidate(self):
        r = cu.resolve_character("hutao")
        safe, reason = cu.can_attach_character_lora(
            r,
            lora_candidate={"canonical_id": "hu_tao@genshin_impact"},
        )
        assert safe is True
        assert reason == "ok"

    def test_resolved_known_with_mismatched_lora_candidate(self):
        # Hu Tao resolved, but caller supplies a different-series LoRA —
        # gate must refuse.
        r = cu.resolve_character("hutao")
        safe, reason = cu.can_attach_character_lora(
            r,
            lora_candidate={
                "canonical_id": "hu_tao@some_other_series",
            },
        )
        assert safe is False
        assert reason == "canonical_id_mismatch"

    def test_resolved_known_with_series_mismatch_via_slugs(self):
        r = cu.resolve_character("hutao")
        safe, reason = cu.can_attach_character_lora(
            r,
            lora_candidate={
                "character_slug": "hu_tao",
                "series_slug": "samurai_champloo",
            },
        )
        assert safe is False
        assert reason == "series_mismatch"

    def test_low_data_profile_with_explicit_lora_hint(self, monkeypatch):
        # Manual override with explicit lora_hint AND safe_to_attach_lora.
        monkeypatch.setattr(
            cu, "_load_manual_overrides",
            lambda path=None: [{
                "canonical_id": "iroha@cosmic_princess_kaguya",
                "display_name": "Iroha",
                "series_slug": "cosmic_princess_kaguya",
                "series_name": "Cosmic Princess Kaguya",
                "aliases": ["iroha"],
                "confidence": 0.85,
                "lora_hint": "iroha_kaguya_v1",
                "safe_to_attach_lora": True,
                "data_status": "manual_override",
            }],
        )
        r = cu.resolve_character(
            "Iroha trong Kaguya Cosmic Princess mặc váy trắng"
        )
        assert r.mode == "low_data_profile"
        safe, reason = cu.can_attach_character_lora(r)
        assert safe is True
        assert reason == "ok"

        # Matching lora_candidate also OK.
        safe2, reason2 = cu.can_attach_character_lora(
            r,
            lora_candidate={"canonical_id": "iroha@cosmic_princess_kaguya"},
        )
        assert safe2 is True
        assert reason2 == "ok"

        # Wrong-series candidate must fail even on a low-data profile.
        safe3, reason3 = cu.can_attach_character_lora(
            r,
            lora_candidate={"canonical_id": "iroha@samurai_champloo"},
        )
        assert safe3 is False
        assert reason3 == "canonical_id_mismatch"


# ── Series-pinning behavior ──────────────────────────────────────────────────

class TestSeriesPinning:
    def test_firefly_with_hsr_only_attaches_on_exact_match(self):
        # Firefly + HSR hint reaches the gate as either resolved (alias
        # table contains firefly@hsr) or low_data/unknown. Whichever path,
        # an exact canonical match must allow; a different-series
        # candidate must block.
        r = cu.resolve_character("firefly hsr trên bầu trời pháo hoa")

        # Wrong-series LoRA candidate is ALWAYS blocked.
        bad_safe, bad_reason = cu.can_attach_character_lora(
            r,
            lora_candidate={
                "canonical_id": "firefly@some_other_series",
            },
        )
        assert bad_safe is False
        assert bad_reason in {
            "canonical_id_mismatch",
            "unresolved_unknown",
            "safe_to_attach_lora_false",
            "low_data_profile_no_lora_hint",
            "not_resolved",
        }
