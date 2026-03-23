@echo off
REM Quick Start Script for Vietnamese Speech-to-Text

echo.
echo [MIC] Vietnamese Speech-to-Text System
echo.

REM Check virtual environment
if not exist "s2t\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found
    echo Please run: python -m venv s2t
    pause
    exit /b 1
)

REM Activate environment
echo [LAUNCH] Activating Python environment...
call s2t\Scripts\activate.bat

REM Menu
echo.
echo Choose your deployment method:
echo 1. [DOCKER] Docker ^(Recommended for production^)
echo 2. [PYTHON] Python CLI ^(Direct execution^)  
echo 3. [DEV] Development mode
echo 4. [CHECK] System health check
echo.

set /p choice=Enter your choice (1-4): 

if "%choice%"=="1" (
    echo [DOCKER] Starting Docker...
    call deployment\start.bat
) else if "%choice%"=="2" (
    echo [PYTHON] Starting Python CLI...
    python src\main.py
) else if "%choice%"=="3" (
    echo [DEV] Starting Development Docker...
    call deployment\start-dev.bat  
) else if "%choice%"=="4" (
    echo [CHECK] Checking system health...
    call deployment\health.bat
) else (
    echo [ERROR] Invalid choice
    pause
)