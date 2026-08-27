# build-installer.ps1 — orchestrate the full Windows installer build for AI-Assistant.
#
# Prerequisites (one-time, on the build machine):
#   1. Node.js 20+ and npm
#   2. Python 3.11.x portable extracted to:
#        app/electron/payload/python311/python.exe
#      Get embeddable zip + bootstrap pip — see PACKAGING.md.
#   3. Wheel caches downloaded (one-time):
#        app/electron/payload/wheels/core/
#        app/electron/payload/wheels/image/
#      See `Build-Wheels` step below.
#   4. (Optional) Code-signing cert: set $env:CSC_LINK and $env:CSC_KEY_PASSWORD.
#
# Usage:
#   cd app/electron
#   powershell -ExecutionPolicy Bypass -File scripts\build-installer.ps1
#   powershell -ExecutionPolicy Bypass -File scripts\build-installer.ps1 -BuildWheels
#   powershell -ExecutionPolicy Bypass -File scripts\build-installer.ps1 -DirOnly
#
# Output:
#   <repo-root>\private\install\AI-Assistant-Setup-<version>.exe

[CmdletBinding()]
param(
    [switch]$BuildWheels,   # (re)download wheel cache before building
    [switch]$DirOnly,       # build unpacked dir only (faster, for sanity checks)
    [switch]$SkipPayload,   # skip prepare-payload (already staged)
    [switch]$SkipNpmInstall # skip npm install (already done)
)

$ErrorActionPreference = 'Stop'
$ElectronDir = Split-Path -Parent $PSScriptRoot
$RepoRoot    = Resolve-Path (Join-Path $ElectronDir '..\..')
$Payload     = Join-Path $ElectronDir 'payload'
$Output      = Join-Path $RepoRoot 'private\install'

Write-Host "==> AI-Assistant installer build" -ForegroundColor Cyan
Write-Host "    repo root : $RepoRoot"
Write-Host "    electron  : $ElectronDir"
Write-Host "    payload   : $Payload"
Write-Host "    output    : $Output"
Write-Host ""

# Ensure output dir exists
New-Item -ItemType Directory -Force -Path $Output | Out-Null

Push-Location $ElectronDir
try {
    if (-not $SkipNpmInstall) {
        Write-Host "==> npm install" -ForegroundColor Cyan
        npm install
        if ($LASTEXITCODE -ne 0) { throw "npm install failed" }
    }

    if ($BuildWheels) {
        Write-Host "==> Building wheel caches (offline pip mirror)" -ForegroundColor Cyan
        $coreReq  = Join-Path $RepoRoot 'app/requirements/freeze-venv-core.txt'
        $imageReq = Join-Path $RepoRoot 'app/requirements/freeze-venv-image.txt'
        $coreOut  = Join-Path $Payload 'wheels\core'
        $imageOut = Join-Path $Payload 'wheels\image'

        # Prefer the bundled standalone Python so wheel cache matches the runtime
        # the installer will use to build venvs on the target machine.
        $py = Join-Path $Payload 'python311\python.exe'
        if (-not (Test-Path $py)) {
            $py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
        }
        if (-not $py) { throw "python.exe not found (no bundled python311 + none on PATH)" }

        New-Item -ItemType Directory -Force -Path $coreOut, $imageOut | Out-Null

        Write-Host "    -> downloading core wheels to $coreOut"
        & $py -m pip download -r $coreReq -d $coreOut --no-deps --prefer-binary
        if ($LASTEXITCODE -ne 0) { Write-Warning "core wheel download had issues (exit $LASTEXITCODE)" }

        Write-Host "    -> downloading image wheels to $imageOut"
        & $py -m pip download -r $imageReq -d $imageOut --no-deps --prefer-binary
        if ($LASTEXITCODE -ne 0) { Write-Warning "image wheel download had issues (exit $LASTEXITCODE)" }

        # Torch (CUDA) is not pinned in freeze-venv-image.txt — fetch from
        # PyTorch's index. Adjust version + cu* tag if you upgrade torch.
        Write-Host "    -> downloading CUDA torch trio (cu128)"
        & $py -m pip download torch==2.11.0+cu128 torchvision==0.26.0+cu128 torchaudio==2.11.0+cu128 `
            -d $imageOut --no-deps --extra-index-url https://download.pytorch.org/whl/cu128
        if ($LASTEXITCODE -ne 0) { Write-Warning "torch+cu128 download had issues (exit $LASTEXITCODE)" }
    }

    if (-not $SkipPayload) {
        Write-Host "==> Staging payload" -ForegroundColor Cyan
        node scripts\prepare-payload.js
        if ($LASTEXITCODE -ne 0) { throw "prepare-payload.js failed" }
    }

    # Sanity checks before invoking electron-builder.
    $py = Join-Path $Payload 'python311\python.exe'
    if (-not (Test-Path $py)) {
        throw "Bundled Python missing: $py`r`nDrop a portable Python 3.11 there. See PACKAGING.md."
    }
    if (-not (Test-Path (Join-Path $Payload 'wheels\core'))) {
        Write-Warning "wheels/core not found — re-run with -BuildWheels."
    }
    if (-not (Test-Path (Join-Path $Payload 'wheels\image'))) {
        Write-Warning "wheels/image not found — re-run with -BuildWheels."
    }

    Write-Host "==> electron-builder" -ForegroundColor Cyan
    if ($DirOnly) {
        npx electron-builder --win --dir --x64 --publish never
    } else {
        npx electron-builder --win nsis --x64 --publish never
    }
    if ($LASTEXITCODE -ne 0) { throw "electron-builder failed (exit $LASTEXITCODE)" }

    Write-Host ""
    Write-Host "==> DONE" -ForegroundColor Green
    Write-Host "Installer(s) in: $Output"
    Get-ChildItem $Output -Filter 'AI-Assistant-Setup-*.exe' -ErrorAction SilentlyContinue |
        ForEach-Object { Write-Host ("  - {0}  ({1:N2} GB)" -f $_.Name, ($_.Length / 1GB)) }
}
finally {
    Pop-Location
}
