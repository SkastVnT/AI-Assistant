from __future__ import annotations

import importlib
import importlib.util
import sys
import types
from pathlib import Path
from unittest.mock import patch

import pytest


def test_secret_key_testing_fallback(monkeypatch):
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.setenv("TESTING", "true")

    from core.secret_key import resolve_flask_secret_key

    assert resolve_flask_secret_key() == "test-only-flask-secret-key"


def test_secret_key_non_dev_requires_env(monkeypatch):
    monkeypatch.delenv("FLASK_SECRET_KEY", raising=False)
    monkeypatch.delenv("TESTING", raising=False)
    monkeypatch.setenv("env", "prod")
    monkeypatch.setenv("FLASK_ENV", "production")

    from core.secret_key import resolve_flask_secret_key

    with pytest.raises(RuntimeError):
        resolve_flask_secret_key()


def test_http_logging_redacts_sensitive_fields():
    from core.http_logging import REDACTED, _body_summary_for_log, redact_for_log

    payload = {
        "Authorization": "Bearer secret",
        "nested": {
            "api_key": "abc",
            "safe": "kept",
            "items": [{"password": "pw"}],
        },
    }

    redacted = redact_for_log(payload)
    assert redacted["Authorization"] == REDACTED
    assert redacted["nested"]["api_key"] == REDACTED
    assert redacted["nested"]["items"][0]["password"] == REDACTED
    assert redacted["nested"]["safe"] == "kept"

    summary = _body_summary_for_log(
        "/chat/stream",
        {"message": "do not log me", "model": "grok", "tools": ["google-search"]},
    )
    assert "do not log me" not in str(summary)
    assert summary["message_length"] == len("do not log me")
    assert summary["tools_count"] == 1


def test_mongodb_tls_invalid_default_is_false(monkeypatch):
    monkeypatch.delenv("MONGODB_TLS_ALLOW_INVALID_CERTIFICATES", raising=False)
    monkeypatch.setenv("TESTING", "true")

    import app.config as app_config

    app_config = importlib.reload(app_config)
    assert app_config.BaseConfig.MONGODB_TLS_ALLOW_INVALID_CERTIFICATES is False

    module_path = Path(__file__).resolve().parents[1] / "config" / "mongodb_config.py"
    spec = importlib.util.spec_from_file_location("mongodb_config_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    assert module.MONGODB_TLS_ALLOW_INVALID_CERTIFICATES is False


def _load_mcp_server_with_stub(monkeypatch):
    class DummyMCP:
        def __init__(self, *_args, **_kwargs):
            pass

        def tool(self):
            return lambda fn: fn

        def resource(self, *_args, **_kwargs):
            return lambda fn: fn

        def prompt(self):
            return lambda fn: fn

        def run(self):
            pass

    mcp_mod = types.ModuleType("mcp")
    server_pkg = types.ModuleType("mcp.server")
    fastmcp_mod = types.ModuleType("mcp.server.fastmcp")
    fastmcp_mod.FastMCP = DummyMCP
    monkeypatch.setitem(sys.modules, "mcp", mcp_mod)
    monkeypatch.setitem(sys.modules, "mcp.server", server_pkg)
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fastmcp_mod)

    module_path = Path(__file__).resolve().parents[2] / "mcp-server" / "server.py"
    server_dir = str(module_path.parent)
    if server_dir not in sys.path:
        sys.path.insert(0, server_dir)
    spec = importlib.util.spec_from_file_location("mcp_server_under_test", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_mcp_search_files_returns_relative_paths_only(monkeypatch):
    server = _load_mcp_server_with_stub(monkeypatch)

    result = server.search_files("AGENTS", "md", 5)

    assert result["results"]
    for item in result["results"]:
        assert "full_path" not in item
        assert not Path(item["path"]).is_absolute()


def test_mcp_read_blocks_sensitive_file(monkeypatch):
    server = _load_mcp_server_with_stub(monkeypatch)

    result = server.read_file_content("app/config/.env", max_lines=20)

    assert "error" in result
    assert "blocked" in result["error"].lower() or "sensitive" in result["error"].lower()


def test_mcp_fetch_url_blocks_loopback(monkeypatch):
    monkeypatch.setenv("TESTING", "true")
    # Allow 127.0.0.1 through the host allowlist so the SSRF check can fire.
    monkeypatch.setenv("MCP_FETCH_ALLOWED_HOSTS", "127.0.0.1")
    import chatbot_main

    response = chatbot_main.app.test_client().post(
        "/api/mcp/fetch-url",
        json={"url": "http://127.0.0.1/admin"},
    )

    assert response.status_code == 400
    assert "unsafe" in response.get_json()["error"].lower()


def test_url_safety_blocks_private_ip():
    """RFC1918 private ranges must be blocked without DNS resolution."""
    import sys
    from pathlib import Path as _Path

    _chatbot_root = _Path(__file__).resolve().parents[1]
    if str(_chatbot_root) not in sys.path:
        sys.path.insert(0, str(_chatbot_root))

    from core.url_safety import UnsafeUrlError, assert_safe_external_url

    for url in (
        "http://192.168.1.1/admin",
        "http://10.0.0.1/secret",
        "http://172.16.0.1/internal",
    ):
        with pytest.raises(UnsafeUrlError):
            assert_safe_external_url(url, resolve=False)


def test_url_safety_blocks_link_local_metadata():
    """169.254.169.254 (cloud IMDS) must be blocked without DNS resolution."""
    import sys
    from pathlib import Path as _Path

    _chatbot_root = _Path(__file__).resolve().parents[1]
    if str(_chatbot_root) not in sys.path:
        sys.path.insert(0, str(_chatbot_root))

    from core.url_safety import UnsafeUrlError, assert_safe_external_url

    with pytest.raises(UnsafeUrlError):
        assert_safe_external_url("http://169.254.169.254/latest/meta-data/", resolve=False)


def test_url_safety_blocks_non_http_schemes():
    """file://, ftp://, gopher:// etc. must be blocked."""
    import sys
    from pathlib import Path as _Path

    _chatbot_root = _Path(__file__).resolve().parents[1]
    if str(_chatbot_root) not in sys.path:
        sys.path.insert(0, str(_chatbot_root))

    from core.url_safety import UnsafeUrlError, assert_safe_external_url

    for url in ("file:///etc/passwd", "ftp://example.com/data", "gopher://evil.com"):
        with pytest.raises(UnsafeUrlError, match="scheme"):
            assert_safe_external_url(url, resolve=False)


def test_mcp_fetch_url_blocks_unsafe_redirect(monkeypatch):
    monkeypatch.setenv("TESTING", "true")
    # Allow example.com through the host allowlist so the redirect SSRF check
    # fires when the response redirects to a loopback address.
    monkeypatch.setenv("MCP_FETCH_ALLOWED_HOSTS", "example.com")

    import core.url_safety as url_safety

    def fake_getaddrinfo(host, *_args, **_kwargs):
        if host == "example.com":
            return [(None, None, None, "", ("93.184.216.34", 0))]
        raise OSError("unexpected host")

    monkeypatch.setattr(url_safety.socket, "getaddrinfo", fake_getaddrinfo)

    import chatbot_main

    class FakeResponse:
        status_code = 302
        headers = {"Location": "http://127.0.0.1/admin"}
        is_redirect = True
        content_type = "text/html"
        text = ""
        content = b""

        def raise_for_status(self):
            return None

    class FakeSession:
        def get(self, *_args, **_kwargs):
            return FakeResponse()

    with patch.object(chatbot_main.requests, "Session", return_value=FakeSession()):
        response = chatbot_main.app.test_client().post(
            "/api/mcp/fetch-url",
            json={"url": "https://example.com/start"},
        )

    assert response.status_code == 400
    assert "unsafe" in response.get_json()["error"].lower()
