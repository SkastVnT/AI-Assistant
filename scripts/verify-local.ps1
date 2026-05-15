Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot   = Split-Path -Parent $PSScriptRoot
$VenvPython = Join-Path $RepoRoot "venv-core\Scripts\python.exe"
$ChatbotDir = Join-Path $RepoRoot "services\chatbot"

function Write-Header([string]$Title) {
    Write-Host ""
    Write-Host "==========================================="-ForegroundColor Cyan
    Write-Host "  $Title" -ForegroundColor Cyan
    Write-Host "==========================================="  -ForegroundColor Cyan
}
function Write-OK([string]$Msg)   { Write-Host "  [PASS] $Msg" -ForegroundColor Green }
function Write-Bad([string]$Msg)  { Write-Host "  [FAIL] $Msg" -ForegroundColor Red }
function Write-Info([string]$Msg) { Write-Host "  [SKIP] $Msg" -ForegroundColor DarkGray }

$failures = @()

# Guard: venv must exist
if (-not (Test-Path $VenvPython)) {
    Write-Bad "venv-core not found at $VenvPython"
    Write-Host "  Activate: python -m venv venv-core and install profile_core_services.txt" -ForegroundColor Yellow
    exit 1
}

# ---- 1. Python import smoke test -------------------------------------------
Write-Header "1 - Python import smoke test"
$smokeOk = $true
Push-Location $ChatbotDir
try {
    # Verify the chatbot entry point imports cleanly (catches missing-module / syntax errors)
    & $VenvPython -c "import sys; sys.path.insert(0, '.'); import core.config; import core.url_safety; import core.secret_key; print('smoke OK')"
    if ($LASTEXITCODE -ne 0) {
        Write-Bad "Chatbot core import smoke FAILED"
        $smokeOk = $false
        $failures += "import-smoke"
    } else {
        Write-OK "Core imports clean"
    }
} finally {
    Pop-Location
}
if ($smokeOk) { Write-OK "Import smoke passed" }

# ---- 2. P0 trust-boundary tests --------------------------------------------
Write-Header "2 - P0 trust-boundary contracts"
Push-Location $ChatbotDir
try {
    & $VenvPython -m pytest tests/test_p0_trust_boundary.py tests/test_mcp_guard.py -q --no-header --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Bad "P0 trust-boundary tests FAILED"
        $failures += "p0-trust-boundary"
    } else {
        Write-OK "P0 trust-boundary passed"
    }
} finally {
    Pop-Location
}

# ---- 3. Default gate --------------------------------------------------------
Write-Header "3 - Default gate (unit + api + smoke)"
$excludeExpr = "not integration and not image and not rag and not hermes and not mongo and not slow and not agentic"
Push-Location $ChatbotDir
try {
    & $VenvPython -m pytest tests/ -m $excludeExpr -q --no-header --tb=short
    if ($LASTEXITCODE -ne 0) {
        Write-Bad "Default gate FAILED"
        $failures += "default-gate"
    } else {
        Write-OK "Default gate passed"
    }
} finally {
    Pop-Location
}

# ---- 4. Electron payload test (optional) ------------------------------------
Write-Header "4 - Electron payload test (optional)"
$ElectronDir = Join-Path $RepoRoot "desktop\electron"
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($null -eq $nodeCmd) {
    Write-Info "Node.js not found - skipping"
} elseif (-not (Test-Path (Join-Path $ElectronDir "package.json"))) {
    Write-Info "desktop\electron\package.json missing - skipping"
} else {
    Push-Location $ElectronDir
    try {
        $pkgJson = Get-Content package.json -Raw | ConvertFrom-Json
        if ($null -ne $pkgJson.scripts -and $null -ne $pkgJson.scripts.'test:payload') {
            & npm run test:payload
            if ($LASTEXITCODE -ne 0) {
                Write-Bad "Electron payload test FAILED"
                $failures += "electron-payload"
            } else {
                Write-OK "Electron payload test passed"
            }
        } else {
            Write-Info "No test:payload script defined - skipping"
        }
    } finally {
        Pop-Location
    }
}

# ---- Final summary ----------------------------------------------------------
Write-Host ""
Write-Host "===========================================" -ForegroundColor Cyan
if ($failures.Count -eq 0) {
    Write-Host "  GATE: PASS - all sections green" -ForegroundColor Green
} else {
    Write-Host "  GATE: FAIL - $($failures.Count) section(s) failed:" -ForegroundColor Red
    foreach ($f in $failures) {
        Write-Host "    - $f" -ForegroundColor Red
    }
}
Write-Host "===========================================" -ForegroundColor Cyan

if ($failures.Count -ne 0) { exit 1 }
