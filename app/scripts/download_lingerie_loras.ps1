#!/usr/bin/env pwsh
# download_lingerie_loras.ps1
# Downloads 11 lingerie LoRA models from CivitAI into ComfyUI/models/loras/
# Usage: .\app\scripts\download_lingerie_loras.ps1

$API_KEY = "aac46d81619df057bb514b8598802501"
$DEST = Join-Path $PSScriptRoot "..\..\ComfyUI\models\loras"

New-Item -ItemType Directory -Force -Path $DEST | Out-Null

$headers = @{ Authorization = "Bearer $API_KEY" }

$loras = @(
    @{
        url      = "https://civitai.com/api/download/models/100290"
        filename = "detailBra-000001.safetensors"
        label    = "Lingerie Helper v1.0 (SD 1.5)"
    },
    @{
        url      = "https://civitai.com/api/download/models/762484"
        filename = "sexy lingerie 2_pony_V1.1.safetensors"
        label    = "2sexy Lingerie v1.0 Pony"
    },
    @{
        url      = "https://civitai.com/api/download/models/1254437"
        filename = "AngelLingerieILL.safetensors"
        label    = "Angel Lingerie (Illustrious)"
    },
    @{
        url      = "https://civitai.com/api/download/models/1821357"
        filename = "lingerie 02 - Shizuka Harness (Ill) v1.safetensors"
        label    = "Lingerie 02 Shizuka Harness (Illustrious)"
    },
    @{
        url      = "https://civitai.com/api/download/models/1470628"
        filename = "Lingerie 01 - Kanon Leotard Ill v1.safetensors"
        label    = "Lingerie 01 Kanon Leotard (Illustrious)"
    },
    @{
        url      = "https://civitai.com/api/download/models/1250522"
        filename = "HollowSeethroughLingerieILL.safetensors"
        label    = "Hollow See-Through Lingerie (Illustrious)"
    },
    @{
        url      = "https://civitai.com/api/download/models/2232188"
        filename = "Chitose_Style_Lingerie-000008.safetensors"
        label    = "Chitose Style Lingerie (Illustrious)"
    },
    @{
        url      = "https://civitai.com/api/download/models/1964686"
        filename = "GyaruBabydollLingerieILL.safetensors"
        label    = "Gyaru Babydoll Lingerie (Illustrious)"
    },
    @{
        url      = "https://civitai.com/api/download/models/1426134"
        filename = "lingerie_miwabe_illustrious.safetensors"
        label    = "Lingerie Miwabe Sakura (Illustrious)"
    },
    @{
        url      = "https://civitai.com/api/download/models/1968047"
        filename = "Sexy_Transparent_Lingerie.safetensors"
        label    = "Sexy Transparent Lingerie (Illustrious)"
    },
    @{
        url      = "https://civitai.com/api/download/models/1015675"
        filename = "Lingerie 03 - Christmas Eve Detective.safetensors"
        label    = "Lingerie 03 Christmas Detective (Pony)"
    }
)

$i = 0
foreach ($lora in $loras) {
    $i++
    $dest_file = Join-Path $DEST $lora.filename

    if (Test-Path $dest_file) {
        Write-Host "[$i/$($loras.Count)] SKIP (exists): $($lora.label)"
        continue
    }

    Write-Host "[$i/$($loras.Count)] Downloading: $($lora.label)"
    Write-Host "  -> $($lora.filename)"

    try {
        Invoke-WebRequest `
            -Uri $lora.url `
            -Headers $headers `
            -OutFile $dest_file `
            -UseBasicParsing `
            -TimeoutSec 600

        $size_mb = [math]::Round((Get-Item $dest_file).Length / 1MB, 1)
        Write-Host "  OK  $size_mb MB" -ForegroundColor Green
    }
    catch {
        Write-Host "  FAIL: $_" -ForegroundColor Red
        # Remove partial file
        if (Test-Path $dest_file) { Remove-Item $dest_file -Force }
    }

    # Small pause to be polite to the API
    Start-Sleep -Milliseconds 500
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
$downloaded = (Get-ChildItem $DEST -Filter "*.safetensors").Count
Write-Host "Total .safetensors in $DEST : $downloaded"
