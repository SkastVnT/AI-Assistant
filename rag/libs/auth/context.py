"""Authenticated request context.

AuthContext is a frozen data class that flows through every layer.
It is created once by the auth middleware and never mutated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID


@dataclass(frozen=True)
class AuthContext:
    """Immutable authentication + authorization identity for one request.

    Attributes:
        tenant_id:   The verified tenant boundary for this request.
        user_id:     Verified user identity (None when auth is 'none' and
                     x-user-id is omitted).
        role:        User role within the tenant (e.g. admin, member, viewer).
        permissions: Arbitrary permission set — populated by authz provider.
                     Default is empty.  Future ReBAC / SpiceDB will fill this.
        max_sensitivity: Highest sensitivity level this user may access.
                     Pre-filter authorization uses this to cap retrieval.
        extra:       Extensible bag for provider-specific claims (JWT iss/aud,
                     API-key scopes, SpiceDB relationships, etc.).
    """

    tenant_id: UUID
    user_id: UUID | None = None
    role: str = "member"
    permissions: frozenset[str] = field(default_factory=frozenset)
    max_sensitivity: str = "internal"
    extra: dict = field(default_factory=dict)

    # ── Convenience predicates ─────────────────────────────────────────

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"

    def has_permission(self, perm: str) -> bool:
        return perm in self.permissions

    def can_access_sensitivity(self, level: str) -> bool:
        """Check whether the user's max_sensitivity is >= the given level."""
        return _SENSITIVITY_RANK.get(
            self.max_sensitivity, 0,
        ) >= _SENSITIVITY_RANK.get(level, 99)


# Ordered mapping: higher rank → broader access.
_SENSITIVITY_RANK: dict[str, int] = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}
