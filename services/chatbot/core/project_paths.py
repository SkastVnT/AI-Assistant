"""Canonical repository paths for chatbot integrations."""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "app"

COMFYUI_DIR = Path(os.getenv("COMFYUI_DIR") or REPO_ROOT / "ComfyUI").resolve()
IMAGE_PIPELINE_DIR = Path(
    os.getenv("IMAGE_PIPELINE_DIR") or APP_ROOT / "image_pipeline"
).resolve()
RAG_DIR = Path(os.getenv("RAG_DIR") or APP_ROOT / "rag").resolve()
CHARACTER_SELECT_DIR = Path(
    os.getenv("CHARACTER_SELECT_DIR") or APP_ROOT / "character_select_stand_alone_app-main"
).resolve()
STORAGE_DIR = Path(os.getenv("STORAGE_DIR") or APP_ROOT / "storage").resolve()
CONFIGS_VPS_DIR = Path(os.getenv("CONFIGS_VPS_DIR") or APP_ROOT / "configs_vps").resolve()
SCRIPTS_DIR = Path(os.getenv("SCRIPTS_DIR") or APP_ROOT / "scripts").resolve()
DOCS_DIR = Path(os.getenv("DOCS_DIR") or APP_ROOT / "docs").resolve()
ELECTRON_DIR = Path(os.getenv("ELECTRON_DIR") or APP_ROOT / "electron").resolve()


def ensure_app_root_on_path() -> None:
    """Allow imports such as `image_pipeline.*` after moving packages under app/."""
    app_root = str(APP_ROOT)
    if app_root not in sys.path:
        sys.path.insert(1 if sys.path else 0, app_root)


def resolve_character_select_path(value: str | os.PathLike[str] | None = None) -> Path:
    """Resolve legacy and new Character Select filesystem paths."""
    raw = value or os.getenv("CHARACTER_SELECT_PATH") or os.getenv("CHARACTER_SELECT_DIR")
    if not raw:
        return CHARACTER_SELECT_DIR

    path = Path(raw).expanduser()
    if path.is_absolute():
        return path.resolve()

    if path.parts and path.parts[0] == "app":
        return (REPO_ROOT / path).resolve()

    if path.parts and path.parts[0] == "character_select_stand_alone_app-main":
        legacy_path = (REPO_ROOT / path).resolve()
        if legacy_path.exists():
            return legacy_path
        return CHARACTER_SELECT_DIR

    return (REPO_ROOT / path).resolve()
