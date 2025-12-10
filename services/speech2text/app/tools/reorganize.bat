@echo off
REM ============================================
REM Project Reorganization Script
REM Sắp xếp lại cấu trúc project cho gọn gàng
REM ============================================

echo ========================================
echo  PROJECT REORGANIZATION
echo ========================================
echo.

cd /d "%~dp0"

REM Create backup first
echo [1/7] Creating backup...
if not exist "BACKUP_REORGANIZE" mkdir "BACKUP_REORGANIZE"
xcopy /E /I /Y "*.bat" "BACKUP_REORGANIZE\" >nul 2>&1
xcopy /E /I /Y "*.md" "BACKUP_REORGANIZE\" >nul 2>&1
echo     ✓ Backup created

REM Create directory structure
echo [2/7] Creating directory structure...
if not exist "scripts" mkdir "scripts"
if not exist "docker" mkdir "docker"
if not exist "tools" mkdir "tools"
if not exist "docs" mkdir "docs"
echo     ✓ Directories created

REM Move batch scripts
echo [3/7] Moving batch scripts to scripts/...
move /Y "setup.bat" "scripts\" >nul 2>&1
move /Y "start_webui.bat" "scripts\" >nul 2>&1
move /Y "start_diarization.bat" "scripts\" >nul 2>&1
move /Y "run_diarization_cli.bat" "scripts\" >nul 2>&1
move /Y "fix_webui.bat" "scripts\" >nul 2>&1
move /Y "install_webui_deps.bat" "scripts\" >nul 2>&1
move /Y "rebuild_project.bat" "scripts\" >nul 2>&1
echo     ✓ Batch scripts moved

REM Move documentation
echo [4/7] Moving documentation to docs/...
move /Y "QUICKSTART_v3.5.md" "docs\QUICKSTART.md" >nul 2>&1
move /Y "INSTALLATION_SUCCESS.md" "docs\INSTALLATION.md" >nul 2>&1
move /Y "SUMMARY_VI.md" "docs\SUMMARY_VI.md" >nul 2>&1
move /Y "CONTRIBUTING.md" "docs\CONTRIBUTING.md" >nul 2>&1
move /Y "VERSION_3.5_UPGRADE_GUIDE.py" "docs\" >nul 2>&1
echo     ✓ Documentation moved

REM Move Docker files
echo [5/7] Moving Docker files to docker/...
if exist "app\docker" (
    xcopy /E /I /Y "app\docker\*" "docker\" >nul 2>&1
    echo     ✓ Docker files copied
) else (
    echo     - No Docker files to move
)

REM Move tools
echo [6/7] Moving development tools to tools/...
if exist "app\tools" (
    for %%f in (app\tools\test_*.py app\tools\download_*.py app\tools\system_*.py app\tools\fix_*.py app\tools\patch_*.py) do (
        move /Y "%%f" "tools\" >nul 2>&1
    )
    echo     ✓ Tools moved
) else (
    echo     - No tools to move
)

REM Clean up duplicates
echo [7/7] Cleaning up duplicates...
if exist "audio" (
    rmdir /S /Q "audio" >nul 2>&1
    echo     ✓ Removed duplicate audio/
)
if exist "input_audio" (
    rmdir /S /Q "input_audio" >nul 2>&1
    echo     ✓ Removed duplicate input_audio/
)
if exist "output" (
    rmdir /S /Q "output" >nul 2>&1
    echo     ✓ Removed duplicate output/
)
if exist "core" (
    rmdir /S /Q "core" >nul 2>&1
    echo     ✓ Removed duplicate core/ (root level)
)
if exist "check.py" (
    del /F /Q "check.py" >nul 2>&1
    echo     ✓ Removed duplicate check.py
)

echo.
echo ========================================
echo  REORGANIZATION COMPLETE!
echo ========================================
echo.
echo New structure:
echo   scripts/     - All batch scripts
echo   docker/      - Docker configuration
echo   tools/       - Development tools
echo   docs/        - Documentation
echo   app/         - Application source code
echo   data/        - Data directories
echo.
echo Backup saved in: BACKUP_REORGANIZE/
echo.
echo ⚠️  IMPORTANT: Update paths in:
echo   - scripts/*.bat (if referencing other files)
echo   - docker/docker-compose.yml
echo   - README.md
echo.
pause
