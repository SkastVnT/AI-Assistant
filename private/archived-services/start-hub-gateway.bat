@echo off
REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

REM Navigate to project root (parent of scripts folder)
cd /d "%~dp0.."

echo ========================================
echo   Starting Hub Gateway
echo ========================================
echo.
echo Service: Hub Gateway (API Orchestrator)
echo Port: 3000
echo Path: services/hub-gateway/
echo.

REM Setup virtual environment and dependencies
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

cd services\hub-gateway

echo.
echo Starting Hub Gateway...
echo Access at: http://localhost:3000
echo.
python hub.py

pause
