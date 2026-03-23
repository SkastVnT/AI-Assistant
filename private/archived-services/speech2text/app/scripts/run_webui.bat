@echo off
REM VistralS2T Web UI Launcher
REM Version 3.1

echo ================================================================================
echo VISTRAL S2T - WEB UI LAUNCHER
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

REM Check Flask installation
python -c "import flask" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] Flask not installed
    echo [INFO] Installing web dependencies...
    echo.
    pip install flask flask-cors flask-socketio python-socketio eventlet
    echo.
)

REM Check pyannote.audio
python -c "import pyannote.audio" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [WARNING] pyannote.audio not installed (optional for diarization)
    echo.
    set /p install="Install speaker diarization support? (y/n): "
    if /i "!install!"=="y" (
        pip install pyannote.audio
        echo.
        echo [IMPORTANT] Accept model license at:
        echo   https://huggingface.co/pyannote/speaker-diarization-3.1
        echo.
        pause
    )
)

REM Create necessary directories
if not exist "app\data\audio\raw" mkdir app\data\audio\raw
if not exist "app\data\results\sessions" mkdir app\data\results\sessions
if not exist "templates" mkdir templates
if not exist "static" mkdir static

echo.
echo ================================================================================
echo STARTING WEB SERVER
echo ================================================================================
echo.
echo Server will start at: http://localhost:5000
echo.
echo Features:
echo   ✓ Drag & drop audio upload
echo   ✓ Real-time processing updates
echo   ✓ Speaker diarization
echo   ✓ Dual model transcription (Whisper + PhoWhisper + Qwen)
echo   ✓ Download results
echo.
echo Press Ctrl+C to stop the server
echo.
echo ================================================================================
echo.

cd app
python web_ui.py

pause
