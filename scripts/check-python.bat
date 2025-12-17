@echo off
REM ============================================================================
REM Check Python Version
REM Requires: Python 3.11.x (Recommended: 3.11.9)
REM ============================================================================

echo Checking Python version...

REM Get Python version
for /f "tokens=2 delims= " %%v in ('python --version 2^>^&1') do set PYTHON_VERSION=%%v

REM Extract major.minor version
for /f "tokens=1,2 delims=." %%a in ("%PYTHON_VERSION%") do (
    set PYTHON_MAJOR=%%a
    set PYTHON_MINOR=%%b
)

REM Check if Python 3.11.x (Recommended) or 3.10.x
if "%PYTHON_MAJOR%.%PYTHON_MINOR%"=="3.11" (
    echo [OK] Python %PYTHON_VERSION% detected (3.11.x - Recommended)
    exit /b 0
)

if "%PYTHON_MAJOR%.%PYTHON_MINOR%"=="3.10" (
    echo [OK] Python %PYTHON_VERSION% detected (3.10.x - Compatible)
    exit /b 0
)

REM Python version not compatible
echo.
echo ============================================================================
echo [WARNING] Python version %PYTHON_VERSION% detected!
echo.
echo Recommended version: Python 3.11.9
echo Also compatible: Python 3.10.x
echo Current version may cause compatibility issues.
echo.
echo You can continue, but some packages may not work correctly.
echo ============================================================================
echo.
timeout /t 3 >nul
exit /b 0
