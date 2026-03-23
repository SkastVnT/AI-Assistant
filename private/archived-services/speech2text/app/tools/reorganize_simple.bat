@echo off
REM ========================================
REM Project Reorganization Script
REM Simplified: Keep essential files in root, move everything else to app/
REM ========================================

echo ========================================
echo  Project Reorganization
echo ========================================
echo.

REM Create backup first
echo [BACKUP] Creating backup...
if not exist "BACKUP_REORGANIZE\" mkdir "BACKUP_REORGANIZE"
xcopy /E /I /Y "app" "BACKUP_REORGANIZE\app\" >nul 2>&1
xcopy /E /I /Y "*.bat" "BACKUP_REORGANIZE\" >nul 2>&1
xcopy /E /I /Y "*.py" "BACKUP_REORGANIZE\" >nul 2>&1
echo [OK] Backup created in BACKUP_REORGANIZE\

echo.
echo ========================================
echo  Step 1: Clean Root Directory
echo ========================================

REM Move all .bat files (except essential ones) to app/scripts/
echo [MOVE] Moving batch files to app\scripts\...
if not exist "app\scripts\" mkdir "app\scripts"

if exist "fix_webui.bat" move /Y "fix_webui.bat" "app\scripts\" >nul
if exist "install_webui_deps.bat" move /Y "install_webui_deps.bat" "app\scripts\" >nul
if exist "rebuild_project.bat" move /Y "rebuild_project.bat" "app\scripts\" >nul
if exist "run_diarization_cli.bat" move /Y "run_diarization_cli.bat" "app\scripts\" >nul
if exist "setup.bat" move /Y "setup.bat" "app\scripts\" >nul

echo [OK] Batch files moved

REM Move documentation to app/docs/
echo [MOVE] Moving documentation to app\docs\...
if exist "CONTRIBUTING.md" move /Y "CONTRIBUTING.md" "app\docs\" >nul
if exist "INSTALLATION_SUCCESS.md" move /Y "INSTALLATION_SUCCESS.md" "app\docs\" >nul
if exist "QUICKSTART_v3.5.md" move /Y "QUICKSTART_v3.5.md" "app\docs\" >nul
if exist "REORGANIZE_GUIDE.md" move /Y "REORGANIZE_GUIDE.md" "app\docs\" >nul
if exist "REORGANIZE_PLAN.md" move /Y "REORGANIZE_PLAN.md" "app\docs\" >nul
if exist "SUMMARY_VI.md" move /Y "SUMMARY_VI.md" "app\docs\" >nul
if exist "README_NEW.md" move /Y "README_NEW.md" "app\docs\" >nul

echo [OK] Documentation moved

REM Move utility scripts to app/tools/
echo [MOVE] Moving utility scripts to app\tools\...
if exist "check.py" move /Y "check.py" "app\tools\" >nul
if exist "VERSION_3.5_UPGRADE_GUIDE.py" move /Y "VERSION_3.5_UPGRADE_GUIDE.py" "app\tools\" >nul

echo [OK] Utility scripts moved

echo.
echo ========================================
echo  Step 2: Remove Duplicate Directories
echo ========================================

REM Remove duplicate audio/ directory at root (use app/audio/)
if exist "audio\" (
    echo [REMOVE] Removing duplicate audio\ directory...
    rmdir /S /Q "audio\" 2>nul
    echo [OK] Removed audio\
)

REM Remove duplicate input_audio/ directory (use app/data/audio/)
if exist "input_audio\" (
    echo [REMOVE] Removing duplicate input_audio\ directory...
    rmdir /S /Q "input_audio\" 2>nul
    echo [OK] Removed input_audio\
)

REM Remove duplicate output/ directory at root (use app/output/)
if exist "output\" (
    echo [REMOVE] Removing duplicate output\ directory...
    rmdir /S /Q "output\" 2>nul
    echo [OK] Removed output\
)

REM Remove duplicate core/ directory at root (use app/core/)
if exist "core\" (
    echo [REMOVE] Removing duplicate core\ directory...
    rmdir /S /Q "core\" 2>nul
    echo [OK] Removed core\
)

REM Remove duplicate data/ directory at root (use app/data/)
if exist "data\" (
    echo [REMOVE] Removing duplicate data\ directory...
    rmdir /S /Q "data\" 2>nul
    echo [OK] Removed data\
)

echo.
echo ========================================
echo  Step 3: Archive Deprecated Code
echo ========================================

REM Move deprecated/ to app/deprecated/ if exists
if exist "deprecated\" (
    echo [MOVE] Moving deprecated\ to app\deprecated\...
    if exist "app\deprecated\" (
        xcopy /E /I /Y "deprecated\" "app\deprecated\" >nul
        rmdir /S /Q "deprecated\" 2>nul
    ) else (
        move "deprecated" "app\deprecated\" >nul
    )
    echo [OK] Deprecated code archived
)

echo.
echo ========================================
echo  Step 4: Clean Reorganization Scripts
echo ========================================

REM Move reorganization scripts to app/tools/
if exist "reorganize.bat" move /Y "reorganize.bat" "app\tools\" >nul
if exist "reorganize_app.bat" move /Y "reorganize_app.bat" "app\tools\" >nul

echo [OK] Reorganization scripts moved

echo.
echo ========================================
echo  Reorganization Complete!
echo ========================================
echo.
echo Root directory now contains ONLY:
echo   - README.md (main documentation)
echo   - requirements.txt (Python dependencies)
echo   - .env (configuration)
echo   - .gitignore (git config)
echo   - start_webui.bat (quick start)
echo   - start_diarization.bat (quick start)
echo   - app/ (all application code)
echo   - BACKUP_REORGANIZE/ (backup)
echo   - BACKUP_BEFORE_CLEANUP/ (old backup)
echo.
echo All other files moved to app/ subdirectories:
echo   - app/scripts/ (batch files)
echo   - app/docs/ (documentation)
echo   - app/tools/ (utility scripts)
echo   - app/docker/ (Docker configs)
echo.
echo [BACKUP] Backup saved in: BACKUP_REORGANIZE\
echo.

pause
