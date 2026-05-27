"""
image_pipeline.reasoning.schemas — Panel spec and state contracts.

These are the canonical, frozen, JSON-safe data classes consumed by every
reasoning module. They model the SKILL.md "Required state objects" section:

    CharacterState, PropState, SceneState,
    SinglePanelSpec, ComicSequenceSpec.

Design rules
------------
* All dataclasses are ``frozen=True`` and ``slots=True``. Mutation is forbidden;
  callers produce a new instance via ``dataclasses.replace`` or the helper
  ``with_*`` methods provided on selected types.
* All collection fields are tuples (not lists) so equality is structural and
  the objects are hashable.
* Every type round-trips through ``to_dict`` / ``from_dict`` so it can be
  persisted in ``RunManifest`` JSON or sent over SSE without custom encoders.
* No I/O. No LLM calls. No ComfyUI imports. This module is safe to import
  from anywhere, including the request hot path.
* No third-party dependency beyond the standard library.

The schemas are intentionally permissive at construction time (only structural
checks fire in ``__post_init__``). Semantic validation — for example, "the
panel's referenced character_key is present in ComicSequenceSpec.character_states"
— is the job of ``image_pipeline.reasoning.panel_spec_validator``, added in a
later commit.
"""

from __future__ import annotations

import enum
import re
import uuid
from dataclasses import asdict, dataclass, field, fields, is_dataclass, replace
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class SchemaValidationError(ValueError):
    """Raised when a schema field fails a structural check."""


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ShotType(str, enum.Enum):
    """Camera framing for a single panel."""

    EXTREME_CLOSE_UP = "extreme_close_up"
    CLOSE_UP = "close_up"
    MEDIUM_CLOSE_UP = "medium_close_up"
    MEDIUM = "medium"
    MEDIUM_WIDE = "medium_wide"
    WIDE = "wide"
    EXTREME_WIDE = "extreme_wide"
    POV = "pov"
    OTS = "over_the_shoulder"
    TOP_DOWN = "top_down"
    LOW_ANGLE = "low_angle"
    DUTCH = "dutch"


class EyeState(str, enum.Enum):
    """Discrete eye states the evaluator can verify against the rendered panel."""

    OPEN = "open"
    HALF = "half"
    CLOSED = "closed"
    WINK_LEFT = "wink_left"
    WINK_RIGHT = "wink_right"
    WIDE = "wide"
    SQUINT = "squint"
    UNSPECIFIED = "unspecified"


class PanelRole(str, enum.Enum):
    """Narrative role of a panel inside a comic sequence."""

    ESTABLISHING = "establishing"
    SETUP = "setup"
    BEAT = "beat"
    REACTION = "reaction"
    PUNCHLINE = "punchline"
    CLOSING = "closing"
    INSERT = "insert"  # Cutaway, e.g. phone screen.


class OverlayKind(str, enum.Enum):
    """Overlay element kinds rendered by the compositor (not by the diffusion model)."""

    TITLE_BAR = "title_bar"
    SPEECH_BUBBLE = "speech_bubble"
    THOUGHT_BUBBLE = "thought_bubble"
    CAPTION = "caption"
    SFX = "sfx"
    PHONE_UI = "phone_ui"
    ID_CARD = "id_card"
    PANEL_LABEL = "panel_label"
    WATERMARK = "watermark"


class OutputLayout(str, enum.Enum):
    """Final assembly layout for a comic sequence."""

    SINGLE = "single"
    HORIZONTAL_STRIP = "horizontal_strip"
    VERTICAL_STRIP = "vertical_strip"
    GRID_2X2 = "grid_2x2"
    GRID_2X3 = "grid_2x3"
    GRID_3X3 = "grid_3x3"
    CUSTOM = "custom"


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------


_ID_RE = re.compile(r"^[A-Za-z0-9_.\-:]{1,128}$")


def _check_id(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not _ID_RE.match(value):
        raise SchemaValidationError(
            f"{field_name} must match {_ID_RE.pattern!r}, got {value!r}"
        )


@dataclass(frozen=True, slots=True)
class BoundingBox:
    """Normalized xyxy bounding box, all values in [0.0, 1.0]."""

    x1: float
    y1: float
    x2: float
    y2: float

    def __post_init__(self) -> None:
        for name in ("x1", "y1", "x2", "y2"):
            v = getattr(self, name)
            if not isinstance(v, (int, float)) or not (0.0 <= float(v) <= 1.0):
                raise SchemaValidationError(
                    f"BoundingBox.{name} must be in [0,1], got {v!r}"
                )
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise SchemaValidationError(
                f"BoundingBox must satisfy x2>x1 and y2>y1, got {self!r}"
            )

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height

    def iou(self, other: "BoundingBox") -> float:
        ix1 = max(self.x1, other.x1)
        iy1 = max(self.y1, other.y1)
        ix2 = min(self.x2, other.x2)
        iy2 = min(self.y2, other.y2)
        iw = max(0.0, ix2 - ix1)
        ih = max(0.0, iy2 - iy1)
        inter = iw * ih
        union = self.area + other.area - inter
        return inter / union if union > 0 else 0.0

    def to_dict(self) -> dict[str, float]:
        return {"x1": self.x1, "y1": self.y1, "x2": self.x2, "y2": self.y2}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "BoundingBox":
        return cls(
            x1=float(data["x1"]),
            y1=float(data["y1"]),
            x2=float(data["x2"]),
            y2=float(data["y2"]),
        )


@dataclass(frozen=True, slots=True)
class ZoneRef:
    """
    Coarse 3x3 zone reference, used by the evaluator's PROP_PLACEMENT dimension.

    ``col`` and ``row`` are in {0, 1, 2}, where (0, 0) is the top-left zone.
    Multiple zones may be combined via ``ZoneRef.union`` (returns a tuple).
    """

    col: int
    row: int

    def __post_init__(self) -> None:
        for name in ("col", "row"):
            v = getattr(self, name)
            if not isinstance(v, int) or not (0 <= v <= 2):
                raise SchemaValidationError(
                    f"ZoneRef.{name} must be int in [0,2], got {v!r}"
                )

    def to_bbox(self) -> BoundingBox:
        step = 1.0 / 3.0
        return BoundingBox(
            x1=self.col * step,
            y1=self.row * step,
            x2=(self.col + 1) * step,
            y2=(self.row + 1) * step,
        )

    def to_dict(self) -> dict[str, int]:
        return {"col": self.col, "row": self.row}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ZoneRef":
        return cls(col=int(data["col"]), row=int(data["row"]))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _as_str_tuple(values: Iterable[Any] | None, field_name: str) -> tuple[str, ...]:
    if values is None:
        return ()
    out: list[str] = []
    for i, v in enumerate(values):
        if not isinstance(v, str) or not v.strip():
            raise SchemaValidationError(
                f"{field_name}[{i}] must be a non-empty string, got {v!r}"
            )
        out.append(v.strip())
    return tuple(out)


def _enum_from(raw: Any, enum_cls: type[enum.Enum], field_name: str) -> enum.Enum:
    if isinstance(raw, enum_cls):
        return raw
    try:
        return enum_cls(raw)
    except (ValueError, KeyError) as exc:
        valid = ", ".join(e.value for e in enum_cls)
        raise SchemaValidationError(
            f"{field_name} must be one of [{valid}], got {raw!r}"
        ) from exc


def _to_jsonable(value: Any) -> Any:
    """Recursively convert dataclasses, enums, tuples to JSON-safe primitives."""
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, BoundingBox) or isinstance(value, ZoneRef):
        return value.to_dict()
    if is_dataclass(value):
        if hasattr(value, "to_dict"):
            return value.to_dict()  # type: ignore[no-any-return]
        return {k: _to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_to_jsonable(v) for v in value]
    raise SchemaValidationError(
        f"Value of type {type(value).__name__} is not JSON-safe"
    )


# ---------------------------------------------------------------------------
# Character state
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class CharacterAppearance:
    """The visual sub-bundle of a CharacterState. Drift is computed against this."""

    hair_color: str = ""
    hairstyle: str = ""
    eye_color: str = ""
    face_shape: str = ""
    skin_tone: str = ""
    age_presentation: str = ""  # e.g. "teen", "adult", "elderly"
    height_class: str = ""  # e.g. "petite", "tall"
    body_type: str = ""
    distinguishing_marks: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "distinguishing_marks",
            _as_str_tuple(self.distinguishing_marks, "distinguishing_marks"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "hair_color": self.hair_color,
            "hairstyle": self.hairstyle,
            "eye_color": self.eye_color,
            "face_shape": self.face_shape,
            "skin_tone": self.skin_tone,
            "age_presentation": self.age_presentation,
            "height_class": self.height_class,
            "body_type": self.body_type,
            "distinguishing_marks": list(self.distinguishing_marks),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CharacterAppearance":
        return cls(
            hair_color=str(data.get("hair_color", "")),
            hairstyle=str(data.get("hairstyle", "")),
            eye_color=str(data.get("eye_color", "")),
            face_shape=str(data.get("face_shape", "")),
            skin_tone=str(data.get("skin_tone", "")),
            age_presentation=str(data.get("age_presentation", "")),
            height_class=str(data.get("height_class", "")),
            body_type=str(data.get("body_type", "")),
            distinguishing_marks=tuple(data.get("distinguishing_marks", ()) or ()),
        )


@dataclass(frozen=True, slots=True)
class CharacterState:
    """
    Frozen identity for one character within a single run.

    Resolved once by ``character_state_manager`` from the user's ``<character>``
    selection plus the registry, then reused by every panel in the run unless
    explicitly mutated by an in-prompt change instruction.

    ``revision`` increments only when an explicit change is recorded; it never
    rolls back. The full lineage is stored in ``RunManifest.character_history``
    (added in a later commit).
    """

    character_key: str
    character_name: str
    appearance: CharacterAppearance = field(default_factory=CharacterAppearance)
    source_series: str = ""
    canonical_tags: tuple[str, ...] = ()
    outfit_family: str = ""
    accessories: tuple[str, ...] = ()
    must_keep: tuple[str, ...] = ()
    forbidden_drift: tuple[str, ...] = ()
    lora_hints: tuple[
        str, ...
    ] = ()  # Optional LoRA names known to render this character.
    reference_image_keys: tuple[str, ...] = ()  # IDs into the run's reference store.
    revision: int = 0
    created_at: str = field(default_factory=_now_iso)
    notes: str = ""

    def __post_init__(self) -> None:
        _check_id(self.character_key, "CharacterState.character_key")
        if not isinstance(self.character_name, str) or not self.character_name.strip():
            raise SchemaValidationError("CharacterState.character_name is required")
        if not isinstance(self.appearance, CharacterAppearance):
            raise SchemaValidationError(
                "CharacterState.appearance must be a CharacterAppearance"
            )
        if not isinstance(self.revision, int) or self.revision < 0:
            raise SchemaValidationError(
                "CharacterState.revision must be a non-negative int"
            )
        for name in (
            "canonical_tags",
            "accessories",
            "must_keep",
            "forbidden_drift",
            "lora_hints",
            "reference_image_keys",
        ):
            object.__setattr__(self, name, _as_str_tuple(getattr(self, name), name))

    def with_revision(self, **changes: Any) -> "CharacterState":
        """Return a new CharacterState with ``revision`` bumped and fields applied."""
        return replace(self, revision=self.revision + 1, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "character_key": self.character_key,
            "character_name": self.character_name,
            "appearance": self.appearance.to_dict(),
            "source_series": self.source_series,
            "canonical_tags": list(self.canonical_tags),
            "outfit_family": self.outfit_family,
            "accessories": list(self.accessories),
            "must_keep": list(self.must_keep),
            "forbidden_drift": list(self.forbidden_drift),
            "lora_hints": list(self.lora_hints),
            "reference_image_keys": list(self.reference_image_keys),
            "revision": self.revision,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "CharacterState":
        appearance_raw = data.get("appearance") or {}
        appearance = (
            appearance_raw
            if isinstance(appearance_raw, CharacterAppearance)
            else CharacterAppearance.from_dict(appearance_raw)
        )
        return cls(
            character_key=str(data["character_key"]),
            character_name=str(data["character_name"]),
            appearance=appearance,
            source_series=str(data.get("source_series", "")),
            canonical_tags=tuple(data.get("canonical_tags", ()) or ()),
            outfit_family=str(data.get("outfit_family", "")),
            accessories=tuple(data.get("accessories", ()) or ()),
            must_keep=tuple(data.get("must_keep", ()) or ()),
            forbidden_drift=tuple(data.get("forbidden_drift", ()) or ()),
            lora_hints=tuple(data.get("lora_hints", ()) or ()),
            reference_image_keys=tuple(data.get("reference_image_keys", ()) or ()),
            revision=int(data.get("revision", 0)),
            created_at=str(data.get("created_at") or _now_iso()),
            notes=str(data.get("notes", "")),
        )


# ---------------------------------------------------------------------------
# Prop state
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PropState:
    """
    A single recurring prop (phone, ID card, bed, pillow, tape, ...).

    A run holds a ``dict[str, PropState]`` keyed by ``prop_key``. The evaluator
    diffs detected props against this state; the correction router consults
    ``canonical_tags`` and ``forbidden_drift`` when it builds an inpaint prompt.
    """

    prop_key: str
    label: str
    canonical_tags: tuple[str, ...] = ()
    color: str = ""
    size_class: str = ""  # e.g. "small", "medium", "large".
    text_content: str = ""  # For props that carry text, e.g. ID card.
    material: str = ""
    forbidden_drift: tuple[str, ...] = ()
    must_keep: tuple[str, ...] = ()
    is_recurring: bool = True
    revision: int = 0
    notes: str = ""

    def __post_init__(self) -> None:
        _check_id(self.prop_key, "PropState.prop_key")
        if not isinstance(self.label, str) or not self.label.strip():
            raise SchemaValidationError("PropState.label is required")
        if not isinstance(self.revision, int) or self.revision < 0:
            raise SchemaValidationError("PropState.revision must be a non-negative int")
        for name in ("canonical_tags", "forbidden_drift", "must_keep"):
            object.__setattr__(self, name, _as_str_tuple(getattr(self, name), name))

    def with_revision(self, **changes: Any) -> "PropState":
        return replace(self, revision=self.revision + 1, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "prop_key": self.prop_key,
            "label": self.label,
            "canonical_tags": list(self.canonical_tags),
            "color": self.color,
            "size_class": self.size_class,
            "text_content": self.text_content,
            "material": self.material,
            "forbidden_drift": list(self.forbidden_drift),
            "must_keep": list(self.must_keep),
            "is_recurring": self.is_recurring,
            "revision": self.revision,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PropState":
        return cls(
            prop_key=str(data["prop_key"]),
            label=str(data["label"]),
            canonical_tags=tuple(data.get("canonical_tags", ()) or ()),
            color=str(data.get("color", "")),
            size_class=str(data.get("size_class", "")),
            text_content=str(data.get("text_content", "")),
            material=str(data.get("material", "")),
            forbidden_drift=tuple(data.get("forbidden_drift", ()) or ()),
            must_keep=tuple(data.get("must_keep", ()) or ()),
            is_recurring=bool(data.get("is_recurring", True)),
            revision=int(data.get("revision", 0)),
            notes=str(data.get("notes", "")),
        )


# ---------------------------------------------------------------------------
# Scene state
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SceneState:
    """
    Locked scene context shared by every panel in a sequence.

    When ``lock_scene`` is True, the evaluator's SCENE_CONTINUITY dimension is
    enforced; otherwise it is recorded as a warning only.
    """

    location: str = ""
    sub_location: str = ""
    lighting: str = ""
    time_of_day: str = ""
    mood: str = ""
    weather: str = ""
    camera_defaults: tuple[str, ...] = ()
    palette_hints: tuple[str, ...] = ()
    lock_scene: bool = True
    revision: int = 0
    notes: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.revision, int) or self.revision < 0:
            raise SchemaValidationError(
                "SceneState.revision must be a non-negative int"
            )
        for name in ("camera_defaults", "palette_hints"):
            object.__setattr__(self, name, _as_str_tuple(getattr(self, name), name))

    def with_revision(self, **changes: Any) -> "SceneState":
        return replace(self, revision=self.revision + 1, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "location": self.location,
            "sub_location": self.sub_location,
            "lighting": self.lighting,
            "time_of_day": self.time_of_day,
            "mood": self.mood,
            "weather": self.weather,
            "camera_defaults": list(self.camera_defaults),
            "palette_hints": list(self.palette_hints),
            "lock_scene": self.lock_scene,
            "revision": self.revision,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SceneState":
        return cls(
            location=str(data.get("location", "")),
            sub_location=str(data.get("sub_location", "")),
            lighting=str(data.get("lighting", "")),
            time_of_day=str(data.get("time_of_day", "")),
            mood=str(data.get("mood", "")),
            weather=str(data.get("weather", "")),
            camera_defaults=tuple(data.get("camera_defaults", ()) or ()),
            palette_hints=tuple(data.get("palette_hints", ()) or ()),
            lock_scene=bool(data.get("lock_scene", True)),
            revision=int(data.get("revision", 0)),
            notes=str(data.get("notes", "")),
        )


# ---------------------------------------------------------------------------
# Panel-level building blocks
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PropRequirement:
    """A prop that must (or must not) appear in a single panel."""

    prop_key: str
    must_appear: bool = True
    expected_zone: ZoneRef | None = None
    expected_bbox: BoundingBox | None = None
    state_overrides: tuple[tuple[str, str], ...] = ()  # additive PropState patches
    notes: str = ""

    def __post_init__(self) -> None:
        _check_id(self.prop_key, "PropRequirement.prop_key")
        if self.expected_zone is not None and not isinstance(
            self.expected_zone, ZoneRef
        ):
            raise SchemaValidationError(
                "PropRequirement.expected_zone must be a ZoneRef or None"
            )
        if self.expected_bbox is not None and not isinstance(
            self.expected_bbox, BoundingBox
        ):
            raise SchemaValidationError(
                "PropRequirement.expected_bbox must be a BoundingBox or None"
            )
        cleaned: list[tuple[str, str]] = []
        for i, item in enumerate(self.state_overrides or ()):
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not isinstance(item[1], str)
            ):
                raise SchemaValidationError(
                    f"PropRequirement.state_overrides[{i}] must be a (str, str) tuple"
                )
            cleaned.append((item[0], item[1]))
        object.__setattr__(self, "state_overrides", tuple(cleaned))

    def to_dict(self) -> dict[str, Any]:
        return {
            "prop_key": self.prop_key,
            "must_appear": self.must_appear,
            "expected_zone": (
                self.expected_zone.to_dict() if self.expected_zone else None
            ),
            "expected_bbox": (
                self.expected_bbox.to_dict() if self.expected_bbox else None
            ),
            "state_overrides": [list(item) for item in self.state_overrides],
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "PropRequirement":
        zone = data.get("expected_zone")
        bbox = data.get("expected_bbox")
        overrides_raw = data.get("state_overrides", ()) or ()
        overrides = tuple((str(p[0]), str(p[1])) for p in overrides_raw)
        return cls(
            prop_key=str(data["prop_key"]),
            must_appear=bool(data.get("must_appear", True)),
            expected_zone=ZoneRef.from_dict(zone) if zone else None,
            expected_bbox=BoundingBox.from_dict(bbox) if bbox else None,
            state_overrides=overrides,
            notes=str(data.get("notes", "")),
        )


@dataclass(frozen=True, slots=True)
class OverlayElement:
    """A single overlay element drawn by the compositor on top of the panel."""

    element_id: str
    kind: OverlayKind
    text: str = ""
    bbox: BoundingBox | None = None  # If None, compositor uses kind-default placement.
    style_key: str = "default"  # Reference into configs/overlay.yaml templates.
    z_order: int = 0
    locale: str = "en"
    extra: tuple[tuple[str, str], ...] = ()  # JSON-safe key/value pairs.

    def __post_init__(self) -> None:
        _check_id(self.element_id, "OverlayElement.element_id")
        object.__setattr__(
            self, "kind", _enum_from(self.kind, OverlayKind, "OverlayElement.kind")
        )
        if self.bbox is not None and not isinstance(self.bbox, BoundingBox):
            raise SchemaValidationError(
                "OverlayElement.bbox must be a BoundingBox or None"
            )
        if not isinstance(self.z_order, int):
            raise SchemaValidationError("OverlayElement.z_order must be an int")
        cleaned: list[tuple[str, str]] = []
        for i, item in enumerate(self.extra or ()):
            if (
                not isinstance(item, tuple)
                or len(item) != 2
                or not isinstance(item[0], str)
                or not isinstance(item[1], str)
            ):
                raise SchemaValidationError(
                    f"OverlayElement.extra[{i}] must be a (str, str) tuple"
                )
            cleaned.append((item[0], item[1]))
        object.__setattr__(self, "extra", tuple(cleaned))

    def to_dict(self) -> dict[str, Any]:
        return {
            "element_id": self.element_id,
            "kind": self.kind.value,
            "text": self.text,
            "bbox": self.bbox.to_dict() if self.bbox else None,
            "style_key": self.style_key,
            "z_order": self.z_order,
            "locale": self.locale,
            "extra": [list(item) for item in self.extra],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OverlayElement":
        bbox = data.get("bbox")
        extra_raw = data.get("extra", ()) or ()
        extra = tuple((str(p[0]), str(p[1])) for p in extra_raw)
        return cls(
            element_id=str(data["element_id"]),
            kind=OverlayKind(data["kind"]),
            text=str(data.get("text", "")),
            bbox=BoundingBox.from_dict(bbox) if bbox else None,
            style_key=str(data.get("style_key", "default")),
            z_order=int(data.get("z_order", 0)),
            locale=str(data.get("locale", "en")),
            extra=extra,
        )


@dataclass(frozen=True, slots=True)
class OverlayPlan:
    """All overlay elements for one panel, drawn in ``z_order`` ascending."""

    elements: tuple[OverlayElement, ...] = ()

    def __post_init__(self) -> None:
        for i, el in enumerate(self.elements):
            if not isinstance(el, OverlayElement):
                raise SchemaValidationError(
                    f"OverlayPlan.elements[{i}] must be OverlayElement, got {type(el).__name__}"
                )
        seen: set[str] = set()
        for el in self.elements:
            if el.element_id in seen:
                raise SchemaValidationError(
                    f"OverlayPlan.elements has duplicate element_id={el.element_id!r}"
                )
            seen.add(el.element_id)

    def to_dict(self) -> dict[str, Any]:
        return {"elements": [el.to_dict() for el in self.elements]}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "OverlayPlan":
        elements = tuple(
            OverlayElement.from_dict(item) for item in data.get("elements", ()) or ()
        )
        return cls(elements=elements)


# ---------------------------------------------------------------------------
# SinglePanelSpec
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SinglePanelSpec:
    """
    Strict, planner-emitted contract for one rendered image.

    Consumed by:
        * ``execution_planner``           — to build the ``ExecutionPlan``.
        * ``correction_target_generator`` — to know what ``must_keep``.
        * ``continuity_evaluator``        — to score the rendered panel.
        * ``overlay.compositor``          — to render ``overlay_plan``.
    """

    panel_id: str
    shot_type: ShotType
    camera_angle: str = ""
    scene_description: str = ""
    action_description: str = ""
    expression: str = ""
    eye_state: EyeState = EyeState.UNSPECIFIED
    panel_role: PanelRole = PanelRole.BEAT
    character_keys: tuple[str, ...] = ()  # IDs into ComicSequenceSpec.character_states.
    primary_character_key: str | None = None
    prop_requirements: tuple[PropRequirement, ...] = ()
    continuity_must_keep: tuple[
        str, ...
    ] = ()  # Free-form bullets, e.g. "same red phone".
    forbidden_drift: tuple[str, ...] = ()
    overlay_plan: OverlayPlan = field(default_factory=OverlayPlan)
    nsfw_flag: bool = False
    aspect_ratio: str = "1:1"  # "1:1", "4:5", "16:9", ...
    seed: int | None = None  # Optional fixed seed.
    extra_positive_tags: tuple[str, ...] = ()
    extra_negative_tags: tuple[str, ...] = ()
    revision: int = 0
    notes: str = ""

    def __post_init__(self) -> None:
        _check_id(self.panel_id, "SinglePanelSpec.panel_id")
        object.__setattr__(
            self,
            "shot_type",
            _enum_from(self.shot_type, ShotType, "SinglePanelSpec.shot_type"),
        )
        object.__setattr__(
            self,
            "eye_state",
            _enum_from(self.eye_state, EyeState, "SinglePanelSpec.eye_state"),
        )
        object.__setattr__(
            self,
            "panel_role",
            _enum_from(self.panel_role, PanelRole, "SinglePanelSpec.panel_role"),
        )
        for name in (
            "character_keys",
            "continuity_must_keep",
            "forbidden_drift",
            "extra_positive_tags",
            "extra_negative_tags",
        ):
            object.__setattr__(self, name, _as_str_tuple(getattr(self, name), name))
        for ck in self.character_keys:
            _check_id(ck, "SinglePanelSpec.character_keys[*]")
        for i, req in enumerate(self.prop_requirements):
            if not isinstance(req, PropRequirement):
                raise SchemaValidationError(
                    f"SinglePanelSpec.prop_requirements[{i}] must be PropRequirement"
                )
        prop_keys_seen: set[str] = set()
        for req in self.prop_requirements:
            if req.prop_key in prop_keys_seen:
                raise SchemaValidationError(
                    f"SinglePanelSpec.prop_requirements has duplicate prop_key={req.prop_key!r}"
                )
            prop_keys_seen.add(req.prop_key)
        if self.primary_character_key is not None:
            _check_id(
                self.primary_character_key, "SinglePanelSpec.primary_character_key"
            )
            if self.primary_character_key not in self.character_keys:
                raise SchemaValidationError(
                    "SinglePanelSpec.primary_character_key must be in character_keys"
                )
        if not isinstance(self.overlay_plan, OverlayPlan):
            raise SchemaValidationError(
                "SinglePanelSpec.overlay_plan must be an OverlayPlan"
            )
        if self.seed is not None and (not isinstance(self.seed, int) or self.seed < 0):
            raise SchemaValidationError(
                "SinglePanelSpec.seed must be a non-negative int"
            )
        if not isinstance(self.revision, int) or self.revision < 0:
            raise SchemaValidationError(
                "SinglePanelSpec.revision must be a non-negative int"
            )
        if not isinstance(self.aspect_ratio, str) or ":" not in self.aspect_ratio:
            raise SchemaValidationError(
                f"SinglePanelSpec.aspect_ratio must look like 'W:H', got {self.aspect_ratio!r}"
            )

    @staticmethod
    def new_panel_id(prefix: str = "panel") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:8]}"

    def with_revision(self, **changes: Any) -> "SinglePanelSpec":
        return replace(self, revision=self.revision + 1, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "panel_id": self.panel_id,
            "shot_type": self.shot_type.value,
            "camera_angle": self.camera_angle,
            "scene_description": self.scene_description,
            "action_description": self.action_description,
            "expression": self.expression,
            "eye_state": self.eye_state.value,
            "panel_role": self.panel_role.value,
            "character_keys": list(self.character_keys),
            "primary_character_key": self.primary_character_key,
            "prop_requirements": [r.to_dict() for r in self.prop_requirements],
            "continuity_must_keep": list(self.continuity_must_keep),
            "forbidden_drift": list(self.forbidden_drift),
            "overlay_plan": self.overlay_plan.to_dict(),
            "nsfw_flag": self.nsfw_flag,
            "aspect_ratio": self.aspect_ratio,
            "seed": self.seed,
            "extra_positive_tags": list(self.extra_positive_tags),
            "extra_negative_tags": list(self.extra_negative_tags),
            "revision": self.revision,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "SinglePanelSpec":
        overlay_raw = data.get("overlay_plan") or {}
        overlay = (
            overlay_raw
            if isinstance(overlay_raw, OverlayPlan)
            else OverlayPlan.from_dict(overlay_raw)
        )
        return cls(
            panel_id=str(data["panel_id"]),
            shot_type=ShotType(data["shot_type"]),
            camera_angle=str(data.get("camera_angle", "")),
            scene_description=str(data.get("scene_description", "")),
            action_description=str(data.get("action_description", "")),
            expression=str(data.get("expression", "")),
            eye_state=EyeState(data.get("eye_state", EyeState.UNSPECIFIED.value)),
            panel_role=PanelRole(data.get("panel_role", PanelRole.BEAT.value)),
            character_keys=tuple(data.get("character_keys", ()) or ()),
            primary_character_key=(
                str(data["primary_character_key"])
                if data.get("primary_character_key") is not None
                else None
            ),
            prop_requirements=tuple(
                PropRequirement.from_dict(r)
                for r in data.get("prop_requirements", ()) or ()
            ),
            continuity_must_keep=tuple(data.get("continuity_must_keep", ()) or ()),
            forbidden_drift=tuple(data.get("forbidden_drift", ()) or ()),
            overlay_plan=overlay,
            nsfw_flag=bool(data.get("nsfw_flag", False)),
            aspect_ratio=str(data.get("aspect_ratio", "1:1")),
            seed=(int(data["seed"]) if data.get("seed") is not None else None),
            extra_positive_tags=tuple(data.get("extra_positive_tags", ()) or ()),
            extra_negative_tags=tuple(data.get("extra_negative_tags", ()) or ()),
            revision=int(data.get("revision", 0)),
            notes=str(data.get("notes", "")),
        )


# ---------------------------------------------------------------------------
# ComicSequenceSpec
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ComicSequenceSpec:
    """Top-level reasoning artifact for a single user request, single or multi-panel."""

    sequence_id: str
    global_story: str
    character_states: tuple[tuple[str, CharacterState], ...] = ()
    prop_states: tuple[tuple[str, PropState], ...] = ()
    scene_state: SceneState = field(default_factory=SceneState)
    ordered_panels: tuple[SinglePanelSpec, ...] = ()
    output_layout: OutputLayout = OutputLayout.SINGLE
    max_correction_rounds: int = 2
    revision: int = 0
    created_at: str = field(default_factory=_now_iso)
    notes: str = ""

    def __post_init__(self) -> None:
        _check_id(self.sequence_id, "ComicSequenceSpec.sequence_id")
        object.__setattr__(
            self,
            "output_layout",
            _enum_from(
                self.output_layout, OutputLayout, "ComicSequenceSpec.output_layout"
            ),
        )
        if not isinstance(self.scene_state, SceneState):
            raise SchemaValidationError(
                "ComicSequenceSpec.scene_state must be a SceneState"
            )
        if (
            not isinstance(self.max_correction_rounds, int)
            or self.max_correction_rounds < 0
        ):
            raise SchemaValidationError(
                "ComicSequenceSpec.max_correction_rounds must be a non-negative int"
            )
        if not isinstance(self.revision, int) or self.revision < 0:
            raise SchemaValidationError(
                "ComicSequenceSpec.revision must be a non-negative int"
            )
        # Coerce character_states / prop_states into validated tuples-of-pairs.
        char_pairs = self._coerce_pairs(
            self.character_states, CharacterState, "character_states"
        )
        prop_pairs = self._coerce_pairs(self.prop_states, PropState, "prop_states")
        object.__setattr__(self, "character_states", char_pairs)
        object.__setattr__(self, "prop_states", prop_pairs)
        # Panels.
        if not isinstance(self.ordered_panels, tuple):
            raise SchemaValidationError(
                "ComicSequenceSpec.ordered_panels must be a tuple"
            )
        for i, panel in enumerate(self.ordered_panels):
            if not isinstance(panel, SinglePanelSpec):
                raise SchemaValidationError(
                    f"ComicSequenceSpec.ordered_panels[{i}] must be SinglePanelSpec"
                )
        seen_panel_ids: set[str] = set()
        for panel in self.ordered_panels:
            if panel.panel_id in seen_panel_ids:
                raise SchemaValidationError(
                    f"ComicSequenceSpec.ordered_panels has duplicate panel_id={panel.panel_id!r}"
                )
            seen_panel_ids.add(panel.panel_id)
        # Layout / count compatibility.
        self._check_layout_compat(self.output_layout, len(self.ordered_panels))
        # Cross-references: every panel character_key must exist in character_states.
        char_keys = {k for k, _ in self.character_states}
        for panel in self.ordered_panels:
            for ck in panel.character_keys:
                if ck not in char_keys:
                    raise SchemaValidationError(
                        f"Panel {panel.panel_id!r} references unknown character_key={ck!r}"
                    )
        # Cross-references: every panel prop_requirement.prop_key must exist in prop_states.
        prop_keys = {k for k, _ in self.prop_states}
        for panel in self.ordered_panels:
            for req in panel.prop_requirements:
                if req.prop_key not in prop_keys:
                    raise SchemaValidationError(
                        f"Panel {panel.panel_id!r} references unknown prop_key={req.prop_key!r}"
                    )

    @staticmethod
    def _coerce_pairs(
        value: Any, item_cls: type, field_name: str
    ) -> tuple[tuple[str, Any], ...]:
        """Accept either ``Mapping[str, item_cls]`` or ``Iterable[tuple[str, item_cls]]``."""
        if value is None:
            return ()
        if isinstance(value, Mapping):
            iterable: Iterable[tuple[str, Any]] = value.items()
        else:
            iterable = value
        out: list[tuple[str, Any]] = []
        seen: set[str] = set()
        for i, item in enumerate(iterable):
            if not isinstance(item, tuple) or len(item) != 2:
                raise SchemaValidationError(
                    f"ComicSequenceSpec.{field_name}[{i}] must be a (key, {item_cls.__name__}) pair"
                )
            key, val = item
            if not isinstance(key, str):
                raise SchemaValidationError(
                    f"ComicSequenceSpec.{field_name}[{i}] key must be a string"
                )
            _check_id(key, f"ComicSequenceSpec.{field_name}[{i}].key")
            if not isinstance(val, item_cls):
                raise SchemaValidationError(
                    f"ComicSequenceSpec.{field_name}[{i}] value must be {item_cls.__name__}"
                )
            if key in seen:
                raise SchemaValidationError(
                    f"ComicSequenceSpec.{field_name} has duplicate key={key!r}"
                )
            seen.add(key)
            out.append((key, val))
        return tuple(out)

    @staticmethod
    def _check_layout_compat(layout: OutputLayout, panel_count: int) -> None:
        if panel_count == 0:
            raise SchemaValidationError(
                "ComicSequenceSpec must contain at least one panel"
            )
        rules: dict[OutputLayout, tuple[int, ...] | None] = {
            OutputLayout.SINGLE: (1,),
            OutputLayout.HORIZONTAL_STRIP: None,
            OutputLayout.VERTICAL_STRIP: None,
            OutputLayout.GRID_2X2: (4,),
            OutputLayout.GRID_2X3: (6,),
            OutputLayout.GRID_3X3: (9,),
            OutputLayout.CUSTOM: None,
        }
        allowed = rules.get(layout)
        if allowed is not None and panel_count not in allowed:
            raise SchemaValidationError(
                f"output_layout={layout.value} requires {allowed} panels, got {panel_count}"
            )

    @staticmethod
    def new_sequence_id(prefix: str = "seq") -> str:
        return f"{prefix}_{uuid.uuid4().hex[:12]}"

    @property
    def panel_count(self) -> int:
        return len(self.ordered_panels)

    @property
    def is_multi_panel(self) -> bool:
        return self.panel_count > 1

    def get_character(self, key: str) -> CharacterState | None:
        for k, v in self.character_states:
            if k == key:
                return v
        return None

    def get_prop(self, key: str) -> PropState | None:
        for k, v in self.prop_states:
            if k == key:
                return v
        return None

    def get_panel(self, panel_id: str) -> SinglePanelSpec | None:
        for p in self.ordered_panels:
            if p.panel_id == panel_id:
                return p
        return None

    def with_revision(self, **changes: Any) -> "ComicSequenceSpec":
        return replace(self, revision=self.revision + 1, **changes)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sequence_id": self.sequence_id,
            "global_story": self.global_story,
            "character_states": [
                {"key": k, "state": v.to_dict()} for k, v in self.character_states
            ],
            "prop_states": [
                {"key": k, "state": v.to_dict()} for k, v in self.prop_states
            ],
            "scene_state": self.scene_state.to_dict(),
            "ordered_panels": [p.to_dict() for p in self.ordered_panels],
            "output_layout": self.output_layout.value,
            "max_correction_rounds": self.max_correction_rounds,
            "revision": self.revision,
            "created_at": self.created_at,
            "notes": self.notes,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ComicSequenceSpec":
        chars = tuple(
            (str(item["key"]), CharacterState.from_dict(item["state"]))
            for item in data.get("character_states", ()) or ()
        )
        props = tuple(
            (str(item["key"]), PropState.from_dict(item["state"]))
            for item in data.get("prop_states", ()) or ()
        )
        scene_raw = data.get("scene_state") or {}
        scene = (
            scene_raw
            if isinstance(scene_raw, SceneState)
            else SceneState.from_dict(scene_raw)
        )
        panels = tuple(
            SinglePanelSpec.from_dict(p) for p in data.get("ordered_panels", ()) or ()
        )
        return cls(
            sequence_id=str(data["sequence_id"]),
            global_story=str(data.get("global_story", "")),
            character_states=chars,
            prop_states=props,
            scene_state=scene,
            ordered_panels=panels,
            output_layout=OutputLayout(
                data.get("output_layout", OutputLayout.SINGLE.value)
            ),
            max_correction_rounds=int(data.get("max_correction_rounds", 2)),
            revision=int(data.get("revision", 0)),
            created_at=str(data.get("created_at") or _now_iso()),
            notes=str(data.get("notes", "")),
        )

    def to_jsonable(self) -> dict[str, Any]:
        """Return a fully JSON-serializable dict (alias of ``to_dict``)."""
        return _to_jsonable(self.to_dict())  # type: ignore[return-value]
