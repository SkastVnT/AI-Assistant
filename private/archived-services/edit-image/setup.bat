@echo off
REM ==============================================================================
REM Edit Image Service - Setup Script (Windows)
REM ==============================================================================

echo.
echo ============================================================
echo   Edit Image Service - Setup
echo ============================================================
echo.

REM Get script directory
set "SCRIPT_DIR=%~dp0"
cd /d "%SCRIPT_DIR%"

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10 or later.
    pause
    exit /b 1
)

echo [INFO] Python version:
python --version

REM Create virtual environment
echo.
echo [INFO] Creating virtual environment...
python -m venv venv
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
echo.
echo [INFO] Upgrading pip...
python -m pip install --upgrade pip

REM Install PyTorch with CUDA
echo.
echo [INFO] Installing PyTorch with CUDA support...
echo [INFO] This may take a while...
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
if errorlevel 1 (
    echo [WARN] Failed to install CUDA version. Trying CPU version...
    pip install torch torchvision torchaudio
)

REM Install other dependencies
echo.
echo [INFO] Installing other dependencies...
pip install -r requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)

REM Verify installation
echo.
echo [INFO] Verifying installation...
python -c "import torch; print(f'PyTorch: {torch.__version__}')"
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"
python -c "import diffusers; print(f'Diffusers: {diffusers.__version__}')"
python -c "import gradio; print(f'Gradio: {gradio.__version__}')"

REM Create directories
echo.
echo [INFO] Creating directories...
if not exist "outputs" mkdir outputs
if not exist "logs" mkdir logs
if not exist "models" mkdir models

echo.
echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo   To start the service, run: start.bat
echo   Or activate venv and run: python -m app.main
echo.

pause
