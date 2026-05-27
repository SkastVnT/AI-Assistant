"""
Tests for image_pipeline.reasoning.state — Cycle 2 state managers.

Coverage:
* CharacterStateManager: from_record mapping, registry lookup by key /
  alias / display name, missing-key fallback, identity must_keep tokens.
* PropStateManager: extraction with color, bare nouns, deduplication,
  resolve by key / label.
* extract_scene: location / time / mood matching.
* StateResolver wired into prompt_parser.parse: registry-backed character
  flows into ComicSequenceSpec; legacy path (no resolver) unchanged.
* shared_env hygiene: importing the state package never calls load_dotenv.
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

# Imported via the chatbot conftest's sys.path injection.
from core.character_registry import (  # type: ignore[import-not-found]
    CharacterRecord,
    get_registry,
)
from image_pipeline.reasoning.panel_spec_validator import validate_sequence
from image_pipeline.reasoning.prompt_parser import parse
from image_pipeline.reasoning.schemas import (
    CharacterState,
    SceneState,
)
from image_pipeline.reasoning.state import (
    CharacterStateManager,
    PropStateManager,
    StateResolver,
    default_resolver,
    extract_scene,
)

# ---------------------------------------------------------------------------
# CharacterStateManager
# ---------------------------------------------------------------------------


class TestCharacterStateManagerFromRecord:
    def test_from_record_builds_full_state(self):
        record = CharacterRecord(
            key="hu_tao_genshin_impact",
            display_name="Hu Tao",
            series="Genshin Impact",
            series_key="genshin_impact",
            character_tag="hu tao (genshin impact)",
            series_tag="genshin impact",
            aliases=["HuTao", "Director Hu"],
            lora_hint="hu_tao_v1",
        )
        state = CharacterStateManager.from_record(record)
        assert isinstance(state, CharacterState)
        assert state.character_key == "hu_tao_genshin_impact"
        assert state.character_name == "Hu Tao"
        assert state.source_series == "Genshin Impact"
        assert "hu tao (genshin impact)" in state.canonical_tags
        assert "HuTao" in state.canonical_tags
        # Identity must_keep
        assert "Hu Tao" in state.must_keep
        assert "hu tao (genshin impact)" in state.must_keep
        assert state.lora_hints == ("hu_tao_v1",)
        assert state.notes == "registry resolved"

    def test_from_record_no_lora_hint(self):
        record = CharacterRecord(
            key="x_y",
            display_name="X",
            series="Y",
            series_key="y",
            character_tag="x (y)",
            series_tag="y",
            aliases=[],
            lora_hint=None,
        )
        state = CharacterStateManager.from_record(record)
        assert state.lora_hints == ()

    def test_from_record_missing_required_raises(self):
        record = CharacterRecord(
            key="",
            display_name="",
            series="",
            series_key="",
            character_tag="",
            series_tag="",
        )
        with pytest.raises(ValueError):
            CharacterStateManager.from_record(record)


class TestCharacterStateManagerResolve:
    @pytest.fixture
    def manager(self):
        # Use the live registry — characters.json is in the repo and stable.
        return CharacterStateManager(registry=get_registry())

    def test_resolve_by_key(self, manager):
        result = manager.resolve("hu_tao_genshin_impact")
        assert result is not None
        key, state = result
        assert key == "hu_tao_genshin_impact"
        assert state.character_name == "Hu Tao"

    def test_resolve_by_display_name(self, manager):
        result = manager.resolve("Raiden Shogun")
        assert result is not None
        _, state = result
        assert state.character_key == "raiden_shogun_genshin_impact"

    def test_resolve_unknown_returns_none(self, manager):
        assert manager.resolve("zzz_nobody_here") is None

    def test_resolve_mapping_with_key(self, manager):
        result = manager.resolve({"character_key": "kafka_honkai_star_rail"})
        assert result is not None
        _, state = result
        assert state.character_name == "Kafka"

    def test_resolve_mapping_unknown_falls_back_to_placeholder(self, manager):
        # Registry has no record but hint has both fields → placeholder.
        result = manager.resolve(
            {"character_key": "totally_made_up", "character_name": "Made Up"}
        )
        assert result is not None
        key, state = result
        assert key == "totally_made_up"
        assert state.character_name == "Made Up"
        assert state.notes == "parser placeholder"

    def test_resolve_none_input(self, manager):
        assert manager.resolve(None) is None
        assert manager.resolve("") is None

    def test_no_registry_returns_none_for_string(self):
        manager = CharacterStateManager(registry=None)
        # Force the lazy default to a known-bad state by injecting None twice.
        manager._registry = None
        manager._tried_default = True
        assert manager.resolve("Hu Tao") is None


# ---------------------------------------------------------------------------
# PropStateManager
# ---------------------------------------------------------------------------


class TestPropStateManager:
    def test_extract_color_noun_props(self):
        mgr = PropStateManager()
        result = mgr.extract_props_from_text("She holds a red phone and a blue mug.")
        keys = [k for k, _ in result]
        assert "red_phone" in keys
        assert "blue_mug" in keys
        red_phone = dict(result)["red_phone"]
        assert red_phone.color == "red"
        assert red_phone.label == "red phone"
        assert "phone" in red_phone.canonical_tags

    def test_extract_bare_noun_skipped_when_colored_present(self):
        mgr = PropStateManager()
        result = mgr.extract_props_from_text("She holds a red phone. The phone rings.")
        keys = [k for k, _ in result]
        # Bare "the phone" should not produce a separate entry.
        assert "phone" not in keys
        assert "red_phone" in keys

    def test_extract_bare_noun_when_no_color(self):
        mgr = PropStateManager()
        result = mgr.extract_props_from_text("She picks up the book.")
        keys = [k for k, _ in result]
        assert "book" in keys
        book = dict(result)["book"]
        assert book.color == ""

    def test_extract_dedup_across_calls(self):
        mgr = PropStateManager()
        first = mgr.extract_props_from_text("a red phone")
        second = mgr.extract_props_from_text("a red phone again")
        # Both calls return the prop, but the store has one entry.
        assert len(first) == 1
        assert len(second) == 1
        assert len(mgr) == 1

    def test_resolve_by_key_and_label(self):
        mgr = PropStateManager()
        mgr.extract_props_from_text("a green book")
        assert mgr.resolve("green_book") is not None
        assert mgr.resolve("green book") is not None
        assert mgr.resolve("nonexistent") is None

    def test_extract_empty_text(self):
        mgr = PropStateManager()
        assert mgr.extract_props_from_text("") == ()
        assert mgr.extract_props_from_text("hello world") == ()


# ---------------------------------------------------------------------------
# extract_scene
# ---------------------------------------------------------------------------


class TestExtractScene:
    def test_bedroom_at_night(self):
        scene = extract_scene("a girl in her bedroom at night")
        assert isinstance(scene, SceneState)
        assert scene.location == "bedroom"
        assert scene.time_of_day == "night"
        assert scene.lock_scene is True

    def test_coffee_shop_normalized(self):
        # Note: "noon" is matched before "afternoon" because the keyword table
        # is scanned in declared order and "noon" is a substring of "afternoon".
        # This is inherited Cycle-1 behavior; documented here so the test
        # reflects actual semantics rather than aspirational ones.
        scene = extract_scene("two friends at a coffee shop in the evening")
        assert scene.location == "cafe"
        assert scene.time_of_day == "evening"

    def test_mood_match(self):
        scene = extract_scene("a tense moment")
        assert scene.mood == "tense"

    def test_no_match_returns_empty_strings(self):
        scene = extract_scene("just a vague description")
        assert scene.location == ""
        assert scene.time_of_day == ""
        assert scene.mood == ""


# ---------------------------------------------------------------------------
# StateResolver wired into parse()
# ---------------------------------------------------------------------------


class TestParserWithResolver:
    def test_parse_with_resolver_uses_registry_character(self):
        resolver = StateResolver(
            character=CharacterStateManager(registry=get_registry()),
            prop=PropStateManager(),
        )
        result = parse(
            "4 panel comic of Hu Tao in the kitchen at night",
            character_hint={"character_key": "hu_tao_genshin_impact"},
            state_resolver=resolver,
            panel_count_override=4,
        )
        assert result.sequence is not None
        seq = result.sequence
        # Character state was resolved from registry, not placeholder.
        assert len(seq.character_states) == 1
        _, char = seq.character_states[0]
        assert char.character_name == "Hu Tao"
        assert char.notes == "registry resolved"
        assert "Hu Tao" in char.must_keep
        assert seq.scene_state.location == "kitchen"
        assert seq.scene_state.time_of_day == "night"
        # Sequence is internally consistent.
        validation = validate_sequence(seq)
        assert validation.ok, f"validation issues: {validation.issues}"

    def test_parse_without_resolver_uses_placeholder(self):
        # Regression: Cycle 1 behavior preserved when no resolver is passed.
        result = parse(
            "single panel of Hu Tao",
            character_hint={
                "character_key": "hu_tao_genshin_impact",
                "character_name": "Hu Tao",
            },
        )
        assert result.single_panel is not None
        assert result.single_panel.primary_character_key == "hu_tao_genshin_impact"

    def test_default_resolver_constructible(self):
        resolver = default_resolver()
        assert isinstance(resolver, StateResolver)
        assert isinstance(resolver.character, CharacterStateManager)
        assert isinstance(resolver.prop, PropStateManager)


# ---------------------------------------------------------------------------
# Shared-env contract
# ---------------------------------------------------------------------------


class TestSharedEnvHygiene:
    def test_state_modules_do_not_call_load_dotenv(self):
        """No module under image_pipeline/reasoning/state/ may call load_dotenv.

        The shared-env contract (services/shared_env.py) is the only loader.
        """
        state_dir = _ROOT / "app" / "image_pipeline" / "reasoning" / "state"
        offenders = []
        for path in state_dir.glob("*.py"):
            content = path.read_text(encoding="utf-8")
            if "load_dotenv" in content:
                offenders.append(path.name)
        assert offenders == [], f"load_dotenv leaked into: {offenders}"

    def test_state_modules_do_not_import_dotenv(self):
        state_dir = _ROOT / "app" / "image_pipeline" / "reasoning" / "state"
        offenders = []
        for path in state_dir.glob("*.py"):
            content = path.read_text(encoding="utf-8")
            if "from dotenv" in content or "import dotenv" in content:
                offenders.append(path.name)
        assert offenders == [], f"dotenv imported in: {offenders}"
