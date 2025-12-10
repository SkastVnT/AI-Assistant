@echo off
echo ========================================
echo   Starting Speech2Text Service
echo ========================================
echo.
echo Service: Audio Transcription + Diarization
echo Port: 7860
echo Path: services/speech2text/
echo.
echo Features:
echo   - Whisper Large-v3 (Vietnamese)
echo   - Speaker Diarization
echo   - Real-time Transcription
echo   - Multi-language Support
echo.

cd services\speech2text

REM Check if virtual environment exists
if exist "venv\Scripts\activate.bat" (
    echo Using virtual environment...
    call venv\Scripts\activate.bat
) else (
    echo Using global Python...
)

echo.
echo Starting Speech2Text Service...
echo Access at: http://localhost:7860
echo.
python app\web_ui.py

pause
