@echo off
REM ============================================================================
REM Start Grok-like Anime Edit Service
REM ============================================================================

setlocal enabledelayedexpansion

echo ============================================================
echo    Grok-like Anime Edit Service
echo    RTX 5090 32GB VRAM
echo ============================================================
echo.

set EDIT_IMAGE_DIR=%~dp0..
cd /d "%EDIT_IMAGE_DIR%"

REM Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python not found!
    pause
    exit /b 1
)

REM Check for CUDA
python -c "import torch; print(f'CUDA: {torch.cuda.is_available()}')" 2>nul
if %errorlevel% neq 0 (
    echo WARNING: PyTorch not installed!
)

REM Start ComfyUI in background
echo.
echo [1/2] Starting ComfyUI on port 8188...
cd ComfyUI
start "ComfyUI" python main.py --listen 0.0.0.0 --port 8188
cd ..

REM Wait for ComfyUI to start
echo Waiting for ComfyUI to start...
timeout /t 10 /nobreak >nul

REM Start Grok-like UI
echo.
echo [2/2] Starting Grok-like UI on port 7860...
python -c "from app.ui.grok_ui import launch_standalone; launch_standalone(7860)"

pause
