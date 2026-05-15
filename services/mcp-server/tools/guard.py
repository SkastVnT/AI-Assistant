"""Guardrails for MCP tool access."""
from __future__ import annotations

import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[3]
BLOCKED_PATTERNS = (".env", "id_rsa", "private_key", "secrets", "credentials", "token")
BLOCKED_DIR_NAMES = {
    ".git",
    ".hg",
    ".svn",
    ".venv",
    "__pycache__",
    "node_modules",
    "generated",
    "payload",
    "payload-lite",
    "private",
    "vendor",
    "venv",
    "venv-core",
    "venv-image",
}
BLOCKED_DIR_PATTERNS = {
    "comfyui",
    "lora",
}
SAFE_TEXT_EXTENSIONS = {
    ".bat",
    ".cfg",
    ".css",
    ".csv",
    ".html",
    ".ini",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".ps1",
    ".py",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".xml",
    ".yaml",
    ".yml",
}
MAX_READ_BYTES = 512 * 1024


def is_blocked_workspace_path(path: Path) -> bool:
    resolved = path.resolve()
    lowered = str(resolved).lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in lowered:
            return True
    for part in resolved.parts:
        lower = part.lower()
        if lower in BLOCKED_DIR_NAMES:
            return True
        if any(pattern in lower for pattern in BLOCKED_DIR_PATTERNS):
            return True
    return False


def validate_workspace_path(path: str) -> Path:
    full = (PROJECT_ROOT / path).resolve() if not Path(path).is_absolute() else Path(path).resolve()
    if PROJECT_ROOT not in full.parents and full != PROJECT_ROOT:
        raise PermissionError("Path outside workspace is not allowed")
    if is_blocked_workspace_path(full):
        raise PermissionError("Sensitive or generated path access blocked")
    return full


def validate_text_file(path: str, *, max_bytes: int = MAX_READ_BYTES) -> Path:
    full = validate_workspace_path(path)
    if not full.is_file():
        raise PermissionError("Path is not a file")
    if full.suffix.lower() not in SAFE_TEXT_EXTENSIONS:
        raise PermissionError("Only known text files can be read")
    if full.stat().st_size > max_bytes:
        raise PermissionError("File is too large to read through MCP")
    return full


def workspace_relative(path: Path) -> str:
    return str(path.resolve().relative_to(PROJECT_ROOT)).replace("\\", "/")


def validate_select_only(query: str) -> None:
    normalized = re.sub(r"\s+", " ", (query or "").strip()).lower()
    if not normalized.startswith("select"):
        raise PermissionError("Only SELECT queries are allowed")
    if ";" in normalized[:-1]:
        raise PermissionError("Multiple SQL statements are blocked")


def clamp_max_rows(limit: int, max_rows: int = 500) -> int:
    return max(1, min(int(limit), max_rows))
