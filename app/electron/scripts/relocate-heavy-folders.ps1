<#
relocate-heavy-folders.ps1 — moves the three heaviest reproducible folders
off the system drive (C:) onto a data drive (default E:) and replaces them
with NTFS directory junctions, so all existing scripts/paths keep working.

Usage:
  powershell -ExecutionPolicy Bypass -File scripts\relocate-heavy-folders.ps1
  # or override target:
  powershell ... -DataRoot 'D:\ai-data'

Idempotent: skips folders already moved (junction present) or already missing.
#>
[CmdletBinding()]
param(
    [string] $RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..\..')).Path,
    [string] $DataRoot = 'E:\my-chat-bot'
)

$ErrorActionPreference = 'Stop'

$pairs = @(
    @{ Src = 'app\electron\payload';            Dst = 'electron-payload' }
    @{ Src = 'private\install\win-unpacked';    Dst = 'install\win-unpacked' }
    @{ Src = 'private\install\nsis-web';        Dst = 'install\nsis-web' }
)

function Test-IsJunction([string]$Path) {
    if (-not (Test-Path $Path)) { return $false }
    $item = Get-Item $Path -Force
    return ($item.Attributes -band [IO.FileAttributes]::ReparsePoint) -ne 0
}

foreach ($pair in $pairs) {
    $src = Join-Path $RepoRoot $pair.Src
    $dst = Join-Path $DataRoot $pair.Dst

    Write-Host "`n=== $($pair.Src) ===" -ForegroundColor Cyan

    if (Test-IsJunction $src) {
        Write-Host "  already a junction \u2192 skip"
        continue
    }
    if (-not (Test-Path $src)) {
        Write-Host "  source missing \u2192 skip"
        continue
    }

    New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null

    if (Test-Path $dst) {
        Write-Host "  destination exists at $dst \u2014 will robocopy /MOVE merge"
    }

    Write-Host "  robocopy /MOVE \u2192 $dst"
    robocopy $src $dst /MOVE /E /MT:16 /R:1 /W:1 /NFL /NDL /NP /NJH /NJS
    if ($LASTEXITCODE -gt 7) { throw "robocopy failed (exit $LASTEXITCODE)" }

    Write-Host "  creating junction"
    cmd /c mklink /J `"$src`" `"$dst`" | Out-Null
    if (-not (Test-IsJunction $src)) { throw "junction creation failed for $src" }

    Write-Host "  done." -ForegroundColor Green
}

Write-Host "`nAll relocations complete." -ForegroundColor Green
Get-PSDrive C, E | Select-Object Name, @{N='FreeGB';E={[math]::Round($_.Free/1GB,1)}}
