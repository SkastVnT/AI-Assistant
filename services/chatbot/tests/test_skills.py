"""
Tests for the runtime skill system:
  - SkillDefinition (schema, serialization)
  - SkillRegistry (load, query, CRUD, enabled filtering)
  - SkillRouter (auto-match, priority, disabled skill skip)
  - SkillResolver (explicit, session, auto, fallback, disabled)
  - SkillSessionStore (set, get, clear, thread safety)
  - SkillOverrides (active property, defaults)
"""

import json
import sys
import threading
from pathlib import Path

# Add chatbot root to path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ── SkillDefinition ──────────────────────────────────────────────────────

from core.skills.registry import SkillDefinition, SkillRegistry, _parse_yaml


class TestSkillDefinition:
    def test_defaults(self):
        s = SkillDefinition(id="test", name="Test")
        assert s.id == "test"
        assert s.prompt_fragments == []
        assert s.preferred_tools == []
        assert s.blocked_tools == []
        assert s.default_model is None
        assert s.default_thinking_mode is None
        assert s.default_context is None
        assert s.trigger_keywords == []
        assert s.priority == 0
        assert s.ui_visible is True
        assert s.builtin is False
        assert s.tags == []
        assert s.enabled is True

    def test_parse_yaml_minimal(self):
        raw = {"id": "x", "name": "X"}
        s = _parse_yaml(raw)
        assert s.id == "x"
        assert s.name == "X"
        assert s.builtin is False
        assert s.tags == []
        assert s.enabled is True

    def test_parse_yaml_full(self):
        raw = {
            "id": "deep",
            "name": "Deep Coder",
            "description": "desc",
            "prompt_fragments": ["You are a coder."],
            "preferred_tools": ["google-search"],
            "blocked_tools": ["saucenao"],
            "default_model": "grok",
            "default_thinking_mode": "deep",
            "default_context": "programming",
            "trigger_keywords": ["code", "debug"],
            "priority": 10,
            "ui_visible": False,
            "tags": ["coding", "dev"],
            "enabled": True,
        }
        s = _parse_yaml(raw, builtin=True)
        assert s.id == "deep"
        assert s.builtin is True
        assert s.prompt_fragments == ["You are a coder."]
        assert s.preferred_tools == ["google-search"]
        assert s.blocked_tools == ["saucenao"]
        assert s.default_model == "grok"
        assert s.default_thinking_mode == "deep"
        assert s.default_context == "programming"
        assert s.trigger_keywords == ["code", "debug"]
        assert s.priority == 10
        assert s.ui_visible is False
        assert s.tags == ["coding", "dev"]
        assert s.enabled is True

    def test_parse_yaml_system_prompt_append_alias(self):
        """``system_prompt_append`` in YAML should map to ``prompt_fragments``."""
        raw = {
            "id": "alias-test",
            "name": "Alias",
            "system_prompt_append": ["You are a helper."],
        }
        s = _parse_yaml(raw)
        assert s.prompt_fragments == ["You are a helper."]

    def test_parse_yaml_disabled(self):
        raw = {"id": "off", "name": "Off", "enabled": False}
        s = _parse_yaml(raw)
        assert s.enabled is False

    def test_to_dict_roundtrip(self):
        s = SkillDefinition(
            id="rt",
            name="Roundtrip",
            description="d",
            tags=["a", "b"],
            enabled=True,
            priority=5,
        )
        d = s.to_dict()
        assert d["id"] == "rt"
        assert d["tags"] == ["a", "b"]
        assert d["enabled"] is True
        assert d["priority"] == 5
        # JSON serializable
        json.dumps(d)

    def test_to_dict_contains_all_fields(self):
        s = SkillDefinition(id="full", name="Full")
        d = s.to_dict()
        expected_keys = {
            "id",
            "name",
            "description",
            "prompt_fragments",
            "preferred_tools",
            "blocked_tools",
            "default_model",
            "default_thinking_mode",
            "default_context",
            "trigger_keywords",
            "priority",
            "ui_visible",
            "builtin",
            "tags",
            "enabled",
        }
        assert set(d.keys()) == expected_keys


# ── SkillRegistry ────────────────────────────────────────────────────────


class TestSkillRegistry:
    def _make_registry(self):
        r = SkillRegistry()
        r.register(SkillDefinition(id="a", name="Alpha", ui_visible=True))
        r.register(SkillDefinition(id="b", name="Beta", ui_visible=False))
        r.register(
            SkillDefinition(id="c", name="Charlie", ui_visible=True, enabled=False)
        )
        return r

    def test_get_existing(self):
        r = self._make_registry()
        assert r.get("a") is not None
        assert r.get("a").name == "Alpha"

    def test_get_missing(self):
        r = self._make_registry()
        assert r.get("nope") is None

    def test_get_by_name(self):
        r = self._make_registry()
        assert r.get_by_name("Alpha").id == "a"

    def test_get_by_name_case_insensitive(self):
        r = self._make_registry()
        assert r.get_by_name("alpha").id == "a"
        assert r.get_by_name("ALPHA").id == "a"

    def test_get_by_name_missing(self):
        r = self._make_registry()
        assert r.get_by_name("no-such-skill") is None

    def test_list_all(self):
        r = self._make_registry()
        assert len(r.list_all()) == 3

    def test_list_enabled(self):
        r = self._make_registry()
        enabled = r.list_enabled()
        ids = {s.id for s in enabled}
        assert "a" in ids
        assert "b" in ids
        assert "c" not in ids

    def test_list_ids(self):
        r = self._make_registry()
        assert set(r.list_ids()) == {"a", "b", "c"}

    def test_list_ui_visible_respects_enabled(self):
        r = self._make_registry()
        vis = r.list_ui_visible()
        ids = {s.id for s in vis}
        # "a" is visible+enabled, "c" is visible+disabled → excluded
        assert ids == {"a"}

    def test_unregister(self):
        r = self._make_registry()
        assert r.unregister("a") is True
        assert r.get("a") is None
        assert r.unregister("a") is False

    def test_overwrite(self):
        r = self._make_registry()
        r.register(SkillDefinition(id="a", name="A-replaced"))
        assert r.get("a").name == "A-replaced"

    def test_load_builtins(self):
        r = SkillRegistry()
        count = r.load_builtins()
        # 5 original skills + 6 new skills = 11
        assert count >= 11
        # Check the 6 new requested skills
        assert r.get("coding-assistant") is not None
        assert r.get("repo-analyzer") is not None
        assert r.get("research-web") is not None
        assert r.get("mcp-file-helper") is not None
        assert r.get("prompt-engineer") is not None
        assert r.get("shopping-advisor") is not None
        # Original skills still present
        assert r.get("code-expert") is not None
        assert r.get("research-analyst") is not None

    def test_builtin_skills_have_tags(self):
        r = SkillRegistry()
        r.load_builtins()
        coding = r.get("coding-assistant")
        assert len(coding.tags) > 0
        assert "coding" in coding.tags

    def test_all_builtins_enabled(self):
        r = SkillRegistry()
        r.load_builtins()
        for skill in r.list_all():
            assert skill.enabled is True, f"Built-in {skill.id} should be enabled"


# ── SkillRouter ──────────────────────────────────────────────────────────

from core.skills.router import SkillRouter


class TestSkillRouter:
    def _build_router(self):
        reg = SkillRegistry()
        reg.register(
            SkillDefinition(
                id="code",
                name="Code",
                trigger_keywords=["code", "debug", "function"],
                priority=10,
            )
        )
        reg.register(
            SkillDefinition(
                id="search",
                name="Search",
                trigger_keywords=["price", "weather", "news"],
                priority=12,
            )
        )
        reg.register(
            SkillDefinition(
                id="no-triggers",
                name="No Triggers",
                trigger_keywords=[],
            )
        )
        reg.register(
            SkillDefinition(
                id="disabled-skill",
                name="Disabled",
                trigger_keywords=["code", "debug"],
                priority=99,
                enabled=False,
            )
        )
        return SkillRouter(registry=reg)

    def test_match_code(self):
        router = self._build_router()
        skill = router.match("Can you debug this function?")
        assert skill is not None
        assert skill.id == "code"

    def test_match_search(self):
        router = self._build_router()
        skill = router.match("What is the weather today?")
        assert skill is not None
        assert skill.id == "search"

    def test_no_match(self):
        router = self._build_router()
        skill = router.match("Hello, how are you?")
        assert skill is None

    def test_empty_message(self):
        router = self._build_router()
        assert router.match("") is None

    def test_disabled_skill_skipped(self):
        """Disabled skills should never auto-match, even with higher priority."""
        router = self._build_router()
        skill = router.match("code debug fix this function please")
        assert skill is not None
        assert skill.id == "code"  # not "disabled-skill" (priority 99 but disabled)

    def test_priority_tiebreak(self):
        reg = SkillRegistry()
        reg.register(
            SkillDefinition(
                id="low",
                name="Low",
                trigger_keywords=["test"],
                priority=1,
            )
        )
        reg.register(
            SkillDefinition(
                id="high",
                name="High",
                trigger_keywords=["test"],
                priority=20,
            )
        )
        router = SkillRouter(registry=reg)
        skill = router.match("this is a test")
        assert skill.id == "high"

    def test_multi_keyword_score(self):
        reg = SkillRegistry()
        reg.register(
            SkillDefinition(
                id="narrow",
                name="Narrow",
                trigger_keywords=["code"],
                priority=5,
            )
        )
        reg.register(
            SkillDefinition(
                id="broad",
                name="Broad",
                trigger_keywords=["code", "debug", "fix", "error"],
                priority=0,
            )
        )
        router = SkillRouter(registry=reg)
        skill = router.match("code debug error please")
        assert skill.id == "broad"

    def test_short_message_skipped(self):
        """Messages with ≤ MIN_MESSAGE_WORDS words should not auto-match."""
        router = self._build_router()
        assert router.match("debug") is None
        assert router.match("debug code") is None
        assert router.match("debug code fix") is None  # 3 words ≤ MIN_MESSAGE_WORDS

    def test_match_detailed_returns_metadata(self):
        """match_detailed() should return RouteMatch with score and keywords."""
        from core.skills.router import RouteMatch

        router = self._build_router()
        result = router.match_detailed("Can you debug this function?")
        assert result is not None
        assert isinstance(result, RouteMatch)
        assert result.skill.id == "code"
        assert result.score > 0
        assert (
            "debug" in result.matched_keywords or "function" in result.matched_keywords
        )

    def test_match_detailed_none_for_no_match(self):
        router = self._build_router()
        assert router.match_detailed("Hello, how are you?") is None

    def test_match_detailed_none_for_short(self):
        router = self._build_router()
        assert router.match_detailed("debug") is None

    def test_threshold_rejects_low_score(self):
        """A single keyword hit on a low-priority skill should be rejected."""
        reg = SkillRegistry()
        reg.register(
            SkillDefinition(
                id="weak",
                name="Weak",
                trigger_keywords=["test"],
                priority=0,
            )
        )
        router = SkillRouter(registry=reg)
        # Single keyword "test" + priority 0 → score = 1.00 < 1.05
        assert router.match("this is a test message") is None

    def test_threshold_accepts_high_priority(self):
        """A single keyword hit on a high-priority skill should pass."""
        reg = SkillRegistry()
        reg.register(
            SkillDefinition(
                id="strong",
                name="Strong",
                trigger_keywords=["test"],
                priority=10,
            )
        )
        router = SkillRouter(registry=reg)
        # Single keyword "test" + priority 10 → score = 1.10 > 1.05
        skill = router.match("this is a test message")
        assert skill is not None
        assert skill.id == "strong"


# ── SkillResolver ────────────────────────────────────────────────────────

from core.skills.resolver import (
    SOURCE_AUTO,
    SOURCE_EXPLICIT,
    SOURCE_SESSION,
    SkillOverrides,
    resolve_skill,
)


class TestSkillResolver:
    def test_no_skill(self):
        overrides = resolve_skill(message="Hello!", auto_route=False)
        assert overrides.active is False
        assert overrides.skill_id is None
        assert overrides.prompt_injection is None
        assert overrides.source is None

    def test_explicit_skill_by_id(self):
        from core.skills.registry import get_skill_registry

        get_skill_registry()  # ensure builtins loaded

        overrides = resolve_skill(
            message="anything", explicit_skill_id="coding-assistant"
        )
        assert overrides.active is True
        assert overrides.skill_id == "coding-assistant"
        assert overrides.context == "programming"
        assert overrides.thinking_mode == "thinking"
        assert overrides.source == SOURCE_EXPLICIT

    def test_explicit_skill_by_name(self):
        from core.skills.registry import get_skill_registry

        get_skill_registry()

        overrides = resolve_skill(
            message="anything", explicit_skill_id="Coding Assistant"
        )
        assert overrides.active is True
        assert overrides.skill_id == "coding-assistant"
        assert overrides.source == SOURCE_EXPLICIT

    def test_explicit_missing_skill_fallback(self):
        overrides = resolve_skill(
            message="Hello!",
            explicit_skill_id="nonexistent-skill-xyz",
            auto_route=False,
        )
        # Falls through to no-skill
        assert overrides.active is False

    def test_explicit_disabled_skill_skipped(self):
        """Explicitly requesting a disabled skill should fall through."""
        from core.skills.registry import get_skill_registry

        reg = get_skill_registry()
        reg.register(SkillDefinition(id="off-skill", name="Off", enabled=False))
        overrides = resolve_skill(
            message="anything",
            explicit_skill_id="off-skill",
            auto_route=False,
        )
        assert overrides.active is False

    def test_auto_route(self):
        from core.skills.registry import get_skill_registry

        get_skill_registry()

        overrides = resolve_skill(message="debug this code error please help me")
        assert overrides.active is True
        assert overrides.source == SOURCE_AUTO
        assert overrides.auto_route_score is not None
        assert overrides.auto_route_score > 0
        assert len(overrides.auto_route_keywords) > 0

    def test_auto_route_disabled(self):
        overrides = resolve_skill(
            message="debug this code please",
            auto_route=False,
        )
        assert overrides.active is False

    def test_session_skill(self):
        from core.skills.registry import get_skill_registry
        from core.skills.session import clear_session_skill, set_session_skill

        get_skill_registry()

        set_session_skill("test-sess-1", "research-web")
        try:
            overrides = resolve_skill(
                message="random chat",
                session_id="test-sess-1",
                auto_route=False,
            )
            assert overrides.active is True
            assert overrides.skill_id == "research-web"
            assert overrides.source == SOURCE_SESSION
        finally:
            clear_session_skill("test-sess-1")

    def test_explicit_overrides_session(self):
        """Explicit skill_id takes precedence over session skill."""
        from core.skills.registry import get_skill_registry
        from core.skills.session import clear_session_skill, set_session_skill

        get_skill_registry()

        set_session_skill("test-sess-2", "research-web")
        try:
            overrides = resolve_skill(
                message="anything",
                explicit_skill_id="coding-assistant",
                session_id="test-sess-2",
            )
            assert overrides.skill_id == "coding-assistant"
        finally:
            clear_session_skill("test-sess-2")

    def test_tool_gating(self):
        from core.skills.registry import get_skill_registry

        get_skill_registry()

        overrides = resolve_skill(
            message="anything", explicit_skill_id="creative-writer"
        )
        assert "google-search" in overrides.blocked_tools
        assert overrides.preferred_tools == []


# ── SkillSessionStore ────────────────────────────────────────────────────

from core.skills.session import SkillSessionStore


class TestSkillSessionStore:
    def test_set_and_get(self):
        store = SkillSessionStore()
        store.set("s1", "coding-assistant")
        assert store.get("s1") == "coding-assistant"

    def test_get_missing(self):
        store = SkillSessionStore()
        assert store.get("missing") is None

    def test_clear(self):
        store = SkillSessionStore()
        store.set("s1", "code-expert")
        assert store.clear("s1") is True
        assert store.get("s1") is None
        assert store.clear("s1") is False

    def test_overwrite(self):
        store = SkillSessionStore()
        store.set("s1", "a")
        store.set("s1", "b")
        assert store.get("s1") == "b"

    def test_list_active(self):
        store = SkillSessionStore()
        store.set("s1", "a")
        store.set("s2", "b")
        active = store.list_active()
        assert active == {"s1": "a", "s2": "b"}

    def test_clear_all(self):
        store = SkillSessionStore()
        store.set("s1", "a")
        store.set("s2", "b")
        assert store.clear_all() == 2
        assert store.list_active() == {}

    def test_thread_safety(self):
        store = SkillSessionStore()
        errors = []

        def writer(session_id, skill_id, n=100):
            try:
                for _ in range(n):
                    store.set(session_id, skill_id)
                    store.get(session_id)
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer, args=(f"s{i}", f"skill-{i}"))
            for i in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []


# ── SkillOverrides dataclass ─────────────────────────────────────────────


class TestSkillOverrides:
    def test_active_when_skill_present(self):
        o = SkillOverrides(skill_id="x")
        assert o.active is True

    def test_inactive_when_empty(self):
        o = SkillOverrides()
        assert o.active is False

    def test_defaults(self):
        o = SkillOverrides()
        assert o.prompt_injection is None
        assert o.preferred_tools == []
        assert o.blocked_tools == []
        assert o.model is None
        assert o.thinking_mode is None
        assert o.context is None
        assert o.source is None
        assert o.auto_route_score is None
        assert o.auto_route_keywords == []


# ── AppliedSkill + apply_skill_overrides ─────────────────────────────────

from core.skills.applicator import AppliedSkill, apply_skill_overrides


class TestAppliedSkillDefaults:
    def test_defaults(self):
        a = AppliedSkill()
        assert a.skill_id is None
        assert a.was_applied is False
        assert a.model == "grok"
        assert a.context == "casual"
        assert a.thinking_mode == "auto"
        assert a.deep_thinking is False
        assert a.custom_prompt == ""
        assert a.tools == []
        assert a.prefer_mcp is False


class TestApplySkillOverrides:
    """Test the centralized apply_skill_overrides function."""

    # ── No skill active → passthrough ────────────────────────────────

    def test_no_skill_passthrough(self):
        """When no skill is resolved, request values pass through unchanged."""
        data = {
            "model": "deepseek",
            "context": "programming",
            "tools": ["google-search"],
        }
        overrides = SkillOverrides()  # empty, no skill
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.was_applied is False
        assert result.model == "deepseek"
        assert result.context == "programming"
        assert result.tools == ["google-search"]
        assert result.custom_prompt == ""

    def test_no_skill_defaults(self):
        """No skill + missing request fields → system defaults."""
        result = apply_skill_overrides(
            data={}, skill_overrides=SkillOverrides(), language="vi"
        )
        assert result.model == "grok"
        assert result.context == "casual"
        assert result.deep_thinking is False

    # ── Explicit skill → all overrides apply ─────────────────────────

    def test_explicit_skill_overrides_model(self):
        """Explicit skill selection overrides model even if user set one."""
        data = {"model": "deepseek", "skill": "coding-assistant"}
        overrides = SkillOverrides(
            skill_id="coding-assistant",
            skill_name="Coding Assistant",
            model="grok",
            context="programming",
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.was_applied is True
        assert result.model == "grok"  # skill overrides user's deepseek
        assert result.context == "programming"

    def test_explicit_skill_overrides_thinking(self):
        """Explicit skill overrides thinking mode."""
        data = {"thinking_mode": "auto", "skill": "deep-code"}
        overrides = SkillOverrides(
            skill_id="deep-code",
            skill_name="Deep Code",
            thinking_mode="deep",
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.thinking_mode == "deep"
        assert result.deep_thinking is True

    # ── Auto-routed skill → conditional overrides ────────────────────

    def test_auto_routed_overrides_defaults(self):
        """Auto-routed skill overrides when user is using default values."""
        data = {"model": "grok", "context": "casual"}  # no "skill" key
        overrides = SkillOverrides(
            skill_id="research-web",
            skill_name="Research Web",
            model="deepseek",
            context="research",
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.model == "deepseek"
        assert result.context == "research"

    def test_auto_routed_respects_user_model(self):
        """Auto-routed skill does NOT override a non-default user model."""
        data = {"model": "openai"}  # user explicitly chose openai, no "skill" key
        overrides = SkillOverrides(
            skill_id="research-web",
            skill_name="Research Web",
            model="deepseek",
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.model == "openai"  # user's choice preserved

    def test_auto_routed_respects_user_thinking(self):
        """Auto-routed skill does NOT override user's explicit thinking mode."""
        data = {"thinking_mode": "deep"}  # user explicitly chose deep
        overrides = SkillOverrides(
            skill_id="auto-x",
            skill_name="Auto X",
            thinking_mode="instant",
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.thinking_mode == "deep"  # user's choice preserved
        assert result.deep_thinking is True

    # ── System prompt composition ────────────────────────────────────

    def test_prompt_injection_appends_to_existing(self):
        """Skill prompt is APPENDED to user's custom_prompt, not replaced."""
        data = {"custom_prompt": "Be concise."}
        overrides = SkillOverrides(
            skill_id="test",
            skill_name="Test",
            prompt_injection="=== SKILL: Test ===\nYou are a test assistant.",
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert "Be concise." in result.custom_prompt
        assert "=== SKILL: Test ===" in result.custom_prompt
        assert result.custom_prompt.startswith("Be concise.")

    def test_prompt_injection_builds_from_context(self):
        """When no custom_prompt, skill prompt is appended to context-based prompt."""
        data = {"context": "casual"}
        overrides = SkillOverrides(
            skill_id="test",
            skill_name="Test",
            prompt_injection="=== SKILL ===",
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        # The result should contain both the context-based prompt and the skill injection
        assert "=== SKILL ===" in result.custom_prompt
        # custom_prompt should not be ONLY the skill injection (it should have the base prompt too)
        assert len(result.custom_prompt) > len("=== SKILL ===")

    def test_no_prompt_injection_no_change(self):
        """When skill has no prompt_injection, custom_prompt is unchanged."""
        data = {"custom_prompt": "Hello"}
        overrides = SkillOverrides(skill_id="test", skill_name="Test")
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.custom_prompt == "Hello"

    # ── Tool gating ──────────────────────────────────────────────────

    def test_blocked_tools_removed(self):
        """Blocked tools are removed from the tools list."""
        data = {"tools": ["google-search", "saucenao", "deep-research"]}
        overrides = SkillOverrides(
            skill_id="test",
            skill_name="Test",
            blocked_tools=["saucenao"],
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert "saucenao" not in result.tools
        assert "google-search" in result.tools
        assert "deep-research" in result.tools

    def test_preferred_tools_added(self):
        """Preferred tools are added if not already present."""
        data = {"tools": ["google-search"]}
        overrides = SkillOverrides(
            skill_id="test",
            skill_name="Test",
            preferred_tools=["deep-research", "google-search"],
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert "deep-research" in result.tools
        assert result.tools.count("google-search") == 1  # no duplicates

    def test_tools_json_string_parsed(self):
        """Tools provided as a JSON string are correctly parsed."""
        data = {"tools": '["google-search", "saucenao"]'}
        overrides = SkillOverrides(
            skill_id="test",
            skill_name="Test",
            blocked_tools=["saucenao"],
        )
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert "google-search" in result.tools
        assert "saucenao" not in result.tools

    # ── Deep thinking derivation ─────────────────────────────────────

    def test_thinking_mode_deep_sets_flag(self):
        data = {"thinking_mode": "deep"}
        overrides = SkillOverrides()
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.deep_thinking is True

    def test_thinking_mode_instant_clears_flag(self):
        data = {"thinking_mode": "instant", "deep_thinking": "true"}
        overrides = SkillOverrides()
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.deep_thinking is False

    # ── Identity fields ──────────────────────────────────────────────

    def test_skill_identity_propagated(self):
        data = {}
        overrides = SkillOverrides(skill_id="my-skill", skill_name="My Skill")
        result = apply_skill_overrides(
            data=data, skill_overrides=overrides, language="vi"
        )
        assert result.skill_id == "my-skill"
        assert result.skill_name == "My Skill"
        assert result.was_applied is True
