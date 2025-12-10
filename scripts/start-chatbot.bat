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

cd services\chatbot

REM Check if virtual environment exists
if exist "venv_chatbot\Scripts\activate.bat" (
    echo Using virtual environment...
    call venv_chatbot\Scripts\activate.bat
) else if exist "venv_chatbot_3113\Scripts\activate.bat" (
    echo Using virtual environment (Python 3.11.3)...
    call venv_chatbot_3113\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found!
    echo Please run setup first.
    pause
    exit /b 1
)

echo.
echo Checking dependencies...
python -c "import numpy; print(f'NumPy: {numpy.__version__}')" 2>nul
if errorlevel 1 (
    echo ERROR: Dependencies not installed!
    echo Please run: pip install -r requirements.txt
    pause
    exit /b 1
)

echo.
echo Starting ChatBot...
echo Access at: http://localhost:5001
echo.
python app.py

pause
