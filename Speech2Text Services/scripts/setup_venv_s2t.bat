@echo off
echo ================================================================
echo   SETUP SPEECH2TEXT VIRTUAL ENVIRONMENT
echo ================================================================
echo.
echo Tao virtual environment rieng cho Speech2Text Service...
echo Moi truong nay su dung Whisper + PhoWhisper + Qwen2.5
echo.

cd /d "i:\AI-Assistant\Speech2Text Services"

REM Create venv
echo [1/6] Dang tao virtual environment venv_s2t...
python -m venv venv_s2t
echo [OK] Da tao venv_s2t
echo.

REM Activate venv
echo [2/6] Dang kich hoat venv_s2t...
call venv_s2t\Scripts\activate.bat
echo [OK] Da kich hoat venv_s2t
echo.

REM Upgrade pip
echo [3/6] Dang nang cap pip...
python -m pip install --upgrade pip
echo [OK] Da nang cap pip
echo.

REM Install PyTorch 2.0.1 with CUDA 11.8
echo [4/6] Dang cai PyTorch 2.0.1 + CUDA 11.8...
pip install torch==2.0.1 torchaudio==2.0.2 --index-url https://download.pytorch.org/whl/cu118
echo [OK] Da cai PyTorch 2.0.1
echo.

REM Install requirements
echo [5/6] Dang cai cac dependencies cua Speech2Text...
pip install -r requirements.txt
echo [OK] Da cai tat ca dependencies
echo.

REM Verify installation
echo [6/6] Kiem tra cai dat...
python -c "import torch; print(f'PyTorch version: {torch.__version__}'); print(f'CUDA available: {torch.cuda.is_available()}'); import transformers; print(f'Transformers: {transformers.__version__}')"
echo.

echo ================================================================
echo   HOAN THANH!
echo ================================================================
echo.
echo Virtual environment da duoc tao tai: venv_s2t
echo.
echo De khoi dong Speech2Text Service:
echo   cd "i:\AI-Assistant\Speech2Text Services"
echo   venv_s2t\Scripts\activate.bat
echo   python app.py
echo.
echo Hoac su dung: start_webui.bat
echo.
echo FEATURES:
echo   - Whisper large-v3 (Global ASR)
echo   - PhoWhisper-large (Vietnamese ASR)
echo   - Qwen2.5-1.5B-Instruct (Smart Fusion)
echo   - Speaker Diarization
echo.
pause
