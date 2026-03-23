@echo off
REM Setup LoRA Training Tool Environment
REM Creates virtual environment and installs all dependencies

echo ===============================================
echo LoRA Training Tool - Environment Setup
echo ===============================================
echo.

REM Check Python version
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python not found!
    echo Please install Python 3.10 or higher from https://www.python.org/
    pause
    exit /b 1
)

echo [1/5] Creating virtual environment...
if exist ".\lora" (
    echo [WARNING] Virtual environment already exists
    choice /C YN /M "Do you want to recreate it"
    if errorlevel 2 goto skip_venv
    echo Removing old environment...
    rmdir /s /q .\lora
)

python -m venv lora
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment created

:skip_venv

REM Activate virtual environment
echo.
echo [2/5] Activating virtual environment...
call .\lora\Scripts\activate.bat

REM Upgrade pip
echo.
echo [3/5] Upgrading pip...
python -m pip install --upgrade pip setuptools wheel --quiet

REM Install PyTorch (CPU version by default)
echo.
echo [4/5] Installing PyTorch...
echo.
echo Select PyTorch version:
echo   1. CPU only (smaller, faster download)
echo   2. CUDA 11.8 (for NVIDIA GPU)
echo   3. CUDA 12.1 (for latest NVIDIA GPU)
echo.
choice /C 123 /M "Select option"

if errorlevel 3 (
    echo Installing PyTorch with CUDA 12.1...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
) else if errorlevel 2 (
    echo Installing PyTorch with CUDA 11.8...
    pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
) else (
    echo Installing PyTorch CPU version...
    pip install torch torchvision torchaudio
)

REM Install main dependencies
echo.
echo [5/5] Installing dependencies...
pip install --quiet --upgrade ^
    diffusers ^
    transformers ^
    accelerate ^
    safetensors ^
    bitsandbytes ^
    peft ^
    xformers ^
    pillow ^
    opencv-python ^
    numpy ^
    pandas ^
    tqdm ^
    omegaconf ^
    einops ^
    tensorboard ^
    wandb ^
    flask ^
    flask-socketio ^
    flask-cors ^
    python-socketio ^
    eventlet ^
    redis ^
    google-generativeai ^
    huggingface-hub ^
    onnxruntime

REM Install WD14 Tagger dependencies
pip install --quiet onnxruntime huggingface-hub pillow

echo.
echo ===============================================
echo Setup Complete!
echo ===============================================
echo.
echo Next steps:
echo   1. Edit .env file with your API keys
echo   2. Run start_webui_with_redis.bat to start WebUI
echo.
echo Optional:
echo   - Start Redis: docker run -d -p 6379:6379 redis:7-alpine
echo   - View logs: tail -f logs/training.log
echo.
pause
