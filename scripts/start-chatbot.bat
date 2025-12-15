@echo off
echo ========================================
echo   Starting ChatBot Service
echo ========================================
echo.
echo Service: Multi-Model AI ChatBot
echo Port: 5001
echo Path: services/chatbot/
echo.
echo Features:
echo   - Gemini 2.0 Flash, GPT-4o Mini, DeepSeek
echo   - Text-to-Image AI (Stable Diffusion)
echo   - Chat History with MongoDB
echo   - File Upload & Analysis
echo.

REM Setup virtual environment and dependencies
call "%~dp0setup-venv.bat"
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to setup environment
    pause
    exit /b 1
)

cd services\chatbot

echo.
echo Starting ChatBot...
echo Access at: http://localhost:5001
echo.
python app.py

pause
