<#
build-lite-installer.ps1 — one-shot builder for the AI-Assistant LITE installer.

What it does:
  1. (Optional) `npm install` if node_modules is missing.
  2. Stage payload-lite/ via prepare-payload-lite.js.
  3. Run electron-builder with electron-builder-lite.yml (no models, no Python,
     no wheels — installer auto-fetches everything online on first install).

Output:
  <repo-root>/private/pre-installer/AI-Assistant-Lite-Setup-<version>.exe

Run:
  powershell -ExecutionPolicy Bypass -File scripts\build-lite-installer.ps1
#>
[CmdletBinding()]
param(
    [switch] $SkipNpmInstall
)

$ErrorActionPreference = 'Stop'

$ScriptDir   = Split-Path -Parent $MyInvocation.MyCommand.Path
$ElectronDir = Split-Path -Parent $ScriptDir
$RepoRoot    = Split-Path -Parent (Split-Path -Parent $ElectronDir)
$Output      = Join-Path $RepoRoot 'private\pre-installer'

Write-Host "==> AI-Assistant LITE installer build" -ForegroundColor Cyan
Write-Host "    electronDir : $ElectronDir"
Write-Host "    repoRoot    : $RepoRoot"
Write-Host "    output      : $Output"

New-Item -ItemType Directory -Path $Output -Force | Out-Null

Push-Location $ElectronDir
try {
    if (-not $SkipNpmInstall) {
        if (-not (Test-Path (Join-Path $ElectronDir 'node_modules\electron-builder'))) {
            Write-Host "==> npm install" -ForegroundColor Cyan
            & npm install
            if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
        }
    }

    Write-Host "==> Staging payload-lite/ ..." -ForegroundColor Cyan
    & node scripts\prepare-payload-lite.js
    if ($LASTEXITCODE -ne 0) { throw "prepare-payload-lite.js failed" }

    Write-Host "==> Running electron-builder (lite) ..." -ForegroundColor Cyan
    $logPath = Join-Path $Output 'build-lite.log'
    & npx electron-builder --win nsis --x64 --config electron-builder-lite.yml --publish never 2>&1 |
        Tee-Object -FilePath $logPath
    if ($LASTEXITCODE -ne 0) { throw "electron-builder failed (see $logPath)" }

    Write-Host "`n==> DONE. Installer + log written to:" -ForegroundColor Green
    Get-ChildItem $Output -Filter 'AI-Assistant-Lite-Setup-*.exe' |
        Format-Table Name, @{N='SizeMB';E={[math]::Round($_.Length/1MB,1)}}, LastWriteTime
}
finally {
    Pop-Location
}
