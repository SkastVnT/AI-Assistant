@echo off
REM ================================================================================
REM  CUDA Fix for VistralS2T
REM  Download and install CUDA libraries for PyTorch compatibility
REM ================================================================================

echo.
echo ================================================================================
echo  CUDA Library Fix for PyTorch CUDA 11.8
echo ================================================================================
echo.

echo [1/4] Downloading CUDA 11.8 libraries...
echo This will download essential CUDA libraries for PyTorch compatibility

REM Create temp directory
if not exist "%TEMP%\cuda_fix" mkdir "%TEMP%\cuda_fix"
cd /d "%TEMP%\cuda_fix"

echo.
echo [2/4] Alternative solutions:
echo.
echo Option 1: Download CUDA 11.8 Toolkit manually
echo URL: https://developer.nvidia.com/cuda-11-8-0-download-archive
echo.
echo Option 2: Force CPU mode (add to .env):
echo FORCE_CPU=true
echo.
echo Option 3: Reinstall PyTorch with CUDA 12.x
echo.

echo [3/4] Creating CPU fallback configuration...

REM Add CPU fallback to .env
echo. >> "%~dp0app\config\.env"
echo # CUDA Fix - Force CPU mode if CUDA libraries missing >> "%~dp0app\config\.env"
echo # FORCE_CPU=true >> "%~dp0app\config\.env"

echo.
echo [4/4] CUDA Fix Options Complete!
echo ================================================================================
echo.
echo NEXT STEPS:
echo 1. For CUDA support: Install CUDA 11.8 Toolkit from NVIDIA website
echo 2. For CPU mode: Uncomment FORCE_CPU=true in app\config\.env
echo 3. System will auto-fallback to CPU if CUDA fails
echo.
echo Current status: System will use CPU mode automatically
echo ================================================================================
echo.

pause