@echo off
REM Run Speech-to-Text with Speaker Diarization
REM VistralS2T v3.1

echo ================================================================================
echo VISTRAL S2T - WITH SPEAKER DIARIZATION v3.1
echo ================================================================================
echo.

REM Check if pyenv is available
where pyenv >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] pyenv not found in PATH
    echo [FIX] Run: fix_pyenv_path.bat
    pause
    exit /b 1
)

REM Check Python version
pyenv version | findstr "3.10" >nul
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Python 3.10 not active
    echo [INFO] Switching to Python 3.10.6...
    pyenv global 3.10.6
)

REM Activate virtual environment
if exist "app\s2t\Scripts\activate.bat" (
    echo [OK] Activating virtual environment...
    call app\s2t\Scripts\activate.bat
) else (
    echo [ERROR] Virtual environment not found
    echo [FIX] Run: setup.bat
    pause
    exit /b 1
)

REM Check required packages
python -c "import pyannote.audio" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] pyannote.audio not installed
    echo.
    echo This feature requires pyannote.audio for speaker diarization.
    echo.
    set /p install="Install now? (y/n): "
    if /i "%install%"=="y" (
        echo.
        echo [INSTALL] Installing pyannote.audio...
        pip install pyannote.audio
        echo.
        echo [OK] Installation complete
        echo.
        echo [IMPORTANT] You need to accept the model license:
        echo   1. Visit: https://huggingface.co/pyannote/speaker-diarization-3.1
        echo   2. Click "Agree and access repository"
        echo   3. Make sure HF_TOKEN is set in app/config/.env
        echo.
        pause
    ) else (
        echo [SKIP] Installation skipped
        echo [INFO] Falling back to standard pipeline without diarization
        pause
    )
)

REM Run the diarization pipeline
echo.
echo Starting diarization pipeline...
echo ────────────────────────────────────────────────────────────────────────────────
echo.

cd app\core
python run_with_diarization.py

echo.
echo ────────────────────────────────────────────────────────────────────────────────
echo.
echo [COMPLETE] Check app\data\results\sessions\ for output files
echo.
pause
