@echo off
REM ============================================
REM Clean App Directory Structure
REM Dọn dẹp và sắp xếp lại thư mục app/
REM ============================================

echo ========================================
echo  CLEANING APP DIRECTORY
echo ========================================
echo.

cd /d "%~dp0\app"

REM Remove duplicate web_ui.py in tools/
echo [1/4] Removing duplicates...
if exist "tools\web_ui.py" (
    del /F /Q "tools\web_ui.py" >nul 2>&1
    echo     ✓ Removed tools/web_ui.py (duplicate)
)

REM Keep only essential files in app/src/
echo [2/4] Cleaning src/ directory...
if exist "src" (
    echo     Files in src/:
    dir /B "src\"
    echo     ⚠️  Manual review needed for src/
)

REM Check for old notebooks
echo [3/4] Checking notebooks...
if exist "notebooks" (
    echo     Notebooks exist - keeping for experiments
)

REM Archive deprecated items
echo [4/4] Handling deprecated code...
if exist "..\deprecated" (
    if not exist "..\BACKUP_BEFORE_CLEANUP\deprecated" (
        move /Y "..\deprecated" "..\BACKUP_BEFORE_CLEANUP\" >nul 2>&1
        echo     ✓ Moved deprecated/ to BACKUP
    )
)

echo.
echo ========================================
echo  APP CLEANUP COMPLETE!
echo ========================================
echo.
echo Current app/ structure:
echo   app/
echo   ├── web_ui.py          (Web UI entry point)
echo   ├── core/              (Business logic)
echo   ├── api/               (API services)
echo   ├── config/            (Configuration)
echo   ├── templates/         (HTML templates)
echo   ├── tests/             (Unit tests)
echo   └── s2t/               (Virtual environment)
echo.
pause
