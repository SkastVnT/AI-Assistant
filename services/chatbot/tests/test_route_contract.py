"""
test_route_contract.py — P1.4 Route contract regression test

Verifies that the critical route surface is present and responds with sensible
HTTP codes. A route returning 200, 400, 401, 405 is considered "present".
A 404 means the route has vanished and is a contract violation.

Some routes legitimately return 404 for non-existent resources (e.g., a GET
for an unknown conversation ID). For those, we inspect the Flask URL map
directly rather than making an HTTP call with a fake resource ID.

Marked `not integration` so it runs in the default CI gate.
The app fixture (conftest.py) sets TESTING=True + MONGODB_ENABLED=False.
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_present(status_code: int) -> bool:
    """Route is registered if the server returns anything except 404."""
    return status_code != 404


def url_map_has(client, partial_rule: str) -> bool:
    """Return True if any URL rule contains *partial_rule* as a substring."""
    return any(partial_rule in str(r) for r in client.application.url_map.iter_rules())


# ---------------------------------------------------------------------------
# Core UI / session routes
# ---------------------------------------------------------------------------


class TestCoreRoutes:
    """Routes directly on the Flask app (inline in chatbot_main.py)."""

    def test_root(self, client):
        r = client.get("/")
        assert is_present(r.status_code), "GET / must not be 404"

    def test_conversation_permalink(self, client):
        # Handler may return 404 for unknown IDs — check URL map instead.
        assert url_map_has(client, "/c/<"), "GET /c/<id> must be in URL map"

    def test_mobile(self, client):
        r = client.get("/mobile")
        assert is_present(r.status_code), "GET /mobile must not be 404"

    def test_desktop(self, client):
        r = client.get("/desktop")
        assert is_present(r.status_code), "GET /desktop must not be 404"

    def test_clear(self, client):
        r = client.post("/clear")
        assert is_present(r.status_code), "POST /clear must not be 404"

    def test_history(self, client):
        r = client.get("/history")
        assert is_present(r.status_code), "GET /history must not be 404"

    def test_chat_post_exists(self, client):
        r = client.post("/chat", json={"message": "ping", "model": "grok"})
        assert is_present(r.status_code), "POST /chat must not be 404"

    def test_generate_title(self, client):
        r = client.post("/api/generate-title", json={})
        assert is_present(r.status_code), "POST /api/generate-title must not be 404"

    def test_chat_suggestions(self, client):
        r = client.post("/api/chat/suggestions", json={})
        assert is_present(r.status_code), "POST /api/chat/suggestions must not be 404"


# ---------------------------------------------------------------------------
# Conversations routes
# ---------------------------------------------------------------------------


class TestConversationRoutes:
    def test_list_conversations(self, client):
        r = client.get("/api/conversations")
        assert is_present(r.status_code), "GET /api/conversations must not be 404"

    def test_new_conversation(self, client):
        r = client.post("/api/conversations/new", json={})
        assert is_present(r.status_code), "POST /api/conversations/new must not be 404"

    def test_get_conversation(self, client):
        # The handler returns 404 for a non-existent ID — correct REST behavior.
        # Use URL map inspection to confirm the route IS registered.
        assert url_map_has(
            client, "/api/conversations/<"
        ), "GET /api/conversations/<id> must be in URL map"

    def test_delete_conversation(self, client):
        r = client.delete("/api/conversations/some-id")
        assert is_present(
            r.status_code
        ), "DELETE /api/conversations/<id> must not be 404"

    def test_archive_conversation(self, client):
        r = client.post("/api/conversations/some-id/archive")
        assert is_present(
            r.status_code
        ), "POST /api/conversations/<id>/archive must not be 404"


# ---------------------------------------------------------------------------
# Primary streaming endpoint (SSE)
# ---------------------------------------------------------------------------


class TestStreamRoutes:
    def test_stream_endpoint_exists(self, client):
        """POST /chat/stream must be registered (stream_bp)."""
        r = client.post(
            "/chat/stream",
            json={"message": "ping", "model": "grok"},
            headers={"Accept": "text/event-stream"},
        )
        assert is_present(
            r.status_code
        ), "POST /chat/stream must not be 404 — primary SSE route"


# ---------------------------------------------------------------------------
# Health endpoints
# ---------------------------------------------------------------------------


class TestHealthRoutes:
    def test_api_v1_health(self, client):
        r = client.get("/api/v1/health")
        assert is_present(r.status_code), "GET /api/v1/health must not be 404"

    def test_db_health(self, client):
        r = client.get("/api/db-health")
        assert is_present(r.status_code), "GET /api/db-health must not be 404"


# ---------------------------------------------------------------------------
# Stable Diffusion proxy routes
# ---------------------------------------------------------------------------


class TestSDRoutes:
    def test_sd_health(self, client):
        r = client.get("/api/sd-health")
        assert is_present(r.status_code), "GET /api/sd-health must not be 404"

    def test_sd_models(self, client):
        r = client.get("/api/sd-models")
        assert is_present(r.status_code), "GET /api/sd-models must not be 404"

    def test_sd_samplers(self, client):
        r = client.get("/api/sd-samplers")
        assert is_present(r.status_code), "GET /api/sd-samplers must not be 404"


# ---------------------------------------------------------------------------
# Skills blueprint (/api/skills/*)
# ---------------------------------------------------------------------------


class TestSkillsRoutes:
    def test_list_skills(self, client):
        r = client.get("/api/skills")
        assert is_present(r.status_code), "GET /api/skills must not be 404"

    def test_active_skill(self, client):
        r = client.get("/api/skills/active")
        assert is_present(r.status_code), "GET /api/skills/active must not be 404"


# ---------------------------------------------------------------------------
# MCP routes
# ---------------------------------------------------------------------------


class TestMCPRoutes:
    def test_mcp_status(self, client):
        r = client.get("/api/mcp/status")
        assert is_present(r.status_code), "GET /api/mcp/status must not be 404"


# ---------------------------------------------------------------------------
# Memory routes
# ---------------------------------------------------------------------------


class TestMemoryRoutes:
    def test_memory_list(self, client):
        r = client.get("/memory/list")
        # memory_bp is registered with url_prefix='/memory'
        assert is_present(r.status_code), "GET /memory/list must not be 404"

    def test_inline_memory_list(self, client):
        r = client.get("/api/memory/list")
        # Also registered inline in chatbot_main.py at /api/memory/*
        assert is_present(r.status_code), "GET /api/memory/list must not be 404"


# ---------------------------------------------------------------------------
# v1 API routes
# ---------------------------------------------------------------------------


class TestV1Routes:
    def test_v1_providers(self, client):
        r = client.get("/api/v1/providers")
        assert is_present(r.status_code), "GET /api/v1/providers must not be 404"

    def test_v1_chat_exists(self, client):
        r = client.post("/api/v1/chat", json={"message": "ping"})
        assert is_present(r.status_code), "POST /api/v1/chat must not be 404"
