"""
image_pipeline.reasoning.prompt_parser — Convert a revised prompt into a draft
``SinglePanelSpec`` or ``ComicSequenceSpec``.

This is step 1+2+3+5 of the SKILL.md chain (parse intent → states → panel
specs). It does **not** run ComfyUI, call an LLM, or perform I/O. It produces
a *draft* spec; ``panel_spec_validator`` enforces semantic rules and
``execution_planner`` (later commit) decides which ComfyUI stages run.

Cross-reference safety
----------------------
``ComicSequenceSpec.__post_init__`` already rejects panels that reference
unknown ``character_key``/``prop_key``. To stay green, this parser **registers
a placeholder ``CharacterState``/``PropState`` for every key it emits** so the
spec constructs cleanly. The validator then decides whether those placeholders
are acceptable for the caller's known registry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Mapping

from image_pipeline.reasoning.capability_router import (
    CapabilityDecision,
    CapabilityRequest,
    RequestKind,
    classify,
)
from image_pipeline.reasoning.prompt_revision import RevisedPrompt, revise
from image_pipeline.reasoning.state import StateResolver
from image_pipeline.reasoning.schemas import (
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
)

# ---------------------------------------------------------------------------
# Public type
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ParseResult:
    """Output of :func:`parse`. Exactly one of ``single_panel`` / ``sequence`` is set."""

    decision: CapabilityDecision
    revision: RevisedPrompt
    single_panel: SinglePanelSpec | None = None
    sequence: ComicSequenceSpec | None = None
    required_stages: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "decision": self.decision.to_dict(),
            "revision": self.revision.to_dict(),
            "single_panel": self.single_panel.to_dict() if self.single_panel else None,
            "sequence": self.sequence.to_dict() if self.sequence else None,
            "required_stages": list(self.required_stages),
            "warnings": list(self.warnings),
        }


# ---------------------------------------------------------------------------
# Detection patterns
# ---------------------------------------------------------------------------

_LOCATION_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("bedroom", "bedroom"),
    ("kitchen", "kitchen"),
    ("bathroom", "bathroom"),
    ("living room", "living_room"),
    ("classroom", "classroom"),
    ("school", "school"),
    ("office", "office"),
    ("park", "park"),
    ("forest", "forest"),
    ("beach", "beach"),
    ("street", "street"),
    ("cafe", "cafe"),
    ("coffee shop", "cafe"),
    ("library", "library"),
    ("rooftop", "rooftop"),
    ("subway", "subway"),
    ("train station", "train_station"),
)

_TIME_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("morning", "morning"),
    ("noon", "noon"),
    ("afternoon", "afternoon"),
    ("evening", "evening"),
    ("sunset", "sunset"),
    ("dusk", "dusk"),
    ("night", "night"),
    ("midnight", "midnight"),
    ("dawn", "dawn"),
)

_MOOD_KEYWORDS: tuple[tuple[str, str], ...] = (
    ("cozy", "cozy"),
    ("tense", "tense"),
    ("dramatic", "dramatic"),
    ("playful", "playful"),
    ("romantic", "romantic"),
    ("sad", "sad"),
    ("happy", "happy"),
    ("mysterious", "mysterious"),
    ("creepy", "creepy"),
)

# Color + noun → prop candidate (Midjourney short-prompt style).
_COLOR_WORDS = (
    "red", "blue", "green", "yellow", "orange", "purple", "pink", "white",
    "black", "gray", "grey", "brown", "gold", "silver",
)
_PROP_NOUNS = (
    "phone", "mug", "cup", "book", "pillow", "blanket", "bed", "lamp",
    "laptop", "card", "letter", "knife", "gun", "sword", "guitar",
    "umbrella", "bag", "backpack", "hat", "mask", "ring", "necklace",
    "id", "license", "ticket", "key", "watch", "camera",
)
_PROP_RE = re.compile(
    r"\b(" + "|".join(_COLOR_WORDS) + r")\s+(" + "|".join(_PROP_NOUNS) + r")\b",
    re.IGNORECASE,
)
# Bare prop (no color) — only flagged when explicitly hinted with "the" / "a".
_BARE_PROP_RE = re.compile(
    r"\b(?:the|a|an)\s+(" + "|".join(_PROP_NOUNS) + r")\b",
    re.IGNORECASE,
)

# Shot type cues.
_SHOT_HINTS: tuple[tuple[re.Pattern[str], ShotType], ...] = (
    (re.compile(r"\bextreme\s*close[\s-]*up\b", re.I), ShotType.EXTREME_CLOSE_UP),
    (re.compile(r"\bclose[\s-]*up\b", re.I), ShotType.CLOSE_UP),
    (re.compile(r"\bmedium\s*close[\s-]*up\b", re.I), ShotType.MEDIUM_CLOSE_UP),
    (re.compile(r"\bmedium\s*wide\b", re.I), ShotType.MEDIUM_WIDE),
    (re.compile(r"\bextreme\s*wide\b", re.I), ShotType.EXTREME_WIDE),
    (re.compile(r"\bwide\s*shot\b|\bestablishing\s*shot\b", re.I), ShotType.WIDE),
    (re.compile(r"\bover[\s-]*the[\s-]*shoulder\b|\bots\b", re.I), ShotType.OTS),
    (re.compile(r"\bpov\b|\bpoint[\s-]*of[\s-]*view\b", re.I), ShotType.POV),
    (re.compile(r"\btop[\s-]*down\b|\bbird'?s?[\s-]*eye\b", re.I), ShotType.TOP_DOWN),
    (re.compile(r"\blow[\s-]*angle\b", re.I), ShotType.LOW_ANGLE),
    (re.compile(r"\bdutch\s*angle\b", re.I), ShotType.DUTCH),
    (re.compile(r"\bmedium\s*shot\b", re.I), ShotType.MEDIUM),
)

# Eye-state cues.
_EYE_HINTS: tuple[tuple[re.Pattern[str], EyeState], ...] = (
    (re.compile(r"\beyes?\s+(?:are\s+)?closed\b|\bclosed\s+eyes?\b", re.I), EyeState.CLOSED),
    (re.compile(r"\bwide\s+eyed?\b|\beyes\s+wide\b", re.I), EyeState.WIDE),
    (re.compile(r"\bsquint(?:ing)?\b", re.I), EyeState.SQUINT),
    (re.compile(r"\bwink(?:ing)?\b", re.I), EyeState.WINK_RIGHT),
    (re.compile(r"\bhalf[\s-]*lidded\b|\bhalf\s+closed\b", re.I), EyeState.HALF),
)

# Aspect-ratio hints.
_AR_RE = re.compile(r"\b(\d{1,2})\s*[:x]\s*(\d{1,2})\b")
_AR_KEYWORDS = (
    ("portrait", "3:4"),
    ("landscape", "4:3"),
    ("widescreen", "16:9"),
    ("square", "1:1"),
    ("vertical", "9:16"),
)

_ID_SAFE_RE = re.compile(r"[^A-Za-z0-9_.\-]+")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse(
    text: str,
    *,
    attached_images: int = 0,
    is_followup: bool = False,
    prior_image_ref: str | None = None,
    explicit_kind: RequestKind | None = None,
    character_hint: Mapping[str, str] | None = None,
    sequence_id: str | None = None,
    panel_count_override: int | None = None,
    state_resolver: StateResolver | None = None,
) -> ParseResult:
    """
    Convert ``text`` into a draft :class:`SinglePanelSpec` or
    :class:`ComicSequenceSpec`, plus a :class:`CapabilityDecision` and
    :class:`RevisedPrompt`.

    ``character_hint`` lets the caller pin the resolved character (name + key)
    so the parser can populate panel ``character_keys`` confidently. When
    omitted, no character is referenced from panels.

    ``state_resolver`` (Cycle 2): when provided, character / prop / scene
    extraction is delegated to the resolver's managers. The resolver may
    produce real registry-backed states (e.g. with ``must_keep`` populated
    from the character DB). When ``None``, legacy placeholder behavior is
    preserved unchanged.
    """
    request = CapabilityRequest(
        text=text,
        attached_images=attached_images,
        is_followup=is_followup,
        prior_image_ref=prior_image_ref,
        explicit_kind=explicit_kind,
    )
    decision = classify(request)
    revision = revise(text)

    warnings: list[str] = []
    if state_resolver is not None:
        scene = state_resolver.extract_scene(revision.source_text)
        props = state_resolver.extract_props(revision.source_text)
        character_state = state_resolver.resolve_character(character_hint)
    else:
        scene = _build_scene(revision)
        props = _extract_props(revision, warnings)
        character_state = _build_character_placeholder(character_hint, warnings)

    panel_count = panel_count_override or decision.panel_count_hint or 1
    if panel_count < 1:
        panel_count = 1

    required_stages = list(decision.required_stages)
    if revision.requires_overlay and "overlay" not in required_stages:
        required_stages.append("overlay")
    if revision.requires_regional_patch:
        # face/eyes → face_patch; other regions → prop_patch.
        regions = set(revision.detected_regions)
        if regions & {"face", "eyes", "eye", "iris", "pupil", "mouth", "lips", "nose", "hair"}:
            if "face_patch" not in required_stages:
                required_stages.append("face_patch")
        if regions - {"face", "eyes", "eye", "iris", "pupil", "mouth", "lips", "nose", "hair"}:
            if "prop_patch" not in required_stages:
                required_stages.append("prop_patch")

    if decision.kind is RequestKind.COMIC_SEQUENCE or panel_count > 1:
        seq = _build_sequence(
            revision=revision,
            scene=scene,
            props=props,
            character_state=character_state,
            panel_count=panel_count,
            sequence_id=sequence_id,
            warnings=warnings,
        )
        return ParseResult(
            decision=decision,
            revision=revision,
            sequence=seq,
            required_stages=tuple(required_stages),
            warnings=tuple(warnings),
        )

    panel = _build_panel(
        revision=revision,
        scene=scene,
        props=props,
        character_state=character_state,
        panel_index=0,
        panel_count=1,
        warnings=warnings,
    )
    return ParseResult(
        decision=decision,
        revision=revision,
        single_panel=panel,
        required_stages=tuple(required_stages),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Internals — extraction
# ---------------------------------------------------------------------------


def _build_scene(rev: RevisedPrompt) -> SceneState:
    text = rev.source_text.lower()
    location = ""
    sub_location = ""
    for kw, canon in _LOCATION_KEYWORDS:
        if kw in text:
            location = canon
            break
    time_of_day = ""
    for kw, canon in _TIME_KEYWORDS:
        if kw in text:
            time_of_day = canon
            break
    mood = ""
    for kw, canon in _MOOD_KEYWORDS:
        if kw in text:
            mood = canon
            break
    return SceneState(
        location=location,
        sub_location=sub_location,
        time_of_day=time_of_day,
        mood=mood,
        lock_scene=True,
    )


def _extract_props(rev: RevisedPrompt, warnings: list[str]) -> tuple[tuple[str, PropState], ...]:
    """Return ``((prop_key, PropState), ...)`` extracted from the revised text."""
    seen: dict[str, PropState] = {}
    for m in _PROP_RE.finditer(rev.source_text):
        color = m.group(1).lower()
        noun = m.group(2).lower()
        key = _safe_id(f"{color}_{noun}")
        label = f"{color} {noun}"
        if key in seen:
            continue
        seen[key] = PropState(
            prop_key=key,
            label=label,
            canonical_tags=(color, noun),
            color=color,
            is_recurring=True,
            notes="parser placeholder",
        )
    # Bare props (no color) — only when nothing else matched the noun.
    matched_nouns = {p.canonical_tags[1] for p in seen.values() if len(p.canonical_tags) >= 2}
    for m in _BARE_PROP_RE.finditer(rev.source_text):
        noun = m.group(1).lower()
        if noun in matched_nouns:
            continue
        key = _safe_id(noun)
        if key in seen:
            continue
        seen[key] = PropState(
            prop_key=key,
            label=noun,
            canonical_tags=(noun,),
            is_recurring=True,
            notes="parser placeholder (uncolored)",
        )
        matched_nouns.add(noun)
    if not seen:
        return ()
    return tuple(seen.items())


def _build_character_placeholder(
    hint: Mapping[str, str] | None,
    warnings: list[str],
) -> tuple[str, CharacterState] | None:
    if not hint:
        return None
    key_raw = hint.get("character_key") or hint.get("key") or ""
    name_raw = hint.get("character_name") or hint.get("name") or ""
    if not key_raw or not name_raw:
        warnings.append("character_hint missing character_key or character_name; ignored")
        return None
    key = _safe_id(key_raw)
    state = CharacterState(
        character_key=key,
        character_name=name_raw,
        appearance=CharacterAppearance(),
        notes="parser placeholder",
    )
    return (key, state)


# ---------------------------------------------------------------------------
# Internals — spec assembly
# ---------------------------------------------------------------------------


def _build_panel(
    *,
    revision: RevisedPrompt,
    scene: SceneState,
    props: tuple[tuple[str, PropState], ...],
    character_state: tuple[str, CharacterState] | None,
    panel_index: int,
    panel_count: int,
    warnings: list[str],
) -> SinglePanelSpec:
    panel_id = SinglePanelSpec.new_panel_id(prefix=f"p{panel_index + 1}")
    shot_type = _detect_shot_type(revision.source_text)
    eye_state = _detect_eye_state(revision.source_text)
    role = _panel_role(panel_index, panel_count)
    aspect = _detect_aspect(revision.source_text)

    char_keys: tuple[str, ...] = ()
    primary_key: str | None = None
    if character_state is not None:
        char_keys = (character_state[0],)
        primary_key = character_state[0]

    prop_reqs = tuple(
        PropRequirement(prop_key=key, must_appear=True, notes="parser placeholder")
        for key, _ in props
    )

    overlay_plan = _build_overlay_plan(revision, panel_index, warnings)

    must_keep = revision.must_keep
    forbidden = revision.forbidden_drift

    extra_pos: tuple[str, ...] = ()
    if revision.normalized_prompt:
        extra_pos = tuple(t for t in (s.strip() for s in revision.normalized_prompt.split(",")) if t)

    return SinglePanelSpec(
        panel_id=panel_id,
        shot_type=shot_type,
        scene_description=_summarize_scene(scene),
        action_description=revision.normalized_prompt,
        eye_state=eye_state,
        panel_role=role,
        character_keys=char_keys,
        primary_character_key=primary_key,
        prop_requirements=prop_reqs,
        continuity_must_keep=must_keep,
        forbidden_drift=forbidden,
        overlay_plan=overlay_plan,
        aspect_ratio=aspect,
        extra_positive_tags=extra_pos,
    )


def _build_sequence(
    *,
    revision: RevisedPrompt,
    scene: SceneState,
    props: tuple[tuple[str, PropState], ...],
    character_state: tuple[str, CharacterState] | None,
    panel_count: int,
    sequence_id: str | None,
    warnings: list[str],
) -> ComicSequenceSpec:
    panels = tuple(
        _build_panel(
            revision=revision,
            scene=scene,
            props=props,
            character_state=character_state,
            panel_index=i,
            panel_count=panel_count,
            warnings=warnings,
        )
        for i in range(panel_count)
    )
    layout = _layout_for(panel_count)
    char_states = (character_state,) if character_state is not None else ()
    seq_id = sequence_id or ComicSequenceSpec.new_sequence_id()

    try:
        return ComicSequenceSpec(
            sequence_id=seq_id,
            global_story=revision.normalized_prompt or revision.source_text[:200],
            character_states=char_states,
            prop_states=props,
            scene_state=scene,
            ordered_panels=panels,
            output_layout=layout,
        )
    except SchemaValidationError as exc:
        # Should not happen because we always register placeholders, but if it
        # does, surface the failure as a warning and fall back to a minimal
        # SINGLE-layout sequence with the first panel.
        warnings.append(f"sequence build fallback: {exc}")
        return ComicSequenceSpec(
            sequence_id=seq_id,
            global_story=revision.source_text[:200],
            character_states=char_states,
            prop_states=props,
            scene_state=scene,
            ordered_panels=(panels[0],),
            output_layout=OutputLayout.SINGLE,
        )


def _build_overlay_plan(
    revision: RevisedPrompt, panel_index: int, warnings: list[str]
) -> OverlayPlan:
    if not revision.requires_overlay:
        return OverlayPlan()
    elements: list[OverlayElement] = []
    quoted = list(revision.extracted_quoted_text)
    kinds = list(revision.detected_overlay_kinds) or [OverlayKind.CAPTION]
    for i, kind in enumerate(kinds):
        text = quoted[i] if i < len(quoted) else ""
        if not text and quoted:
            text = quoted[0]
        element_id = _safe_id(f"p{panel_index + 1}_{kind.value}_{i + 1}")
        try:
            elements.append(
                OverlayElement(
                    element_id=element_id,
                    kind=kind,
                    text=text,
                    z_order=i,
                )
            )
        except SchemaValidationError as exc:
            warnings.append(f"overlay element rejected: {exc}")
    return OverlayPlan(elements=tuple(elements))


# ---------------------------------------------------------------------------
# Internals — small helpers
# ---------------------------------------------------------------------------


def _detect_shot_type(text: str) -> ShotType:
    for pat, kind in _SHOT_HINTS:
        if pat.search(text):
            return kind
    return ShotType.MEDIUM


def _detect_eye_state(text: str) -> EyeState:
    for pat, kind in _EYE_HINTS:
        if pat.search(text):
            return kind
    return EyeState.UNSPECIFIED


def _detect_aspect(text: str) -> str:
    m = _AR_RE.search(text)
    if m:
        w, h = int(m.group(1)), int(m.group(2))
        if 1 <= w <= 32 and 1 <= h <= 32:
            return f"{w}:{h}"
    lower = text.lower()
    for kw, ar in _AR_KEYWORDS:
        if kw in lower:
            return ar
    return "1:1"


def _panel_role(index: int, total: int) -> PanelRole:
    if total <= 1:
        return PanelRole.BEAT
    if index == 0:
        return PanelRole.ESTABLISHING
    if index == total - 1:
        return PanelRole.PUNCHLINE
    if index == total - 2:
        return PanelRole.REACTION
    if index == 1:
        return PanelRole.SETUP
    return PanelRole.BEAT


def _layout_for(panel_count: int) -> OutputLayout:
    if panel_count == 1:
        return OutputLayout.SINGLE
    if panel_count == 4:
        return OutputLayout.GRID_2X2
    if panel_count == 6:
        return OutputLayout.GRID_2X3
    if panel_count == 9:
        return OutputLayout.GRID_3X3
    return OutputLayout.HORIZONTAL_STRIP


def _summarize_scene(scene: SceneState) -> str:
    parts = [p for p in (scene.location, scene.time_of_day, scene.mood) if p]
    return ", ".join(parts)


def _safe_id(raw: str) -> str:
    cleaned = _ID_SAFE_RE.sub("_", raw.strip()).strip("_")
    if not cleaned:
        cleaned = "x"
    return cleaned[:128]


__all__ = ["ParseResult", "parse"]
