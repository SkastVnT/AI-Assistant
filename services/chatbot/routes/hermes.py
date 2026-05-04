"""
Flask blueprint — Hermes Agent proxy route.

Provides:
  POST /api/hermes/chat — proxy to Hermes sidecar (JSON response)

Bridge behavior (opt-in, requires REASONING_PIPELINE=true):
  When both HERMES_ENABLED and REASONING_PIPELINE are active, incoming messages
  are first classified by image_pipeline.reasoning.capability_router. The
  redirect to the reasoning image pipeline only fires when ALL of the
  following are true:

    1. The message contains at least one explicit image-generation keyword
       (Vietnamese or English). Generic chat phrasing — "giải thích",
       "tóm tắt", "audit", "what is this", "summarize" — never triggers
       redirect, even if the classifier guesses TEXT_TO_IMAGE.
    2. The classifier returns an image-capable kind (text_to_image,
       comic_sequence, image_edit, multi_image_compose, iterative_refine).
    3. Confidence >= 0.75.

  Bridge is fully opt-in and fails-safe: any error during gating, import,
  classification, or pipeline execution falls through to Hermes unchanged.

  Note: the FastAPI mirror at fastapi_app/routers/hermes.py does NOT
  implement this bridge today. See docs/INTEGRATION_MAP.md §1 for the
  parity gap.
"""
import logging
import re
import time

from flask import Blueprint, jsonify, request

hermes_bp = Blueprint('hermes', __name__)
logger = logging.getLogger(__name__)


# ── Image-intent keyword guard ───────────────────────────────────────────────
# Conservative whitelist: redirect only when the user message explicitly asks
# for an image. Curated for the chatbot's UI (Vietnamese-first, English second).
# Patterns are word-boundary or phrase-anchored to avoid matches inside
# normal chat (e.g. "ảnh hưởng" must not match "ảnh").
_IMAGE_KEYWORD_RE = re.compile(
    r"(?:"
    # Vietnamese phrases (require verb context so bare "ảnh" doesn't match)
    r"\btạo\s+(?:ảnh|tranh|hình)\b"
    r"|\bsinh\s+(?:ảnh|tranh|hình)\b"
    r"|\bvẽ\s+(?:ảnh|tranh|hình|cho|một|cái|cảnh|nhân vật|người|chân dung)?\b"
    r"|\bvẽ\s+\w+"   # "vẽ Hoshino", "vẽ landscape"
    r"|\b(?:làm|render|tạo)\s+(?:cho\s+\w+\s+)?(?:bức\s+)?(?:ảnh|tranh|hình|comic|truyện\s+tranh|webtoon)\b"
    r"|\b(?:bức\s+)?tranh\s+(?:vẽ|của|về)\b"
    r"|\btruyện\s+tranh\b"
    # English phrases
    r"|\b(?:generate|create|make|draw|paint|render|produce)\s+(?:an?|the|me|us|some)?\s*"
    r"(?:image|images|picture|pictures|pic|pics|illustration|illustrations|"
    r"comic|comics|manga|webtoon|storyboard|panel|panels|scene|scenes|"
    r"artwork|portrait|drawing|sketch|wallpaper)\b"
    r"|\bdraw\s+\w+"   # "draw Hoshino", "draw a cat"
    r"|\bpaint\s+\w+"
    r"|\bsketch\s+\w+"
    r"|\b(?:image|comic|manga|webtoon|storyboard)\s+of\b"
    r"|\b\d+[-\s]?panel\b"
    r")",
    re.IGNORECASE,
)


def _has_image_keyword(message: str) -> bool:
    """Return True iff the message contains an explicit image-generation cue.

    This is a guard layered on top of the capability classifier — the
    classifier alone over-triggers on prompts like "show me X" or "vẽ" used
    figuratively. Combined gating: classifier confidence ≥ 0.75 AND keyword
    present.
    """
    if not message:
        return False
    # Cap length to avoid ReDoS on adversarial inputs with many repeated spaces.
    return _IMAGE_KEYWORD_RE.search(message[:2000]) is not None


@hermes_bp.route('/api/hermes/chat', methods=['POST'])
def hermes_chat_route():
    """Forward a chat request to the Hermes Agent sidecar.

    If REASONING_PIPELINE=true and the message is classified as an image
    request (confidence >= 0.75), the call is redirected to the reasoning
    image-gen pipeline and the response is returned directly without touching
    the Hermes sidecar.
    """
    data = request.get_json(silent=True) or {}

    message = (data.get('message') or '').strip()
    if not message:
        return jsonify({
            'success': False, 'result': '', 'error': 'Missing required field: message',
        }), 400

    conversation_history = data.get('conversation_history')
    if conversation_history is not None and not isinstance(conversation_history, list):
        conversation_history = None

    model = data.get('model') or None

    logger.info(
        "[HERMES-ROUTE] Request: msg_len=%d model=%s history_len=%d",
        len(message), model, len(conversation_history or []),
    )

    # ── Reasoning-pipeline bridge (opt-in) ────────────────────────────────────
    # Only active when REASONING_PIPELINE=true AND the message contains an
    # explicit image-generation keyword AND the classifier agrees with high
    # confidence. Fails-safe: any error falls through to the normal Hermes
    # path.
    try:
        from core.image_intent import (
            detect_image_intent,
            IMAGE_KINDS_NAMES,
            is_reasoning_pipeline_enabled,
        )
        if is_reasoning_pipeline_enabled() and _has_image_keyword(message):
            decision = detect_image_intent(message)
            if (
                decision is not None
                and decision.kind.value in IMAGE_KINDS_NAMES
                and decision.confidence >= 0.75
            ):
                logger.info(
                    "[HERMES-ROUTE] Redirecting to reasoning pipeline — kind=%s confidence=%.2f",
                    decision.kind.value, decision.confidence,
                )
                return _call_reasoning_pipeline(message, decision)
    except Exception as _bridge_err:
        logger.warning("[HERMES-ROUTE] Bridge check failed (%s) — falling through to Hermes", _bridge_err)
    # ── End bridge ────────────────────────────────────────────────────────────

    try:
        from core.hermes_adapter import hermes_chat
        result = hermes_chat(
            message,
            conversation_history=conversation_history,
            model=model,
        )
    except Exception as e:
        logger.error("[HERMES-ROUTE] Unhandled error: %s", e)
        return jsonify({
            'success': False, 'result': '',
            'error': 'Internal server error',
        }), 500

    status_code = 200 if result.get('success') else 422
    return jsonify(result), status_code


def _call_reasoning_pipeline(message: str, decision) -> tuple:
    """Call the reasoning-image-gen pipeline and return a Flask response tuple.

    Calls :func:`routes.reasoning_image_gen.run_pipeline_for_prompt` directly
    (no HTTP round-trip). Maps the pipeline's image-bearing response into the
    Hermes ``{success, result, ...}`` shape so the frontend doesn't need to
    branch on the route source.

    On any failure (route not registered, pipeline error, missing image),
    falls back to a normal Hermes call so the user always gets a response.
    """
    started = time.monotonic()
    try:
        # routes/reasoning_image_gen.py is registered only when
        # REASONING_PIPELINE_ENABLED — guarded by the caller.
        from routes.reasoning_image_gen import run_pipeline_for_prompt  # noqa: PLC0415

        pipeline_result = run_pipeline_for_prompt(message)
    except (ImportError, AttributeError) as imp_err:
        logger.warning(
            "[HERMES-ROUTE] reasoning_image_gen unavailable (%s) — using Hermes fallback",
            imp_err,
        )
        return _fallback_to_hermes(message)
    except Exception as exc:
        logger.error("[HERMES-ROUTE] reasoning pipeline raised: %s", exc)
        return _fallback_to_hermes(message)

    elapsed_s = time.monotonic() - started

    # Pipeline returned a structured failure (e.g. parse failed, no panels).
    # Don't silently fall through — surface the error to the caller.
    if not pipeline_result.get("success"):
        logger.warning("[HERMES-ROUTE] reasoning pipeline failure: %s", pipeline_result.get("error"))
        return jsonify({
            "success": False,
            "result": "",
            "error": "reasoning pipeline failed",
            "source": "reasoning_pipeline",
            "elapsed_s": elapsed_s,
        }), 422

    image_b64 = pipeline_result.get("image_b64") or ""
    if not image_b64:
        return _fallback_to_hermes(message)

    # Markdown response so the chat UI can render the image inline without a
    # special-case renderer. Matches the tool-response-contract used by other
    # image tools.
    markdown = f"![reasoning-pipeline-output](data:image/png;base64,{image_b64})"
    return jsonify({
        "success": True,
        "result": markdown,
        "image_b64": image_b64,
        "source": "reasoning_pipeline",
        "job_id": pipeline_result.get("job_id"),
        "elapsed_s": elapsed_s,
    }), 200


def _fallback_to_hermes(message: str) -> tuple:
    """Run the standard Hermes adapter call and shape the response tuple."""
    from core.hermes_adapter import hermes_chat  # noqa: PLC0415
    result = hermes_chat(message)
    status_code = 200 if result.get("success") else 422
    return jsonify(result), status_code
