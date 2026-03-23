@echo off
REM ==============================================================================
REM Edit Image Service - Startup Script (Windows)
REM ==============================================================================

echo.
echo ============================================================
echo   Edit Image Service - Starting...
echo ============================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call venv\Scripts\activate.bat
) else if exist ".venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call .venv\Scripts\activate.bat
) else (
    echo [WARN] No virtual environment found. Using system Python.
)

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    pause
    exit /b 1
)

echo [INFO] Python version:
python --version

REM Check if dependencies are installed
python -c "import torch; import diffusers; import gradio" >nul 2>&1
if errorlevel 1 (
    echo.
    echo [INFO] Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
)

REM Check CUDA availability
echo.
echo [INFO] Checking GPU/CUDA availability...
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}'); print(f'Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU\"}')"

REM Create necessary directories
if not exist "outputs" mkdir outputs
if not exist "logs" mkdir logs
if not exist "models" mkdir models

REM Start the service
echo.
echo ============================================================
echo   Starting Edit Image Service...
echo   Web UI: http://localhost:8100
echo   API Docs: http://localhost:8100/docs
echo ============================================================
echo.

python -m app.main

pause
