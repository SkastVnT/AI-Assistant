# Expose LORA/new_2/* to ComfyUI via directory junctions + 1 hardlink.
# Safe: idempotent, never deletes real data, skips existing links/files.
# Run from repo root (no admin required on NTFS / same volume).

param(
    [switch]$WhatIf
)

$ErrorActionPreference = 'Stop'
$root = (Get-Location).Path

function Ensure-Junction($linkPath, $target) {
    if (-not (Test-Path $target)) {
        Write-Host "  skip (target missing): $target" -ForegroundColor Yellow
        return
    }
    if (Test-Path $linkPath) {
        $item = Get-Item $linkPath -Force
        $isLink = $item.Attributes -band [IO.FileAttributes]::ReparsePoint
        if ($isLink) {
            Write-Host "  exists (junction): $linkPath" -ForegroundColor DarkGray
        } else {
            Write-Host "  SKIP (real dir, not touching): $linkPath" -ForegroundColor Red
        }
        return
    }
    if ($WhatIf) {
        Write-Host "  would link: $linkPath -> $target" -ForegroundColor Cyan
        return
    }
    New-Item -ItemType Junction -Path $linkPath -Target $target | Out-Null
    Write-Host "  LINK: $linkPath -> $target" -ForegroundColor Green
}

function Ensure-Hardlink($linkPath, $target) {
    if (-not (Test-Path $target)) {
        Write-Host "  skip (target missing): $target" -ForegroundColor Yellow
        return
    }
    if (Test-Path $linkPath) {
        Write-Host "  exists: $linkPath" -ForegroundColor DarkGray
        return
    }
    if ($WhatIf) {
        Write-Host "  would hardlink: $linkPath -> $target" -ForegroundColor Cyan
        return
    }
    New-Item -ItemType HardLink -Path $linkPath -Target $target | Out-Null
    Write-Host "  HLINK: $linkPath -> $target" -ForegroundColor Green
}

$loraRoot  = Join-Path $root 'ComfyUI\models\loras'
$ultraRoot = Join-Path $root 'ComfyUI\models\ultralytics'
$src       = Join-Path $root 'LORA\new_2'

if (-not (Test-Path $ultraRoot)) { New-Item -ItemType Directory -Path $ultraRoot | Out-Null }

Write-Host "=== LoRA junctions ===" -ForegroundColor Cyan
Ensure-Junction (Join-Path $loraRoot  'new_2_character')  (Join-Path $src 'character')
Ensure-Junction (Join-Path $loraRoot  'new_2_style')      (Join-Path $src 'style')
Ensure-Junction (Join-Path $loraRoot  'new_2_eyes')       (Join-Path $src 'eyes')
Ensure-Junction (Join-Path $loraRoot  'new_2_expression') (Join-Path $src 'expression')
Ensure-Junction (Join-Path $loraRoot  'new_2_pixai')      (Join-Path $src 'pixai_mirror')

Write-Host "`n=== Ultralytics junction ===" -ForegroundColor Cyan
Ensure-Junction (Join-Path $ultraRoot 'new_2')            (Join-Path $src 'detection')

Write-Host "`n=== PixAI root file hardlink ===" -ForegroundColor Cyan
# PixAI model 2001904744702518492 "chubby styleXL" (244 MB) ??? treat as style LoRA
$pixaiHardlink = Join-Path $loraRoot 'new_2_pixai\chubby_styleXL.safetensors'
Ensure-Hardlink $pixaiHardlink (Join-Path $src 'checkpoint-e18_s324.safetensors')

Write-Host "`n=== Note ===" -ForegroundColor Cyan
$wai = Join-Path $root 'ComfyUI\models\checkpoints\waiIllustriousSDXL_v170.safetensors'
if (Test-Path $wai) {
    Write-Host "  waiIllustriousSDXL_v170 already in checkpoints/ ??? duplicate at LORA\new_2\checkpoint\ may be deleted manually." -ForegroundColor Yellow
}

Write-Host '
Done.' -ForegroundColor Green

