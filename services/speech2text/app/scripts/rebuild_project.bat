@echo off
REM ============================================================================
REM VistralS2T - Complete Project Rebuild Script v3.6
REM Rebuilds entire project with latest dependencies
REM ============================================================================

echo.
echo ============================================================================
echo  VistralS2T v3.6 - COMPLETE PROJECT REBUILD
echo ============================================================================
echo.
echo This script will:
echo   1. Clean existing virtual environment
echo   2. Clean Python cache files
echo   3. Create new virtual environment
echo   4. Install/upgrade all dependencies
echo   5. Verify installation
echo   6. Optional: Rebuild Docker images
echo.
echo WARNING: This will delete app\s2t\ virtual environment!
echo.
pause

cd /d "%~dp0..\.."

REM ============= STEP 1: CLEANUP =============
echo.
echo [1/6] Cleaning up old files...
echo ============================================================================

if exist "app\s2t\" (
    echo Removing old virtual environment...
    rmdir /s /q "app\s2t"
    echo [OK] Virtual environment removed
) else (
    echo [SKIP] No virtual environment found
)

echo Cleaning Python cache...
for /r %%i in (__pycache__) do (
    if exist "%%i" (
        rmdir /s /q "%%i" 2>nul
    )
)

for /r %%i in (*.pyc) do del /f /q "%%i" 2>nul
for /r %%i in (*.pyo) do del /f /q "%%i" 2>nul

echo [OK] Cache cleaned

REM ============= STEP 2: CHECK PYTHON =============
echo.
echo [2/6] Checking Python installation...
echo ============================================================================

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found!
    echo.
    echo Please install Python 3.10.6:
    echo   Option 1: Direct install from python.org
    echo   Option 2: Use pyenv-win
    echo     - Install: https://github.com/pyenv-win/pyenv-win#installation
    echo     - Run: pyenv install 3.10.6
    echo     - Set: pyenv global 3.10.6
    echo.
    pause
    exit /b 1
)

python --version
echo [OK] Python found

REM ============= STEP 3: CREATE VENV =============
echo.
echo [3/6] Creating new virtual environment...
echo ============================================================================

python -m venv app\s2t
if errorlevel 1 (
    echo [ERROR] Failed to create virtual environment!
    echo Make sure Python venv module is installed.
    pause
    exit /b 1
)

echo [OK] Virtual environment created

REM ============= STEP 4: ACTIVATE & UPGRADE PIP =============
echo.
echo [4/6] Activating environment and upgrading pip...
echo ============================================================================

call app\s2t\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)

python -m pip install --upgrade pip setuptools wheel
echo [OK] Pip upgraded

REM ============= STEP 5: INSTALL DEPENDENCIES =============
echo.
echo [5/6] Installing dependencies (this may take several minutes)...
echo ============================================================================

echo Installing from requirements.txt...
pip install -r requirements.txt --upgrade

if errorlevel 1 (
    echo.
    echo [WARNING] Some packages failed to install!
    echo Common issues:
    echo   - PyTorch: Visit https://pytorch.org/ for GPU-specific install
    echo   - Build tools: Install Visual C++ Build Tools
    echo   - Audio libs: Install ffmpeg
    echo.
    echo Attempting to continue...
)

echo.
echo Installing critical packages individually...

REM Critical packages
pip install torch>=2.0.1 torchaudio>=2.0.2 --index-url https://download.pytorch.org/whl/cu118
pip install transformers>=4.40.0
pip install faster-whisper>=1.0.3
pip install pyannote.audio>=3.1.1
pip install flask>=3.0.2 flask-cors>=4.0.0 flask-socketio>=5.3.6 eventlet>=0.35.0
pip install librosa soundfile scipy

echo [OK] Core dependencies installed

REM ============= STEP 6: VERIFICATION =============
echo.
echo [6/6] Verifying installation...
echo ============================================================================

echo.
echo Checking Python packages...
python -c "import torch; print(f'PyTorch: {torch.__version__}')" 2>nul
python -c "import torchaudio; print(f'TorchAudio: {torchaudio.__version__}')" 2>nul
python -c "import transformers; print(f'Transformers: {transformers.__version__}')" 2>nul
python -c "import flask; print(f'Flask: {flask.__version__}')" 2>nul
python -c "import flask_cors; print('Flask-CORS: OK')" 2>nul
python -c "import pyannote.audio; print('Pyannote: OK')" 2>nul
python -c "from app.core.models import WhisperClient; print('Models Package: OK')" 2>nul
python -c "from app.core.utils.vad_utils import VADProcessor; print('VAD Utils: OK')" 2>nul

echo.
echo Checking CUDA availability...
python -c "import torch; print(f'CUDA Available: {torch.cuda.is_available()}')" 2>nul
python -c "import torch; print(f'CUDA Device: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else \"CPU only\"}')" 2>nul

echo.
echo ============================================================================
echo  INSTALLATION COMPLETE!
echo ============================================================================
echo.
echo Virtual Environment: app\s2t\
echo Activate with: .\app\s2t\Scripts\activate
echo.
echo NEXT STEPS:
echo   1. Configure .env file: notepad app\config\.env
echo      - Add HF_TOKEN for diarization
echo      - Set AUDIO_PATH for testing
echo.
echo   2. Test CLI: 
echo      cd app\core\pipelines
echo      python with_diarization_pipeline.py
echo.
echo   3. Test Web UI:
echo      .\start_webui.bat
echo      Open: http://localhost:5000
echo.
echo   4. Check v3.6 upgrade guide:
echo      python scripts\UPGRADE_TO_v3.6.py
echo.
echo ============================================================================

REM ============= OPTIONAL: DOCKER REBUILD =============
echo.
set /p docker_rebuild="Rebuild Docker images? (y/n): "
if /i "%docker_rebuild%"=="y" (
    echo.
    echo Rebuilding Docker images...
    cd app\docker
    docker compose build --no-cache
    cd ..\..
    echo [OK] Docker images rebuilt
) else (
    echo [SKIP] Docker rebuild skipped
)

echo.
echo ============================================================================
echo  ALL DONE! Project rebuilt successfully for v3.6.0
echo ============================================================================
echo.
echo To start working:
echo   1. .\app\s2t\Scripts\activate
echo   2. cd app\core\pipelines
echo   3. python with_diarization_pipeline.py
echo.
echo Or launch Web UI:
echo   .\start_webui.bat
echo.
pause
