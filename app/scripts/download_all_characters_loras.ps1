# =============================================================================
# Download All-Characters LoRA packs from CivitAI
# Usage:  .\app\scripts\download_all_characters_loras.ps1
#         .\app\scripts\download_all_characters_loras.ps1 -DryRun
# =============================================================================
param(
    [switch]$DryRun
)

$ApiKey    = 
$TargetDir = Join-Path $PSScriptRoot "..\..\ComfyUI\models\loras"
$TargetDir = [System.IO.Path]::GetFullPath($TargetDir)

if (-not (Test-Path $TargetDir)) {
    New-Item -ItemType Directory -Path $TargetDir -Force | Out-Null
    Write-Host "Created directory: $TargetDir"
}

# Format: @{ version_id; local_name; civitai_filename (actual server name); description }
$Downloads = @(
    @{
        version_id       = 554678
        local_name       = "azur_lane_all_pony.safetensors"
        civitai_filename = "azur_lane_all_v1.safetensors"
        description      = "All Characters Azur Lane (Pony, 200+ chars)"
    },
    @{
        version_id       = 1010462
        local_name       = "all_chars_hsr_illustrious.safetensors"
        civitai_filename = "star_rail_all-000014.safetensors"
        description      = "All Characters Honkai: Star Rail v2.0 (Illustrious, 70+ chars)"
    },
    @{
        version_id       = 637867
        local_name       = "all_chars_arknights_pony.safetensors"
        civitai_filename = "arknights_all_v4_0711.safetensors"
        description      = "All Characters Arknights v2.0 (Pony, 150-200 chars)"
    },
    @{
        version_id       = 470400
        local_name       = "all_chars_lol_pony.safetensors"
        civitai_filename = "league_of_legends_pony.safetensors"
        description      = "All Characters League of Legends (Pony, 50+ chars)"
    },
    @{
        version_id       = 561561
        local_name       = "all_chars_hi3_pony.safetensors"
        civitai_filename = "honkai_impact_3rd_v1.safetensors"
        description      = "All Characters Honkai Impact 3rd v1.0 (Pony)"
    },
    @{
        version_id       = 550532
        local_name       = "all_chars_genshin_pony124.safetensors"
        civitai_filename = "genshin_v4.safetensors"
        description      = "All Characters Genshin Impact v4.0 (Pony, 127 chars)"
    },
    @{
        version_id       = 501862
        local_name       = "all_chars_genshin_sd15.safetensors"
        civitai_filename = "mki-genshin108-1.5-v3.safetensors"
        description      = "All Characters Genshin Impact 100 chars (SD1.5)"
    },
    @{
        version_id       = 890954
        local_name       = "all_chars_wuthering_waves_pony.safetensors"
        civitai_filename = "wuthering_waves_all.safetensors"
        description      = "All Characters Wuthering Waves v0.9 (Pony, 27 chars)"
    },
    @{
        version_id       = 589974
        local_name       = "all_chars_umamusume_pony.safetensors"
        civitai_filename = "umamusume_all.safetensors"
        description      = "All Characters Umamusume (Pony, 50-100 chars)"
    },
    @{
        version_id       = 899943
        local_name       = "all_chars_idolmaster_cinderella_pony.safetensors"
        civitai_filename = "idolmaster_cinderella_all.safetensors"
        description      = "All Characters Idolmaster Cinderella Girls (Pony, 250+ chars)"
    },
    @{
        version_id       = 559278
        local_name       = "all_chars_idolmaster_shinycolors_pony.safetensors"
        civitai_filename = "idolmaster_shiny_colors.safetensors"
        description      = "All Characters Idolmaster Shiny Colors (Pony)"
    },
    @{
        version_id       = 450477
        local_name       = "all_chars_bocchi_the_rock_sdxl.safetensors"
        civitai_filename = "bocchi_the_rock.safetensors"
        description      = "All Characters Bocchi the Rock! (SDXL, 6 chars)"
    },
    @{
        version_id       = 556880
        local_name       = "all_chars_fate_stay_night_pony.safetensors"
        civitai_filename = "stay_night_all.safetensors"
        description      = "All Characters Fate/stay night + FGO (Pony, 200+ chars)"
    },
    @{
        version_id       = 2250685
        local_name       = "all_chars_amphoreus_hsr_illustrious.safetensors"
        civitai_filename = "All_inone_Amphoreus_V3.6.safetensors"
        description      = "All Characters Amphoreus HSR v3.6 (Illustrious, 14 chars)"
    },
    @{
        version_id       = 2312748
        local_name       = "all_chars_hsr_2025_illustrious.safetensors"
        civitai_filename = "Star_Rail_251013.safetensors"
        description      = "2025 All Characters HSR (Illustrious, 80+ chars)"
    },
    @{
        version_id       = 1051022
        local_name       = "lewd_elves_pony.safetensors"
        civitai_filename = "All_Characters_from_Youkoso_Sukebe_Elf_no_Mori_e_r1.safetensors"
        description      = "All Characters Youkoso! Sukebe Elf no Mori e (Pony, 8 chars)"
    }
)

# =============================================================================
# Summary header
# =============================================================================
Write-Host ""
Write-Host "=== CivitAI All-Characters LoRA Downloader ===" -ForegroundColor Cyan
Write-Host "Target dir : $TargetDir"
Write-Host "Total files: $($Downloads.Count)"
if ($DryRun) { Write-Host "[DRY RUN - no files will be written]" -ForegroundColor Yellow }
Write-Host ""

$skipped  = 0
$downloaded = 0
$failed   = 0

foreach ($item in $Downloads) {
    $localPath = Join-Path $TargetDir $item.local_name

    if (Test-Path $localPath) {
        $sizeMB = [math]::Round((Get-Item $localPath).Length / 1MB, 1)
        Write-Host "SKIP  $($item.local_name)  ($sizeMB MB already exists)" -ForegroundColor DarkGray
        $skipped++
        continue
    }

    $url = "https://civitai.com/api/download/models/$($item.version_id)"
    Write-Host "GET   $($item.local_name)" -ForegroundColor White
    Write-Host "      $($item.description)"
    Write-Host "      URL: $url"

    if ($DryRun) {
        Write-Host "      [dry-run skip]" -ForegroundColor Yellow
        continue
    }

    try {
        $headers = @{ Authorization = "Bearer $ApiKey" }
        Invoke-WebRequest `
            -Uri     $url `
            -Headers $headers `
            -OutFile $localPath `
            -UseBasicParsing `
            -ErrorAction Stop

        $sizeMB = [math]::Round((Get-Item $localPath).Length / 1MB, 1)
        Write-Host "  OK  $sizeMB MB saved" -ForegroundColor Green
        $downloaded++
    }
    catch {
        Write-Host "  FAIL  $($_.Exception.Message)" -ForegroundColor Red
        # Remove partial file
        if (Test-Path $localPath) { Remove-Item $localPath -Force }
        $failed++
    }

    Write-Host ""
}

# =============================================================================
# Final summary
# =============================================================================
Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
Write-Host "  Skipped (already exist): $skipped"
Write-Host "  Downloaded              : $downloaded"
Write-Host "  Failed                  : $failed"
