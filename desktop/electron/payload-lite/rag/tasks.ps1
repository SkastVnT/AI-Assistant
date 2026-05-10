<# 
.SYNOPSIS
    RAG System — PowerShell task runner (Windows equivalent of Makefile)

.DESCRIPTION
    Usage: .\tasks.ps1 <command>
    Run without arguments to see available commands.
#>

param(
    [Parameter(Position=0)]
    [string]$Command = "help"
)

$ErrorActionPreference = "Stop"
$VENV = ".venv"
$PYTHON = "$VENV\Scripts\python.exe"
$PIP = "$VENV\Scripts\pip.exe"
$UVICORN = "$VENV\Scripts\uvicorn.exe"
$PYTEST = "$VENV\Scripts\pytest.exe"
$RUFF = "$VENV\Scripts\ruff.exe"

function Show-Help {
    Write-Host "`nRAG System — Task Runner" -ForegroundColor Cyan
    Write-Host "========================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Setup:" -ForegroundColor Yellow
    Write-Host "  venv          Create Python virtual environment"
    Write-Host "  env           Copy .env.example to .env"
    Write-Host "  setup         Full local setup (venv + env)"
    Write-Host ""
    Write-Host "Infrastructure:" -ForegroundColor Yellow
    Write-Host "  infra-up      Start infra services (postgres, redis, minio)"
    Write-Host "  infra-down    Stop infrastructure"
    Write-Host "  up            Start ALL services in Docker"
    Write-Host "  down          Stop all services"
    Write-Host "  logs          Tail all service logs"
    Write-Host "  ps            Show service status"
    Write-Host ""
    Write-Host "Development:" -ForegroundColor Yellow
    Write-Host "  dev           Run API locally with auto-reload"
    Write-Host "  worker        Run worker locally"
    Write-Host ""
    Write-Host "Database:" -ForegroundColor Yellow
    Write-Host "  db-upgrade    Apply all pending migrations"
    Write-Host "  db-downgrade  Rollback one migration"
    Write-Host ""
    Write-Host "Quality:" -ForegroundColor Yellow
    Write-Host "  test          Run all tests"
    Write-Host "  lint          Run ruff linter"
    Write-Host "  lint-fix      Auto-fix lint issues"
    Write-Host "  format        Format code"
    Write-Host "  check         Run lint + tests"
    Write-Host ""
    Write-Host "Utilities:" -ForegroundColor Yellow
    Write-Host "  health        Check API health endpoint"
    Write-Host "  clean         Remove caches and build artifacts"
    Write-Host ""
}

function Invoke-Venv {
    python -m venv $VENV
    & $PIP install --upgrade pip
    & $PIP install -r requirements.txt
    Write-Host "Virtual environment ready. Activate: .\.venv\Scripts\Activate.ps1" -ForegroundColor Green
}

function Invoke-Env {
    if (Test-Path .env) {
        Write-Host ".env already exists, skipping" -ForegroundColor Yellow
    } else {
        Copy-Item .env.example .env
        Write-Host ".env created - edit it with your API keys" -ForegroundColor Green
    }
}

function Invoke-Setup {
    Invoke-Venv
    Invoke-Env
    Write-Host "Setup complete. Next: .\tasks.ps1 infra-up; .\tasks.ps1 dev" -ForegroundColor Green
}

function Invoke-InfraUp {
    docker compose up -d postgres redis minio minio-init
    Write-Host "Infrastructure starting..." -ForegroundColor Cyan
    Start-Sleep -Seconds 5
    docker compose ps
}

function Invoke-InfraDown {
    docker compose down
}

function Invoke-Up {
    docker compose up -d --build
    Write-Host "All services started. API at http://localhost:8000" -ForegroundColor Green
}

function Invoke-Down {
    docker compose down
}

function Invoke-Logs {
    docker compose logs -f
}

function Invoke-Ps {
    docker compose ps
}

function Invoke-Dev {
    $env:PYTHONPATH = "."
    & $UVICORN apps.api.main:app --reload --host 0.0.0.0 --port 8000
}

function Invoke-Worker {
    $env:PYTHONPATH = "."
    & $PYTHON -m apps.worker.main
}

function Invoke-DbUpgrade {
    $env:PYTHONPATH = "."
    & "$VENV\Scripts\alembic.exe" upgrade head
}

function Invoke-DbDowngrade {
    $env:PYTHONPATH = "."
    & "$VENV\Scripts\alembic.exe" downgrade -1
}

function Invoke-Test {
    $env:PYTHONPATH = "."
    & $PYTEST tests/ -v
}

function Invoke-Lint {
    & $RUFF check .
}

function Invoke-LintFix {
    & $RUFF check . --fix
}

function Invoke-Format {
    & $RUFF format .
}

function Invoke-Check {
    Invoke-Lint
    Invoke-Test
}

function Invoke-Health {
    $resp = Invoke-RestMethod -Uri http://localhost:8000/health -Method Get
    $resp | ConvertTo-Json -Depth 5
}

function Invoke-Clean {
    Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Directory -Filter ".pytest_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Directory -Filter ".mypy_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem -Recurse -Directory -Filter ".ruff_cache" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
    Write-Host "Cleaned" -ForegroundColor Green
}

# --- Dispatch ---
switch ($Command) {
    "help"          { Show-Help }
    "venv"          { Invoke-Venv }
    "env"           { Invoke-Env }
    "setup"         { Invoke-Setup }
    "infra-up"      { Invoke-InfraUp }
    "infra-down"    { Invoke-InfraDown }
    "up"            { Invoke-Up }
    "down"          { Invoke-Down }
    "logs"          { Invoke-Logs }
    "ps"            { Invoke-Ps }
    "dev"           { Invoke-Dev }
    "worker"        { Invoke-Worker }
    "db-upgrade"    { Invoke-DbUpgrade }
    "db-downgrade"  { Invoke-DbDowngrade }
    "test"          { Invoke-Test }
    "lint"          { Invoke-Lint }
    "lint-fix"      { Invoke-LintFix }
    "format"        { Invoke-Format }
    "check"         { Invoke-Check }
    "health"        { Invoke-Health }
    "clean"         { Invoke-Clean }
    default         { Write-Host "Unknown command: $Command" -ForegroundColor Red; Show-Help }
}
