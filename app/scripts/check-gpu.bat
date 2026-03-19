@echo off
REM ============================================================================
REM GPU Detection Utility - Quick Check
REM ============================================================================

title AI-Assistant - GPU Check
color 0B

REM Get project root
cd /d "%~dp0.."

echo.
echo ================================================================================
echo   GPU Detection and Verification
echo ================================================================================
echo.

REM Check if virtual environment exists
if exist ".venv\Scripts\activate.bat" (
    call .venv\Scripts\activate.bat
    python scripts\utilities\check_gpu.py
) else (
    echo [ERROR] Virtual environment not found!
    echo Please run scripts\setup-venv.bat first
    echo.
    pause
    exit /b 1
)

echo.
pause
