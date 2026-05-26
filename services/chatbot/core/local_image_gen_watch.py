"""
Local image-gen watcher — reads the ComfyUI output directory and reports
files newer than a given epoch timestamp.

Used by the Local Image Gen modal to surface SAA-generated images back into
the chatbot conversation. Pure stdlib; no ComfyUI HTTP coupling.
"""

from __future__ import annotations

import logging
import mimetypes
import os
from collections.abc import Iterable
from pathlib import Path

from core.config import COMFYUI_OUTPUT_DIR

logger = logging.getLogger(__name__)

_ALLOWED_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".gif"}


def _safe_root() -> Path | None:
    try:
        root = Path(COMFYUI_OUTPUT_DIR).resolve()
        if not root.is_dir():
            return None
        return root
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "[LOCAL-IMG-GEN] Bad output dir: %s (%s)", COMFYUI_OUTPUT_DIR, exc
        )
        return None


def list_recent(since: float = 0.0, limit: int = 12) -> dict:
    """Return image files in the ComfyUI output dir newer than ``since`` (epoch seconds).

    Shape::
        {
            "ok": bool,
            "root": str,
            "now": float,
            "files": [
                {"name": str, "size": int, "mtime": float, "url": str}
            ],
            "error": str | None,
        }
    """
    import time

    now = time.time()
    root = _safe_root()
    if root is None:
        return {
            "ok": False,
            "root": str(COMFYUI_OUTPUT_DIR),
            "now": now,
            "files": [],
            "error": f"output_dir_not_found: {COMFYUI_OUTPUT_DIR}",
        }

    files: list[dict] = []
    try:
        with os.scandir(root) as it:
            entries: Iterable[os.DirEntry] = list(it)
        for entry in entries:
            if not entry.is_file():
                continue
            ext = Path(entry.name).suffix.lower()
            if ext not in _ALLOWED_EXTS:
                continue
            try:
                stat = entry.stat()
            except OSError:
                continue
            if stat.st_mtime <= since:
                continue
            files.append(
                {
                    "name": entry.name,
                    "size": stat.st_size,
                    "mtime": stat.st_mtime,
                    "url": f"/api/local-image-gen/file/{entry.name}",
                }
            )
    except OSError as exc:
        return {
            "ok": False,
            "root": str(root),
            "now": now,
            "files": [],
            "error": f"scan_failed: {exc}",
        }

    files.sort(key=lambda f: f["mtime"], reverse=True)
    return {
        "ok": True,
        "root": str(root),
        "now": now,
        "files": files[:limit],
        "error": None,
    }


def resolve_file(name: str) -> tuple[Path | None, str]:
    """Resolve a filename to an absolute path inside the output dir.

    Returns ``(path, mime)`` or ``(None, '')`` on failure / traversal attempt.
    """
    root = _safe_root()
    if root is None:
        return None, ""
    # Reject any path-like input
    if not name or "/" in name or "\\" in name or name.startswith("."):
        return None, ""
    candidate = (root / name).resolve()
    try:
        candidate.relative_to(root)
    except ValueError:
        return None, ""
    if not candidate.is_file():
        return None, ""
    if candidate.suffix.lower() not in _ALLOWED_EXTS:
        return None, ""
    mime, _ = mimetypes.guess_type(str(candidate))
    return candidate, mime or "application/octet-stream"
