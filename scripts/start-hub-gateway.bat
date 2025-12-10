@echo off
echo ========================================
echo   Starting Hub Gateway
echo ========================================
echo.
echo Service: Hub Gateway (API Orchestrator)
echo Port: 3000
echo Path: services/hub-gateway/
echo.

cd services\hub-gateway

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Using virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Using global Python...
)

echo Starting Hub Gateway...
python hub.py

pause
