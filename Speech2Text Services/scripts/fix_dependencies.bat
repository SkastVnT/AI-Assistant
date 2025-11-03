@echo off
REM ============================================================================
REM VistralS2T - Fix Dependencies Installation (Step-by-Step)
REM Purpose: Install dependencies in correct order to avoid resolution conflicts
REM ============================================================================

echo.
echo ================================================================================
echo  VistralS2T - Fixing Dependencies Installation
echo ================================================================================
echo.

REM Check if virtual environment is activated
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python not found. Please activate virtual environment first:
    echo         .\app\s2t\Scripts\activate
    echo.
    pause
    exit /b 1
)

echo [INFO] Current Python environment:
python --version
echo.

REM Upgrade pip first
echo [STEP 0/5] Upgrading pip, setuptools, wheel...
python -m pip install --upgrade pip setuptools wheel
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to upgrade pip
    pause
    exit /b 1
)
echo [OK] Pip upgraded
echo.

REM Step 1: Install PyTorch and NumPy
echo ================================================================================
echo [STEP 1/5] Installing PyTorch and NumPy (Foundation)
echo ================================================================================
pip install -r requirements-step1.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install PyTorch foundation
    echo Trying alternative: CPU-only PyTorch
    pip install torch==2.0.1 torchaudio==2.0.2 numpy==1.24.4 --index-url https://download.pytorch.org/whl/cpu
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Still failed. Please check your internet connection.
        pause
        exit /b 1
    )
)
echo [OK] PyTorch foundation installed
echo.

REM Step 2: Install AI Models
echo ================================================================================
echo [STEP 2/5] Installing AI Models (Transformers, Whisper, Pyannote)
echo ================================================================================
pip install -r requirements-step2.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Some AI models failed to install
    echo Continuing with available models...
)
echo [OK] AI models installed
echo.

REM Step 3: Install Audio Processing
echo ================================================================================
echo [STEP 3/5] Installing Audio Processing Libraries
echo ================================================================================
pip install -r requirements-step3.txt
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Some audio libraries failed to install
    echo System will work with basic audio support
)
echo [OK] Audio processing installed
echo.

REM Step 4: Install Web UI and Utilities
echo ================================================================================
echo [STEP 4/5] Installing Web UI and Utilities
echo ================================================================================
pip install -r requirements-step4.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install Web UI dependencies
    pause
    exit /b 1
)
echo [OK] Web UI installed
echo.

REM Step 5: Optional - Install TorchCodec (if FFmpeg available)
echo ================================================================================
echo [STEP 5/5] Installing TorchCodec (Optional)
echo ================================================================================
where ffmpeg >nul 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [INFO] FFmpeg found, installing TorchCodec...
    pip install torchcodec --no-deps
    if %ERRORLEVEL% EQU 0 (
        echo [OK] TorchCodec installed
    ) else (
        echo [WARN] TorchCodec installation failed (non-critical)
        echo        PhoWhisper will use fallback audio loading
    )
) else (
    echo [SKIP] FFmpeg not found, skipping TorchCodec
    echo        Run scripts\install_ffmpeg.bat if you need PhoWhisper optimization
)
echo.

REM Verification
echo ================================================================================
echo [VERIFICATION] Checking critical imports...
echo ================================================================================

python -c "import torch; print('[OK] PyTorch:', torch.__version__)" 2>nul || echo [FAIL] PyTorch
python -c "import transformers; print('[OK] Transformers:', transformers.__version__)" 2>nul || echo [FAIL] Transformers
python -c "import faster_whisper; print('[OK] Faster-Whisper: OK')" 2>nul || echo [FAIL] Faster-Whisper
python -c "import pyannote.audio; print('[OK] Pyannote: OK')" 2>nul || echo [FAIL] Pyannote
python -c "import flask; print('[OK] Flask:', flask.__version__)" 2>nul || echo [FAIL] Flask
python -c "import accelerate; print('[OK] Accelerate:', accelerate.__version__)" 2>nul || echo [FAIL] Accelerate

echo.
echo ================================================================================
echo  Installation Complete!
echo ================================================================================
echo.
echo Next steps:
echo 1. Configure .env file with HF_TOKEN (for diarization)
echo 2. Optionally run: .\scripts\install_ffmpeg.bat (for PhoWhisper optimization)
echo 3. Start Web UI: .\start_webui.bat
echo.
echo For detailed setup guide, see: docs\WEBUI_ERROR_FIXES.md
echo.
pause
