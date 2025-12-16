@echo off
echo ========================================
echo   Starting Speech2Text Service
echo ========================================
echo.
echo Service: Audio Transcription + Diarization
echo Port: 5001 (SPEECH2TEXT_PORT in .env)
echo Path: services/speech2text/
echo.
echo Features:
echo   - Whisper Large-v3 (Vietnamese)
echo   - Speaker Diarization
echo   - Real-time Transcription
echo   - Multi-language Support
echo.

REM Setup virtual environment and dependencies
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

cd services\speech2text

echo.
echo Starting Speech2Text Service...
echo Access at: http://localhost:7860
echo.

REM Change to app directory before running
cd app
python web_ui.py

pause
