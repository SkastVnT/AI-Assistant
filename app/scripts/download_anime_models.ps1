#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Download anime-quality checkpoints, LoRAs, and VAEs recommended for LOCAL ComfyUI mode.
  
  Models downloaded:
    Checkpoints: Animagine XL 4.0 Opt, NoobAI XL 1.1, ChenkinNoob-XL V0.2
    LoRAs (SDXL): anime-detailer-xl, style-enhancer-xl, dynamic-anatomy,
                  striking-a-confident-pose, huge-anime-eyes, headshot, messy-hair
    VAE:          sdxl-vae-fp16-fix (recommended for SDXL anime)

.NOTES
  Requirements: Hugging Face account (free).
    Option A — Token-based (recommended for models that require login):
      $env:HF_TOKEN = "hf_..."
    Option B — No token needed for public models.

  Target paths (relative to repo root):
    Checkpoints  → ComfyUI/models/checkpoints/
    LoRAs        → ComfyUI/models/loras/anime-quality/
    VAE          → ComfyUI/models/vae/
#>

param(
    [string]$Root = (Resolve-Path "$PSScriptRoot\..\..\ComfyUI").Path,
    [string]$HFToken = $env:HF_TOKEN,
    [switch]$SkipCheckpoints,
    [switch]$SkipLoras,
    [switch]$SkipVae,
    [switch]$SkipAdetailer,
    [switch]$SkipControlnet
)

$CkptDir       = Join-Path $Root "models\checkpoints"
$LoraDir       = Join-Path $Root "models\loras\anime-quality"
$VaeDir        = Join-Path $Root "models\vae"
$AdetailerDir  = Join-Path $Root "models\ultralytics\bbox"
$ControlnetDir = Join-Path $Root "models\controlnet"

foreach ($d in @($CkptDir, $LoraDir, $VaeDir, $AdetailerDir, $ControlnetDir)) {
    New-Item -ItemType Directory -Force -Path $d | Out-Null
}

# ── Helpers ───────────────────────────────────────────────────────────────

function Get-HFFile {
    param(
        [string]$Repo,
        [string]$Filename,
        [string]$DestDir,
        [string]$Token = $HFToken
    )
    $destFile = Join-Path $DestDir (Split-Path $Filename -Leaf)
    if (Test-Path $destFile) {
        Write-Host "  [skip] Already exists: $destFile" -ForegroundColor DarkGray
        return
    }

    $url = "https://huggingface.co/$Repo/resolve/main/$Filename"
    $headers = @{}
    if ($Token) { $headers["Authorization"] = "Bearer $Token" }

    Write-Host "  [download] $Repo / $Filename" -ForegroundColor Cyan
    Write-Host "    -> $destFile"

    try {
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -Uri $url -Headers $headers -OutFile $destFile -UseBasicParsing
        $sizeMB = [math]::Round((Get-Item $destFile).Length / 1MB, 1)
        Write-Host "  [ok] ${sizeMB} MB" -ForegroundColor Green
    } catch {
        Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
        if (Test-Path $destFile) { Remove-Item $destFile -Force }
    }
}

# ── 1. Checkpoints ────────────────────────────────────────────────────────

if (-not $SkipCheckpoints) {
    Write-Host "`n=== Checkpoints ===" -ForegroundColor Yellow

    # Animagine XL 4.0 Opt  (~6.7 GB) — stable, anatomy accuracy
    Get-HFFile `
        -Repo "cagliostrolab/animagine-xl-4.0" `
        -Filename "animagine-xl-4.0-opt.safetensors" `
        -DestDir $CkptDir

    # NoobAI XL 1.1  (~6.7 GB) — Danbooru/e621 native tags, SDXL base
    # Note: tagged Not-For-All-Audiences on HF; login required
    Get-HFFile `
        -Repo "Laxhar/noobai-XL-1.1" `
        -Filename "noobaiXLVpred_v11.safetensors" `
        -DestDir $CkptDir

    # ChenkinNoob-XL V0.2  (~6.7 GB) — character consistency, detail fidelity
    Get-HFFile `
        -Repo "ChenkinNoob/ChenkinNoob-XL-V0.2" `
        -Filename "ChenkinNoob-XL-V0.2.safetensors" `
        -DestDir $CkptDir

    # Kohaku XL Delta rev1  (~6.7 GB) — Illustrious-based, ultra-clean anime art
    # Exceptional for character portraits, soft shading, vivid colors
    Get-HFFile `
        -Repo "KBlueLeaf/kohaku-XL-delta-rev1" `
        -Filename "kohakuXLDelta_rev1.safetensors" `
        -DestDir $CkptDir
}

# ── 2. LoRAs (SDXL) ──────────────────────────────────────────────────────

if (-not $SkipLoras) {
    Write-Host "`n=== LoRAs ===" -ForegroundColor Yellow

    # Detail / style
    Get-HFFile `
        -Repo "Linaqruf/anime-detailer-xl-lora" `
        -Filename "anime-detailer-xl.safetensors" `
        -DestDir $LoraDir
    Rename-Item -Path (Join-Path $LoraDir "anime-detailer-xl.safetensors") `
                -NewName "anime_detailer_xl.safetensors" -ErrorAction SilentlyContinue

    Get-HFFile `
        -Repo "Linaqruf/style-enhancer-xl-lora" `
        -Filename "style-enhancer-xl.safetensors" `
        -DestDir $LoraDir
    Rename-Item -Path (Join-Path $LoraDir "style-enhancer-xl.safetensors") `
                -NewName "style_enhancer_xl.safetensors" -ErrorAction SilentlyContinue

    # Anatomy / pose
    Get-HFFile `
        -Repo "ntc-ai/SDXL-LoRA-slider.dynamic-anatomy" `
        -Filename "dynamic anatomy.safetensors" `
        -DestDir $LoraDir

    Get-HFFile `
        -Repo "ntc-ai/SDXL-LoRA-slider.striking-a-confident-pose" `
        -Filename "striking a confident pose.safetensors" `
        -DestDir $LoraDir

    # Eyes / face
    Get-HFFile `
        -Repo "ntc-ai/SDXL-LoRA-slider.huge-anime-eyes" `
        -Filename "huge anime eyes.safetensors" `
        -DestDir $LoraDir

    Get-HFFile `
        -Repo "ntc-ai/SDXL-LoRA-slider.headshot" `
        -Filename "headshot.safetensors" `
        -DestDir $LoraDir

    # Hair
    Get-HFFile `
        -Repo "ntc-ai/SDXL-LoRA-slider.messy-hair" `
        -Filename "messy hair.safetensors" `
        -DestDir $LoraDir

    # Gaze / iris — looking at viewer: anchor gaze, improve iris "contact" feel
    Get-HFFile `
        -Repo "ntc-ai/SDXL-LoRA-slider.looking-at-viewer" `
        -Filename "looking at viewer.safetensors" `
        -DestDir $LoraDir

    # Fine detail — extremely detailed: adds extra fine lines in iris, lashes, face
    Get-HFFile `
        -Repo "ntc-ai/SDXL-LoRA-slider.extremely-detailed" `
        -Filename "extremely detailed.safetensors" `
        -DestDir $LoraDir

    # Micro detail — pupil texture, catchlight, lash tips, iris ring
    Get-HFFile `
        -Repo "ntc-ai/SDXL-LoRA-slider.micro-details-fine-details-detailed" `
        -Filename "micro details, fine details, detailed.safetensors" `
        -DestDir $LoraDir
}

# ── 3. VAE ────────────────────────────────────────────────────────────────

if (-not $SkipVae) {
    Write-Host "`n=== VAE ===" -ForegroundColor Yellow

    # sdxl-vae-fp16-fix — fixes grey/blown-out issue on SDXL at fp16
    Get-HFFile `
        -Repo "madebyollin/sdxl-vae-fp16-fix" `
        -Filename "sdxl_vae.safetensors" `
        -DestDir $VaeDir
}

# ── 4. ADetailer / Ultralytics YOLO detectors ────────────────────────────
# Used by ComfyUI Impact Pack for automatic face/hand detection + inpaint.
# Requires: ComfyUI-Impact-Pack custom node (install via ComfyUI Manager).

if (-not $SkipAdetailer) {
    Write-Host "`n=== ADetailer YOLO Models ===" -ForegroundColor Yellow

    # Face detector — best for face fix pass
    Get-HFFile `
        -Repo "Bingsu/adetailer" `
        -Filename "face_yolov8n.pt" `
        -DestDir $AdetailerDir

    # Hand detector — best for hand fix pass
    Get-HFFile `
        -Repo "Bingsu/adetailer" `
        -Filename "hand_yolov8n.pt" `
        -DestDir $AdetailerDir

    Write-Host "  [note] These require ComfyUI-Impact-Pack to use." -ForegroundColor DarkYellow
    Write-Host "         Install via ComfyUI Manager: search 'Impact Pack'" -ForegroundColor DarkYellow
}

# ── 5. ControlNet (SDXL) ─────────────────────────────────────────────────
# OpenPose for SDXL — use for complex pose guidance (full-body / hands).
# Usage: provide a pose reference image alongside your prompt in img2img mode.

if (-not $SkipControlnet) {
    Write-Host "`n=== ControlNet (SDXL) ===" -ForegroundColor Yellow

    # OpenPose XL2 (~1.4 GB) — best for full-body / hand / face pose control
    Get-HFFile `
        -Repo "thibaud/controlnet-openpose-sdxl-1.0" `
        -Filename "OpenPoseXL2.safetensors" `
        -DestDir $ControlnetDir

    Write-Host "  [note] For txt2img pose control, supply a DWPose skeleton image as source." -ForegroundColor DarkYellow
}

# ── Summary ───────────────────────────────────────────────────────────────

Write-Host "`n=== Done ===" -ForegroundColor Green
Write-Host "Checkpoints  : $CkptDir"
Write-Host "LoRAs        : $LoraDir"
Write-Host "VAE          : $VaeDir"
Write-Host "ADetailer    : $AdetailerDir"
Write-Host "ControlNet   : $ControlnetDir"
Write-Host ""
Write-Host "Next step: restart ComfyUI, then the chatbot will auto-discover the new models." -ForegroundColor Cyan
Write-Host "LoRA trigger words:"
Write-Host "  dynamic anatomy  |  striking a confident pose  |  huge anime eyes  |  headshot  |  messy hair" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "ADetailer/Impact Pack setup (face + hand fix):" -ForegroundColor Cyan
Write-Host "  1. Open ComfyUI  2. ComfyUI Manager -> Install Custom Nodes -> search 'Impact Pack'" -ForegroundColor DarkCyan
Write-Host "  3. Restart ComfyUI -- YOLO models in models/ultralytics/bbox/ are auto-detected" -ForegroundColor DarkCyan
Write-Host ""
Write-Host "ControlNet OpenPose usage:" -ForegroundColor Cyan
Write-Host "  Provide a DWPose / OpenPose skeleton image as source in img2img mode." -ForegroundColor DarkCyan
Write-Host "  SDXL model: OpenPoseXL2.safetensors" -ForegroundColor DarkCyan
