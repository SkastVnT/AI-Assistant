@echo off
echo ========================================
echo   Starting LoRA Training Tool
echo ========================================
echo.
echo Service: AI Model Fine-tuning
echo Port: 7862
echo Path: services/lora-training/
echo.
echo Features:
echo   - LoRA Model Training
echo   - Gemini AI Assistant
echo   - Dataset Tools (WD14 Tagger)
echo   - Redis Caching
echo   - Training Monitoring
echo.

cd services\lora-training

REM Check if virtual environment exists
if exist "lora\Scripts\activate.bat" (
    echo Using virtual environment...
    call lora\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found!
    echo Please run setup first.
    pause
    exit /b 1
)

echo.
echo Starting LoRA Training WebUI...
echo Access at: http://localhost:7862
echo.
python webui.py --port 7862

pause
