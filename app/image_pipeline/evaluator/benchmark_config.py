"""Shared loading helpers for LOCAL anime benchmark policy and suites."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from image_pipeline.paths import CONFIGS_DIR

POLICY_PATH = CONFIGS_DIR / "anime_benchmark_policy.yaml"
SFW_SUITE_PATH = CONFIGS_DIR / "anime_benchmark_suite.yaml"
ADULT_SUITE_PATH = CONFIGS_DIR / "anime_benchmark_suite_adult_only.yaml"


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def load_benchmark_config(path: str | Path) -> dict[str, Any]:
    """Merge shared qualification policy with one concrete suite."""

    policy = _read_yaml(POLICY_PATH)
    suite = _read_yaml(Path(path))
    return {**policy, **suite}


def resolve_suite_path(suite: str, profile: str) -> Path:
    selected = (suite or "auto").strip().lower()
    if selected == "auto":
        selected = "adult_only" if profile in {"pc_12gb", "vps_96gb"} else "sfw"
    if selected == "sfw":
        return SFW_SUITE_PATH
    if selected == "adult_only":
        return ADULT_SUITE_PATH
    raise ValueError(f"Unknown benchmark suite: {suite}")


__all__ = [
    "ADULT_SUITE_PATH",
    "POLICY_PATH",
    "SFW_SUITE_PATH",
    "load_benchmark_config",
    "resolve_suite_path",
]
