@echo off
REM Document Intelligence Service - Setup Script
REM Phase 1: Basic OCR & WebUI

REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

echo ========================================
echo Document Intelligence Service - Setup
echo Phase 1: Basic OCR with FREE models
echo ========================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found! Please install Python 3.10+
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

echo [2/5] Activating virtual environment...
call venv\Scripts\activate.bat

echo [3/5] Upgrading pip...
python -m pip install --upgrade pip

echo [4/5] Installing dependencies (this may take 5-10 minutes)...
pip install -r requirements.txt

if errorlevel 1 (
    echo [ERROR] Failed to install dependencies
    pause
    exit /b 1
)

echo [5/5] Creating .env file...
if not exist .env (
    copy .env.example .env
    echo Created .env file from template
)

echo.
echo ========================================
echo Setup completed successfully!
echo ========================================
echo.
echo Next steps:
echo 1. Edit .env file if needed
echo 2. Run: start_service.bat
echo.
echo For manual start:
echo   venv\Scripts\activate
echo   python app.py
echo.
pause
