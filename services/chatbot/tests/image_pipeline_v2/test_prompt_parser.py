"""Tests for image_pipeline.reasoning.prompt_parser."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


from image_pipeline.reasoning.capability_router import RequestKind
from image_pipeline.reasoning.prompt_parser import parse
from image_pipeline.reasoning.schemas import (
    ComicSequenceSpec,
    EyeState,
    OutputLayout,
    OverlayKind,
    PanelRole,
    ShotType,
    SinglePanelSpec,
)


class TestSinglePanelTextToImage:
    def test_basic_single_panel(self):
        result = parse("a red apple on a wooden table")
        assert result.decision.kind is RequestKind.TEXT_TO_IMAGE
        assert result.single_panel is not None
        assert result.sequence is None
        panel = result.single_panel
        assert isinstance(panel, SinglePanelSpec)
        assert panel.shot_type is ShotType.MEDIUM  # default
        assert panel.aspect_ratio == "1:1"

    def test_shot_type_detected(self):
        r = parse("an extreme close-up of her eye")
        assert r.single_panel.shot_type is ShotType.EXTREME_CLOSE_UP

    def test_eye_state_detected(self):
        r = parse("close-up portrait, eyes closed")
        assert r.single_panel.eye_state is EyeState.CLOSED

    def test_aspect_keyword(self):
        r = parse("portrait of a knight")
        assert r.single_panel.aspect_ratio == "3:4"

    def test_aspect_explicit(self):
        r = parse("a 16:9 cinematic landscape")
        assert r.single_panel.aspect_ratio == "16:9"

    def test_props_extracted_with_color(self):
        r = parse("a hero holding a red phone next to a blue mug")
        prop_keys = {req.prop_key for req in r.single_panel.prop_requirements}
        assert "red_phone" in prop_keys
        assert "blue_mug" in prop_keys


class TestImageEditFlow:
    def test_image_edit_includes_inpaint_stage(self):
        r = parse("change the sky to sunset", attached_images=1)
        assert r.decision.kind is RequestKind.IMAGE_EDIT
        # Edit defaults include inpaint; parser does not run anything.
        assert "inpaint" in r.required_stages

    def test_face_region_adds_face_patch_stage(self):
        r = parse("fix the eyes", attached_images=1)
        assert "face_patch" in r.required_stages

    def test_background_region_adds_prop_patch(self):
        r = parse("change the background to night", attached_images=1)
        assert "prop_patch" in r.required_stages


class TestMultiReferenceCompose:
    def test_two_attachments_compose(self):
        r = parse("combine these two outfits", attached_images=2)
        assert r.decision.kind is RequestKind.MULTI_IMAGE_COMPOSE
        assert "reference_encode" in r.required_stages
        assert r.single_panel is not None

    def test_moodboard_keyword(self):
        r = parse("use this as a moodboard", attached_images=1)
        assert r.decision.kind is RequestKind.MULTI_IMAGE_COMPOSE


class TestComicSequence:
    def test_ten_panel_comic_sequence(self):
        r = parse("a 10 panel comic of Alice in her bedroom holding a red phone")
        assert r.decision.kind is RequestKind.COMIC_SEQUENCE
        assert r.sequence is not None
        seq = r.sequence
        assert isinstance(seq, ComicSequenceSpec)
        assert seq.panel_count == 10
        # 10 panels falls back to a horizontal strip.
        assert seq.output_layout is OutputLayout.HORIZONTAL_STRIP
        # First/last roles are assigned.
        assert seq.ordered_panels[0].panel_role is PanelRole.ESTABLISHING
        assert seq.ordered_panels[-1].panel_role is PanelRole.PUNCHLINE
        # Prop registered once at sequence level.
        prop_keys = {k for k, _ in seq.prop_states}
        assert "red_phone" in prop_keys
        # Every panel references the prop.
        for panel in seq.ordered_panels:
            assert any(req.prop_key == "red_phone" for req in panel.prop_requirements)

    def test_four_panel_uses_grid_layout(self):
        r = parse("4-panel comic about a cat")
        assert r.sequence.output_layout is OutputLayout.GRID_2X2
        assert r.sequence.panel_count == 4

    def test_six_panel_uses_grid_2x3(self):
        r = parse("6 panel storyboard of a chase")
        assert r.sequence.output_layout is OutputLayout.GRID_2X3

    def test_character_hint_registers_state(self):
        r = parse(
            "4 panel comic of Alice in her bedroom",
            character_hint={"character_key": "alice", "character_name": "Alice"},
        )
        seq = r.sequence
        char_keys = {k for k, _ in seq.character_states}
        assert "alice" in char_keys
        for panel in seq.ordered_panels:
            assert "alice" in panel.character_keys
            assert panel.primary_character_key == "alice"

    def test_sequence_serializes(self):
        r = parse("4 panel comic of a cat in a kitchen")
        d = r.sequence.to_dict()
        assert d["output_layout"] == "grid_2x2"
        assert len(d["ordered_panels"]) == 4


class TestSceneExtraction:
    def test_location_detected(self):
        r = parse("a girl in her bedroom at night")
        seq_or_panel = r.single_panel
        assert seq_or_panel.scene_description != ""

    def test_unknown_location_empty(self):
        r = parse("a vague drawing of nothing in particular")
        # No location keyword matched → scene_description may be empty/short.
        assert isinstance(r.single_panel.scene_description, str)


class TestOverlayInPanel:
    def test_quoted_text_creates_overlay_element(self):
        r = parse('a phone screen showing "you are late"')
        plan = r.single_panel.overlay_plan
        assert len(plan.elements) >= 1
        # Phone UI overlay was detected.
        kinds = {el.kind for el in plan.elements}
        assert OverlayKind.PHONE_UI in kinds
        # Text carried through.
        assert any(el.text == "you are late" for el in plan.elements)
        assert "overlay" in r.required_stages
