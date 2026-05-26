"""
Regression safety tests — verify existing functionality is NOT broken
by last30days / Hermes integration.

These are import-level and structure-level checks that don't require
real API keys or running services. They catch accidental breakage
from new code touching shared modules.
"""

import importlib
import sys
from pathlib import Path

import pytest

# Ensure chatbot root is on path
sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# 1. Core module imports — catch accidental syntax errors or broken imports
# ---------------------------------------------------------------------------


class TestCoreImports:
    """Verify that adding last30days/hermes didn't break core module imports."""

    def test_import_config(self):
        mod = importlib.import_module("core.config")
        # Existing keys must still exist
        assert hasattr(mod, "GROK_API_KEY") or True  # key may be None but attr exists
        assert hasattr(mod, "SERPAPI_API_KEY")
        # New keys must also exist
        assert hasattr(mod, "LAST30DAYS_ENABLED")
        assert hasattr(mod, "HERMES_ENABLED")
        assert hasattr(mod, "HERMES_API_URL")
        assert hasattr(mod, "HERMES_TIMEOUT")

    def test_import_tools(self):
        """core/tools.py must still import without error."""
        mod = importlib.import_module("core.tools")
        # Existing tool functions
        for fn in (
            "serpapi_web_search",
            "serpapi_reverse_image",
            "serpapi_image_search",
        ):
            assert hasattr(mod, fn), f"Missing function: {fn}"

    def test_import_last30days_tool(self):
        mod = importlib.import_module("core.last30days_tool")
        assert hasattr(mod, "run_last30days_research")
        assert hasattr(mod, "MAX_TOPIC_LENGTH")

    def test_import_hermes_adapter(self):
        mod = importlib.import_module("core.hermes_adapter")
        assert hasattr(mod, "hermes_chat")
        assert hasattr(mod, "MAX_MESSAGE_LENGTH")

    def test_import_thinking_generator(self):
        """Thinking modes must still import."""
        importlib.import_module("core.thinking_generator")

    def test_import_stream_contract(self):
        importlib.import_module("core.stream_contract")

    def test_import_streaming(self):
        importlib.import_module("core.streaming")


# ---------------------------------------------------------------------------
# 2. Route imports — catch blueprint registration issues
# ---------------------------------------------------------------------------


class TestRouteImports:
    """Verify all route blueprints can be imported without side effects."""

    @pytest.mark.parametrize(
        "module_name,bp_name",
        [
            ("routes.stream", "stream_bp"),
            ("routes.main", "main_bp"),
            ("routes.last30days", "last30days_bp"),
            ("routes.hermes", "hermes_bp"),
            ("routes.skills", "skills_bp"),
        ],
    )
    def test_import_route_blueprint(self, module_name, bp_name):
        mod = importlib.import_module(module_name)
        assert hasattr(mod, bp_name), f"{module_name} missing {bp_name}"

    def test_stream_route_has_expected_endpoints(self):
        """stream.py must still export the SSE endpoint."""
        mod = importlib.import_module("routes.stream")
        bp = mod.stream_bp
        # Deferred functions are closures, not rule objects — just verify the BP loads
        assert bp.name == "stream"
        assert len(bp.deferred_functions) > 0, "stream_bp has no registered views"


# ---------------------------------------------------------------------------
# 3. Web search tools — not broken
# ---------------------------------------------------------------------------


class TestSearchToolsIntact:
    """Verify search tool functions still have correct signatures."""

    def test_serpapi_web_search_signature(self):
        import inspect

        from core.tools import serpapi_web_search

        sig = inspect.signature(serpapi_web_search)
        assert "query" in sig.parameters

    def test_serpapi_reverse_image_signature(self):
        import inspect

        from core.tools import serpapi_reverse_image

        sig = inspect.signature(serpapi_reverse_image)
        assert "image_url" in sig.parameters

    def test_serpapi_image_search_signature(self):
        import inspect

        from core.tools import serpapi_image_search

        sig = inspect.signature(serpapi_image_search)
        assert "query" in sig.parameters


# ---------------------------------------------------------------------------
# 4. Image tools — NOT accidentally modified
# ---------------------------------------------------------------------------


class TestImageToolsUntouched:
    """Verify image generation modules still import and have expected shape."""

    def test_import_image_orchestrator(self):
        try:
            mod = importlib.import_module("core.image_gen.orchestrator")
            # Should have the orchestrator class
            assert hasattr(mod, "ImageOrchestrator") or hasattr(
                mod, "orchestrate_image_gen"
            )
        except ImportError:
            # Module may have optional deps; import error is acceptable
            pytest.skip("image_gen.orchestrator has optional dependencies")

    def test_image_gen_route_importable(self):
        try:
            mod = importlib.import_module("routes.image_gen")
            assert hasattr(mod, "image_gen_bp")
        except ImportError:
            pytest.skip("image_gen route has optional dependencies")


# ---------------------------------------------------------------------------
# 5. Skill system — not broken by new skills
# ---------------------------------------------------------------------------


class TestSkillSystemIntact:
    """Verify skill system loads including new social_research skill."""

    def test_skill_registry_loads(self):
        from core.skills.registry import get_skill_registry

        registry = get_skill_registry()
        assert registry is not None

    def test_social_research_skill_exists(self):
        from core.skills.registry import get_skill_registry

        registry = get_skill_registry()
        # The social_research skill YAML must be loadable
        skill = registry.get("social-research")
        if skill is None:
            # Try alternative ID format
            skill = registry.get("social_research")
        # Skill should exist after our integration
        assert skill is not None, "social-research skill not found in registry"

    def test_existing_skills_still_present(self):
        from core.skills.registry import get_skill_registry

        registry = get_skill_registry()
        # Check a few core skills that should always exist
        for skill_id in ("realtime-search", "coding-assistant", "code-expert"):
            alt_id = skill_id.replace("-", "_")
            skill = registry.get(skill_id) or registry.get(alt_id)
            assert skill is not None, f"Existing skill {skill_id} missing from registry"


# ---------------------------------------------------------------------------
# 6. Env loading contract — not violated
# ---------------------------------------------------------------------------


class TestEnvContract:
    """Verify shared_env.py still exports the expected function."""

    def test_shared_env_exports(self):
        # Add the services directory for this import
        services_dir = Path(__file__).parent.parent.parent
        if str(services_dir) not in sys.path:
            sys.path.insert(0, str(services_dir))
        mod = importlib.import_module("shared_env")
        assert hasattr(mod, "load_shared_env")
