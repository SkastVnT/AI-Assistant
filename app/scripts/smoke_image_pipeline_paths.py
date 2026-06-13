"""
smoke_image_pipeline_paths.py — Sanity-check canonical image pipeline paths.

Exits 0 (SMOKE OK) when all required directories and config files exist.
Exits 1 (SMOKE FAILED) with a list of missing/bad entries.

Usage:
    python app/scripts/smoke_image_pipeline_paths.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# Allow `from image_pipeline.paths import ...` without installing the package.
_APP_ROOT = Path(__file__).resolve().parents[1]
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))

from image_pipeline.paths import (  # noqa: E402
    APP_ROOT,
    COMFYUI_DIR,
    CONFIGS_DIR,
    STORAGE_DIR,
)

IMAGE_PIPELINE_DIR = APP_ROOT / "image_pipeline"

# ── Required directories ───────────────────────────────────────────────────

REQUIRED_DIRS: dict[str, Path] = {
    "image_pipeline_dir": IMAGE_PIPELINE_DIR,
    "configs_dir": CONFIGS_DIR,
    "storage_dir": STORAGE_DIR,
}

OPTIONAL_DIRS: dict[str, Path] = {
    "comfyui_dir": COMFYUI_DIR,
}

# ── Required config files ──────────────────────────────────────────────────

REQUIRED_CONFIGS: list[Path] = [
    CONFIGS_DIR / "anime_pipeline.yaml",
    CONFIGS_DIR / "anime_pipeline_assets.yaml",
    CONFIGS_DIR / "anime_benchmark_suite.yaml",
    CONFIGS_DIR / "models.yaml",
    CONFIGS_DIR / "routing.yaml",
]


# ── Checks ─────────────────────────────────────────────────────────────────

def _check_dir(name: str, path: Path, required: bool = True) -> list[str]:
    errors: list[str] = []
    if not path.exists():
        if required:
            errors.append(f"MISSING dir  [{name}] → {path}")
    elif not path.is_dir():
        errors.append(f"NOT A DIR    [{name}] → {path}")
    return errors


def main() -> int:
    errors: list[str] = []

    for name, path in REQUIRED_DIRS.items():
        errors.extend(_check_dir(name, path, required=True))

    for name, path in OPTIONAL_DIRS.items():
        if path.exists():
            errors.extend(_check_dir(name, path, required=False))

    for cfg in REQUIRED_CONFIGS:
        if not cfg.exists():
            errors.append(f"MISSING cfg  → {cfg}")
        elif not cfg.is_file():
            errors.append(f"NOT A FILE   → {cfg}")

    if errors:
        print("SMOKE FAILED")
        for msg in errors:
            print(f"  - {msg}")
        return 1

    print("SMOKE OK")
    print(f"  image_pipeline : {IMAGE_PIPELINE_DIR}")
    print(f"  configs        : {CONFIGS_DIR}")
    print(f"  storage        : {STORAGE_DIR}")
    if COMFYUI_DIR.exists():
        print(f"  comfyui        : {COMFYUI_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
