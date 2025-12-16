@echo off
REM ================================================================================
REM  VistralS2T - Web UI Launcher
REM  Quick launcher for the web interface
REM ================================================================================

echo.
echo ================================================================================
echo  Starting VistralS2T Web UI...
echo ================================================================================
echo.

REM Change to script directory
cd /d "%~dp0"

REM Activate virtual environment (check root venv first, then local)
if exist "..\..\\.venv\Scripts\activate.bat" (
    call ..\..\\.venv\Scripts\activate.bat
    echo [OK] Using root virtual environment
) else if exist "app\s2t\Scripts\activate.bat" (
    call app\s2t\Scripts\activate.bat
    echo [OK] Using local virtual environment
) else (
    echo [WARNING] Virtual environment not found, using system Python
)

REM Suppress Python warnings (torchcodec, deprecations)
set PYTHONWARNINGS=ignore

REM Change to app directory and run web UI
cd app
python web_ui.py

REM Pause to see errors
pause

pause
