"""Guardrails for MCP tool access."""
from __future__ import annotations

from pathlib import Path
import re

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BLOCKED_PATTERNS = (".env", "id_rsa", "private_key", "secrets", "credentials", "token")


def validate_workspace_path(path: str) -> Path:
    full = (PROJECT_ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if PROJECT_ROOT not in full.parents and full != PROJECT_ROOT:
        raise PermissionError("Path outside workspace is not allowed")
    lowered = str(full).lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in lowered:
            raise PermissionError("Sensitive file access blocked")
    return full


def validate_select_only(query: str) -> None:
    normalized = re.sub(r"\s+", " ", (query or "").strip()).lower()
    if not normalized.startswith("select"):
        raise PermissionError("Only SELECT queries are allowed")
    if ";" in normalized[:-1]:
        raise PermissionError("Multiple SQL statements are blocked")


def clamp_max_rows(limit: int, max_rows: int = 500) -> int:
    return max(1, min(int(limit), max_rows))
