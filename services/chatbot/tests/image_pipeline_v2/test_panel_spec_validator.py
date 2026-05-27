"""Tests for image_pipeline.reasoning.panel_spec_validator."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest
from image_pipeline.reasoning.panel_spec_validator import (
    validate_panel,
    validate_sequence,
)
from image_pipeline.reasoning.prompt_parser import parse
from image_pipeline.reasoning.schemas import (
    CharacterAppearance,
    CharacterState,
    ComicSequenceSpec,
    OutputLayout,
    OverlayElement,
    OverlayKind,
    OverlayPlan,
    PropRequirement,
    PropState,
    SceneState,
    ShotType,
    SinglePanelSpec,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def alice():
    return CharacterState(
        character_key="alice",
        character_name="Alice",
        appearance=CharacterAppearance(hair_color="red", eye_color="green"),
        must_keep=("red hair",),
    )


@pytest.fixture
def red_phone():
    return PropState(
        prop_key="red_phone",
        label="red phone",
        color="red",
        canonical_tags=("red", "phone"),
    )


@pytest.fixture
def basic_panel():
    return SinglePanelSpec(
        panel_id="p1_basic",
        shot_type=ShotType.MEDIUM,
        action_description="alice holding the red phone",
        character_keys=("alice",),
        primary_character_key="alice",
        prop_requirements=(PropRequirement(prop_key="red_phone"),),
    )


# ---------------------------------------------------------------------------
# Single-panel validator
# ---------------------------------------------------------------------------


class TestValidatePanelSingleton:
    def test_clean_panel_passes(self, basic_panel):
        result = validate_panel(
            basic_panel,
            known_character_keys={"alice"},
            known_prop_keys={"red_phone"},
        )
        assert result.ok
        assert result.errors == ()

    def test_unknown_character(self, basic_panel):
        result = validate_panel(
            basic_panel,
            known_character_keys={"bob"},
            known_prop_keys={"red_phone"},
        )
        assert not result.ok
        codes = {i.code for i in result.errors}
        assert "unknown_character" in codes

    def test_unknown_prop(self, basic_panel):
        result = validate_panel(
            basic_panel,
            known_character_keys={"alice"},
            known_prop_keys={"blue_mug"},
        )
        assert not result.ok
        codes = {i.code for i in result.errors}
        assert "unknown_prop" in codes

    def test_no_registry_skips_registry_checks(self, basic_panel):
        # Without registries, only intra-panel checks fire.
        result = validate_panel(basic_panel)
        assert result.ok

    def test_contradictory_must_keep_vs_forbidden(self):
        panel = SinglePanelSpec(
            panel_id="p_bad",
            shot_type=ShotType.MEDIUM,
            continuity_must_keep=("red hair",),
            forbidden_drift=("red hair",),
        )
        result = validate_panel(panel)
        assert not result.ok
        codes = {i.code for i in result.errors}
        assert "contradictory_continuity" in codes

    def test_prop_must_appear_false_but_in_must_keep(self):
        panel = SinglePanelSpec(
            panel_id="p_propbad",
            shot_type=ShotType.MEDIUM,
            continuity_must_keep=("red_phone",),
            prop_requirements=(
                PropRequirement(prop_key="red_phone", must_appear=False),
            ),
        )
        result = validate_panel(panel)
        codes = {i.code for i in result.errors}
        assert "contradictory_prop_requirement" in codes


# ---------------------------------------------------------------------------
# Overlay plan validator
# ---------------------------------------------------------------------------


class TestOverlayValidation:
    def test_caption_with_empty_text_rejected(self):
        plan = OverlayPlan(
            elements=(
                OverlayElement(element_id="c1", kind=OverlayKind.CAPTION, text=""),
            )
        )
        panel = SinglePanelSpec(
            panel_id="p_overlay",
            shot_type=ShotType.MEDIUM,
            overlay_plan=plan,
        )
        result = validate_panel(panel)
        codes = {i.code for i in result.errors}
        assert "empty_overlay_text" in codes

    def test_speech_bubble_requires_text(self):
        plan = OverlayPlan(
            elements=(
                OverlayElement(
                    element_id="b1", kind=OverlayKind.SPEECH_BUBBLE, text=""
                ),
            )
        )
        panel = SinglePanelSpec(
            panel_id="p_b",
            shot_type=ShotType.MEDIUM,
            overlay_plan=plan,
        )
        assert not validate_panel(panel).ok

    def test_z_order_collision_warning(self):
        plan = OverlayPlan(
            elements=(
                OverlayElement(
                    element_id="o1", kind=OverlayKind.CAPTION, text="hi", z_order=1
                ),
                OverlayElement(
                    element_id="o2", kind=OverlayKind.CAPTION, text="bye", z_order=1
                ),
            )
        )
        panel = SinglePanelSpec(
            panel_id="p_z", shot_type=ShotType.MEDIUM, overlay_plan=plan
        )
        result = validate_panel(panel)
        # Warning, not error.
        assert result.ok
        codes = {i.code for i in result.warnings}
        assert "overlay_z_order_collision" in codes


# ---------------------------------------------------------------------------
# Sequence validator
# ---------------------------------------------------------------------------


class TestValidateSequenceClean:
    def test_parsed_sequence_passes(self):
        result = parse("4 panel comic of a cat in a kitchen")
        seq = result.sequence
        assert seq is not None
        v = validate_sequence(seq)
        assert v.ok, v.issues

    def test_parsed_sequence_with_character_hint_passes(self):
        result = parse(
            "4 panel comic of Alice in the bedroom holding a red phone",
            character_hint={"character_key": "alice", "character_name": "Alice"},
        )
        seq = result.sequence
        v = validate_sequence(
            seq,
            known_character_keys={"alice"},
            known_prop_keys={"red_phone"},
        )
        assert v.ok, [i.to_dict() for i in v.issues]


class TestValidateSequenceErrors:
    def test_unknown_character_against_registry(self):
        result = parse(
            "4 panel comic of Alice somewhere",
            character_hint={"character_key": "alice", "character_name": "Alice"},
        )
        seq = result.sequence
        v = validate_sequence(seq, known_character_keys={"bob"})
        assert not v.ok
        codes = {i.code for i in v.errors}
        assert "unknown_character" in codes

    def test_unknown_prop_against_registry(self):
        result = parse("storyboard of 3 panels with a red phone")
        seq = result.sequence
        v = validate_sequence(seq, known_prop_keys={"blue_mug"})
        assert not v.ok
        codes = {i.code for i in v.errors}
        assert "unknown_prop" in codes

    def test_global_character_must_keep_vs_panel_forbidden(self, alice, red_phone):
        # Hand-build a sequence where alice.must_keep contains "red hair" and
        # one panel forbids drift on the same token.
        panel_ok = SinglePanelSpec(
            panel_id="p_a",
            shot_type=ShotType.MEDIUM,
            character_keys=("alice",),
            primary_character_key="alice",
            prop_requirements=(PropRequirement(prop_key="red_phone"),),
        )
        panel_bad = SinglePanelSpec(
            panel_id="p_b",
            shot_type=ShotType.MEDIUM,
            character_keys=("alice",),
            primary_character_key="alice",
            prop_requirements=(PropRequirement(prop_key="red_phone"),),
            forbidden_drift=("red hair",),
        )
        seq = ComicSequenceSpec(
            sequence_id="seq_contradict",
            global_story="contradiction test",
            character_states=(("alice", alice),),
            prop_states=(("red_phone", red_phone),),
            scene_state=SceneState(),
            ordered_panels=(panel_ok, panel_bad),
            output_layout=OutputLayout.HORIZONTAL_STRIP,
        )
        v = validate_sequence(seq)
        codes = {i.code for i in v.errors}
        assert "contradicts_character_must_keep" in codes


class TestSequenceLayoutDefense:
    def test_grid_2x2_with_4_panels_ok(self, alice, red_phone):
        panels = tuple(
            SinglePanelSpec(
                panel_id=f"p_grid_{i}",
                shot_type=ShotType.MEDIUM,
                character_keys=("alice",),
                primary_character_key="alice",
                prop_requirements=(PropRequirement(prop_key="red_phone"),),
            )
            for i in range(4)
        )
        seq = ComicSequenceSpec(
            sequence_id="seq_grid",
            global_story="grid test",
            character_states=(("alice", alice),),
            prop_states=(("red_phone", red_phone),),
            scene_state=SceneState(),
            ordered_panels=panels,
            output_layout=OutputLayout.GRID_2X2,
        )
        v = validate_sequence(seq)
        assert v.ok


class TestResultShape:
    def test_result_to_dict(self, basic_panel):
        v = validate_panel(
            basic_panel, known_character_keys={"alice"}, known_prop_keys={"red_phone"}
        )
        d = v.to_dict()
        assert d["ok"] is True
        assert isinstance(d["issues"], list)
