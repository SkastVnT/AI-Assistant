"""Root conftest.py — blocks pytest from wandering into directories that
belong to other service stacks or require unavailable dependencies.
"""

from __future__ import annotations

import os
from pathlib import Path

# Directories (relative to repo root) that pytest must never enter.
_ROOT = Path(__file__).parent

_EXCLUDED_DIRS = [
    # RAG subsystem — requires pgvector / redis not in venv-core
    _ROOT / "app" / "rag",
    # Scripts — not a test suite, causes import-file-mismatch
    _ROOT / "app" / "scripts",
    _ROOT / "services" / "chatbot" / "scripts",
    # Archived / copied service tree (path contains a space)
    _ROOT / "services" / "chatbot" / "private copy",
    # Electron payload bundles
    _ROOT / "app" / "electron",
    # Image-pipeline / ComfyUI stacks — different venv
    _ROOT / "app" / "image_pipeline",
    _ROOT / "app" / "ComfyUI",
    _ROOT / "app" / "character_select_stand_alone_app-main",
]


def pytest_ignore_collect(collection_path, config):
    """Return True to prevent collection of files/dirs under _EXCLUDED_DIRS."""
    try:
        p = Path(collection_path).resolve()
    except Exception:
        return False
    for exc in _EXCLUDED_DIRS:
        try:
            p.relative_to(exc.resolve())
            return True
        except ValueError:
            continue
    return False
