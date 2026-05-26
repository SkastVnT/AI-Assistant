"""
Shared request normalization for the chat endpoints.

Both /chat (routes/main.py) and /chat/stream (routes/stream.py) historically
parsed the inbound request inline, and they drifted apart on three concrete
contracts that the frontend depends on:

  1. conversation_id — extracted, validated, and bound to the Flask session
     so downstream save_message_to_db / load_conversation_history target the
     conversation the user is actually viewing in the URL bar.
  2. generated_images — converted into a structured asset context block via
     core.asset_memory so the LLM can see what was generated earlier in the
     conversation (URL, prompt, manifest summary, character key, …).
  3. history — capped to a sane upper bound so a runaway client cannot push
     unbounded payloads through the JSON body.

This module owns those three contracts. Both endpoints call into it. If a
fourth contract appears, add it here rather than re-implementing it in two
places.

Scope notes:
  - This module is intentionally **not** a full request-handler abstraction.
    It does not own message extraction, file upload handling, multipart
    decoding, skill resolution, MCP injection, or model routing — those
    have endpoint-specific shapes (multipart for /chat, SSE for /chat/stream)
    that would be premature to merge in this step.
  - It also does not consolidate the two ChatbotAgent classes
    (core/chatbot.py vs core/chatbot_v2.py). That is a deliberate, larger
    refactor tracked separately. See the LEGACY V1 marker in core/chatbot.py.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, MutableMapping, Sequence
from typing import Any

from core.asset_memory import build_asset_context_block

# ── conversation_id ──────────────────────────────────────────────────────

# Same pattern enforced on the URL route /c/<conversation_id> in chatbot_main.py.
# Keeping the regex here so the helper can be reused without importing Flask.
_CONVERSATION_ID_RE = re.compile(r"[A-Za-z0-9_\-]{1,64}")
_CONVERSATION_ID_MAX = 64


def extract_conversation_id(data: Mapping[str, Any] | None) -> str:
    """Pull a conversation_id out of a request payload.

    Returns the validated id, or '' when missing/invalid. Truncates to 64 chars
    before validation so an oversized client value is silently rejected rather
    than partially accepted (which would open a hole between truncate and
    validate steps).
    """
    if not data:
        return ""
    raw = data.get("conversation_id")
    if not isinstance(raw, str):
        return ""
    candidate = raw.strip()[:_CONVERSATION_ID_MAX]
    if not candidate:
        return ""
    return candidate if _CONVERSATION_ID_RE.fullmatch(candidate) else ""


def bind_conversation_id_to_session(
    flask_session: MutableMapping[str, Any] | None,
    conversation_id: str,
) -> bool:
    """Bind a validated conversation_id onto the Flask session.

    Returns True when the bind happened. Safe to call with an empty id (no-op).
    Failures are swallowed — binding is a best-effort signal for downstream
    persistence layers, not a precondition for the request itself.
    """
    if not conversation_id or flask_session is None:
        return False
    try:
        flask_session["conversation_id"] = conversation_id
        return True
    except Exception:
        return False


# ── generated_images → asset context block ───────────────────────────────


def extract_generated_images(data: Mapping[str, Any] | None) -> list:
    """Return the generated_images list from the payload, or [] if missing.

    Drops non-list values silently — the asset-memory normalizer handles
    record-level validation, but we don't want to feed it a string or dict.
    """
    if not data:
        return []
    raw = data.get("generated_images")
    if isinstance(raw, list):
        return raw
    return []


def apply_image_context(
    message: str, generated_images: Sequence[Any]
) -> tuple[str, int]:
    """Append the structured asset context block (if any) to the message.

    Returns (message_with_context, injected_count). ``injected_count`` is the
    number of asset records that survived normalization, which is what the
    caller wants to log as ``Injected N image(s) into context``.

    Safe on bad input — the build helper itself swallows record errors and
    returns ''. We re-raise nothing.
    """
    if not generated_images:
        return message or "", 0
    # Local-pipeline enrichment: records that only carry a job_id (the
    # frontend stores those after an anime-pipeline run) get back-filled
    # with manifest_path / character_key / preset / live state from the
    # JobQueue singleton. Soft-imported so tests can exercise this module
    # without the queue subsystem present.
    try:
        from core.image_pipeline_link import enrich_records_with_live_state

        records_for_block = enrich_records_with_live_state(generated_images)
    except Exception:
        records_for_block = generated_images
    try:
        block = build_asset_context_block(records_for_block)
    except Exception:
        return message or "", 0
    if not block:
        return message or "", 0
    # Count the structured bullet lines the formatter emits. Mirrors the
    # existing log line in stream.py so observability does not change.
    injected = sum(1 for line in block.split("\n") if line.startswith("- "))
    return ((message or "") + block), injected


# ── history cap ──────────────────────────────────────────────────────────

# Mirrors the frontend cap in static/js/main.js buildConversationHistory().
# Defending in depth so a misbehaving (or compromised) client cannot push
# unbounded history through either endpoint.
DEFAULT_HISTORY_MAX_TURNS = 30
DEFAULT_HISTORY_MAX_CHARS = 4000


def cap_history(
    history: Any,
    *,
    max_turns: int = DEFAULT_HISTORY_MAX_TURNS,
    max_chars_per_turn: int = DEFAULT_HISTORY_MAX_CHARS,
) -> list | None:
    """Cap a history list to bound payload size, preserving wire shape.

    Returns the capped ``[{role, content}, ...]`` list, or None if the input
    is None/missing (so the caller can distinguish 'no history sent' from
    'empty history').

    Drops non-dict entries and entries without role/content. Truncates per-turn
    content to ``max_chars_per_turn``. Keeps the most recent ``max_turns``.
    """
    if history is None:
        return None
    if not isinstance(history, list):
        return []

    cleaned: list[dict] = []
    for entry in history:
        if not isinstance(entry, dict):
            continue
        role = entry.get("role")
        content = entry.get("content")
        if role not in ("user", "assistant", "system"):
            continue
        if not isinstance(content, str):
            continue
        if len(content) > max_chars_per_turn:
            content = content[:max_chars_per_turn] + "\n…(truncated)"
        cleaned.append({"role": role, "content": content})

    if len(cleaned) > max_turns:
        cleaned = cleaned[-max_turns:]
    return cleaned


# ── Convenience: normalize the three contracts in one pass ───────────────


def normalize_chat_request(
    data: Mapping[str, Any] | None,
    flask_session: MutableMapping[str, Any] | None = None,
    *,
    message: str | None = None,
    cap_history_turns: int = DEFAULT_HISTORY_MAX_TURNS,
    cap_history_chars: int = DEFAULT_HISTORY_MAX_CHARS,
) -> dict:
    """Apply all three shared contracts and return the normalized fields.

    Returns a dict with::

        {
            'conversation_id': str,           # '' when missing/invalid
            'conversation_id_bound': bool,    # True when bound to flask_session
            'generated_images': list,
            'message': str,                   # message with image context appended
            'image_context_count': int,
            'history': list | None,
        }

    The caller still owns message extraction (multipart vs json), skill
    resolution, MCP injection, and model routing. This helper only enforces
    the contracts that the two endpoints had been silently disagreeing on.
    """
    conversation_id = extract_conversation_id(data)
    bound = bind_conversation_id_to_session(flask_session, conversation_id)

    generated_images = extract_generated_images(data)
    msg_in = message if message is not None else (data or {}).get("message", "") or ""
    msg_out, injected = apply_image_context(msg_in, generated_images)

    history = cap_history(
        (data or {}).get("history"),
        max_turns=cap_history_turns,
        max_chars_per_turn=cap_history_chars,
    )

    return {
        "conversation_id": conversation_id,
        "conversation_id_bound": bound,
        "generated_images": generated_images,
        "message": msg_out,
        "image_context_count": injected,
        "history": history,
    }
