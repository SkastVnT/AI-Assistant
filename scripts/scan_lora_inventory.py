"""Scan LoRA inventory and write a JSON manifest.

Usage:
    python scripts/scan_lora_inventory.py
        -> writes storage/lora_inventory.json

Cross-references entries against configs/lora_registry.yaml and flags
LoRAs that are present on disk but not yet registered.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LORA_DIR = ROOT / "LORA"
COMFY_LORA = ROOT / "ComfyUI" / "models" / "loras"
REGISTRY = ROOT / "configs" / "lora_registry.yaml"
OUT = ROOT / "storage" / "lora_inventory.json"

EXCLUDE_DIR_PARTS = {"venv-core", "venv-image", "node_modules", ".git"}


def is_safetensor(p: Path) -> bool:
    return p.is_file() and p.suffix.lower() == ".safetensors"


def walk(root: Path):
    if not root.exists():
        return
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        # prune
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR_PARTS]
        for fn in filenames:
            p = Path(dirpath) / fn
            if is_safetensor(p):
                yield p


def load_registered_names() -> set[str]:
    if not REGISTRY.exists():
        return set()
    try:
        import yaml  # type: ignore
    except ImportError:
        print("[warn] PyYAML not installed; skipping registry cross-reference", file=sys.stderr)
        return set()
    data = yaml.safe_load(REGISTRY.read_text(encoding="utf-8")) or {}
    names: set[str] = set()
    for category, entries in data.items():
        if not isinstance(entries, list):
            continue
        for e in entries:
            if isinstance(e, dict) and e.get("name"):
                names.add(e["name"])
    return names


def main() -> int:
    registered = load_registered_names()
    items: list[dict] = []
    seen_names: set[str] = set()

    for src_label, root in (("lora_dir", LORA_DIR), ("comfyui", COMFY_LORA)):
        for p in walk(root):
            rel = str(p.relative_to(ROOT)).replace("\\", "/")
            name = p.name
            items.append({
                "name": name,
                "rel_path": rel,
                "size_mb": round(p.stat().st_size / (1024 * 1024), 1),
                "location": src_label,
                "registered": name in registered,
            })
            seen_names.add(name)

    items.sort(key=lambda x: (x["location"], x["rel_path"].lower()))

    unregistered = sorted({i["name"] for i in items if not i["registered"]})
    missing_files = sorted(registered - seen_names)

    manifest = {
        "scanned_root": str(ROOT),
        "total_count": len(items),
        "total_size_mb": round(sum(i["size_mb"] for i in items), 1),
        "registered_count": sum(1 for i in items if i["registered"]),
        "unregistered_count": len(unregistered),
        "unregistered_names": unregistered,
        "registry_entries_missing_on_disk": missing_files,
        "items": items,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"[scan_lora_inventory] wrote {OUT}")
    print(f"  total: {manifest['total_count']} files, {manifest['total_size_mb']} MB")
    print(f"  registered: {manifest['registered_count']}")
    print(f"  unregistered: {manifest['unregistered_count']}")
    print(f"  registry-missing-on-disk: {len(missing_files)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
