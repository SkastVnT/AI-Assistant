"""Asset memory: structured records for previously generated images.

This module is the single place that knows the canonical shape of a
"generated image record" the chatbot remembers across turns, and how to
format that record into concise context lines the LLM can consume.

Design constraints (per chatbot-core skill set):
  * stdlib only — must run in venv-core without extras.
  * No I/O at import time.
  * No new dotenv loaders (shared_env already loaded by the host service).
  * Backwards compatible with the old frontend payload shape that only
    carried ``{url, prompt, provider, model, timestamp}``.
  * Never inflate context: hard caps on field length and record count.
  * Manifest reads are sandboxed and size-capped — a malformed or
    attacker-controlled manifest_path must not crash the request or
    leak filesystem state.

The companion frontend lives in
``services/chatbot/static/js/modules/chat-manager.js`` (``addGeneratedImage``).
The two sides agree on field names; new fields are all optional so old
sessions keep working.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Iterable
from typing import Any

logger = logging.getLogger(__name__)

# ── Field caps (mirror frontend so payloads coming back match what we store) ──
MAX_PROMPT_LEN = 240
MAX_URL_LEN = 500
MAX_SHORT_FIELD_LEN = 64
MAX_PATH_LEN = 400
MAX_RECORDS_IN_CONTEXT = 5
MAX_MANIFEST_BYTES = 256 * 1024  # 256 KiB — generous, but bounded

# Canonical ordered list of fields a normalized record carries.
# Keep this in sync with the frontend session shape and any docs.
ASSET_RECORD_FIELDS = (
    "job_id",
    "conversation_id",
    "url",
    "prompt",
    "provider",
    "model",
    "timestamp",
    "character_key",
    "series_key",
    "preset",
    "manifest_path",
    "seed",
)


def _clip(value: Any, limit: int) -> str | None:
    """Return a stringified, length-capped value or None for empties."""
    if value is None:
        return None
    try:
        s = str(value).strip()
    except Exception:
        return None
    if not s:
        return None
    return s[:limit]


def _coerce_int(value: Any) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_asset_record(
    raw: Any,
    *,
    default_conversation_id: str | None = None,
) -> dict | None:
    """Coerce *raw* (legacy or new shape) into the canonical asset record.

    Returns ``None`` when the input cannot be salvaged into something
    referenceable (no url AND no prompt AND no job_id).

    Extra/unknown keys are dropped. Missing keys become ``None``. This is
    the migration path for sessions that were saved before the asset
    schema existed and only carried ``{url, prompt, provider, model, timestamp}``.
    """
    if not isinstance(raw, dict):
        return None

    url = _clip(raw.get("url") or raw.get("image_url") or raw.get("path"), MAX_URL_LEN)
    # Reject base64 inline blobs — they would bloat both storage and context.
    if url and url.startswith("data:"):
        url = None

    record = {
        "job_id": _clip(raw.get("job_id"), MAX_SHORT_FIELD_LEN),
        "conversation_id": _clip(
            raw.get("conversation_id") or default_conversation_id,
            MAX_SHORT_FIELD_LEN,
        ),
        "url": url,
        "prompt": _clip(raw.get("prompt"), MAX_PROMPT_LEN),
        "provider": _clip(raw.get("provider"), MAX_SHORT_FIELD_LEN),
        "model": _clip(raw.get("model"), MAX_SHORT_FIELD_LEN),
        "timestamp": _coerce_int(raw.get("timestamp")),
        "character_key": _clip(raw.get("character_key"), MAX_SHORT_FIELD_LEN),
        "series_key": _clip(raw.get("series_key"), MAX_SHORT_FIELD_LEN),
        "preset": _clip(raw.get("preset"), MAX_SHORT_FIELD_LEN),
        "manifest_path": _clip(raw.get("manifest_path"), MAX_PATH_LEN),
        "seed": _coerce_int(raw.get("seed")),
    }

    if not (record["url"] or record["prompt"] or record["job_id"]):
        return None
    return record


def _safe_load_manifest(manifest_path: str) -> dict | None:
    """Read a manifest JSON file with strict bounds and no path traversal.

    The check rejects paths containing ``..`` segments and refuses files
    larger than ``MAX_MANIFEST_BYTES``. Errors are logged at DEBUG and
    swallowed — manifest enrichment is best-effort.
    """
    if not manifest_path:
        return None
    if ".." in manifest_path.replace("\\", "/").split("/"):
        logger.debug(
            "asset_memory: rejecting manifest path with .. segment: %r", manifest_path
        )
        return None
    try:
        if not os.path.isfile(manifest_path):
            return None
        size = os.path.getsize(manifest_path)
        if size <= 0 or size > MAX_MANIFEST_BYTES:
            logger.debug("asset_memory: manifest size out of bounds (%d bytes)", size)
            return None
        with open(manifest_path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError) as exc:
        logger.debug(
            "asset_memory: manifest read failed for %r: %s", manifest_path, exc
        )
        return None
    return data if isinstance(data, dict) else None


def _manifest_summary(manifest: dict) -> str:
    """Produce a one-line summary of the relevant manifest fields.

    Pulls the small handful the LLM benefits from knowing — preset,
    character_key, seed, models_used. Anything missing is skipped.
    """
    parts: list[str] = []
    for key in ("preset", "character_key", "series_key", "seed"):
        val = manifest.get(key)
        if val not in (None, "", []):
            parts.append(f"{key}={val}")
    models_used = manifest.get("models_used")
    if isinstance(models_used, (list, tuple)) and models_used:
        models_str = ",".join(str(m)[:32] for m in list(models_used)[:4])
        parts.append(f"models=[{models_str}]")
    refine_rounds = manifest.get("refine_rounds")
    if isinstance(refine_rounds, int) and refine_rounds > 0:
        parts.append(f"refine_rounds={refine_rounds}")
    return ", ".join(parts)


def format_asset_context_lines(
    records: Iterable[Any],
    *,
    max_records: int = MAX_RECORDS_IN_CONTEXT,
    enrich_from_manifest: bool = True,
) -> list[str]:
    """Format a sequence of (raw or normalized) records into context lines.

    Each line is concise, structured, and skips empty fields. When a
    record has a ``manifest_path`` and ``enrich_from_manifest=True``, the
    manifest is read (sandboxed) and its summary is appended to the line —
    this is the "manifest-backed context preferred over shallow context"
    path called out in the upgrade brief.
    """
    if max_records <= 0:
        return []
    lines: list[str] = []
    seen = 0
    for raw in records:
        if seen >= max_records:
            break
        rec = normalize_asset_record(raw)
        if rec is None:
            continue
        seen += 1

        head_bits: list[str] = []
        if rec["job_id"]:
            head_bits.append(f"job={rec['job_id']}")
        if rec["provider"] or rec["model"]:
            head_bits.append(f"by {rec['provider'] or '?'}/{rec['model'] or '?'}")
        if rec["preset"]:
            head_bits.append(f"preset={rec['preset']}")
        if rec["character_key"]:
            head_bits.append(f"character={rec['character_key']}")
        if rec["seed"] is not None:
            head_bits.append(f"seed={rec['seed']}")
        head = " | ".join(head_bits) if head_bits else "image"

        body_parts = [f"- {head}"]
        if rec["prompt"]:
            body_parts.append(f"  prompt: {rec['prompt']}")
        if rec["url"]:
            body_parts.append(f"  url: {rec['url']}")

        if enrich_from_manifest and rec["manifest_path"]:
            manifest = _safe_load_manifest(rec["manifest_path"])
            if manifest:
                summary = _manifest_summary(manifest)
                if summary:
                    body_parts.append(f"  manifest: {summary}")

        # Live local-pipeline state hint (only present on records that went
        # through core.image_pipeline_link.enrich_records_with_live_state).
        # Soft-imported so unit tests that exercise asset_memory in isolation
        # do not require the job_queue stack.
        try:
            from core.image_pipeline_link import format_pipeline_hint  # type: ignore
        except Exception:
            format_pipeline_hint = None  # type: ignore[assignment]
        if format_pipeline_hint is not None:
            hint = format_pipeline_hint(raw)
            if hint:
                body_parts.append(f"  {hint}")

        lines.append("\n".join(body_parts))
    return lines


def build_asset_context_block(
    records: Iterable[Any],
    *,
    max_records: int = MAX_RECORDS_IN_CONTEXT,
    enrich_from_manifest: bool = True,
) -> str:
    """Return a complete context block (header + lines + footer), or ''.

    Empty when there are no usable records. Callers append this directly
    to the user message before sending it to the LLM.
    """
    lines = format_asset_context_lines(
        records,
        max_records=max_records,
        enrich_from_manifest=enrich_from_manifest,
    )
    if not lines:
        return ""
    return (
        "\n\n[Ảnh đã được tạo trong cuộc trò chuyện này]\n"
        + "\n".join(lines)
        + "\n[Bạn có thể tham chiếu các ảnh này khi người dùng hỏi về chúng.]\n"
    )
