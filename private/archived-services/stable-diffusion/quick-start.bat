@echo off
REM Quick Start - Stable Diffusion với Python 3.11
echo ================================================================
echo   Starting Stable Diffusion WebUI (Quick Mode)
echo ================================================================
echo.

cd /d K:\AI-Assistant\services\stable-diffusion

REM Check venv
if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Run quick-setup.bat first
    pause
    exit /b 1
)

REM Check PyTorch
echo [INFO] Checking PyTorch installation...
venv\Scripts\python.exe -c "import torch" 2>nul
if errorlevel 1 (
    echo [WARNING] PyTorch not installed! Installing CPU version...
    venv\Scripts\python.exe -m pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1
)

echo.
echo [INFO] Starting Stable Diffusion WebUI...
echo [INFO] Access at: http://localhost:7861
echo [INFO] This may take 3-5 minutes on first run (downloading models)
echo.

REM Set COMMANDLINE_ARGS and run
set COMMANDLINE_ARGS=--skip-python-version-check --port 7861 --api
call webui.bat

pause
