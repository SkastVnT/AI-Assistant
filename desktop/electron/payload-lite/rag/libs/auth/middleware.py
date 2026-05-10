"""Authentication middleware — resolves AuthContext from request headers.

Supports three backends (AUTH_BACKEND env var):
    "none"    — trust x-tenant-id / x-user-id headers (dev / testing).
    "api_key" — validate x-api-key against per-tenant keys stored in DB.
    "jwt"     — placeholder for future OIDC / external IdP integration.

The resolved AuthContext is attached to request.state and available via
the ``get_auth_context`` FastAPI dependency.
"""

from __future__ import annotations

import logging
import uuid
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from libs.auth.context import AuthContext
from libs.core.models import Tenant
from libs.core.settings import AuthSettings, get_settings

logger = logging.getLogger("rag.auth")

# ── Role → max sensitivity mapping ────────────────────────────────────────
# Determines the highest sensitivity a role may see by default.
# Admins can see everything; viewers only public data.
ROLE_SENSITIVITY_CEILING: dict[str, str] = {
    "admin": "restricted",
    "editor": "confidential",
    "member": "internal",
    "viewer": "public",
}


# ── Backend: none (dev / test) ────────────────────────────────────────────


async def _authenticate_none(
    tenant_id_header: str,
    user_id_header: str | None,
    settings: AuthSettings,
    db: AsyncSession,
) -> AuthContext:
    """Trust headers without validation.  NEVER use in production."""
    try:
        tenant_id = uuid.UUID(tenant_id_header)
    except ValueError as exc:
        raise HTTPException(400, "x-tenant-id must be a valid UUID") from exc

    user_id: UUID | None = None
    role = "member"
    if user_id_header:
        try:
            user_id = uuid.UUID(user_id_header)
        except ValueError as exc:
            raise HTTPException(400, "x-user-id must be a valid UUID") from exc

    if settings.require_user_id and user_id is None:
        raise HTTPException(403, "x-user-id header is required")

    max_sensitivity = ROLE_SENSITIVITY_CEILING.get(role, "internal")
    return AuthContext(
        tenant_id=tenant_id,
        user_id=user_id,
        role=role,
        max_sensitivity=max_sensitivity,
    )


# ── Backend: api_key ──────────────────────────────────────────────────────


async def _authenticate_api_key(
    api_key: str | None,
    settings: AuthSettings,
    db: AsyncSession,
) -> AuthContext:
    """Validate API key against tenant.settings['api_keys']."""
    if not api_key:
        raise HTTPException(
            401,
            "Missing API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Look up tenant whose settings->'api_keys' array contains this key.
    # Each tenant stores: {"api_keys": [{"key": "...", "user_id": "...", "role": "..."}]}
    stmt = select(Tenant).where(
        Tenant.is_active.is_(True),
        Tenant.settings["api_keys"].astext.contains(api_key),
    )
    result = await db.execute(stmt)
    tenant = result.scalar_one_or_none()

    if tenant is None:
        raise HTTPException(
            401,
            "Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # Find matching key entry to resolve user_id and role
    user_id: UUID | None = None
    role = "member"
    for entry in tenant.settings.get("api_keys", []):
        if entry.get("key") == api_key:
            if entry.get("user_id"):
                user_id = uuid.UUID(entry["user_id"])
            role = entry.get("role", "member")
            break

    max_sensitivity = ROLE_SENSITIVITY_CEILING.get(role, "internal")
    return AuthContext(
        tenant_id=tenant.id,
        user_id=user_id,
        role=role,
        max_sensitivity=max_sensitivity,
    )


# ── Backend: jwt (placeholder) ────────────────────────────────────────────


async def _authenticate_jwt(
    authorization: str | None,
    settings: AuthSettings,
    db: AsyncSession,
) -> AuthContext:
    """Placeholder for JWT / OIDC authentication.

    Future implementation:
        1. Parse Bearer token from Authorization header.
        2. Verify signature using settings.jwt_secret or JWKS endpoint.
        3. Extract tenant_id, user_id, role from claims.
        4. Optionally look up additional permissions from SpiceDB.
    """
    raise HTTPException(
        501,
        "JWT authentication is not yet implemented. "
        "Set AUTH_BACKEND=api_key or AUTH_BACKEND=none.",
    )


# ── FastAPI dependency ────────────────────────────────────────────────────


async def get_auth_context(
    request: Request,
    db: AsyncSession = Depends(),
    x_tenant_id: str = Header(""),
    x_user_id: str | None = Header(None),
    x_api_key: str | None = Header(None),
    authorization: str | None = Header(None),
) -> AuthContext:
    """Resolve and return the AuthContext for the current request.

    Inject via `auth: AuthContext = Depends(get_auth_context)`.
    """
    settings = get_settings().auth

    if settings.backend == "none":
        if not x_tenant_id:
            raise HTTPException(400, "x-tenant-id header is required")
        ctx = await _authenticate_none(
            x_tenant_id, x_user_id, settings, db,
        )
    elif settings.backend == "api_key":
        ctx = await _authenticate_api_key(x_api_key, settings, db)
    elif settings.backend == "jwt":
        ctx = await _authenticate_jwt(authorization, settings, db)
    else:
        raise HTTPException(500, f"Unknown auth backend: {settings.backend}")

    # Attach to request state for downstream middleware / logging
    request.state.auth = ctx

    logger.debug(
        "auth ok tenant=%s user=%s role=%s backend=%s",
        ctx.tenant_id,
        ctx.user_id,
        ctx.role,
        settings.backend,
    )
    return ctx
