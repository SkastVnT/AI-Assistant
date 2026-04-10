"""
core.agentic — 4-Agent Internal Council
=========================================
Public surface of the agentic orchestration layer.

Quick-start::

    from core.agentic import CouncilOrchestrator, CouncilConfig, PreContext

    orch = CouncilOrchestrator(CouncilConfig())
    result = await orch.run(PreContext(original_message="..."))
"""
from core.agentic.blackboard import BlackboardStore, create_blackboard
from core.agentic.blackboard_memory import InMemoryBlackboard
from core.agentic.config import CouncilConfig
from core.agentic.contracts import (
    AgentMode,
    AgentRole,
    AgentStrategy,
    CouncilResult,
    CouncilStep,
    CouncilTrace,
    CriticOutput,
    CritiqueIssue,
    EvidenceItem,
    FinalAnswer,
    PlannerOutput,
    ResearcherOutput,
    RunStatus,
    SynthesizerOutput,
    TaskNode,
)
from core.agentic.events import CouncilEvent, CouncilEventEmitter, EventStage, EventStatus
from core.agentic.orchestrator import CouncilOrchestrator
from core.agentic.prompts import get_system_prompt
from core.agentic.state import AgentRunState, PreContext

__all__ = [
    # Blackboard
    "BlackboardStore",
    "InMemoryBlackboard",
    "create_blackboard",
    # Orchestrator
    "CouncilOrchestrator",
    # Config
    "CouncilConfig",
    # Enums
    "AgentMode",
    "AgentRole",
    "AgentStrategy",
    "RunStatus",
    # Events
    "CouncilEvent",
    "CouncilEventEmitter",
    "EventStage",
    "EventStatus",
    # State
    "AgentRunState",
    "PreContext",
    # Contracts — Planner
    "TaskNode",
    "PlannerOutput",
    # Contracts — Researcher
    "EvidenceItem",
    "ResearcherOutput",
    # Contracts — Critic
    "CritiqueIssue",
    "CriticOutput",
    # Contracts — Synthesizer
    "FinalAnswer",
    "SynthesizerOutput",
    # Trace
    "CouncilStep",
    "CouncilTrace",
    "CouncilResult",
    # Prompts
    "get_system_prompt",
]
