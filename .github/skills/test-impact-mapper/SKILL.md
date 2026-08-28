---
name: test-impact-mapper
description: "Map changed files to the smallest sufficient verification set. Use when: deciding which tests to run after a code change, explaining why a test scope is enough, or choosing between unit tests, integration tests, and manual checks."
---

# Test-Impact Mapper

## When to use this skill

- After any code change, to decide what to test.
- When the user asks "what tests should I run?" or "is this safe?"
- When reviewing a PR to assess test coverage of the diff.
- To justify skipping tests that cannot be affected by a change.

## Test infrastructure

| Runner | Command | Working dir | Env |
|---|---|---|---|
| CI (tests.yml) | `pytest tests/ -v --tb=short --timeout=60` | `./services/chatbot` | `TESTING=True`, `MONGODB_ENABLED=False` |
| CI (ci-cd.yml) | Same + lint job first | `./services/chatbot` | Same |
| Local | `cd services/chatbot && pytest tests/ -v` | `services/chatbot` | activate `venv-core` |
| RAG subsystem | `cd rag && pytest tests/` | `rag` | Python 3.11+ |
| Security | bandit + pip-audit (CI only) | `services/`, `app/src/` | — |

## File-to-test map

Use this table to find the minimum test set for a changed file.

| Changed file pattern | Tests to run | Reason |
|---|---|---|
| `routes/stream.py` | `test_stream_complete_contract`, `test_stream_metrics_contract`, `test_app`, `test_api_integration` | SSE contract and endpoint behavior |
| `routes/main.py` | `test_app` | Root, /chat, /clear, /history endpoints |
| `routes/conversations.py` | `test_integration`, `test_repositories` | Conversation CRUD + DB layer |
| `routes/mcp.py` | Manual: call MCP proxy routes | No dedicated unit test; verify via inspector |
| `routes/image_gen.py` | `test_image_orchestration`, `test_endpoint_orchestrator_integration` | Image generation pipeline |
| `routes/memory.py` | `test_integration` | Memory persistence through DB |
| `routes/skills.py` | `test_skills_api` | Skill management endpoints |
| `core/chatbot.py` | `test_api_integration`, `test_integration`, `test_llm_clients`, `test_multi_turn_followup` | Model routing and tool dispatch |
| `core/chatbot_v2.py` | Same as `core/chatbot.py` | V2 agent |
| `core/tools.py` | `test_api_integration` + manual search-tool check | Tool functions are mocked in CI; verify cascade manually |
| `core/config.py` | `test_app` (smoke) | Config is read at import; any test that imports the app exercises it |
| `core/thinking_generator.py` | `test_agentic_*` (all 9 files) | Thinking modes feed the agentic pipeline |
| `core/streaming.py` | `test_stream_complete_contract`, `test_stream_metrics_contract` | SSE helpers |
| `core/extensions.py` | `test_app` | Flask extensions shared across blueprints |
| `core/db_helpers.py` | `test_integration`, `test_performance`, `test_repositories` | Database access layer |
| `core/error_handler.py` | `test_app` | Error middleware |
| `core/agentic/**` | `test_agentic_*` (all 9 files) | Multi-agent orchestration |
| `src/rag/**` | `test_ingest`, `test_retrieval`, `test_rag_*` | RAG pipeline |
| `src/audio_transcription.py` | Manual only | No dedicated test |
| `src/ocr_integration.py` | Manual only | No dedicated test |
| `src/video_generation.py` | `test_video_aspect_ratio_contract` | Video parameter contract |
| `templates/index.html` | `test_ui_smoke_contracts`, `test_app` (root endpoint) | UI contract |
| `static/**` | `test_ui_smoke_contracts` | UI asset changes |
| `services/shared_env.py` | `test_app` (smoke) + check all services start | Env loader is process-wide |
| `services/mcp-server/server.py` | Inspector test: `npx @modelcontextprotocol/inspector python server.py` | MCP has no pytest suite |
| `services/mcp-server/tools/**` | Same inspector test | Utility functions not auto-registered |
| `.env*` / `app/config/**` | `test_app` (smoke) | Config read at startup |
| `.github/workflows/**` | No code test needed | Review YAML diff only |
| `README.md` / docs only | No test needed | Docs-only changes never need tests |

## Decision procedure

1. **List changed files** in the diff.
2. **Look up each file** in the map above.
3. **Union the test sets** — that is the minimum scope.
4. **If any file has "Manual only"**, note it separately.
5. **If the change is docs/config/workflow only**, state "no tests needed" and explain why.
6. **State the rationale**: which tests cover which changed files, and why the remaining tests can be skipped.

## Scope sufficiency rules

- **Unit tests are enough** when the change is limited to a single module and the file-to-test map covers it.
- **Integration tests are needed** when the change crosses module boundaries (e.g., route → chatbot → tool → config).
- **Manual verification is needed** when the map says "Manual only" or when the change affects MCP, audio, OCR, or live API integrations.
- **Full suite (`pytest tests/ -v`)** is warranted when: `conftest.py` changes, `core/config.py` changes, `extensions.py` changes, or more than 3 modules are affected.
- **RAG tests** are separate and only needed when `src/rag/**` changes.

## CI workflow awareness

| Workflow | Triggers on | What it validates |
|---|---|---|
| `tests.yml` | Push/PR to master, develop, feat/**, refactor/** | `pytest tests/ -v` in chatbot |
| `ci-cd.yml` | Same triggers | lint (compileall + flake8) → test-chatbot → test-root → security → docker |
| `security-scan.yml` | Push/PR to master, develop + weekly cron | bandit + pip-audit |
| `codeql-analysis.yml` | Push to master, develop + weekly cron | CodeQL security-and-quality |
| `dependency-review.yml` | PR to master, develop (requirements paths) | License + vulnerability check |

If CI will run the same tests automatically, say so. The user may still want to run locally first for faster feedback.

## Mandatory checklist

After identifying the test scope:

- [ ] Every changed file is accounted for in the file-to-test map.
- [ ] The test set is the **union** of all matched tests — nothing dropped without justification.
- [ ] If a file maps to "Manual only," this is called out explicitly.
- [ ] The rationale explains **why untouched tests can be skipped**.
- [ ] If the change affects config, env, or extensions, the full suite is recommended.
- [ ] The response includes the exact command to run (e.g., `pytest tests/test_stream_complete_contract.py tests/test_app.py -v`).
