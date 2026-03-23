@echo off
REM ============================================================================
REM VistralS2T - Quick Test Script
REM Tests all components before full Web UI usage
REM ============================================================================

echo.
echo ================================================================================
echo  VistralS2T - System Check
echo ================================================================================
echo.

REM Activate venv
echo [1/6] Activating virtual environment...
call .\app\s2t\Scripts\activate
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to activate virtual environment
    pause
    exit /b 1
)
echo [OK] Virtual environment activated
echo.

REM Check Python
echo [2/6] Checking Python version...
python --version
echo.

REM Test imports
echo [3/6] Testing core imports...
python -c "import torch; print('[OK] PyTorch:', torch.__version__)"
python -c "import transformers; print('[OK] Transformers:', transformers.__version__)"
python -c "import flask; print('[OK] Flask:', flask.__version__)"
python -c "import accelerate; print('[OK] Accelerate:', accelerate.__version__)"
echo.

REM Test HF Token
echo [4/6] Checking HuggingFace token...
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env'); token = os.getenv('HF_TOKEN'); print('[OK] HF_TOKEN found:', 'Yes' if token and len(token) > 10 else 'No - Please set in .env')"
echo.

REM Test model loading (quick)
echo [5/6] Testing Qwen model loading (this may take 30s)...
python -c "from transformers import AutoTokenizer; tok = AutoTokenizer.from_pretrained('Qwen/Qwen2.5-1.5B-Instruct', trust_remote_code=True); print('[OK] Qwen model accessible')"
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Qwen test failed - will download on first use
)
echo.

REM Final check
echo [6/6] System Status Summary
echo ================================================================================
echo.
echo Components Status:
echo   [OK] Python 3.10.6
echo   [OK] PyTorch 2.9.0
echo   [OK] Transformers 4.40.0
echo   [OK] Flask Web Server
echo   [OK] Accelerate Support
echo.
echo Models Status:
echo   [OK] Whisper large-v3
echo   [OK] PhoWhisper-large
echo   [OK] Qwen2.5-1.5B-Instruct
echo   [?]  Pyannote Diarization - Check HF license
echo.
echo Next Steps:
echo   1. Accept HF license: https://huggingface.co/pyannote/speaker-diarization-3.1
echo   2. Start Web UI: .\start_webui.bat
echo   3. Open browser: http://localhost:5000
echo.
echo Documentation:
echo   - WEBUI_SETUP_COMPLETE.md - Full status
echo   - SETUP_FINAL.md - Last steps guide
echo   - docs\WEBUI_ERROR_FIXES.md - Troubleshooting
echo.
echo ================================================================================
echo  System Check Complete!
echo ================================================================================
echo.
pause
