"""Agentic RAG — optional orchestration layer for complex multi-step queries.

Architecture
============

Standard path (default):
    query ──► retrieve() ──► generate_grounded_answer() ──► AnswerResponse

Agentic path (opt-in via AGENT_ENABLED=true):
    query ──► AgentController.run()
                │
                ├─ 1. PLAN   — LLM decomposes the task into sub-goals
                ├─ 2. ACT    — select & execute a tool (retriever, web, python, policy)
                ├─ 3. OBSERVE — read the tool result, update short-term memory
                ├─ 4. REFLECT — self-check: is the accumulated evidence sufficient?
                ├─ 5. ANSWER  — synthesise final response from all evidence
                └─ 6. DONE   — return AgentResponse (or ERROR if max iterations hit)

Decision:  build from scratch vs LangGraph vs CrewAI vs AutoGen
──────────────────────────────────────────────────────────────
  ┌──────────┬───────────────┬────────────────┬──────────────┬────────────────┐
  │ Criteria │ LangGraph     │ CrewAI         │ AutoGen      │ From Scratch   │
  ├──────────┼───────────────┼────────────────┼──────────────┼────────────────┤
  │ Overhead │ Medium (lang- │ Heavy (multi-  │ Heavy (multi │ Minimal —      │
  │          │ chain deps)   │ agent runtime) │ agent conv)  │ zero new deps  │
  ├──────────┼───────────────┼────────────────┼──────────────┼────────────────┤
  │ Control  │ State graph,  │ YAML roles,    │ Chat-based,  │ Full control,  │
  │          │ composable    │ limited hooks  │ actor model  │ exact fit      │
  ├──────────┼───────────────┼────────────────┼──────────────┼────────────────┤
  │ Auth     │ Must bolt on  │ No built-in    │ No built-in  │ First-class    │
  │          │               │ tenant auth    │ tenant auth  │ AuthContext     │
  ├──────────┼───────────────┼────────────────┼──────────────┼────────────────┤
  │ Observe  │ LangSmith     │ Limited        │ Custom       │ SpanCollector  │
  │          │ (external)    │                │              │ (built-in)     │
  ├──────────┼───────────────┼────────────────┼──────────────┼────────────────┤
  │ RAG fit  │ Good (tools)  │ Fair (tasks)   │ Fair (chat)  │ Exact (tools   │
  │          │               │                │              │ wrap our APIs) │
  └──────────┴───────────────┴────────────────┴──────────────┴────────────────┘

  RECOMMENDATION: Build from scratch.
  ─────────────────────────────────────
  • Zero additional dependencies — the pipeline is already async + protocols
  • AuthContext / SpanCollector / guardrails integrate natively
  • LangGraph's state-graph concept is elegant but brings langchain as
    a transitive dependency (200+ packages); we replicate only the useful
    state-machine pattern in ~300 lines
  • CrewAI and AutoGen target multi-agent collaboration; our use case is
    a single planner-executor loop — simpler than what they provide

Module layout:
    libs/agent/
    ├── __init__.py      ← this file (architecture diagram)
    ├── types.py         ← AgentState, ToolCall, ToolResult, Turn, StopReason
    ├── tools.py         ← Tool protocol + retriever / web / python / policy
    ├── planner.py       ← LLM-based planning + tool selection
    ├── memory.py        ← ShortTermMemory (scratchpad + evidence accumulator)
    ├── safety.py        ← DelegatedAuth token, budget guards, content checks
    ├── controller.py    ← AgentController state machine (PLAN→ACT→OBSERVE→REFLECT→ANSWER)
    └── orchestrator.py  ← agentic_answer() entry point wrapping the full loop
"""
