"""Validate configs/lora_registry.yaml against on-disk LoRA files.

Walks every entry in the registry and checks whether the referenced
``.safetensors`` file actually exists in the location declared by the
entry's ``location`` field:

    location: comfyui  -> ComfyUI/models/loras/<name>
                          (also ComfyUI/models/loras/characters/<name>)
    location: lora_dir -> LORA/<name>

Exit code 0 when every entry resolves, 1 when one or more are missing.
Run from the repo root:

    python scripts/validate_lora_registry.py
    python scripts/validate_lora_registry.py --category character
    python scripts/validate_lora_registry.py --verbose
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable

try:
    import yaml
except ImportError:
    print("error: pyyaml not installed (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRY_PATH = REPO_ROOT / "configs" / "lora_registry.yaml"
COMFYUI_LORAS = REPO_ROOT / "ComfyUI" / "models" / "loras"
COMFYUI_LORAS_CHAR = COMFYUI_LORAS / "characters"
LORA_DIR = REPO_ROOT / "LORA"


def _candidate_paths(name: str, location: str) -> list[Path]:
    if location == "comfyui":
        return [COMFYUI_LORAS / name, COMFYUI_LORAS_CHAR / name]
    if location == "lora_dir":
        return [LORA_DIR / name]
    # Unknown location — try everywhere as best-effort.
    return [COMFYUI_LORAS / name, COMFYUI_LORAS_CHAR / name, LORA_DIR / name]


def _iter_entries(registry: dict, categories: Iterable[str] | None):
    for category, entries in registry.items():
        if not isinstance(entries, list):
            continue
        if categories and category not in categories:
            continue
        for entry in entries:
            if isinstance(entry, dict) and "name" in entry:
                yield category, entry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--category",
        action="append",
        default=None,
        help="restrict to one or more categories (repeatable)",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="print every entry, not just missing ones",
    )
    args = parser.parse_args()

    if not REGISTRY_PATH.exists():
        print(f"error: registry not found: {REGISTRY_PATH}", file=sys.stderr)
        return 2

    with REGISTRY_PATH.open("r", encoding="utf-8") as f:
        registry = yaml.safe_load(f) or {}

    total = 0
    missing: list[tuple[str, str, list[Path]]] = []
    unknown_location: list[tuple[str, str]] = []

    for category, entry in _iter_entries(registry, args.category):
        total += 1
        name = entry["name"]
        location = entry.get("location", "")
        if location not in ("comfyui", "lora_dir"):
            unknown_location.append((category, name))
        paths = _candidate_paths(name, location)
        found = next((p for p in paths if p.exists()), None)
        if found is None:
            missing.append((category, name, paths))
        elif args.verbose:
            print(f"OK   {category:<14} {name}  ->  {found.relative_to(REPO_ROOT)}")

    print()
    print(f"checked: {total} entries")
    print(f"missing: {len(missing)}")
    if unknown_location:
        print(f"unknown location field: {len(unknown_location)}")
        for cat, name in unknown_location:
            print(f"  ?  {cat:<14} {name}")

    if missing:
        print("\nMISSING:")
        for cat, name, paths in missing:
            tried = ", ".join(str(p.relative_to(REPO_ROOT)) for p in paths)
            print(f"  -  {cat:<14} {name}  (tried: {tried})")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
