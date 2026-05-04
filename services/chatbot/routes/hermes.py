"""
Flask blueprint — Hermes Agent proxy route.

Provides:
  POST /api/hermes/chat — proxy to Hermes sidecar (JSON response)

Bridge behavior (opt-in, requires REASONING_PIPELINE=true):
  When both HERMES_ENABLED and REASONING_PIPELINE are active, incoming messages
  are first classified by image_pipeline.reasoning.capability_router. If the
  message is confidently an image-generation request (confidence >= 0.75), the
  route redirects to the reasoning-image-gen pipeline instead of Hermes.

  This allows Hermes to serve as a unified chat endpoint while transparently
  offloading image work to the local ComfyUI pipeline.

  Bridge is fully opt-in and fails-safe: if REASONING_PIPELINE is false, or
  image_pipeline is not importable, classification is skipped and the request
  goes to Hermes unchanged.
"""
import logging

from flask import Blueprint, jsonify, request

hermes_bp = Blueprint('hermes', __name__)
logger = logging.getLogger(__name__)


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
    # Only active when REASONING_PIPELINE=true. Fails-safe: any error falls
    # through to the normal Hermes path.
    try:
        from core.image_intent import detect_image_intent, IMAGE_KINDS_NAMES, is_reasoning_pipeline_enabled
        if is_reasoning_pipeline_enabled():
            decision = detect_image_intent(message)
            if decision is not None and decision.kind.value in IMAGE_KINDS_NAMES and decision.confidence >= 0.75:
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
            'error': f'Internal error: {e}',
        }), 500

    status_code = 200 if result.get('success') else 422
    return jsonify(result), status_code


def _call_reasoning_pipeline(message: str, decision) -> tuple:
    """Call the reasoning-image-gen pipeline and return a Flask response tuple.

    Internally calls the same logic as POST /api/reasoning-image-gen/generate
    but without doing a real HTTP round-trip (direct function call).

    Returns a (jsonify(result), status_code) tuple compatible with what
    hermes_chat_route normally returns — bridge is transparent to callers.
    """
    try:
        # Import the reasoning route handler directly to avoid HTTP round-trip.
        # routes/reasoning_image_gen.py must be registered (REASONING_PIPELINE=true).
        from routes.reasoning_image_gen import run_reasoning_pipeline  # noqa: PLC0415
        result = run_reasoning_pipeline(
            prompt=message,
            capability_decision=decision.to_dict(),
        )
        return jsonify({
            'success': True,
            'result': result.get('result', ''),
            'source': 'reasoning_pipeline',
            'capability': decision.kind.value,
            'elapsed_s': result.get('elapsed_s', 0),
        }), 200
    except (ImportError, AttributeError) as imp_err:
        # reasoning_image_gen route not registered or API changed — fall back silently.
        logger.warning(
            "[HERMES-ROUTE] reasoning_image_gen not available (%s) — using Hermes fallback",
            imp_err,
        )
        from core.hermes_adapter import hermes_chat
        result = hermes_chat(message)
        status_code = 200 if result.get('success') else 422
        return jsonify(result), status_code
