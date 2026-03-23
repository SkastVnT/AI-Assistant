@echo off
echo ================================================================
echo   Fix Stable Diffusion PyTorch - Install CPU Version
echo ================================================================
echo.
echo This installs CPU-only PyTorch for Stable Diffusion
echo (Faster setup, but slower generation)
echo.

cd /d K:\AI-Assistant\services\stable-diffusion

if not exist "venv\Scripts\python.exe" (
    echo [ERROR] Venv not found! Run quick-setup.bat first
    pause
    exit /b 1
)

echo [1/2] Activating venv...
call venv\Scripts\activate.bat

echo [2/2] Installing PyTorch 2.4.1 CPU-only...
pip uninstall -y torch torchvision torchaudio
pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1

echo.
echo [OK] PyTorch CPU installed
echo.
echo Verifying...
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
echo.
echo ================================================================
echo   Done! Now run: webui.bat --skip-python-version-check
echo ================================================================
pause
