"""
Tests for last30days integration — tool wrapper + Flask route.

All tests use mocks. No real subprocess or network calls.
"""

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Ensure chatbot root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def _enable_last30days(monkeypatch):
    """Enable last30days feature flag for the duration of a test."""
    monkeypatch.setattr("core.last30days_tool.LAST30DAYS_ENABLED", True)
    monkeypatch.setattr(
        "core.last30days_tool._resolve_script_path",
        lambda: "/fake/last30days.py",
    )
    monkeypatch.setattr("core.last30days_tool.LAST30DAYS_PYTHON_PATH", "python3.12")


@pytest.fixture
def successful_subprocess(monkeypatch):
    """Mock subprocess.run to return a successful JSON result."""
    fake_output = json.dumps(
        {
            "summary": "AI trends are rising.",
            "insights": [{"text": "LLMs dominate"}, {"text": "Agents are growing"}],
            "sources": [{"name": "Reddit", "count": 42}],
            "sentiment": "Positive",
            "trends": ["multi-modal", "agentic"],
        }
    )
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = fake_output
    mock_result.stderr = ""
    monkeypatch.setattr(
        "core.last30days_tool.subprocess.run", lambda *a, **kw: mock_result
    )
    return mock_result


# ---------------------------------------------------------------------------
# Tool wrapper tests
# ---------------------------------------------------------------------------


class TestRunLast30daysResearch:
    """Tests for core.last30days_tool.run_last30days_research."""

    def test_disabled_returns_error(self, monkeypatch):
        monkeypatch.setattr("core.last30days_tool.LAST30DAYS_ENABLED", False)
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("AI trends")
        assert "❌" in result
        assert "LAST30DAYS_ENABLED" in result

    def test_missing_script_returns_error(self, monkeypatch):
        monkeypatch.setattr("core.last30days_tool.LAST30DAYS_ENABLED", True)
        monkeypatch.setattr("core.last30days_tool._resolve_script_path", lambda: "")
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("test")
        assert "❌" in result
        assert "engine" in result.lower()

    def test_empty_topic_returns_error(self, _enable_last30days):
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("")
        assert "❌" in result
        assert "topic" in result.lower()

    def test_topic_too_long_returns_error(self, _enable_last30days):
        from core.last30days_tool import run_last30days_research

        long_topic = "x" * 600
        result = run_last30days_research(long_topic)
        assert "❌" in result
        assert "500" in result  # MAX_TOPIC_LENGTH

    def test_successful_research(self, _enable_last30days, successful_subprocess):
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("AI trends")
        assert "AI trends" in result
        assert "❌" not in result
        assert "LLMs dominate" in result

    def test_successful_research_raw_text(self, _enable_last30days, monkeypatch):
        """Non-JSON output is formatted as raw report."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Some plain text research output"
        mock_result.stderr = ""
        monkeypatch.setattr(
            "core.last30days_tool.subprocess.run", lambda *a, **kw: mock_result
        )
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("test topic")
        assert "test topic" in result
        assert "plain text" in result

    def test_timeout_returns_error(self, _enable_last30days, monkeypatch):
        def raise_timeout(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="fake", timeout=180)

        monkeypatch.setattr("core.last30days_tool.subprocess.run", raise_timeout)
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("test")
        assert "❌" in result
        assert "timeout" in result.lower()

    def test_file_not_found_returns_error(self, _enable_last30days, monkeypatch):
        def raise_fnf(*a, **kw):
            raise FileNotFoundError("python3.12 not found")

        monkeypatch.setattr("core.last30days_tool.subprocess.run", raise_fnf)
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("test")
        assert "❌" in result
        assert "Python" in result

    def test_nonzero_exit_code(self, _enable_last30days, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "ImportError: something broke"
        monkeypatch.setattr(
            "core.last30days_tool.subprocess.run", lambda *a, **kw: mock_result
        )
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("test")
        assert "❌" in result
        assert "code 1" in result

    def test_empty_output_returns_error(self, _enable_last30days, monkeypatch):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = ""
        mock_result.stderr = ""
        monkeypatch.setattr(
            "core.last30days_tool.subprocess.run", lambda *a, **kw: mock_result
        )
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("test")
        assert "❌" in result
        assert "rỗng" in result

    def test_invalid_depth_falls_back(self, _enable_last30days, successful_subprocess):
        """Invalid depth silently falls back to 'default'."""
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("test", depth="invalid")
        assert "❌" not in result

    def test_invalid_sources_ignored(self, _enable_last30days, successful_subprocess):
        """Sources with special chars are silently ignored."""
        from core.last30days_tool import run_last30days_research

        result = run_last30days_research("test", sources="red<script>dit")
        assert "❌" not in result

    def test_days_clamped(self, _enable_last30days, successful_subprocess):
        from core.last30days_tool import run_last30days_research

        # days > 90 should clamp to 90, days < 1 → 1
        result = run_last30days_research("test", days=999)
        assert "❌" not in result
        result2 = run_last30days_research("test", days=-5)
        assert "❌" not in result2


# ---------------------------------------------------------------------------
# Flask route tests
# ---------------------------------------------------------------------------


class TestLast30daysRoute:
    """Tests for routes/last30days.py Flask blueprint."""

    @pytest.fixture
    def client(self, monkeypatch):
        """Create a minimal Flask app with only the last30days blueprint."""
        from flask import Flask

        app = Flask(__name__)
        app.config["TESTING"] = True
        from routes.last30days import last30days_bp

        app.register_blueprint(last30days_bp)
        return app.test_client()

    def test_missing_topic_returns_400(self, client):
        resp = client.post(
            "/api/tools/last30days",
            json={},
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False
        assert "topic" in data["error"].lower()

    def test_successful_request(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.last30days_tool.run_last30days_research",
            lambda topic, **kw: f"## 🔍 Results for {topic}",
        )
        resp = client.post(
            "/api/tools/last30days",
            json={"topic": "AI agents", "depth": "quick", "days": 7},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "AI agents" in data["result"]
        assert data["metadata"]["depth"] == "quick"
        assert data["metadata"]["days"] == 7

    def test_tool_error_returns_422(self, client, monkeypatch):
        monkeypatch.setattr(
            "core.last30days_tool.run_last30days_research",
            lambda topic, **kw: "❌ something went wrong",
        )
        resp = client.post(
            "/api/tools/last30days",
            json={"topic": "test"},
            content_type="application/json",
        )
        assert resp.status_code == 422
        data = resp.get_json()
        assert data["success"] is False

    def test_internal_exception_returns_500(self, client, monkeypatch):
        def boom(*a, **kw):
            raise RuntimeError("unexpected")

        monkeypatch.setattr("core.last30days_tool.run_last30days_research", boom)
        resp = client.post(
            "/api/tools/last30days",
            json={"topic": "test"},
            content_type="application/json",
        )
        assert resp.status_code == 500

    def test_invalid_depth_silently_fixed(self, client, monkeypatch):
        captured = {}

        def capture(topic, **kw):
            captured.update(kw)
            return "ok"

        monkeypatch.setattr("core.last30days_tool.run_last30days_research", capture)
        resp = client.post(
            "/api/tools/last30days",
            json={"topic": "test", "depth": "INVALID"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert captured.get("depth") == "default"

    def test_days_clamped_in_route(self, client, monkeypatch):
        captured = {}

        def capture(topic, **kw):
            captured.update(kw)
            return "ok"

        monkeypatch.setattr("core.last30days_tool.run_last30days_research", capture)
        resp = client.post(
            "/api/tools/last30days",
            json={"topic": "test", "days": 999},
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert captured.get("days") == 90


# ---------------------------------------------------------------------------
# Parse output tests
# ---------------------------------------------------------------------------


class TestParseCompactOutput:
    """Tests for JSON output parsing."""

    def test_json_with_all_fields(self):
        from core.last30days_tool import _parse_compact_output

        data = json.dumps(
            {
                "summary": "Summary text",
                "insights": [{"text": "Insight 1"}],
                "sources": [{"name": "Reddit", "count": 10}],
                "sentiment": "Positive",
                "trends": ["trend1"],
            }
        )
        result = _parse_compact_output(data, "topic")
        assert "Summary text" in result
        assert "Insight 1" in result
        assert "Reddit" in result
        assert "Positive" in result
        assert "trend1" in result

    def test_invalid_json_falls_back(self):
        from core.last30days_tool import _parse_compact_output

        result = _parse_compact_output("not json at all", "topic")
        assert "topic" in result
        assert "not json at all" in result

    def test_empty_json_falls_back(self):
        from core.last30days_tool import _parse_compact_output

        result = _parse_compact_output("{}", "topic")
        assert "topic" in result

    def test_long_raw_output_truncated(self):
        from core.last30days_tool import _format_raw_report

        long_text = "x" * 5000
        result = _format_raw_report(long_text, "topic")
        assert "truncated" in result
        assert len(result) < 5000


# ---------------------------------------------------------------------------
# 4. parse_research_params — inline command parser
# ---------------------------------------------------------------------------


class TestParseResearchParams:
    """Verify the research parameter parser used by stream.py."""

    def test_plain_topic(self):
        from core.last30days_tool import parse_research_params

        p = parse_research_params("AI trends")
        assert p == {
            "topic": "AI trends",
            "depth": "default",
            "days": 30,
            "sources": None,
        }

    def test_deep_flag(self):
        from core.last30days_tool import parse_research_params

        p = parse_research_params("crypto --deep")
        assert p["topic"] == "crypto"
        assert p["depth"] == "deep"

    def test_quick_flag(self):
        from core.last30days_tool import parse_research_params

        p = parse_research_params("AI --quick --days=7")
        assert p["depth"] == "quick"
        assert p["days"] == 7

    def test_sources_flag(self):
        from core.last30days_tool import parse_research_params

        p = parse_research_params("topic --sources=reddit,youtube")
        assert p["sources"] == "reddit,youtube"
        assert p["topic"] == "topic"

    def test_days_clamped(self):
        from core.last30days_tool import parse_research_params

        p = parse_research_params("x --days=999")
        assert p["days"] == 90
