@echo off
REM Document Intelligence Service - Start Script

echo ========================================
echo Starting Document Intelligence Service
echo ========================================
echo.

REM Check if DIS venv exists
if not exist DIS (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv DIS
    pause
    exit /b 1
)

REM Activate DIS venv
call DIS\Scripts\activate.bat

REM Check if .env exists
if not exist .env (
    echo [WARNING] .env file not found, using defaults
)

echo Starting service on http://localhost:5003
echo.
echo Press Ctrl+C to stop
echo.

REM Set protobuf to use pure Python implementation (fixes PaddlePaddle compatibility)
set PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION=python

REM Start Flask app
python app.py

pause
