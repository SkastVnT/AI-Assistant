@echo off
echo ================================================================
echo   SETUP CHATBOT VIRTUAL ENVIRONMENT
echo ================================================================
echo.
echo Tao virtual environment rieng cho ChatBot voi Local Models...
echo Moi truong nay su dung PyTorch 2.4.0 de ho tro transformers
echo.

cd /d i:\AI-Assistant\ChatBot

REM Create venv
echo [1/6] Dang tao virtual environment venv_chatbot...
python -m venv venv_chatbot
echo [OK] Da tao venv_chatbot
echo.

REM Activate venv
echo [2/6] Dang kich hoat venv_chatbot...
call venv_chatbot\Scripts\activate.bat
echo [OK] Da kich hoat venv_chatbot
echo.

REM Install PyTorch 2.4.0 with CUDA 11.8
echo [3/6] Dang cai PyTorch 2.4.0 + CUDA 11.8...
pip install torch==2.4.0+cu118 torchvision==0.19.0+cu118 torchaudio==2.4.0+cu118 --index-url https://download.pytorch.org/whl/cu118
echo [OK] Da cai PyTorch 2.4.0
echo.

REM Install xformers for PyTorch 2.4
echo [4/6] Dang cai xformers 0.0.27...
pip install xformers==0.0.27.post2+cu118 --index-url https://download.pytorch.org/whl/cu118
echo [OK] Da cai xformers
echo.

REM Install ChatBot requirements
echo [5/6] Dang cai cac dependencies cua ChatBot...
pip install -r requirements.txt
echo [OK] Da cai tat ca dependencies
echo.

REM Install local model dependencies
echo [6/6] Dang cai dependencies cho local models...
pip install transformers>=4.40.0 accelerate bitsandbytes sentencepiece
echo [OK] Da cai local model dependencies
echo.

REM Verify installation
echo ================================================================
echo   KIEM TRA CAI DAT
echo ================================================================
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); print(f'CUDA version: {torch.version.cuda if torch.cuda.is_available() else \"N/A\"}'); print(f'GPU: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"N/A\"}'); import transformers; print(f'Transformers: {transformers.__version__}')"
echo.

echo ================================================================
echo   HOAN THANH!
echo ================================================================
echo.
echo Virtual environment da duoc tao tai: venv_chatbot
echo.
echo De khoi dong ChatBot:
echo   cd i:\AI-Assistant\ChatBot
echo   venv_chatbot\Scripts\activate.bat
echo   python app.py
echo.
echo Hoac su dung: scripts\startup\start_chatbot_with_sd.bat
echo.
echo LOCAL MODELS:
echo   - Qwen1.5-1.8B Local (2GB VRAM)
echo   - BloomVN-8B Local (4GB VRAM with 8-bit)
echo   - Qwen2.5-14B Local (7GB VRAM with 8-bit)
echo.
pause
