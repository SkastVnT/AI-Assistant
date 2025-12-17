@echo off
setlocal enabledelayedexpansion
REM Navigate to project root
cd /d "%~dp0.."

echo ============================================================================
echo   Stable Diffusion Virtual Environment Setup
echo ============================================================================
echo.
echo This will create a Python 3.10.x virtual environment for Stable Diffusion
echo Location: services/stable-diffusion/venv
echo.

REM Check Python version
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found in PATH
    echo.
    echo Please install Python 3.10.6 or higher and add it to PATH
    pause
    exit /b 1
)

for /f "tokens=2" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo Current Python version: %PYTHON_VERSION%

REM Navigate to Stable Diffusion directory
cd services\stable-diffusion

REM Remove old venv if exists
if exist "venv" (
    echo.
    echo [WARNING] Existing venv found. Removing...
    rmdir /s /q venv
    echo [OK] Old venv removed
)

echo.
echo Creating new virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)

echo [OK] Virtual environment created
echo.
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo.
echo Installing basic dependencies...
python -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
    echo [WARNING] Failed to upgrade pip/setuptools/wheel
)

echo.
echo ============================================================================
echo [SUCCESS] Stable Diffusion venv is ready!
echo ============================================================================
echo.
echo Virtual environment: services\stable-diffusion\venv
echo Python: !PYTHON_VERSION!
echo.
echo Next steps:
echo   1. Run start-stable-diffusion.bat to start the WebUI
echo   2. WebUI will auto-install remaining dependencies on first run
echo.
pause
