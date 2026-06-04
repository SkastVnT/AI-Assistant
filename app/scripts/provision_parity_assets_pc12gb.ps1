#!/usr/bin/env pwsh
<#
.SYNOPSIS
  Download and verify the 5 assets required for pc_12gb parity preflight.

  Assets:
    1. xinsir-controlnet-union-sdxl-1.0.safetensors  → ComfyUI/models/controlnet/
    2. yolox_l.onnx  (DWPose bbox detector)           → services/edit-image/ComfyUI/…/DWPose/
    3. dw-ll_ucoco_384_bs5.torchscript.pt             → services/edit-image/ComfyUI/…/DWPose/
    4. ip-adapter-plus-face_sdxl_vit-h.safetensors    → ComfyUI/models/ipadapter/
    5. CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors    → ComfyUI/models/clip_vision/

  After downloading, run this script again with -ComputeChecksums to print sha256
  values for pasting into anime_pipeline_assets.yaml.

.PARAMETER Root
  Repository root (default: two levels above this script).
.PARAMETER HFToken
  Optional HuggingFace token for authenticated downloads. Set via $env:HF_TOKEN.
.PARAMETER ComputeChecksums
  Skip downloads; compute and print sha256 for all target files that exist.
.PARAMETER SkipExisting
  Skip files that already exist on disk (default: true).

.NOTES
  The WAI SDXL checkpoint (waiIllustriousSDXL_v170.safetensors) is NOT downloaded
  here — it must be obtained manually from https://civitai.com/models/827184
  and placed at ComfyUI/models/checkpoints/waiIllustriousSDXL_v170.safetensors.
#>

param(
    [string]$Root = (Resolve-Path "$PSScriptRoot\..\.." -ErrorAction SilentlyContinue).Path,
    [string]$HFToken = $env:HF_TOKEN,
    [switch]$ComputeChecksums,
    [switch]$SkipExisting = $true
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

if (-not $Root -or -not (Test-Path $Root)) {
    $Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
}

$ComfyDir    = Join-Path $Root "ComfyUI"
$EditImageComfyDir = Join-Path $Root "services\edit-image\ComfyUI"

# ── Asset table ───────────────────────────────────────────────────────────────
$assets = @(
    @{
        id          = "xinsir_controlnet_union_sdxl"
        destDir     = Join-Path $ComfyDir "models\controlnet"
        destName    = "xinsir-controlnet-union-sdxl-1.0.safetensors"
        hfRepo      = "xinsir/controlnet-union-sdxl-1.0"
        hfFile      = "diffusion_pytorch_model_promax.safetensors"
        license     = "Apache-2.0"
    },
    @{
        id          = "dwpose_bbox_detector"
        destDir     = Join-Path $EditImageComfyDir "custom_nodes\comfyui_controlnet_aux\ckpts\yzd-v\DWPose"
        destName    = "yolox_l.onnx"
        hfRepo      = "yzd-v/DWPose"
        hfFile      = "yolox_l.onnx"
        license     = "Apache-2.0"
    },
    @{
        id          = "dwpose_pose_estimator"
        destDir     = Join-Path $EditImageComfyDir "custom_nodes\comfyui_controlnet_aux\ckpts\yzd-v\DWPose"
        destName    = "dw-ll_ucoco_384_bs5.torchscript.pt"
        hfRepo      = "yzd-v/DWPose"
        hfFile      = "dw-ll_ucoco_384_bs5.torchscript.pt"
        license     = "Apache-2.0"
    },
    @{
        id          = "ipadapter_plus_face_sdxl_vit_h"
        destDir     = Join-Path $ComfyDir "models\ipadapter"
        destName    = "ip-adapter-plus-face_sdxl_vit-h.safetensors"
        hfRepo      = "h94/IP-Adapter"
        hfFile      = "sdxl_models/ip-adapter-plus-face_sdxl_vit-h.safetensors"
        license     = "Apache-2.0"
    },
    @{
        id          = "clip_vision_vit_h"
        destDir     = Join-Path $ComfyDir "models\clip_vision"
        destName    = "CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
        hfRepo      = "laion/CLIP-ViT-H-14-laion2B-s32B-b79K"
        hfFile      = "model.safetensors"
        license     = "MIT"
    }
)

# ── Helpers ───────────────────────────────────────────────────────────────────

function Get-HFFile {
    param([string]$Repo, [string]$HFFile, [string]$DestDir, [string]$DestName, [string]$Token)

    $destPath = Join-Path $DestDir $DestName
    if ($SkipExisting -and (Test-Path $destPath)) {
        Write-Host "  [skip] already exists: $destPath" -ForegroundColor DarkGray
        return
    }

    $url = "https://huggingface.co/$Repo/resolve/main/$HFFile"
    $headers = @{}
    if ($Token) { $headers["Authorization"] = "Bearer $Token" }

    New-Item -ItemType Directory -Force -Path $DestDir | Out-Null
    Write-Host "  [download] $Repo / $HFFile" -ForegroundColor Cyan
    Write-Host "    -> $destPath"

    $tmp = "$destPath.tmp"
    try {
        $ProgressPreference = "SilentlyContinue"
        Invoke-WebRequest -Uri $url -Headers $headers -OutFile $tmp -UseBasicParsing
        Move-Item -Path $tmp -Destination $destPath -Force
        $sizeMB = [math]::Round((Get-Item $destPath).Length / 1MB, 1)
        Write-Host "  [ok] ${sizeMB} MB" -ForegroundColor Green
    } catch {
        if (Test-Path $tmp) { Remove-Item $tmp -Force }
        Write-Host "  [FAIL] $($_.Exception.Message)" -ForegroundColor Red
    }
}

function Get-FileSHA256 {
    param([string]$Path)
    (Get-FileHash $Path -Algorithm SHA256).Hash.ToLower()
}

# ── Checksum-only mode ────────────────────────────────────────────────────────

if ($ComputeChecksums) {
    Write-Host "`n=== SHA256 checksums for anime_pipeline_assets.yaml ===" -ForegroundColor Yellow
    foreach ($asset in $assets) {
        $destPath = Join-Path $asset.destDir $asset.destName
        if (Test-Path $destPath) {
            Write-Host "  Computing $($asset.id)..." -NoNewline
            $hash = Get-FileSHA256 $destPath
            Write-Host " done"
            Write-Host "  $($asset.id):"
            Write-Host "    sha256: `"$hash`""
        } else {
            Write-Host "  [missing] $($asset.id): $destPath" -ForegroundColor DarkYellow
        }
    }
    Write-Host ""
    return
}

# ── Download mode ─────────────────────────────────────────────────────────────

Write-Host "`n=== Provisioning pc_12gb parity assets ===" -ForegroundColor Yellow
Write-Host "  Root: $Root"
if ($HFToken) {
    Write-Host "  HF Token: set (authenticated downloads)" -ForegroundColor Green
} else {
    Write-Host "  HF Token: not set (public models only)" -ForegroundColor DarkYellow
}

foreach ($asset in $assets) {
    Write-Host "`n--- $($asset.id) ---"
    Get-HFFile `
        -Repo    $asset.hfRepo `
        -HFFile  $asset.hfFile `
        -DestDir $asset.destDir `
        -DestName $asset.destName `
        -Token   $HFToken
}

Write-Host "`n=== Done ===" -ForegroundColor Yellow
Write-Host "After all files are downloaded, run with -ComputeChecksums to get sha256 values."
Write-Host "Paste the hashes into app/configs_vps/anime_pipeline_assets.yaml."
Write-Host "Then re-run: python app/scripts/check_anime_pipeline_assets.py --parity --json"
