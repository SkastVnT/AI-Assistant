"""
Agentic Council — Configuration
================================
Runtime configuration for the council orchestrator and its agents.

All values have sensible defaults so the system works out-of-the-box.
The ``CouncilConfig`` Pydantic model is designed to be sent by the
client as an optional field on ``ChatRequest``.

Default model assignments come from ``model_resolver.ROLE_FALLBACK_CHAINS``
(first entry in each chain).  At runtime the resolver picks the first
*available* model — see :func:`model_resolver.resolve_model`.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from core.agentic.contracts import AgentRole
from core.agentic.model_resolver import ROLE_FALLBACK_CHAINS


# ── Per-agent model mapping ────────────────────────────────────────────

DEFAULT_AGENT_MODELS: dict[AgentRole, str] = {
    role: chain[0] for role, chain in ROLE_FALLBACK_CHAINS.items()
}
"""Default LLM model name used by each agent role.

Derived from the *first* entry in each resolver fallback chain:
  planner → openai,  researcher → gemini,
  critic → grok,     synthesizer → stepfun.
"""


# ── Client-facing config ───────────────────────────────────────────────

class CouncilConfig(BaseModel):
    """Optional overrides sent by the client inside ``ChatRequest``.

    Every field has a default so the client can simply send
    ``{"agent_mode": "council"}`` without any ``council_config``.
    """
    max_rounds: int = Field(
        2,
        ge=1,
        le=5,
        description="Maximum Planner→Researcher→Critic rounds before forced synthesis",
    )
    quality_threshold: int = Field(
        7,
        ge=1,
        le=10,
        description="Minimum Critic quality_score to skip additional rounds",
    )

    # Per-role model overrides (keys from ModelRegistry)
    planner_model: str = Field(
        default_factory=lambda: DEFAULT_AGENT_MODELS[AgentRole.planner],
        description="Model for the Planner agent",
    )
    researcher_model: str = Field(
        default_factory=lambda: DEFAULT_AGENT_MODELS[AgentRole.researcher],
        description="Model for the Researcher agent",
    )
    critic_model: str = Field(
        default_factory=lambda: DEFAULT_AGENT_MODELS[AgentRole.critic],
        description="Model for the Critic agent",
    )
    synthesizer_model: str = Field(
        default_factory=lambda: DEFAULT_AGENT_MODELS[AgentRole.synthesizer],
        description="Model for the Synthesizer agent",
    )

    # Feature toggles
    enable_tools: bool = Field(True, description="Allow Researcher to call tools (web search, etc.)")
    enable_rag: bool = Field(True, description="Allow Researcher to query RAG collections")
    enable_mcp: bool = Field(True, description="Allow Researcher to read MCP file context")

    def model_for_role(self, role: AgentRole) -> str:
        """Return the configured model name for *role*."""
        mapping = {
            AgentRole.planner: self.planner_model,
            AgentRole.researcher: self.researcher_model,
            AgentRole.critic: self.critic_model,
            AgentRole.synthesizer: self.synthesizer_model,
        }
        return mapping.get(role, "grok")
