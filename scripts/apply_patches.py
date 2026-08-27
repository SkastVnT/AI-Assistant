#!/usr/bin/env python3
"""Apply local patches to vendored submodules. Safe to re-run."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHES = ROOT / "patches"
TARGET = ROOT / "ComfyUI"


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(TARGET), *args],
        capture_output=True,
        text=True,
    )


def main() -> int:
    if not (TARGET / "main.py").exists():
        print(f"ComfyUI not checked out at {TARGET}", file=sys.stderr)
        print("Run: git submodule update --init ComfyUI", file=sys.stderr)
        return 1

    patches = sorted(PATCHES.glob("*.patch"))
    if not patches:
        print("No patches found.")
        return 0

    failed = 0
    for patch in patches:
        rel = patch.relative_to(ROOT)
        # Already applied? --reverse --check succeeds when the change is present.
        if _git("apply", "--reverse", "--check", str(patch)).returncode == 0:
            print(f"  skip     {rel}  (already applied)")
            continue
        result = _git("apply", str(patch))
        if result.returncode == 0:
            print(f"  applied  {rel}")
        else:
            print(f"  FAILED   {rel}")
            print(f"           {result.stderr.strip()}")
            failed += 1

    if failed:
        print(f"\n{failed} patch(es) failed - see patches/README.md", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
