"""Safety model — delegated authorization + budget guards + content checks.

The agent must never exceed the permissions of the calling user.
This module enforces:
1. Delegated auth: tool calls inherit the original AuthContext
2. Budget guards: iteration, token, and tool-call limits
3. Task-level content checks: reject clearly unsafe tasks before execution
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from libs.agent.types import AgentConfig, AgentState, StopReason

if TYPE_CHECKING:
    from libs.auth.context import AuthContext

logger = logging.getLogger("rag.agent.safety")


# ═══════════════════════════════════════════════════════════════════════
# Delegated authorization token
# ═══════════════════════════════════════════════════════════════════════


@dataclass(frozen=True)
class DelegatedAuth:
    """Immutable authorization scope derived from the caller's AuthContext.

    Every tool invocation receives this instead of raw AuthContext, ensuring
    the agent cannot escalate permissions. The scope can only be equal to
    or narrower than the original context.

    Attributes
    ----------
    tenant_id:
        The tenant boundary — all queries scoped to this tenant.
    user_id:
        The user performing the request.
    role:
        The user's role (admin | editor | member | viewer).
    max_sensitivity:
        Highest data sensitivity the user can access.
    allowed_tools:
        Subset of tools this user's role permits.
    permissions:
        Frozen set of specific permissions (from AuthContext).
    """

    tenant_id: object  # UUID
    user_id: object    # UUID | None
    role: str
    max_sensitivity: str
    allowed_tools: frozenset[str]
    permissions: frozenset[str]


# Role → allowed tools mapping
ROLE_TOOL_ALLOWLIST: dict[str, frozenset[str]] = {
    "admin": frozenset({"retriever", "web_search", "python", "policy_check"}),
    "editor": frozenset({"retriever", "web_search", "policy_check"}),
    "member": frozenset({"retriever", "policy_check"}),
    "viewer": frozenset({"retriever"}),
}


def create_delegated_auth(auth: AuthContext) -> DelegatedAuth:
    """Derive a DelegatedAuth from the caller's AuthContext.

    The allowed_tools set is determined by the user's role.
    """
    allowed = ROLE_TOOL_ALLOWLIST.get(auth.role, frozenset({"retriever"}))
    return DelegatedAuth(
        tenant_id=auth.tenant_id,
        user_id=auth.user_id,
        role=auth.role,
        max_sensitivity=auth.max_sensitivity,
        allowed_tools=allowed,
        permissions=auth.permissions,
    )


def is_tool_allowed(delegated: DelegatedAuth, tool_name: str) -> bool:
    """Check if the delegated auth scope permits calling this tool."""
    return tool_name in delegated.allowed_tools


# ═══════════════════════════════════════════════════════════════════════
# Budget guards
# ═══════════════════════════════════════════════════════════════════════


@dataclass
class BudgetCheckResult:
    """Result of a budget check."""

    allowed: bool
    reason: str = ""


def check_budget(state: AgentState, config: AgentConfig) -> BudgetCheckResult:
    """Check whether the agent has budget remaining.

    Returns allowed=False with a reason if any limit is exceeded.
    """
    if state.iteration >= config.max_iterations:
        return BudgetCheckResult(
            allowed=False,
            reason=f"Max iterations reached ({config.max_iterations})",
        )
    if state.total_tool_calls >= config.max_tool_calls:
        return BudgetCheckResult(
            allowed=False,
            reason=f"Max tool calls reached ({config.max_tool_calls})",
        )
    if state.total_tokens_used >= config.max_tokens:
        return BudgetCheckResult(
            allowed=False,
            reason=f"Token budget exhausted ({config.max_tokens})",
        )
    return BudgetCheckResult(allowed=True)


def get_stop_reason_for_budget(state: AgentState, config: AgentConfig) -> StopReason:
    """Map a budget violation to the appropriate StopReason."""
    if state.iteration >= config.max_iterations:
        return StopReason.MAX_ITERATIONS
    if state.total_tokens_used >= config.max_tokens:
        return StopReason.MAX_TOKENS
    return StopReason.ERROR


# ═══════════════════════════════════════════════════════════════════════
# Task-level content screening
# ═══════════════════════════════════════════════════════════════════════

# Patterns that indicate unsafe / out-of-scope tasks
_BLOCKED_PATTERNS: list[re.Pattern] = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions", re.IGNORECASE),
    re.compile(r"(system|admin)\s+prompt", re.IGNORECASE),
    re.compile(r"bypass\s+(security|auth|guardrail)", re.IGNORECASE),
    re.compile(r"execute\s+(shell|bash|cmd|powershell)", re.IGNORECASE),
    re.compile(r"delete\s+(all|every|database|table)", re.IGNORECASE),
]


@dataclass
class ScreeningResult:
    """Result of the task-level content screening."""

    allowed: bool
    blocked_reason: str = ""


def screen_task(query: str) -> ScreeningResult:
    """Screen the user's task for prompt injection or unsafe intent.

    This is a lightweight pre-check. The full guardrail pipeline still
    runs on retrieved evidence and generated answers.
    """
    for pattern in _BLOCKED_PATTERNS:
        if pattern.search(query):
            logger.warning("task_blocked: pattern=%s query=%r", pattern.pattern, query[:100])
            return ScreeningResult(
                allowed=False,
                blocked_reason=f"Task matches blocked pattern: {pattern.pattern}",
            )
    return ScreeningResult(allowed=True)
