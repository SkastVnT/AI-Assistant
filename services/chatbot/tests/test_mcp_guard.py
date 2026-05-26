import importlib.util
from pathlib import Path

import pytest

module_path = Path(__file__).resolve().parents[2] / "mcp-server" / "tools" / "guard.py"
spec = importlib.util.spec_from_file_location("mcp_guard", module_path)
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def test_validate_workspace_path_blocks_sensitive():
    with pytest.raises(PermissionError):
        guard.validate_workspace_path("app/config/.env")


def test_validate_workspace_path_blocks_generated_dirs():
    with pytest.raises(PermissionError):
        guard.validate_workspace_path("generated/report.txt")


def test_validate_workspace_path_blocks_vendor_dirs():
    with pytest.raises(PermissionError):
        guard.validate_workspace_path("vendor/package/index.js")


def test_validate_workspace_path_blocks_symlink_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(guard, "PROJECT_ROOT", tmp_path)
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("secret", encoding="utf-8")
    link = tmp_path / "link.txt"
    try:
        link.symlink_to(outside)
    except OSError as exc:
        pytest.skip(f"symlink not available: {exc}")

    with pytest.raises(PermissionError):
        guard.validate_workspace_path("link.txt")


def test_validate_text_file_blocks_large_file(tmp_path, monkeypatch):
    monkeypatch.setattr(guard, "PROJECT_ROOT", tmp_path)
    target = tmp_path / "docs" / "large.md"
    target.parent.mkdir()
    target.write_text("x" * 32, encoding="utf-8")

    with pytest.raises(PermissionError):
        guard.validate_text_file("docs/large.md", max_bytes=16)


def test_validate_text_file_blocks_unknown_extension(tmp_path, monkeypatch):
    monkeypatch.setattr(guard, "PROJECT_ROOT", tmp_path)
    target = tmp_path / "data.bin"
    target.write_bytes(b"small")

    with pytest.raises(PermissionError):
        guard.validate_text_file("data.bin")


def test_validate_select_only_blocks_delete():
    with pytest.raises(PermissionError):
        guard.validate_select_only("DELETE FROM users")


def test_validate_select_only_accepts_select():
    guard.validate_select_only("SELECT * FROM users LIMIT 5")
