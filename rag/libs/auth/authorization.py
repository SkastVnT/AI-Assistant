"""Authorization filter protocols and default implementations.

Two extension points designed for easy swap to ReBAC / SpiceDB:

    PreFilterAuthorization  — narrows the DB query BEFORE retrieval.
    PostFilterAuthorization — drops results AFTER retrieval (defense-in-depth).

Default implementations use the ``AuthContext.max_sensitivity`` field
(derived from the user's role) to enforce sensitivity-level gating.

┌──────────────────────────────────────────────────────────────────────┐
│ Migration path to SpiceDB / ReBAC:                                  │
│                                                                     │
│ 1. Implement SpiceDBPreFilter that calls                            │
│    SpiceDB LookupResources to get allowed document IDs.             │
│ 2. Implement SpiceDBPostFilter that calls                           │
│    SpiceDB CheckPermission per chunk.                               │
│ 3. Register them in the DI container (dependencies.py).             │
│ 4. The rest of the code stays unchanged — same Protocol interface.  │
│                                                                     │
│ Patterns supported:                                                 │
│   Pool  — shared DB, row-level tenant_id (current)                  │
│   Bridge — shared DB, separate schemas per tenant                   │
│   Silo  — dedicated DB per tenant                                   │
│   ReBAC — SpiceDB relationship graph for fine-grained authz         │
└──────────────────────────────────────────────────────────────────────┘
"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from libs.auth.context import AuthContext
from libs.retrieval.search import SearchFilters, SearchResult

logger = logging.getLogger("rag.authz")


# ── Sensitivity level ordering ─────────────────────────────────────────────

_SENSITIVITY_RANK: dict[str, int] = {
    "public": 0,
    "internal": 1,
    "confidential": 2,
    "restricted": 3,
}

# Inverse: ceiling → set of allowed levels at or below that ceiling.
_ALLOWED_LEVELS: dict[str, list[str]] = {}
for _ceiling, _ceiling_rank in _SENSITIVITY_RANK.items():
    _ALLOWED_LEVELS[_ceiling] = [
        level for level, rank in _SENSITIVITY_RANK.items()
        if rank <= _ceiling_rank
    ]


# ── Protocol: PreFilterAuthorization ───────────────────────────────────────


@runtime_checkable
class PreFilterAuthorization(Protocol):
    """Narrows search filters BEFORE the retrieval query executes.

    Implementations MUST:
      - Enforce tenant_id (never return filters that cross tenants).
      - Return a SearchFilters whose sensitivity_level is capped by
        the caller's max_sensitivity.
      - NOT raise on valid calls — return a restrictive filter instead.

    To swap for SpiceDB:
        class SpiceDBPreFilter:
            async def apply(self, auth, filters):
                allowed_ids = await spicedb.lookup_resources(
                    "document", "view", auth.user_id)
                return filters | SearchFilters(source_ids=allowed_ids)
    """

    async def apply(
        self,
        auth: AuthContext,
        filters: SearchFilters | None,
    ) -> SearchFilters: ...


# ── Protocol: PostFilterAuthorization ──────────────────────────────────────


@runtime_checkable
class PostFilterAuthorization(Protocol):
    """Drops search results AFTER retrieval — defense-in-depth.

    Implementations MUST:
      - Verify every chunk belongs to auth.tenant_id.
      - Drop chunks whose sensitivity exceeds auth.max_sensitivity.
      - Never add results that weren't in the input.

    To swap for SpiceDB:
        class SpiceDBPostFilter:
            async def apply(self, auth, results):
                checks = await spicedb.batch_check(
                    [(auth.user_id, "view", r.chunk_id) for r in results])
                return [r for r, ok in zip(results, checks) if ok]
    """

    async def apply(
        self,
        auth: AuthContext,
        results: list[SearchResult],
    ) -> list[SearchResult]: ...


# ── Default: SensitivityPreFilter ──────────────────────────────────────────


class SensitivityPreFilter:
    """Pre-filter that caps sensitivity_level based on the user's role.

    If the caller's requested sensitivity is higher than their ceiling,
    it is silently capped down.  If no sensitivity was requested, the
    ceiling is applied automatically.
    """

    async def apply(
        self,
        auth: AuthContext,
        filters: SearchFilters | None,
    ) -> SearchFilters:
        ceiling = auth.max_sensitivity
        allowed = _ALLOWED_LEVELS.get(ceiling, ["public"])

        if filters is None or filters.sensitivity_level is None:
            effective_sensitivity = ceiling
        elif filters.sensitivity_level in allowed:
            effective_sensitivity = filters.sensitivity_level
        else:
            # Requested sensitivity exceeds ceiling → cap down
            logger.warning(
                "authz: user %s requested sensitivity=%s but ceiling=%s; "
                "capping to %s",
                auth.user_id,
                filters.sensitivity_level,
                ceiling,
                ceiling,
            )
            effective_sensitivity = ceiling

        base = filters or SearchFilters()
        return SearchFilters(
            sensitivity_level=effective_sensitivity,
            language=base.language,
            tags=base.tags,
            data_source_id=base.data_source_id,
            source_ids=base.source_ids,
        )


# ── Default: SensitivityPostFilter ────────────────────────────────────────


class SensitivityPostFilter:
    """Post-filter that drops results exceeding the user's sensitivity ceiling.

    Also enforces tenant isolation: any result whose metadata suggests a
    different tenant is silently dropped (should never happen if the DB
    query is correct, but defense-in-depth).
    """

    async def apply(
        self,
        auth: AuthContext,
        results: list[SearchResult],
    ) -> list[SearchResult]:
        allowed = set(_ALLOWED_LEVELS.get(auth.max_sensitivity, ["public"]))
        filtered: list[SearchResult] = []
        dropped = 0

        for r in results:
            if r.sensitivity_level not in allowed:
                dropped += 1
                continue
            filtered.append(r)

        if dropped:
            logger.info(
                "authz post-filter: dropped %d chunks exceeding "
                "sensitivity ceiling=%s for user=%s",
                dropped,
                auth.max_sensitivity,
                auth.user_id,
            )
        return filtered
