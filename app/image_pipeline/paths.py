"""Canonical paths for the image pipeline package."""

from __future__ import annotations

import os
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = APP_ROOT.parent

COMFYUI_DIR = Path(os.getenv("COMFYUI_DIR") or REPO_ROOT / "ComfyUI").resolve()
CHARACTER_SELECT_DIR = Path(
    os.getenv("CHARACTER_SELECT_DIR")
    or APP_ROOT / "character_select_stand_alone_app-main"
).resolve()
CONFIGS_DIR = Path(os.getenv("CONFIGS_VPS_DIR") or APP_ROOT / "configs_vps").resolve()
STORAGE_DIR = Path(os.getenv("STORAGE_DIR") or APP_ROOT / "storage").resolve()
LORA_DIR = Path(os.getenv("LORA_DIR") or REPO_ROOT / "LORA").resolve()
