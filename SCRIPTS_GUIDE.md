# Project Structure & Scripts

## Quick Start (Root Level)

**Main entry points (all ready to use):**
```bash
./start_all_services.sh      # Start all microservices
./start_chatbot.sh           # ChatBot only
./start_services.sh          # Web services
./menu.sh                    # Interactive CLI (also menu.bat on Windows)
docker-compose up -d         # Container setup
```

## Daily Operations (scripts/ folder)

**Service Management:**
```bash
scripts/start-all.sh/bat              # All services
scripts/start-hub-gateway.sh/bat      # Hub Gateway
scripts/start-chatbot.sh/bat          # ChatBot
scripts/start-text2sql.sh/bat         # Text2SQL
scripts/health-check-all.sh/bat       # Service health
scripts/stop-all.sh/bat               # Stop services
scripts/test-all.sh/bat               # Run all tests
```

**Deployment & Maintenance:**
```bash
scripts/deploy-chatbot.sh/bat         # Deploy with backup
scripts/rollback-chatbot.sh/bat       # Rollback if needed
scripts/setup-all.sh/bat              # Initial setup
scripts/cleanup.bat                   # Clean temp files
```

**Health & Diagnostics:**
```bash
scripts/check_system.py               # System check
scripts/health_check.py               # Service health
scripts/fix_dependencies.py           # Fix deps
```

**Tunnel & Networking:**
```bash
scripts/expose-*.sh                   # Public tunnel setup
scripts/update_cloudflare_dns.sh      # DNS updates
```

## CI/CD Pipelines (GitHub Actions)

**Workflows in `.github/workflows/` (public, for GitHub Actions):**
- `ci-cd.yml` — Main CI/CD pipeline
- `tests.yml` — Automated testing
- `security-scan.yml` — Security checks
- `codeql-analysis.yml` — Code analysis
- `dependency-review.yml` — Dependency checks

## Docker

**Container setup:**
- `docker-compose.yml` — Full container stack
- `docker-compose.light.yml` — Lightweight variant
- `docker/` — Docker configs

## Private (Collaborators Only)

Config in `private/dev-tools/`:
- `.flake8` — Code linting
- `.pre-commit-config.yaml` — Pre-commit hooks
- More configs in submodule

See [private/README.md](../private/README.md) for details.
