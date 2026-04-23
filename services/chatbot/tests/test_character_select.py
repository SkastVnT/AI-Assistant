"""
Tests for Character Select SAA sidecar integration — adapter + Flask route.

All tests use mocks. No real network/filesystem checks against the sidecar.
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def _enable(monkeypatch):
    monkeypatch.setattr("core.character_select_adapter.CHARACTER_SELECT_ENABLED", True)
    monkeypatch.setattr("core.character_select_adapter.CHARACTER_SELECT_URL", "http://fake-saa:51028")
    monkeypatch.setattr("core.character_select_adapter.CHARACTER_SELECT_PORT", 51028)
    monkeypatch.setattr("core.character_select_adapter.CHARACTER_SELECT_TIMEOUT", 1)


@pytest.fixture
def _disable(monkeypatch):
    monkeypatch.setattr("core.character_select_adapter.CHARACTER_SELECT_ENABLED", False)


# ---------------------------------------------------------------------------
# Adapter tests
# ---------------------------------------------------------------------------

class TestAdapter:
    def test_disabled_returns_error(self, _disable):
        from core.character_select_adapter import get_status, is_enabled
        assert is_enabled() is False
        result = get_status()
        assert result["enabled"] is False
        assert result["reachable"] is False
        assert "CHARACTER_SELECT_ENABLED" in result["error"]

    def test_enabled_port_closed(self, _enable, monkeypatch):
        monkeypatch.setattr("core.character_select_adapter._port_is_open", lambda *a, **kw: False)
        from core.character_select_adapter import get_status
        result = get_status()
        assert result["enabled"] is True
        assert result["reachable"] is False
        assert result["error"] is not None
        assert "not reachable" in result["error"]

    def test_enabled_port_open_http_ok(self, _enable, monkeypatch):
        monkeypatch.setattr("core.character_select_adapter._port_is_open", lambda *a, **kw: True)
        mock_resp = MagicMock(status_code=200)
        monkeypatch.setattr(
            "core.character_select_adapter.requests.get",
            lambda *a, **kw: mock_resp,
        )
        from core.character_select_adapter import get_status
        result = get_status()
        assert result["enabled"] is True
        assert result["reachable"] is True
        assert result["running"] is True
        assert result["http_status"] == 200
        assert result["error"] is None

    def test_enabled_port_open_http_fails(self, _enable, monkeypatch):
        """HTTP probe failure is non-fatal — WebSocket-only listener counts as reachable."""
        import requests as _requests
        monkeypatch.setattr("core.character_select_adapter._port_is_open", lambda *a, **kw: True)

        def _raise(*a, **kw):
            raise _requests.ConnectionError("ws-only")
        monkeypatch.setattr("core.character_select_adapter.requests.get", _raise)

        from core.character_select_adapter import get_status
        result = get_status()
        assert result["reachable"] is True
        assert result["http_status"] is None


# ---------------------------------------------------------------------------
# Flask route tests
# ---------------------------------------------------------------------------

class TestFlaskRoute:
    @pytest.fixture
    def client(self):
        from flask import Flask
        from routes.character_select import character_select_bp
        app = Flask(__name__)
        app.register_blueprint(character_select_bp)
        return app.test_client()

    def test_status_route_disabled(self, client, _disable):
        resp = client.get("/api/character-select/status")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["enabled"] is False
        assert "installed" in body

    def test_url_route(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.config.CHARACTER_SELECT_URL",
            "http://localhost:51028",
        )
        resp = client.get("/api/character-select/url")
        assert resp.status_code == 200
        body = resp.get_json()
        assert "url" in body
        assert "enabled" in body
