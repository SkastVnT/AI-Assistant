# Agentic Council v1 — Architecture Decision Record

> **Status**: v1 complete — all agents, orchestrator, SSE streaming, router integration, tests, logging
> **Date**: 2026-04-03
> **Author**: AI-Assistant team

---

## 1. Why an additive internal council?

The existing `ReasoningService` (in `app/services/reasoning_service.py`) implements
a "4-Agents" label, but it actually runs **N identical trajectories** with the same
prompt template and no role differentiation.  There is no Planner, no tool-calling
Researcher, no Critic feedback loop, and no named Synthesizer.

We need a true multi-agent council where:

- **Planner** decomposes the question into sub-tasks and suggests tools.
- **Researcher** gathers evidence (LLM + web search + RAG + MCP).
- **Critic** evaluates quality and can request another round.
- **Synthesizer** produces the final, polished answer.

### Design constraints

| Constraint | Rationale |
|---|---|
| Additive (no existing file deleted) | Zero risk to current `/chat`, `/chat/stream`, `/chat/upload` |
| No new framework (no LangGraph, Celery) | Keep the dependency graph lightweight |
| Plain Python + Flask + Pydantic v2 | Matches the active stack already in use |
| Optional Redis adapter (future) | Enables inter-process state sharing later |
| Existing `thinking_mode=multi-thinking` unchanged | Backward compatibility for current UI |
| Future xAI native multi-agent hook | `AgentMode.xai_native` placeholder reserved |

---

## 2. How it maps onto the existing repo

```
services/chatbot/
├── core/
│   ├── base_chat.py          # ModelConfig, ChatContext, ChatResponse ← reused
│   ├── chatbot_v2.py         # ModelRegistry, ChatbotAgent           ← reused (ModelRegistry)
│   └── agentic/              # ★ NEW — the council layer
│       ├── __init__.py        #   Public API
│       ├── contracts.py       #   All typed models (AgentMode, AgentRole, etc.)
│       ├── config.py          #   CouncilConfig (client-facing Pydantic model)
│       ├── state.py           #   AgentRunState + PreContext
│       ├── orchestrator.py    #   CouncilOrchestrator (drives the loop)
│       └── agents/
│           ├── __init__.py
│           ├── base.py        #   BaseAgent ABC + LLMCallResult
│           ├── planner.py     #   PlannerAgent
│           ├── researcher.py  #   ResearcherAgent
│           ├── critic.py      #   CriticAgent
│           └── synthesizer.py #   SynthesizerAgent
├── routes/
│   └── stream.py              # Flask SSE integration point
└── app/services/
    └── reasoning_service.py   # ← untouched; still serves thinking_mode=multi-thinking
```

### Integration seams

| Seam | Existing code | Council code |
|---|---|---|
| LLM calls | `ModelRegistry.get_handler(model).chat(ctx, ...)` | `BaseAgent._call_llm()` wraps the same registry |
| RAG | `RAGOrchestrator.retrieve_for_chat()` | Pre-fetched in router, passed via `PreContext.rag_chunks` |
| Web search | `_run_web_search()` in stream routers | Pre-fetched in router, passed via `PreContext.web_search_context`; Researcher may also call tools directly |
| MCP | `inject_code_context()` | Pre-fetched, passed via `PreContext.mcp_context` |
| SSE | `_sse()` helper function | Orchestrator yields `CouncilStep`, router wraps in `_sse("council_step", ...)` |

---

## 3. Files added (complete v1)

| File | Purpose |
|---|---|
| `core/agentic/__init__.py` | Public re-exports (`CouncilOrchestrator`, all contracts) |
| `core/agentic/contracts.py` | All typed Pydantic models: enums, data objects, trace objects |
| `core/agentic/config.py` | `CouncilConfig` Pydantic model (client-facing, sensible defaults) |
| `core/agentic/state.py` | `PreContext` + `AgentRunState` (mutable state bag) |
| `core/agentic/orchestrator.py` | `CouncilOrchestrator` with `run()` and `run_stream()` |
| `core/agentic/entrypoint.py` | Router bridge: `run_council()`, `run_council_stream()`, feature flag |
| `core/agentic/council_entry.py` | Alternate entry point (legacy) |
| `core/agentic/events.py` | `CouncilEvent` + `CouncilEventEmitter` for SSE streaming |
| `core/agentic/evidence_gathering.py` | Normalized evidence extraction from 4 sources |
| `core/agentic/llm_adapter.py` | Bridge to `ModelRegistry` (deferred imports) |
| `core/agentic/model_resolver.py` | Role → model fallback chains with priority ordering |
| `core/agentic/prompts.py` | Role-specific system prompts with JSON schema definitions |
| `core/agentic/blackboard.py` | `BlackboardStore` protocol + factory |
| `core/agentic/blackboard_memory.py` | In-memory blackboard adapter |
| `core/agentic/blackboard_redis.py` | Optional Redis-backed blackboard adapter |
| `core/agentic/agents/__init__.py` | Re-exports all four agent classes |
| `core/agentic/agents/base.py` | `BaseAgent` ABC + `LLMCallResult` |
| `core/agentic/agents/planner.py` | `PlannerAgent` — task decomposition |
| `core/agentic/agents/researcher.py` | `ResearcherAgent` — evidence gathering + LLM synthesis |
| `core/agentic/agents/critic.py` | `CriticAgent` — quality evaluation + retry targeting |
| `core/agentic/agents/synthesizer.py` | `SynthesizerAgent` — final answer composition |
| `routes/stream.py` | SSE route `POST /chat/stream` |
| `docs/architecture/agentic-v1.md` | This document |
| `docs/architecture/agentic-api.md` | API reference |
| `docs/architecture/agentic-trace.md` | Trace and observability guide |

**Tests:**

| File | Tests | Coverage |
|---|---|---|
| `tests/test_agentic_agents.py` | 43 | Agent workers, JSON parsing, prompts |
| `tests/test_agentic_state.py` | 21 | Blackboard adapters, full lifecycle |
| `tests/test_agentic_model_integration.py` | 23 | Model resolver, LLM adapter |
| `tests/test_agentic_evidence.py` | 38 | Evidence gathering, budget enforcement |
| `tests/test_agentic_orchestrator.py` | 23 | Orchestrator state machine, all exit paths |
| `tests/test_agentic_critic_loop.py` | 24 | Critic loop, selective retry, circuit breaker |
| `tests/test_agentic_entrypoint.py` | 20 | Entry point, config builders, feature flag |

**Note:** The previous parallel API integration tests were removed with the retired API path in May 2026.

---

## 4. Import paths for the Flask monolith

When wiring council behavior, keep imports inside `routes/stream.py` and shared `core/agentic/*` modules. Do not reintroduce a parallel API package.

---

## 5. Phase roadmap

| Phase | What | Status |
|---|---|---|
| **1 — Scaffolding** | Contracts, agents, orchestrator structure | ✅ Complete |
| **2 — Agent logic** | Real prompts, LLM calls via ModelRegistry, output parsing | ✅ Complete |
| **3 — Pydantic models** | `AgentMode`, `CouncilConfig`, `CouncilTrace` in `models.py` | ✅ Complete |
| **4 — SSE wiring** | `agent_mode=council` branch in stream router, EventEmitter | ✅ Complete |
| **5 — JSON wiring** | Council branch in `chat.py` | ✅ Complete |
| **6 — Evidence pipeline** | Researcher gathers from RAG, MCP, web search, files | ✅ Complete |
| **7 — Critic loop** | Selective retry, circuit breaker, quality threshold | ✅ Complete |
| **8 — Tests** | Unit + focused integration tests (9 files, ~217 tests) | ✅ Complete |
| **9 — Logging & Docs** | Structured logging, architecture docs, migration notes | ✅ Complete |
| **10 — Frontend** | "Council" option in thinking-mode dropdown | ❌ Not started |
| **11 — Tool bridge** | Runtime web search / RAG calls from Researcher | ❌ Not started |
| **12 — Redis adapter** | Optional Redis-backed state sharing | ❌ Not started |

## 6. Logging

All log messages use the pattern `[Component] run_id=X | key=value` for easy
grep-based filtering and log aggregation.

| Component | Level | What is logged |
|---|---|---|
| Orchestrator | `INFO` | Pipeline start/finish, stage transitions, retry decisions |
| Orchestrator | `INFO` | Circuit breaker triggers, exit reason, quality scores |
| Orchestrator | `ERROR` | Pipeline failures with reason |
| Planner | `INFO` | run_id, round, model, task count, complexity |
| Researcher | `INFO` | run_id, round, model, evidence count, tools used |
| Critic | `INFO` | run_id, round, model, quality score, verdict, issue count |
| Synthesizer | `INFO` | run_id, model, answer length, confidence |
| Entrypoint | `INFO` | Config summary, final exit reason |
| Entrypoint | `DEBUG` | Feature flag status |
| BaseAgent | `DEBUG` | LLM call metadata (model, tokens, elapsed) |

**Not logged**: Raw LLM prompts/responses, API keys, full user messages, file contents.

## 7. Migration notes

See the full migration guide at the bottom of this document.

### Why the old single-agent path remains

The existing `ReasoningService` and standard chatbot flow (`agent_mode="off"`)
are untouched. Council mode is entirely additive:

- **Zero risk**: No existing endpoint, import, or response format changed.
- **Feature flag**: `AGENTIC_V1_ENABLED=false` (default) means the council
  code never executes — not even loaded into the hot path.
- **Gradual rollout**: Enable per-server or per-environment. The frontend
  can offer council as an opt-in "deep thinking" mode.

### How to enable council mode

1. Set environment variable:
   ```bash
   export AGENTIC_V1_ENABLED=true
   ```
2. Send requests with `agent_mode: "council"`:
   ```json
   {
     "message": "Compare Python and Rust for web development",
     "model": "grok",
     "agent_mode": "council",
     "max_agent_iterations": 2
   }
   ```
3. For streaming, use `POST /chat/council/stream` with the same body.

### Known limitations in v1

| Limitation | Impact | Planned fix |
|---|---|---|
| No runtime tool calling | Researcher uses only pre-fetched context | Phase 11 |
| No parallel research | Tasks executed sequentially | `AgentStrategy.parallel_research` |
| No frontend UI | Must set `agent_mode` manually in API | Phase 10 |
| Redis adapter untested | Only in-memory blackboard verified | Phase 12 |
| No cost tracking | Token counts tracked but not dollar amounts | Future |
| English prompts only | System prompts are English; output language follows `language` param | Future |
| Single model per role | Cannot split a role across multiple models | Future |
