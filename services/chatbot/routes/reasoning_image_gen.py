"""
Reasoning Image Generation API — Flask Blueprint (Cycle 6).

This is the FIRST cycle that wires the ``image_pipeline.reasoning`` library
(Cycles 1-5) into the live chatbot. The route is registered ONLY when
``REASONING_PIPELINE=true`` (see :mod:`core.config`); when disabled the
import is never executed and the URL map is byte-identical to today.

Endpoints (URL prefix ``/api/reasoning-image-gen``):

* ``GET  /status``    → flag + dependency snapshot
* ``POST /generate``  → run the full pipeline:
        parse → (per panel) plan_panel → run_panel → maybe_correct
        → assemble_comic → return descriptor + base64 image

Module-level injectables (overridable in tests via monkeypatch):

* :func:`_default_route_fn`         — stage → (model, provider, location, cost)
* :func:`_default_comfy_client`     — ComfyClientLike adapter around
                                       :class:`ComfyUIClient`
* :func:`_default_scorer_fn`        — no-op scorer (passes everything)
* :func:`_default_inpaint_runner`   — pass-through inpaint (returns input bytes)

This file does NOT call ``load_dotenv``; environment is loaded once via
``services.shared_env`` through :mod:`core.config`.
"""

from __future__ import annotations

import base64
import logging
import time
import uuid
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from flask import Blueprint, jsonify, request

from core.config import (
    REASONING_PIPELINE_COMFY_URL,
    REASONING_PIPELINE_MAX_CORRECTION_PASSES,
    REASONING_PIPELINE_MAX_PANELS,
)

from image_pipeline.reasoning import (
    ComicSequenceSpec,
    OutputLayout,
    SchemaValidationError,
    SinglePanelSpec,
    parse,
)
from image_pipeline.reasoning.execution import (
    assemble_comic,
    maybe_correct,
    run_panel,
)
from image_pipeline.reasoning.state import default_resolver

logger = logging.getLogger(__name__)

reasoning_image_gen_bp = Blueprint(
    "reasoning_image_gen", __name__, url_prefix="/api/reasoning-image-gen"
)


# ---------------------------------------------------------------------------
# Default injected dependencies (test-overridable)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _RouteDecision:
    """Concrete RouteDecisionLike used by the local pipeline."""

    model: str
    provider: str
    location: str
    cost_usd: float


def _default_route_fn(task_type: str) -> _RouteDecision:
    """Stage → route decision. All stages run on local ComfyUI."""
    return _RouteDecision(
        model="local-comfyui",
        provider="comfyui",
        location="local",
        cost_usd=0.0,
    )


@dataclass(frozen=True)
class _ComfyJobResult:
    """ComfyClientLike.submit_workflow return shape."""

    success: bool
    images_b64: tuple[str, ...]
    duration_ms: float
    error: str = ""
    cancelled: bool = False


class _ComfyClientAdapter:
    """Adapter over :class:`ComfyUIClient` matching ``ComfyClientLike``.

    The reasoning runner expects ``submit_workflow(workflow, job_id, pass_name)``
    returning an object with ``success / images_b64 / duration_ms / error /
    cancelled``. The chatbot's ``ComfyUIClient`` exposes lower-level
    ``_queue_prompt`` + ``_wait_for_prompt`` + ``_get_image``.
    """

    def __init__(self, api_url: str | None = None) -> None:
        # Lazy import — keeps the module import cheap when the flag is off
        # AND avoids hard-binding tests to the real client.
        from src.utils.comfyui_client import ComfyUIClient  # type: ignore

        self._client = ComfyUIClient(api_url or REASONING_PIPELINE_COMFY_URL)

    def submit_workflow(
        self, workflow: dict, job_id: str = "", pass_name: str = ""
    ) -> _ComfyJobResult:
        started = time.monotonic()
        try:
            prompt_id = self._client._queue_prompt(workflow)  # noqa: SLF001
        except Exception as exc:  # pragma: no cover — defensive
            return _ComfyJobResult(
                success=False,
                images_b64=(),
                duration_ms=(time.monotonic() - started) * 1000.0,
                error=f"queue_prompt raised: {exc}",
            )
        if not prompt_id:
            return _ComfyJobResult(
                success=False,
                images_b64=(),
                duration_ms=(time.monotonic() - started) * 1000.0,
                error="ComfyUI did not return a prompt_id",
            )
        outputs = self._client._wait_for_prompt(prompt_id, timeout=300)  # noqa: SLF001
        duration_ms = (time.monotonic() - started) * 1000.0
        if not outputs:
            return _ComfyJobResult(
                success=False, images_b64=(), duration_ms=duration_ms,
                error=f"timeout waiting for prompt {prompt_id}",
            )
        if isinstance(outputs, dict) and outputs.get("error"):
            return _ComfyJobResult(
                success=False, images_b64=(), duration_ms=duration_ms,
                error=str(outputs["error"]),
            )
        img_bytes = self._client._get_image(outputs)  # noqa: SLF001
        if not img_bytes:
            return _ComfyJobResult(
                success=False, images_b64=(), duration_ms=duration_ms,
                error=f"no image in outputs for prompt {prompt_id}",
            )
        return _ComfyJobResult(
            success=True,
            images_b64=(base64.b64encode(img_bytes).decode("ascii"),),
            duration_ms=duration_ms,
        )


def _default_comfy_client() -> Any:
    """Return a fresh ComfyClientLike. Override in tests via monkeypatch."""
    return _ComfyClientAdapter()


@dataclass(frozen=True)
class _NoopScore:
    score: float = 1.0
    targets: tuple = ()


def _default_scorer_fn(panel: SinglePanelSpec, image_bytes: bytes) -> _NoopScore:
    """No-op scorer. Always 1.0 / empty targets — correction loop short-circuits."""
    return _NoopScore()


def _default_inpaint_runner(
    panel: SinglePanelSpec, image_bytes: bytes, targets: Iterable[Any]
) -> bytes:
    """No-op inpaint runner — returns input unchanged."""
    return image_bytes


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _coerce_layout(value: Any, default: OutputLayout) -> OutputLayout:
    if value is None:
        return default
    if isinstance(value, OutputLayout):
        return value
    try:
        return OutputLayout(str(value).lower())
    except ValueError:
        return default


def _panels_from_parse(result: Any) -> tuple[tuple[SinglePanelSpec, ...], OutputLayout]:
    if result.sequence is not None:
        seq: ComicSequenceSpec = result.sequence
        return seq.ordered_panels, seq.output_layout
    if result.single_panel is not None:
        return (result.single_panel,), OutputLayout.SINGLE
    return (), OutputLayout.SINGLE


def _decode_image_b64(data_b64: str) -> bytes:
    return base64.b64decode(data_b64.encode("ascii"))


# ---------------------------------------------------------------------------
# Preflight risk assessment (cheap, no GPU, no ComfyUI)
# ---------------------------------------------------------------------------


_PREFLIGHT_NEXT_ACTION = {
    "ambiguous": "confirm which candidate",
    "unresolved_unknown_no_traits": "choose character from SAA picker",
    "collision_no_series": "add series hint",
    "multiple_characters": "split into separate prompts (one character each)",
    "style_misparsed_as_character": "rephrase as style-only or pick a character",
    "asks_for_known_identity_unsafe": "add character_overrides.json profile",
    "low_data_no_reference": "provide reference image",
    "unknown_with_series_and_traits": "add character_overrides.json profile",
    "known_no_lora": "provide reference image",
    "ok": "",
}


def _assess_preflight(
    prompt_text: str,
    understanding,  # CharacterUnderstandingResult | None
    character_hint,  # mapping | None
) -> dict:
    """Classify a prompt's character-identity risk before generation.

    Returns a dict matching the public preflight contract:
    ``would_generate``, ``character_mode``, ``canonical_id``,
    ``safe_to_attach_lora``, ``needs_review``, ``risk_level``,
    ``blocking_reason``, ``suggested_next_action``.
    """
    # Defaults — generic prompt with no named character is low-risk.
    out: dict[str, Any] = {
        "would_generate": True,
        "character_mode": "",
        "canonical_id": None,
        "safe_to_attach_lora": False,
        "needs_review": False,
        "risk_level": "low",
        "blocking_reason": "",
        "suggested_next_action": "",
        "signals": {},
    }

    # Cheap entity extraction — independent of registry.
    try:
        from core.character_understanding import (  # noqa: PLC0415
            extract_prompt_entities,
        )
        entities = extract_prompt_entities(prompt_text or "")
    except Exception:  # noqa: BLE001
        entities = {
            "candidate_name_slug": "",
            "series_hint": "",
            "style_hint": "",
            "multiple_characters": False,
            "extraction_confidence": 0.0,
        }

    out["signals"] = {
        "candidate_name_slug": entities.get("candidate_name_slug", ""),
        "series_hint": entities.get("series_hint", ""),
        "style_hint": entities.get("style_hint", ""),
        "multiple_characters": bool(entities.get("multiple_characters")),
        "extraction_confidence": float(entities.get("extraction_confidence", 0.0)),
    }

    has_character_hint = bool(character_hint)

    # If a character_hint is explicitly pinned (SAA / manual / registry
    # match), the user has accepted responsibility — risk is low and we
    # echo the canonical identity.
    if has_character_hint:
        out["character_mode"] = "manual_pin"
        out["canonical_id"] = (
            (character_hint or {}).get("key")
            or (character_hint or {}).get("canonical_id")
        )
        out["safe_to_attach_lora"] = True
        out["needs_review"] = False
        out["risk_level"] = "low"
        out["suggested_next_action"] = ""
        return out

    # Multi-character — the reasoning route does not pin per-panel
    # character identity, so any 2+ named character prompt is high-risk
    # for cross-talk / wrong identity.
    if out["signals"]["multiple_characters"]:
        out["risk_level"] = "high"
        out["blocking_reason"] = "multiple_characters"
        out["suggested_next_action"] = _PREFLIGHT_NEXT_ACTION["multiple_characters"]
        out["needs_review"] = True
        out["character_mode"] = "multi_character"
        return out

    # Style-only prompt that ALSO carries a candidate name — risky parse:
    # we'd render a character based on a style cue. Block as high.
    if out["signals"]["style_hint"] and out["signals"]["candidate_name_slug"]:
        out["risk_level"] = "high"
        out["blocking_reason"] = "style_misparsed_as_character"
        out["suggested_next_action"] = (
            _PREFLIGHT_NEXT_ACTION["style_misparsed_as_character"]
        )
        out["needs_review"] = True
        out["character_mode"] = "style_collision"
        return out

    if understanding is None:
        # No resolver result — treat as generic prompt.
        return out

    out["character_mode"] = understanding.mode or ""
    best = understanding.best
    out["canonical_id"] = best.canonical_id if best is not None else None
    out["safe_to_attach_lora"] = bool(understanding.safe_to_attach_lora)

    if understanding.unknown_profile is not None:
        out["needs_review"] = bool(understanding.unknown_profile.needs_review)
    else:
        out["needs_review"] = bool(understanding.ambiguous)

    # Ambiguous → high.
    if understanding.ambiguous:
        out["risk_level"] = "high"
        out["blocking_reason"] = "ambiguous"
        out["suggested_next_action"] = _PREFLIGHT_NEXT_ACTION["ambiguous"]
        return out

    mode = understanding.mode or ""

    # Empty resolver mode = no real attempt (generic prompt with no
    # character signal). Keep low-risk default.
    if not mode:
        return out

    # Unresolved unknown.
    if mode == "unresolved_unknown":
        traits_count = 0
        if understanding.unknown_profile is not None:
            traits_count = (
                len(understanding.unknown_profile.visual_traits)
                + len(understanding.unknown_profile.outfit_traits)
            )
        if traits_count == 0:
            out["risk_level"] = "high"
            # collision_no_series is more specific when a name was
            # extracted but no series was mentioned.
            if (
                out["signals"]["candidate_name_slug"]
                and not out["signals"]["series_hint"]
            ):
                out["blocking_reason"] = "collision_no_series"
                out["suggested_next_action"] = (
                    _PREFLIGHT_NEXT_ACTION["collision_no_series"]
                )
            else:
                out["blocking_reason"] = "unresolved_unknown_no_traits"
                out["suggested_next_action"] = (
                    _PREFLIGHT_NEXT_ACTION["unresolved_unknown_no_traits"]
                )
            return out
        # Unknown with series_hint AND traits → medium.
        if out["signals"]["series_hint"]:
            out["risk_level"] = "medium"
            out["blocking_reason"] = "unknown_with_series_and_traits"
            out["suggested_next_action"] = (
                _PREFLIGHT_NEXT_ACTION["unknown_with_series_and_traits"]
            )
            return out
        # Otherwise unknown but with traits — still medium, ask for ref.
        out["risk_level"] = "medium"
        out["blocking_reason"] = "unknown_with_traits_only"
        out["suggested_next_action"] = _PREFLIGHT_NEXT_ACTION["low_data_no_reference"]
        return out

    # Resolved-known with safe LoRA + lora_hint → low.
    if mode == "resolved_known" and out["safe_to_attach_lora"]:
        if best is not None and best.lora_hint:
            out["risk_level"] = "low"
            return out
        # Known character but no LoRA hint → medium (prompt-only render).
        out["risk_level"] = "medium"
        out["blocking_reason"] = "known_no_lora"
        out["suggested_next_action"] = _PREFLIGHT_NEXT_ACTION["known_no_lora"]
        return out

    # Resolved-known but UNSAFE — caller asked for an exact identity we
    # cannot deliver reliably. High.
    if mode == "resolved_known" and not out["safe_to_attach_lora"]:
        out["risk_level"] = "high"
        out["blocking_reason"] = "asks_for_known_identity_unsafe"
        out["suggested_next_action"] = (
            _PREFLIGHT_NEXT_ACTION["asks_for_known_identity_unsafe"]
        )
        return out

    # Low-data profile.
    if mode == "low_data_profile":
        if best is not None and best.lora_hint and out["safe_to_attach_lora"]:
            out["risk_level"] = "low"
            return out
        out["risk_level"] = "medium"
        out["blocking_reason"] = "low_data_no_reference"
        out["suggested_next_action"] = (
            _PREFLIGHT_NEXT_ACTION["low_data_no_reference"]
        )
        return out

    return out


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@reasoning_image_gen_bp.get("/status")
def status() -> Any:
    """Lightweight introspection — confirms flag is on and dependencies load."""
    return jsonify({
        "enabled": True,
        "comfy_url": REASONING_PIPELINE_COMFY_URL,
        "max_panels": REASONING_PIPELINE_MAX_PANELS,
        "max_correction_passes": REASONING_PIPELINE_MAX_CORRECTION_PASSES,
    })


def run_pipeline_for_prompt(
    prompt_text: str,
    *,
    layout: Any = None,
    attached_images: int = 0,
    character_hint: Mapping[str, Any] | None = None,
) -> dict:
    """Run the full reasoning pipeline as a plain Python call (no Flask).

    Returns a dict with the same keys as the ``/generate`` HTTP endpoint plus
    a ``status_code`` field (so callers like :mod:`routes.image_gen` can map
    the result back to HTTP). The ``status_code`` mirrors what the route
    handler would return; callers may ignore it.

    This is the integration boundary used by Cycle 7 to plug the reasoning
    pipeline into the existing LOCAL image-gen flow without spinning a second
    HTTP hop.
    """
    prompt_text = (prompt_text or "").strip()
    if not prompt_text:
        return {"success": False, "error": "prompt is required", "status_code": 400}

    job_id = f"reason-{uuid.uuid4().hex[:12]}"
    logger.info("[%s] reasoning pipeline start: %r", job_id, prompt_text[:160])

    # 1. Parse — wire the chatbot's CharacterRegistry via Cycle 2 resolver.
    try:
        parse_result = parse(
            prompt_text,
            attached_images=int(attached_images or 0),
            character_hint=character_hint,
            state_resolver=default_resolver(),
        )
    except SchemaValidationError as exc:
        return {"success": False, "error": f"parse failed: {exc}", "status_code": 400}
    except Exception as exc:
        logger.exception("[%s] parse raised", job_id)
        return {"success": False, "error": f"parse raised: {exc}", "status_code": 500}

    panels, parsed_layout = _panels_from_parse(parse_result)
    if not panels:
        return {
            "success": False,
            "error": "parser produced no panels",
            "parse": parse_result.to_dict(),
            "status_code": 422,
        }
    if len(panels) > REASONING_PIPELINE_MAX_PANELS:
        return {
            "success": False,
            "error": (
                f"panel count {len(panels)} exceeds max "
                f"{REASONING_PIPELINE_MAX_PANELS}"
            ),
            "status_code": 422,
        }

    chosen_layout = _coerce_layout(layout, parsed_layout)
    required_stages = tuple(parse_result.required_stages or ())

    # 2. Per-panel: plan + run + correct.
    comfy_client = _default_comfy_client()
    panel_reports: list[dict] = []
    panel_bytes: list[bytes] = []
    any_failure = False

    for panel in panels:
        panel_result = run_panel(
            panel,
            comfy_client=comfy_client,
            route_fn=_default_route_fn,
            required_stages=required_stages,
            job_id=job_id,
        )
        report: dict = {
            "panel_id": panel.panel_id,
            "success": panel_result.success,
            "duration_ms": panel_result.duration_ms,
            "error": panel_result.error,
            "cancelled": panel_result.cancelled,
        }
        if not panel_result.success or not panel_result.images_b64:
            report["correction"] = None
            panel_reports.append(report)
            any_failure = True
            continue

        raw_bytes = _decode_image_b64(panel_result.images_b64[0])
        if REASONING_PIPELINE_MAX_CORRECTION_PASSES > 0:
            correction = maybe_correct(
                panel,
                raw_bytes,
                scorer_fn=_default_scorer_fn,
                inpaint_runner_fn=_default_inpaint_runner,
                required_stages=required_stages,
                max_passes=REASONING_PIPELINE_MAX_CORRECTION_PASSES,
            )
            report["correction"] = correction.to_dict()
            panel_bytes.append(correction.image_bytes)
        else:
            report["correction"] = {"skipped": True}
            panel_bytes.append(raw_bytes)
        panel_reports.append(report)

    # 3. Assemble — bail if any panel produced no bytes.
    if any_failure or not panel_bytes:
        return {
            "success": False,
            "job_id": job_id,
            "parse": parse_result.to_dict(),
            "panels": panel_reports,
            "error": "one or more panels failed to render",
            "status_code": 200,
        }

    try:
        # SINGLE layout supports exactly 1 panel; downgrade if mismatch.
        if chosen_layout is OutputLayout.SINGLE and len(panel_bytes) != 1:
            chosen_layout = OutputLayout.HORIZONTAL_STRIP
        comic = assemble_comic(chosen_layout, panel_bytes)
    except ValueError as exc:
        return {
            "success": False,
            "job_id": job_id,
            "parse": parse_result.to_dict(),
            "panels": panel_reports,
            "error": f"assemble_comic: {exc}",
            "status_code": 200,
        }

    return {
        "success": True,
        "job_id": job_id,
        "parse": parse_result.to_dict(),
        "panels": panel_reports,
        "comic": comic.to_dict(),
        "image_b64": base64.b64encode(comic.image_bytes).decode("ascii"),
        "status_code": 200,
    }


@reasoning_image_gen_bp.post("/generate")
def generate() -> Any:
    """HTTP wrapper around :func:`run_pipeline_for_prompt`.

    Request JSON
    ------------
    ``prompt`` (str, required) — natural-language request.
    ``layout`` (str, optional) — override OutputLayout (e.g. ``"grid_2x2"``).
    ``attached_images`` (int, optional) — count of attachments, forwarded to parser.
    ``character_hint`` (mapping, optional) — pin character resolution.

    Response JSON
    -------------
    ``job_id``, ``parse``, ``panels`` (per-panel diagnostic dicts),
    ``comic`` (descriptor from :meth:`AssembledComic.to_dict`),
    ``image_b64`` (final assembled comic, base64 PNG).
    """
    payload = request.get_json(silent=True) or {}

    prompt_text = payload.get("prompt") or ""

    # ── Character understanding (Phase 2 wiring — log + hint only) ───
    # Lightweight, fail-safe call into core.character_understanding. Never
    # overrides an explicit character_hint / character_key; only fills the
    # hint when the resolver is confident AND not ambiguous. Result is
    # always echoed back in the response under ``understanding`` for
    # debugging and frontend transparency.
    understanding_payload: dict | None = None
    try:
        from core.character_understanding import resolve_character_intent  # noqa: PLC0415

        understanding = resolve_character_intent(
            prompt_text,
            selected_character=payload.get("selected_character"),
        )
        understanding_payload = {
            "resolved": understanding.resolved,
            "ambiguous": understanding.ambiguous,
            "mode": understanding.mode,
            "safe_to_attach_lora": understanding.safe_to_attach_lora,
            "reason": understanding.reason,
            # Phase 4 debug metadata — stable, small, frontend-safe.
            "character_mode": understanding.mode,
            "canonical_id": (
                understanding.best.canonical_id if understanding.best else None
            ),
            "provisional_id": (
                understanding.unknown_profile.provisional_id
                if understanding.unknown_profile else None
            ),
            "data_status": (
                understanding.unknown_profile.data_status
                if understanding.unknown_profile
                else ("known" if understanding.resolved and not understanding.ambiguous
                      else ("ambiguous" if understanding.ambiguous else "unresolved"))
            ),
            "needs_review": (
                understanding.unknown_profile.needs_review
                if understanding.unknown_profile
                else (understanding.ambiguous or not understanding.resolved)
            ),
            "candidates": [
                {
                    "canonical_id": c.canonical_id,
                    "display_name": c.display_name,
                    "series_name": c.series_name,
                    "source": c.source,
                    "confidence": round(c.confidence, 3),
                }
                for c in understanding.candidates
            ],
            "unknown_profile": (
                understanding.unknown_profile.to_dict()
                if understanding.unknown_profile is not None else None
            ),
            "character_identity_block": understanding.character_identity_block,
        }
        if understanding.ambiguous:
            logger.info(
                "[reasoning_image_gen] character ambiguous (%d candidates) — no auto-attach: %s",
                len(understanding.candidates),
                [c.canonical_id for c in understanding.candidates],
            )
        elif understanding.best is not None:
            logger.info(
                "[reasoning_image_gen] character resolved → %s (source=%s, conf=%.2f)",
                understanding.best.canonical_id,
                understanding.best.source,
                understanding.best.confidence,
            )
    except Exception as _ue:  # noqa: BLE001 — fail-safe; never break gen
        logger.warning("[reasoning_image_gen] character_understanding failed: %s", _ue)
        understanding = None

    # ── Preflight risk assessment ───────────────────────────────────
    # Computed BEFORE auto-fill so a same-prompt heuristic auto-attach
    # cannot mask multi-character / unsafe-identity risks. Uses ONLY the
    # caller-supplied character_hint (explicit pin = trusted).
    explicit_hint = payload.get("character_hint")
    preflight = _assess_preflight(prompt_text, understanding, explicit_hint)
    preflight_only = bool(payload.get("preflight_only"))
    require_preflight_pass = bool(payload.get("require_preflight_pass"))

    if preflight_only:
        body: dict = {"preflight": True, **preflight}
        if understanding_payload is not None:
            body["understanding"] = understanding_payload
        # Cost estimate is cheap and useful in preflight mode.
        from core.image_gen.cost_estimator import (  # noqa: PLC0415
            estimate_image_request_cost,
        )
        body["cost"] = estimate_image_request_cost(payload, preflight)
        return jsonify(body), 200

    if require_preflight_pass and preflight["risk_level"] == "high":
        body = {
            "success": False,
            "preflight": True,
            "preflight_blocked": True,
            **preflight,
        }
        if understanding_payload is not None:
            body["understanding"] = understanding_payload
        return jsonify(body), 200

    # ── Cost estimation / budget gate ───────────────────────────────
    # Cheap heuristic — never invokes the pipeline. When the caller
    # supplies ``max_cost_level`` and the estimate exceeds it, we return
    # early with ``needs_confirmation`` so the user can opt-in. Old
    # payloads (no budget fields) keep current behavior; the metadata is
    # still attached for observability when generation runs.
    from core.image_gen.cost_estimator import estimate_image_request_cost  # noqa: PLC0415
    cost = estimate_image_request_cost(payload, preflight)
    if cost["should_require_confirmation"]:
        body = {
            "success": False,
            "needs_confirmation": True,
            "preflight": True,
            "cost": cost,
            **preflight,
        }
        if understanding_payload is not None:
            body["understanding"] = understanding_payload
        return jsonify(body), 200

    # ── SAA character pin ────────────────────────────────────────────
    # Accept either an explicit ``character_hint`` mapping (legacy) or a
    # picker-style ``character_key`` (preferred). When ``character_key`` is
    # supplied we resolve it via the local registry → SAA WAI fallback and
    # build a ``character_hint`` that the parser can consume directly.
    character_hint = explicit_hint
    char_key = (payload.get("character_key") or "").strip()
    if not character_hint and char_key:
        try:
            from core.character_registry import get_registry as _get_reg
            rec = _get_reg().get(char_key)
            if rec is not None:
                character_hint = {
                    "key": rec.key,
                    "display_name": rec.display_name,
                    "series": rec.series,
                    "series_key": rec.series_key,
                    "character_tag": rec.character_tag,
                }
            else:
                from image_pipeline.anime_pipeline.saa_character_db import lookup_character as _saa_lookup
                hit = _saa_lookup(char_key)
                if hit is not None:
                    character_hint = {
                        "key": char_key,
                        "display_name": hit.display_name,
                        "series": hit.series_hint or "",
                        "character_tag": hit.tag,
                        "source": "saa",
                    }
        except Exception as _ce:  # pragma: no cover
            logger.warning("[reasoning_image_gen] character resolve failed: %s", _ce)

    # If still no hint, fall back to the understanding result — but ONLY
    # when it is confident and unambiguous. Ambiguous resolutions must
    # never auto-attach (per character-picker integration rules).
    lora_blocked_reason: str | None = None
    if not character_hint and understanding is not None:
        try:
            from core.character_understanding import (  # noqa: PLC0415
                can_attach_character_lora,
            )
            safe, reason = can_attach_character_lora(understanding)
        except Exception:  # noqa: BLE001
            safe, reason = False, "safety_gate_error"
        if safe and (
            understanding.best is not None
            and understanding.best.confidence >= 0.8
        ):
            best = understanding.best
            character_hint = {
                "key": best.canonical_id,
                "display_name": best.display_name,
                "series": best.series_name,
                "series_key": best.series_slug,
                "character_tag": best.character_slug,
                "source": f"understanding:{best.source}",
            }
            logger.info(
                "[reasoning_image_gen] auto-filled character_hint from understanding: %s",
                best.canonical_id,
            )
        else:
            # Auto-attach blocked — surface why so frontend / logs can show it.
            if not safe:
                lora_blocked_reason = reason
            elif understanding.best is not None and understanding.best.confidence < 0.8:
                lora_blocked_reason = "below_confidence_threshold"
            else:
                lora_blocked_reason = "no_best_candidate"
            logger.info(
                "[reasoning_image_gen] auto-attach blocked: %s",
                lora_blocked_reason,
            )
    if understanding_payload is not None:
        understanding_payload["lora_blocked_reason"] = lora_blocked_reason

    result = run_pipeline_for_prompt(
        prompt_text,
        layout=payload.get("layout"),
        attached_images=payload.get("attached_images") or 0,
        character_hint=character_hint,
    )
    status_code = int(result.pop("status_code", 200))
    if understanding_payload is not None:
        result["understanding"] = understanding_payload
    result["preflight_assessment"] = preflight
    result["cost"] = cost
    return jsonify(result), status_code


__all__ = ["reasoning_image_gen_bp", "run_pipeline_for_prompt"]
