@echo off
REM Session Management Helper Script
REM VistralS2T v3.0

echo ================================================================================
echo SESSION MANAGER - VistralS2T v3.0
echo ================================================================================
echo.

:menu
echo [1] List all sessions
echo [2] Show latest session
echo [3] Read latest transcript
echo [4] Clean old sessions (keep last 10)
echo [5] Archive sessions to ZIP
echo [6] Exit
echo.
set /p choice="Select option (1-6): "

if "%choice%"=="1" goto list_all
if "%choice%"=="2" goto show_latest
if "%choice%"=="3" goto read_latest
if "%choice%"=="4" goto clean_old
if "%choice%"=="5" goto archive
if "%choice%"=="6" goto end
echo Invalid choice!
goto menu

:list_all
echo.
echo All Sessions:
echo ----------------------------------------
powershell -Command "Get-ChildItem app\data\results\sessions\ -Directory | Sort-Object Name -Descending | ForEach-Object { Write-Host \"  [$($_.Name.Replace('session_', ''))]\" -ForegroundColor Cyan; $count = (Get-ChildItem $_.FullName -File).Count; Write-Host \"    Files: $count\" -ForegroundColor Gray }"
echo.
pause
goto menu

:show_latest
echo.
echo Latest Session:
echo ----------------------------------------
powershell -Command "$latest = Get-ChildItem app\data\results\sessions\ -Directory | Sort-Object Name -Descending | Select-Object -First 1; if ($latest) { Write-Host \"Session: $($latest.Name)\" -ForegroundColor Green; Write-Host \"Created: $($latest.CreationTime)\" -ForegroundColor Gray; Write-Host \"`nFiles:\" -ForegroundColor Yellow; Get-ChildItem $latest.FullName -File | ForEach-Object { Write-Host \"  - $($_.Name)\" -ForegroundColor Cyan; Write-Host \"    Size: $([math]::Round($_.Length/1KB, 2)) KB\" -ForegroundColor Gray } } else { Write-Host 'No sessions found' -ForegroundColor Red }"
echo.
pause
goto menu

:read_latest
echo.
echo Latest Final Transcript:
echo ========================================
powershell -Command "$latest = Get-ChildItem app\data\results\sessions\ -Directory | Sort-Object Name -Descending | Select-Object -First 1; if ($latest) { $transcript = Get-ChildItem $latest.FullName -Filter 'final_transcript_*.txt' -ErrorAction SilentlyContinue; if (-not $transcript) { $transcript = Get-ChildItem $latest.FullName -Filter 'dual_fused_*.txt' | Select-Object -First 1 }; if ($transcript) { Write-Host \"File: $($transcript.Name)\" -ForegroundColor Green; Write-Host \"\" ; Get-Content $transcript.FullName } else { Write-Host 'No transcript found in session' -ForegroundColor Red } } else { Write-Host 'No sessions found' -ForegroundColor Red }"
echo.
pause
goto menu

:clean_old
echo.
echo Cleaning old sessions (keeping last 10)...
powershell -Command "$sessions = Get-ChildItem app\data\results\sessions\ -Directory | Sort-Object Name -Descending; $toKeep = $sessions | Select-Object -First 10; $toDelete = $sessions | Select-Object -Skip 10; if ($toDelete) { Write-Host \"Deleting $($toDelete.Count) old sessions...\" -ForegroundColor Yellow; $toDelete | ForEach-Object { Write-Host \"  - $($_.Name)\" -ForegroundColor Gray; Remove-Item $_.FullName -Recurse -Force }; Write-Host \"`nDone! Kept $($toKeep.Count) sessions\" -ForegroundColor Green } else { Write-Host 'No old sessions to delete (less than 10 total)' -ForegroundColor Cyan }"
echo.
pause
goto menu

:archive
echo.
set /p days="Archive sessions older than how many days? (default: 7): "
if "%days%"=="" set days=7
echo.
echo Archiving sessions older than %days% days...
powershell -Command "$days = %days%; $threshold = (Get-Date).AddDays(-$days); $old = Get-ChildItem app\data\results\sessions\ -Directory | Where-Object { $_.CreationTime -lt $threshold }; if ($old) { $archiveName = \"archive_sessions_$(Get-Date -Format 'yyyyMMdd_HHmmss').zip\"; Write-Host \"Creating archive: $archiveName\" -ForegroundColor Yellow; $old | Compress-Archive -DestinationPath $archiveName; Write-Host \"`nArchived $($old.Count) sessions\" -ForegroundColor Green; Write-Host \"Archive location: $(Get-Location)\$archiveName\" -ForegroundColor Cyan; $delete = Read-Host \"`nDelete archived sessions? (y/n)\"; if ($delete -eq 'y') { $old | Remove-Item -Recurse -Force; Write-Host \"Deleted archived sessions\" -ForegroundColor Green } } else { Write-Host \"No sessions older than $days days found\" -ForegroundColor Cyan }"
echo.
pause
goto menu

:end
echo.
echo Goodbye!
exit /b
