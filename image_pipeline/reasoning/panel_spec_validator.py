"""
image_pipeline.reasoning.panel_spec_validator — Semantic validation of draft
``SinglePanelSpec`` / ``ComicSequenceSpec`` instances.

The schemas already enforce **structural** rules (types, ranges, ID format,
duplicate IDs, layout/panel-count compatibility, panel cross-references that
the spec itself controls). This module adds the **semantic** checks the planner
needs:

* unknown character / prop references against an external registry,
* contradictory ``must_keep`` vs ``forbidden_drift`` clauses,
* broken overlay plans (e.g. text-bearing overlay kind with empty text),
* inconsistent ``primary_character_key`` placement,
* prop requirements that contradict the panel's continuity contract.

Returns a :class:`ValidationResult` with errors **and** warnings. Errors mean
"do not execute"; warnings mean "execute but record".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from image_pipeline.reasoning.schemas import (
    ComicSequenceSpec,
    OverlayElement,
    OverlayKind,
    OverlayPlan,
    PropRequirement,
    SchemaValidationError,
    SinglePanelSpec,
)

# ---------------------------------------------------------------------------
# Public types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single semantic finding. ``severity`` ∈ {"error", "warning"}."""

    severity: str
    code: str
    message: str
    path: str = ""

    def __post_init__(self) -> None:
        if self.severity not in ("error", "warning"):
            raise ValueError(
                f"ValidationIssue.severity must be 'error' or 'warning', got {self.severity!r}"
            )

    def to_dict(self) -> dict[str, str]:
        return {
            "severity": self.severity,
            "code": self.code,
            "message": self.message,
            "path": self.path,
        }


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Aggregate validator output."""

    issues: tuple[ValidationIssue, ...] = ()

    @property
    def errors(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "error")

    @property
    def warnings(self) -> tuple[ValidationIssue, ...]:
        return tuple(i for i in self.issues if i.severity == "warning")

    @property
    def ok(self) -> bool:
        return not self.errors

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "issues": [i.to_dict() for i in self.issues],
        }


# Overlay kinds that *must* carry non-empty text when present.
_TEXT_BEARING_OVERLAYS: frozenset[OverlayKind] = frozenset(
    {
        OverlayKind.TITLE_BAR,
        OverlayKind.SPEECH_BUBBLE,
        OverlayKind.THOUGHT_BUBBLE,
        OverlayKind.CAPTION,
        OverlayKind.SFX,
        OverlayKind.PHONE_UI,
        OverlayKind.ID_CARD,
        OverlayKind.PANEL_LABEL,
    }
)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_panel(
    panel: SinglePanelSpec,
    *,
    known_character_keys: Iterable[str] | None = None,
    known_prop_keys: Iterable[str] | None = None,
    path: str = "panel",
) -> ValidationResult:
    """Validate a stand-alone :class:`SinglePanelSpec`."""
    if not isinstance(panel, SinglePanelSpec):
        raise SchemaValidationError(
            f"validate_panel expects SinglePanelSpec, got {type(panel).__name__}"
        )
    issues: list[ValidationIssue] = []
    _validate_panel_into(
        panel,
        known_character_keys=_freeze(known_character_keys),
        known_prop_keys=_freeze(known_prop_keys),
        path=path,
        issues=issues,
    )
    return ValidationResult(issues=tuple(issues))


def validate_sequence(
    sequence: ComicSequenceSpec,
    *,
    known_character_keys: Iterable[str] | None = None,
    known_prop_keys: Iterable[str] | None = None,
) -> ValidationResult:
    """
    Validate a :class:`ComicSequenceSpec`.

    When ``known_character_keys`` / ``known_prop_keys`` are provided, every
    key registered in the sequence must be present in the registry; otherwise
    that registry check is skipped (useful in unit tests / offline planning).
    """
    if not isinstance(sequence, ComicSequenceSpec):
        raise SchemaValidationError(
            f"validate_sequence expects ComicSequenceSpec, got {type(sequence).__name__}"
        )
    issues: list[ValidationIssue] = []
    known_chars = _freeze(known_character_keys)
    known_props = _freeze(known_prop_keys)

    seq_char_keys = {k for k, _ in sequence.character_states}
    seq_prop_keys = {k for k, _ in sequence.prop_states}

    if known_chars is not None:
        for key in seq_char_keys - known_chars:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="unknown_character",
                    message=f"character_key={key!r} is not in the known registry",
                    path=f"sequence.character_states[{key}]",
                )
            )
    if known_props is not None:
        for key in seq_prop_keys - known_props:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="unknown_prop",
                    message=f"prop_key={key!r} is not in the known registry",
                    path=f"sequence.prop_states[{key}]",
                )
            )

    # Layout/panel-count is structurally checked by the schema, but if a caller
    # bypasses the schema (e.g. via a future builder), re-check defensively.
    _check_layout_consistency(sequence, issues)

    # Per-panel checks. Use the sequence's own registries as the universe so
    # cross-references are validated against what the spec actually carries.
    for i, panel in enumerate(sequence.ordered_panels):
        _validate_panel_into(
            panel,
            known_character_keys=seq_char_keys,
            known_prop_keys=seq_prop_keys,
            path=f"sequence.ordered_panels[{i}]({panel.panel_id})",
            issues=issues,
        )

    # Sequence-level continuity contradictions: any token that appears in the
    # global character must_keep but also in a panel forbidden_drift.
    for ck, char_state in sequence.character_states:
        for token in _normalize_tokens(char_state.must_keep):
            for panel in sequence.ordered_panels:
                if token in _normalize_tokens(panel.forbidden_drift):
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="contradicts_character_must_keep",
                            message=(
                                f"panel {panel.panel_id!r} forbids drift on {token!r} "
                                f"that character {ck!r} requires to be kept"
                            ),
                            path=f"sequence.character_states[{ck}]",
                        )
                    )

    return ValidationResult(issues=tuple(issues))


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _validate_panel_into(
    panel: SinglePanelSpec,
    *,
    known_character_keys: frozenset[str] | None,
    known_prop_keys: frozenset[str] | None,
    path: str,
    issues: list[ValidationIssue],
) -> None:
    # Unknown character refs.
    if known_character_keys is not None:
        for ck in panel.character_keys:
            if ck not in known_character_keys:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="unknown_character",
                        message=f"panel references unknown character_key={ck!r}",
                        path=f"{path}.character_keys",
                    )
                )

    # primary_character_key sanity (the schema enforces it must be in
    # character_keys; here we add the registry check + presence reminder).
    if (
        panel.primary_character_key is None
        and panel.character_keys
    ):
        issues.append(
            ValidationIssue(
                severity="warning",
                code="missing_primary_character",
                message="character_keys is non-empty but primary_character_key is None",
                path=f"{path}.primary_character_key",
            )
        )

    # Unknown prop refs.
    if known_prop_keys is not None:
        for req in panel.prop_requirements:
            if req.prop_key not in known_prop_keys:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="unknown_prop",
                        message=f"panel references unknown prop_key={req.prop_key!r}",
                        path=f"{path}.prop_requirements",
                    )
                )

    # Contradiction: must_keep ∩ forbidden_drift on the same panel.
    keep_norm = _normalize_tokens(panel.continuity_must_keep)
    forbid_norm = _normalize_tokens(panel.forbidden_drift)
    for token in keep_norm & forbid_norm:
        issues.append(
            ValidationIssue(
                severity="error",
                code="contradictory_continuity",
                message=(
                    f"{token!r} appears in both continuity_must_keep and forbidden_drift"
                ),
                path=f"{path}.forbidden_drift",
            )
        )

    # Contradiction: prop must_appear=False but referenced in continuity_must_keep.
    for req in panel.prop_requirements:
        if req.must_appear is False:
            for token in keep_norm:
                if req.prop_key in token or token in req.prop_key:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="contradictory_prop_requirement",
                            message=(
                                f"prop {req.prop_key!r} is must_appear=False yet referenced "
                                f"in continuity_must_keep ({token!r})"
                            ),
                            path=f"{path}.prop_requirements[{req.prop_key}]",
                        )
                    )

    # Overlay plan checks.
    _validate_overlay_plan(panel.overlay_plan, path=f"{path}.overlay_plan", issues=issues)


def _validate_overlay_plan(
    plan: OverlayPlan, *, path: str, issues: list[ValidationIssue]
) -> None:
    z_seen: dict[int, str] = {}
    for el in plan.elements:
        # Text-bearing kinds must have non-empty text.
        if el.kind in _TEXT_BEARING_OVERLAYS and not el.text.strip():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="empty_overlay_text",
                    message=(
                        f"overlay element {el.element_id!r} of kind {el.kind.value!r} "
                        f"requires non-empty text"
                    ),
                    path=f"{path}.elements[{el.element_id}]",
                )
            )
        # Z-order collision is allowed but worth flagging.
        if el.z_order in z_seen:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="overlay_z_order_collision",
                    message=(
                        f"elements {z_seen[el.z_order]!r} and {el.element_id!r} share "
                        f"z_order={el.z_order}; render order is undefined"
                    ),
                    path=f"{path}.elements[{el.element_id}]",
                )
            )
        else:
            z_seen[el.z_order] = el.element_id


def _check_layout_consistency(
    sequence: ComicSequenceSpec, issues: list[ValidationIssue]
) -> None:
    """
    Defense in depth: re-check layout vs panel count even though the schema
    already enforces it. Helps if the schema rules are relaxed in the future.
    """
    from image_pipeline.reasoning.schemas import OutputLayout

    rules: dict[OutputLayout, tuple[int, ...] | None] = {
        OutputLayout.SINGLE: (1,),
        OutputLayout.GRID_2X2: (4,),
        OutputLayout.GRID_2X3: (6,),
        OutputLayout.GRID_3X3: (9,),
    }
    expected = rules.get(sequence.output_layout)
    if expected is not None and sequence.panel_count not in expected:
        issues.append(
            ValidationIssue(
                severity="error",
                code="incompatible_layout",
                message=(
                    f"output_layout={sequence.output_layout.value} requires {expected} "
                    f"panels, got {sequence.panel_count}"
                ),
                path="sequence.output_layout",
            )
        )


def _normalize_tokens(values: Iterable[str]) -> set[str]:
    out: set[str] = set()
    for v in values:
        if not isinstance(v, str):
            continue
        token = " ".join(v.lower().split())
        if token:
            out.add(token)
    return out


def _freeze(values: Iterable[str] | None) -> frozenset[str] | None:
    if values is None:
        return None
    return frozenset(values)


__all__ = [
    "ValidationIssue",
    "ValidationResult",
    "validate_panel",
    "validate_sequence",
]
