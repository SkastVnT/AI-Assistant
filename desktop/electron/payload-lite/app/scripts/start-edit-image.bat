@echo off
REM ============================================================================
REM Edit Image Service Launcher
REM Port: 8100 (Full API) + 7860 (Grok UI)
REM ============================================================================

chcp 65001 >nul 2>&1
title Edit Image Service

cd /d "%~dp0\..\services\edit-image"

echo ================================================================================
echo   Edit Image Service - Grok-like Image Editor
echo ================================================================================
echo.
echo   [1] Grok-like UI     (Port 7860) - UI don gian, nhap text de edit
echo   [2] Full Service     (Port 8100) - Day du tinh nang
echo   [3] Both             (7860 + 8100)
echo.
echo ================================================================================
set /p mode="Select mode [1/2/3]: "

REM Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    call venv\Scripts\activate.bat
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
) else (
    call venv\Scripts\activate.bat
)

echo.

if "%mode%"=="1" goto GROK_UI
if "%mode%"=="2" goto FULL_SERVICE
if "%mode%"=="3" goto BOTH
goto GROK_UI

:GROK_UI
echo [INFO] Starting Grok-like UI on port 7860...
echo [INFO] Open: http://localhost:7860
echo.
python run_grok_ui.py
goto END

:FULL_SERVICE
echo [INFO] Starting Full Service on port 8100...
echo [INFO] Open: http://localhost:8100
echo.
python -m uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
goto END

:BOTH
echo [INFO] Starting both services...
echo [INFO] Grok UI: http://localhost:7860
echo [INFO] Full API: http://localhost:8100
echo.
start "Grok UI" cmd /k "cd /d %cd% && venv\Scripts\activate && python run_grok_ui.py"
timeout /t 3 >nul
python -m uvicorn app.main:app --host 0.0.0.0 --port 8100 --reload
goto END

:END
pause
