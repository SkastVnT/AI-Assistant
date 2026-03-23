@echo off
REM Quick Setup for Stable Diffusion with Python 3.11
echo ================================================================
echo   Quick Setup - Stable Diffusion WebUI
echo ================================================================
echo.

REM Refresh PATH
set "Path=C:\Program Files\Python311;C:\Program Files\Python311\Scripts;%Path%"

REM Create venv if not exists
if not exist "venv\Scripts\python.exe" (
    echo [1/3] Creating virtual environment...
    python -m venv venv
    echo [OK] Virtual environment created
) else (
    echo [OK] Virtual environment already exists
)
echo.

REM Activate and install
echo [2/3] Installing dependencies...
call venv\Scripts\activate.bat
python -m pip install --upgrade pip

REM Install PyTorch 2.4.1 (compatible with Python 3.11)
pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 --index-url https://download.pytorch.org/whl/cu118

REM Install other requirements if requirements.txt exists
if exist "requirements_versions.txt" (
    pip install -r requirements_versions.txt
)

echo.
echo [3/3] Verifying installation...
python -c "import torch; print('PyTorch:', torch.__version__); print('CUDA:', torch.cuda.is_available())"
echo.
echo ================================================================
echo   Setup Complete!
echo ================================================================
echo.
echo Now you can run: webui.bat --skip-python-version-check
echo.
pause
