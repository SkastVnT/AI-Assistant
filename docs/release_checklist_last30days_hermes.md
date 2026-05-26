# Release Checklist: last30days + Hermes Integration

> Use this checklist before merging the last30days / Hermes feature branch.

---

## Pre-merge — Code Quality

- [ ] All new tests pass locally: `cd services/chatbot && pytest tests/test_last30days.py tests/test_hermes.py tests/test_regression_safety.py -v`
- [ ] Full test suite passes: `pytest tests/ -v --tb=short --timeout=60`
- [ ] No new lint errors: `python -m compileall -q services/ app/src/`
- [ ] No hardcoded API keys, URLs, or ports in new code
- [ ] Feature flags default to `false` (both `LAST30DAYS_ENABLED` and `HERMES_ENABLED`)

## Pre-merge — Integration Points

### last30days
- [ ] `core/last30days_tool.py` — subprocess wrapper with timeout, input validation, max topic length
- [ ] `routes/last30days.py` — Flask blueprint registered in `chatbot_main.py`
- [ ] `core/skills/builtins/social_research.yaml` — skill definition loadable by SkillRegistry
- [ ] `/last30days` command detection works in `routes/stream.py`
- [ ] Tool button visible in `templates/index.html` with working JS binding
- [ ] `vendor/last30days/setup.ps1` and `setup.sh` clone correctly

### Hermes
- [ ] `core/hermes_adapter.py` — HTTP proxy with timeout, auth header, error handling
- [ ] `routes/hermes.py` — Flask blueprint registered in `chatbot_main.py`
- [ ] `core/config.py` has `HERMES_ENABLED`, `HERMES_API_URL`, `HERMES_API_KEY`, `HERMES_TIMEOUT`

## Pre-merge — Regression Safety

- [ ] `test_regression_safety.py` passes — verifies:
  - Core module imports (config, tools, streaming, thinking)
  - Route blueprint imports (stream, main, last30days, hermes, skills)
  - Search tool signatures unchanged
  - Image generation modules still importable
  - Skill registry loads with existing + new skills
  - `shared_env.py` still exports `load_shared_env`
- [ ] Existing test files still pass (especially `test_app.py`, `test_skills.py`, `test_stream_complete_contract.py`)

## Pre-merge — Environment & Config

- [ ] `app/config/.env.example` has all new variables with safe defaults
- [ ] `services/chatbot/.env.example` has all new variables
- [ ] No `load_dotenv` calls added (shared env contract)
- [ ] Dockerfile uses port 5000 (not 5001) and entrypoint `run.py` (not `app.py`)

## Pre-merge — Docs

- [ ] `docs/deployment_last30days_hermes.md` exists with:
  - Service matrix
  - Environment variables table
  - Local development setup
  - Docker setup
  - Health checks
  - Common failure modes
  - Rollback procedures
- [ ] `docs/integration_plan_hermes_last30days.md` status updated
- [ ] `README.md` has "Optional Tools & Sidecars" section
- [ ] `README.md` Docker instructions reference root `docker-compose.yml`
- [ ] `services/chatbot/docs/last30days_integration.md` up to date

## Pre-merge — CI

- [ ] `.github/workflows/tests.yml` runs new tests (they're in `tests/` so auto-included)
- [ ] CI passes on the feature branch

---

## Post-merge — Deployment

### Enabling last30days on a new machine

1. Clone last30days engine: `cd services/chatbot/vendor/last30days && ./setup.ps1`
2. Configure last30days API keys: `~/.config/last30days/.env`
3. Set env: `LAST30DAYS_ENABLED=true`, `LAST30DAYS_PYTHON_PATH=python3.12`
4. Restart chatbot
5. Verify: `curl -X POST http://localhost:5000/api/tools/last30days -H 'Content-Type: application/json' -d '{"topic": "test"}'`

### Enabling Hermes on a new machine

1. Clone Hermes: `mkdir -p vendor/hermes && cd vendor/hermes && git clone https://github.com/NousResearch/hermes-agent.git repo`
2. Set up Hermes venv: `cd repo && python -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. Start sidecar: `cd repo && python -m gateway.platforms.api_server --port 8080`
4. Set env: `HERMES_ENABLED=true`, `HERMES_API_URL=http://localhost:8080`
5. Restart chatbot
6. Verify: `curl -X POST http://localhost:5000/api/hermes/chat -H 'Content-Type: application/json' -d '{"message": "hello"}'`

### Docker

```bash
# Core only
docker compose up -d

# With last30days
docker compose --profile tools up -d

# With Hermes (requires vendor/hermes/Dockerfile)
docker compose --profile hermes up -d

# Everything
docker compose --profile all up -d
```

---

## Known Risks

| Risk | Severity | Mitigation |
|---|---|---|
| last30days subprocess timeout (1-5 min) | Medium | Default 180s timeout; `depth=quick` option |
| Hermes sidecar not running | Low | Feature flag gates; clear error message |
| Python 3.12+ not available for last30days | Medium | Clear error message; feature flag |
| Node.js missing for X/Twitter source | Low | Graceful skip; other sources work |
| Hermes dependency conflicts with venv-core | N/A | Sidecar pattern — separate process |
| SSE blocking during long research | Medium | Acceptable for sync flow; document clearly |
| New blueprints fail to register | Low | try/except pattern (existing convention) |

---

## Rollback Plan

### Quick disable (no code change)
```bash
# In app/config/.env
LAST30DAYS_ENABLED=false
HERMES_ENABLED=false
# Restart chatbot
```

### Full removal
See [deployment docs — rollback section](./deployment_last30days_hermes.md#rollback-procedures).
