<#
.SYNOPSIS
    Clone/update the last30days-skill engine for AI-Assistant integration.
.DESCRIPTION
    Downloads the last30days-skill repo into vendor/last30days/repo/.
    Requires: git, Python 3.12+
    Config: ~/.config/last30days/.env (API keys per source — see last30days docs)
#>

param(
    [string]$Branch = "main",
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$RepoUrl = "https://github.com/mvanhorn/last30days-skill.git"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RepoDir = Join-Path $ScriptDir "repo"

Write-Host "[last30days] Setup starting..." -ForegroundColor Cyan

# Clone or update
if (Test-Path (Join-Path $RepoDir ".git")) {
    if ($Force) {
        Write-Host "[last30days] Force update — pulling latest..." -ForegroundColor Yellow
        Push-Location $RepoDir
        git fetch origin
        git reset --hard "origin/$Branch"
        Pop-Location
    } else {
        Write-Host "[last30days] Repo already exists. Use -Force to update." -ForegroundColor Green
    }
} else {
    Write-Host "[last30days] Cloning $RepoUrl ..." -ForegroundColor Yellow
    git clone --depth 1 --branch $Branch $RepoUrl $RepoDir
}

# Verify entry point exists
$EntryPoint = Join-Path $RepoDir "scripts" "last30days.py"
if (-not (Test-Path $EntryPoint)) {
    Write-Error "[last30days] Entry point not found: $EntryPoint"
    exit 1
}

# Check Python version
try {
    $pyVersion = & python --version 2>&1
    Write-Host "[last30days] System Python: $pyVersion" -ForegroundColor Gray
} catch {
    Write-Warning "[last30days] Python not found on PATH. Ensure Python 3.12+ is available."
}

Write-Host "[last30days] Setup complete. Engine at: $RepoDir" -ForegroundColor Green
Write-Host "[last30days] Configure API keys in: ~/.config/last30days/.env" -ForegroundColor Gray
