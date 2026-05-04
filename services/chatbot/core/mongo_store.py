"""MongoDB persistence for chatbot activity logging (schema v2).

Fail-safe wrapper around the v2 collections used by the chatbot:

* ``conversations``      — per-conversation envelope.
* ``messages``           — chat / tool / image-result message log.
* ``tool_calls``         — tool invocation lifecycle.
* ``uploaded_files``     — file metadata only (no bytes, no base64).
* ``character_profiles`` — per-character resolved/manual identity records.
* ``generation_jobs``    — preflight + image-gen lifecycle state.
* ``image_assets``       — image file metadata. Never bytes.

Design rules:

* Reads ``MONGODB_URI`` and the database name from env. Database name
  resolution order: ``MONGODB_DB`` → ``MONGODB_DB_NAME`` → default
  ``"ai_assistant_v2"``. The legacy ``MONGODB_DB_NAME`` is honored
  only as a fallback so existing deployments keep working; new code
  paths target ``ai_assistant_v2``.
* If the URI is missing, OR pymongo is not installed, OR the client
  cannot ping the server, this module reports disabled and ALL
  save/update functions become no-ops returning
  ``{"ok": False, "disabled": True}``. They never raise.
* Every persisted document carries ``schema_version: 2`` and ISO-8601
  ``created_at`` / ``updated_at`` timestamps where appropriate.
* No image / file bytes / base64 are ever stored. ``image_assets`` and
  ``uploaded_files`` reference ``local_path`` / ``public_url`` /
  ``sha256`` only.
* No GridFS.
* Index creation is best-effort and never required for save calls.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime, timezone
from typing import Any, Mapping

logger = logging.getLogger(__name__)

# ── Connection state (module-private, lazily initialized) ──────────────

_LOCK = threading.Lock()


class _MongoState:
    """Container for MongoDB connection state.

    Using a single mutable object avoids ``global`` declarations for
    each individual state variable, which in turn makes the data-flow
    clear to static-analysis tools.
    """

    __slots__ = ("initialized", "client", "db", "disabled_reason", "indexes_ensured")

    def __init__(self) -> None:
        self.initialized: bool = False
        self.client: Any = None
        self.db: Any = None
        self.disabled_reason: str = ""
        self.indexes_ensured: bool = False


_state = _MongoState()

SCHEMA_VERSION = 2
_DEFAULT_DB_NAME = "ai_assistant_v2"


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_env() -> tuple[str, str]:
    """Resolve (uri, db_name).

    DB name resolution: MONGODB_DB → MONGODB_DB_NAME → default v2.
    URI must be supplied explicitly; never defaulted to localhost so
    misconfigured deploys don't silently write to a stranger's mongod.
    """
    uri = (os.getenv("MONGODB_URI") or "").strip()
    db_name = (
        (os.getenv("MONGODB_DB") or "").strip()
        or (os.getenv("MONGODB_DB_NAME") or "").strip()
        or _DEFAULT_DB_NAME
    )
    return uri, db_name


def _init() -> None:
    """Lazy one-shot connection attempt. Idempotent."""
    if _state.initialized:
        return
    with _LOCK:
        if _state.initialized:
            return
        _state.initialized = True
        # Optional explicit kill-switch. When set falsy, do not even
        # attempt to connect.
        enabled_flag = (os.getenv("MONGODB_ENABLED") or "").strip().lower()
        if enabled_flag in ("0", "false", "no", "off"):
            _state.disabled_reason = "MONGODB_ENABLED is false"
            logger.info("mongo_store disabled: %s", _state.disabled_reason)
            return
        uri, db_name = _read_env()
        if not uri:
            _state.disabled_reason = "missing MONGODB_URI"
            logger.info("mongo_store disabled: %s", _state.disabled_reason)
            return
        try:
            from pymongo import MongoClient  # noqa: PLC0415
        except Exception as exc:  # noqa: BLE001
            _state.disabled_reason = f"pymongo import failed: {exc}"
            logger.warning("mongo_store disabled: %s", _state.disabled_reason)
            return
        try:
            client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            client.admin.command("ping")
            _state.client = client
            _state.db = client[db_name]
            logger.info("mongo_store connected -> db=%s", db_name)
        except Exception as exc:  # noqa: BLE001
            _state.disabled_reason = f"connect/ping failed: {exc}"
            logger.warning("mongo_store disabled: %s", _state.disabled_reason)
            _state.client = None
            _state.db = None


def is_mongo_enabled() -> bool:
    """Return True iff the client connected and a DB handle is available."""
    _init()
    return _state.db is not None


def get_mongo_db() -> Any:
    """Return the active database handle, or ``None`` when disabled."""
    _init()
    return _state.db


def ensure_indexes() -> dict:
    """Best-effort index creation. Public so callers may force it on boot.

    Always idempotent; never raises. Returns a small status dict.
    """
    _init()
    return _ensure_indexes_internal(force=True)


def _ensure_indexes_internal(*, force: bool = False) -> dict:
    if _state.db is None:
        return {"ok": False, "disabled": True}
    if _state.indexes_ensured and not force:
        return {"ok": True, "skipped": True}
    _state.indexes_ensured = True  # mark up-front so failures don't retry forever
    created: list[str] = []
    try:
        from pymongo import ASCENDING  # noqa: PLC0415
        # conversations
        _state.db["conversations"].create_index("conversation_id", unique=True)
        created.append("conversations.conversation_id")
        # messages
        _state.db["messages"].create_index("message_id", unique=True)
        _state.db["messages"].create_index([
            ("conversation_id", ASCENDING), ("created_at", ASCENDING),
        ])
        created.append("messages.message_id+conversation_id+created_at")
        # tool_calls
        _state.db["tool_calls"].create_index("tool_call_id", unique=True)
        _state.db["tool_calls"].create_index("conversation_id")
        created.append("tool_calls.tool_call_id+conversation_id")
        # uploaded_files
        _state.db["uploaded_files"].create_index("file_id", unique=True)
        created.append("uploaded_files.file_id")
        # character_profiles
        _state.db["character_profiles"].create_index("canonical_id", unique=True)
        created.append("character_profiles.canonical_id")
        # generation_jobs
        _state.db["generation_jobs"].create_index("job_id", unique=True)
        _state.db["generation_jobs"].create_index("character_result.canonical_id")
        _state.db["generation_jobs"].create_index("status")
        _state.db["generation_jobs"].create_index("created_at")
        created.append("generation_jobs.job_id+character+status+created_at")
        # image_assets
        _state.db["image_assets"].create_index("image_id", unique=True)
        _state.db["image_assets"].create_index("job_id")
        _state.db["image_assets"].create_index("canonical_id")
        _state.db["image_assets"].create_index("sha256")
        created.append("image_assets.image_id+job+canonical+sha256")
        return {"ok": True, "created": created}
    except Exception as exc:  # noqa: BLE001
        logger.warning("mongo_store ensure_indexes failed (non-fatal): %s", exc)
        return {"ok": False, "error": str(exc)}


def _disabled_response() -> dict:
    return {"ok": False, "disabled": True, "reason": _state.disabled_reason}


# Keys forbidden in any persisted document — defense-in-depth so callers
# can't accidentally store binary blobs / base64 / file bytes.
_FORBIDDEN_KEYS = (
    "data", "data_b64", "image_b64", "bytes", "binary",
    "file_bytes", "file_b64", "content_b64",
)


def _strip_forbidden(doc: Mapping[str, Any]) -> dict:
    return {k: v for k, v in dict(doc).items() if k not in _FORBIDDEN_KEYS}


# ── conversations ──────────────────────────────────────────────────────


def save_conversation(doc: Mapping[str, Any]) -> dict:
    """Insert (or upsert) a conversation envelope keyed by ``conversation_id``."""
    if not is_mongo_enabled():
        return _disabled_response()
    conversation_id = (doc.get("conversation_id") or "").strip()
    if not conversation_id:
        return {"ok": False, "error": "missing conversation_id"}
    now = _utcnow_iso()
    body = _strip_forbidden(doc)
    body["conversation_id"] = conversation_id
    body["schema_version"] = SCHEMA_VERSION
    body.setdefault("title", "")
    body.setdefault("last_message_at", now)
    body["updated_at"] = now
    try:
        _ensure_indexes_internal()
        _state.db["conversations"].update_one(
            {"conversation_id": conversation_id},
            {"$set": body, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return {"ok": True, "conversation_id": conversation_id}
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_conversation failed: %s", exc)
        return {"ok": False, "error": str(exc)}


def update_conversation(conversation_id: str, patch: Mapping[str, Any]) -> dict:
    if not is_mongo_enabled():
        return _disabled_response()
    conversation_id = (conversation_id or "").strip()
    if not conversation_id:
        return {"ok": False, "error": "missing conversation_id"}
    update = _strip_forbidden(patch)
    update["updated_at"] = _utcnow_iso()
    try:
        result = _state.db["conversations"].update_one(
            {"conversation_id": conversation_id}, {"$set": update}
        )
        return {
            "ok": True,
            "conversation_id": conversation_id,
            "matched": getattr(result, "matched_count", 0),
            "modified": getattr(result, "modified_count", 0),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("update_conversation failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ── messages ───────────────────────────────────────────────────────────


def save_message(doc: Mapping[str, Any]) -> dict:
    """Insert a message log entry keyed by ``message_id``.

    Strips any binary/base64 keys. Side-effect: bumps the parent
    conversation's ``last_message_at`` when ``conversation_id`` is set.
    """
    if not is_mongo_enabled():
        return _disabled_response()
    message_id = (doc.get("message_id") or "").strip()
    if not message_id:
        return {"ok": False, "error": "missing message_id"}
    now = _utcnow_iso()
    body = _strip_forbidden(doc)
    body["message_id"] = message_id
    body["schema_version"] = SCHEMA_VERSION
    body.setdefault("role", "user")
    body.setdefault("message_type", "chat")
    body.setdefault("content", "")
    body.setdefault("metadata", {})
    body.setdefault("attachments", [])
    body.setdefault("created_at", now)
    body["updated_at"] = now
    try:
        _ensure_indexes_internal()
        _state.db["messages"].update_one(
            {"message_id": message_id},
            {"$setOnInsert": body},
            upsert=True,
        )
        conv_id = (body.get("conversation_id") or "").strip()
        if conv_id:
            try:
                _state.db["conversations"].update_one(
                    {"conversation_id": conv_id},
                    {"$set": {"last_message_at": now, "updated_at": now}},
                )
            except Exception:  # noqa: BLE001
                pass  # parent bump is best-effort
        return {"ok": True, "message_id": message_id}
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_message failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ── tool_calls ─────────────────────────────────────────────────────────


def save_tool_call(doc: Mapping[str, Any]) -> dict:
    if not is_mongo_enabled():
        return _disabled_response()
    tool_call_id = (doc.get("tool_call_id") or "").strip()
    if not tool_call_id:
        return {"ok": False, "error": "missing tool_call_id"}
    now = _utcnow_iso()
    body = _strip_forbidden(doc)
    body["tool_call_id"] = tool_call_id
    body["schema_version"] = SCHEMA_VERSION
    body.setdefault("status", "running")
    body.setdefault("input_summary", {})
    body.setdefault("result_summary", {})
    body.setdefault("error", None)
    body.setdefault("started_at", now)
    body.setdefault("created_at", now)
    body["updated_at"] = now
    try:
        _ensure_indexes_internal()
        _state.db["tool_calls"].update_one(
            {"tool_call_id": tool_call_id},
            {"$setOnInsert": body},
            upsert=True,
        )
        return {"ok": True, "tool_call_id": tool_call_id}
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_tool_call failed: %s", exc)
        return {"ok": False, "error": str(exc)}


def update_tool_call(tool_call_id: str, patch: Mapping[str, Any]) -> dict:
    if not is_mongo_enabled():
        return _disabled_response()
    tool_call_id = (tool_call_id or "").strip()
    if not tool_call_id:
        return {"ok": False, "error": "missing tool_call_id"}
    update = _strip_forbidden(patch)
    update["updated_at"] = _utcnow_iso()
    if update.get("status") in ("completed", "failed") and "completed_at" not in update:
        update["completed_at"] = update["updated_at"]
    try:
        result = _state.db["tool_calls"].update_one(
            {"tool_call_id": tool_call_id}, {"$set": update}
        )
        return {
            "ok": True,
            "tool_call_id": tool_call_id,
            "matched": getattr(result, "matched_count", 0),
            "modified": getattr(result, "modified_count", 0),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("update_tool_call failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ── uploaded_files ─────────────────────────────────────────────────────


def save_uploaded_file(doc: Mapping[str, Any]) -> dict:
    """Insert an uploaded_files metadata record. Never stores file bytes."""
    if not is_mongo_enabled():
        return _disabled_response()
    file_id = (doc.get("file_id") or "").strip()
    if not file_id:
        return {"ok": False, "error": "missing file_id"}
    now = _utcnow_iso()
    body = _strip_forbidden(doc)
    body["file_id"] = file_id
    body["schema_version"] = SCHEMA_VERSION
    body.setdefault("file_name", "")
    body.setdefault("mime_type", "")
    body.setdefault("local_path", "")
    body.setdefault("file_size", 0)
    body.setdefault("purpose", "chat_attachment")
    body.setdefault("created_at", now)
    body["updated_at"] = now
    try:
        _ensure_indexes_internal()
        _state.db["uploaded_files"].update_one(
            {"file_id": file_id},
            {"$setOnInsert": body},
            upsert=True,
        )
        return {"ok": True, "file_id": file_id}
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_uploaded_file failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ── character_profiles ─────────────────────────────────────────────────


def upsert_character_profile(profile: Mapping[str, Any]) -> dict:
    """Upsert a character_profiles document keyed by ``canonical_id``.

    Identity-safety rule: when ``data_status`` is unknown/ambiguous/
    low_data, this clamps ``safe_to_attach_lora`` to False as defense
    in depth so a buggy caller cannot promote an unverified character.
    """
    if not is_mongo_enabled():
        return _disabled_response()
    canonical_id = (profile.get("canonical_id") or "").strip()
    if not canonical_id:
        return {"ok": False, "error": "missing canonical_id"}
    data_status = (profile.get("data_status") or "").strip().lower()
    safe_to_attach = bool(profile.get("safe_to_attach_lora", False))
    if data_status in ("unknown", "ambiguous", "low_data"):
        safe_to_attach = False
    now = _utcnow_iso()
    doc: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "canonical_id": canonical_id,
        "display_name": profile.get("display_name", ""),
        "series_slug": profile.get("series_slug", ""),
        "aliases": list(profile.get("aliases") or []),
        "data_status": data_status or "unknown",
        "visual_traits": list(profile.get("visual_traits") or []),
        "outfit_traits": list(profile.get("outfit_traits") or []),
        "negative_identity_guard": list(profile.get("negative_identity_guard") or []),
        "lora_hint": profile.get("lora_hint"),
        "safe_to_attach_lora": safe_to_attach,
        "needs_review": bool(profile.get("needs_review", False)),
        "updated_at": now,
    }
    try:
        _ensure_indexes_internal()
        _state.db["character_profiles"].update_one(
            {"canonical_id": canonical_id},
            {"$set": doc, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        return {"ok": True, "canonical_id": canonical_id}
    except Exception as exc:  # noqa: BLE001
        logger.warning("upsert_character_profile failed: %s", exc)
        return {"ok": False, "error": str(exc)}


def get_character_profile(canonical_id: str) -> dict | None:
    if not is_mongo_enabled():
        return None
    canonical_id = (canonical_id or "").strip()
    if not canonical_id:
        return None
    try:
        doc = _state.db["character_profiles"].find_one({"canonical_id": canonical_id})
        if doc is not None and "_id" in doc:
            doc["_id"] = str(doc["_id"])
        return doc
    except Exception as exc:  # noqa: BLE001
        logger.warning("get_character_profile failed: %s", exc)
        return None


# ── generation_jobs ────────────────────────────────────────────────────


def save_generation_job(job_doc: Mapping[str, Any]) -> dict:
    """Insert a new generation_jobs document. Idempotent on ``job_id``."""
    if not is_mongo_enabled():
        return _disabled_response()
    job_id = (job_doc.get("job_id") or "").strip()
    if not job_id:
        return {"ok": False, "error": "missing job_id"}
    now = _utcnow_iso()
    doc = _strip_forbidden(job_doc)
    doc["job_id"] = job_id
    doc["schema_version"] = SCHEMA_VERSION
    doc.setdefault("created_at", now)
    doc.setdefault("updated_at", now)
    doc.setdefault("status", "preflight_only")
    doc.setdefault("provider", "reasoning_image_gen")
    doc.setdefault("output_image_ids", [])
    doc.setdefault("error", None)
    try:
        _ensure_indexes_internal()
        _state.db["generation_jobs"].update_one(
            {"job_id": job_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return {"ok": True, "job_id": job_id}
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_generation_job failed: %s", exc)
        return {"ok": False, "error": str(exc)}


def update_generation_job(job_id: str, patch: Mapping[str, Any]) -> dict:
    if not is_mongo_enabled():
        return _disabled_response()
    job_id = (job_id or "").strip()
    if not job_id:
        return {"ok": False, "error": "missing job_id"}
    update = _strip_forbidden(patch)
    update["updated_at"] = _utcnow_iso()
    try:
        result = _state.db["generation_jobs"].update_one(
            {"job_id": job_id}, {"$set": update}
        )
        return {
            "ok": True,
            "job_id": job_id,
            "matched": getattr(result, "matched_count", 0),
            "modified": getattr(result, "modified_count", 0),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("update_generation_job failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ── image_assets ───────────────────────────────────────────────────────


def save_image_asset(asset_doc: Mapping[str, Any]) -> dict:
    """Insert an image_assets document. Strips any binary/base64 keys.

    Identity-safety: never stores raw image data. ``local_path`` /
    ``public_url`` / ``sha256`` are the canonical references.
    """
    if not is_mongo_enabled():
        return _disabled_response()
    image_id = (asset_doc.get("image_id") or "").strip()
    if not image_id:
        return {"ok": False, "error": "missing image_id"}
    now = _utcnow_iso()
    doc = _strip_forbidden(asset_doc)
    doc["image_id"] = image_id
    doc["schema_version"] = SCHEMA_VERSION
    doc.setdefault("created_at", now)
    doc["updated_at"] = now
    doc.setdefault("role", "output")
    doc.setdefault("scope", "job_output")
    doc.setdefault("needs_review", False)
    try:
        _ensure_indexes_internal()
        _state.db["image_assets"].update_one(
            {"image_id": image_id},
            {"$setOnInsert": doc},
            upsert=True,
        )
        return {"ok": True, "image_id": image_id}
    except Exception as exc:  # noqa: BLE001
        logger.warning("save_image_asset failed: %s", exc)
        return {"ok": False, "error": str(exc)}


# ── Test/reset hook ────────────────────────────────────────────────────


def _reset_for_tests() -> None:
    """Reset module-level state. Intended for tests only."""
    with _LOCK:
        _state.initialized = False
        _state.client = None
        _state.db = None
        _state.disabled_reason = ""
        _state.indexes_ensured = False


__all__ = [
    "SCHEMA_VERSION",
    "is_mongo_enabled",
    "get_mongo_db",
    "ensure_indexes",
    "save_conversation",
    "update_conversation",
    "save_message",
    "save_tool_call",
    "update_tool_call",
    "save_uploaded_file",
    "upsert_character_profile",
    "get_character_profile",
    "save_generation_job",
    "update_generation_job",
    "save_image_asset",
]
