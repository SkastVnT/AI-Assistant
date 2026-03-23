@echo off
REM Force UTF-8 encoding to prevent Unicode errors
chcp 65001 >nul 2>&1

echo ================================================================
echo   SETUP STABLE DIFFUSION VIRTUAL ENVIRONMENT
echo ================================================================
echo.
echo Tao virtual environment rieng cho Stable Diffusion WebUI...
echo Moi truong nay su dung PyTorch 2.0.1 de tuong thich voi SD
echo.

cd /d i:\AI-Assistant\stable-diffusion-webui

REM Create venv
echo [1/5] Dang tao virtual environment venv_sd...
python -m venv venv_sd
echo [OK] Da tao venv_sd
echo.

REM Activate venv
echo [2/5] Dang kich hoat venv_sd...
call venv_sd\Scripts\activate.bat
echo [OK] Da kich hoat venv_sd
echo.

REM Install PyTorch 2.0.1 with CUDA 11.8
echo [3/5] Dang cai PyTorch 2.0.1 + CUDA 11.8...
pip install torch==2.0.1+cu118 torchvision==0.15.2+cu118 torchaudio==2.0.2+cu118 --index-url https://download.pytorch.org/whl/cu118
echo [OK] Da cai PyTorch 2.0.1
echo.

REM Install xformers 0.0.20
echo [4/5] Dang cai xformers 0.0.20...
pip install xformers==0.0.20 --index-url https://download.pytorch.org/whl/cu118
echo [OK] Da cai xformers
echo.

REM Install SD requirements
echo [5/5] Dang cai cac dependencies cua Stable Diffusion...
pip install -r requirements.txt
echo [OK] Da cai tat ca dependencies
echo.

REM Verify installation
echo ================================================================
echo   KIEM TRA CAI DAT
echo ================================================================
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}')"
echo.

echo ================================================================
echo   HOAN THANH!
echo ================================================================
echo.
echo Virtual environment da duoc tao tai: venv_sd
echo.
echo De khoi dong Stable Diffusion:
echo   cd i:\AI-Assistant\stable-diffusion-webui
echo   venv_sd\Scripts\activate.bat
echo   python webui.py --api --xformers --no-half-vae --disable-safe-unpickle
echo.
echo Hoac su dung: scripts\startup\start_chatbot_with_sd.bat
echo.
pause
