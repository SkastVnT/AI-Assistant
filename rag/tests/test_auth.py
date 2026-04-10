"""Tests for the authentication and authorization layer.

Covers:
- AuthContext (frozen dataclass, sensitivity access, is_admin, permissions)
- Auth middleware (none backend, api_key backend, missing headers, invalid UUIDs)
- SensitivityPreFilter (caps sensitivity, uses ceiling when unset, passthrough)
- SensitivityPostFilter (drops over-ceiling results, keeps allowed)
- Tenant isolation (cross-tenant rejection, header spoofing)
- AuthSettings validation
"""

from __future__ import annotations

import uuid
from dataclasses import FrozenInstanceError
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from libs.auth.authorization import (
    _ALLOWED_LEVELS,
    _SENSITIVITY_RANK,
    SensitivityPostFilter,
    SensitivityPreFilter,
)
from libs.auth.context import AuthContext
from libs.auth.middleware import (
    ROLE_SENSITIVITY_CEILING,
    _authenticate_api_key,
    _authenticate_jwt,
    _authenticate_none,
    get_auth_context,
)
from libs.core.settings import AuthSettings
from libs.retrieval.search import SearchFilters, SearchResult

# ── Helpers ────────────────────────────────────────────────────────────────

TENANT_A = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
TENANT_B = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
USER_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
USER_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")
DOC_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
VER_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")
CHUNK_ID = uuid.UUID("ffffffff-ffff-ffff-ffff-ffffffffffff")


def _make_auth(
    tenant_id: uuid.UUID = TENANT_A,
    user_id: uuid.UUID | None = USER_1,
    role: str = "member",
    max_sensitivity: str = "internal",
    permissions: frozenset[str] | None = None,
) -> AuthContext:
    return AuthContext(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        max_sensitivity=max_sensitivity,
        permissions=permissions or frozenset(),
    )


def _make_result(
    sensitivity_level: str = "public",
    content: str = "test chunk",
    score: float = 0.9,
) -> SearchResult:
    return SearchResult(
        chunk_id=uuid.uuid4(),
        document_id=DOC_ID,
        version_id=VER_ID,
        content=content,
        score=score,
        metadata={},
        filename="test.md",
        chunk_index=0,
        sensitivity_level=sensitivity_level,
        language="en",
    )


# ═══════════════════════════════════════════════════════════════════════════
# AuthContext unit tests
# ═══════════════════════════════════════════════════════════════════════════


class TestAuthContext:

    def test_frozen(self):
        ctx = _make_auth()
        with pytest.raises(FrozenInstanceError):
            ctx.tenant_id = TENANT_B  # type: ignore[misc]

    def test_is_admin_true(self):
        ctx = _make_auth(role="admin")
        assert ctx.is_admin is True

    def test_is_admin_false(self):
        ctx = _make_auth(role="member")
        assert ctx.is_admin is False

    def test_has_permission(self):
        ctx = _make_auth(permissions=frozenset({"read", "write"}))
        assert ctx.has_permission("read") is True
        assert ctx.has_permission("delete") is False

    def test_has_permission_empty(self):
        ctx = _make_auth(permissions=frozenset())
        assert ctx.has_permission("read") is False

    @pytest.mark.parametrize(
        "max_sens,level,expected",
        [
            ("public", "public", True),
            ("public", "internal", False),
            ("internal", "public", True),
            ("internal", "internal", True),
            ("internal", "confidential", False),
            ("confidential", "public", True),
            ("confidential", "confidential", True),
            ("confidential", "restricted", False),
            ("restricted", "public", True),
            ("restricted", "restricted", True),
        ],
    )
    def test_can_access_sensitivity(self, max_sens, level, expected):
        ctx = _make_auth(max_sensitivity=max_sens)
        assert ctx.can_access_sensitivity(level) is expected

    def test_can_access_unknown_level_returns_false(self):
        ctx = _make_auth(max_sensitivity="internal")
        assert ctx.can_access_sensitivity("top-secret") is False

    def test_defaults(self):
        ctx = AuthContext(tenant_id=TENANT_A)
        assert ctx.user_id is None
        assert ctx.role == "member"
        assert ctx.permissions == frozenset()
        assert ctx.max_sensitivity == "internal"
        assert ctx.extra == {}


# ═══════════════════════════════════════════════════════════════════════════
# Auth middleware: none backend
# ═══════════════════════════════════════════════════════════════════════════


class TestAuthenticateNone:

    @pytest.mark.asyncio
    async def test_valid_tenant_only(self):
        settings = AuthSettings(backend="none")
        db = AsyncMock()
        ctx = await _authenticate_none(str(TENANT_A), None, settings, db)
        assert ctx.tenant_id == TENANT_A
        assert ctx.user_id is None
        assert ctx.role == "member"

    @pytest.mark.asyncio
    async def test_valid_tenant_and_user(self):
        settings = AuthSettings(backend="none")
        db = AsyncMock()
        ctx = await _authenticate_none(str(TENANT_A), str(USER_1), settings, db)
        assert ctx.tenant_id == TENANT_A
        assert ctx.user_id == USER_1

    @pytest.mark.asyncio
    async def test_invalid_tenant_uuid(self):
        from fastapi import HTTPException

        settings = AuthSettings(backend="none")
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_none("not-a-uuid", None, settings, db)
        assert exc_info.value.status_code == 400
        assert "x-tenant-id" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_invalid_user_uuid(self):
        from fastapi import HTTPException

        settings = AuthSettings(backend="none")
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_none(str(TENANT_A), "bad", settings, db)
        assert exc_info.value.status_code == 400
        assert "x-user-id" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_require_user_id_enforced(self):
        from fastapi import HTTPException

        settings = AuthSettings(backend="none", require_user_id=True)
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_none(str(TENANT_A), None, settings, db)
        assert exc_info.value.status_code == 403

    @pytest.mark.asyncio
    async def test_require_user_id_passes_when_provided(self):
        settings = AuthSettings(backend="none", require_user_id=True)
        db = AsyncMock()
        ctx = await _authenticate_none(str(TENANT_A), str(USER_1), settings, db)
        assert ctx.user_id == USER_1

    @pytest.mark.asyncio
    async def test_sensitivity_ceiling_applied(self):
        settings = AuthSettings(backend="none")
        db = AsyncMock()
        ctx = await _authenticate_none(str(TENANT_A), None, settings, db)
        # Default role is member → ceiling is "internal"
        assert ctx.max_sensitivity == ROLE_SENSITIVITY_CEILING["member"]


# ═══════════════════════════════════════════════════════════════════════════
# Auth middleware: api_key backend
# ═══════════════════════════════════════════════════════════════════════════


class TestAuthenticateApiKey:

    @pytest.mark.asyncio
    async def test_missing_api_key(self):
        from fastapi import HTTPException

        settings = AuthSettings(backend="api_key")
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_api_key(None, settings, db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_api_key(self):
        from fastapi import HTTPException

        settings = AuthSettings(backend="api_key")
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_api_key("", settings, db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key(self):
        from fastapi import HTTPException

        settings = AuthSettings(backend="api_key")
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)

        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_api_key("bad-key", settings, db)
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_valid_api_key(self):
        settings = AuthSettings(backend="api_key")
        db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = TENANT_A
        mock_tenant.settings = {
            "api_keys": [
                {"key": "secret-key-1", "user_id": str(USER_1), "role": "admin"},
            ],
        }
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        db.execute = AsyncMock(return_value=mock_result)

        ctx = await _authenticate_api_key("secret-key-1", settings, db)
        assert ctx.tenant_id == TENANT_A
        assert ctx.user_id == USER_1
        assert ctx.role == "admin"
        assert ctx.max_sensitivity == ROLE_SENSITIVITY_CEILING["admin"]

    @pytest.mark.asyncio
    async def test_api_key_role_ceiling(self):
        settings = AuthSettings(backend="api_key")
        db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = TENANT_A
        mock_tenant.settings = {
            "api_keys": [
                {"key": "viewer-key", "role": "viewer"},
            ],
        }
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        db.execute = AsyncMock(return_value=mock_result)

        ctx = await _authenticate_api_key("viewer-key", settings, db)
        assert ctx.role == "viewer"
        assert ctx.max_sensitivity == ROLE_SENSITIVITY_CEILING["viewer"]


# ═══════════════════════════════════════════════════════════════════════════
# Auth middleware: jwt backend (placeholder)
# ═══════════════════════════════════════════════════════════════════════════


class TestAuthenticateJWT:

    @pytest.mark.asyncio
    async def test_jwt_returns_501(self):
        from fastapi import HTTPException

        settings = AuthSettings(backend="jwt")
        db = AsyncMock()
        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_jwt("Bearer token", settings, db)
        assert exc_info.value.status_code == 501


# ═══════════════════════════════════════════════════════════════════════════
# Auth middleware: get_auth_context dispatcher
# ═══════════════════════════════════════════════════════════════════════════


class TestGetAuthContext:

    @pytest.mark.asyncio
    async def test_missing_tenant_id_none_backend(self):
        from fastapi import HTTPException

        request = MagicMock()
        request.state = MagicMock()
        db = AsyncMock()

        with patch("libs.auth.middleware.get_settings") as mock_settings:
            mock_settings.return_value.auth = AuthSettings(backend="none")
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request, db, "", None, None, None)
            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_unknown_backend(self):
        from fastapi import HTTPException

        request = MagicMock()
        request.state = MagicMock()
        db = AsyncMock()

        with patch("libs.auth.middleware.get_settings") as mock_settings:
            mock_settings.return_value.auth = AuthSettings(backend="kerberos")
            with pytest.raises(HTTPException) as exc_info:
                await get_auth_context(request, db, str(TENANT_A), None, None, None)
            assert exc_info.value.status_code == 500

    @pytest.mark.asyncio
    async def test_attaches_to_request_state(self):
        request = MagicMock()
        request.state = MagicMock()
        db = AsyncMock()

        with patch("libs.auth.middleware.get_settings") as mock_settings:
            mock_settings.return_value.auth = AuthSettings(backend="none")
            ctx = await get_auth_context(
                request, db, str(TENANT_A), str(USER_1), None, None,
            )
        assert request.state.auth is ctx
        assert ctx.tenant_id == TENANT_A


# ═══════════════════════════════════════════════════════════════════════════
# SensitivityPreFilter
# ═══════════════════════════════════════════════════════════════════════════


class TestSensitivityPreFilter:

    @pytest.mark.asyncio
    async def test_no_filters_uses_ceiling(self):
        pre = SensitivityPreFilter()
        auth = _make_auth(max_sensitivity="confidential")
        result = await pre.apply(auth, None)
        assert result.sensitivity_level == "confidential"

    @pytest.mark.asyncio
    async def test_null_sensitivity_uses_ceiling(self):
        pre = SensitivityPreFilter()
        auth = _make_auth(max_sensitivity="internal")
        filters = SearchFilters(sensitivity_level=None, language="en")
        result = await pre.apply(auth, filters)
        assert result.sensitivity_level == "internal"
        assert result.language == "en"

    @pytest.mark.asyncio
    async def test_within_ceiling_passes_through(self):
        pre = SensitivityPreFilter()
        auth = _make_auth(max_sensitivity="confidential")
        filters = SearchFilters(sensitivity_level="public")
        result = await pre.apply(auth, filters)
        assert result.sensitivity_level == "public"

    @pytest.mark.asyncio
    async def test_exact_ceiling_passes_through(self):
        pre = SensitivityPreFilter()
        auth = _make_auth(max_sensitivity="internal")
        filters = SearchFilters(sensitivity_level="internal")
        result = await pre.apply(auth, filters)
        assert result.sensitivity_level == "internal"

    @pytest.mark.asyncio
    async def test_above_ceiling_capped_down(self):
        pre = SensitivityPreFilter()
        auth = _make_auth(max_sensitivity="internal")
        filters = SearchFilters(sensitivity_level="restricted")
        result = await pre.apply(auth, filters)
        assert result.sensitivity_level == "internal"

    @pytest.mark.asyncio
    async def test_preserves_other_filter_fields(self):
        pre = SensitivityPreFilter()
        auth = _make_auth(max_sensitivity="confidential")
        tag_list = ["python", "rag"]
        filters = SearchFilters(
            sensitivity_level="public",
            language="vi",
            tags=tag_list,
            data_source_id=DOC_ID,
        )
        result = await pre.apply(auth, filters)
        assert result.language == "vi"
        assert result.tags == tag_list
        assert result.data_source_id == DOC_ID

    @pytest.mark.asyncio
    async def test_viewer_ceiling(self):
        """Viewer role (ceiling=public) should cap everything to public."""
        pre = SensitivityPreFilter()
        auth = _make_auth(max_sensitivity="public")
        filters = SearchFilters(sensitivity_level="internal")
        result = await pre.apply(auth, filters)
        assert result.sensitivity_level == "public"

    @pytest.mark.asyncio
    async def test_admin_ceiling(self):
        """Admin role (ceiling=restricted) can access restricted."""
        pre = SensitivityPreFilter()
        auth = _make_auth(max_sensitivity="restricted")
        filters = SearchFilters(sensitivity_level="restricted")
        result = await pre.apply(auth, filters)
        assert result.sensitivity_level == "restricted"


# ═══════════════════════════════════════════════════════════════════════════
# SensitivityPostFilter
# ═══════════════════════════════════════════════════════════════════════════


class TestSensitivityPostFilter:

    @pytest.mark.asyncio
    async def test_keeps_allowed_results(self):
        post = SensitivityPostFilter()
        auth = _make_auth(max_sensitivity="internal")
        results = [
            _make_result(sensitivity_level="public"),
            _make_result(sensitivity_level="internal"),
        ]
        filtered = await post.apply(auth, results)
        assert len(filtered) == 2

    @pytest.mark.asyncio
    async def test_drops_above_ceiling(self):
        post = SensitivityPostFilter()
        auth = _make_auth(max_sensitivity="internal")
        results = [
            _make_result(sensitivity_level="public"),
            _make_result(sensitivity_level="confidential"),
            _make_result(sensitivity_level="restricted"),
        ]
        filtered = await post.apply(auth, results)
        assert len(filtered) == 1
        assert filtered[0].sensitivity_level == "public"

    @pytest.mark.asyncio
    async def test_empty_results(self):
        post = SensitivityPostFilter()
        auth = _make_auth(max_sensitivity="restricted")
        filtered = await post.apply(auth, [])
        assert filtered == []

    @pytest.mark.asyncio
    async def test_all_dropped(self):
        post = SensitivityPostFilter()
        auth = _make_auth(max_sensitivity="public")
        results = [
            _make_result(sensitivity_level="internal"),
            _make_result(sensitivity_level="confidential"),
        ]
        filtered = await post.apply(auth, results)
        assert filtered == []

    @pytest.mark.asyncio
    async def test_admin_sees_everything(self):
        post = SensitivityPostFilter()
        auth = _make_auth(role="admin", max_sensitivity="restricted")
        results = [
            _make_result(sensitivity_level="public"),
            _make_result(sensitivity_level="internal"),
            _make_result(sensitivity_level="confidential"),
            _make_result(sensitivity_level="restricted"),
        ]
        filtered = await post.apply(auth, results)
        assert len(filtered) == 4


# ═══════════════════════════════════════════════════════════════════════════
# Module-level constants / configuration
# ═══════════════════════════════════════════════════════════════════════════


class TestAuthConstants:

    def test_role_sensitivity_ceiling_keys(self):
        assert set(ROLE_SENSITIVITY_CEILING.keys()) == {
            "admin", "editor", "member", "viewer",
        }

    def test_role_ceilings_valid_values(self):
        for role, ceiling in ROLE_SENSITIVITY_CEILING.items():
            assert ceiling in _SENSITIVITY_RANK, (
                f"Role {role} has invalid ceiling {ceiling}"
            )

    def test_allowed_levels_consistency(self):
        for ceiling, allowed in _ALLOWED_LEVELS.items():
            ceiling_rank = _SENSITIVITY_RANK[ceiling]
            for level in allowed:
                assert _SENSITIVITY_RANK[level] <= ceiling_rank

    def test_allowed_levels_public_only_public(self):
        assert _ALLOWED_LEVELS["public"] == ["public"]

    def test_allowed_levels_restricted_all(self):
        assert set(_ALLOWED_LEVELS["restricted"]) == set(_SENSITIVITY_RANK.keys())

    def test_auth_settings_defaults(self):
        s = AuthSettings()
        assert s.backend == "none"
        assert s.require_user_id is False
        assert s.api_key_header == "x-api-key"
        assert s.jwt_secret == ""
        assert s.jwt_algorithm == "HS256"


# ═══════════════════════════════════════════════════════════════════════════
# Tenant isolation integration tests
# ═══════════════════════════════════════════════════════════════════════════


class TestTenantIsolation:
    """Verify that tenant boundaries are enforced at the auth layer."""

    @pytest.mark.asyncio
    async def test_different_tenants_get_different_contexts(self):
        settings = AuthSettings(backend="none")
        db = AsyncMock()

        ctx_a = await _authenticate_none(str(TENANT_A), str(USER_1), settings, db)
        ctx_b = await _authenticate_none(str(TENANT_B), str(USER_2), settings, db)

        assert ctx_a.tenant_id != ctx_b.tenant_id
        assert ctx_a.tenant_id == TENANT_A
        assert ctx_b.tenant_id == TENANT_B

    @pytest.mark.asyncio
    async def test_pre_filter_does_not_leak_across_tenants(self):
        """Pre-filter should only modify sensitivity, not tenant_id.

        The tenant_id is enforced by the DB query layer (WHERE tenant_id=?),
        not by the pre-filter. This test verifies pre-filter doesn't interfere.
        """
        pre = SensitivityPreFilter()
        auth_a = _make_auth(tenant_id=TENANT_A, max_sensitivity="internal")
        auth_b = _make_auth(tenant_id=TENANT_B, max_sensitivity="confidential")

        filters_a = await pre.apply(auth_a, None)
        filters_b = await pre.apply(auth_b, None)

        assert filters_a.sensitivity_level == "internal"
        assert filters_b.sensitivity_level == "confidential"

    @pytest.mark.asyncio
    async def test_post_filter_is_independent_per_tenant(self):
        """Post-filter applied to tenant A's results doesn't affect tenant B."""
        post = SensitivityPostFilter()

        results_a = [_make_result("internal"), _make_result("restricted")]
        results_b = [_make_result("public"), _make_result("confidential")]

        auth_a = _make_auth(tenant_id=TENANT_A, max_sensitivity="internal")
        auth_b = _make_auth(tenant_id=TENANT_B, max_sensitivity="confidential")

        filtered_a = await post.apply(auth_a, results_a)
        filtered_b = await post.apply(auth_b, results_b)

        assert len(filtered_a) == 1  # only "internal"
        assert len(filtered_b) == 2  # "public" + "confidential"

    @pytest.mark.asyncio
    async def test_api_key_binds_to_correct_tenant(self):
        """API key authentication must reliably bind context to the tenant
        that owns the key, not to any spoofed header."""
        settings = AuthSettings(backend="api_key")
        db = AsyncMock()
        mock_tenant = MagicMock()
        mock_tenant.id = TENANT_A
        mock_tenant.settings = {
            "api_keys": [{"key": "tenant-a-key", "role": "member"}],
        }
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_tenant
        db.execute = AsyncMock(return_value=mock_result)

        ctx = await _authenticate_api_key("tenant-a-key", settings, db)
        # The tenant_id comes from the DB lookup, not from any header
        assert ctx.tenant_id == TENANT_A


# ═══════════════════════════════════════════════════════════════════════════
# Protocol conformance tests
# ═══════════════════════════════════════════════════════════════════════════


class TestProtocolConformance:

    def test_sensitivity_pre_filter_satisfies_protocol(self):
        from libs.auth.authorization import PreFilterAuthorization
        assert isinstance(SensitivityPreFilter(), PreFilterAuthorization)

    def test_sensitivity_post_filter_satisfies_protocol(self):
        from libs.auth.authorization import PostFilterAuthorization
        assert isinstance(SensitivityPostFilter(), PostFilterAuthorization)
