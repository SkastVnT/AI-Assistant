# =============================================================================
# RAG System — Makefile
# Common commands for development, testing, and deployment
# =============================================================================

.DEFAULT_GOAL := help
SHELL := /bin/bash

# --- Variables ---
PYTHON := python
VENV := .venv
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
UVICORN := $(VENV)/bin/uvicorn
COMPOSE := docker compose

# =============================================================================
# Help
# =============================================================================

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# =============================================================================
# Setup
# =============================================================================

.PHONY: venv
venv: ## Create Python virtual environment
	$(PYTHON) -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "✓ Virtual environment ready. Activate with: source $(VENV)/bin/activate"

.PHONY: env
env: ## Copy .env.example to .env (won't overwrite existing)
	@[ -f .env ] && echo ".env already exists, skipping" || (cp .env.example .env && echo "✓ .env created — edit it with your API keys")

.PHONY: setup
setup: venv env ## Full local setup (venv + .env)
	@echo "✓ Setup complete. Next: make infra-up && make dev"

# =============================================================================
# Infrastructure
# =============================================================================

.PHONY: infra-up
infra-up: ## Start infrastructure services (postgres, redis, minio)
	$(COMPOSE) up -d postgres redis minio minio-init
	@echo "Waiting for services to be healthy..."
	$(COMPOSE) exec postgres pg_isready -U rag_user -d rag || sleep 3
	@echo "✓ Infrastructure ready"

.PHONY: infra-down
infra-down: ## Stop infrastructure services
	$(COMPOSE) down

.PHONY: infra-reset
infra-reset: ## Stop and remove all volumes (DESTRUCTIVE)
	@echo "⚠️  This will delete all data. Press Ctrl+C to cancel."
	@sleep 3
	$(COMPOSE) down -v

.PHONY: up
up: ## Start ALL services (infra + api + worker) in Docker
	$(COMPOSE) up -d --build
	@echo "✓ All services started. API at http://localhost:8000"

.PHONY: down
down: ## Stop all services
	$(COMPOSE) down

.PHONY: logs
logs: ## Tail logs from all services
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show service status
	$(COMPOSE) ps

# =============================================================================
# Development (local Python, infra in Docker)
# =============================================================================

.PHONY: dev
dev: ## Run API locally with auto-reload
	PYTHONPATH=. $(UVICORN) apps.api.main:app --reload --host 0.0.0.0 --port 8000

.PHONY: worker
worker: ## Run worker locally
	PYTHONPATH=. $(PYTHON) -m apps.worker.main

# =============================================================================
# Database
# =============================================================================

.PHONY: db-migrate
db-migrate: ## Generate a new Alembic migration (usage: make db-migrate msg="add users table")
	PYTHONPATH=. $(VENV)/bin/alembic revision --autogenerate -m "$(msg)"

.PHONY: db-upgrade
db-upgrade: ## Apply all pending migrations
	PYTHONPATH=. $(VENV)/bin/alembic upgrade head

.PHONY: db-downgrade
db-downgrade: ## Rollback one migration
	PYTHONPATH=. $(VENV)/bin/alembic downgrade -1

# =============================================================================
# Testing & Quality
# =============================================================================

.PHONY: test
test: ## Run all tests
	PYTHONPATH=. $(PYTEST) tests/ -v

.PHONY: test-cov
test-cov: ## Run tests with coverage
	PYTHONPATH=. $(PYTEST) tests/ -v --cov=libs --cov=apps --cov-report=term-missing

.PHONY: lint
lint: ## Run ruff linter
	$(RUFF) check .

.PHONY: lint-fix
lint-fix: ## Auto-fix lint issues
	$(RUFF) check . --fix

.PHONY: format
format: ## Format code with ruff
	$(RUFF) format .

.PHONY: typecheck
typecheck: ## Run mypy type checking
	PYTHONPATH=. $(VENV)/bin/mypy libs/ apps/ --ignore-missing-imports

.PHONY: check
check: lint typecheck test ## Run all quality checks (lint + types + tests)

# =============================================================================
# Utilities
# =============================================================================

.PHONY: health
health: ## Check API health
	@curl -s http://localhost:8000/health | python -m json.tool

.PHONY: clean
clean: ## Remove build artifacts and caches
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov .coverage
	@echo "✓ Cleaned"
