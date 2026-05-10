"""Shared environment loader for all services.

Loads environment variables from app/config using the same convention as the
sample settings.py:
- app/config/.env_<env> (where env comes from ENV "env", default: dev)
- fallback to app/config/.env
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv


def _find_project_root(start: Path) -> Path:
    """Walk up from the current file to locate the repository root."""
    for parent in [start.parent, *start.parents]:
        if (parent / "services").exists() and (parent / "app" / "config").exists():
            return parent
    # Fallback to current working directory if root cannot be inferred.
    return Path.cwd()


def resolve_shared_env_file(source_file: Optional[str] = None) -> Optional[Path]:
    """Resolve the shared env file path based on current environment name."""
    start = Path(source_file).resolve() if source_file else Path.cwd().resolve()
    root = _find_project_root(start)

    env_name = os.getenv("env", "dev")
    env_dir = root / "app" / "config"

    preferred = env_dir / f".env_{env_name}"
    if preferred.exists():
        return preferred

    fallback = env_dir / ".env"
    if fallback.exists():
        return fallback

    return None


def load_shared_env(source_file: Optional[str] = None) -> Optional[Path]:
    """Load shared env file into process environment and return the loaded path."""
    env_file = resolve_shared_env_file(source_file)
    if env_file is not None:
        load_dotenv(env_file)
    return env_file

