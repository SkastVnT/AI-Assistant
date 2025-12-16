@echo off
echo ========================================
echo   Starting ChatBot Service
echo ========================================
echo.
echo Service: Multi-Model AI ChatBot
echo Port: 5000 (CHATBOT_PORT in .env)
echo Path: services/chatbot/
echo.
echo Features:
echo   - Gemini 2.0 Flash, GPT-4o Mini, DeepSeek
echo   - Text-to-Image AI (Stable Diffusion)
echo   - Chat History with MongoDB
echo   - File Upload ^& Analysis
echo   - MCP Integration for Code Access
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
echo Access at: http://localhost:5000
echo.
echo Development mode: Set DEBUG=1 for auto-reload
echo Production mode: Default (DEBUG=0)
echo.
set DEBUG=1
set HOST=127.0.0.1
set CHATBOT_PORT=5000
python app.py

pause
