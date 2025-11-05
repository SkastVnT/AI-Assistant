@echo off
REM Document Intelligence Service - Start Script

echo ========================================
echo Starting Document Intelligence Service
echo ========================================
echo.

REM Check if venv exists
if not exist venv (
    echo [ERROR] Virtual environment not found!
    echo Please run setup.bat first
    pause
    exit /b 1
)

REM Activate venv
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found, using defaults
)

echo Starting service on http://localhost:5003
echo.
echo Press Ctrl+C to stop
echo.

REM Start Flask app
python app.py

pause
