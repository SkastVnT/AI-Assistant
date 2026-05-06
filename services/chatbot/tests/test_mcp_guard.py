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


def test_validate_select_only_blocks_delete():
    with pytest.raises(PermissionError):
        guard.validate_select_only("DELETE FROM users")


def test_validate_select_only_accepts_select():
    guard.validate_select_only("SELECT * FROM users LIMIT 5")
