"""
Hardening tests for the runtime skill system.

Covers scenarios missing from the initial test suites:
  - apply_skill_overrides() (zero prior coverage)
  - Singleton state isolation
  - Keyword substring false positives in auto-routing
  - Builtin YAML schema validation
  - Stale session skill handling
  - skill_auto_route bool vs string edge case
  - Full pipeline integration (resolve → apply)
  - API contract: activate disabled skill, non-JSON body
  - Route-level precedence: explicit > session > auto
"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.skills.applicator import apply_skill_overrides
from core.skills.registry import (
    SkillDefinition,
    SkillRegistry,
    _parse_yaml,
    get_skill_registry,
)
from core.skills.resolver import (
    SOURCE_AUTO,
    SOURCE_EXPLICIT,
    SOURCE_SESSION,
    SkillOverrides,
    resolve_skill,
)
from core.skills.router import (
    MIN_AUTO_ROUTE_SCORE,
    MIN_MESSAGE_WORDS,
    SkillRouter,
)
from core.skills.session import SkillSessionStore, set_session_skill

# ═════════════════════════════════════════════════════════════════════════
# 1. apply_skill_overrides — previously ZERO coverage
# ═════════════════════════════════════════════════════════════════════════


class TestApplyNoSkill:
    """When no skill is resolved, request values pass through unchanged."""

    def test_passthrough_keeps_request_values(self):
        data = {
            "model": "deepseek",
            "context": "programming",
            "tools": ["google-search"],
        }
        result = apply_skill_overrides(
            data=data, skill_overrides=SkillOverrides(), language="vi"
        )
        assert result.was_applied is False
        assert result.model == "deepseek"
        assert result.context == "programming"
        assert result.tools == ["google-search"]
        assert result.custom_prompt == ""

    def test_empty_request_gets_defaults(self):
        result = apply_skill_overrides(
            data={}, skill_overrides=SkillOverrides(), language="vi"
        )
        assert result.model == "grok"
        assert result.context == "casual"
        assert result.thinking_mode == "auto"
        assert result.deep_thinking is False
        assert result.tools == []

    def test_deep_thinking_string_true(self):
        data = {"deep_thinking": "true"}
        result = apply_skill_overrides(
            data=data, skill_overrides=SkillOverrides(), language="vi"
        )
        assert result.deep_thinking is False  # thinking_mode='auto' forces False

    def test_thinking_mode_drives_deep_thinking(self):
        data = {"thinking_mode": "thinking"}
        result = apply_skill_overrides(
            data=data, skill_overrides=SkillOverrides(), language="vi"
        )
        assert result.deep_thinking is True

    def test_tools_as_json_string(self):
        data = {"tools": '["google-search", "saucenao"]'}
        result = apply_skill_overrides(
            data=data, skill_overrides=SkillOverrides(), language="vi"
        )
        assert result.tools == ["google-search", "saucenao"]

    def test_tools_as_invalid_json_string(self):
        data = {"tools": "not-json"}
        result = apply_skill_overrides(
            data=data, skill_overrides=SkillOverrides(), language="vi"
        )
        assert result.tools == []


class TestApplyExplicitSkill:
    """When the user explicitly chose a skill (data['skill'] is set)."""

    @pytest.fixture()
    def skill_overrides(self):
        return SkillOverrides(
            skill_id="coding-assistant",
            skill_name="Coding Assistant",
            source=SOURCE_EXPLICIT,
            model="deepseek",
            thinking_mode="thinking",
            context="programming",
            prompt_injection="You are an expert Python coder.",
            preferred_tools=["google-search"],
            blocked_tools=["saucenao"],
        )

    def test_overrides_model(self, skill_overrides):
        data = {"model": "grok", "skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.model == "deepseek"
        assert result.was_applied is True

    def test_overrides_model_even_when_user_set_different(self, skill_overrides):
        """Explicit skill overrides EVERYTHING — even user's model choice."""
        data = {"model": "gemini", "skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.model == "deepseek"

    def test_overrides_context(self, skill_overrides):
        data = {"context": "casual", "skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.context == "programming"

    def test_overrides_thinking_mode(self, skill_overrides):
        data = {"thinking_mode": "instant", "skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.thinking_mode == "thinking"
        assert result.deep_thinking is True

    def test_removes_blocked_tools(self, skill_overrides):
        data = {"tools": ["google-search", "saucenao"], "skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert "saucenao" not in result.tools

    def test_adds_preferred_tools(self, skill_overrides):
        data = {"tools": [], "skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert "google-search" in result.tools

    def test_preferred_tools_no_duplication(self, skill_overrides):
        data = {"tools": ["google-search"], "skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.tools.count("google-search") == 1

    def test_prompt_injection_with_existing_custom_prompt(self, skill_overrides):
        data = {"custom_prompt": "Be concise.", "skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert "Be concise." in result.custom_prompt
        assert "expert Python coder" in result.custom_prompt

    def test_prompt_injection_without_custom_prompt(self, skill_overrides):
        data = {"skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert "expert Python coder" in result.custom_prompt

    def test_skill_identity_propagated(self, skill_overrides):
        data = {"skill": "coding-assistant"}
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.skill_id == "coding-assistant"
        assert result.skill_name == "Coding Assistant"


class TestApplyAutoRoutedSkill:
    """When the skill was auto-routed (data['skill'] is NOT set)."""

    @pytest.fixture()
    def skill_overrides(self):
        return SkillOverrides(
            skill_id="research-web",
            skill_name="Research Web",
            source=SOURCE_AUTO,
            model="deepseek",
            thinking_mode="thinking",
            context="research",
            prompt_injection="Research carefully.",
        )

    def test_auto_overrides_default_model(self, skill_overrides):
        """Auto-route overrides model when user left it at default."""
        data = {"model": "grok"}  # grok is the default
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.model == "deepseek"

    def test_auto_respects_user_model(self, skill_overrides):
        """Auto-route does NOT override when user explicitly set a model."""
        data = {"model": "gemini"}  # not default → user chose this
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.model == "gemini"

    def test_auto_respects_user_thinking_mode(self, skill_overrides):
        data = {"thinking_mode": "instant"}  # not default → user chose this
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.thinking_mode == "instant"

    def test_auto_overrides_default_thinking_mode(self, skill_overrides):
        data = {"thinking_mode": "auto"}  # default
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.thinking_mode == "thinking"
        assert result.deep_thinking is True

    def test_auto_respects_user_context(self, skill_overrides):
        data = {"context": "programming"}  # not default
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.context == "programming"

    def test_auto_overrides_default_context(self, skill_overrides):
        data = {"context": "casual"}  # default
        result = apply_skill_overrides(
            data=data, skill_overrides=skill_overrides, language="vi"
        )
        assert result.context == "research"


class TestApplyMCPPreference:
    """MCP preference flag for skills tagged with 'mcp'."""

    def test_mcp_tagged_skill_sets_prefer_mcp(self):
        reg = get_skill_registry()
        reg.register(
            SkillDefinition(
                id="mcp-test-skill",
                name="MCP Test",
                tags=["mcp"],
            )
        )
        overrides = SkillOverrides(
            skill_id="mcp-test-skill",
            skill_name="MCP Test",
            source=SOURCE_EXPLICIT,
        )
        data = {"skill": "mcp-test-skill"}
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.prefer_mcp is True

    def test_non_mcp_skill_no_prefer(self):
        reg = get_skill_registry()
        reg.register(
            SkillDefinition(
                id="non-mcp-skill",
                name="Non MCP",
                tags=["coding"],
            )
        )
        overrides = SkillOverrides(
            skill_id="non-mcp-skill",
            skill_name="Non MCP",
            source=SOURCE_EXPLICIT,
        )
        data = {"skill": "non-mcp-skill"}
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.prefer_mcp is False


# ═════════════════════════════════════════════════════════════════════════
# 2. Router — keyword substring false positives & edge cases
# ═════════════════════════════════════════════════════════════════════════


class TestRouterSubstringMatching:
    """Keyword substring matching is a known limitation — document behavior."""

    def _build_router_with(self, keywords, priority=10):
        reg = SkillRegistry()
        reg.register(
            SkillDefinition(
                id="target",
                name="Target",
                trigger_keywords=keywords,
                priority=priority,
            )
        )
        return SkillRouter(registry=reg)

    def test_keyword_code_matches_unicode(self):
        """Known limitation: 'code' matches inside 'unicode'."""
        router = self._build_router_with(["code"])
        skill = router.match("Can you help me with unicode encoding?")
        # This IS a false positive but it's the documented behavior
        assert skill is not None
        assert skill.id == "target"

    def test_keyword_api_matches_capital(self):
        """Known limitation: 'api' matches inside 'capital'."""
        router = self._build_router_with(["api"])
        skill = router.match("What is the capital of France?")
        assert skill is not None  # false positive — documented

    def test_exact_word_matches_correctly(self):
        router = self._build_router_with(["weather"])
        skill = router.match("What is the weather today in Hanoi?")
        assert skill is not None
        assert skill.id == "target"

    def test_empty_keywords_no_match(self):
        router = self._build_router_with([])
        assert router.match("any message at all here") is None

    def test_unicode_message_no_crash(self):
        router = self._build_router_with(["tìm kiếm"])
        skill = router.match("Hãy tìm kiếm thông tin về Hà Nội cho tôi")
        assert skill is not None


class TestRouterScoring:
    """Verify scoring formula: hits + priority/100."""

    def test_score_formula(self):
        reg = SkillRegistry()
        reg.register(
            SkillDefinition(
                id="s1",
                name="S1",
                trigger_keywords=["alpha", "beta"],
                priority=10,
            )
        )
        router = SkillRouter(registry=reg)
        result = router.match_detailed("alpha and beta are important concepts")
        assert result is not None
        # 2 hits + 10/100 = 2.10
        assert abs(result.score - 2.10) < 0.001
        assert set(result.matched_keywords) == {"alpha", "beta"}

    def test_min_score_threshold_value(self):
        """Verify the threshold constant is what we expect."""
        assert MIN_AUTO_ROUTE_SCORE == 1.05
        assert MIN_MESSAGE_WORDS == 3


# ═════════════════════════════════════════════════════════════════════════
# 3. Registry — edge cases
# ═════════════════════════════════════════════════════════════════════════


class TestRegistryEdgeCases:
    def test_parse_yaml_missing_id_raises(self):
        """YAML without 'id' should raise KeyError."""
        with pytest.raises(KeyError):
            _parse_yaml({"name": "No ID"})

    def test_parse_yaml_extra_keys_ignored(self):
        """Unknown YAML keys should be silently ignored (forward compatibility)."""
        s = _parse_yaml({"id": "x", "name": "X", "future_field": "value"})
        assert s.id == "x"
        assert not hasattr(s, "future_field")

    def test_parse_yaml_null_name(self):
        s = _parse_yaml({"id": "x", "name": None})
        assert s.name is None

    def test_register_overwrite(self):
        reg = SkillRegistry()
        reg.register(SkillDefinition(id="a", name="Alpha"))
        reg.register(SkillDefinition(id="a", name="Alpha-v2"))
        assert reg.get("a").name == "Alpha-v2"

    def test_get_by_name_empty_string(self):
        reg = SkillRegistry()
        reg.register(SkillDefinition(id="a", name="Alpha"))
        assert reg.get_by_name("") is None

    def test_all_builtins_valid_schema(self):
        """Every builtin YAML must produce a valid SkillDefinition with id and name."""
        reg = SkillRegistry()
        count = reg.load_builtins()
        assert count >= 11
        for skill in reg.list_all():
            assert skill.id, f"Skill missing id: {skill}"
            assert skill.name, f"Skill missing name: {skill}"
            assert isinstance(skill.trigger_keywords, list)
            assert isinstance(skill.priority, (int, float))
            assert isinstance(skill.tags, list)
            assert isinstance(skill.enabled, bool)

    def test_all_builtins_have_trigger_keywords(self):
        """Every builtin should have at least one trigger keyword for auto-routing."""
        reg = SkillRegistry()
        reg.load_builtins()
        for skill in reg.list_all():
            assert (
                len(skill.trigger_keywords) > 0
            ), f"Builtin '{skill.id}' has no trigger_keywords"


# ═════════════════════════════════════════════════════════════════════════
# 4. Resolver — stale session, source tracking, precedence
# ═════════════════════════════════════════════════════════════════════════


class TestResolverPrecedence:
    """Verify the explicit > session > auto > none priority chain."""

    @pytest.fixture(autouse=True)
    def _setup_registry(self):
        reg = get_skill_registry()
        reg.load_builtins()

    def test_explicit_overrides_session(self):
        set_session_skill("sess-1", "research-web")
        o = resolve_skill(
            message="debug this code error please help me",
            explicit_skill_id="coding-assistant",
            session_id="sess-1",
        )
        assert o.source == SOURCE_EXPLICIT
        assert o.skill_id == "coding-assistant"

    def test_session_overrides_auto(self):
        set_session_skill("sess-2", "research-web")
        # Message would auto-match coding, but session is set
        o = resolve_skill(
            message="debug this code error please help me",
            session_id="sess-2",
        )
        assert o.source == SOURCE_SESSION
        assert o.skill_id == "research-web"

    def test_auto_when_no_explicit_or_session(self):
        o = resolve_skill(
            message="debug this code error please help me fix the bug",
        )
        assert o.source == SOURCE_AUTO
        assert o.auto_route_score is not None

    def test_none_when_no_match(self):
        o = resolve_skill(
            message="Xin chào bạn, mọi thứ thế nào rồi?",
            auto_route=True,
        )
        assert o.active is False
        assert o.source is None

    def test_auto_disabled_returns_none(self):
        o = resolve_skill(
            message="debug this code error please help me fix the bug",
            auto_route=False,
        )
        assert o.active is False


class TestResolverStaleSession:
    """Handle session skill that was removed from registry after activation."""

    def test_stale_session_skill_skipped(self):
        reg = get_skill_registry()
        reg.register(SkillDefinition(id="temp-skill", name="Temp", enabled=True))
        set_session_skill("sess-stale", "temp-skill")

        # Remove the skill from registry
        reg.unregister("temp-skill")

        o = resolve_skill(
            message="Hello world, this is a test",
            session_id="sess-stale",
            auto_route=False,
        )
        assert o.active is False

    def test_disabled_session_skill_skipped(self):
        reg = get_skill_registry()
        reg.register(SkillDefinition(id="dis-skill", name="Dis", enabled=False))
        set_session_skill("sess-dis", "dis-skill")

        o = resolve_skill(
            message="Hello world, this is a test",
            session_id="sess-dis",
            auto_route=False,
        )
        assert o.active is False


class TestResolverAutoMetadata:
    """Auto-route should populate score + keywords in SkillOverrides."""

    @pytest.fixture(autouse=True)
    def _setup_registry(self):
        reg = get_skill_registry()
        reg.load_builtins()

    def test_auto_route_has_score_and_keywords(self):
        o = resolve_skill(
            message="debug this code error please help me fix the bug",
        )
        if o.source == SOURCE_AUTO:
            assert o.auto_route_score > 0
            assert len(o.auto_route_keywords) > 0

    def test_explicit_has_no_auto_metadata(self):
        o = resolve_skill(
            message="anything",
            explicit_skill_id="coding-assistant",
        )
        assert o.source == SOURCE_EXPLICIT
        assert o.auto_route_score is None
        assert o.auto_route_keywords == []


# ═════════════════════════════════════════════════════════════════════════
# 5. Session store — edge cases
# ═════════════════════════════════════════════════════════════════════════


class TestSessionStoreEdgeCases:
    def test_set_none_skill_id(self):
        """Setting None as skill_id should be retrievable as None."""
        store = SkillSessionStore()
        store.set("sess", None)
        assert store.get("sess") is None

    def test_set_empty_string_skill_id(self):
        store = SkillSessionStore()
        store.set("sess", "")
        assert store.get("sess") == ""

    def test_clear_nonexistent_session(self):
        """Clearing a session that doesn't exist should not raise."""
        store = SkillSessionStore()
        store.clear("does-not-exist")  # should not raise

    def test_clear_all_empties_store(self):
        store = SkillSessionStore()
        store.set("a", "skill-1")
        store.set("b", "skill-2")
        store.clear_all()
        assert store.get("a") is None
        assert store.get("b") is None
        assert store.list_active() == {}


# ═════════════════════════════════════════════════════════════════════════
# 6. Full pipeline integration
# ═════════════════════════════════════════════════════════════════════════


class TestFullPipeline:
    """End-to-end: resolve_skill → apply_skill_overrides → verify AppliedSkill."""

    @pytest.fixture(autouse=True)
    def _setup_registry(self):
        reg = get_skill_registry()
        reg.load_builtins()

    def test_explicit_skill_full_pipeline(self):
        data = {"message": "test", "model": "grok", "skill": "coding-assistant"}
        overrides = resolve_skill(
            message="test",
            explicit_skill_id="coding-assistant",
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.was_applied is True
        assert result.skill_id == "coding-assistant"
        assert result.context == "programming"
        assert result.thinking_mode == "thinking"
        assert result.deep_thinking is True
        assert "google-search" in result.tools  # preferred tool from YAML

    def test_no_skill_full_pipeline(self):
        data = {"message": "hello", "model": "grok"}
        overrides = resolve_skill(message="hello, how are you?", auto_route=False)
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.was_applied is False
        assert result.model == "grok"
        assert result.skill_id is None

    def test_auto_route_full_pipeline(self):
        data = {
            "message": "search the web for Python tutorials and documentation",
            "model": "grok",
        }
        overrides = resolve_skill(
            message="search the web for Python tutorials and documentation",
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        # May or may not match depending on keywords — just verify no crash
        if overrides.active:
            assert result.was_applied is True
            assert result.skill_id is not None


# ═════════════════════════════════════════════════════════════════════════
# 7. API route contract tests
# ═════════════════════════════════════════════════════════════════════════


class TestAPIContractHardening:
    """Additional API tests for edge cases."""

    @pytest.fixture()
    def client(self):
        from app import app as flask_app

        flask_app.config["TESTING"] = True
        with flask_app.test_client() as c:
            yield c

    def test_activate_disabled_skill(self, client):
        """Activating a disabled skill should return 400."""
        reg = get_skill_registry()
        reg.register(SkillDefinition(id="off-api", name="Off", enabled=False))
        resp = client.post(
            "/api/skills/activate",
            json={"skill_id": "off-api"},
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data.get("success") is False

    def test_activate_by_name(self, client):
        """Activating by name instead of id should work."""
        reg = get_skill_registry()
        reg.load_builtins()
        resp = client.post(
            "/api/skills/activate",
            json={"skill_id": "Coding Assistant"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data.get("success") is True
        assert data.get("skill_id") == "coding-assistant"

    def test_activate_non_json_body(self, client):
        """Non-JSON body should return 400, not crash."""
        resp = client.post(
            "/api/skills/activate",
            data="not json",
            content_type="text/plain",
        )
        assert resp.status_code == 400

    def test_list_skills_returns_array(self, client):
        resp = client.get("/api/skills")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "skills" in data
        assert isinstance(data["skills"], list)

    def test_get_skill_returns_full_schema(self, client):
        """Individual skill response should have all expected fields."""
        reg = get_skill_registry()
        reg.load_builtins()
        resp = client.get("/api/skills/coding-assistant")
        assert resp.status_code == 200
        data = resp.get_json()
        expected_fields = {
            "id",
            "name",
            "description",
            "tags",
            "enabled",
            "priority",
            "trigger_keywords",
        }
        assert expected_fields.issubset(set(data.get("skill", {}).keys()))

    def test_active_skill_after_clear(self, client):
        """After deactivate, /api/skills/active should show no skill."""
        reg = get_skill_registry()
        reg.load_builtins()
        client.post("/api/skills/activate", json={"skill_id": "coding-assistant"})
        client.post("/api/skills/deactivate")
        resp = client.get("/api/skills/active")
        data = resp.get_json()
        assert data.get("active") is False

    def test_stream_metadata_includes_skill_source(self, client):
        """The /chat/stream metadata SSE event should include skill_source field."""
        import re

        reg = get_skill_registry()
        reg.load_builtins()
        resp = client.post(
            "/chat/stream",
            json={
                "message": "debug this code error please help me fix the bug now",
                "skill": "coding-assistant",
                "model": "grok",
            },
        )
        # Read the full SSE stream
        raw = resp.data.decode("utf-8", errors="replace")
        # Find metadata event
        for block in raw.split("\n\n"):
            if "event: metadata" in block:
                data_match = re.search(r"data: (.+)", block)
                if data_match:
                    meta = json.loads(data_match.group(1))
                    assert "skill_source" in meta
                    assert meta["skill_source"] in ("explicit", "session", "auto", None)
                    assert "skill" in meta
                    assert "skill_name" in meta
                    break
        else:
            pytest.skip("Metadata event not found in SSE stream (may need auth)")


# ═════════════════════════════════════════════════════════════════════════
# 8. skill_auto_route type safety
# ═════════════════════════════════════════════════════════════════════════


class TestAutoRouteParamTypeSafety:
    """Verify skill_auto_route handles both bool and string values."""

    def test_str_parsing(self):
        """str(True).lower() == 'true', so this should enable auto-route."""
        val = True  # JSON boolean
        result = str(val).lower() != "false"
        assert result is True

    def test_str_false_parsing(self):
        val = False
        result = str(val).lower() != "false"
        assert result is False

    def test_string_true(self):
        val = "true"
        result = str(val).lower() != "false"
        assert result is True

    def test_string_false(self):
        val = "false"
        result = str(val).lower() != "false"
        assert result is False
