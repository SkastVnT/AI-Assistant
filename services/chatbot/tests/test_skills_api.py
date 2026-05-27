"""
Tests for the skills API routes (/api/skills/*).

Tests both:
  - Unit-level tests using direct function calls (no Flask app needed)
  - Route-level tests using the Flask test client (conftest.py client fixture)
"""

import sys
from pathlib import Path

# Add chatbot root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.skills.registry import get_skill_registry
from core.skills.session import (
    clear_session_skill,
    get_session_skill,
    set_session_skill,
)

# ── Unit tests — skill session interactions ──────────────────────────────


class TestSkillSessionContract:
    """Verify session skill set/get/clear contract used by routes."""

    def test_activate_and_retrieve(self):
        sid = "test-api-sess-1"
        set_session_skill(sid, "coding-assistant")
        try:
            assert get_session_skill(sid) == "coding-assistant"
        finally:
            clear_session_skill(sid)

    def test_deactivate_returns_true_when_active(self):
        sid = "test-api-sess-2"
        set_session_skill(sid, "research-web")
        assert clear_session_skill(sid) is True

    def test_deactivate_returns_false_when_empty(self):
        assert clear_session_skill("nonexistent-session") is False

    def test_overwrite_skill(self):
        sid = "test-api-sess-3"
        set_session_skill(sid, "coding-assistant")
        set_session_skill(sid, "research-web")
        try:
            assert get_session_skill(sid) == "research-web"
        finally:
            clear_session_skill(sid)


# ── Unit tests — registry queries used by routes ─────────────────────────


class TestSkillRegistryForAPI:
    """Verify registry operations that back the API endpoints."""

    def test_list_ui_visible_returns_list(self):
        registry = get_skill_registry()
        skills = registry.list_ui_visible()
        assert isinstance(skills, list)
        assert len(skills) > 0

    def test_get_by_id(self):
        registry = get_skill_registry()
        skill = registry.get("code-expert")
        assert skill is not None
        assert skill.id == "code-expert"

    def test_get_by_name(self):
        registry = get_skill_registry()
        skill = registry.get_by_name("Code Expert")
        assert skill is not None
        assert skill.id == "code-expert"

    def test_get_nonexistent_returns_none(self):
        registry = get_skill_registry()
        assert registry.get("nonexistent-skill-xyz") is None

    def test_to_dict_api_fields(self):
        """Verify to_dict has all fields the API endpoint needs."""
        registry = get_skill_registry()
        skill = registry.get("code-expert")
        d = skill.to_dict()
        required_keys = {
            "id",
            "name",
            "description",
            "default_model",
            "default_thinking_mode",
            "default_context",
            "preferred_tools",
            "blocked_tools",
            "tags",
            "enabled",
            "ui_visible",
        }
        assert required_keys.issubset(d.keys())


# ── Route-level tests — Flask test client ────────────────────────────────


class TestSkillsListRoute:
    """GET /api/skills"""

    def test_list_skills_returns_200(self, client):
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "skills" in data
        assert "total" in data
        assert isinstance(data["skills"], list)
        assert data["total"] == len(data["skills"])

    def test_list_skills_shape(self, client):
        resp = client.get("/api/skills")
        data = resp.get_json()
        if data["total"] > 0:
            skill = data["skills"][0]
            assert "id" in skill
            assert "name" in skill
            assert "description" in skill
            assert "tags" in skill
            assert "enabled" in skill

    def test_list_skills_excludes_disabled_by_default(self, client):
        """Disabled skills should not appear unless include_disabled=true."""
        resp = client.get("/api/skills")
        data = resp.get_json()
        for skill in data["skills"]:
            assert skill["enabled"] is True

    def test_list_skills_include_disabled(self, client):
        resp = client.get("/api/skills?include_disabled=true")
        assert resp.status_code == 200
        data = resp.get_json()
        assert isinstance(data["skills"], list)

    def test_list_skills_filter_by_tag(self, client):
        resp = client.get("/api/skills?tag=search")
        assert resp.status_code == 200
        data = resp.get_json()
        for skill in data["skills"]:
            assert "search" in skill["tags"]


class TestSkillGetRoute:
    """GET /api/skills/<id>"""

    def test_get_existing_skill(self, client):
        resp = client.get("/api/skills/code-expert")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "skill" in data
        assert data["skill"]["id"] == "code-expert"
        assert "prompt_fragments" in data["skill"]
        assert "trigger_keywords" in data["skill"]

    def test_get_skill_by_name(self, client):
        resp = client.get("/api/skills/Code Expert")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["skill"]["id"] == "code-expert"

    def test_get_nonexistent_skill(self, client):
        resp = client.get("/api/skills/nonexistent-xyz")
        assert resp.status_code == 404
        data = resp.get_json()
        assert "error" in data


class TestSkillActivateRoute:
    """POST /api/skills/activate"""

    def test_activate_valid_skill(self, client):
        resp = client.post(
            "/api/skills/activate",
            json={"skill_id": "code-expert"},
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["skill_id"] == "code-expert"
        assert "skill_name" in data
        assert "session_id" in data

    def test_activate_missing_skill_id(self, client):
        resp = client.post(
            "/api/skills/activate", json={}, content_type="application/json"
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["success"] is False

    def test_activate_nonexistent_skill(self, client):
        resp = client.post(
            "/api/skills/activate",
            json={"skill_id": "nonexistent-xyz"},
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_activate_empty_string(self, client):
        resp = client.post(
            "/api/skills/activate",
            json={"skill_id": ""},
            content_type="application/json",
        )
        assert resp.status_code == 400


class TestSkillDeactivateRoute:
    """POST /api/skills/deactivate"""

    def test_deactivate_no_active_skill(self, client):
        resp = client.post("/api/skills/deactivate")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True

    def test_activate_then_deactivate(self, client):
        # First activate
        client.post(
            "/api/skills/activate",
            json={"skill_id": "code-expert"},
            content_type="application/json",
        )
        # Then deactivate
        resp = client.post("/api/skills/deactivate")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True


class TestSkillActiveRoute:
    """GET /api/skills/active"""

    def test_no_active_skill(self, client):
        resp = client.get("/api/skills/active")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["active"] is False
        assert data["skill_id"] is None

    def test_active_after_activate(self, client):
        # Activate a skill
        client.post(
            "/api/skills/activate",
            json={"skill_id": "code-expert"},
            content_type="application/json",
        )
        # Check active
        resp = client.get("/api/skills/active")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["active"] is True
        assert data["skill_id"] == "code-expert"
        assert "skill_name" in data


class TestSkillsInStreamMetadata:
    """Verify that the SSE metadata event includes skill info."""

    def test_stream_metadata_has_skill_fields(self):
        """The stream.py metadata event should include skill and skill_name."""
        # This is a structural test — verify the code includes the fields.
        # Reading the source to confirm rather than making an actual stream call.
        stream_path = Path(__file__).parent.parent / "routes" / "stream.py"
        content = stream_path.read_text(encoding="utf-8")
        assert '"skill": applied.skill_id' in content
        assert '"skill_name": applied.skill_name' in content
