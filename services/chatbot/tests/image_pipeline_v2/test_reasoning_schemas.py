"""
Tests for image_pipeline.reasoning.schemas.

Covers:
    * Frozen / hashable / JSON round-trip behavior of all schemas.
    * Structural validation errors fire on bad input.
    * Cross-reference validation in ComicSequenceSpec.
    * Layout/panel-count compatibility rules.
    * with_revision() append-only semantics.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Ensure the workspace root is importable so `image_pipeline` resolves when
# pytest is invoked from `services/chatbot/`. Mirrors the bootstrap used by
# tests/test_anime_pipeline.py.
_ROOT = Path(__file__).resolve().parents[4]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import pytest

from image_pipeline.reasoning.schemas import (
    BoundingBox,
    CharacterAppearance,
    CharacterState,
    ComicSequenceSpec,
    EyeState,
    OutputLayout,
    OverlayElement,
    OverlayKind,
    OverlayPlan,
    PanelRole,
    PropRequirement,
    PropState,
    SceneState,
    SchemaValidationError,
    ShotType,
    SinglePanelSpec,
    ZoneRef,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def alice_char() -> CharacterState:
    return CharacterState(
        character_key="alice",
        character_name="Alice",
        appearance=CharacterAppearance(
            hair_color="blonde",
            hairstyle="long_straight",
            eye_color="blue",
            face_shape="oval",
            age_presentation="young_adult",
        ),
        source_series="wonderland",
        canonical_tags=("blonde hair", "blue eyes", "blue dress"),
        outfit_family="blue_dress",
        accessories=("hairband",),
        must_keep=("blonde hair", "blue eyes"),
        forbidden_drift=("brown hair", "short hair"),
        lora_hints=("alice_v1",),
    )


@pytest.fixture
def red_phone_prop() -> PropState:
    return PropState(
        prop_key="red_phone",
        label="Alice's red phone",
        canonical_tags=("red phone", "smartphone", "matte case"),
        color="red",
        size_class="medium",
        must_keep=("red color",),
        forbidden_drift=("blue phone", "flip phone"),
    )


@pytest.fixture
def id_card_prop() -> PropState:
    return PropState(
        prop_key="id_card",
        label="Student ID card",
        canonical_tags=("id card", "white card"),
        text_content="ALICE - WONDERLAND U",
        color="white",
    )


@pytest.fixture
def bedroom_scene() -> SceneState:
    return SceneState(
        location="bedroom",
        sub_location="bed",
        lighting="warm afternoon sun",
        time_of_day="afternoon",
        mood="cozy",
        camera_defaults=("eye-level", "shallow_dof"),
        palette_hints=("warm pastels",),
        lock_scene=True,
    )


@pytest.fixture
def panel_one() -> SinglePanelSpec:
    return SinglePanelSpec(
        panel_id="panel_001",
        shot_type=ShotType.MEDIUM,
        camera_angle="eye-level",
        scene_description="Alice on her bed holding her phone.",
        action_description="Alice is laughing at the phone screen.",
        expression="laughing",
        eye_state=EyeState.CLOSED,
        panel_role=PanelRole.SETUP,
        character_keys=("alice",),
        primary_character_key="alice",
        prop_requirements=(
            PropRequirement(
                prop_key="red_phone",
                must_appear=True,
                expected_zone=ZoneRef(col=1, row=1),
            ),
        ),
        continuity_must_keep=("same red phone", "same blonde hair"),
        forbidden_drift=("brown hair",),
        overlay_plan=OverlayPlan(
            elements=(
                OverlayElement(
                    element_id="title",
                    kind=OverlayKind.TITLE_BAR,
                    text="Chapter 1",
                    z_order=10,
                ),
            )
        ),
        aspect_ratio="4:5",
        seed=42,
    )


@pytest.fixture
def panel_two() -> SinglePanelSpec:
    return SinglePanelSpec(
        panel_id="panel_002",
        shot_type=ShotType.CLOSE_UP,
        action_description="Close-up of the phone screen showing a meme.",
        eye_state=EyeState.UNSPECIFIED,
        panel_role=PanelRole.INSERT,
        character_keys=(),
        prop_requirements=(
            PropRequirement(prop_key="red_phone", must_appear=True),
        ),
    )


@pytest.fixture
def sequence(
    alice_char: CharacterState,
    red_phone_prop: PropState,
    id_card_prop: PropState,
    bedroom_scene: SceneState,
    panel_one: SinglePanelSpec,
    panel_two: SinglePanelSpec,
) -> ComicSequenceSpec:
    return ComicSequenceSpec(
        sequence_id="seq_test_0001",
        global_story="Alice laughs at a meme on her phone, then shows her ID.",
        character_states=((alice_char.character_key, alice_char),),
        prop_states=(
            (red_phone_prop.prop_key, red_phone_prop),
            (id_card_prop.prop_key, id_card_prop),
        ),
        scene_state=bedroom_scene,
        ordered_panels=(panel_one, panel_two),
        output_layout=OutputLayout.HORIZONTAL_STRIP,
    )


# ---------------------------------------------------------------------------
# BoundingBox / ZoneRef
# ---------------------------------------------------------------------------


class TestBoundingBox:
    def test_iou_self_is_one(self) -> None:
        b = BoundingBox(0.1, 0.1, 0.5, 0.5)
        assert b.iou(b) == pytest.approx(1.0)

    def test_iou_disjoint_is_zero(self) -> None:
        a = BoundingBox(0.0, 0.0, 0.4, 0.4)
        b = BoundingBox(0.5, 0.5, 0.9, 0.9)
        assert a.iou(b) == 0.0

    def test_iou_partial_overlap(self) -> None:
        a = BoundingBox(0.0, 0.0, 0.5, 0.5)
        b = BoundingBox(0.25, 0.25, 0.75, 0.75)
        # inter = 0.25*0.25 = 0.0625; union = 0.25 + 0.25 - 0.0625 = 0.4375
        assert a.iou(b) == pytest.approx(0.0625 / 0.4375)

    @pytest.mark.parametrize(
        "args",
        [
            (-0.1, 0.0, 0.5, 0.5),
            (0.0, 0.0, 1.5, 0.5),
            (0.5, 0.5, 0.5, 0.9),  # x2 == x1
            (0.5, 0.5, 0.6, 0.5),  # y2 == y1
        ],
    )
    def test_invalid_box_raises(self, args: tuple[float, ...]) -> None:
        with pytest.raises(SchemaValidationError):
            BoundingBox(*args)

    def test_round_trip(self) -> None:
        b = BoundingBox(0.1, 0.2, 0.7, 0.8)
        assert BoundingBox.from_dict(b.to_dict()) == b


class TestZoneRef:
    def test_to_bbox_center(self) -> None:
        z = ZoneRef(col=1, row=1)
        bb = z.to_bbox()
        assert bb.x1 == pytest.approx(1 / 3)
        assert bb.x2 == pytest.approx(2 / 3)
        assert bb.y1 == pytest.approx(1 / 3)
        assert bb.y2 == pytest.approx(2 / 3)

    @pytest.mark.parametrize("col,row", [(-1, 0), (3, 0), (0, 4), (1.0, 1)])
    def test_invalid(self, col: int, row: int) -> None:
        with pytest.raises(SchemaValidationError):
            ZoneRef(col=col, row=row)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# CharacterState
# ---------------------------------------------------------------------------


class TestCharacterState:
    def test_round_trip(self, alice_char: CharacterState) -> None:
        restored = CharacterState.from_dict(alice_char.to_dict())
        assert restored == alice_char

    def test_frozen(self, alice_char: CharacterState) -> None:
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            alice_char.character_name = "Bob"  # type: ignore[misc]

    def test_hashable(self, alice_char: CharacterState) -> None:
        assert {alice_char} == {alice_char}

    def test_with_revision_appends(self, alice_char: CharacterState) -> None:
        bumped = alice_char.with_revision(notes="dyed hair red")
        assert bumped.revision == alice_char.revision + 1
        assert bumped.notes == "dyed hair red"
        # Original is unchanged.
        assert alice_char.notes == ""

    def test_invalid_key_raises(self) -> None:
        with pytest.raises(SchemaValidationError):
            CharacterState(character_key="bad key!", character_name="X")

    def test_missing_name_raises(self) -> None:
        with pytest.raises(SchemaValidationError):
            CharacterState(character_key="x", character_name="   ")

    def test_canonical_tags_must_be_non_empty_strings(self) -> None:
        with pytest.raises(SchemaValidationError):
            CharacterState(
                character_key="x",
                character_name="X",
                canonical_tags=("ok", ""),  # empty string forbidden
            )


# ---------------------------------------------------------------------------
# PropState
# ---------------------------------------------------------------------------


class TestPropState:
    def test_round_trip(self, red_phone_prop: PropState) -> None:
        assert PropState.from_dict(red_phone_prop.to_dict()) == red_phone_prop

    def test_with_revision(self, red_phone_prop: PropState) -> None:
        v2 = red_phone_prop.with_revision(color="black")
        assert v2.revision == red_phone_prop.revision + 1
        assert v2.color == "black"


# ---------------------------------------------------------------------------
# SceneState
# ---------------------------------------------------------------------------


class TestSceneState:
    def test_round_trip(self, bedroom_scene: SceneState) -> None:
        assert SceneState.from_dict(bedroom_scene.to_dict()) == bedroom_scene

    def test_lock_scene_default_true(self) -> None:
        assert SceneState().lock_scene is True


# ---------------------------------------------------------------------------
# Overlay
# ---------------------------------------------------------------------------


class TestOverlayPlan:
    def test_duplicate_element_id_raises(self) -> None:
        e1 = OverlayElement(element_id="a", kind=OverlayKind.CAPTION, text="x")
        e2 = OverlayElement(element_id="a", kind=OverlayKind.CAPTION, text="y")
        with pytest.raises(SchemaValidationError):
            OverlayPlan(elements=(e1, e2))

    def test_round_trip(self) -> None:
        plan = OverlayPlan(
            elements=(
                OverlayElement(
                    element_id="t1",
                    kind=OverlayKind.TITLE_BAR,
                    text="Hello",
                    bbox=BoundingBox(0, 0, 1, 0.1),
                    z_order=5,
                ),
                OverlayElement(
                    element_id="b1",
                    kind=OverlayKind.SPEECH_BUBBLE,
                    text="Hi!",
                    z_order=10,
                    extra=(("tail_dir", "left"),),
                ),
            )
        )
        restored = OverlayPlan.from_dict(plan.to_dict())
        assert restored == plan


# ---------------------------------------------------------------------------
# SinglePanelSpec
# ---------------------------------------------------------------------------


class TestSinglePanelSpec:
    def test_round_trip(self, panel_one: SinglePanelSpec) -> None:
        restored = SinglePanelSpec.from_dict(panel_one.to_dict())
        assert restored == panel_one

    def test_primary_character_must_be_in_keys(self) -> None:
        with pytest.raises(SchemaValidationError):
            SinglePanelSpec(
                panel_id="p1",
                shot_type=ShotType.MEDIUM,
                character_keys=("alice",),
                primary_character_key="bob",
            )

    def test_duplicate_prop_requirements_raises(self) -> None:
        with pytest.raises(SchemaValidationError):
            SinglePanelSpec(
                panel_id="p1",
                shot_type=ShotType.MEDIUM,
                prop_requirements=(
                    PropRequirement(prop_key="phone"),
                    PropRequirement(prop_key="phone"),
                ),
            )

    def test_aspect_ratio_must_be_w_colon_h(self) -> None:
        with pytest.raises(SchemaValidationError):
            SinglePanelSpec(panel_id="p1", shot_type=ShotType.MEDIUM, aspect_ratio="square")

    def test_with_revision_increments(self, panel_one: SinglePanelSpec) -> None:
        v2 = panel_one.with_revision(action_description="updated")
        assert v2.revision == panel_one.revision + 1
        assert v2.action_description == "updated"

    def test_new_panel_id_is_unique(self) -> None:
        ids = {SinglePanelSpec.new_panel_id() for _ in range(50)}
        assert len(ids) == 50


# ---------------------------------------------------------------------------
# ComicSequenceSpec
# ---------------------------------------------------------------------------


class TestComicSequenceSpec:
    def test_round_trip_via_json(self, sequence: ComicSequenceSpec) -> None:
        encoded = json.dumps(sequence.to_dict())
        decoded = json.loads(encoded)
        restored = ComicSequenceSpec.from_dict(decoded)
        assert restored == sequence

    def test_to_jsonable_is_json_dumpable(self, sequence: ComicSequenceSpec) -> None:
        # Should not raise.
        json.dumps(sequence.to_jsonable())

    def test_panel_references_unknown_character_raises(
        self, alice_char: CharacterState, bedroom_scene: SceneState
    ) -> None:
        bad_panel = SinglePanelSpec(
            panel_id="p1",
            shot_type=ShotType.MEDIUM,
            character_keys=("ghost",),
        )
        with pytest.raises(SchemaValidationError):
            ComicSequenceSpec(
                sequence_id="seq_x",
                global_story="x",
                character_states=((alice_char.character_key, alice_char),),
                scene_state=bedroom_scene,
                ordered_panels=(bad_panel,),
                output_layout=OutputLayout.SINGLE,
            )

    def test_panel_references_unknown_prop_raises(
        self, alice_char: CharacterState, bedroom_scene: SceneState
    ) -> None:
        bad_panel = SinglePanelSpec(
            panel_id="p1",
            shot_type=ShotType.MEDIUM,
            prop_requirements=(PropRequirement(prop_key="unknown_thing"),),
        )
        with pytest.raises(SchemaValidationError):
            ComicSequenceSpec(
                sequence_id="seq_x",
                global_story="x",
                character_states=((alice_char.character_key, alice_char),),
                scene_state=bedroom_scene,
                ordered_panels=(bad_panel,),
                output_layout=OutputLayout.SINGLE,
            )

    def test_layout_grid_2x2_requires_4_panels(
        self,
        alice_char: CharacterState,
        red_phone_prop: PropState,
        bedroom_scene: SceneState,
        panel_one: SinglePanelSpec,
    ) -> None:
        with pytest.raises(SchemaValidationError):
            ComicSequenceSpec(
                sequence_id="seq_x",
                global_story="x",
                character_states=((alice_char.character_key, alice_char),),
                prop_states=((red_phone_prop.prop_key, red_phone_prop),),
                scene_state=bedroom_scene,
                ordered_panels=(panel_one,),
                output_layout=OutputLayout.GRID_2X2,
            )

    def test_layout_single_requires_one_panel(
        self,
        alice_char: CharacterState,
        red_phone_prop: PropState,
        bedroom_scene: SceneState,
        panel_one: SinglePanelSpec,
        panel_two: SinglePanelSpec,
    ) -> None:
        with pytest.raises(SchemaValidationError):
            ComicSequenceSpec(
                sequence_id="seq_x",
                global_story="x",
                character_states=((alice_char.character_key, alice_char),),
                prop_states=((red_phone_prop.prop_key, red_phone_prop),),
                scene_state=bedroom_scene,
                ordered_panels=(panel_one, panel_two),
                output_layout=OutputLayout.SINGLE,
            )

    def test_duplicate_panel_id_raises(
        self,
        alice_char: CharacterState,
        red_phone_prop: PropState,
        bedroom_scene: SceneState,
        panel_one: SinglePanelSpec,
    ) -> None:
        with pytest.raises(SchemaValidationError):
            ComicSequenceSpec(
                sequence_id="seq_x",
                global_story="x",
                character_states=((alice_char.character_key, alice_char),),
                prop_states=((red_phone_prop.prop_key, red_phone_prop),),
                scene_state=bedroom_scene,
                ordered_panels=(panel_one, panel_one),
                output_layout=OutputLayout.HORIZONTAL_STRIP,
            )

    def test_must_have_at_least_one_panel(
        self, alice_char: CharacterState, bedroom_scene: SceneState
    ) -> None:
        with pytest.raises(SchemaValidationError):
            ComicSequenceSpec(
                sequence_id="seq_x",
                global_story="x",
                character_states=((alice_char.character_key, alice_char),),
                scene_state=bedroom_scene,
                ordered_panels=(),
                output_layout=OutputLayout.SINGLE,
            )

    def test_lookup_helpers(
        self,
        sequence: ComicSequenceSpec,
        alice_char: CharacterState,
        red_phone_prop: PropState,
        panel_one: SinglePanelSpec,
    ) -> None:
        assert sequence.get_character("alice") == alice_char
        assert sequence.get_character("ghost") is None
        assert sequence.get_prop("red_phone") == red_phone_prop
        assert sequence.get_prop("ghost") is None
        assert sequence.get_panel("panel_001") == panel_one
        assert sequence.get_panel("missing") is None
        assert sequence.is_multi_panel
        assert sequence.panel_count == 2

    def test_with_revision(self, sequence: ComicSequenceSpec) -> None:
        v2 = sequence.with_revision(notes="updated")
        assert v2.revision == sequence.revision + 1
        assert v2.notes == "updated"
        # Original untouched.
        assert sequence.notes == ""

    def test_character_states_accepts_mapping(
        self,
        alice_char: CharacterState,
        bedroom_scene: SceneState,
        panel_one: SinglePanelSpec,
    ) -> None:
        # Pass a plain dict; should be coerced into a tuple of pairs.
        seq = ComicSequenceSpec(
            sequence_id="seq_dict",
            global_story="x",
            character_states={alice_char.character_key: alice_char},  # type: ignore[arg-type]
            prop_states={},  # type: ignore[arg-type]
            scene_state=bedroom_scene,
            ordered_panels=(
                SinglePanelSpec(
                    panel_id="solo",
                    shot_type=ShotType.MEDIUM,
                    character_keys=("alice",),
                ),
            ),
            output_layout=OutputLayout.SINGLE,
        )
        assert seq.get_character("alice") == alice_char
