# =============================================================================
# Download New LoRA / Detector / Character packs — Batch 2
# Usage:  $env:CIVITAI_API_KEY = "your-key"
#         .\app\scripts\download_new_loras_batch2.ps1
#         .\app\scripts\download_new_loras_batch2.ps1 -DryRun
# =============================================================================
param(
    [switch]$DryRun,
    [string]$ApiKey = $env:CIVITAI_API_KEY
)

if (-not $ApiKey) {
    Write-Error "CivitAI API key not set. Export CIVITAI_API_KEY or pass -ApiKey."
    exit 1
}

$BaseDir = Join-Path $PSScriptRoot "..\..\ComfyUI\models"
$BaseDir = [System.IO.Path]::GetFullPath($BaseDir)
$LoraDir  = Join-Path $BaseDir "loras"
$BboxDir  = Join-Path $BaseDir "ultralytics\bbox"
$SegmDir  = Join-Path $BaseDir "ultralytics\segm"

# Ensure subdirs
foreach ($sub in @(
    "$LoraDir\effects\nsfw",
    "$LoraDir\effects\pose",
    "$LoraDir\effects\outfit",
    "$LoraDir\effects\expression",
    "$LoraDir\effects\medical",
    "$LoraDir\characters\zenless_zone_zero",
    "$LoraDir\characters\frieren",
    "$LoraDir\characters\nikke",
    "$LoraDir\characters\to_love_ru",
    "$LoraDir\characters\oshi_no_ko",
    "$LoraDir\characters\fire_emblem",
    "$LoraDir\characters\kantai_collection",
    "$LoraDir\characters\fate_hollow_ataraxia",
    "$LoraDir\characters\touhou",
    "$LoraDir\characters\fate",
    $BboxDir, $SegmDir
)) {
    if (-not (Test-Path $sub)) {
        New-Item -ItemType Directory -Path $sub -Force | Out-Null
    }
}

# ── Helper: Resolve version ID from civitai model ID ───────────────────
function Get-CivitaiVersionId {
    param([int]$ModelId)
    $url = "https://civitai.com/api/v1/models/$ModelId"
    $headers = @{ "Authorization" = "Bearer $ApiKey" }
    try {
        $resp = Invoke-RestMethod -Uri $url -Headers $headers -TimeoutSec 15
        $latest = $resp.modelVersions | Select-Object -First 1
        $file = $latest.files | Where-Object { $_.name -like "*.safetensors" -or $_.name -like "*.pt" -or $_.name -like "*.zip" } | Select-Object -First 1
        return @{
            version_id = $latest.id
            filename   = $file.name
            size_mb    = [math]::Round($file.sizeKB / 1024, 1)
        }
    } catch {
        Write-Warning "  Failed to query model $ModelId : $_"
        return $null
    }
}

# ── Download list ──────────────────────────────────────────────────────
# Format: civitai_model_id, target_subdir (relative to loras/ or ultralytics/), category label
$Models = @(
    # ─── NSFW / Anatomy effects ─────────────────────────────────
    @{ id = 11363;   subdir = "effects\nsfw";          label = "Spread Pussy" }
    @{ id = 17105;   subdir = "effects\nsfw";          label = "Some Perfect Pussy" }
    @{ id = 68107;   subdir = "effects\nsfw";          label = "Better Pussy v010" }
    @{ id = 22564;   subdir = "effects\nsfw";          label = "Lovely Pussy" }
    @{ id = 255148;  subdir = "effects\nsfw";          label = "Folded/Spread Pussy" }
    @{ id = 69531;   subdir = "effects\nsfw";          label = "Pussy Peek" }
    @{ id = 162832;  subdir = "effects\nsfw";          label = "Pussy Gaping Patch" }
    @{ id = 17028;   subdir = "effects\nsfw";          label = "Dikko Perfect Pussy" }
    @{ id = 1498136; subdir = "effects\nsfw";          label = "Pussy Spec Report IL" }
    @{ id = 17122;   subdir = "effects\nsfw";          label = "Better Pink Pussy" }
    @{ id = 144264;  subdir = "effects\nsfw";          label = "Pussy Show LoRA" }
    @{ id = 22901;   subdir = "effects\nsfw";          label = "Anal Hair Pony/1.5" }
    @{ id = 704418;  subdir = "effects\nsfw";          label = "All The Way In (Goofy)" }
    @{ id = 604841;  subdir = "effects\nsfw";          label = "69 Position Pony" }
    @{ id = 637921;  subdir = "effects\nsfw";          label = "Ass-to-Ass / Ass Press" }
    @{ id = 125639;  subdir = "effects\nsfw";          label = "Anal Beads (125639)" }
    @{ id = 12704;   subdir = "effects\nsfw";          label = "Anal Beads (12704)" }
    @{ id = 152366;  subdir = "effects\pose";          label = "Legs Together Anal Pose" }

    # ─── Pose / Concept LoRAs ───────────────────────────────────
    @{ id = 171863;  subdir = "effects\pose";          label = "Pet Play / All Fours" }
    @{ id = 2368542; subdir = "effects\medical";       label = "Medical Examination Room IL" }
    @{ id = 267756;  subdir = "effects\medical";       label = "Surgery Medical Bondage" }

    # ─── Detector: Pussy ADetailer ──────────────────────────────
    @{ id = 150234;  subdir = "_DETECTOR_BBOX";        label = "Pussy ADetailer" }

    # ─── Character packs (ALL-IN-ONE) ───────────────────────────
    @{ id = 471854;  subdir = "characters\zenless_zone_zero";   label = "All Chars ZZZ (Pony)" }
    @{ id = 558527;  subdir = "characters\frieren";             label = "All Chars Frieren" }
    @{ id = 677863;  subdir = "characters\nikke";               label = "All Chars NIKKE" }
    @{ id = 758394;  subdir = "characters\to_love_ru";          label = "All Chars To Love-Ru" }
    @{ id = 422352;  subdir = "characters\oshi_no_ko";          label = "All Chars Oshi no Ko" }
    @{ id = 539130;  subdir = "characters\fire_emblem";         label = "All Chars Fire Emblem" }
    @{ id = 832686;  subdir = "characters\kantai_collection";   label = "All Chars KanColle 440" }
    @{ id = 513404;  subdir = "characters\fate_hollow_ataraxia"; label = "All Chars Fate/HA" }
    @{ id = 818590;  subdir = "characters\zenless_zone_zero";   label = "ZZZ 15 Female SDXL" }
    @{ id = 413006;  subdir = "characters\touhou";              label = "Touhou 145 Chars Pony" }
    @{ id = 194989;  subdir = "characters\fate";                label = "Ishtar/Ereshkigal Duo" }
    @{ id = 804903;  subdir = "characters\idolmaster_cinderella"; label = "Idolmaster Cinderella 250" }
)

# ── Main download loop ────────────────────────────────────────────────
$total = $Models.Count
$ok = 0; $skip = 0; $fail = 0

Write-Host "`n=== Batch 2 Download: $total models ===" -ForegroundColor Cyan
Write-Host "API Key: $($ApiKey.Substring(0,8))..." -ForegroundColor DarkGray
Write-Host ""

foreach ($m in $Models) {
    $idx = $Models.IndexOf($m) + 1
    Write-Host "[$idx/$total] $($m.label) (civitai:$($m.id))..." -ForegroundColor Yellow -NoNewline

    # Resolve version ID + filename from API
    $info = Get-CivitaiVersionId -ModelId $m.id
    if (-not $info) {
        Write-Host " FAIL (API error)" -ForegroundColor Red
        $fail++
        continue
    }

    $versionId = $info.version_id
    $filename  = $info.filename
    $sizeMb    = $info.size_mb

    # Determine target directory
    if ($m.subdir -eq "_DETECTOR_BBOX") {
        $targetDir = $BboxDir
    } elseif ($m.subdir -eq "_DETECTOR_SEGM") {
        $targetDir = $SegmDir
    } else {
        $targetDir = Join-Path $LoraDir $m.subdir
    }

    $targetPath = Join-Path $targetDir $filename

    if (Test-Path $targetPath) {
        Write-Host " SKIP (exists: $filename)" -ForegroundColor DarkGray
        $skip++
        continue
    }

    Write-Host " v$versionId → $filename ($($sizeMb)MB)" -ForegroundColor White

    if ($DryRun) {
        Write-Host "  [DRY RUN] Would download to: $targetPath" -ForegroundColor DarkYellow
        $ok++
        continue
    }

    # Download
    $downloadUrl = "https://civitai.com/api/download/models/$versionId"
    $headers = @{ "Authorization" = "Bearer $ApiKey" }
    try {
        Invoke-WebRequest -Uri $downloadUrl -Headers $headers -OutFile $targetPath -TimeoutSec 300
        if (Test-Path $targetPath) {
            $actualSize = [math]::Round((Get-Item $targetPath).Length / 1MB, 1)
            Write-Host "  OK ($($actualSize)MB)" -ForegroundColor Green
            $ok++
        } else {
            Write-Host "  FAIL (file not created)" -ForegroundColor Red
            $fail++
        }
    } catch {
        Write-Host "  FAIL: $_" -ForegroundColor Red
        $fail++
        if (Test-Path $targetPath) { Remove-Item $targetPath -Force }
    }
}

Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "OK: $ok  |  Skipped: $skip  |  Failed: $fail  |  Total: $total"
Write-Host ""
