@echo off
REM Install CUDA-enabled PyTorch for GPU acceleration
REM This will replace CPU-only PyTorch with GPU version

echo ================================================
echo CUDA PyTorch Installation Script
echo ================================================
echo.

REM Check if nvidia-smi works
echo Checking for NVIDIA GPU...
nvidia-smi >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] NVIDIA GPU not detected or drivers not installed
    echo.
    echo Please:
    echo 1. Install NVIDIA GPU drivers from https://www.nvidia.com/Download/index.aspx
    echo 2. Restart your computer
    echo 3. Run this script again
    echo.
    pause
    exit /b 1
)

echo [OK] NVIDIA GPU detected!
nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader
echo.

REM Ask user for CUDA version
echo Select CUDA version to install:
echo 1. CUDA 11.8 (Recommended - Best compatibility, RTX 20xx/30xx/40xx)
echo 2. CUDA 12.1 (Latest - For RTX 40xx series)
echo 3. CPU Only (No GPU acceleration)
echo.
set /p choice="Enter choice (1-3): "

if "%choice%"=="1" (
    echo.
    echo Installing PyTorch with CUDA 11.8...
    pip uninstall -y torch torchvision torchaudio
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu118
) else if "%choice%"=="2" (
    echo.
    echo Installing PyTorch with CUDA 12.1...
    pip uninstall -y torch torchvision torchaudio
    pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
) else if "%choice%"=="3" (
    echo.
    echo Installing CPU-only PyTorch...
    pip uninstall -y torch torchvision torchaudio
    pip install torch torchvision
) else (
    echo Invalid choice. Exiting.
    pause
    exit /b 1
)

echo.
echo ================================================
echo Installation complete!
echo ================================================
echo.

REM Verify installation
echo Verifying CUDA installation...
python -c "import torch; print(f'PyTorch: {torch.__version__}'); print(f'CUDA Available: {torch.cuda.is_available()}'); print(f'CUDA Version: {torch.version.cuda}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"None\"}')"

echo.
echo ================================================
echo Next Steps:
echo ================================================
echo 1. Run: python gpu_info.py
echo 2. Check optimal settings for your GPU
echo 3. Update config.yaml with recommended settings
echo 4. Test: python test_upscale.py
echo.

pause
